"""
统一日志管理模块

提供双重输出（命令行+文件）和结构化日志功能
保持时序性和完整XML信息保留
"""

from .unified_logger import UnifiedLogger, get_logger, close_logger

__all__ = ['UnifiedLogger', 'get_logger', 'close_logger']
