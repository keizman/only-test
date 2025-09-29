#!/usr/bin/env python3
"""
Poco工具函数 - 统一管理本地Poco库的导入
使用与example_airtest_record.py相同的导入方式，优先使用真正的poco.click()
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Iterable, Awaitable
import time
import asyncio
import threading
import logging

logger = logging.getLogger(__name__)

# 立即设置Poco路径，在模块导入时就执行
def _find_repo_root(start: Path) -> Path:
    p = start.resolve()
    # 尝试向上寻找包含 Poco 目录的根
    for ancestor in [p] + list(p.parents):
        if (ancestor / "Poco").exists():
            return ancestor
    # 回退：再上一层（适配 only_test/lib 相对路径问题）
    if p.parents:
        return p.parents[-1]
    return p


def _init_poco_path():
    """模块导入时立即设置Poco路径（健壮的向上查找方式）"""
    current_file = Path(__file__).resolve()
    repo_root = _find_repo_root(current_file.parent)
    poco_path = (repo_root / "Poco").resolve()

    if poco_path.exists():
        poco_path_str = str(poco_path)
        if poco_path_str not in sys.path:
            sys.path.insert(0, poco_path_str)
            return True
    return False

# 模块导入时立即执行
_init_poco_path()


def setup_local_poco_path():
    """设置本地Poco库路径"""
    # 获取项目根目录 (uni)
    current_file = Path(__file__).resolve()
    repo_root = _find_repo_root(current_file.parent)
    poco_path = (repo_root / "Poco").resolve()
    
    if poco_path.exists():
        poco_path_str = str(poco_path)
        if poco_path_str not in sys.path:
            sys.path.insert(0, poco_path_str)
            print(f"已添加本地Poco路径: {poco_path_str}")
        return True
    else:
        print(f"警告: 本地Poco路径不存在: {poco_path}")
        return False


def get_android_poco(
    use_airtest_input: bool = False,
    screenshot_each_action: bool = False,
    disable_cache: bool = True,
    device_id: Optional[str] = None,
    app_id: Optional[str] = None,
):
    """获取AndroidPoco实例，并在创建成功后注入播放态自动唤起 Hook。"""
    try:
        print("正在初始化Poco...")

        # 路径已在模块导入时设置，直接导入
        from poco.drivers.android.uiautomation2 import AndroidUiautomator2Poco
        print("✓ 成功导入AndroidUiautomator2Poco类")

        # 禁用缓存机制 (解决缓存导致的元素定位问题)
        if disable_cache:
            disable_poco_cache()
            disable_dumper_cache()

        # 应用set_text增强补丁
        patch_poco_set_text()

        # 使用您要求的参数设置: use_airtest_input=False, screenshot_each_action=False
        poco = AndroidUiautomator2Poco(use_airtest_input=use_airtest_input, screenshot_each_action=screenshot_each_action)
        print("✓ 使用本地Poco库成功创建AndroidUiautomator2Poco实例")
        print(f"✓ 设置: use_airtest_input={use_airtest_input}, screenshot_each_action={screenshot_each_action}")

        if disable_cache:
            print("✓ 缓存已禁用 - 每次查询都获取最新UI状态")

        try:
            enable_auto_wake_for_poco(poco, device_id=device_id, app_id=app_id)
        except Exception as exc:  # noqa: BLE001 - logging only
            logger.debug("自动注入播放态Hook失败: %s", exc)

        return poco
        
    except ImportError as import_error:
        print(f"❌ Poco导入失败: {import_error}")
        print("尝试检查本地Poco库结构...")
        
        # 检查Poco文件结构
        poco_root = _find_repo_root(Path(__file__).resolve().parent) / "Poco"
        uiautomation2_file = poco_root / "poco" / "drivers" / "android" / "uiautomation2.py"
        
        if not poco_root.exists():
            print(f"❌ Poco根目录不存在: {poco_root}")
        elif not uiautomation2_file.exists():
            print(f"❌ uiautomation2.py文件不存在: {uiautomation2_file}")
        else:
            print(f"✓ Poco文件结构正常: {uiautomation2_file}")
        
        # 重新抛出ImportError，保持错误类型
        raise
            
    except RuntimeError as device_error:
        # 处理设备连接错误 - 这是用户最常见的问题
        error_msg = str(device_error)
        if "Failed to connect to Android device" in error_msg:
            print(f"❌ Android设备连接失败: {device_error}")
            print("请检查:")
            print("  1. Android设备是否已连接并开启USB调试")
            print("  2. 运行 'adb devices' 确认设备可见")
            print("  3. 设备是否已授权此计算机进行调试")
            raise RuntimeError(f"设备连接失败: {device_error}")
        else:
            print(f"❌ Poco运行时错误: {device_error}")
            raise
            
    except Exception as other_error:
        print(f"❌ 创建Poco实例失败 ({type(other_error).__name__}): {other_error}")
        raise


# === 辅助：带像素偏移的点击 ===
def _get_screen_size_fallback() -> tuple[int, int]:
    """多策略获取屏幕分辨率，返回 (w,h)。"""
    # 1) 优先从 Airtest 设备取
    try:
        from airtest.core.api import device as current_device
        dev = current_device()
        if dev:
            try:
                w, h = dev.get_current_resolution()  # type: ignore[attr-defined]
                if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
                    return w, h
            except Exception:
                info = getattr(dev, 'display_info', {}) or {}
                w = int(info.get('width', 0) or 0)
                h = int(info.get('height', 0) or 0)
                if w > 0 and h > 0:
                    return w, h
    except Exception:
        pass
    # 2) 尝试 poco.get_screen_size()
    try:
        from .poco_utils import get_android_poco  # self import safe
        p = get_android_poco()
        if hasattr(p, 'get_screen_size'):
            w, h = p.get_screen_size()  # type: ignore[attr-defined]
            if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
                return w, h
    except Exception:
        pass
    # 3) ADB wm size
    try:
        import subprocess
        out = subprocess.run(["adb", "shell", "wm", "size"], capture_output=True, text=True)
        if out.returncode == 0 and 'Physical size:' in out.stdout:
            sz = out.stdout.split('Physical size:')[-1].strip().split('\n')[0].strip()
            w, h = sz.split('x')
            return int(w), int(h)
    except Exception:
        pass
    # 4) 回退
    return 1080, 1920


# 原生扩展已加到 Poco/poco/proxy.py: UIObjectProxy.click_with_bias()


def force_refresh_ui_cache(poco_instance):
    """
    强制刷新Poco/UIAutomator2的UI缓存

    Args:
        poco_instance: Poco实例

    Returns:
        bool: 刷新是否成功
    """
    try:
        # 方法1: 尝试刷新dumper缓存（最彻底）
        if hasattr(poco_instance, 'agent') and hasattr(poco_instance.agent, 'hierarchy'):
            if hasattr(poco_instance.agent.hierarchy, 'dumper'):
                if hasattr(poco_instance.agent.hierarchy.dumper, 'invalidate_cache'):
                    poco_instance.agent.hierarchy.dumper.invalidate_cache()
                    print("✓ 已刷新dumper缓存")
                    return True
                elif hasattr(poco_instance.agent.hierarchy.dumper, '_root_node'):
                    # 如果没有invalidate_cache方法，直接清除根节点缓存
                    poco_instance.agent.hierarchy.dumper._root_node = None
                    print("✓ 已清除根节点缓存")
                    return True

        print("⚠ 无法访问dumper缓存，刷新可能不完整")
        return False

    except Exception as e:
        print(f"❌ 缓存刷新失败: {e}")
        return False


# === 自动唤起（播放态）- Poco Monkey Patch 支持 ===
_auto_wake_state: Dict[str, Dict[str, Any]] = {}
_auto_wake_poco_contexts: Dict[int, Dict[str, Any]] = {}
_auto_wake_context_lock = threading.Lock()


def _normalize_device_id(value: Optional[str]) -> str:
    if not value:
        return "default"
    text = str(value).strip()
    return text or "default"


def _extract_serial_from_object(obj: Any, visited: Optional[set[int]] = None) -> Optional[str]:
    if obj is None:
        return None
    if visited is None:
        visited = set()
    obj_id = id(obj)
    if obj_id in visited:
        return None
    visited.add(obj_id)
    attr_names = (
        "serial",
        "serialno",
        "serial_no",
        "serialnumber",
        "device_id",
        "adb_serial",
        "_serial",
        "_serialno",
    )
    for attr in attr_names:
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            if callable(value):
                try:
                    value = value()
                except Exception:
                    continue
            if value:
                return str(value)
    nested_attrs = (
        "adb",
        "adb_device",
        "device",
        "_device",
        "u2",
        "client",
    )
    for attr in nested_attrs:
        if hasattr(obj, attr):
            serial = _extract_serial_from_object(getattr(obj, attr), visited)
            if serial:
                return serial
    return None


def _infer_device_id_from_poco(poco_instance) -> Optional[str]:
    serial = _extract_serial_from_object(poco_instance)
    if serial:
        return serial
    try:
        from airtest.core.api import device as current_device

        dev = current_device()
        if dev:
            serial = _extract_serial_from_object(dev)
            if not serial:
                for candidate in ("uuid", "serialno", "serial", "adb_serial"):
                    value = getattr(dev, candidate, None)
                    if value:
                        serial = str(value)
                        break
            if serial:
                return serial
    except Exception:
        pass
    try:
        from only_test.lib.config_manager import ConfigManager

        cfg = ConfigManager().get_config()
        devices_cfg = cfg.get("devices") or {}
        if len(devices_cfg) == 1:
            first = next(iter(devices_cfg.values()))
            connection = (first or {}).get("connection", {}) or {}
            serial = connection.get("adb_serial")
            if serial:
                return str(serial)
    except Exception:
        pass
    env_serial = os.getenv("ANDROID_SERIAL")
    if env_serial:
        return env_serial
    return None


def _register_poco_context(poco_instance, device_id: Optional[str], app_id: Optional[str]) -> Dict[str, Any]:
    resolved_device_id = _normalize_device_id(device_id or _infer_device_id_from_poco(poco_instance))
    context = {
        "device_id": resolved_device_id,
        "app_id": app_id,
    }
    with _auto_wake_context_lock:
        _auto_wake_poco_contexts[id(poco_instance)] = context
    logger.info(
        "播放态自动唤起: 绑定 Poco 实例 context=%s", context
    )
    entry = _get_state_entry(resolved_device_id)
    with entry["lock"]:
        entry["poco_instance"] = poco_instance
        if app_id:
            entry.setdefault("app_id", app_id)
    return context


def _resolve_poco_context(proxy, default_poco=None) -> Optional[Dict[str, Any]]:
    poco_obj = getattr(proxy, "poco", None)
    if poco_obj is not None:
        ctx = _auto_wake_poco_contexts.get(id(poco_obj))
        if ctx:
            return ctx
    if default_poco is not None:
        ctx = _auto_wake_poco_contexts.get(id(default_poco))
        if ctx:
            return ctx
    return None


def _state_key(device_id: Optional[str]) -> str:
    return device_id or "default"


def _get_state_entry(device_id: Optional[str]) -> Dict[str, Any]:
    entry = _auto_wake_state.setdefault(_state_key(device_id), {})
    if entry.get("lock") is None:
        entry["lock"] = threading.Lock()
    return entry


def _run_async_fn(factory: Callable[[], Awaitable[Any]]) -> Any:
    try:
        return asyncio.run(factory())
    except RuntimeError as exc:
        if "asyncio.run()" in str(exc) and "running event loop" in str(exc):
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(factory())
            finally:
                loop.close()
        raise


def _get_inspector(device_id: Optional[str]):
    from only_test.lib.mcp_interface.device_inspector import DeviceInspector

    entry = _get_state_entry(device_id)
    inspector = entry.get("inspector")
    if inspector:
        return inspector

    inspector = DeviceInspector(device_id=device_id)
    _run_async_fn(lambda: inspector.initialize())
    entry["inspector"] = inspector
    return inspector


def _launch_media_probe(device_id: Optional[str], inspector, entry: Dict[str, Any]) -> None:
    lock = entry.get("lock")
    if lock is None:
        lock = threading.Lock()
        entry["lock"] = lock

    def _runner():
        try:
            result = bool(_run_async_fn(lambda: inspector._is_media_playing()))  # type: ignore[attr-defined]
            logger.info(
                "播放态自动唤起: 后台刷新探针 device=%s playing=%s",
                device_id or "default",
                result,
            )
        except Exception as exc:  # noqa: BLE001 - logging only
            logger.debug("播放状态探测失败: %s", exc)
            result = bool(entry.get("last_playing", False))
        with lock:
            entry["last_playing"] = result
            entry["last_probe_ts"] = time.time()
            entry["probe_running"] = False
        if result:
            _auto_wake_from_probe(device_id, inspector)

    threading.Thread(
        target=_runner,
        name=f"onlytest-playback-probe-{_state_key(device_id)}",
        daemon=True,
    ).start()


def _is_media_playing_cached(device_id: Optional[str], min_interval_s: float) -> bool:
    entry = _get_state_entry(device_id)
    min_interval = max(0.05, float(min_interval_s or 0.0))
    now = time.time()

    need_initial_probe = False
    should_launch = False

    with entry["lock"]:
        last_ts = float(entry.get("last_probe_ts", 0.0))
        last_value = bool(entry.get("last_playing", False))
        probe_running = bool(entry.get("probe_running", False))

        if last_ts <= 0.0:
            if not probe_running:
                entry["probe_running"] = True
                need_initial_probe = True
        elif (now - last_ts) < min_interval:
            logger.debug(
                "播放态自动唤起: 复用缓存 device=%s last_playing=%s age=%.2fs",
                device_id or "default",
                last_value,
                now - last_ts,
            )
            if last_value:
                _auto_wake_from_probe(device_id, None)
            return last_value
        else:
            if not probe_running:
                entry["probe_running"] = True
                should_launch = True

    inspector = None
    if need_initial_probe or should_launch:
        inspector = _get_inspector(device_id)

    if need_initial_probe and inspector is not None:
        try:
            result = bool(_run_async_fn(lambda: inspector._is_media_playing()))  # type: ignore[attr-defined]
            logger.info(
                "播放态自动唤起: 初次探针结果 device=%s playing=%s",
                device_id or "default",
                result,
            )
        except Exception as exc:  # noqa: BLE001 - logging only
            logger.debug("首次播放状态探测失败: %s", exc)
            result = False
        with entry["lock"]:
            entry["last_playing"] = result
            entry["last_probe_ts"] = time.time()
            entry["probe_running"] = False
        if result:
            _auto_wake_from_probe(device_id, inspector)
        return result

    if should_launch and inspector is not None:
        _launch_media_probe(device_id, inspector, entry)

    with entry["lock"]:
        value = bool(entry.get("last_playing", False))
    logger.debug(
        "播放态自动唤起: 返回探针状态 device=%s playing=%s",
        device_id or "default",
        value,
    )
    if value:
        _auto_wake_from_probe(device_id, inspector)
    return value


def _auto_wake_from_probe(device_id: Optional[str], inspector) -> None:
    entry = _get_state_entry(device_id)
    now = time.time()
    with entry["lock"]:
        poco_instance = entry.get("poco_instance")
        app_id_hint = entry.get("app_id")
        last_wake_ts = float(entry.get("last_wake_ts", 0.0))
        last_probe_wake_ts = float(entry.get("last_probe_wake_ts", 0.0))
        last_wake_success = bool(entry.get("last_wake_success", False))

    if poco_instance is None:
        logger.debug("播放态自动唤起: 无 Poco 实例，跳过探针唤起 device=%s", device_id or "default")
        return

    try:
        inspector_obj = inspector or _get_inspector(device_id)
    except Exception as exc:  # noqa: BLE001 - logging only
        logger.debug("播放态自动唤起: 获取探针实例失败: %s", exc)
        return

    config = _resolve_playback_config(inspector_obj, app_id_hint)
    throttle = max(0.5, (config.get("post_tap_sleep_ms", 250) / 1000.0) + 0.5)

    if last_wake_success and (now - last_wake_ts) < throttle:
        logger.info(
            "播放态自动唤起: 最近%.2fs内唤起成功，跳过探针唤起 device=%s",
            now - last_wake_ts,
            device_id or "default",
        )
        return

    if (now - last_probe_wake_ts) < max(0.5, config.get("probe_min_interval_s", 0.5)):
        logger.debug(
            "播放态自动唤起: 探针唤起节流 %.2fs device=%s",
            now - last_probe_wake_ts,
            device_id or "default",
        )
        return

    result = _perform_auto_wake(device_id, inspector_obj, poco_instance, None, config)
    with entry["lock"]:
        entry["last_probe_wake_ts"] = now
        if result:
            entry["last_wake_success"] = bool(result.get("controls_visible"))


def _collect_keywords(values: Iterable[Any]) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = str(value).strip()
        if text and text not in seen:
            keywords.append(text)
            seen.add(text)
    return keywords


def _resolve_playback_config(inspector, app_id: Optional[str]) -> Dict[str, Any]:
    defaults = {
        "ensure_visible_on_playback": True,
        "probe_min_interval_s": 0.5,
        "tap_y_norm": 0.15,
        "post_tap_sleep_ms": 250,
        "wake_keywords": [],
        "app_id": app_id,
    }

    try:
        from only_test.lib.config_manager import ConfigManager

        cfg = ConfigManager().get_config()
    except Exception as exc:  # noqa: BLE001 - logging only
        logger.debug("读取播放自动唤起配置失败: %s", exc)
        return defaults

    global_cfg = (cfg.get("global_config") or {}).get("playback_auto_wake", {}) or {}

    ensure_visible = bool(global_cfg.get("ensure_visible_on_playback", defaults["ensure_visible_on_playback"]))
    try:
        probe_min = float(global_cfg.get("probe_min_interval_s", defaults["probe_min_interval_s"]))
    except Exception:  # noqa: BLE001 - fallback to default
        probe_min = defaults["probe_min_interval_s"]
    try:
        tap_y_norm = float(global_cfg.get("tap_y_norm", defaults["tap_y_norm"]))
    except Exception:
        tap_y_norm = defaults["tap_y_norm"]
    tap_y_norm = min(1.0, max(0.0, tap_y_norm))
    try:
        post_sleep_ms = int(global_cfg.get("post_tap_sleep_ms", defaults["post_tap_sleep_ms"]))
    except Exception:
        post_sleep_ms = defaults["post_tap_sleep_ms"]
    post_sleep_ms = max(0, post_sleep_ms)

    merged_keywords = _collect_keywords(global_cfg.get("wake_keywords", []))

    resolved_app_id = app_id
    app_cfg: Dict[str, Any] = {}
    applications = cfg.get("applications") or {}

    if resolved_app_id and resolved_app_id in applications:
        app_cfg = (applications.get(resolved_app_id) or {}).get("playback_auto_wake", {}) or {}
    else:
        target_pkg = getattr(inspector, "target_app_package", None)
        if target_pkg:
            for candidate_id, candidate_cfg in applications.items():
                pkg = (candidate_cfg or {}).get("package_name")
                if pkg and str(pkg) == str(target_pkg):
                    resolved_app_id = candidate_id
                    app_cfg = (candidate_cfg.get("playback_auto_wake") or {}) if candidate_cfg else {}
                    break

    merged_keywords.extend(_collect_keywords(app_cfg.get("wake_keywords", [])))
    merged_keywords = list(dict.fromkeys(merged_keywords))

    resolved = {
        "ensure_visible_on_playback": ensure_visible,
        "probe_min_interval_s": max(0.05, probe_min),
        "tap_y_norm": tap_y_norm,
        "post_tap_sleep_ms": post_sleep_ms,
        "wake_keywords": merged_keywords,
        "app_id": resolved_app_id,
    }
    logger.debug(
        "播放态自动唤起: 解析配置 app=%s resolved=%s",
        resolved_app_id or "",
        resolved,
    )
    return resolved


def _perform_auto_wake(
    device_id: Optional[str],
    inspector,
    poco_instance,
    target_proxy,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    wake_result: Dict[str, Any] = {}
    try:
        logger.info(
            "播放态自动唤起: 执行唤起动作 device=%s app=%s keywords=%s",
            device_id or "default",
            config.get("app_id") or "",
            config.get("wake_keywords", []),
        )
        wake_result = _run_async_fn(
            lambda: inspector._ensure_controls_visible_once(  # type: ignore[attr-defined]
                config.get("wake_keywords", []),
                tap_y_norm=config.get("tap_y_norm", 0.15),
                post_tap_sleep_ms=config.get("post_tap_sleep_ms", 250),
            )
        )
        if not isinstance(wake_result, dict):
            wake_result = {}
    except Exception as exc:  # noqa: BLE001 - logging only
        logger.debug("播放控件唤起失败: %s", exc)
        wake_result = {}

    if wake_result.get("tap_performed"):
        try:
            force_refresh_ui_cache(poco_instance)
        except Exception as exc:  # noqa: BLE001 - logging only
            logger.debug("刷新Poco缓存失败: %s", exc)
        if target_proxy is not None:
            try:
                exists_fn = getattr(target_proxy, "exists", None)
                if callable(exists_fn):
                    exists_fn()
            except Exception:
                pass

    entry = _get_state_entry(device_id)
    with entry["lock"]:
        entry["last_wake_ts"] = time.time()
        entry["last_wake_success"] = bool(wake_result.get("controls_visible"))

    return wake_result


def _wrap_action_with_auto_wake(
    poco_instance,
    action: Callable,
):
    def wrapper(self, *args, **kwargs):
        try:
            context = _resolve_poco_context(self, default_poco=poco_instance)
            if not context:
                logger.info(
                    "播放态自动唤起: 未找到Poco上下文，跳过唤起 proxy=%s poco=%s",
                    type(self).__name__,
                    type(getattr(self, "poco", None)).__name__ if hasattr(self, "poco") else "<none>",
                )
                return action(self, *args, **kwargs)

            device_id = context.get("device_id")
            app_hint = context.get("app_id")

            logger.info(
                "播放态自动唤起: 拦截操作 name=%s device=%s app_hint=%s",
                getattr(action, "__name__", str(action)),
                device_id,
                app_hint or "",
            )

            inspector = _get_inspector(device_id)
            config = _resolve_playback_config(inspector, app_hint)
            if not config.get("app_id"):
                config["app_id"] = app_hint

            if not config.get("ensure_visible_on_playback", True):
                logger.debug("播放态自动唤起已禁用(ensure_visible_on_playback=false)，直连原操作")
                return action(self, *args, **kwargs)

            try:
                playing = _is_media_playing_cached(device_id, config.get("probe_min_interval_s", 0.5))
            except Exception as exc:  # noqa: BLE001 - logging only
                logger.debug("播放状态缓存检测失败: %s", exc)
                playing = False

            if not playing:
                logger.info(
                    "播放态自动唤起: 探针显示未播放，跳过唤起 device=%s app=%s",
                    device_id,
                    config.get("app_id") or "",
                )
                return action(self, *args, **kwargs)

            keywords = tuple(config.get("wake_keywords", []))
            entry = _get_state_entry(device_id)
            now = time.time()
            throttle_window = max(0.2, (config.get("post_tap_sleep_ms", 250) / 1000.0) + 0.2)

            with entry["lock"]:
                recent_success = bool(entry.get("last_wake_success", False))
                recent_ts = float(entry.get("last_wake_ts", 0.0))

            if recent_success and (now - recent_ts) < throttle_window:
                logger.info(
                    "播放态自动唤起: 前一轮%.2fs内成功，跳过重复点击 device=%s app=%s",
                    now - recent_ts,
                    device_id,
                    config.get("app_id") or "",
                )
                return action(self, *args, **kwargs)

            controls_visible = False
            if keywords:
                try:
                    controls_visible = bool(
                        _run_async_fn(
                            lambda: inspector._has_wake_keywords(  # type: ignore[attr-defined]
                                keywords,
                                max_age=0.3,
                            )
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - logging only
                    logger.debug("检测播放控件可见状态失败: %s", exc)

            if not controls_visible:
                wake_result = _perform_auto_wake(device_id, inspector, poco_instance, self, config)
                logger.info(
                    "播放态自动唤起: 结果 wake_attempted=%s controls_visible=%s",
                    wake_result.get("wake_attempted"),
                    wake_result.get("controls_visible"),
                )
            else:
                logger.info(
                    "播放态自动唤起: 播控已可见，跳过唤起 device=%s app=%s",
                    device_id,
                    config.get("app_id") or "",
                )

        except Exception as exc:  # noqa: BLE001 - logging only
            logger.debug("播放态自动唤起流程异常: %s", exc)

        return action(self, *args, **kwargs)

    return wrapper


def enable_auto_wake_for_poco(
    poco_instance,
    device_id: Optional[str] = None,
    app_id: Optional[str] = None,
) -> bool:
    """启用播放态自动唤起 Hook。"""

    if poco_instance is None:
        logger.debug("未提供 Poco 实例，跳过自动唤起 Hook")
        return False

    context = _register_poco_context(poco_instance, device_id, app_id)
    resolved_device_id = context.get("device_id")
    resolved_app_id = context.get("app_id")

    try:
        _get_inspector(resolved_device_id)
    except Exception as exc:  # noqa: BLE001 - logging only
        logger.debug("初始化 DeviceInspector 失败: %s", exc)

    try:
        from poco.proxy import UIObjectProxy

        originals = getattr(UIObjectProxy, "__auto_wake_originals__", None)
        if originals is None:
            originals = {}
            for attr in ("click", "long_click", "swipe", "set_text"):
                method = getattr(UIObjectProxy, attr, None)
                if callable(method):
                    originals[attr] = method
        UIObjectProxy.__auto_wake_originals__ = originals  # type: ignore[attr-defined]

        for name, original in (originals or {}).items():
            if callable(original):
                setattr(
                    UIObjectProxy,
                    name,
                    _wrap_action_with_auto_wake(poco_instance, original),
                )

        UIObjectProxy.__auto_wake_patched__ = True  # type: ignore[attr-defined]
        UIObjectProxy.__auto_wake_context__ = {  # type: ignore[attr-defined]
            "device_id": resolved_device_id,
            "app_id": resolved_app_id,
        }

        logger.info(
            "播放态自动唤起: Hook 安装完成 device=%s app=%s",
            resolved_device_id,
            resolved_app_id or "",
        )

        print("✓ 已启用播放态自动唤起（Poco Hook）—— 外部用例与 LLM 无需改动")
        return True
    except Exception as exc:  # noqa: BLE001 - keep stdout message
        print(f"❌ 启用自动唤起失败: {exc}")
        logger.debug("启用自动唤起失败详情", exc_info=True)
        return False


def get_text_with_refresh(selector, max_retries=2):
    """
    获取文本时自动处理缓存刷新

    Args:
        selector: Poco选择器
        max_retries: 最大重试次数

    Returns:
        str: 元素文本
    """
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"尝试第{attempt}次刷新...")
                selector.refresh()  # 使用Poco内置刷新

            return selector.get_text()

        except Exception as e:
            if attempt < max_retries:
                print(f"获取文本失败，重试中... ({e})")
                continue
            else:
                raise


# 重写UIObjectProxy的set_text方法，让它返回实际文本
def enhanced_set_text_method(self, text):
    """
    增强版的set_text方法 - 返回实际文本内容

    由于缓存已被禁用，不需要手动刷新缓存

    Args:
        text: 要设置的文本

    Returns:
        str: 实际设置后的文本内容
    """
    # 1. 执行原始的文本设置
    self.setattr('text', text)

    # 2. 由于缓存已被禁用，get_text()会自动获取最新状态
    actual_text = self.get_text()

    # 3. 验证是否输入成功
    if actual_text == text:
        return text
    else:
        print(f"Warning: 输入可能失败: 期望'{text}', 实际'{actual_text}'")
        return f"Warning: 输入可能失败: 期望'{text}', 实际'{actual_text}'"
    


def disable_poco_cache():
    """
    彻底禁用Poco的缓存机制，让每次查询都重新获取UI状态
    """
    try:
        from poco.proxy import UIObjectProxy

        # 1. 重写_do_query方法，强制每次都刷新
        def no_cache_do_query(self, multiple=True, refresh=True):
            """无缓存的查询方法 - 每次都重新获取"""
            # 强制refresh=True，忽略_evaluated状态
            raw = self.poco.agent.hierarchy.select(self.query, multiple)
            if multiple:
                self._nodes = raw
                self._nodes_proxy_is_list = True
            else:
                if isinstance(raw, list):
                    self._nodes = raw[0] if len(raw) > 0 else None
                else:
                    self._nodes = raw
                self._nodes_proxy_is_list = False

            if not self._nodes:
                self.invalidate()
                from poco.exceptions import PocoNoSuchNodeException
                raise PocoNoSuchNodeException(self)

            # 不设置_evaluated=True，让下次查询继续刷新
            self._query_multiple = multiple
            return self._nodes

        # 2. 重写exists方法，每次都刷新
        def no_cache_exists(self):
            """无缓存的exists检查"""
            try:
                self._do_query(multiple=False, refresh=True)
                return True
            except:
                return False

        # 3. 重写get_text方法，每次都刷新
        def no_cache_get_text(self):
            """无缓存的get_text"""
            nodes = self._do_query(multiple=False, refresh=True)
            return self.poco.agent.hierarchy.getAttr(nodes, 'text') or ''

        # 备份原始方法
        if not hasattr(UIObjectProxy, '_original_do_query'):
            UIObjectProxy._original_do_query = UIObjectProxy._do_query
            UIObjectProxy._original_exists = UIObjectProxy.exists
            UIObjectProxy._original_get_text = UIObjectProxy.get_text

        # 替换为无缓存版本
        UIObjectProxy._do_query = no_cache_do_query
        UIObjectProxy.exists = no_cache_exists
        UIObjectProxy.get_text = no_cache_get_text

        print("✓ Poco缓存已完全禁用 (每次查询都重新获取UI状态)")
        return True

    except Exception as e:
        print(f"⚠ 禁用Poco缓存失败: {e}")
        return False


def disable_dumper_cache():
    """
    禁用UIAutomator2Dumper的缓存机制
    """
    try:
        from poco.drivers.android.uiautomation2 import UIAutomator2Dumper

        # 重写getRoot方法，每次都重新获取
        def no_cache_getRoot(self):
            """无缓存的getRoot - 每次都刷新"""
            self._root_node = None  # 强制清除缓存
            self._update_hierarchy()
            return self._root_node

        # 备份原始方法
        if not hasattr(UIAutomator2Dumper, '_original_getRoot'):
            UIAutomator2Dumper._original_getRoot = UIAutomator2Dumper.getRoot

        # 替换为无缓存版本
        UIAutomator2Dumper.getRoot = no_cache_getRoot

        print("✓ UIAutomator2Dumper缓存已禁用 (每次都重新获取UI层次)")
        return True

    except Exception as e:
        print(f"⚠ 禁用Dumper缓存失败: {e}")
        return False


def patch_poco_set_text():
    """
    替换Poco的set_text方法为增强版本
    """
    try:
        from poco.proxy import UIObjectProxy
        # 备份原始方法
        if not hasattr(UIObjectProxy, '_original_set_text'):
            UIObjectProxy._original_set_text = UIObjectProxy.set_text

        # 替换为增强版本
        UIObjectProxy.set_text = enhanced_set_text_method
        # print("✓ Poco set_text方法已增强 (自动刷新缓存并返回实际文本)")
        return True
    except Exception as e:
        print(f"⚠ 增强set_text方法失败: {e}")
        return False


if __name__ == "__main__":
    # 测试导入
    try:
        setup_local_poco_path()
        print("本地Poco库路径设置成功")
        
        # 只测试路径设置，不创建poco实例（需要airtest环境）
        print("路径设置测试通过")
        
    except Exception as e:
        print(f"测试失败: {e}")
