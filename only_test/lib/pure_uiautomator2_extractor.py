#!/usr/bin/env python3
"""
Enhanced Pure UIAutomator2 Widget Extractor with Omniparser Integration
增强版纯UIAutomator2提取器，集成Omniparser视觉识别能力

核心功能:
1. 正常模式: 使用 XML 方式定位元素并点击，执行用户任务
2. 播放状态: 使用 Omniparser 解析现有模式进行视觉识别
3. 统一接口: 智能调度器自动选择最佳工具，对外输出一致
4. 手动选择: 支持外部指定使用的具体组件
"""

import sys
import os
import json
import xml.etree.ElementTree as ET
import asyncio
import base64
import time
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum
from dataclasses import dataclass

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("enhanced_ui_extractor")

class ExtractionMode(Enum):
    """提取模式枚举"""
    AUTO = "auto"           # 自动选择模式
    XML_ONLY = "xml_only"   # 仅使用XML模式
    VISUAL_ONLY = "visual_only"  # 仅使用视觉模式
    HYBRID = "hybrid"       # 混合模式


class PlaybackState(Enum):
    """播放状态枚举"""
    UNKNOWN = "unknown"
    PLAYING = "playing"
    STOPPED = "stopped"


@dataclass
class UnifiedElement:
    """统一元素结构"""
    uuid: str
    element_type: str  # "xml" or "visual"
    name: str
    text: str
    package: str
    resource_id: str
    content_desc: str
    class_name: str
    clickable: bool
    bounds: List[float]  # 归一化坐标 [x1, y1, x2, y2]
    center_x: float      # 归一化中心X
    center_y: float      # 归一化中心Y
    confidence: float    # 识别置信度 (0.0-1.0)
    source: str         # 数据源 ("xml_extractor" or "omniparser")
    metadata: Dict[str, Any] = None  # 额外元数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "uuid": self.uuid,
            "element_type": self.element_type,
            "name": self.name,
            "text": self.text,
            "package": self.package,
            "resource_id": self.resource_id,
            "content_desc": self.content_desc,
            "class_name": self.class_name,
            "clickable": self.clickable,
            "bounds": self.bounds,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "confidence": self.confidence,
            "source": self.source,
            "metadata": self.metadata or {}
        }

    def get_screen_coordinates(self, screen_width: int, screen_height: int, bias: bool = False) -> Tuple[int, int]:
        """获取实际屏幕坐标"""
        x = int(self.center_x * screen_width)
        y = int(self.center_y * screen_height)
        
        # 媒体内容偏差校正
        if bias:
            bias_pixels = int(screen_height * 0.02)  # 2% 上移
            y = max(0, y - bias_pixels)
        
        return x, y


class PlaybackDetector:
    """播放状态检测器"""
    
    def __init__(self, device=None):
        self.device = device
        
    async def detect_playback_state(self) -> PlaybackState:
        """检测当前播放状态"""
        try:
            # 方法1: 检查音频flinger状态
            audio_active = await self._check_audio_flinger()
            
            # 方法2: 检查Wake Locks
            wake_lock_active = await self._check_wake_locks()
            
            # 综合判断
            if audio_active or wake_lock_active:
                logger.info("检测到播放状态")
                return PlaybackState.PLAYING
            else:
                logger.info("未检测到播放状态")
                return PlaybackState.STOPPED
                
        except Exception as e:
            logger.error(f"播放状态检测失败: {e}")
            return PlaybackState.UNKNOWN
    
    async def _check_audio_flinger(self) -> bool:
        """检查音频flinger状态"""
        try:
            cmd = 'adb shell "dumpsys media.audio_flinger | grep \\"Standby: no\\" | wc -l"'
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                count = int(stdout.decode().strip())
                return count >= 1
                
        except Exception as e:
            logger.warning(f"音频flinger检测失败: {e}")
        
        return False
    
    async def _check_wake_locks(self) -> bool:
        """检查Wake Locks状态"""
        try:
            cmd = 'adb shell "dumpsys power | grep -i wake | grep Audio | wc -l"'
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                count = int(stdout.decode().strip())
                return count >= 1
                
        except Exception as e:
            logger.warning(f"Wake Lock检测失败: {e}")
        
        return False


