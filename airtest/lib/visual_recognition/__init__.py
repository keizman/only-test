"""
Only-Test 视觉识别模块
==============================

提供智能的元素识别和交互能力，支持：
- XML模式：基于UIAutomator2的快速元素定位
- 视觉模式：基于Omniparser的视觉识别
- 智能Fallback：根据播放状态和界面复杂度动态切换
- 统一接口：对外提供透明的元素识别服务

核心组件：
- ElementRecognizer: 统一元素识别接口
- StrategyManager: 策略选择和切换管理器  
- OmniparserClient: 视觉识别客户端
- PlaybackDetector: 播放状态检测器
"""

from .element_recognizer import ElementRecognizer
from .strategy_manager import StrategyManager, RecognitionStrategy
from .omniparser_client import OmniparserClient
from .playback_detector import PlaybackDetector

__version__ = "1.0.0"
__author__ = "Only-Test Team"

# 导出主要接口
__all__ = [
    "ElementRecognizer",
    "StrategyManager", 
    "RecognitionStrategy",
    "OmniparserClient",
    "PlaybackDetector"
]

# 默认配置
DEFAULT_CONFIG = {
    "omniparser_server": "http://100.122.57.128:9333",
    "strategy_fallback_enabled": True,
    "playback_detection_enabled": True,
    "cache_enabled": True,
    "debug_mode": False
}