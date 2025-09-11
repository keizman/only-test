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

# 为避免 `python -m only_test.lib.mcp_interface.device_inspector` 运行时的重复导入警告，
# 不在此处直接导入子模块，而是通过 __getattr__ 延迟加载。

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

def __getattr__(name):  # PEP 562
    if name == "DeviceInspector":
        from .device_inspector import DeviceInspector
        return DeviceInspector
    if name in ("MCPServer",):
        from .mcp_server import MCPServer
        return MCPServer
    if name in ("ToolRegistry", "tool"):
        from .tool_registry import ToolRegistry, tool
        return {"ToolRegistry": ToolRegistry, "tool": tool}[name]
    if name == "InteractiveCaseGenerator":
        from .case_generator import InteractiveCaseGenerator
        return InteractiveCaseGenerator
    if name == "FeedbackLoop":
        from .feedback_loop import FeedbackLoop
        return FeedbackLoop
    if name == "WorkflowOrchestrator":
        from .workflow_orchestrator import WorkflowOrchestrator
        return WorkflowOrchestrator
    raise AttributeError(name)
