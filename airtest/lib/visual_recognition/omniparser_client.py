#!/usr/bin/env python3
"""
Only-Test Omniparser 客户端
==============================

负责与Omniparser服务器通信，提供视觉元素识别服务
从phone-use项目迁移而来，针对Only-Test框架进行了优化
"""

import asyncio
import json
import logging
import time
import base64
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class OmniElement:
    """Omniparser识别的UI元素"""
    uuid: str
    type: str                    # "text", "icon", etc.
    bbox: List[float]           # [x1, y1, x2, y2] 归一化坐标
    interactivity: bool         # 是否可交互
    content: str               # 元素内容
    source: str = "omniparser"
    
    @property
    def center_x(self) -> float:
        """获取中心X坐标（归一化）"""
        return (self.bbox[0] + self.bbox[2]) / 2
    
    @property
    def center_y(self) -> float:
        """获取中心Y坐标（归一化）"""
        return (self.bbox[1] + self.bbox[3]) / 2
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "uuid": self.uuid,
            "type": self.type,
            "bbox": self.bbox,
            "interactivity": self.interactivity,
            "content": self.content,
            "source": self.source,
            "center_x": self.center_x,
            "center_y": self.center_y
        }


@dataclass
class AnalysisResult:
    """Omniparser分析结果"""
    success: bool
    elements: List[OmniElement]
    total_count: int
    analysis_time: float
    server_version: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "elements": [elem.to_dict() for elem in self.elements],
            "total_count": self.total_count,
            "analysis_time": self.analysis_time,
            "server_version": self.server_version,
            "error_message": self.error_message,
            "timestamp": datetime.now().isoformat()
        }


