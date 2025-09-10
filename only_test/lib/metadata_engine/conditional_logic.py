"""
条件分支逻辑引擎

处理智能测试用例中的条件判断和分支逻辑
支持复杂的条件表达式和多路径选择

例如: "根据搜索框是否有内容，选择点击搜索或取消按钮"
"""

import re
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ConditionType(Enum):
    """条件类型枚举"""
    ELEMENT_EXISTS = "element_exists"
    ELEMENT_CONTENT_CHECK = "element_content_check"
    ELEMENT_VISIBLE = "element_visible"
    PAGE_STATE = "page_state"
    APP_STATE = "app_state"
    CUSTOM = "custom"


@dataclass
class Condition:
    """条件定义"""
    type: ConditionType
    target: str
    check: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class ConditionalPath:
    """条件分支路径"""
    condition_result: bool
    action: str
    target: str
    data: Optional[str] = None
    reason: Optional[str] = None
    ai_hint: Optional[str] = None


class ConditionalLogicEngine:
    """条件逻辑引擎"""
    
    def __init__(self, context_manager=None):
        """
        初始化条件逻辑引擎
        
        Args:
            context_manager: 上下文管理器，用于获取当前状态
        """
        self.context_manager = context_manager
        self._condition_evaluators = {
            ConditionType.ELEMENT_EXISTS: self._evaluate_element_exists,
            ConditionType.ELEMENT_CONTENT_CHECK: self._evaluate_element_content,
            ConditionType.ELEMENT_VISIBLE: self._evaluate_element_visible,
            ConditionType.PAGE_STATE: self._evaluate_page_state,
            ConditionType.APP_STATE: self._evaluate_app_state,
        }
    
    def parse_conditional_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析条件动作配置
        
        Args:
            action_data: 包含条件逻辑的动作数据
            
        Returns:
            Dict: 解析后的条件动作
            
        Example:
            action_data = {
                "action": "conditional_action",
                "condition": {
                    "type": "element_content_check",
                    "target": "search_input_box", 
                    "check": "has_text_content"
                },
                "conditional_paths": {
                    "if_has_content": {...},
                    "if_empty": {...}
                }
            }
        """
        if action_data.get("action") != "conditional_action":
            return action_data
            
        condition_config = action_data.get("condition", {})
        condition = Condition(
            type=ConditionType(condition_config.get("type")),
            target=condition_config.get("target"),
            check=condition_config.get("check"),
            params=condition_config.get("params")
        )
        
        return {
            "condition": condition,
            "paths": action_data.get("conditional_paths", {}),
            "description": action_data.get("description", ""),
            "business_logic": action_data.get("business_logic", "")
        }
    
    def evaluate_condition(self, condition: Condition) -> bool:
        """
        评估条件是否满足
        
        Args:
            condition: 条件对象
            
        Returns:
            bool: 条件评估结果
        """
        evaluator = self._condition_evaluators.get(condition.type)
        if not evaluator:
            raise ValueError(f"Unsupported condition type: {condition.type}")
            
        return evaluator(condition)
    
    def select_path(self, conditional_action: Dict[str, Any]) -> ConditionalPath:
        """
        根据条件选择执行路径
        
        Args:
            conditional_action: 条件动作配置
            
        Returns:
            ConditionalPath: 选择的执行路径
        """
        condition = conditional_action["condition"]
        paths = conditional_action["paths"]
        
        # 评估条件
        condition_result = self.evaluate_condition(condition)
        
        # 选择路径
        if condition_result:
            path_key = "if_has_content" if "if_has_content" in paths else "if_true"
            path_data = paths.get(path_key, {})
        else:
            path_key = "if_empty" if "if_empty" in paths else "if_false"
            path_data = paths.get(path_key, {})
        
        return ConditionalPath(
            condition_result=condition_result,
            action=path_data.get("action"),
            target=path_data.get("target"),
            data=path_data.get("data"),
            reason=path_data.get("reason"),
            ai_hint=path_data.get("ai_hint")
        )
    
    def _evaluate_element_exists(self, condition: Condition) -> bool:
        """评估元素是否存在"""
        # 这里将集成实际的元素检查逻辑
        # 暂时返回模拟结果
        return True
    
    def _evaluate_element_content(self, condition: Condition) -> bool:
        """
        评估元素内容状态
        
        处理类似："judge by box have content or not" 的逻辑
        """
        target = condition.target
        check = condition.check
        
        if check == "has_text_content":
            # 这里将集成实际的内容检查逻辑
            # 检查输入框是否有文本内容
            # 暂时返回模拟结果，实际应该检查元素的text属性
            return False  # 假设搜索框为空
        
        elif check == "is_empty":
            # 检查元素是否为空
            return True
        
        elif check == "contains_text":
            # 检查元素是否包含特定文本
            expected_text = condition.params.get("text", "") if condition.params else ""
            # 这里应该获取实际元素内容进行比较
            return False
        
        return False
    
    def _evaluate_element_visible(self, condition: Condition) -> bool:
        """评估元素是否可见"""
        # 这里将集成实际的可见性检查逻辑
        return True
    
    def _evaluate_page_state(self, condition: Condition) -> bool:
        """评估页面状态"""
        if self.context_manager:
            current_page = self.context_manager.get_current_page()
            expected_page = condition.check
            return current_page == expected_page
        return True
    
    def _evaluate_app_state(self, condition: Condition) -> bool:
        """评估应用状态"""
        if self.context_manager:
            app_state = self.context_manager.get_app_state()
            expected_state = condition.check
            return app_state == expected_state
        return True
    
    def generate_execution_plan(self, conditional_action: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成条件执行计划
        
        Args:
            conditional_action: 条件动作配置
            
        Returns:
            Dict: 执行计划，包含选择的路径和原因
        """
        selected_path = self.select_path(conditional_action)
        
        return {
            "selected_path": selected_path,
            "condition_result": selected_path.condition_result,
            "execution_reason": selected_path.reason,
            "ai_hint": selected_path.ai_hint,
            "business_logic": conditional_action.get("business_logic", ""),
            "fallback_available": len(conditional_action["paths"]) > 1
        }