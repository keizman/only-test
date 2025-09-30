#!/usr/bin/env python3
"""
播放页控制栏保活工具（XML-only）
================================

用途
- UIAutomator2 只能识别当前可见元素。播放页的控制栏/seekbar 会在短时间内自动隐藏，
  导致后续 XML 选择器找不到控件。
- 本模块提供单实例的异步“保活点击”功能：按指定时长定期检测控制栏是否可见，若不可见则在安全区域轻点唤醒。

设计要点
- 单实例：新的调用会自动取消之前的保活任务，防止并发点击。
- 安全点击区域：x=屏幕宽度的 1/2，y=屏幕高度的 15%（横/竖屏自适应）。
- 可见性判定：
  - 若 XML 中不存在 exist_field_keyword（例如 "Brightness"），且拥有非空 resource-id 的节点数 < 10，
    认为控制栏处于隐藏状态，需要点击唤醒。
- 设备适配：通过 `adb wm size` 读取实际分辨率，点击点使用像素坐标。

API
- start_keep_play_controls(duration_s, detect_interval=0.1, exist_field_keyword="Brightness", device_id=None)
- stop_keep_play_controls()
"""

import asyncio
import subprocess
import time
from typing import Optional
import xml.etree.ElementTree as ET

__all__ = [
    "start_keep_play_controls",
    "stop_keep_play_controls",
    "is_full_screen",
    "playing_stat_keep_displayed_button",
]

_keeper_task: Optional[asyncio.Task] = None
_keeper_lock = asyncio.Lock()


def _adb_prefix(device_id: Optional[str]) -> list[str]:
    return ["adb"] + (["-s", device_id] if device_id else [])


def _get_screen_size(device_id: Optional[str]) -> tuple[int, int]:
    try:
        out = subprocess.run(
            _adb_prefix(device_id) + ["shell", "wm", "size"], capture_output=True
        )
        if out.returncode == 0 and out.stdout:
            txt = out.stdout.decode("utf-8", errors="ignore")
            if "Physical size:" in txt:
                sz = txt.split("Physical size:")[-1].strip().split("\n")[0].strip()
                w, h = sz.split("x")
                return int(w), int(h)
    except Exception:
        pass
    return 1080, 1920


def _parse_bounds(bounds_str: str) -> tuple[int, int, int, int]:
    try:
        s = bounds_str.replace('[', '').replace(']', ',')
        xs = [int(x) for x in s.split(',') if x.strip()]
        if len(xs) >= 4:
            return xs[0], xs[1], xs[2], xs[3]
    except Exception:
        pass
    return 0, 0, 0, 0


def _xml_stats(xml_text: str) -> tuple[int, bool]:
    """返回 (非空 resource-id 数量, 是否包含 exist_field_keyword) 的占位函数使用方需再次传 keyword。"""
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return 0, False
    rid_count = 0
    # exist_field_keyword 的判断在调用处完成，这里只统计 rid
    for node in root.iter():
        if node.tag == 'hierarchy':
            continue
        rid = (node.attrib.get('resource-id') or '').strip()
        if rid:
            rid_count += 1
    return rid_count, False


def _xml_has_keyword(xml_text: str, keyword: str) -> bool:
    kw = (keyword or '').strip()
    if not kw:
        return False
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return False
    k = kw.lower()
    for node in root.iter():
        if node.tag == 'hierarchy':
            continue
        attrib = node.attrib
        text = (attrib.get('text') or '').lower()
        desc = (attrib.get('content-desc') or '').lower()
        rid = (attrib.get('resource-id') or '').lower()
        cls = (attrib.get('class') or '').lower()
        if (k in text) or (k in desc) or (k in rid) or (k in cls):
            return True
    return False


def _xml_has_keyword_timed(xml_text: str, keyword: str) -> tuple[bool, dict]:
    """Like _xml_has_keyword, but with timing details: {'parse_ms':..., 'scan_nodes':..., 'total_ms':...} """
    from time import perf_counter
    t0 = perf_counter()
    try:
        t1 = perf_counter()
        root = ET.fromstring(xml_text)
        parse_ms = (perf_counter() - t1) * 1000.0
    except Exception:
        return False, {'parse_ms': 0.0, 'scan_nodes': 0, 'total_ms': (perf_counter()-t0)*1000.0}
    k = (keyword or '').strip().lower()
    scanned = 0
    found = False
    for node in root.iter():
        if node.tag == 'hierarchy':
            continue
        scanned += 1
        attrib = node.attrib
        blob = (attrib.get('text','') + attrib.get('content-desc','') + attrib.get('resource-id','') + attrib.get('class','')).lower()
        if k and (k in blob):
            found = True
            break
    return found, {'parse_ms': parse_ms, 'scan_nodes': scanned, 'total_ms': (perf_counter()-t0)*1000.0}


