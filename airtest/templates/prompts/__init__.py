"""
Only-Test Prompt Templates Package

包含所有LLM调用的提示词模板，提供结构化和可维护的Prompt管理。
"""

from .generate_cases import TestCaseGenerationPrompts
from .element_location import ElementLocationPrompts
from .conditional_logic import ConditionalLogicPrompts
from .similar_cases import SimilarTestCasePrompts
from .code_optimization import CodeOptimizationPrompts

__all__ = [
    'TestCaseGenerationPrompts',
    'ElementLocationPrompts', 
    'ConditionalLogicPrompts',
    'SimilarTestCasePrompts',
    'CodeOptimizationPrompts'
]

__version__ = '1.0.0'