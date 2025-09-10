#!/usr/bin/env python3
"""
Only-Test Framework
===================

智能化移动应用自动化测试框架，基于Airtest进行二次开发
专注于Android应用的UI自动化测试，集成LLM和视觉识别能力

主要功能：
- 基于XML的UI元素识别
- 视觉识别和OCR文本识别
- LLM驱动的智能测试用例生成
- MCP协议支持的设备检查工具
- 智能重试和错误恢复机制
"""

__version__ = "1.0.0"
__author__ = "Only-Test Team"
__email__ = "support@only-test.com"

# 导出主要模块
try:
    from .lib.pure_uiautomator2_extractor import UIAutomationScheduler, EnhancedUIAutomator2Extractor
    from .lib.visual_recognition.element_recognizer import ElementRecognizer
    from .lib.mcp_interface import WorkflowOrchestrator, MCPServer
    from .lib.test_generator import TestGenerator
    from .lib.json_to_python import PythonCodeGenerator
except ImportError as e:
    # 某些模块可能需要额外的依赖，允许部分导入失败
    import warnings
    warnings.warn(f"某些Only-Test模块导入失败: {e}", ImportWarning)

__all__ = [
    "UIAutomationScheduler",
    "EnhancedUIAutomator2Extractor", 
    "ElementRecognizer",
    "WorkflowOrchestrator",
    "MCPServer",
    "TestGenerator",
    "PythonCodeGenerator"
]