class OmniparserClient:
    """
    Omniparser客户端 - 视觉识别服务接口
    
    功能特性：
    1. 服务器通信：与Omniparser服务器进行可靠通信
    2. 元素识别：获取屏幕上的所有可视元素
    3. 智能重试：网络异常时自动重试
    4. 性能监控：跟踪识别性能和服务器状态
    5. 缓存支持：减少重复请求，提高响应速度
    """
    
    def __init__(self, 
                 server_url: str = "http://100.122.57.128:9333",
                 timeout: int = 30,
                 max_retries: int = 3):
        """
        初始化Omniparser客户端
        
        Args:
            server_url: Omniparser服务器地址
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 创建会话和重试策略
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置请求头
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Only-Test-Visual-Recognition/1.0'
        })
        
        # 内部状态
        self._server_healthy = None
        self._last_health_check = 0
        self._health_check_interval = 60  # 60秒
        self._analysis_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5分钟缓存
        
        logger.info(f"OmniparserClient初始化完成 - 服务器: {server_url}")
    
    async def health_check(self, force_check: bool = False) -> bool:
        """
        检查Omniparser服务器健康状态
        
        Args:
            force_check: 是否强制检查，忽略缓存
            
        Returns:
            bool: 服务器是否健康
        """
        current_time = time.time()
        
        # 使用缓存的健康状态
        if not force_check and self._server_healthy is not None:
            if current_time - self._last_health_check < self._health_check_interval:
                return self._server_healthy
        
        try:
            probe_url = f"{self.server_url}/probe/"
            
            # 使用asyncio执行同步请求
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.session.get(probe_url, timeout=5)
            )
            
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            is_healthy = result.get("status") == "healthy"
            
            # 更新缓存状态
            self._server_healthy = is_healthy
            self._last_health_check = current_time
            
            if is_healthy:
                logger.info("Omniparser服务器健康检查通过")
            else:
                logger.warning(f"Omniparser服务器状态异常: {result}")
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"Omniparser健康检查失败: {e}")
            self._server_healthy = False
            self._last_health_check = current_time
            return False
    
    async def analyze_screen(self, 
                           screenshot_base64: str,
                           use_paddleocr: Optional[bool] = None,
                           enable_cache: bool = True) -> Dict[str, Any]:
        """
        分析屏幕截图，识别UI元素
        
        Args:
            screenshot_base64: Base64编码的屏幕截图
            use_paddleocr: 是否使用PaddleOCR（True=全文本，False=仅图标，None=服务器默认）
            enable_cache: 是否启用缓存
            
        Returns:
            Dict: 分析结果
        """
        start_time = time.time()
        
        try:
            # 生成缓存键
            cache_key = None
            if enable_cache:
                import hashlib
                cache_key = hashlib.md5(
                    f"{screenshot_base64[:100]}{use_paddleocr}".encode()
                ).hexdigest()
                
                # 检查缓存
                if cache_key in self._analysis_cache:
                    cache_data = self._analysis_cache[cache_key]
                    if time.time() - cache_data["timestamp"] < self._cache_ttl:
                        logger.debug("使用缓存的分析结果")
                        return cache_data["result"]
            
            # 准备请求数据
            request_data = {
                "base64_image": screenshot_base64
            }
            
            if use_paddleocr is not None:
                request_data["use_paddleocr"] = use_paddleocr
            
            # 发送分析请求
            parse_url = f"{self.server_url}/parse/"
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.session.post(
                    parse_url, 
                    json=request_data, 
                    timeout=self.timeout
                )
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 解析响应
            analysis_result = self._parse_analysis_response(result, time.time() - start_time)
            result_dict = analysis_result.to_dict()
            
            # 更新缓存
            if enable_cache and cache_key:
                self._analysis_cache[cache_key] = {
                    "result": result_dict,
                    "timestamp": time.time()
                }
                
                # 清理过期缓存
                self._cleanup_cache()
            
            logger.info(f"屏幕分析完成 - 识别到 {analysis_result.total_count} 个元素，耗时 {analysis_result.analysis_time:.2f}s")
            
            return result_dict
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"屏幕分析失败: {e}")
            
            return AnalysisResult(
                success=False,
                elements=[],
                total_count=0,
                analysis_time=execution_time,
                error_message=str(e)
            ).to_dict()
    
    async def find_elements_by_content(self, 
                                     screenshot_base64: str,
                                     target_content: str,
                                     similarity_threshold: float = 0.8) -> List[OmniElement]:
        """
        根据内容查找元素
        
        Args:
            screenshot_base64: Base64编码的屏幕截图
            target_content: 目标内容
            similarity_threshold: 相似度阈值
            
        Returns:
            List[OmniElement]: 匹配的元素列表
        """
        analysis_result = await self.analyze_screen(screenshot_base64)
        
        if not analysis_result["success"]:
            return []
        
        matching_elements = []
        target_lower = target_content.lower()
        
        for element_data in analysis_result["elements"]:
            element = self._dict_to_omni_element(element_data)
            content_lower = element.content.lower()
            
            # 简单的文本匹配（可以后续优化为更智能的匹配）
            if target_lower in content_lower or content_lower in target_lower:
                matching_elements.append(element)
        
        logger.info(f"内容匹配找到 {len(matching_elements)} 个元素")
        return matching_elements
    
    async def find_interactive_elements(self, screenshot_base64: str) -> List[OmniElement]:
        """
        查找所有可交互元素
        
        Args:
            screenshot_base64: Base64编码的屏幕截图
            
        Returns:
            List[OmniElement]: 可交互元素列表
        """
        analysis_result = await self.analyze_screen(screenshot_base64)
        
        if not analysis_result["success"]:
            return []
        
        interactive_elements = []
        
        for element_data in analysis_result["elements"]:
            element = self._dict_to_omni_element(element_data)
            if element.interactivity:
                interactive_elements.append(element)
        
        logger.info(f"找到 {len(interactive_elements)} 个可交互元素")
        return interactive_elements
    
    async def get_server_info(self) -> Dict[str, Any]:
        """
        获取服务器信息
        
        Returns:
            Dict: 服务器信息
        """
        try:
            info_url = f"{self.server_url}/info/"
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.session.get(info_url, timeout=10)
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"获取服务器信息失败: {e}")
            return {"error": str(e)}
    
    def clear_cache(self) -> None:
        """清空所有缓存"""
        self._analysis_cache.clear()
        logger.info("Omniparser缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        current_time = time.time()
        valid_entries = sum(
            1 for data in self._analysis_cache.values()
            if current_time - data["timestamp"] < self._cache_ttl
        )
        
        return {
            "total_entries": len(self._analysis_cache),
            "valid_entries": valid_entries,
            "cache_ttl": self._cache_ttl,
            "last_cleanup": getattr(self, "_last_cleanup", 0)
        }
    
    # === 私有方法 ===
    
    def _parse_analysis_response(self, response: Dict[str, Any], execution_time: float) -> AnalysisResult:
        """解析Omniparser响应"""
        try:
            success = response.get("success", False)
            
            if not success:
                return AnalysisResult(
                    success=False,
                    elements=[],
                    total_count=0,
                    analysis_time=execution_time,
                    error_message=response.get("error", "未知错误")
                )
            
            # 解析元素列表
            elements = []
            elements_data = response.get("elements", [])
            
            for i, element_data in enumerate(elements_data):
                try:
                    element = OmniElement(
                        uuid=element_data.get("uuid", f"omni_{i}"),
                        type=element_data.get("type", "unknown"),
                        bbox=element_data.get("bbox", [0, 0, 0, 0]),
                        interactivity=element_data.get("interactivity", False),
                        content=element_data.get("content", ""),
                        source="omniparser"
                    )
                    elements.append(element)
                except Exception as e:
                    logger.warning(f"解析元素 {i} 失败: {e}")
            
            return AnalysisResult(
                success=True,
                elements=elements,
                total_count=len(elements),
                analysis_time=execution_time,
                server_version=response.get("version")
            )
            
        except Exception as e:
            logger.error(f"解析Omniparser响应失败: {e}")
            return AnalysisResult(
                success=False,
                elements=[],
                total_count=0,
                analysis_time=execution_time,
                error_message=f"响应解析失败: {e}"
            )
    
    def _dict_to_omni_element(self, element_data: Dict[str, Any]) -> OmniElement:
        """将字典转换为OmniElement对象"""
        return OmniElement(
            uuid=element_data.get("uuid", ""),
            type=element_data.get("type", "unknown"),
            bbox=element_data.get("bbox", [0, 0, 0, 0]),
            interactivity=element_data.get("interactivity", False),
            content=element_data.get("content", ""),
            source="omniparser"
        )
    
    def _cleanup_cache(self) -> None:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, data in self._analysis_cache.items()
            if current_time - data["timestamp"] > self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._analysis_cache[key]
        
        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 个过期缓存项")
        
        self._last_cleanup = current_time