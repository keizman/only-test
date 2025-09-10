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

    def take_screenshot(self, save_path: Optional[str] = None) -> str:
        if save_path is None:
            save_path = str(Path("/tmp") / f"screenshot_{self.device_id or 'default'}.png")
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        # 通过 exec-out screencap -p 抓 PNG 字节
        proc = subprocess.run(self._adb_cmd(["exec-out", "screencap", "-p"]), capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(f"ADB screencap failed: {proc.stderr}")
        Path(save_path).write_bytes(proc.stdout)
        return save_path

    def get_screenshot_base64(self) -> str:
        proc = subprocess.run(self._adb_cmd(["exec-out", "screencap", "-p"]), capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(f"ADB screencap failed: {proc.stderr}")
        return base64.b64encode(proc.stdout).decode("utf-8")

    def is_media_playing(self) -> bool:
        # 可结合 dumpsys 判断；此处保持简单实现
        return False

    def get_current_activity(self) -> str:
        return ""

    def detect_ui_mode(self) -> str:
        info = self.get_screen_info()
        return 'landscape' if info.orientation == 'landscape' else 'normal'

