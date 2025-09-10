"""
保留旧路径以兼容历史导入；实际从 only_test.lib.screen_capture 导入。
"""

from ..screen_capture import ScreenCapture, ScreenInfo

__all__ = ["ScreenCapture", "ScreenInfo"]
