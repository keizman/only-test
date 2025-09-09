"""
Only-Test MCP (Model Context Protocol) Interface
===============================================

为LLM提供实时设备控制和信息获取能力
让AI能够像人类测试工程师一样探测设备、分析界面、生成用例

核心功能：
- 实时设备信息获取
- 元素识别和分析  
- 用例执行和反馈
- 错误分析和修复建议
"""

from .mcp_server import MCPServer
from .tool_registry import ToolRegistry, tool
from .device_inspector import DeviceInspector
from .case_generator import InteractiveCaseGenerator
from .feedback_loop import FeedbackLoop
from .workflow_orchestrator import WorkflowOrchestrator

__version__ = "1.0.0"
__author__ = "Only-Test Team"

# 导出主要接口
__all__ = [
    "MCPServer",
    "ToolRegistry", 
    "tool",
    "DeviceInspector",
    "InteractiveCaseGenerator",
    "FeedbackLoop",
    "WorkflowOrchestrator"
]