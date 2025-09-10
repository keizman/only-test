#!/usr/bin/env python3
"""
Only-Test Workflow Orchestrator
===============================

完整的AI驱动测试用例生成和执行流程编排器
实现用户设想的端到端工作流程：
1. 生成新用例 → 2. LLM获取设备信息 → 3. LLM筛选信息生成用例 → 4. JSON转Python → 5. 执行并反馈
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from .mcp_server import MCPServer, MCPTool, mcp_tool
from .tool_registry import ToolRegistry
from .device_inspector import DeviceInspector
from .case_generator import InteractiveCaseGenerator
from .feedback_loop import FeedbackLoop

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Only-Test工作流程编排器
    
    核心功能：
    1. 编排完整的测试用例生成流程
    2. 协调LLM与设备交互
    3. 管理执行反馈循环
    4. 跟踪工作流程状态
    5. 提供流程监控和统计
    """
    
    def __init__(self, device_id: Optional[str] = None):
        """初始化工作流程编排器"""
        self.device_id = device_id
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 核心组件
        self.mcp_server = MCPServer(device_id)
        self.tool_registry = ToolRegistry(self.mcp_server)
        self.device_inspector = DeviceInspector(device_id)
        self.case_generator = InteractiveCaseGenerator(device_id)
        self.feedback_loop = FeedbackLoop(device_id)
        
        # 工作流程状态
        self.workflow_history: List[Dict[str, Any]] = []
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_stats = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "average_completion_time": 0.0
        }
        
        # 初始化标记
        self._initialized = False
        
        logger.info(f"工作流程编排器初始化 - 会话ID: {self.session_id}")
    
    async def initialize(self) -> bool:
        """初始化编排器和所有组件"""
        try:
            # 初始化所有组件
            await self.device_inspector.initialize()
            await self.case_generator.initialize()
            await self.feedback_loop.initialize()
            
            # 注册所有MCP工具
            self._register_orchestrator_tools()
            self._register_component_tools()
            
            self._initialized = True
            logger.info("工作流程编排器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"工作流程编排器初始化失败: {e}")
            return False
    
    @mcp_tool(
        name="start_complete_workflow",
        description="启动完整的测试用例生成和执行工作流程",
        category="workflow",
        parameters={
            "test_requirement": {"type": "string", "description": "测试需求描述"},
            "target_app": {"type": "string", "description": "目标应用", "default": "unknown"},
            "workflow_mode": {"type": "string", "description": "工作流程模式", "enum": ["quick", "standard", "comprehensive"], "default": "standard"},
            "max_iterations": {"type": "integer", "description": "最大迭代次数", "default": 3}
        }
    )
    async def start_complete_workflow(
        self, 
        test_requirement: str, 
        target_app: str = "unknown", 
        workflow_mode: str = "standard",
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """启动完整的工作流程"""
        if not self._initialized:
            await self.initialize()
        
        workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.workflow_history)}"
        
        workflow_context = {
            "workflow_id": workflow_id,
            "test_requirement": test_requirement,
            "target_app": target_app,
            "workflow_mode": workflow_mode,
            "max_iterations": max_iterations,
            "current_iteration": 0,
            "status": "started",
            "start_time": datetime.now().isoformat(),
            "phases": []
        }
        
        self.active_workflows[workflow_id] = workflow_context
        
        try:
            logger.info(f"开始工作流程: {workflow_id} - {test_requirement}")
            
            # 阶段1: 设备信息收集
            device_info_result = await self._phase_1_collect_device_info(workflow_context)
            workflow_context["phases"].append(device_info_result)
            
            if not device_info_result["success"]:
                return await self._complete_workflow(workflow_context, "failed", "设备信息收集失败")
            
            # 阶段2: 用例生成（支持迭代）
            for iteration in range(max_iterations):
                workflow_context["current_iteration"] = iteration + 1
                
                # 2a: LLM生成用例
                case_generation_result = await self._phase_2_generate_case(
                    workflow_context, device_info_result["device_info"]
                )
                workflow_context["phases"].append(case_generation_result)
                
                if not case_generation_result["success"]:
                    continue  # 尝试下一次迭代
                
                # 2b: 转换为Python代码
                conversion_result = await self._phase_3_convert_to_python(
                    workflow_context, case_generation_result["test_case"]
                )
                workflow_context["phases"].append(conversion_result)
                
                if not conversion_result["success"]:
                    continue  # 尝试下一次迭代
                
                # 2c: 执行和反馈
                execution_result = await self._phase_4_execute_and_feedback(
                    workflow_context, 
                    case_generation_result["test_case"],
                    conversion_result["python_code"]
                )
                workflow_context["phases"].append(execution_result)
                
                # 如果执行成功，完成工作流程
                if execution_result["success"] and execution_result.get("execution_success", False):
                    return await self._complete_workflow(workflow_context, "completed", "工作流程成功完成")
                
                # 如果不是最后一次迭代，准备反馈给下一轮
                if iteration < max_iterations - 1:
                    workflow_context["feedback_for_next_iteration"] = execution_result.get("feedback", {})
            
            # 所有迭代都失败
            return await self._complete_workflow(workflow_context, "failed", f"达到最大迭代次数({max_iterations})，未能生成成功的用例")
            
        except Exception as e:
            logger.error(f"工作流程执行失败: {e}")
            return await self._complete_workflow(workflow_context, "error", str(e))
    
    @mcp_tool(
        name="get_workflow_status",
        description="获取工作流程状态",
        category="workflow",
        parameters={
            "workflow_id": {"type": "string", "description": "工作流程ID", "required": False}
        }
    )
    async def get_workflow_status(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """获取工作流程状态"""
        if workflow_id:
            workflow = self.active_workflows.get(workflow_id)
            if workflow:
                return {
                    "found": True,
                    "workflow": workflow,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "found": False,
                    "error": f"工作流程 {workflow_id} 不存在",
                    "timestamp": datetime.now().isoformat()
                }
        else:
            return {
                "active_workflows": len(self.active_workflows),
                "workflow_stats": self.workflow_stats,
                "active_workflow_ids": list(self.active_workflows.keys()),
                "timestamp": datetime.now().isoformat()
            }
    
    @mcp_tool(
        name="pause_workflow",
        description="暂停工作流程",
        category="workflow",
        parameters={
            "workflow_id": {"type": "string", "description": "工作流程ID"}
        }
    )
    async def pause_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """暂停工作流程"""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id]["status"] = "paused"
            self.active_workflows[workflow_id]["paused_at"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "message": f"工作流程 {workflow_id} 已暂停",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": f"工作流程 {workflow_id} 不存在",
                "timestamp": datetime.now().isoformat()
            }
    
    @mcp_tool(
        name="resume_workflow",
        description="恢复工作流程",
        category="workflow", 
        parameters={
            "workflow_id": {"type": "string", "description": "工作流程ID"}
        }
    )
    async def resume_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """恢复工作流程"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            if workflow["status"] == "paused":
                workflow["status"] = "running"
                workflow["resumed_at"] = datetime.now().isoformat()
                
                return {
                    "success": True,
                    "message": f"工作流程 {workflow_id} 已恢复",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"工作流程 {workflow_id} 当前状态不是暂停",
                    "timestamp": datetime.now().isoformat()
                }
        else:
            return {
                "success": False,
                "error": f"工作流程 {workflow_id} 不存在",
                "timestamp": datetime.now().isoformat()
            }
    
    # === 私有工作流程阶段方法 ===
    
    async def _phase_1_collect_device_info(self, workflow_context: Dict[str, Any]) -> Dict[str, Any]:
        """阶段1: 收集设备信息"""
        phase_result = {
            "phase": "device_info_collection",
            "start_time": datetime.now().isoformat(),
            "success": False
        }
        
        try:
            logger.info(f"工作流程 {workflow_context['workflow_id']} - 阶段1: 收集设备信息")
            
            # 使用设备检查器获取完整设备信息
            device_info = await self.device_inspector.get_comprehensive_device_info()
            
            if device_info.get("success", False):
                phase_result["success"] = True
                phase_result["device_info"] = device_info["result"]
                logger.info(f"设备信息收集成功 - {len(phase_result['device_info'])} 项信息")
            else:
                phase_result["error"] = device_info.get("error", "设备信息收集失败")
                logger.error(f"设备信息收集失败: {phase_result['error']}")
            
            phase_result["end_time"] = datetime.now().isoformat()
            return phase_result
            
        except Exception as e:
            phase_result["error"] = str(e)
            phase_result["end_time"] = datetime.now().isoformat()
            logger.error(f"设备信息收集阶段异常: {e}")
            return phase_result
    
    async def _phase_2_generate_case(self, workflow_context: Dict[str, Any], device_info: Dict[str, Any]) -> Dict[str, Any]:
        """阶段2: 生成测试用例"""
        phase_result = {
            "phase": "case_generation",
            "iteration": workflow_context["current_iteration"],
            "start_time": datetime.now().isoformat(),
            "success": False
        }
        
        try:
            iteration = workflow_context["current_iteration"]
            logger.info(f"工作流程 {workflow_context['workflow_id']} - 阶段2.{iteration}: 生成测试用例")
            
            # 准备LLM上下文
            llm_context = {
                "test_requirement": workflow_context["test_requirement"],
                "target_app": workflow_context["target_app"],
                "device_info": device_info,
                "workflow_mode": workflow_context["workflow_mode"]
            }
            
            # 如果是重试，添加前一次的反馈
            if iteration > 1 and "feedback_for_next_iteration" in workflow_context:
                llm_context["previous_feedback"] = workflow_context["feedback_for_next_iteration"]
            
            # 使用用例生成器
            generation_result = await self.case_generator.generate_case_with_llm_guidance(
                workflow_context["test_requirement"],
                llm_context
            )
            
            if generation_result.get("success", False):
                phase_result["success"] = True
                phase_result["test_case"] = generation_result["result"]
                phase_result["generation_method"] = generation_result.get("generation_method", "llm_guided")
                logger.info(f"用例生成成功 - 迭代 {iteration}")
            else:
                phase_result["error"] = generation_result.get("error", "用例生成失败")
                logger.error(f"用例生成失败 - 迭代 {iteration}: {phase_result['error']}")
            
            phase_result["end_time"] = datetime.now().isoformat()
            return phase_result
            
        except Exception as e:
            phase_result["error"] = str(e)
            phase_result["end_time"] = datetime.now().isoformat()
            logger.error(f"用例生成阶段异常: {e}")
            return phase_result
    
    async def _phase_3_convert_to_python(self, workflow_context: Dict[str, Any], test_case: Dict[str, Any]) -> Dict[str, Any]:
        """阶段3: 转换为Python代码"""
        phase_result = {
            "phase": "python_conversion", 
            "iteration": workflow_context["current_iteration"],
            "start_time": datetime.now().isoformat(),
            "success": False
        }
        
        try:
            iteration = workflow_context["current_iteration"]
            logger.info(f"工作流程 {workflow_context['workflow_id']} - 阶段3.{iteration}: 转换为Python代码")
            
            # 使用反馈循环的转换功能
            conversion_result = await self.feedback_loop._convert_case_to_python(test_case)
            
            if conversion_result.get("success", False):
                phase_result["success"] = True
                phase_result["python_code"] = conversion_result["python_code"]
                phase_result["converter"] = conversion_result.get("converter", "unknown")
                logger.info(f"Python转换成功 - 迭代 {iteration}")
            else:
                phase_result["error"] = conversion_result.get("error", "Python转换失败")
                logger.error(f"Python转换失败 - 迭代 {iteration}: {phase_result['error']}")
            
            phase_result["end_time"] = datetime.now().isoformat()
            return phase_result
            
        except Exception as e:
            phase_result["error"] = str(e)
            phase_result["end_time"] = datetime.now().isoformat()
            logger.error(f"Python转换阶段异常: {e}")
            return phase_result
    
    async def _phase_4_execute_and_feedback(
        self, 
        workflow_context: Dict[str, Any], 
        test_case: Dict[str, Any], 
        python_code: str
    ) -> Dict[str, Any]:
        """阶段4: 执行并反馈"""
        phase_result = {
            "phase": "execution_and_feedback",
            "iteration": workflow_context["current_iteration"],
            "start_time": datetime.now().isoformat(),
            "success": False
        }
        
        try:
            iteration = workflow_context["current_iteration"]
            logger.info(f"工作流程 {workflow_context['workflow_id']} - 阶段4.{iteration}: 执行并反馈")
            
            # 使用反馈循环执行和分析
            execution_mode = "quick" if workflow_context["workflow_mode"] == "quick" else "full"
            execution_result = await self.feedback_loop.execute_and_analyze(test_case, execution_mode)
            
            if execution_result.get("status") == "completed":
                phase_result["success"] = True
                phase_result["execution_success"] = execution_result.get("execution", {}).get("success", False)
                phase_result["execution_result"] = execution_result
                phase_result["feedback"] = execution_result.get("feedback", {})
                
                # 判断是否真的成功
                if phase_result["execution_success"]:
                    logger.info(f"执行成功 - 迭代 {iteration}")
                else:
                    logger.warning(f"执行完成但用例失败 - 迭代 {iteration}")
            else:
                phase_result["error"] = execution_result.get("error", "执行失败")
                phase_result["execution_result"] = execution_result
                logger.error(f"执行失败 - 迭代 {iteration}: {phase_result['error']}")
            
            phase_result["end_time"] = datetime.now().isoformat()
            return phase_result
            
        except Exception as e:
            phase_result["error"] = str(e)
            phase_result["end_time"] = datetime.now().isoformat()
            logger.error(f"执行反馈阶段异常: {e}")
            return phase_result
    
    async def _complete_workflow(self, workflow_context: Dict[str, Any], status: str, message: str) -> Dict[str, Any]:
        """完成工作流程"""
        workflow_context["status"] = status
        workflow_context["completion_message"] = message
        workflow_context["end_time"] = datetime.now().isoformat()
        
        # 计算执行时间
        start_time = datetime.fromisoformat(workflow_context["start_time"])
        end_time = datetime.fromisoformat(workflow_context["end_time"])
        execution_time = (end_time - start_time).total_seconds()
        workflow_context["execution_time"] = execution_time
        
        # 更新统计
        self.workflow_stats["total_workflows"] += 1
        if status == "completed":
            self.workflow_stats["successful_workflows"] += 1
        else:
            self.workflow_stats["failed_workflows"] += 1
        
        # 更新平均完成时间
        total_time = self.workflow_stats["average_completion_time"] * (self.workflow_stats["total_workflows"] - 1)
        self.workflow_stats["average_completion_time"] = (total_time + execution_time) / self.workflow_stats["total_workflows"]
        
        # 移到历史记录
        self.workflow_history.append(workflow_context.copy())
        if workflow_context["workflow_id"] in self.active_workflows:
            del self.active_workflows[workflow_context["workflow_id"]]
        
        logger.info(f"工作流程完成: {workflow_context['workflow_id']} - {status} - {message}")
        
        return {
            "workflow_id": workflow_context["workflow_id"],
            "status": status,
            "message": message,
            "execution_time": execution_time,
            "phases_completed": len(workflow_context["phases"]),
            "iterations": workflow_context["current_iteration"],
            "full_context": workflow_context,
            "timestamp": datetime.now().isoformat()
        }
    
    def _register_orchestrator_tools(self) -> None:
        """注册编排器自身的MCP工具"""
        # 工具会通过装饰器自动注册
        pass
    
    def _register_component_tools(self) -> None:
        """注册所有组件的MCP工具"""
        # 注册设备检查器工具
        self.tool_registry.register_tool_class(DeviceInspector)
        
        # 注册用例生成器工具  
        self.tool_registry.register_tool_class(InteractiveCaseGenerator)
        
        # 注册反馈循环工具
        self.tool_registry.register_tool_class(FeedbackLoop)
        
        logger.info(f"已注册 {len(self.tool_registry.get_all_tools())} 个MCP工具")


# === 便捷函数 ===

async def create_workflow_orchestrator(device_id: Optional[str] = None) -> WorkflowOrchestrator:
    """创建并初始化工作流程编排器"""
    orchestrator = WorkflowOrchestrator(device_id)
    await orchestrator.initialize()
    return orchestrator


async def run_quick_workflow(test_requirement: str, device_id: Optional[str] = None) -> Dict[str, Any]:
    """快速运行工作流程"""
    orchestrator = await create_workflow_orchestrator(device_id)
    return await orchestrator.start_complete_workflow(
        test_requirement=test_requirement,
        workflow_mode="quick",
        max_iterations=1
    )