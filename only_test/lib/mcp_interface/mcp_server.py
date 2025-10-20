#!/usr/bin/env python3
"""
Only-Test MCP Server
====================

为LLM提供实时设备控制能力的MCP服务器
让AI能够像人类测试工程师一样操作设备
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """MCP工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable
    category: str = "general"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "category": self.category
        }


@dataclass
class MCPResponse:
    """MCP响应格式"""
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    tool_name: str = ""
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MCPServer:
    """
    Only-Test MCP服务器
    
    功能特性：
    1. 工具注册和管理
    2. LLM请求处理
    3. 设备状态缓存
    4. 执行历史记录
    5. 错误处理和恢复
    """
    
    def __init__(self, device_id: Optional[str] = None):
        """初始化MCP服务器"""
        self.device_id = device_id
        self.tools: Dict[str, MCPTool] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.device_cache: Dict[str, Any] = {}
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info(f"MCP服务器初始化 - 会话ID: {self.session_id}")
    
    def register_tool(self, tool: MCPTool) -> None:
        """注册MCP工具"""
        self.tools[tool.name] = tool
        logger.info(f"注册工具: {tool.name} - {tool.description}")
    
    def register_tools(self, tools: List[MCPTool]) -> None:
        """批量注册工具"""
        for tool in tools:
            self.register_tool(tool)
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> MCPResponse:
        """
        执行MCP工具
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            MCPResponse: 执行结果
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            if tool_name not in self.tools:
                return MCPResponse(
                    success=False,
                    result=None,
                    error=f"工具 '{tool_name}' 不存在",
                    tool_name=tool_name,
                    timestamp=datetime.now().isoformat()
                )
            
            tool = self.tools[tool_name]
            
            # 执行工具函数
            if asyncio.iscoroutinefunction(tool.function):
                result = await tool.function(**parameters)
            else:
                result = tool.function(**parameters)

            execution_time = asyncio.get_event_loop().time() - start_time

            # 若工具返回字典且包含 success=False，则将本次执行判定为失败
            derived_success = True
            derived_error: Optional[str] = None
            try:
                if isinstance(result, dict) and ("success" in result):
                    if not bool(result.get("success")):
                        derived_success = False
                        derived_error = str(result.get("error") or f"{tool_name} 执行返回失败")
            except Exception:
                pass

            response = MCPResponse(
                success=derived_success,
                result=result,
                error=derived_error,
                execution_time=execution_time,
                tool_name=tool_name,
                timestamp=datetime.now().isoformat()
            )
            
            # 记录执行历史
            self._record_execution(tool_name, parameters, response)
            
            if response.success:
                logger.info(f"工具执行成功: {tool_name} ({execution_time:.2f}s)")
            else:
                logger.error(f"工具执行失败: {tool_name} - {response.error or 'unknown error'}")
            return response
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            
            response = MCPResponse(
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time,
                tool_name=tool_name,
                timestamp=datetime.now().isoformat()
            )
            
            self._record_execution(tool_name, parameters, response)
            
            logger.error(f"工具执行失败: {tool_name} - {e}")
            return response
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return [tool.to_dict() for tool in self.tools.values()]
    
    async def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """按类别获取工具"""
        return [
            tool.to_dict() for tool in self.tools.values() 
            if tool.category == category
        ]
    
    def get_execution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self.execution_history[-limit:]
    
    def get_device_cache(self) -> Dict[str, Any]:
        """获取设备缓存信息"""
        return self.device_cache.copy()
    
    def update_device_cache(self, key: str, value: Any) -> None:
        """更新设备缓存"""
        self.device_cache[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.device_cache.clear()
        logger.info("设备缓存已清空")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计"""
        total_executions = len(self.execution_history)
        successful_executions = sum(
            1 for exec_record in self.execution_history 
            if exec_record["response"]["success"]
        )
        
        success_rate = (successful_executions / total_executions) if total_executions > 0 else 0
        
        tool_usage = {}
        for exec_record in self.execution_history:
            tool_name = exec_record["tool_name"]
            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
        
        return {
            "session_id": self.session_id,
            "device_id": self.device_id,
            "total_tools": len(self.tools),
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": success_rate,
            "tool_usage": tool_usage,
            "cache_entries": len(self.device_cache),
            "session_start": self.session_id,
            "last_activity": self.execution_history[-1]["timestamp"] if self.execution_history else None
        }
    
    # === LLM交互接口 ===
    
    async def process_llm_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理LLM请求
        
        Args:
            request: LLM请求，格式：
            {
                "action": "execute_tool" | "list_tools" | "get_device_info" | "get_history",
                "tool_name": "工具名称",
                "parameters": {"参数": "值"}
            }
            
        Returns:
            Dict: 响应结果
        """
        action = request.get("action", "")
        
        if action == "execute_tool":
            tool_name = request.get("tool_name", "")
            parameters = request.get("parameters", {})
            response = await self.execute_tool(tool_name, parameters)
            return response.to_dict()
        
        elif action == "list_tools":
            category = request.get("category")
            if category:
                tools = await self.get_tools_by_category(category)
            else:
                tools = await self.get_available_tools()
            return {"success": True, "result": tools}
        
        elif action == "get_device_info":
            return {"success": True, "result": self.get_device_cache()}
        
        elif action == "get_history":
            limit = request.get("limit", 10)
            history = self.get_execution_history(limit)
            return {"success": True, "result": history}
        
        elif action == "get_stats":
            stats = self.get_session_stats()
            return {"success": True, "result": stats}
        
        else:
            return {
                "success": False, 
                "error": f"不支持的操作: {action}"
            }
    
    # === 私有方法 ===
    
    def _record_execution(self, tool_name: str, parameters: Dict[str, Any], response: MCPResponse) -> None:
        """记录工具执行历史"""
        record = {
            "tool_name": tool_name,
            "parameters": parameters,
            "response": response.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        self.execution_history.append(record)
        
        # 保持历史记录在合理范围内
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-500:]


# === 工具装饰器 ===

def mcp_tool(name: str, description: str, category: str = "general", parameters: Dict[str, Any] = None):
    """
    MCP工具装饰器
    
    使用方法:
    @mcp_tool("tool_name", "工具描述", "category", {"param": {"type": "string"}})
    async def my_tool(param: str):
        return "result"
    """
    def decorator(func):
        func._mcp_tool_info = {
            "name": name,
            "description": description,
            "category": category,
            "parameters": parameters or {}
        }
        return func
    return decorator
