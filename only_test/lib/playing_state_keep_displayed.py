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
            _adb_prefix(device_id) + ["shell", "wm", "size"], capture_output=True, text=True
        )
        if out.returncode == 0 and "Physical size:" in out.stdout:
            sz = out.stdout.split("Physical size:")[-1].strip().split("\n")[0].strip()
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


async def _dump_current_xml(device_id: Optional[str]) -> str:
    # 优先 exec-out → /dev/tty，回退到 /sdcard/window_dump.xml
    try:
        proc = await asyncio.create_subprocess_exec(
            *_adb_prefix(device_id), "exec-out", "uiautomator", "dump", "/dev/tty",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0 and stdout:
            txt = stdout.decode(errors='ignore')
            idx = txt.find("<hierarchy")
            if idx >= 0:
                return txt[idx:]
    except Exception:
        pass
    try:
        _ = subprocess.run(_adb_prefix(device_id) + ["shell", "uiautomator", "dump", "/sdcard/window_dump.xml"], capture_output=True, text=True)
        out = subprocess.run(_adb_prefix(device_id) + ["shell", "cat", "/sdcard/window_dump.xml"], capture_output=True, text=True)
        if out.returncode == 0:
            return out.stdout
    except Exception:
        pass
    return ""


async def _keep_worker(duration_s: float, detect_interval: float, exist_field_keyword: str, device_id: Optional[str]) -> None:
    try:
        end_t = time.time() + float(duration_s)
        w, h = _get_screen_size(device_id)
        tap_x = int(w / 2)
        tap_y = max(1, int(h * 0.15))
        while time.time() < end_t:
            xml_text = await _dump_current_xml(device_id)
            rid_count, _ = _xml_stats(xml_text)
            has_kw = _xml_has_keyword(xml_text, exist_field_keyword)
            # 判定：关键字缺失 且 resource-id 数偏少 → 点击唤醒
            if (not has_kw) and (rid_count < 10):
                subprocess.run(_adb_prefix(device_id) + ["shell", "input", "tap", str(tap_x), str(tap_y)], capture_output=True, text=True)
                await asyncio.sleep(0.25)
            await asyncio.sleep(max(0.05, float(detect_interval)))
    except asyncio.CancelledError:
        # 正常取消
        return
    except Exception:
        return


def is_full_screen(device_id: Optional[str] = None) -> bool:
    """简单基于 dumpsys activity top 的启发式判断：
    - mCurrentConfig 字段包含 "port" → 视为“全屏”
    - 包含 "land" → 视为“非全屏/横屏界面”
    注意：这是一个启发式方法，仅供将来区分使用，当前保活策略与此无关。
    """
    try:
        out = subprocess.run(
            _adb_prefix(device_id) + ["shell", "dumpsys", "activity", "top"], capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0 and out.stdout:
            s = out.stdout.lower()
            if "mcurrentconfig" in s:
                if " port " in (" " + s + " "):
                    return True
                if " land " in (" " + s + " "):
                    return False
    except Exception:
        pass
    # 默认返回 True（不影响保活点击坐标）
    return True


async def start_keep_play_controls(duration_s: float, detect_interval: float = 0.1, exist_field_keyword: str = "Brightness", device_id: Optional[str] = None) -> None:
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
        _keeper_task = loop.create_task(_keep_worker(duration_s, detect_interval, exist_field_keyword, device_id))


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
                                            device_id: Optional[str] = None) -> None:
    return await start_keep_play_controls(duration_s=duration_s,
                                          detect_interval=detect_interval,
                                          exist_field_keyword=exist_filed_keyword,
                                          device_id=device_id)