async def _dump_current_xml_timed(device_id: Optional[str]) -> tuple[str, str, dict]:
    """Dump UI XML with timing detail.
    Returns: (xml_text, mode, timings)
      - mode: 'sdcard' | 'exec-out' | 'none'
      - timings: {'dump_ms':..., 'cat_ms':..., 'exec_ms':..., 'total_ms':...}
    """
    from time import perf_counter
    # Try sdcard method first
    t0 = perf_counter()
    try:
        t1 = perf_counter()
        _ = subprocess.run(_adb_prefix(device_id) + ["shell", "uiautomator", "dump", "/sdcard/window_dump.xml"], capture_output=True)
        dump_ms = (perf_counter() - t1) * 1000.0
        t2 = perf_counter()
        out = subprocess.run(_adb_prefix(device_id) + ["shell", "cat", "/sdcard/window_dump.xml"], capture_output=True)
        cat_ms = (perf_counter() - t2) * 1000.0
        if out.returncode == 0 and out.stdout:
            txt = out.stdout.decode("utf-8", errors='ignore')
            return txt, 'sdcard', {'dump_ms': dump_ms, 'cat_ms': cat_ms, 'total_ms': (perf_counter()-t0)*1000.0}
    except Exception:
        pass
    # Fallback to exec-out
    try:
        t3 = perf_counter()
        proc = await asyncio.create_subprocess_exec(
            *_adb_prefix(device_id), "exec-out", "uiautomator", "dump", "/dev/tty",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        exec_ms = (perf_counter() - t3) * 1000.0
        if proc.returncode == 0 and stdout:
            txt = stdout.decode(errors='ignore')
            idx = txt.find("<hierarchy")
            if idx >= 0:
                return txt[idx:], 'exec-out', {'exec_ms': exec_ms, 'total_ms': (perf_counter()-t0)*1000.0}
    except Exception:
        pass
    return "", 'none', {'total_ms': (perf_counter()-t0)*1000.0}


async def _dump_current_xml(device_id: Optional[str]) -> str:
    txt, _, _ = await _dump_current_xml_timed(device_id)
    return txt


async def _keep_worker(duration_s: float, detect_interval: float, exist_field_keyword: str, device_id: Optional[str], verbose: bool) -> None:
    try:
        start_t = time.time()
        end_t = start_t + float(duration_s)
        w, h = _get_screen_size(device_id)
        tap_x = int(w / 2)
        # 点击点默认使用顶部 15%（避免中间点导致控件被再次隐藏）。如需扩展可调整为 [0.15, 0.50, 0.85]
        y_norm_candidates = [0.15]
        idx = 0
        # 反抖与保护：避免短时间内重复点击导致控件被隐藏
        last_tap_ts = 0.0
        last_seen_ts = 0.0
        consecutive_miss = 0
        tap_cooldown_s = 0.8         # 每次点击后至少冷却 0.8s 再允许下一次点击
        visible_grace_s = 1.0        # 最近刚看到可见时，给予 1.0s 宽限，不立即点击
        require_misses = 1           # 连续观察到不可见 Misses 次后才允许点击（加速首次点击）
        if verbose:
            print(f"[keep] start: duration={duration_s}s interval={detect_interval}s keyword='{exist_field_keyword}' device={device_id} screen={w}x{h} candidates={y_norm_candidates}")
        # 主循环：每个 interval 周期获取 XML，若无关键字则点击；有则等待下一个周期
        while time.time() < end_t:
            # 1) dump XML + decode
            xml_text, mode, dump_t = await _dump_current_xml_timed(device_id)
            # 2) parse+scan keyword
            has_kw, parse_t = _xml_has_keyword_timed(xml_text, exist_field_keyword)
            now = time.time()
            elapsed = now - start_t
            if verbose:
                if mode == 'sdcard':
                    print(f"[keep] t={elapsed:.1f}s step: dump mode=sdcard dump_ms={dump_t.get('dump_ms',0):.1f} cat_ms={dump_t.get('cat_ms',0):.1f} total={dump_t.get('total_ms',0):.1f} size={len(xml_text)}")
                elif mode == 'exec-out':
                    print(f"[keep] t={elapsed:.1f}s step: dump mode=exec-out exec_ms={dump_t.get('exec_ms',0):.1f} total={dump_t.get('total_ms',0):.1f} size={len(xml_text)}")
                else:
                    print(f"[keep] t={elapsed:.1f}s step: dump mode=none total={dump_t.get('total_ms',0):.1f} size={len(xml_text)}")
                print(f"[keep] t={elapsed:.1f}s step: parse parse_ms={parse_t.get('parse_ms',0):.1f} scanned={parse_t.get('scan_nodes',0)} total={parse_t.get('total_ms',0):.1f} has_kw={has_kw}")
            if has_kw:
                last_seen_ts = now
                consecutive_miss = 0
                if verbose:
                    print(f"[keep] t={elapsed:.1f}s decision: idle (recently visible)")
            else:
                consecutive_miss += 1
                # 判断是否允许点击
                if (now - last_tap_ts) < tap_cooldown_s:
                    if verbose:
                        print(f"[keep] t={elapsed:.1f}s decision: skip (cooldown {tap_cooldown_s:.1f}s)")
                elif (now - last_seen_ts) < visible_grace_s:
                    if verbose:
                        print(f"[keep] t={elapsed:.1f}s decision: skip (visible grace {visible_grace_s:.1f}s, misses={consecutive_miss})")
                elif consecutive_miss < require_misses:
                    if verbose:
                        print(f"[keep] t={elapsed:.1f}s decision: wait (require_misses={require_misses}, misses={consecutive_miss})")
                else:
                    y_norm = y_norm_candidates[idx % len(y_norm_candidates)]
                    tap_y = max(1, int(h * y_norm))
                    if verbose:
                        print(f"[keep] t={elapsed:.1f}s decision: TAP x={tap_x} y={tap_y} (y_norm={y_norm:.2f})")
                    t_tap0 = time.perf_counter()
                    subprocess.run(_adb_prefix(device_id) + ["shell", "input", "tap", str(tap_x), str(tap_y)], capture_output=True)
                    tap_ms = (time.perf_counter() - t_tap0) * 1000.0
                    if verbose:
                        print(f"[keep] t={elapsed:.1f}s action: tap_ms={tap_ms:.1f}; post_tap_sleep_ms=250")
                    last_tap_ts = now
                    consecutive_miss = 0
                    idx += 1
                    await asyncio.sleep(0.25)  # 点击后给 UI 少许时间反应
            sleep_s = max(0.05, float(detect_interval))
            if verbose:
                print(f"[keep] t={elapsed:.1f}s sleep: {sleep_s*1000:.0f}ms to next interval")
            await asyncio.sleep(sleep_s)
        if verbose:
            print("[keep] end: worker finished")
    except asyncio.CancelledError:
        if verbose:
            print("[keep] cancelled")
        return
    except Exception as e:
        if verbose:
            print(f"[keep] error: {e}")
        return


def is_full_screen(device_id: Optional[str] = None) -> bool:
    """Heuristic orientation/fullscreen check based on dumpsys activity top.
    - If mCurrentConfig contains "port" -> True (portrait)
    - If contains "land" -> False (landscape)
    Note: heuristic only; keep-display coordinates are robust in both cases.
    """
    try:
        out = subprocess.run(
            _adb_prefix(device_id) + ["shell", "dumpsys", "activity", "top"], capture_output=True, timeout=5
        )
        if out.returncode == 0 and out.stdout:
            s = out.stdout.decode("utf-8", errors="ignore").lower()
            if "mcurrentconfig" in s:
                if " port " in (" " + s + " "):
                    return True
                if " land " in (" " + s + " "):
                    return False
    except Exception:
        pass
    # Default True
    return True


async def start_keep_play_controls(duration_s: float, detect_interval: float = 0.1, exist_field_keyword: str = "Brightness", device_id: Optional[str] = None, verbose: bool = False) -> None:
    """
    启动播放页控制栏保活。

    Args:
        duration_s: 保活持续时间（秒）
        detect_interval: 侦测间隔（秒），建议 0.1~0.3
        exist_field_keyword: 控制栏可见时必然存在的字段（如 Brightness）
        device_id: ADB 设备 ID，可选
    """
    global _keeper_task
    async with _keeper_lock:
        # 取消旧任务
        if _keeper_task and not _keeper_task.done():
            _keeper_task.cancel()
            try:
                await _keeper_task
            except Exception:
                pass
        # 启动新任务
        loop = asyncio.get_running_loop()
        _keeper_task = loop.create_task(_keep_worker(duration_s, detect_interval, exist_field_keyword, device_id, verbose))


async def stop_keep_play_controls() -> None:
    """停止当前的控制栏保活任务（如果存在）。"""
    global _keeper_task
    async with _keeper_lock:
        if _keeper_task and not _keeper_task.done():
            _keeper_task.cancel()
            try:
                await _keeper_task
            except Exception:
                pass
        _keeper_task = None


# 兼容你给出的命名（exist_filed_keyword 的 filed 保持原文拼写）
async def playing_stat_keep_displayed_button(duration_s: float,
                                            detect_interval: float = 0.1,
                                            exist_filed_keyword: str = "Brightness",
                                            device_id: Optional[str] = None,
                                            verbose: bool = False) -> None:
    return await start_keep_play_controls(duration_s=duration_s,
                                          detect_interval=detect_interval,
                                          exist_field_keyword=exist_filed_keyword,
                                          device_id=device_id,
                                          verbose=verbose)

