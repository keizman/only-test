"""
统一屏幕截图与屏幕信息获取的抽象（ScreenCapture）。

实现策略：默认通过 ADB 与指定 device_id 通信；
对上层仅暴露统一接口，便于未来替换为更高效实现。
"""

import base64
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os
import time

# 尝试导入日志记录器（可选）
try:
    from only_test.lib.android_interaction_logger import log_adb_interaction
except ImportError:
    def log_adb_interaction(command: str, **kwargs):
        pass


@dataclass
class ScreenInfo:
    width: int
    height: int
    density: float
    orientation: str
    screenshot_path: Optional[str] = None
    screenshot_base64: Optional[str] = None


class ScreenCapture:
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id

    def _adb_cmd(self, args: list[str]) -> list[str]:
        prefix = ["adb"]
        if self.device_id:
            prefix += ["-s", self.device_id]
        return prefix + args

    def get_screen_info(self) -> ScreenInfo:
        width, height = 1080, 1920
        density = 440.0
        try:
            # 解析分辨率
            out = subprocess.run(self._adb_cmd(["shell", "wm", "size"]), capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and "Physical size:" in out.stdout:
                sz = out.stdout.split("Physical size:")[-1].strip().split("\n")[0].strip()
                if "x" in sz:
                    parts = sz.split("x")
                    width = int(parts[0].strip())
                    height = int(parts[1].strip())
            # 解析密度
            out = subprocess.run(self._adb_cmd(["shell", "wm", "density"]), capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and "Physical density:" in out.stdout:
                dn = out.stdout.split("Physical density:")[-1].strip().split("\n")[0].strip()
                density = float(dn)
        except Exception:
            pass
        orientation = "landscape" if width > height else "portrait"
        return ScreenInfo(width=width, height=height, density=density, orientation=orientation)

    def ensure_screen_awake_and_unlocked(self, max_wait: float = 3.0) -> None:
        """Best-effort to wake the device to avoid black screenshots.
        
        逻辑:
        1. 检查设备类型（手机 vs 其他）
        2. 检查屏幕状态（Awake vs Asleep）
        3. 如果息屏，使用 keyevent 26 唤醒
        """
        try:
            # 1. 检查是否是手机设备
            cmd_getprop = self._adb_cmd(["shell", "getprop", "ro.product.device"])
            result = subprocess.run(cmd_getprop, capture_output=True, text=True, timeout=2)
            device_type = result.stdout.strip().lower() if result.returncode == 0 else ""
            
            # 如果明确不是手机设备（如 TV、tablet），直接退出
            if device_type and any(x in device_type for x in ['tv', 'tablet', 'box']):
                log_adb_interaction("check_device_type", result=device_type, skipped=True, reason="not_phone")
                return
            
            # 2. 检查屏幕状态
            cmd_power = self._adb_cmd(["shell", "dumpsys", "power"])
            result = subprocess.run(cmd_power, capture_output=True, text=True, timeout=2)
            wakefulness = "Unknown"
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'mWakefulness=' in line:
                        wakefulness = line.split('mWakefulness=')[-1].strip()
                        break
            
            log_adb_interaction("check_wakefulness", result=wakefulness)
            
            # 3. 如果息屏，唤醒
            if wakefulness == "Asleep":
                cmd_wake = self._adb_cmd(["shell", "input", "keyevent", "26"])
                result = subprocess.run(cmd_wake, capture_output=True, timeout=2)
                log_adb_interaction("keyevent_wake", keyevent="26", success=result.returncode == 0)
                time.sleep(min(max_wait, 0.5))
            else:
                log_adb_interaction("keyevent_wake", skipped=True, reason=f"already_{wakefulness.lower()}")
                
        except Exception as e:
            log_adb_interaction("ensure_screen_awake", error=str(e))

    def _capture_png_bytes(self) -> bytes:
        """Robustly capture a PNG screenshot from the device.

        Strategy:
        1) Prefer `adb exec-out screencap -p` (binary-safe)
        2) If header invalid/empty, fall back to `adb shell screencap -p` and fix CRLF
        """
        # Ensure screen is on and unlocked before capture
        self.ensure_screen_awake_and_unlocked()

        # Primary method: exec-out
        proc = subprocess.run(self._adb_cmd(["exec-out", "screencap", "-p"]), capture_output=True)
        data = proc.stdout if proc.returncode == 0 else b""

        def _looks_like_png(b: bytes) -> bool:
            return len(b) > 8 and b[:8] == b"\x89PNG\r\n\x1a\n"

        if _looks_like_png(data):
            return data

        # Fallback: shell mode may introduce CRLF; normalize
        proc2 = subprocess.run(self._adb_cmd(["shell", "screencap", "-p"]), capture_output=True)
        if proc2.returncode != 0:
            # Return the original even if invalid to surface an error upstream
            return data
        # Normalize potential CRLF line endings in PNG stream
        fixed = proc2.stdout.replace(b"\r\r\n", b"\n").replace(b"\r\n", b"\n")
        return fixed

    def take_screenshot(self, save_path: Optional[str] = None) -> str:
        # 使用跨平台临时目录
        if save_path is None:
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            save_path = str(temp_dir / f"screenshot_{self.device_id or 'default'}.png")
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        data = self._capture_png_bytes()
        if not data:
            raise RuntimeError("ADB screencap returned empty data")
        Path(save_path).write_bytes(data)
        return save_path

    def get_screenshot_base64(self) -> str:
        data = self._capture_png_bytes()
        if not data:
            raise RuntimeError("ADB screencap returned empty data")
        return base64.b64encode(data).decode("utf-8")

    def is_media_playing(self) -> bool:
        # 可结合 dumpsys 判断；此处保持简单实现
        return False

    def get_current_activity(self) -> str:
        return ""

    def detect_ui_mode(self) -> str:
        info = self.get_screen_info()
        return 'landscape' if info.orientation == 'landscape' else 'normal'
