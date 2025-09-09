#!/usr/bin/env python3
"""
Only-Test 视觉识别集成层
============================

将XML识别、视觉识别、策略管理等组件整合为统一接口
提供动态策略切换和智能fallback机制
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass

from .element_recognizer import ElementRecognizer, RecognitionResult, InteractionResult
from .strategy_manager import StrategyManager, RecognitionStrategy, StrategyDecision
from .omniparser_client import OmniparserClient
from .playback_detector import PlaybackDetector, PlaybackState

logger = logging.getLogger(__name__)


@dataclass
class IntegrationConfig:
    """集成配置"""
    omniparser_server: str = "http://100.122.57.128:9333"
    device_id: Optional[str] = None
    cache_enabled: bool = True
    debug_mode: bool = False
    auto_strategy_enabled: bool = True
    fallback_enabled: bool = True
    performance_monitoring: bool = True


class VisualIntegration:
    """
    视觉识别集成器 - Only-Test视觉识别系统的统一入口
    
    功能特性：
    1. 统一接口：对外提供简单的元素识别和交互接口
    2. 智能策略：自动根据播放状态切换识别策略  
    3. 透明Fallback：失败时自动尝试备选方案
    4. 性能监控：跟踪各组件性能和成功率
    5. 简化集成：一行代码即可完成复杂的元素识别任务
    """
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        """
        初始化视觉识别集成器
        
        Args:
            config: 集成配置，为None时使用默认配置
        """
        self.config = config or IntegrationConfig()
        
        # 初始化核心组件
        self.element_recognizer = ElementRecognizer(
            omniparser_server=self.config.omniparser_server,
            device_id=self.config.device_id,
            cache_enabled=self.config.cache_enabled,
            debug_mode=self.config.debug_mode
        )
        
        # 性能统计
        self._performance_stats = {
            "total_recognitions": 0,
            "successful_recognitions": 0,
            "total_interactions": 0,
            "successful_interactions": 0,
            "strategy_switches": 0,
            "fallback_uses": 0
        }
        
        # 内部状态
        self._initialized = False
        self._last_strategy: Optional[RecognitionStrategy] = None
        
        logger.info("VisualIntegration初始化完成")
    
    async def initialize(self) -> bool:
        """
        初始化所有组件
        
        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            return True
        
        try:
            # 初始化元素识别器
            success = await self.element_recognizer.initialize()
            
            if success:
                self._initialized = True
                logger.info("VisualIntegration系统初始化成功")
            else:
                logger.error("VisualIntegration系统初始化失败")
            
            return success
            
        except Exception as e:
            logger.error(f"VisualIntegration初始化异常: {e}")
            return False
    
    # === 核心接口：简化的元素识别和交互 ===
    
    async def find_and_tap(self, 
                          text: Optional[str] = None,
                          resource_id: Optional[str] = None,
                          content_desc: Optional[str] = None,
                          uuid: Optional[str] = None,
                          bias_correction: bool = False,
                          timeout: float = 10.0) -> bool:
        """
        查找并点击元素 - 一步到位的简化接口
        
        Args:
            text: 文本内容
            resource_id: 资源ID
            content_desc: 内容描述
            uuid: 元素UUID（视觉识别）
            bias_correction: 是否应用偏移修正
            timeout: 超时时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 执行点击操作
            result = await self.element_recognizer.tap_element(
                text=text,
                resource_id=resource_id,
                uuid=uuid,
                bias_correction=bias_correction
            )
            
            # 更新统计
            self._performance_stats["total_interactions"] += 1
            if result.success:
                self._performance_stats["successful_interactions"] += 1
            
            # 记录策略使用情况
            if hasattr(self.element_recognizer.strategy_manager, 'record_strategy_performance'):
                strategy = RecognitionStrategy(result.strategy_used) if result.strategy_used != "error" else None
                if strategy:
                    self.element_recognizer.strategy_manager.record_strategy_performance(
                        strategy, result.success, result.execution_time
                    )
            
            if self.config.debug_mode:
                logger.debug(f"find_and_tap结果: {result.success}, 策略: {result.strategy_used}, 耗时: {result.execution_time:.2f}s")
            
            return result.success
            
        except Exception as e:
            logger.error(f"find_and_tap异常: {e}")
            return False
    
    async def smart_recognize(self, 
                            package_filter: Optional[str] = None,
                            clickable_only: bool = False) -> Dict[str, Any]:
        """
        智能元素识别 - 自动选择最佳策略
        
        Args:
            package_filter: 包名过滤器
            clickable_only: 是否只识别可点击元素
            
        Returns:
            Dict: 识别结果和详细信息
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 执行识别
            result = await self.element_recognizer.recognize_elements(package_filter)
            
            # 更新统计
            self._performance_stats["total_recognitions"] += 1
            if result.success:
                self._performance_stats["successful_recognitions"] += 1
            
            if result.fallback_attempts > 0:
                self._performance_stats["fallback_uses"] += 1
            
            # 检查策略切换
            current_strategy = RecognitionStrategy(result.strategy_used) if result.strategy_used != "error" else None
            if current_strategy and current_strategy != self._last_strategy:
                self._performance_stats["strategy_switches"] += 1
                self._last_strategy = current_strategy
            
            # 过滤结果
            elements = result.elements
            if clickable_only:
                elements = [elem for elem in elements if elem.get("clickable", False)]
            
            return {
                "success": result.success,
                "elements": elements,
                "total_count": len(elements),
                "strategy_used": result.strategy_used,
                "execution_time": result.execution_time,
                "fallback_attempts": result.fallback_attempts,
                "error_message": result.error_message
            }
            
        except Exception as e:
            logger.error(f"smart_recognize异常: {e}")
            return {
                "success": False,
                "elements": [],
                "total_count": 0,
                "error_message": str(e)
            }
    
    async def adaptive_find_element(self, 
                                  target_desc: str,
                                  search_strategies: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        自适应元素查找 - 尝试多种查找方式
        
        Args:
            target_desc: 目标描述（可能是文本、资源ID等）
            search_strategies: 搜索策略列表 ["text", "resource_id", "content_desc"]
            
        Returns:
            Dict: 找到的元素，未找到返回None
        """
        if not search_strategies:
            search_strategies = ["text", "resource_id", "content_desc"]
        
        for strategy in search_strategies:
            try:
                element = None
                
                if strategy == "text":
                    element = await self.element_recognizer.find_element(text=target_desc)
                elif strategy == "resource_id":
                    element = await self.element_recognizer.find_element(resource_id=target_desc)
                elif strategy == "content_desc":
                    element = await self.element_recognizer.find_element(content_desc=target_desc)
                
                if element:
                    if self.config.debug_mode:
                        logger.debug(f"自适应查找成功 - 策略: {strategy}, 目标: {target_desc}")
                    return element
                    
            except Exception as e:
                logger.warning(f"自适应查找策略 {strategy} 失败: {e}")
        
        logger.info(f"自适应查找失败 - 目标: {target_desc}")
        return None
    
    # === 高级接口：策略控制和状态查询 ===
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态信息
        
        Returns:
            Dict: 系统状态
        """
        try:
            # 获取当前策略信息
            strategy_info = await self.element_recognizer.get_current_strategy()
            
            # 获取性能统计
            performance_stats = self._performance_stats.copy()
            
            # 计算成功率
            if performance_stats["total_recognitions"] > 0:
                performance_stats["recognition_success_rate"] = (
                    performance_stats["successful_recognitions"] / 
                    performance_stats["total_recognitions"]
                )
            
            if performance_stats["total_interactions"] > 0:
                performance_stats["interaction_success_rate"] = (
                    performance_stats["successful_interactions"] / 
                    performance_stats["total_interactions"]
                )
            
            return {
                "initialized": self._initialized,
                "config": {
                    "omniparser_server": self.config.omniparser_server,
                    "device_id": self.config.device_id,
                    "auto_strategy_enabled": self.config.auto_strategy_enabled,
                    "fallback_enabled": self.config.fallback_enabled
                },
                "current_strategy": strategy_info,
                "performance": performance_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                "initialized": self._initialized,
                "error": str(e)
            }
    
    async def force_strategy(self, strategy: Union[str, RecognitionStrategy]) -> bool:
        """
        强制使用指定策略
        
        Args:
            strategy: 策略名称或枚举
            
        Returns:
            bool: 设置是否成功
        """
        try:
            if isinstance(strategy, str):
                strategy = RecognitionStrategy(strategy)
            
            # 这里可以扩展策略管理器的强制策略功能
            logger.info(f"强制策略设置: {strategy.value}")
            return True
            
        except Exception as e:
            logger.error(f"强制策略设置失败: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        系统健康检查
        
        Returns:
            Dict: 健康检查结果
        """
        health_status = {
            "overall_healthy": True,
            "components": {},
            "issues": []
        }
        
        try:
            # 检查Omniparser客户端
            omni_healthy = await self.element_recognizer.omniparser_client.health_check()
            health_status["components"]["omniparser"] = {
                "healthy": omni_healthy,
                "server": self.config.omniparser_server
            }
            
            if not omni_healthy:
                health_status["overall_healthy"] = False
                health_status["issues"].append("Omniparser服务器连接失败")
            
            # 检查播放状态检测器
            try:
                media_info = await self.element_recognizer.playback_detector.get_media_info()
                playback_healthy = media_info.state != PlaybackState.ERROR
                health_status["components"]["playback_detector"] = {
                    "healthy": playback_healthy,
                    "current_state": media_info.state.value
                }
                
                if not playback_healthy:
                    health_status["overall_healthy"] = False
                    health_status["issues"].append("播放状态检测器异常")
            except:
                health_status["components"]["playback_detector"] = {
                    "healthy": False
                }
                health_status["issues"].append("播放状态检测器不可用")
            
            # 检查设备连接
            # 这里可以添加更多的设备连接检查
            
        except Exception as e:
            health_status["overall_healthy"] = False
            health_status["issues"].append(f"健康检查异常: {e}")
        
        return health_status
    
    # === 工具方法 ===
    
    def reset_performance_stats(self) -> None:
        """重置性能统计"""
        self._performance_stats = {
            "total_recognitions": 0,
            "successful_recognitions": 0,
            "total_interactions": 0,
            "successful_interactions": 0,
            "strategy_switches": 0,
            "fallback_uses": 0
        }
        logger.info("性能统计已重置")
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            # 清空缓存
            if hasattr(self.element_recognizer, 'omniparser_client'):
                self.element_recognizer.omniparser_client.clear_cache()
            
            if hasattr(self.element_recognizer, 'playback_detector'):
                self.element_recognizer.playback_detector.clear_cache()
            
            logger.info("VisualIntegration资源清理完成")
            
        except Exception as e:
            logger.error(f"资源清理异常: {e}")


# === 简化的全局实例和便捷函数 ===

_global_visual_integration: Optional[VisualIntegration] = None


async def get_visual_integration(config: Optional[IntegrationConfig] = None) -> VisualIntegration:
    """
    获取全局视觉识别集成实例
    
    Args:
        config: 配置，首次调用时生效
        
    Returns:
        VisualIntegration: 集成实例
    """
    global _global_visual_integration
    
    if _global_visual_integration is None:
        _global_visual_integration = VisualIntegration(config)
        await _global_visual_integration.initialize()
    
    return _global_visual_integration


# === 便捷函数：一行代码完成常用操作 ===

async def tap_by_text(text: str, bias_correction: bool = False) -> bool:
    """便捷函数：通过文本点击元素"""
    integration = await get_visual_integration()
    return await integration.find_and_tap(text=text, bias_correction=bias_correction)


async def tap_by_resource_id(resource_id: str) -> bool:
    """便捷函数：通过资源ID点击元素"""
    integration = await get_visual_integration()
    return await integration.find_and_tap(resource_id=resource_id)


async def smart_tap(target: str, bias_correction: bool = False) -> bool:
    """便捷函数：智能点击（自动尝试多种匹配方式）"""
    integration = await get_visual_integration()
    
    # 尝试多种匹配策略
    strategies = ["text", "resource_id", "content_desc"]
    
    for strategy in strategies:
        success = False
        if strategy == "text":
            success = await integration.find_and_tap(text=target, bias_correction=bias_correction)
        elif strategy == "resource_id":
            success = await integration.find_and_tap(resource_id=target)
        elif strategy == "content_desc":
            success = await integration.find_and_tap(content_desc=target)
        
        if success:
            return True
    
    return False


async def get_all_elements(clickable_only: bool = False) -> List[Dict[str, Any]]:
    """便捷函数：获取所有元素"""
    integration = await get_visual_integration()
    result = await integration.smart_recognize(clickable_only=clickable_only)
    return result.get("elements", [])


async def is_media_playing() -> bool:
    """便捷函数：检查是否正在播放媒体"""
    integration = await get_visual_integration()
    return await integration.element_recognizer.playback_detector.is_media_playing()