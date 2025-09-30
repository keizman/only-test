#!/usr/bin/env python3
"""
Only-Test Framework
===================

智能化移动应用自动化测试框架，基于 Airtest 进行二次开发
专注于 Android 应用的 UI 自动化测试，集成 LLM，使用 XML（UIAutomator2）进行元素识别

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
    # NOTE: Avoid importing mcp_interface symbols eagerly to prevent pre-importing
    # submodules (e.g., device_inspector) before `-m only_test.lib.mcp_interface.device_inspector` runs.
    # They are exposed lazily via __getattr__ below.
    from .lib.test_generator import TestGenerator
    from .lib.code_generator.python_code_generator import PythonCodeGenerator
except ImportError as e:
    # 某些模块可能需要额外的依赖，允许部分导入失败
    import warnings
    warnings.warn(f"某些Only-Test模块导入失败: {e}", ImportWarning)

__all__ = [
    "UIAutomationScheduler",
    "EnhancedUIAutomator2Extractor",
    "WorkflowOrchestrator",
    "MCPServer",
    "TestGenerator",
    "PythonCodeGenerator"
]

# Lazy attribute access to avoid importing heavy submodules at package import time.
def __getattr__(name):  # PEP 562 lazy export
    if name in ("WorkflowOrchestrator", "MCPServer"):
        from .lib.mcp_interface import WorkflowOrchestrator, MCPServer
        return {"WorkflowOrchestrator": WorkflowOrchestrator, "MCPServer": MCPServer}[name]
    raise AttributeError(name)
