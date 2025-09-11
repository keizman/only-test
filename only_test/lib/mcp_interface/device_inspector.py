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
from lib.visual_recognition.visual_integration import IntegrationConfig
from lib.device_adapter import DeviceAdapter
from .mcp_server import mcp_tool
from lib.yaml_monitor import YamlMonitor
from lib.app_launcher import start_app as unified_start_app

# === 广告检测/关闭关键词（统一常量） ===
# 全部使用小写做比较，匹配时先对目标字符串 lower()
PRIORITY_CLOSE_IDS = {
    'mivclose', 'ivclose', 'close_ad', 'btn_close_ad',
    'close_ad_button', 'ad_close', 'close_btn'
}
EXCLUDED_CLOSE_IDS = {
    # 常见需要跳过的关闭按钮（例如优惠券）
    'imcouponclose1'
}
# GENERIC_CLOSE_KEYWORDS 说明：用于在三个字段中匹配通用“关闭/跳过”语义
# - resource-id（例如: com.xxx:id/ivClose；会在小写化后匹配 'close' 等子串）
# - text（控件显示文本，例如 “关闭”/“跳过”/"close"）
# - content-desc（无障碍描述，可能标注为 close/关闭 等）
# 检测逻辑会在 kw['rid']、kw['text']、kw['desc'] 三者上进行包含匹配
GENERIC_CLOSE_KEYWORDS = {'close', '关闭', '跳过', 'skip', 'x'}

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
            # 初始化视觉识别系统（带设备ID）
            self.visual_integration = VisualIntegration(IntegrationConfig(device_id=self.device_id))
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
    async def get_current_screen_info(self, include_elements: bool = False, clickable_only: bool = True, auto_close_ads: bool = True) -> Dict[str, Any]:
        """获取当前屏幕信息"""
        if not self._initialized:
            await self.initialize()
        
        try:
            screen_info = {
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "current_screen"
            }
            
            # 获取前台应用（避免主机侧管道与grep兼容问题，直接拉取并在本地解析）
            import subprocess, re
            adb_cmd = ["adb"] + (["-s", self.device_id] if self.device_id else []) + ["shell", "dumpsys", "window", "windows"]
            result = subprocess.run(adb_cmd, capture_output=True, text=True)
            current_pkg = "Unknown"
            if result.returncode == 0 and result.stdout:
                out = result.stdout
                # 查找 mCurrentFocus=Window{... u0 package/Activity}
                m = re.search(r"mCurrentFocus=Window\{[^}]*\s([\w\.]+)/", out)
                if not m:
                    # 备选: mFocusedApp=AppWindowToken{... package}
                    m = re.search(r"mFocusedApp=.*?\s([\w\.]+)\/[\w\.]+", out)
                if not m:
                    # 更宽松: 任意像包名的片段
                    m = re.search(r"([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+){1,})", out)
                if m:
                    current_pkg = m.group(1)
            screen_info["current_app"] = current_pkg
            
            # 在分析前，按默认参数尝试自动连续关闭广告（支持开关）
            if auto_close_ads:
                try:
                    _ = await self.close_ads(mode="continuous", consecutive_no_ad=3, max_duration=10.0)
                except Exception as _e:
                    logger.debug(f"预关闭广告失败（忽略）：{_e}")

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
            
            # 二次检测：基于当前元素再计算一次广告信息（记录purpose）
            all_elements = elements if not clickable_only else await get_all_elements(clickable_only=False)
            ads_info = await self._auto_handle_ads(all_elements)
            if ads_info.get("auto_close_attempts", 0) > 0:
                elements = await get_all_elements(clickable_only=clickable_only)

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
            
            # 附加广告信息
            if ads_info:
                screen_info["ads_info"] = ads_info
            return screen_info
            
        except Exception as e:
            logger.error(f"获取屏幕信息失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_device_info(self) -> Dict[str, Any]:
        """获取设备信息并自动处理广告 - 兼容性方法"""
        return await self.get_current_screen_info(include_elements=True, clickable_only=False)

    @mcp_tool(
        name="close_ads",
        description="关闭广告：single=单次尝试，continuous=连续尝试直到多次未检测到广告或超时",
        category="interaction",
        parameters={
            "mode": {"type": "string", "enum": ["single", "continuous"], "default": "continuous"},
            "consecutive_no_ad": {"type": "integer", "default": 3},
            "max_duration": {"type": "number", "default": 10.0}
        }
    )
    async def close_ads(self, mode: str = "continuous", consecutive_no_ad: int = 3, max_duration: float = 10.0) -> Dict[str, Any]:
        """对外提供的广告关闭入口。返回统计信息。"""
        if not self._initialized:
            await self.initialize()

        # 单次：调用一次自动关闭
        if mode == "single":
            elements = await get_all_elements(clickable_only=False)
            info = await self._auto_handle_ads(elements)
            return {"mode": mode, "rounds": 1, "last_ads_info": info}

        # 连续：直到连续N次未检测到广告或达到最大时长
        rounds = 0
        closes = 0
        no_ad_streak = 0
        import time as _t
        end_t = _t.time() + float(max_duration)
        last_info = {}
        while _t.time() < end_t:
            rounds += 1
            elements = await get_all_elements(clickable_only=False)
            info = await self._auto_handle_ads(elements)
            last_info = info

            if info.get("auto_closed"):
                closes += 1
                no_ad_streak = 0
            else:
                conf = float(info.get("confidence", 0.0) or 0.0)
                # 低置信度且未尝试关闭，认为当前轮无广告
                if conf < 0.2 and int(info.get("auto_close_attempts", 0)) == 0:
                    no_ad_streak += 1
                else:
                    no_ad_streak = 0

            if no_ad_streak >= max(1, int(consecutive_no_ad)):
                break

            await asyncio.sleep(0.2)

        return {
            "mode": mode,
            "rounds": rounds,
            "close_count": closes,
            "no_ad_streak": no_ad_streak,
            "last_ads_info": last_info,
            "timed_out": (_t.time() >= end_t)
        }

    @mcp_tool(
        name="start_app",
        description="启动应用：支持 app_id 或 package_name；若配置了 ui_activity 则优先使用该方式",
        category="app_control",
        parameters={
            "application": {"type": "string", "description": "app_id 或 package_name"},
            "force_restart": {"type": "boolean", "default": True},
        }
    )
    async def start_app(self, application: str, force_restart: bool = True) -> Dict[str, Any]:
        """统一的启动应用入口（读取 main.yaml，优先使用 ui_activity）。"""
        if not self._initialized:
            await self.initialize()
        try:
            # 通过 YAML 解析，支持 app_id / package
            ym = YamlMonitor()
            pkg = ym.get_package_name(application) or application
            result = unified_start_app(application=pkg, device_id=self.device_id, force_restart=force_restart)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    # === 广告自动处理相关 ===
    def _elem_center(self, bounds: list) -> tuple:
        try:
            left, top, right, bottom = bounds
            return ((left + right) / 2.0, (top + bottom) / 2.0)
        except Exception:
            return (0.5, 0.5)

    async def _auto_handle_ads(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检测广告并尝试自动关闭。最多尝试3次。

        置信度计算因子：
        - 元素数量偏少（<=20）: +0.25
        - 存在含 'ad/ads/广告' 的元素: +0.35
        - 存在含 'close/关闭/跳过/ivClose/mIvClose' 的元素: +0.25
        - 特征 close id（ivClose/mIvClose）且可点击: +0.30
        - 'ad' 与 'close' 的中心距离较近（<0.2 相对阈值）: +0.20
        """
        info = {"auto_close_attempts": 0, "auto_closed": False, "confidence": 0.0, "warnings": []}
        if not elements:
            return info

        def keywords(elem: Dict[str, Any]) -> Dict[str, str]:
            return {
                'text': (elem.get('text') or '').lower(),
                'rid': (elem.get('resource_id') or '').lower(),
                'desc': (elem.get('content_desc') or '').lower(),
                'cls': (elem.get('class_name') or '').lower(),
            }

        def detect_conf(elements: List[Dict[str, Any]]):
            n = len(elements)
            score = 0.0
            ad_elems = []
            close_elems = []
            logger.debug(f"🔍 检测广告置信度 - 元素数量: {n}")
            # 使用统一常量
            
            for e in elements:
                kw = keywords(e)
                
                # 首先检查是否在排除列表中
                is_excluded = any(excluded_id in kw['rid'] for excluded_id in EXCLUDED_CLOSE_IDS)
                if is_excluded:
                    logger.info(f"跳过排除列表中的广告按钮: {e.get('resource_id')}")
                    continue
                
                if any(k in kw['text'] or k in kw['rid'] for k in ['ad', 'ads', '广告', 'sponsor', 'upgrade', 'version', 'update', '升级', '更新']):
                    ad_elems.append(e)
                    logger.debug(f"  📢 发现广告元素: {e.get('text', '')} | {e.get('resource_id', '')}")
                
                # 优先检测强制广告关闭按钮
                force_close = False
                for ad_id in PRIORITY_CLOSE_IDS:
                    if ad_id in kw['rid']:
                        close_elems.append(e)
                        force_close = True
                        break
                
                # 常规关闭按钮检测
                if not force_close and (
                    any(k in kw['text'] or k in kw['rid'] or k in kw['desc'] for k in GENERIC_CLOSE_KEYWORDS)
                ):
                    close_elems.append(e)
                    logger.debug(f"  🔘 发现关闭元素: {e.get('text', '')} | {e.get('resource_id', '')}")
            if n <= 20:
                score += 0.25
            if ad_elems:
                score += 0.35
            if close_elems:
                score += 0.25
            if any('ivclose' in keywords(e)['rid'] or 'mivclose' in keywords(e)['rid'] for e in close_elems) and any(e.get('clickable') for e in close_elems):
                score += 0.30
            # 距离
            if ad_elems and close_elems:
                try:
                    import math
                    dmin = 1.0
                    for a in ad_elems:
                        for c in close_elems:
                            ca = self._elem_center(a.get('bounds', []))
                            cc = self._elem_center(c.get('bounds', []))
                            # 归一化假设：bounds已归一到[0,1]，否则以相对量衡量
                            dx = (ca[0] - cc[0])
                            dy = (ca[1] - cc[1])
                            dist = math.hypot(dx, dy)
                            dmin = min(dmin, dist)
                    if dmin < 0.2:
                        score += 0.20
                except Exception:
                    pass
            logger.debug(f"  📊 置信度计算: 总分={score:.2f}, 广告元素={len(ad_elems)}, 关闭元素={len(close_elems)}")
            return min(1.0, score), ad_elems, close_elems

        async def try_close(close_elems: List[Dict[str, Any]]) -> bool:
            # 使用poco直接关闭广告 - 采用正确的 resourceId 关键字参数
            try:
                # 使用本地自定义的Poco库
                from ..poco_utils import get_android_poco
                poco = get_android_poco()

                success_count = 0

                # 遍历所有关闭元素，使用poco直接点击
                for e in close_elems:
                    resource_id = e.get('resource_id', '')
                    text_val = (e.get('text') or '').strip()
                    if not resource_id and not text_val:
                        continue

                    rid_lower = (resource_id or '').lower()

                    # 检查是否在排除列表中
                    is_excluded = any(excluded_id in rid_lower for excluded_id in EXCLUDED_CLOSE_IDS)
                    if is_excluded:
                        logger.info(f"跳过排除列表中的广告按钮: {resource_id}")
                        continue

                    # 检查是否是优先级广告按钮或一般关闭按钮
                    should_click = any(ad_id in rid_lower for ad_id in PRIORITY_CLOSE_IDS) or \
                                   any(keyword in rid_lower for keyword in GENERIC_CLOSE_KEYWORDS) or \
                                   any(keyword in (text_val or '').lower() for keyword in GENERIC_CLOSE_KEYWORDS)

                    if should_click:
                        try:
                            logger.info(f"尝试使用poco点击广告关闭按钮: {resource_id or text_val}")

                            # 1) 优先按 resourceId 精准定位（正确写法：resourceId=...）
                            obj = None
                            if resource_id:
                                obj = poco(resourceId=resource_id)
                                if not obj.exists():
                                    # 兼容某些驱动，尝试 name=resource_id
                                    obj = poco(name=resource_id)

                            # 2) 退而求其次按文本定位
                            if (not obj or not obj.exists()) and text_val:
                                obj = poco(text=text_val)

                            # 3) 再次兜底，尝试通过后缀匹配ID（部分ROM会省略包名前缀）
                            if (not obj or not obj.exists()) and resource_id and '/' in resource_id:
                                rid_suffix = resource_id.split('/')[-1]
                                try:
                                    obj = poco(resourceIdMatches=f".*:id/{rid_suffix}$")
                                except Exception:
                                    # 某些实现不支持正则，退化为 name 后缀判断
                                    obj = poco(name=rid_suffix)

                            if obj and obj.exists():
                                try:
                                    # 等待出现后点击，提升稳定性
                                    try:
                                        obj.wait_for_appearance(timeout=2.0)
                                    except Exception:
                                        pass
                                    obj.click()
                                    success_count += 1
                                    logger.info(f"成功点击广告关闭按钮: {resource_id or text_val}")

                                    # 点击后稍等一下让界面更新
                                    try:
                                        import asyncio as _aio
                                        await _aio.sleep(0.5)
                                    except Exception:
                                        pass
                                    continue
                                except Exception as click_error:
                                    logger.warning(f"poco点击失败 {resource_id or text_val}: {click_error}")
                                    # 继续尝试下一个候选
                                    continue

                        except Exception as e:
                            logger.warning(f"poco点击处理异常 {resource_id or text_val}: {e}")
                            # 失败了也不要紧，继续尝试其他按钮
                            continue

                # 若poco可用但未成功，继续走坐标兜底
                if success_count > 0:
                    return True
                else:
                    logger.info("poco点击未奏效，尝试坐标兜底")
                    # fall through to coordinate fallback
            except ImportError as import_error:
                logger.error(f"poco库导入失败，回退到坐标方式: {import_error}")
            except RuntimeError as device_error:
                if "设备连接失败" in str(device_error) or "Failed to connect" in str(device_error):
                    logger.error(f"Android设备未连接，回退到坐标方式: {device_error}")
                else:
                    logger.error(f"poco运行时错误，回退到坐标方式: {device_error}")
            except Exception as e:
                logger.error(f"poco广告关闭失败，回退到坐标方式: {e}")

            # === 兜底：坐标点击关闭 ===
            try:
                import subprocess, time

                # 获取屏幕尺寸
                def _screen_size():
                    out = subprocess.run(
                        f"adb {'-s ' + self.device_id if self.device_id else ''} shell wm size".split(),
                        capture_output=True, text=True
                    )
                    if out.returncode == 0 and 'Physical size:' in out.stdout:
                        sz = out.stdout.split('Physical size:')[-1].strip().split('\n')[0].strip()
                        w, h = sz.split('x')
                        return int(w), int(h)
                    return 1080, 1920

                sw, sh = _screen_size()

                # 优先点击优先级高的关闭元素
                tried = 0
                for e in close_elems:
                    b = e.get('bounds') or []
                    if not (isinstance(b, (list, tuple)) and len(b) == 4):
                        continue
                    # 归一化->像素
                    if max(b) <= 1.0:
                        left, top, right, bottom = int(b[0] * sw), int(b[1] * sh), int(b[2] * sw), int(b[3] * sh)
                    else:
                        left, top, right, bottom = map(int, b)
                    cx, cy = (left + right) // 2, (top + bottom) // 2
                    # 轻微扰动多次点击
                    for dx, dy in [(0,0), (8,0), (-8,0), (0,8), (0,-8)]:
                        cmd = f"adb {'-s ' + self.device_id + ' ' if self.device_id else ''}shell input tap {cx+dx} {cy+dy}"
                        subprocess.run(cmd.split(), capture_output=True, text=True)
                        time.sleep(0.25)
                    tried += 1
                    # 点击一次高优先级元素后先退出循环，交由外层再次评估置信度
                    break

                return tried > 0
            except Exception as e:
                logger.error(f"坐标兜底失败: {e}")
                return False

        # 自动关闭循环
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            conf, ad_es, close_es = detect_conf(elements)
            info['confidence'] = conf
            # 如果有广告关闭按钮，直接尝试点击，无视置信度
            # 特别是对于已知的广告关闭按钮ID，但排除不应该关闭的按钮
            excluded_ids = EXCLUDED_CLOSE_IDS
            priority_ids = PRIORITY_CLOSE_IDS
            
            has_priority_close = any(
                any(ad_id in (e.get('resource_id', '')).lower() for ad_id in priority_ids) and
                not any(excluded_id in (e.get('resource_id', '')).lower() for excluded_id in excluded_ids)
                for e in close_es
            )
            
            if (has_priority_close or conf >= 0.50) and close_es:
                clicked = await try_close(close_es)
                info['auto_close_attempts'] += 1
                if not clicked:
                    break
                # 刷新元素以便下一轮判断  
                elements = await get_all_elements(clickable_only=False)
                # 若置信度下降则退出
                conf2, _, _ = detect_conf(elements)
                if conf2 < 0.70:
                    info['auto_closed'] = True
                    break
            else:
                break

        # 若多次后仍>=0.70，发出警告
        conf_final, _, _ = detect_conf(elements)
        info['confidence'] = conf_final
        if conf_final >= 0.70 and not info.get('auto_closed', False):
            info['warnings'].append('可能存在未关闭的广告')
        return info

    @mcp_tool(
        name="perform_ui_action",
        description="执行UI动作（click/input/swipe），基于选择器或坐标并返回结果",
        category="interaction",
        parameters={
            "action": {"type": "string", "enum": ["click", "input", "swipe"], "description": "动作类型"},
            "target": {"type": "object", "description": "目标选择器，支持 priority_selectors/resource_id/text/content_desc/bounds_px 或 swipe.start_px/end_px"},
            "data": {"type": "string", "description": "输入文本（当 action=input 时）", "default": ""},
            "wait_after": {"type": "number", "description": "动作后等待秒数", "default": 0.5}
        }
    )
    async def perform_ui_action(self, action: str, target: Dict[str, Any], data: str = "", wait_after: float = 0.5) -> Dict[str, Any]:
        """执行单步UI动作。优先 resource_id > content_desc > text；若给定 bounds_px 则直接坐标点击。"""
        if not self._initialized:
            await self.initialize()
        import subprocess, time
        used_selector = None
        try:
            # 解出选择器
            def pick_selector(t: Dict[str, Any]):
                if not isinstance(t, dict):
                    return None, None
                # 直接键
                if t.get('resource_id'):
                    return 'resource_id', t['resource_id']
                if t.get('content_desc'):
                    return 'content_desc', t['content_desc']
                if t.get('text'):
                    return 'text', t['text']
                # 列表
                sels = t.get('priority_selectors') or t.get('selectors') or []
                for s in sels:
                    if s.get('resource_id'):
                        return 'resource_id', s['resource_id']
                for s in sels:
                    if s.get('content_desc'):
                        return 'content_desc', s['content_desc']
                for s in sels:
                    if s.get('text'):
                        return 'text', s['text']
                return None, None

            # 坐标点击兜底
            bounds_px = target.get('bounds_px') if isinstance(target, dict) else None
            if action == 'click' and bounds_px and isinstance(bounds_px, (list, tuple)) and len(bounds_px) == 4:
                x = (bounds_px[0] + bounds_px[2]) // 2
                y = (bounds_px[1] + bounds_px[3]) // 2
                cmd = f"adb {'-s ' + self.device_id + ' ' if self.device_id else ''}shell input tap {x} {y}"
                subprocess.run(cmd.split(), capture_output=True, text=True)
                time.sleep(max(0.0, float(wait_after)))
                return {"success": True, "used": {"type": "bounds_px", "value": bounds_px}}

            sel_type, sel_value = pick_selector(target)
            used_selector = {"type": sel_type, "value": sel_value}

            # 通过 ElementRecognizer 执行动作
            if not self.visual_integration:
                self.visual_integration = VisualIntegration(IntegrationConfig(device_id=self.device_id))
                await self.visual_integration.initialize()

            if action == 'click':
                ok = await self.visual_integration.find_and_tap(
                    text=sel_value if sel_type == 'text' else None,
                    resource_id=sel_value if sel_type == 'resource_id' else None,
                    content_desc=sel_value if sel_type == 'content_desc' else None,
                    timeout=10.0
                )
                time.sleep(max(0.0, float(wait_after)))
                return {"success": bool(ok), "used": used_selector}
            elif action == 'input':
                # 聚焦输入框
                _ = await self.visual_integration.find_and_tap(
                    text=sel_value if sel_type == 'text' else None,
                    resource_id=sel_value if sel_type == 'resource_id' else None,
                    content_desc=sel_value if sel_type == 'content_desc' else None,
                    timeout=10.0
                )
                # ADB 输入（空格替换为% s以兼容input）
                safe = (data or '').replace(' ', '%s')
                cmd = f"adb {'-s ' + self.device_id + ' ' if self.device_id else ''}shell input text {safe}"
                subprocess.run(cmd.split(), capture_output=True, text=True)
                time.sleep(max(0.0, float(wait_after)))
                return {"success": True, "used": used_selector}
            elif action == 'swipe':
                # 支持 target.swipe.start_px/end_px 或通过 bounds_px 推导方向
                swipe = target.get('swipe', {}) if isinstance(target, dict) else {}
                def _screen_size():
                    import subprocess
                    out = subprocess.run(f"adb {'-s ' + self.device_id if self.device_id else ''} shell wm size".split(), capture_output=True, text=True)
                    if out.returncode == 0 and 'Physical size:' in out.stdout:
                        sz = out.stdout.split('Physical size:')[-1].strip().split('\n')[0].strip()
                        w, h = sz.split('x')
                        return int(w), int(h)
                    return 1080, 1920
                w, h = _screen_size()
                start_px = swipe.get('start_px')
                end_px = swipe.get('end_px')
                if not (start_px and end_px):
                    # 若缺失，则尝试通过 bounds_px 生成从元素中心向上滑动
                    bp = target.get('bounds_px')
                    if isinstance(bp, list) and len(bp) == 4:
                        cx = int((bp[0] + bp[2]) / 2)
                        cy = int((bp[1] + bp[3]) / 2)
                        start_px = [cx, cy]
                        end_px = [cx, max(0, cy - int(0.3 * h))]
                if start_px and end_px:
                    dur = int((swipe.get('duration_ms') or 300))
                    cmd = f"adb {'-s ' + self.device_id + ' ' if self.device_id else ''}shell input swipe {int(start_px[0])} {int(start_px[1])} {int(end_px[0])} {int(end_px[1])} {dur}"
                    subprocess.run(cmd.split(), capture_output=True, text=True)
                    time.sleep(max(0.0, float(wait_after)))
                    return {"success": True, "used": {"type": "swipe", "start_px": start_px, "end_px": end_px, "duration_ms": dur}}
                return {"success": False, "error": "invalid swipe parameters"}
            else:
                return {"success": False, "error": f"unsupported action: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e), "used": used_selector}

    @mcp_tool(
        name="perform_and_verify",
        description="执行UI动作并前后对比屏幕元素签名/等待条件，返回是否发生变化",
        category="interaction",
        parameters={
            "action": {"type": "string", "enum": ["click", "input", "swipe"], "description": "动作类型"},
            "target": {"type": "object", "description": "目标选择器，支持 priority_selectors/resource_id/text/content_desc/bounds_px 或 swipe.start_px/end_px"},
            "data": {"type": "string", "description": "输入文本（可选）", "default": ""},
            "wait_after": {"type": "number", "description": "动作后等待秒数", "default": 0.8},
            "wait_for": {"type": "object", "description": "等待条件 {type: appearance|disappearance, selectors: [...], timeout: 10}", "default": {}}
        }
    )
    async def perform_and_verify(self, action: str, target: Dict[str, Any], data: str = "", wait_after: float = 0.8, wait_for: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行动作并通过前后两次 get_current_screen_info 对比是否变化。"""
        from hashlib import md5
        import json as _json
        pre = await self.get_current_screen_info(include_elements=True, clickable_only=True)
        r = await self.perform_ui_action(action=action, target=target, data=data, wait_after=wait_after)
        post = await self.get_current_screen_info(include_elements=True, clickable_only=True)
        # Optional wait condition
        waited = None
        if isinstance(wait_for, dict) and wait_for.get('type') in ('appearance', 'disappearance'):
            import time as _t
            end_t = _t.time() + float(wait_for.get('timeout', 10))
            sels = wait_for.get('selectors') or []
            def _exists(el_list):
                for s in sels:
                    rid = s.get('resource_id'); txt = s.get('text'); desc = s.get('content_desc') or s.get('desc')
                    for ee in el_list:
                        if rid and ee.get('resource_id') == rid:
                            return True
                        if txt and ee.get('text') == txt:
                            return True
                        if desc and ee.get('content_desc') == desc:
                            return True
                return False
            desired = (wait_for['type'] == 'appearance')
            while _t.time() < end_t:
                cur = await self.get_current_screen_info(include_elements=True, clickable_only=True)
                ex = _exists(cur.get('elements', []))
                if (ex and desired) or ((not ex) and (not desired)):
                    waited = True
                    post = cur
                    break
            if waited is None:
                waited = False
        def signature(d: Dict[str, Any]) -> str:
            els = d.get('elements', []) if isinstance(d, dict) else []
            sig = [f"{e.get('resource_id','')}|{e.get('text','')}|{e.get('clickable',False)}" for e in els]
            payload = "|".join(sig) + f";cnt={d.get('total_elements',0)}"
            return md5(payload.encode('utf-8', errors='ignore')).hexdigest()
        pre_sig = signature(pre)
        post_sig = signature(post)
        changed = (pre_sig != post_sig)
        return {
            "success": r.get("success", False),
            "used": r.get("used"),
            "changed": changed,
            "wait_result": waited,
            "pre_signature": pre_sig,
            "post_signature": post_sig,
            "pre": pre,
            "post": post
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

