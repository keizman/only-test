#!/usr/bin/env python3
"""
Unified App Launcher
====================

面向所有调用方提供统一的启动应用能力：
- 若 main.yaml 中配置了 ui_activity，则使用 `adb shell am start -S -W -n pkg/ui_activity`
- 否则回退到 launcher 方式（monkey 最小事件）或简单 am start

可作为库函数调用，也可通过命令行运行便测。
"""

import subprocess
from typing import Optional, Dict, Any

from .yaml_monitor import YamlMonitor


def _adb_prefix(device_id: Optional[str]) -> list:
    base = ["adb"]
    if device_id:
        base += ["-s", device_id]
    return base


def start_app(
    application: str,
    device_id: Optional[str] = None,
    force_restart: bool = True,
) -> Dict[str, Any]:
    """启动应用（同步，快速返回）。

    Args:
        application: app_id 或 package_name
        device_id: ADB 设备ID（可选）
        force_restart: 是否强制重启（-S）

    Returns:
        Dict: 执行结果（包含命令、返回码、stdout/ stderr）
    """
    ym = YamlMonitor()
    pkg = ym.get_package_name(application) or application
    act = ym.get_ui_activity(application)

    if not pkg:
        return {"success": False, "error": f"无法解析应用: {application}"}

    # 优先 ui_activity
    if act:
        cmd = _adb_prefix(device_id) + [
            "shell", "am", "start",
            "-W",
        ]
        if force_restart:
            cmd.append("-S")
        cmd += ["-n", f"{pkg}/{act}"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return {
            "success": proc.returncode == 0,
            "used": "am_start_activity",
            "command": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    # 回退：使用 launcher（monkey 最小事件）
    cmd = _adb_prefix(device_id) + [
        "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "success": proc.returncode == 0,
        "used": "monkey_launcher",
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser(description="Unified app launcher")
    parser.add_argument("application", help="app_id 或 package_name")
    parser.add_argument("--device-id", default=None)
    parser.add_argument("--no-force-restart", action="store_true")
    args = parser.parse_args()

    result = start_app(
        application=args.application,
        device_id=args.device_id,
        force_restart=not args.no_force_restart,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

