"""
Only-Test Prompt Templates Package

包含所有LLM调用的提示词模板，提供结构化和可维护的Prompt管理。
"""

from .generate_cases import TestCaseGenerationPrompts
from .element_location import ElementLocationPrompts
from .conditional_logic import ConditionalLogicPrompts
from .similar_cases import SimilarTestCasePrompts
# 延迟导入或暂不导入体量较大的模板，避免不必要的语法解析/加载
# from .code_optimization import CodeOptimizationPrompts

__all__ = [
    'TestCaseGenerationPrompts',
    'ElementLocationPrompts', 
    'ConditionalLogicPrompts',
    'SimilarTestCasePrompts'
]

__version__ = '1.0.0'
