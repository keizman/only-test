#!/usr/bin/env python3
"""
Only-Test Device Inspector
==========================

为LLM提供设备探测能力
让AI能够获取实时设备信息、分析界面状态
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

from lib.visual_recognition import VisualIntegration, get_all_elements, is_media_playing
from lib.device_adapter import DeviceAdapter
from .mcp_server import mcp_tool

logger = logging.getLogger(__name__)


class DeviceInspector:
    """
    设备探测器 - 为LLM提供设备信息获取能力
    
    功能特性：
    1. 设备基本信息探测
    2. 当前界面分析
    3. 元素识别和分类
    4. 应用状态检测
    5. 播放状态分析
    """
    
    def __init__(self, device_id: Optional[str] = None):
        """初始化设备探测器"""
        self.device_id = device_id
        self.visual_integration: Optional[VisualIntegration] = None
        self.device_adapter: Optional[DeviceAdapter] = None
        self._initialized = False
        
        logger.info(f"设备探测器初始化 - 设备: {device_id or 'default'}")
    
    async def initialize(self) -> bool:
        """初始化所有组件"""
        try:
            # 初始化视觉识别系统
            self.visual_integration = VisualIntegration()
            await self.visual_integration.initialize()
            
            # 初始化设备适配器
            self.device_adapter = DeviceAdapter()
            
            self._initialized = True
            logger.info("设备探测器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"设备探测器初始化失败: {e}")
            return False
    
    @mcp_tool(
        name="get_device_basic_info",
        description="获取设备基本信息（型号、分辨率、Android版本等）",
        category="device_info",
        parameters={
            "include_cache": {"type": "boolean", "description": "是否包含缓存信息", "default": False}
        }
    )
    async def get_device_basic_info(self, include_cache: bool = False) -> Dict[str, Any]:
        """获取设备基本信息"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # 获取设备基本信息
            device_info = {
                "device_id": self.device_id,
                "timestamp": datetime.now().isoformat(),
                "connection_status": "connected"
            }
            
            # 使用ADB获取设备信息
            import subprocess
            
            # 设备型号
            result = subprocess.run(
                f"adb {'-s ' + self.device_id if self.device_id else ''} shell getprop ro.product.model".split(),
                capture_output=True, text=True
            )
            device_info["model"] = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            # Android版本
            result = subprocess.run(
                f"adb {'-s ' + self.device_id if self.device_id else ''} shell getprop ro.build.version.release".split(),
                capture_output=True, text=True
            )
            device_info["android_version"] = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            # 屏幕分辨率
            result = subprocess.run(
                f"adb {'-s ' + self.device_id if self.device_id else ''} shell wm size".split(),
                capture_output=True, text=True
            )
            if result.returncode == 0 and "Physical size:" in result.stdout:
                size_info = result.stdout.split("Physical size: ")[1].strip()
                device_info["screen_resolution"] = size_info
            else:
                device_info["screen_resolution"] = "Unknown"
            
            # 屏幕密度
            result = subprocess.run(
                f"adb {'-s ' + self.device_id if self.device_id else ''} shell wm density".split(),
                capture_output=True, text=True
            )
            if result.returncode == 0 and "Physical density:" in result.stdout:
                density_info = result.stdout.split("Physical density: ")[1].strip()
                device_info["screen_density"] = density_info
            else:
                device_info["screen_density"] = "Unknown"
            
            return device_info
            
        except Exception as e:
            logger.error(f"获取设备基本信息失败: {e}")
            return {
                "error": str(e),
                "device_id": self.device_id,
                "timestamp": datetime.now().isoformat()
            }
    
    @mcp_tool(
        name="get_current_screen_info",
        description="获取当前屏幕信息（前台应用、页面状态、元素数量等）",
        category="screen_analysis",
        parameters={
            "include_elements": {"type": "boolean", "description": "是否包含元素列表", "default": False},
            "clickable_only": {"type": "boolean", "description": "是否只分析可点击元素", "default": True}
        }
    )
    async def get_current_screen_info(self, include_elements: bool = False, clickable_only: bool = True) -> Dict[str, Any]:
        """获取当前屏幕信息"""
        if not self._initialized:
            await self.initialize()
        
        try:
            screen_info = {
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "current_screen"
            }
            
            # 获取前台应用
            import subprocess
            result = subprocess.run(
                f"adb {'-s ' + self.device_id if self.device_id else ''} shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'".split(),
                capture_output=True, text=True, shell=True
            )
            
            if result.returncode == 0:
                output = result.stdout
                # 解析包名
                import re
                match = re.search(r'(\w+\.\w+\.\w+)', output)
                screen_info["current_app"] = match.group(1) if match else "Unknown"
            else:
                screen_info["current_app"] = "Unknown"
            
            # 获取元素信息
            elements = await get_all_elements(clickable_only=clickable_only)
            screen_info["total_elements"] = len(elements)
            
            if clickable_only:
                screen_info["clickable_elements"] = len(elements)
                screen_info["element_types"] = {}
                for element in elements:
                    element_type = element.get("source", "unknown")
                    screen_info["element_types"][element_type] = screen_info["element_types"].get(element_type, 0) + 1
            
            # 分析元素类型分布
            if elements:
                # 按文本内容分类
                text_elements = [e for e in elements if e.get("text", "").strip()]
                button_elements = [e for e in elements if "button" in e.get("class_name", "").lower()]
                input_elements = [e for e in elements if "edit" in e.get("class_name", "").lower()]
                
                screen_info["element_analysis"] = {
                    "has_text": len(text_elements),
                    "buttons": len(button_elements),  
                    "input_fields": len(input_elements),
                    "recognition_strategy": elements[0].get("source", "unknown") if elements else "none"
                }
            
            # 播放状态检测
            playing = await is_media_playing()
            screen_info["media_playing"] = playing
            
            # 如果需要包含元素列表
            if include_elements:
                # 限制元素数量避免响应过大
                limited_elements = elements[:50] if len(elements) > 50 else elements
                screen_info["elements"] = [
                    {
                        "text": elem.get("text", "")[:50],  # 限制文本长度
                        "resource_id": elem.get("resource_id", ""),
                        "class_name": elem.get("class_name", ""),
                        "clickable": elem.get("clickable", False),
                        "source": elem.get("source", ""),
                        "bounds": elem.get("bounds", [])
                    }
                    for elem in limited_elements
                ]
                if len(elements) > 50:
                    screen_info["elements_truncated"] = True
                    screen_info["total_elements_available"] = len(elements)
            
            return screen_info
            
        except Exception as e:
            logger.error(f"获取屏幕信息失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @mcp_tool(
        name="find_elements_by_content",
        description="根据内容查找元素（文本、资源ID等）",
        category="element_search",
        parameters={
            "search_text": {"type": "string", "description": "搜索文本"},
            "search_type": {"type": "string", "description": "搜索类型", "enum": ["text", "resource_id", "content_desc", "all"], "default": "all"},
            "case_sensitive": {"type": "boolean", "description": "是否区分大小写", "default": False}
        }
    )
    async def find_elements_by_content(self, search_text: str, search_type: str = "all", case_sensitive: bool = False) -> Dict[str, Any]:
        """根据内容查找元素"""
        if not self._initialized:
            await self.initialize()
        
        try:
            if not self.visual_integration:
                return {"error": "视觉识别系统未初始化"}
            
            search_results = {
                "search_text": search_text,
                "search_type": search_type,
                "case_sensitive": case_sensitive,
                "timestamp": datetime.now().isoformat(),
                "matches": []
            }
            
            # 获取所有元素
            all_elements = await get_all_elements()
            
            # 搜索逻辑
            search_term = search_text if case_sensitive else search_text.lower()
            
            for element in all_elements:
                match_found = False
                match_details = {"element": element, "match_type": []}
                
                # 检查不同类型的匹配
                if search_type in ["text", "all"]:
                    element_text = element.get("text", "")
                    compare_text = element_text if case_sensitive else element_text.lower()
                    if search_term in compare_text:
                        match_found = True
                        match_details["match_type"].append("text")
                
                if search_type in ["resource_id", "all"]:
                    resource_id = element.get("resource_id", "")
                    compare_id = resource_id if case_sensitive else resource_id.lower()
                    if search_term in compare_id:
                        match_found = True
                        match_details["match_type"].append("resource_id")
                
                if search_type in ["content_desc", "all"]:
                    content_desc = element.get("content_desc", "")
                    compare_desc = content_desc if case_sensitive else content_desc.lower()
                    if search_term in compare_desc:
                        match_found = True
                        match_details["match_type"].append("content_desc")
                
                if match_found:
                    # 简化元素信息
                    simplified_element = {
                        "text": element.get("text", ""),
                        "resource_id": element.get("resource_id", ""),
                        "content_desc": element.get("content_desc", ""),
                        "class_name": element.get("class_name", ""),
                        "clickable": element.get("clickable", False),
                        "bounds": element.get("bounds", []),
                        "source": element.get("source", "")
                    }
                    
                    search_results["matches"].append({
                        "element": simplified_element,
                        "match_types": match_details["match_type"]
                    })
            
            search_results["total_matches"] = len(search_results["matches"])
            
            return search_results
            
        except Exception as e:
            logger.error(f"元素搜索失败: {e}")
            return {
                "error": str(e),
                "search_text": search_text,
                "timestamp": datetime.now().isoformat()
            }
    
    @mcp_tool(
        name="analyze_app_state",
        description="分析当前应用状态（登录状态、页面类型、功能可用性等）",
        category="app_analysis",
        parameters={
            "app_package": {"type": "string", "description": "应用包名（可选）", "default": ""},
            "deep_analysis": {"type": "boolean", "description": "是否进行深度分析", "default": False}
        }
    )
    async def analyze_app_state(self, app_package: str = "", deep_analysis: bool = False) -> Dict[str, Any]:
        """分析应用状态"""
        if not self._initialized:
            await self.initialize()
        
        try:
            analysis_result = {
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "app_state",
                "target_package": app_package
            }
            
            # 获取当前屏幕信息
            screen_info = await self.get_current_screen_info(include_elements=True, clickable_only=False)
            current_app = screen_info.get("current_app", "")
            elements = screen_info.get("elements", [])
            
            analysis_result["current_app"] = current_app
            analysis_result["is_target_app"] = (app_package == current_app) if app_package else True
            
            # 页面类型推断
            page_type = self._infer_page_type(elements)
            analysis_result["inferred_page_type"] = page_type
            
            # 功能状态分析
            feature_analysis = self._analyze_features(elements)
            analysis_result["features"] = feature_analysis
            
            # 播放状态分析
            media_playing = await is_media_playing()
            analysis_result["media_state"] = {
                "is_playing": media_playing,
                "playback_elements": self._find_playback_elements(elements)
            }
            
            # 如果启用深度分析
            if deep_analysis:
                # 弹窗检测
                popups = self._detect_popups(elements)
                analysis_result["popups"] = popups
                
                # 错误状态检测
                error_indicators = self._detect_error_states(elements)
                analysis_result["errors"] = error_indicators
                
                # 加载状态检测
                loading_indicators = self._detect_loading_states(elements)
                analysis_result["loading"] = loading_indicators
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"应用状态分析失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @mcp_tool(
        name="get_system_status",
        description="获取设备系统状态（内存、电量、网络等）",
        category="system_info",
        parameters={
            "include_performance": {"type": "boolean", "description": "是否包含性能信息", "default": False}
        }
    )
    async def get_system_status(self, include_performance: bool = False) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            import subprocess
            
            system_status = {
                "timestamp": datetime.now().isoformat(),
                "device_id": self.device_id
            }
            
            # 电池状态
            result = subprocess.run(
                f"adb {'-s ' + self.device_id if self.device_id else ''} shell dumpsys battery".split(),
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                battery_info = {}
                for line in result.stdout.split('\n'):
                    if 'level:' in line:
                        battery_info['level'] = line.split(':')[1].strip()
                    elif 'status:' in line:
                        battery_info['status'] = line.split(':')[1].strip()
                    elif 'temperature:' in line:
                        battery_info['temperature'] = line.split(':')[1].strip()
                
                system_status["battery"] = battery_info
            
            # 网络状态
            result = subprocess.run(
                f"adb {'-s ' + self.device_id if self.device_id else ''} shell dumpsys connectivity".split(),
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                network_connected = "CONNECTED" in result.stdout
                system_status["network"] = {"connected": network_connected}
            
            # 性能信息（如果需要）
            if include_performance:
                # 内存信息
                result = subprocess.run(
                    f"adb {'-s ' + self.device_id if self.device_id else ''} shell dumpsys meminfo".split(),
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    # 简化内存信息提取
                    memory_info = {"available": "unknown", "total": "unknown"}
                    system_status["memory"] = memory_info
            
            return system_status
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # === 私有辅助方法 ===
    
    def _infer_page_type(self, elements: List[Dict[str, Any]]) -> str:
        """推断页面类型"""
        element_texts = [elem.get("text", "").lower() for elem in elements]
        all_text = " ".join(element_texts)
        
        # 关键词映射
        if any(keyword in all_text for keyword in ["search", "搜索"]):
            return "search"
        elif any(keyword in all_text for keyword in ["login", "登录", "sign in"]):
            return "login"
        elif any(keyword in all_text for keyword in ["play", "播放", "pause", "暂停"]):
            return "playing"
        elif any(keyword in all_text for keyword in ["home", "首页", "主页"]):
            return "home"
        elif any(keyword in all_text for keyword in ["setting", "设置"]):
            return "settings"
        else:
            return "unknown"
    
    def _analyze_features(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析可用功能"""
        features = {
            "search_available": False,
            "login_available": False,
            "media_controls": False,
            "navigation_available": False
        }
        
        for element in elements:
            text = element.get("text", "").lower()
            resource_id = element.get("resource_id", "").lower()
            
            if "search" in text or "search" in resource_id:
                features["search_available"] = True
            if "login" in text or "sign" in text:
                features["login_available"] = True
            if "play" in text or "pause" in text:
                features["media_controls"] = True
            if "back" in text or "menu" in text or "home" in text:
                features["navigation_available"] = True
        
        return features
    
    def _find_playback_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """查找播放相关元素"""
        playback_elements = []
        
        for element in elements:
            text = element.get("text", "").lower()
            resource_id = element.get("resource_id", "").lower()
            
            if any(keyword in text or keyword in resource_id 
                   for keyword in ["play", "pause", "stop", "播放", "暂停", "停止"]):
                playback_elements.append({
                    "text": element.get("text", ""),
                    "resource_id": element.get("resource_id", ""),
                    "clickable": element.get("clickable", False)
                })
        
        return playback_elements
    
    def _detect_popups(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测弹窗"""
        popup_indicators = []
        
        for element in elements:
            text = element.get("text", "").lower()
            
            if any(keyword in text for keyword in ["确定", "取消", "ok", "cancel", "close", "关闭"]):
                popup_indicators.append({
                    "text": element.get("text", ""),
                    "type": "dialog_button"
                })
        
        return popup_indicators
    
    def _detect_error_states(self, elements: List[Dict[str, Any]]) -> List[str]:
        """检测错误状态"""
        error_indicators = []
        
        for element in elements:
            text = element.get("text", "").lower()
            
            if any(keyword in text for keyword in ["error", "错误", "failed", "失败", "网络异常"]):
                error_indicators.append(element.get("text", ""))
        
        return error_indicators
    
    def _detect_loading_states(self, elements: List[Dict[str, Any]]) -> List[str]:
        """检测加载状态"""
        loading_indicators = []
        
        for element in elements:
            text = element.get("text", "").lower()
            class_name = element.get("class_name", "").lower()
            
            if any(keyword in text for keyword in ["loading", "加载", "请稍等"]) or \
               "progress" in class_name:
                loading_indicators.append(element.get("text", "") or "Loading indicator")
        
        return loading_indicators