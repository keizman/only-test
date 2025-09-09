#!/usr/bin/env python3
"""
Only-Test 统一元素识别器
===========================

提供统一的元素识别接口，自动选择最佳识别策略
支持XML模式、视觉模式和智能Fallback机制
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .strategy_manager import StrategyManager, RecognitionStrategy
from .omniparser_client import OmniparserClient
from .playback_detector import PlaybackDetector

logger = logging.getLogger(__name__)


@dataclass
class RecognitionResult:
    """元素识别结果"""
    success: bool
    strategy_used: str
    elements: List[Dict[str, Any]]
    execution_time: float
    error_message: Optional[str] = None
    fallback_attempts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "strategy_used": self.strategy_used,
            "elements": self.elements,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "fallback_attempts": self.fallback_attempts,
            "timestamp": datetime.now().isoformat()
        }


@dataclass 
class InteractionResult:
    """交互结果"""
    success: bool
    action: str
    target: str
    strategy_used: str
    execution_time: float
    error_message: Optional[str] = None
    coordinates: Optional[Tuple[int, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "action": self.action,
            "target": self.target,
            "strategy_used": self.strategy_used,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "coordinates": self.coordinates,
            "timestamp": datetime.now().isoformat()
        }


class ElementRecognizer:
    """
    统一元素识别器 - Only-Test 视觉识别系统的核心接口
    
    功能特性：
    1. 智能策略选择：根据播放状态和界面复杂度自动选择最佳识别策略
    2. 透明Fallback：失败时自动尝试备选策略，对外无感知
    3. 统一接口：XML和视觉识别使用相同的API接口
    4. 性能优化：缓存机制和智能调度，减少重复计算
    """
    
    def __init__(self, 
                 omniparser_server: str = "http://100.122.57.128:9333",
                 device_id: Optional[str] = None,
                 cache_enabled: bool = True,
                 debug_mode: bool = False):
        """
        初始化元素识别器
        
        Args:
            omniparser_server: Omniparser服务器地址
            device_id: 设备ID（可选）
            cache_enabled: 是否启用缓存
            debug_mode: 是否启用调试模式
        """
        self.device_id = device_id
        self.cache_enabled = cache_enabled
        self.debug_mode = debug_mode
        
        # 初始化核心组件
        self.strategy_manager = StrategyManager()
        self.omniparser_client = OmniparserClient(omniparser_server)
        self.playback_detector = PlaybackDetector()
        
        # 内部状态
        self._last_recognition_result: Optional[RecognitionResult] = None
        self._cache: Dict[str, Any] = {}
        
        logger.info(f"ElementRecognizer初始化完成 - 服务器: {omniparser_server}")
    
    async def initialize(self) -> bool:
        """
        初始化识别器和所有依赖组件
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 初始化Omniparser客户端
            omni_available = await self.omniparser_client.health_check()
            
            # 初始化播放状态检测器
            playback_init = await self.playback_detector.initialize(self.device_id)
            
            # 初始化策略管理器
            self.strategy_manager.set_omniparser_available(omni_available)
            
            if self.debug_mode:
                logger.info(f"初始化状态 - Omniparser: {omni_available}, Playback: {playback_init}")
            
            return omni_available or playback_init  # 至少一个可用即可
            
        except Exception as e:
            logger.error(f"ElementRecognizer初始化失败: {e}")
            return False
    
    async def recognize_elements(self, 
                               filter_package: Optional[str] = None,
                               force_strategy: Optional[RecognitionStrategy] = None) -> RecognitionResult:
        """
        识别屏幕上的所有元素 - 核心识别接口
        
        Args:
            filter_package: 包名过滤器（可选）
            force_strategy: 强制使用指定策略（可选）
            
        Returns:
            RecognitionResult: 识别结果
        """
        start_time = asyncio.get_event_loop().time()
        fallback_attempts = 0
        
        try:
            # 1. 选择识别策略
            if force_strategy:
                strategy = force_strategy
                logger.info(f"使用强制指定策略: {strategy.name}")
            else:
                # 检测播放状态
                is_playing = await self.playback_detector.is_media_playing()
                strategy = self.strategy_manager.select_strategy(
                    is_playing=is_playing,
                    omniparser_available=await self.omniparser_client.health_check()
                )
                logger.info(f"自动选择策略: {strategy.name} (播放状态: {is_playing})")
            
            # 2. 执行识别
            elements = await self._execute_recognition(strategy, filter_package)
            
            # 3. 如果失败且允许fallback，尝试备选策略
            if not elements and strategy != RecognitionStrategy.XML_ONLY:
                logger.warning(f"策略 {strategy.name} 失败，尝试fallback...")
                fallback_attempts += 1
                
                # 尝试XML fallback
                fallback_elements = await self._execute_recognition(
                    RecognitionStrategy.XML_ONLY, filter_package
                )
                
                if fallback_elements:
                    elements = fallback_elements
                    strategy = RecognitionStrategy.XML_ONLY
                    logger.info("Fallback到XML策略成功")
            
            # 4. 构建结果
            execution_time = asyncio.get_event_loop().time() - start_time
            result = RecognitionResult(
                success=len(elements) > 0,
                strategy_used=strategy.name,
                elements=elements,
                execution_time=execution_time,
                fallback_attempts=fallback_attempts
            )
            
            self._last_recognition_result = result
            return result
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"元素识别异常: {e}")
            
            return RecognitionResult(
                success=False,
                strategy_used="error",
                elements=[],
                execution_time=execution_time,
                error_message=str(e),
                fallback_attempts=fallback_attempts
            )
    
    async def find_element(self, 
                          text: Optional[str] = None,
                          resource_id: Optional[str] = None,
                          uuid: Optional[str] = None,
                          content_desc: Optional[str] = None,
                          clickable_only: bool = False) -> Optional[Dict[str, Any]]:
        """
        查找单个元素
        
        Args:
            text: 文本内容
            resource_id: 资源ID
            uuid: 元素UUID（视觉识别）
            content_desc: 内容描述
            clickable_only: 是否只查找可点击元素
            
        Returns:
            Dict: 找到的元素，未找到返回None
        """
        elements = await self.find_elements(
            text=text, resource_id=resource_id, uuid=uuid,
            content_desc=content_desc, clickable_only=clickable_only
        )
        
        return elements[0] if elements else None
    
    async def find_elements(self,
                           text: Optional[str] = None,
                           resource_id: Optional[str] = None,
                           uuid: Optional[str] = None,
                           content_desc: Optional[str] = None,
                           clickable_only: bool = False) -> List[Dict[str, Any]]:
        """
        查找多个元素
        
        Args:
            text: 文本内容
            resource_id: 资源ID  
            uuid: 元素UUID（视觉识别）
            content_desc: 内容描述
            clickable_only: 是否只查找可点击元素
            
        Returns:
            List[Dict]: 找到的元素列表
        """
        # 首先获取所有元素
        recognition_result = await self.recognize_elements()
        
        if not recognition_result.success:
            return []
        
        # 过滤元素
        filtered_elements = []
        
        for element in recognition_result.elements:
            # 文本匹配
            if text and text.lower() not in element.get("text", "").lower():
                continue
                
            # 资源ID匹配
            if resource_id and resource_id != element.get("resource_id"):
                continue
                
            # UUID匹配（视觉识别）
            if uuid and uuid != element.get("uuid"):
                continue
                
            # 内容描述匹配
            if content_desc and content_desc not in element.get("content_desc", ""):
                continue
                
            # 可点击性过滤
            if clickable_only and not element.get("clickable", False):
                continue
            
            filtered_elements.append(element)
        
        return filtered_elements
    
    async def tap_element(self, 
                         element: Optional[Dict[str, Any]] = None,
                         text: Optional[str] = None,
                         resource_id: Optional[str] = None,
                         uuid: Optional[str] = None,
                         bias_correction: bool = False) -> InteractionResult:
        """
        点击元素 - 统一交互接口
        
        Args:
            element: 直接指定要点击的元素
            text: 通过文本查找元素
            resource_id: 通过资源ID查找元素
            uuid: 通过UUID查找元素（视觉识别）
            bias_correction: 是否应用偏移修正（媒体内容）
            
        Returns:
            InteractionResult: 交互结果
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 1. 确定目标元素
            target_element = element
            target_desc = ""
            
            if not target_element:
                if text:
                    target_element = await self.find_element(text=text)
                    target_desc = f"text:{text}"
                elif resource_id:
                    target_element = await self.find_element(resource_id=resource_id)
                    target_desc = f"resource_id:{resource_id}"
                elif uuid:
                    target_element = await self.find_element(uuid=uuid)
                    target_desc = f"uuid:{uuid}"
                else:
                    raise ValueError("必须指定element或查找条件")
            
            if not target_element:
                execution_time = asyncio.get_event_loop().time() - start_time
                return InteractionResult(
                    success=False,
                    action="tap",
                    target=target_desc,
                    strategy_used="none",
                    execution_time=execution_time,
                    error_message="未找到目标元素"
                )
            
            # 2. 计算点击坐标
            coordinates = await self._calculate_tap_coordinates(target_element, bias_correction)
            
            # 3. 执行点击
            success = await self._execute_tap(coordinates)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return InteractionResult(
                success=success,
                action="tap",
                target=target_desc or f"element:{target_element.get('uuid', 'unknown')}",
                strategy_used=target_element.get("source", "unknown"),
                execution_time=execution_time,
                coordinates=coordinates
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"点击操作异常: {e}")
            
            return InteractionResult(
                success=False,
                action="tap",
                target=target_desc,
                strategy_used="error",
                execution_time=execution_time,
                error_message=str(e)
            )
    
    async def get_current_strategy(self) -> Dict[str, Any]:
        """
        获取当前使用的识别策略信息
        
        Returns:
            Dict: 策略信息
        """
        is_playing = await self.playback_detector.is_media_playing()
        omni_available = await self.omniparser_client.health_check()
        
        current_strategy = self.strategy_manager.select_strategy(
            is_playing=is_playing,
            omniparser_available=omni_available
        )
        
        return {
            "current_strategy": current_strategy.name,
            "is_media_playing": is_playing,
            "omniparser_available": omni_available,
            "last_recognition": self._last_recognition_result.to_dict() if self._last_recognition_result else None,
            "timestamp": datetime.now().isoformat()
        }
    
    # === 私有方法 ===
    
    async def _execute_recognition(self, 
                                 strategy: RecognitionStrategy, 
                                 filter_package: Optional[str] = None) -> List[Dict[str, Any]]:
        """执行具体的识别策略"""
        if strategy == RecognitionStrategy.VISUAL_ONLY:
            return await self._recognize_with_omniparser()
        elif strategy == RecognitionStrategy.XML_ONLY:
            return await self._recognize_with_xml(filter_package)
        elif strategy == RecognitionStrategy.HYBRID:
            # 混合模式：先尝试XML，再尝试视觉
            xml_elements = await self._recognize_with_xml(filter_package)
            if xml_elements:
                return xml_elements
            return await self._recognize_with_omniparser()
        else:
            raise ValueError(f"不支持的识别策略: {strategy}")
    
    async def _recognize_with_xml(self, filter_package: Optional[str] = None) -> List[Dict[str, Any]]:
        """使用XML模式识别元素"""
        try:
            # 这里调用现有的XML识别逻辑
            from ..pure_uiautomator2_extractor import UIAutomator2Extractor
            
            extractor = UIAutomator2Extractor()
            elements, _ = await extractor.extract_elements_unified()
            
            # 转换为统一格式
            result = []
            for element in elements:
                if filter_package and filter_package not in element.package:
                    continue
                    
                result.append({
                    "uuid": element.uuid,
                    "text": element.text,
                    "resource_id": element.resource_id,
                    "content_desc": element.content_desc,
                    "clickable": element.clickable,
                    "bounds": element.bounds,
                    "package": element.package,
                    "class_name": element.class_name,
                    "source": "xml_extractor"
                })
            
            return result
            
        except Exception as e:
            logger.error(f"XML识别失败: {e}")
            return []
    
    async def _recognize_with_omniparser(self) -> List[Dict[str, Any]]:
        """使用Omniparser视觉识别元素"""
        try:
            # 获取屏幕截图
            screenshot_base64 = await self._take_screenshot()
            
            # 调用Omniparser分析
            analysis_result = await self.omniparser_client.analyze_screen(screenshot_base64)
            
            # 转换为统一格式
            result = []
            for element in analysis_result.get("elements", []):
                result.append({
                    "uuid": element.get("uuid"),
                    "text": element.get("content", ""),
                    "resource_id": "",  # 视觉识别没有resource_id
                    "content_desc": element.get("content", ""),
                    "clickable": element.get("interactivity", False),
                    "bounds": self._bbox_to_bounds(element.get("bbox", [])),
                    "package": "",  # 视觉识别没有package信息
                    "class_name": element.get("type", "visual_element"),
                    "source": "omniparser"
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Omniparser识别失败: {e}")
            return []
    
    async def _calculate_tap_coordinates(self, 
                                       element: Dict[str, Any], 
                                       bias_correction: bool = False) -> Tuple[int, int]:
        """计算点击坐标"""
        bounds = element.get("bounds", [])
        
        if len(bounds) == 4:
            # bounds格式：[left, top, right, bottom]
            center_x = (bounds[0] + bounds[2]) // 2
            center_y = (bounds[1] + bounds[3]) // 2
            
            # 应用偏移修正（用于媒体内容）
            if bias_correction:
                # 媒体内容的标题通常在可点击区域下方，需要向上偏移
                height = bounds[3] - bounds[1]
                center_y -= int(height * 0.3)  # 向上偏移30%
                
            return (center_x, center_y)
        else:
            raise ValueError(f"无效的bounds格式: {bounds}")
    
    async def _execute_tap(self, coordinates: Tuple[int, int]) -> bool:
        """执行点击操作"""
        try:
            # 这里调用实际的点击接口
            # 可以使用uiautomator2或adb命令
            import subprocess
            x, y = coordinates
            
            cmd = f"adb tap {x} {y}"
            if self.device_id:
                cmd = f"adb -s {self.device_id} shell input tap {x} {y}"
            
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"执行点击失败: {e}")
            return False
    
    async def _take_screenshot(self) -> str:
        """获取屏幕截图的base64编码"""
        try:
            import subprocess
            import base64
            
            # 使用adb获取屏幕截图
            cmd = "adb exec-out screencap -p"
            if self.device_id:
                cmd = f"adb -s {self.device_id} exec-out screencap -p"
                
            result = subprocess.run(cmd.split(), capture_output=True)
            
            if result.returncode == 0:
                return base64.b64encode(result.stdout).decode('utf-8')
            else:
                raise Exception(f"截图失败: {result.stderr}")
                
        except Exception as e:
            logger.error(f"获取屏幕截图失败: {e}")
            raise
    
    def _bbox_to_bounds(self, bbox: List[float]) -> List[int]:
        """将归一化的bbox转换为bounds格式"""
        if len(bbox) != 4:
            return []
        
        # 假设屏幕尺寸（实际应从设备获取）
        screen_width = 1080
        screen_height = 1920
        
        return [
            int(bbox[0] * screen_width),   # left
            int(bbox[1] * screen_height),  # top
            int(bbox[2] * screen_width),   # right
            int(bbox[3] * screen_height)   # bottom
        ]