class OmniparserClient:
    """Omniparser客户端 - 从phone_mcp复制过来的核心代码"""
    
    def __init__(self, server_url: str = "http://100.122.57.128:9333"):
        self.server_url = server_url.rstrip('/')
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept-Encoding': 'gzip, deflate'
        })
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            probe_url = f"{self.server_url}/probe/"
            response = self.session.get(probe_url, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"Omniparser健康检查失败: {e}")
            return False
    
    async def parse_screen(self, base64_image: str, use_paddleocr: Optional[bool] = None) -> Dict[str, Any]:
        """解析屏幕图像"""
        try:
            payload = {
                "base64_image": base64_image
            }
            if use_paddleocr is not None:
                payload["use_paddleocr"] = use_paddleocr
            
            parse_url = f"{self.server_url}/parse/"
            response = self.session.post(
                parse_url,
                json=payload,
                timeout=90
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Omniparser解析失败: {e}")
            raise Exception(f"Failed to parse screen: {str(e)}")


class VisualExtractor:
    """视觉提取器 - 基于Omniparser"""
    
    def __init__(self, omniparser_client: OmniparserClient, device=None):
        self.client = omniparser_client
        self.device = device
        self.screen_width = 1080
        self.screen_height = 1920
        self._cache = {}
        self._cache_timeout = 5.0
    
    async def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        try:
            if self.device:
                info = self.device.info
                self.screen_width = info.get('displayWidth', 1080)
                self.screen_height = info.get('displayHeight', 1920)
            else:
                # 使用ADB获取
                proc = await asyncio.create_subprocess_shell(
                    "adb shell wm size",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    import re
                    match = re.search(r'(\d+)x(\d+)', stdout.decode())
                    if match:
                        self.screen_width = int(match.group(1))
                        self.screen_height = int(match.group(2))
            
            return self.screen_width, self.screen_height
            
        except Exception as e:
            logger.error(f"获取屏幕尺寸失败: {e}")
            return 1080, 1920
    
    async def take_screenshot(self) -> str:
        """截屏并返回base64"""
        try:
            # 使用ADB截屏
            temp_file = f"/tmp/screenshot_{int(time.time())}.png"
            
            proc = await asyncio.create_subprocess_shell(
                f"adb shell screencap -p > {temp_file}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise Exception(f"截屏失败: {stderr.decode()}")
            
            # 读取并转换为base64
            with open(temp_file, 'rb') as f:
                image_data = f.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # 清理临时文件
            try:
                os.remove(temp_file)
            except:
                pass
            
            return base64_image
            
        except Exception as e:
            logger.error(f"截屏失败: {e}")
            raise
    
    async def extract_elements(self, use_cache: bool = True) -> List[UnifiedElement]:
        """提取视觉元素"""
        try:
            # 检查缓存
            cache_key = "visual_elements"
            current_time = time.time()
            
            if use_cache and cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                if current_time - timestamp < self._cache_timeout:
                    logger.info("使用缓存的视觉分析结果")
                    return cached_data
            
            # 获取屏幕尺寸
            screen_width, screen_height = await self.get_screen_size()
            
            # 截屏
            base64_image = await self.take_screenshot()
            
            # Omniparser解析
            parse_result = await self.client.parse_screen(base64_image, use_paddleocr=True)
            
            # 转换为统一元素格式
            elements = []
            parsed_content = parse_result.get("parsed_content_list", [])
            
            for i, item in enumerate(parsed_content):
                bbox = item.get("bbox", [])
                if len(bbox) >= 4:
                    element = UnifiedElement(
                        uuid=item.get("uuid", f"visual_{i}"),
                        element_type="visual",
                        name=item.get("content", ""),
                        text=item.get("content", ""),
                        package="",  # 视觉识别无包名信息
                        resource_id="",
                        content_desc=item.get("content", ""),
                        class_name=item.get("type", "visual_element"),
                        clickable=item.get("interactivity", True),
                        bounds=bbox,  # 已经是归一化坐标
                        center_x=(bbox[0] + bbox[2]) / 2,
                        center_y=(bbox[1] + bbox[3]) / 2,
                        confidence=1.0,  # Omniparser默认高置信度
                        source="omniparser",
                        metadata={
                            "omniparser_type": item.get("type", ""),
                            "omniparser_source": item.get("source", ""),
                            "screen_size": {"width": screen_width, "height": screen_height}
                        }
                    )
                    elements.append(element)
            
            # 缓存结果
            if use_cache:
                self._cache[cache_key] = (elements, current_time)
            
            logger.info(f"提取到 {len(elements)} 个视觉元素")
            return elements
            
        except Exception as e:
            logger.error(f"视觉元素提取失败: {e}")
            return []


class EnhancedUIAutomator2Extractor:
    """增强版UIAutomator2提取器"""
    
    def __init__(self, device_id=None, omniparser_url="http://100.122.57.128:9333"):
        """初始化提取器
        
        Args:
            device_id: 设备ID，None为默认设备
            omniparser_url: Omniparser服务器URL
        """
        self.device_id = device_id
        self.device = None
        self.xml_content = None
        self.screen_size = (1440, 2560)
        
        # 初始化组件
        self.omniparser_client = OmniparserClient(omniparser_url)
        self.visual_extractor = VisualExtractor(self.omniparser_client)
        self.playback_detector = PlaybackDetector()
        
        # 缓存
        self._xml_elements_cache = None
        self._visual_elements_cache = None
        self._last_extraction_mode = None
        
    async def stop_uiautomator_service(self):
        """停止UIAutomator服务"""
        try:
            logger.info("正在停止UIAutomator服务...")
            
            # 使用ADB命令停止UIAutomator服务
            cmd = "adb shell am force-stop com.github.uiautomator"
            cmd2 = "adb shell am force-stop com.github.uiautomator.test"
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )         
            proc2 = await asyncio.create_subprocess_shell(
                cmd2,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                logger.info("✅ UIAutomator服务已停止")
                # 等待一段时间确保服务完全停止
                await asyncio.sleep(2)
                return True
            else:
                logger.warning(f"停止UIAutomator服务时出现警告: {stderr.decode().strip()}")
                # 即使有警告，也认为执行成功，因为force-stop命令通常都会成功
                await asyncio.sleep(2)
                return True
                
        except Exception as e:
            logger.error(f"停止UIAutomator服务失败: {e}")
            return False

    def connect_device(self):
        """连接设备"""
        try:
            import uiautomator2 as u2
            
            if self.device_id:
                self.device = u2.connect(self.device_id)
                logger.info(f"已连接到设备: {self.device_id}")
            else:
                self.device = u2.connect()
                logger.info("已连接到默认设备")
            
            # 获取屏幕尺寸
            info = self.device.info
            self.screen_size = (info.get('displayWidth', 1440), info.get('displayHeight', 2560))
            logger.info(f"屏幕尺寸: {self.screen_size[0]}x{self.screen_size[1]}")
            
            # 更新相关组件的设备引用
            self.visual_extractor.device = self.device
            self.visual_extractor.screen_width = self.screen_size[0]
            self.visual_extractor.screen_height = self.screen_size[1]
            self.playback_detector.device = self.device
            
            return True
            
        except Exception as e:
            logger.error(f"连接设备失败: {e}")
            return False
    
    async def detect_optimal_mode(self) -> ExtractionMode:
        """检测最佳提取模式"""
        try:
            # 检查Omniparser服务器状态
            omniparser_available = await self.omniparser_client.health_check()
            
            # 检查播放状态
            playback_state = await self.playback_detector.detect_playback_state()
            
            if playback_state == PlaybackState.PLAYING:
                if omniparser_available:
                    logger.info("检测到播放状态，选择视觉模式")
                    return ExtractionMode.VISUAL_ONLY
                else:
                    logger.warning("播放状态但Omniparser不可用，回退到XML模式")
                    return ExtractionMode.XML_ONLY
            else:
                logger.info("非播放状态，选择XML模式")
                return ExtractionMode.XML_ONLY
                
        except Exception as e:
            logger.error(f"模式检测失败: {e}")
            return ExtractionMode.XML_ONLY
    
    def parse_bounds(self, bounds_str):
        """解析bounds字符串"""
        try:
            bounds_str = bounds_str.replace('[', '').replace(']', ',')
            coords = [int(x) for x in bounds_str.split(',') if x]
            if len(coords) >= 4:
                return coords[0], coords[1], coords[2], coords[3]
        except (ValueError, IndexError):
            pass
        return 0, 0, 0, 0
    
    def get_xml_from_device(self):
        """从设备获取XML"""
        if not self.device:
            if not self.connect_device():
                return False
        
        try:
            logger.info("正在获取设备UI层次结构XML...")
            self.xml_content = self.device.dump_hierarchy()
            
            if not self.xml_content:
                logger.error("获取XML失败")
                return False
            
            logger.info(f"获取XML成功，长度: {len(self.xml_content)} 字符")
            return True
            
        except Exception as e:
            logger.error(f"获取XML失败: {e}")
            return False
    
    def extract_xml_elements(self) -> List[UnifiedElement]:
        """提取XML元素"""
        if not self.xml_content:
            if not self.get_xml_from_device():
                return []
        
        try:
            logger.info("正在解析XML...")
            root = ET.fromstring(self.xml_content)
            
            elements = []
            self._extract_xml_node_recursive(root, elements, [])
            
            logger.info(f"成功提取 {len(elements)} 个XML元素")
            return elements
            
        except Exception as e:
            logger.error(f"解析XML失败: {e}")
            return []
    
    def _extract_xml_node_recursive(self, node_elem, elements: List[UnifiedElement], path: List[int]):
        """递归提取XML节点"""
        # 跳过hierarchy根节点
        if node_elem.tag == 'hierarchy':
            for i, child in enumerate(node_elem):
                self._extract_xml_node_recursive(child, elements, [i])
            return
        
        # 提取当前节点属性
        attrib = node_elem.attrib
        bounds_str = attrib.get('bounds', '[0,0][0,0]')
        x1, y1, x2, y2 = self.parse_bounds(bounds_str)
        
        # 计算归一化坐标
        if self.screen_size[0] > 0 and self.screen_size[1] > 0:
            norm_bounds = [
                x1 / self.screen_size[0],
                y1 / self.screen_size[1],
                x2 / self.screen_size[0],
                y2 / self.screen_size[1]
            ]
            center_x = (norm_bounds[0] + norm_bounds[2]) / 2
            center_y = (norm_bounds[1] + norm_bounds[3]) / 2
        else:
            norm_bounds = [0, 0, 0, 0]
            center_x, center_y = 0, 0
        
        # 创建统一元素
        text = attrib.get('text', '').strip()
        class_name = attrib.get('class', '')
        resource_id = attrib.get('resource-id', '')
        content_desc = attrib.get('content-desc', '').strip()
        package = attrib.get('package', '')
        
        element = UnifiedElement(
            uuid=f"xml_{len(elements)}",
            element_type="xml",
            name=resource_id if resource_id else (text if text else class_name),
            text=text,
            package=package,
            resource_id=resource_id,
            content_desc=content_desc,
            class_name=class_name,
            clickable=attrib.get('clickable', 'false').lower() == 'true',
            bounds=norm_bounds,
            center_x=center_x,
            center_y=center_y,
            confidence=1.0,  # XML数据置信度为1.0
            source="xml_extractor",
            metadata={
                "path": '/'.join(map(str, path)) if path else 'root',
                "raw_bounds": bounds_str,
                "enabled": attrib.get('enabled', 'false').lower() == 'true',
                "focusable": attrib.get('focusable', 'false').lower() == 'true',
                "scrollable": attrib.get('scrollable', 'false').lower() == 'true',
                "children_count": len(list(node_elem))
            }
        )
        
        elements.append(element)
        
        # 递归处理子节点
        for i, child in enumerate(node_elem):
            self._extract_xml_node_recursive(child, elements, path + [i])
    
    async def extract_elements_unified(self, 
                                     mode: ExtractionMode = ExtractionMode.AUTO,
                                     use_cache: bool = True) -> Tuple[List[UnifiedElement], ExtractionMode]:
        """统一元素提取接口
        
        Returns:
            (elements, actual_mode): 元素列表和实际使用的模式
        """
        # 自动模式检测
        if mode == ExtractionMode.AUTO:
            mode = await self.detect_optimal_mode()
        
        # 检查缓存
        if use_cache and mode == self._last_extraction_mode:
            if mode in [ExtractionMode.XML_ONLY, ExtractionMode.HYBRID] and self._xml_elements_cache:
                logger.info("使用缓存的XML元素")
                return self._xml_elements_cache, mode
            elif mode == ExtractionMode.VISUAL_ONLY and self._visual_elements_cache:
                logger.info("使用缓存的视觉元素")
                return self._visual_elements_cache, mode
        
        elements = []
        
        try:
            if mode == ExtractionMode.XML_ONLY:
                elements = self.extract_xml_elements()
                self._xml_elements_cache = elements
                
            elif mode == ExtractionMode.VISUAL_ONLY:
                elements = await self.visual_extractor.extract_elements(use_cache)
                self._visual_elements_cache = elements
                
            elif mode == ExtractionMode.HYBRID:
                # 混合模式：同时使用两种方法
                xml_elements = self.extract_xml_elements()
                visual_elements = await self.visual_extractor.extract_elements(use_cache)
                
                # 合并元素，优先视觉识别结果
                elements = visual_elements + xml_elements
                
                self._xml_elements_cache = xml_elements
                self._visual_elements_cache = visual_elements
            
            self._last_extraction_mode = mode
            logger.info(f"使用 {mode.value} 模式提取到 {len(elements)} 个元素")
            
        except Exception as e:
            logger.error(f"元素提取失败: {e}")
            # 降级处理
            if mode != ExtractionMode.XML_ONLY:
                logger.info("降级到XML模式")
                elements = self.extract_xml_elements()
                mode = ExtractionMode.XML_ONLY
        
        return elements, mode
    
    async def find_elements_by_text(self, 
                                  text: str, 
                                  partial_match: bool = True,
                                  mode: ExtractionMode = ExtractionMode.AUTO) -> List[UnifiedElement]:
        """根据文本查找元素"""
        elements, actual_mode = await self.extract_elements_unified(mode)
        
        matches = []
        for element in elements:
            element_text = element.text.lower()
            search_text = text.lower()
            
            if partial_match:
                if search_text in element_text or search_text in element.name.lower():
                    matches.append(element)
            else:
                if element_text == search_text or element.name.lower() == search_text:
                    matches.append(element)
        
        logger.info(f"找到 {len(matches)} 个匹配 '{text}' 的元素")
        return matches
    
    async def find_elements_by_resource_id(self, 
                                         resource_id: str,
                                         mode: ExtractionMode = ExtractionMode.AUTO) -> List[UnifiedElement]:
        """根据resource_id查找元素"""
        elements, actual_mode = await self.extract_elements_unified(mode)
        
        matches = []
        for element in elements:
            if resource_id in element.resource_id:
                matches.append(element)
        
        logger.info(f"找到 {len(matches)} 个匹配resource_id '{resource_id}' 的元素")
        return matches
    
    async def find_clickable_elements(self, 
                                    mode: ExtractionMode = ExtractionMode.AUTO) -> List[UnifiedElement]:
        """查找所有可点击元素"""
        elements, actual_mode = await self.extract_elements_unified(mode)
        
        clickable_elements = [e for e in elements if e.clickable]
        logger.info(f"找到 {len(clickable_elements)} 个可点击元素")
        return clickable_elements
    
    async def tap_element(self, element: UnifiedElement, bias: bool = False) -> bool:
        """点击元素"""
        try:
            if not self.device and not self.connect_device():
                logger.error("无法连接设备")
                return False
            
            # 获取实际屏幕坐标
            x, y = element.get_screen_coordinates(self.screen_size[0], self.screen_size[1], bias)
            
            # 使用uiautomator2点击
            if self.device:
                self.device.click(x, y)
                logger.info(f"点击元素 {element.uuid} 在坐标 ({x}, {y})")
                return True
            else:
                # 降级使用ADB
                proc = await asyncio.create_subprocess_shell(
                    f"adb shell input tap {x} {y}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    logger.info(f"ADB点击元素 {element.uuid} 在坐标 ({x}, {y})")
                    return True
                else:
                    logger.error(f"ADB点击失败: {stderr.decode()}")
                    return False
                
        except Exception as e:
            logger.error(f"点击元素失败: {e}")
            return False
    
    async def tap_by_text(self, 
                         text: str, 
                         partial_match: bool = True,
                         bias: bool = False,
                         mode: ExtractionMode = ExtractionMode.AUTO) -> bool:
        """根据文本点击元素"""
        elements = await self.find_elements_by_text(text, partial_match, mode)
        
        if not elements:
            logger.warning(f"未找到文本为 '{text}' 的元素")
            return False
        
        # 选择第一个可点击的元素
        for element in elements:
            if element.clickable:
                return await self.tap_element(element, bias)
        
        # 如果没有可点击的，尝试点击第一个
        logger.warning("没有可点击元素，尝试点击第一个")
        return await self.tap_element(elements[0], bias)
    
    async def get_elements_json(self, 
                              mode: ExtractionMode = ExtractionMode.AUTO,
                              filter_package: str = None) -> Dict[str, Any]:
        """获取元素的JSON格式数据"""
        elements, actual_mode = await self.extract_elements_unified(mode)
        
        # 包过滤
        if filter_package:
            elements = [e for e in elements if filter_package in e.package]
        
        return {
            "total_count": len(elements),
            "extraction_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "extraction_mode": actual_mode.value,
            "screen_size": self.screen_size,
            "playback_state": (await self.playback_detector.detect_playback_state()).value,
            "elements": [element.to_dict() for element in elements],
            "statistics": {
                "xml_elements": len([e for e in elements if e.element_type == "xml"]),
                "visual_elements": len([e for e in elements if e.element_type == "visual"]),
                "clickable_elements": len([e for e in elements if e.clickable]),
                "text_elements": len([e for e in elements if e.text.strip()])
            }
        }
    
    def save_elements_json(self, filename: str, mode: ExtractionMode = ExtractionMode.AUTO, filter_package: str = None):
        """保存元素到JSON文件（同步版本）"""
        async def _save():
            data = await self.get_elements_json(mode, filter_package)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"元素数据已保存到: {filename}")
        
        # 运行异步函数
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在事件循环中，创建任务
                import asyncio
                task = loop.create_task(_save())
                # 注意：这里不能await，因为我们在同步函数中
                logger.info("异步保存任务已创建")
            else:
                loop.run_until_complete(_save())
        except Exception as e:
            logger.error(f"保存失败: {e}")


# 智能调度器 - 统一对外接口
class UIAutomationScheduler:
    """UI自动化智能调度器
    
    对外提供统一接口，内部智能选择XML或视觉识别方法
    """
    
    def __init__(self, device_id=None, omniparser_url="http://100.122.57.128:9333"):
        self.extractor = EnhancedUIAutomator2Extractor(device_id, omniparser_url)
        self.default_mode = ExtractionMode.AUTO
    
    async def initialize(self):
        """初始化调度器"""
        # 首先停止UIAutomator服务
        await self.extractor.stop_uiautomator_service()
        
        # 然后连接设备
        return self.extractor.connect_device()
    
    # 统一对外接口 - 对LLM透明
    async def get_screen_elements(self, filter_package: str = None) -> Dict[str, Any]:
        """获取屏幕元素 - 统一接口"""
        return await self.extractor.get_elements_json(self.default_mode, filter_package)
    
    async def find_elements(self, 
                          text: str = None, 
                          resource_id: str = None,
                          clickable_only: bool = False) -> List[Dict[str, Any]]:
        """查找元素 - 统一接口"""
        if text:
            elements = await self.extractor.find_elements_by_text(text, True, self.default_mode)
        elif resource_id:
            elements = await self.extractor.find_elements_by_resource_id(resource_id, self.default_mode)
        elif clickable_only:
            elements = await self.extractor.find_clickable_elements(self.default_mode)
        else:
            elements, _ = await self.extractor.extract_elements_unified(self.default_mode)
        
        return [element.to_dict() for element in elements]
    
    async def tap_element_by_text(self, text: str, bias: bool = False) -> Dict[str, Any]:
        """根据文本点击元素 - 统一接口"""
        success = await self.extractor.tap_by_text(text, True, bias, self.default_mode)
        
        return {
            "success": success,
            "action": "tap",
            "target": text,
            "bias_applied": bias,
            "timestamp": datetime.now().isoformat()
        }
    
    async def tap_element_by_uuid(self, uuid: str, bias: bool = False) -> Dict[str, Any]:
        """根据UUID点击元素 - 统一接口"""
        # 获取所有元素
        elements, _ = await self.extractor.extract_elements_unified(self.default_mode)
        
        # 查找目标元素
        target_element = None
        for element in elements:
            if element.uuid == uuid:
                target_element = element
                break
        
        if not target_element:
            return {
                "success": False,
                "error": f"Element with UUID {uuid} not found",
                "action": "tap",
                "timestamp": datetime.now().isoformat()
            }
        
        success = await self.extractor.tap_element(target_element, bias)
        
        return {
            "success": success,
            "action": "tap",
            "target": uuid,
            "element": target_element.to_dict(),
            "bias_applied": bias,
            "timestamp": datetime.now().isoformat()
        }
    
    # 手动模式选择接口 - 允许外部指定组件
    async def force_xml_mode(self):
        """强制使用XML模式"""
        self.default_mode = ExtractionMode.XML_ONLY
        logger.info("已切换到强制XML模式")
    
    async def force_visual_mode(self):
        """强制使用视觉模式"""
        self.default_mode = ExtractionMode.VISUAL_ONLY
        logger.info("已切换到强制视觉模式")
    
    async def auto_mode(self):
        """恢复自动模式"""
        self.default_mode = ExtractionMode.AUTO
        logger.info("已恢复自动模式")
    
    async def get_current_mode_info(self) -> Dict[str, Any]:
        """获取当前模式信息"""
        playback_state = await self.extractor.playback_detector.detect_playback_state()
        omniparser_available = await self.extractor.omniparser_client.health_check()
        
        return {
            "current_mode": self.default_mode.value,
            "playback_state": playback_state.value,
            "omniparser_available": omniparser_available,
            "screen_size": self.extractor.screen_size,
            "device_connected": self.extractor.device is not None
        }
    
    async def stop_uiautomator_service(self) -> bool:
        """手动停止UIAutomator服务 - 对外接口"""
        return await self.extractor.stop_uiautomator_service()


# 兼容性函数 - 保持向后兼容
def extract_from_device(device_id=None, output_file="enhanced_ui_widgets.json"):
    """从设备提取widget信息的简单接口 - 兼容原有API"""
    async def _extract():
        scheduler = UIAutomationScheduler(device_id)
        
        # 初始化时会自动停止UIAutomator服务
        if not await scheduler.initialize():
            logger.error("初始化失败")
            return None
        
        data = await scheduler.get_screen_elements()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"数据已保存到: {output_file}")
        return data
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_extract())
        loop.close()
        return result
    except Exception as e:
        logger.error(f"提取失败: {e}")
        return None


async def main():
    """主函数 - 演示增强功能"""
    print("Enhanced UIAutomator2 Extractor with Omniparser Integration")
    print("=" * 70)
    
    try:
        
        # 创建调度器
        scheduler = UIAutomationScheduler()
        
        # 初始化（包含停止UIAutomator服务）
        print("正在初始化调度器（包含停止UIAutomator服务）...")
        if not await scheduler.initialize():
            print("❌ 初始化失败")
            return
        
        print("✅ 调度器初始化完成")
        
        # 获取模式信息
        mode_info = await scheduler.get_current_mode_info()
        print(f"当前模式: {mode_info['current_mode']}")
        print(f"播放状态: {mode_info['playback_state']}")
        print(f"Omniparser可用: {mode_info['omniparser_available']}")
        print(f"屏幕尺寸: {mode_info['screen_size']}")
        
        # 获取屏幕元素
        print("\n正在获取屏幕元素...")
        elements_data = await scheduler.get_screen_elements()
        
        print(f"✅ 提取完成!")
        print(f"总元素数: {elements_data['total_count']}")
        print(f"提取模式: {elements_data['extraction_mode']}")
        print(f"统计信息: {elements_data['statistics']}")
        
        # 保存结果
        filename = f"enhanced_ui_elements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(elements_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 数据已保存到: {filename}")
        
        # 演示查找功能
        print("\n演示元素查找功能...")
        clickable_elements = await scheduler.find_elements(clickable_only=True)
        print(f"找到 {len(clickable_elements)} 个可点击元素")
        
        # 显示前5个可点击元素
        for i, element in enumerate(clickable_elements[:5]):
            print(f"  {i+1}. {element['name']} - {element['text'][:20]}...")
        
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())