#!/usr/bin/env python3
"""
Only-Test MCP Tool Registry
===========================

工具注册和管理系统
自动发现和注册MCP工具，提供统一的工具管理接口
"""

import asyncio
import inspect
import logging
from typing import Dict, List, Any, Callable, Optional, Type
from dataclasses import dataclass
from functools import wraps

from .mcp_server import MCPTool, MCPServer

logger = logging.getLogger(__name__)


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "description": self.description
        }
        if not self.required:
            result["required"] = False
        if self.default is not None:
            result["default"] = self.default
        if self.enum:
            result["enum"] = self.enum
        return result


class ToolRegistry:
    """
    MCP工具注册器
    
    功能特性：
    1. 自动工具发现和注册
    2. 参数类型验证
    3. 工具分类管理
    4. 权限控制
    5. 工具依赖管理
    """
    
    def __init__(self, server: Optional[MCPServer] = None):
        """初始化工具注册器"""
        self.server = server
        self.registered_tools: Dict[str, MCPTool] = {}
        self.tool_categories: Dict[str, List[str]] = {}
        self.tool_dependencies: Dict[str, List[str]] = {}
        
        logger.info("工具注册器初始化完成")
    
    def register_tool_class(self, tool_class: Type) -> None:
        """
        注册工具类
        
        Args:
            tool_class: 包含MCP工具方法的类
        """
        instance = tool_class()
        
        # 扫描类中的MCP工具方法
        for method_name in dir(instance):
            method = getattr(instance, method_name)
            
            if hasattr(method, '_mcp_tool_info'):
                tool_info = method._mcp_tool_info
                
                # 创建MCP工具
                mcp_tool = MCPTool(
                    name=tool_info['name'],
                    description=tool_info['description'],
                    parameters=tool_info['parameters'],
                    function=method,
                    category=tool_info.get('category', 'general')
                )
                
                self.register_tool(mcp_tool)
                logger.info(f"从类 {tool_class.__name__} 注册工具: {tool_info['name']}")
    
    def register_tool(self, tool: MCPTool) -> None:
        """注册单个工具"""
        self.registered_tools[tool.name] = tool
        
        # 更新分类索引
        if tool.category not in self.tool_categories:
            self.tool_categories[tool.category] = []
        self.tool_categories[tool.category].append(tool.name)
        
        # 如果有服务器实例，同时注册到服务器
        if self.server:
            self.server.register_tool(tool)
        
        logger.info(f"工具注册成功: {tool.name} [{tool.category}]")
    
    def register_tools_from_modules(self, modules: List[Any]) -> None:
        """从模块批量注册工具"""
        for module in modules:
            self._scan_module_for_tools(module)
    
    def _scan_module_for_tools(self, module: Any) -> None:
        """扫描模块中的MCP工具"""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # 检查是否是工具类
            if inspect.isclass(attr) and hasattr(attr, '_mcp_tool_class'):
                self.register_tool_class(attr)
            
            # 检查是否是工具函数
            elif callable(attr) and hasattr(attr, '_mcp_tool_info'):
                tool_info = attr._mcp_tool_info
                
                mcp_tool = MCPTool(
                    name=tool_info['name'],
                    description=tool_info['description'],
                    parameters=tool_info['parameters'],
                    function=attr,
                    category=tool_info.get('category', 'general')
                )
                
                self.register_tool(mcp_tool)
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """获取指定工具"""
        return self.registered_tools.get(name)
    
    def get_tools_by_category(self, category: str) -> List[MCPTool]:
        """获取指定分类的工具"""
        tool_names = self.tool_categories.get(category, [])
        return [self.registered_tools[name] for name in tool_names]
    
    def get_all_tools(self) -> List[MCPTool]:
        """获取所有注册的工具"""
        return list(self.registered_tools.values())
    
    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具注册信息"""
        return {
            "total_tools": len(self.registered_tools),
            "categories": {
                category: len(tools) 
                for category, tools in self.tool_categories.items()
            },
            "tool_list": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category,
                    "parameters": tool.parameters
                }
                for tool in self.registered_tools.values()
            ]
        }
    
    def validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证工具参数"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"工具 '{tool_name}' 不存在")
        
        # TODO: 实现详细的参数验证逻辑
        # 包括类型检查、必需参数检查、枚举值检查等
        
        return parameters
    
    def set_tool_dependency(self, tool_name: str, dependencies: List[str]) -> None:
        """设置工具依赖关系"""
        self.tool_dependencies[tool_name] = dependencies
    
    def get_tool_dependencies(self, tool_name: str) -> List[str]:
        """获取工具依赖"""
        return self.tool_dependencies.get(tool_name, [])


# === 工具装饰器 ===

def tool(name: str, description: str, category: str = "general", **kwargs):
    """
    MCP工具装饰器
    
    Args:
        name: 工具名称
        description: 工具描述
        category: 工具分类
        **kwargs: 其他工具配置
    
    使用示例:
    @tool("get_device_info", "获取设备信息", "device")
    async def get_device_info():
        return {"device": "info"}
    """
    def decorator(func):
        # 自动从函数签名生成参数定义
        sig = inspect.signature(func)
        parameters = {}
        
        for param_name, param in sig.parameters.items():
            param_type = "string"  # 默认类型
            
            # 根据类型注解推断参数类型
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"
                elif param.annotation == dict:
                    param_type = "object"
            
            parameters[param_name] = {
                "type": param_type,
                "description": f"参数 {param_name}",
                "required": param.default == inspect.Parameter.empty
            }
        
        func._mcp_tool_info = {
            "name": name,
            "description": description,
            "category": category,
            "parameters": parameters,
            **kwargs
        }
        
        return func
    
    return decorator


def tool_class(category: str = "general"):
    """
    MCP工具类装饰器
    
    Args:
        category: 工具类分类
    
    使用示例:
    @tool_class("device")
    class DeviceTools:
        @tool("get_info", "获取设备信息")
        async def get_info(self):
            return {"device": "info"}
    """
    def decorator(cls):
        cls._mcp_tool_class = True
        cls._tool_category = category
        return cls
    
    return decorator


# === 预定义参数类型 ===

class ParameterTypes:
    """常用参数类型定义"""
    
    STRING = {"type": "string", "description": "字符串参数"}
    INTEGER = {"type": "integer", "description": "整数参数"}
    NUMBER = {"type": "number", "description": "数字参数"}
    BOOLEAN = {"type": "boolean", "description": "布尔参数"}
    ARRAY = {"type": "array", "description": "数组参数"}
    OBJECT = {"type": "object", "description": "对象参数"}
    
    @staticmethod
    def enum(values: List[Any], description: str = "枚举参数") -> Dict[str, Any]:
        """创建枚举参数"""
        return {
            "type": "string",
            "description": description,
            "enum": values
        }
    
    @staticmethod
    def optional(param_type: Dict[str, Any], default: Any = None) -> Dict[str, Any]:
        """创建可选参数"""
        result = param_type.copy()
        result["required"] = False
        if default is not None:
            result["default"] = default
        return result


# === 工具注册助手函数 ===

def create_registry(server: Optional[MCPServer] = None) -> ToolRegistry:
    """创建工具注册器实例"""
    return ToolRegistry(server)


def auto_register_tools(registry: ToolRegistry, modules: List[Any]) -> None:
    """自动注册模块中的所有工具"""
    registry.register_tools_from_modules(modules)
    logger.info(f"自动注册完成，共注册 {len(registry.get_all_tools())} 个工具")