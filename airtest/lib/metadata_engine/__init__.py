"""
智能元数据处理引擎

处理智能元数据的解析、条件判断和上下文管理
支持条件分支逻辑和AI友好的用例描述
"""

from .metadata_parser import MetadataParser
from .conditional_logic import ConditionalLogicEngine  
from .context_manager import ContextManager

__all__ = [
    'MetadataParser',
    'ConditionalLogicEngine',
    'ContextManager'
]

__version__ = '1.0.0'