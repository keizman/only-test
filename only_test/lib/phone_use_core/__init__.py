"""
Phone-Use 核心功能集成模块

从 phone-use 项目提取的核心功能，用于 Only-Test 框架
包含屏幕信息获取、设备控制、元素识别等功能
"""

from .screen_capture import ScreenCapture

__all__ = [
    'ScreenCapture'
]

__version__ = '1.0.0'