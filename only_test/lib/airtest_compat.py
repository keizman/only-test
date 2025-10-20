#!/usr/bin/env python3
"""
Airtest Compatibility Layer
===========================

对外提供与 `airtest.core.api` 等价的导入接口，但重写 `start_app`，
统一走 only_test 的应用启动策略（优先 main.yaml.ui_activity，回退 launcher/monkey）。
"""

from typing import Optional, Any

# 原生 airtest API 全量导入（其余函数保持原样使用）
from airtest.core.api import *  # noqa: F401,F403
from airtest.core import api as _air_api

# 统一启动模块
try:
    from .app_launcher import start_app as _unified_start_app
except Exception:  # 允许从仓库根目录直接运行
    from only_test.lib.app_launcher import start_app as _unified_start_app  # type: ignore

try:
    # 获取当前设备（用于解析 adb 序列号）
    from airtest.core.api import device as _current_device
except Exception:  # pragma: no cover
    _current_device = None  # type: ignore

# 可选：录制Hook（与 ONLY_TEST_RECORD 配合使用）
try:
    from only_test.lib.recorder import start_recording as _rec_start, install_airtest_hooks as _rec_install_air
    import os as _os
    if str(_os.getenv("ONLY_TEST_RECORD", "")).strip() in ("1", "true", "True"):
        # 初始化录制器 + 安装Airtest钩子（幂等）
        _rec_start(device_id=_os.getenv("ONLY_TEST_DEVICE_ID") or None)
        _rec_install_air()
except Exception:
    pass


def _get_current_serial() -> Optional[str]:
    try:
        if not _current_device:
            return None
        dev = _current_device()
        adb = getattr(dev, 'adb', None)
        if not adb:
            return None
        # 常见属性名尝试
        for attr in ('serial', 'device_serial', 'adb_serial'):
            val = getattr(adb, attr, None)
            if isinstance(val, str) and val:
                return val
            if callable(val):
                try:
                    s = val()
                    if isinstance(s, str) and s:
                        return s
                except Exception:
                    pass
        return None
    except Exception:
        return None


def start_app(package: str, *args: Any, **kwargs: Any):  # type: ignore[override]
    """替换 airtest 的 start_app，统一调用 only_test 的启动逻辑。

    兼容签名：忽略多余参数（如 activity），但会尽力使用。
    - 优先 main.yaml.ui_activity 启动
    - 否则回退 launcher（monkey 1）
    - 失败时回退原生 airtest 的 start_app 避免中断
    """
    device_id = _get_current_serial()
    try:
        # 允许传入 app_id 或 package 名称
        result = _unified_start_app(application=package, device_id=device_id, force_restart=True)
        # 可根据需要添加等待逻辑或校验
        return result
    except Exception:
        # 兜底：回退到原生 airtest 行为，避免破坏既有用例
        return _air_api.start_app(package, *args, **kwargs)
