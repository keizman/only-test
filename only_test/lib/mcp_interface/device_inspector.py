#!/usr/bin/env python3
"""
Only-Test Device Inspector
==========================

为LLM提供设备探测能力
让AI能够获取实时设备信息、分析界面状态
"""

import asyncio
import asyncio.subprocess as aio_subprocess
import json
import logging
from typing import Dict, List, Any, Optional, Iterable, Tuple
from datetime import datetime
import sys
import os
import subprocess
import re
import time
import xml.etree.ElementTree as ET

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# XML-only mode: remove visual_recognition dependency
# Provide local XML extraction helpers and playback detection
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
    # 注意：这些ID应该使用小写，因为代码中会转换为小写进行匹配
    'imcouponclose', 'mivclosenotice', "mtvnotice"
}
# GENERIC_CLOSE_KEYWORDS 说明：用于在三个字段中匹配通用“关闭/跳过”语义
# - resource-id（例如: com.xxx:id/ivClose；会在小写化后匹配 'close' 等子串）
# - text（控件显示文本，例如 “关闭”/“跳过”/"close"）
# - content-desc（无障碍描述，可能标注为 close/关闭 等）
# 检测逻辑会在 kw['rid']、kw['text']、kw['desc'] 三者上进行包含匹配
GENERIC_CLOSE_KEYWORDS = {'close', '关闭', '跳过', 'skip', 'x', 'fechar', 'pular'}

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
        self.device_adapter: Optional[DeviceAdapter] = None
        self._initialized = False
        # 目标应用包名（用于限制操作范围）
        self.target_app_package: Optional[str] = None
        # 允许操作的系统包白名单（权限对话框等）
        self.allowed_external_packages = {
            'android',
            'com.android.permissioncontroller',
            'com.google.android.permissioncontroller',
            'com.android.packageinstaller',
            'com.android.systemui'
        }
        # MCP 屏幕分析轮次计数，用于限制自动关广告次数
        self._analysis_round: int = 0
        # 屏幕尺寸缓存
        self._screen_size_cache: Optional[tuple[int,int]] = None
        # 设备配置缓存（来自 main.yaml）
        self._device_profile: Optional[Dict[str, Any]] = None
        # 最近一次UI快照（供快速检测播放控件）
        self._ui_snapshot_cache: Dict[str, Any] = {"xml": "", "lower": "", "ts": 0.0}
        # 最近一次播放控件检测结果
        self._wake_keyword_cache: Dict[str, Any] = {"keywords": tuple(), "visible": False, "ts": 0.0}
        # 自动关广告最大轮次（可通过 get_current_screen_info 的 auto_close_limit 覆盖）
        self.auto_close_ads_limit: int = 3
        # 从环境变量读取全局覆盖（每会话），例如 ONLY_TEST_AUTO_CLOSE_LIMIT=2
        try:
            env_limit = os.getenv("ONLY_TEST_AUTO_CLOSE_LIMIT")
            if env_limit is not None and str(env_limit).strip() != "":
                self.auto_close_ads_limit = int(env_limit)
        except Exception:
            pass

        # 预读取 main.yaml 中的设备配置
        self._device_profile = self._load_device_profile()
        if self._device_profile:
            logger.info(
                "设备配置绑定: device_key=%s serial=%s resolution=%s",
                self._device_profile.get("device_key"),
                self._device_profile.get("serial"),
                self._device_profile.get("resolution"),
            )

        logger.info(f"设备探测器初始化 - 设备: {device_id or 'default'}")
    
    # === XML-only 辅助方法 ===
    def _adb_prefix(self) -> list:
        return ["adb"] + (["-s", self.device_id] if self.device_id else [])

    def _get_screen_size(self) -> tuple[int, int]:
        if self._screen_size_cache:
            return self._screen_size_cache
        try:
            out = subprocess.run(self._adb_prefix() + ["shell", "wm", "size"], capture_output=True, text=True)
            if out.returncode == 0 and "Physical size:" in out.stdout:
                sz = out.stdout.split("Physical size:")[-1].strip().split("\n")[0].strip()
                w, h = sz.split("x")
                self._screen_size_cache = (int(w), int(h))
                return self._screen_size_cache
        except Exception:
            pass
        self._screen_size_cache = (1080, 1920)
        return self._screen_size_cache

    @staticmethod
    def _normalize_serial(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return text.split(':')[0]

    @staticmethod
    def _parse_resolution(value: Any) -> Optional[tuple[int, int]]:
        if not value:
            return None
        text = str(value).lower().replace('×', 'x')
        text = text.replace(' ', '')
        if 'x' not in text:
            return None
        parts = text.split('x', 1)
        try:
            w = int(parts[0])
            h = int(parts[1])
            if w > 0 and h > 0:
                return w, h
        except Exception:
            return None
        return None

    def _load_device_profile(self) -> Optional[Dict[str, Any]]:
        try:
            from only_test.lib.config_manager import ConfigManager

            cfg = ConfigManager().get_config()
            devices_cfg = cfg.get('devices') or {}
            if not devices_cfg:
                return None

            normalized_target = self._normalize_serial(self.device_id)
            chosen_key = None
            chosen_serial = None

            if normalized_target:
                for dev_key, dev_cfg in devices_cfg.items():
                    conn = (dev_cfg or {}).get('connection', {}) or {}
                    candidate = self._normalize_serial(conn.get('adb_serial'))
                    if candidate and candidate == normalized_target:
                        chosen_key = dev_key
                        chosen_serial = conn.get('adb_serial')
                        break

            if chosen_key is None and len(devices_cfg) == 1:
                chosen_key = next(iter(devices_cfg))
                chosen_serial = (devices_cfg[chosen_key] or {}).get('connection', {}).get('adb_serial')

            if chosen_key is None:
                return None

            dev_cfg = devices_cfg.get(chosen_key) or {}
            screen_cfg = (dev_cfg.get('screen_info') or {}) if isinstance(dev_cfg, dict) else {}
            resolution_value = screen_cfg.get('override_resolution') or screen_cfg.get('resolution')
            resolution_tuple = self._parse_resolution(resolution_value)

            return {
                'device_key': chosen_key,
                'serial': chosen_serial,
                'resolution': resolution_tuple,
                'raw_resolution': resolution_value,
            }
        except Exception as exc:
            logger.debug(f"设备配置加载失败: {exc}")
            return None

    async def _dump_current_xml(self) -> str:
        """获取当前UI层级XML，确保每次获取最新状态。"""
        # 首先清理可能存在的旧文件
        try:
            subprocess.run(self._adb_prefix() + ["shell", "rm", "-f", "/sdcard/window_dump*.xml"],
                         capture_output=True, text=True, timeout=5)
        except Exception:
            pass

        # 方法1: 直接使用 uiautomator2 库 (最可靠，无缓存)
        try:
            import uiautomator2 as u2  # type: ignore
            ui = u2.connect(self.device_id) if self.device_id else u2.connect()

            if ui:
                # 强制刷新设备状态，确保获取最新界面
                try:
                    ui.app_current()  # 触发状态刷新
                    import time
                    time.sleep(0.1)
                except Exception:
                    pass

                xml = ui.dump_hierarchy()
                if xml and "<hierarchy" in xml:
                    logger.debug(f"uiautomator2获取XML成功，长度: {len(xml)}")
                    return xml
                else:
                    logger.warning("uiautomator2返回空XML或格式错误")
            else:
                logger.warning("uiautomator2连接失败")
        except Exception as e:
            logger.warning(f"uiautomator2方法失败: {e}")

        # 方法2: 使用带时间戳的唯一文件名避免缓存
        try:
            import time
            timestamp = int(time.time() * 1000000)  # 微秒时间戳确保唯一性
            unique_filename = f"/sdcard/ui_dump_{timestamp}.xml"

            # dump到唯一文件名
            dump_result = subprocess.run(
                self._adb_prefix() + ["shell", "uiautomator", "dump", unique_filename],
                capture_output=True, text=True, timeout=15
            )

            if dump_result.returncode == 0:
                time.sleep(0.3)  # 等待文件写入完成

                # 验证文件存在并读取
                check_result = subprocess.run(
                    self._adb_prefix() + ["shell", "test", "-f", unique_filename],
                    capture_output=True, text=True, timeout=5
                )

                if check_result.returncode == 0:
                    out = subprocess.run(
                        self._adb_prefix() + ["shell", "cat", unique_filename],
                        capture_output=True, text=True, timeout=15
                    )

                    # 立即清理临时文件
                    try:
                        subprocess.run(self._adb_prefix() + ["shell", "rm", "-f", unique_filename],
                                     capture_output=True, text=True, timeout=5)
                    except Exception:
                        pass

                    if out.returncode == 0 and out.stdout.strip():
                        content = out.stdout.strip()
                        if "<hierarchy" in content:
                            logger.debug("文件dump方法获取XML成功")
                            return content
                        else:
                            logger.warning("文件内容格式错误，未找到hierarchy标签")
                    else:
                        logger.warning("文件内容为空或读取失败")
                else:
                    logger.warning("dump文件未创建成功")
            else:
                logger.warning(f"dump到文件失败: {dump_result.stderr}")
        except Exception as e:
            logger.warning(f"文件dump方法异常: {e}")

        # 方法3: exec-out 方法作为最后备选
        try:
            for target in ["/dev/fd/1", "/dev/stdout"]:
                try:
                    cmd = self._adb_prefix() + ["exec-out", "uiautomator", "dump", target]
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)

                    if stderr:
                        stderr_text = stderr.decode(errors='ignore')
                        # 如果是"Killed"错误，尝试下一个目标
                        if "Killed" in stderr_text:
                            continue

                    if proc.returncode == 0 and stdout:
                        txt = stdout.decode(errors='ignore')

                        # 输出中可能包含路径与提示，提取 <hierarchy ..> 起始
                        idx = txt.find("<hierarchy")
                        if idx >= 0:
                            xml_content = txt[idx:]

                            # 查找XML结束标记，清理垃圾内容
                            end_idx = xml_content.find("</hierarchy>")
                            if end_idx >= 0:
                                xml_content = xml_content[:end_idx + len("</hierarchy>")]
                                logger.debug(f"exec-out方法获取XML成功，长度: {len(xml_content)}")
                                return xml_content
                            else:
                                logger.warning("未找到</hierarchy>结束标签")
                        else:
                            logger.warning("未找到<hierarchy标签")
                except Exception as target_e:
                    logger.warning(f"exec-out({target})方法失败: {target_e}")
                    continue
        except Exception as e:
            logger.error(f"exec-out方法异常: {e}")

        logger.error("所有XML获取方法均失败，返回空字符串")
        return ""

    def _parse_bounds(self, s: str) -> tuple[int,int,int,int]:
        try:
            s = s.replace('[', '').replace(']', ',')
            xs = [int(x) for x in s.split(',') if x.strip()]
            if len(xs) >= 4:
                return xs[0], xs[1], xs[2], xs[3]
        except Exception:
            pass
        return 0,0,0,0

    def _xml_to_elements(self, xml_str: str) -> list[dict]:
        if not xml_str:
            logger.warning("XML字符串为空，无法解析")
            return []

        w, h = self._get_screen_size()

        try:
            root = ET.fromstring(xml_str)
        except Exception as e:
            logger.error(f"XML解析失败: {e}")
            logger.debug(f"XML前100字符: {xml_str[:100]}")
            return []
        elements: list[dict] = []
        def walk(node):
            if node is None:
                return
            if node.tag != 'hierarchy':
                attrib = node.attrib
                bounds_str = attrib.get('bounds', '[0,0][0,0]')
                x1, y1, x2, y2 = self._parse_bounds(bounds_str)
                # 归一化
                if w > 0 and h > 0:
                    nb = [x1/w, y1/h, x2/w, y2/h]
                else:
                    nb = [0,0,0,0]
                text = attrib.get('text', '')
                resource_id = attrib.get('resource-id', '')
                content_desc = attrib.get('content-desc', '')
                class_name = attrib.get('class', '')
                package = attrib.get('package', '')
                visible = (attrib.get('visible', 'true').lower() == 'true')
                is_clickable = (
                    (attrib.get('clickable', 'false').lower() == 'true') or
                    (attrib.get('long-clickable', 'false').lower() == 'true') or
                    (attrib.get('touchable', 'false').lower() == 'true')
                ) and visible and (attrib.get('enabled', 'true').lower() == 'true')
                elements.append({
                    "uuid": f"xml_{len(elements)}",
                    "element_type": "xml",
                    "name": resource_id or (text or class_name),
                    "text": text,
                    "package": package,
                    "resource_id": resource_id,
                    "content_desc": content_desc,
                    "class_name": class_name,
                    "clickable": bool(is_clickable),
                    "bounds": nb,
                    "source": "xml_extractor"
                })
            for c in list(node):
                walk(c)
        walk(root)
        return elements

    async def _get_elements_xml(self, clickable_only: bool = True) -> list[dict]:
        xml_str = await self._dump_current_xml()

        if not xml_str:
            logger.warning("XML字符串为空，无法解析元素")
            return []

        elems = self._xml_to_elements(xml_str)
        logger.debug(f"解析得到 {len(elems)} 个原始元素")

        if clickable_only:
            clickable_elems = [e for e in elems if e.get('clickable')]
            logger.debug(f"过滤后得到 {len(clickable_elems)} 个可点击元素")
            return clickable_elems

        return elems

    async def _is_media_playing(self) -> bool:
        # 简化策略：检测 audio_flinger 中是否存在 Standby: no
        try:
            proc = await asyncio.create_subprocess_exec(
                *self._adb_prefix(), "shell", "dumpsys", "media.audio_flinger",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0 and stdout:
                txt = stdout.decode(errors='ignore').lower()
                # 任意输出包含 "standby: no" 视为音频活动
                if "standby: no" in txt:
                    return True
        except Exception:
            pass
        # 备选：检查 media_session 状态（存在正在播放会话）
        try:
            proc2 = await asyncio.create_subprocess_exec(
                *self._adb_prefix(), "shell", "dumpsys", "media_session",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout2, _ = await proc2.communicate()
            if proc2.returncode == 0 and stdout2:
                if b"state=PlaybackState" in stdout2 or b"state=3" in stdout2:
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def _normalize_keyword(keyword: Any) -> str:
        try:
            text = str(keyword)
        except Exception:
            return ""
        text = text.strip()
        return text.casefold() if text else ""

    def _normalize_keywords(self, keywords: Iterable[str]) -> Tuple[str, ...]:
        normalized: List[str] = []
        for kw in keywords or []:
            norm = self._normalize_keyword(kw)
            if norm:
                normalized.append(norm)
        if not normalized:
            return tuple()
        return tuple(sorted(set(normalized)))

    def _invalidate_ui_snapshot_cache(self) -> None:
        self._ui_snapshot_cache = {"xml": "", "lower": "", "ts": 0.0}
        self._wake_keyword_cache = {"keywords": tuple(), "visible": False, "ts": 0.0}

    async def _get_ui_snapshot(self, max_age: float = 0.0) -> str:
        if not self._initialized:
            await self.initialize()
        reuse_window = max(0.0, float(max_age))
        cached_xml = self._ui_snapshot_cache.get("xml") or ""
        now = time.time()
        if cached_xml and reuse_window > 0.0:
            cached_ts = float(self._ui_snapshot_cache.get("ts", 0.0))
            if (now - cached_ts) <= reuse_window:
                return cached_xml
        xml = await self._dump_current_xml()
        lower_xml = xml.lower() if isinstance(xml, str) else ""
        self._ui_snapshot_cache = {"xml": xml, "lower": lower_xml, "ts": now}
        return xml

    async def _has_wake_keywords(self, wake_keywords: Iterable[str], max_age: float = 0.5) -> bool:
        normalized = self._normalize_keywords(wake_keywords)
        if not normalized:
            return False
        reuse_window = max(0.0, float(max_age))
        now = time.time()
        cached_keywords = self._wake_keyword_cache.get("keywords", tuple())
        if cached_keywords == normalized and reuse_window > 0.0:
            cached_ts = float(self._wake_keyword_cache.get("ts", 0.0))
            if (now - cached_ts) <= reuse_window:
                return bool(self._wake_keyword_cache.get("visible", False))
        await self._get_ui_snapshot(max_age)
        lower_xml = self._ui_snapshot_cache.get("lower", "") or ""
        visible = all(kw in lower_xml for kw in normalized)
        logger.debug(
            "播放控件关键词检测: keywords=%s visible=%s",
            list(normalized),
            visible,
        )
        self._wake_keyword_cache = {"keywords": normalized, "visible": visible, "ts": now}
        return visible

    async def _ensure_controls_visible_once(
        self,
        wake_keywords: Optional[Iterable[str]] = None,
        tap_y_norm: float = 0.15,
        post_tap_sleep_ms: int = 250,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "wake_attempted": False,
            "tap_performed": False,
            "controls_visible": False,
        }

        try:
            if not self._initialized:
                await self.initialize()

            normalized = self._normalize_keywords(wake_keywords or [])

            # 若控件已可见，直接返回
            if normalized and await self._has_wake_keywords(normalized, max_age=0.3):
                logger.info(
                    "播放控件唤起: 关键字已可见，跳过唤起 (keywords=%s)",
                    list(normalized),
                )
                result["controls_visible"] = True
                return result

            width, height = self._get_screen_size()
            if self._device_profile and self._device_profile.get('resolution'):
                prof_width, prof_height = self._device_profile['resolution']
                if prof_width > 0 and prof_height > 0:
                    width, height = prof_width, prof_height
                    logger.info(
                        "播放控件唤起: 使用 main.yaml 分辨率 (%s, %s) device_key=%s",
                        width,
                        height,
                        self._device_profile.get('device_key'),
                    )

            y_norm = max(0.0, min(1.0, float(tap_y_norm)))
            tap_x = max(1, int(width / 2))
            tap_y = max(1, min(height - 1, int(height * y_norm)))

            logger.info(
                "播放控件唤起: 尝试点击屏幕 (%s, %s) y_norm=%.3f", tap_x, tap_y, y_norm
            )

            cmd = self._adb_prefix() + ["shell", "input", "tap", str(tap_x), str(tap_y)]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=aio_subprocess.DEVNULL,
                stderr=aio_subprocess.DEVNULL,
            )
            await proc.communicate()

            result["wake_attempted"] = True
            result["tap_performed"] = True

            if int(post_tap_sleep_ms) > 0:
                await asyncio.sleep(max(0.0, int(post_tap_sleep_ms) / 1000.0))

            # 清理缓存，确保重新检查是最新状态
            self._invalidate_ui_snapshot_cache()

            if normalized:
                result["controls_visible"] = await self._has_wake_keywords(normalized, max_age=0.0)
            else:
                result["controls_visible"] = True

            logger.info(
                "播放控件唤起: tap_performed=%s controls_visible=%s",
                result.get("tap_performed"),
                result.get("controls_visible"),
            )

        except Exception as exc:
            logger.warning("播放控件唤起失败: %s", exc)

        return result

    async def initialize(self) -> bool:
        """初始化组件（XML-only）"""
        try:
            # 初始化设备适配器
            self.device_adapter = DeviceAdapter()
            self._initialized = True
            logger.info("设备探测器初始化成功（XML-only）")
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
            "clickable_only": {"type": "boolean", "description": "是否只分析可点击元素", "default": True},
            "auto_close_limit": {"type": "integer", "description": "限制仅在前N次分析时自动关闭广告(默认3)", "default": 3}
        }
    )
    async def get_current_screen_info(self, include_elements: bool = False, clickable_only: bool = True, auto_close_ads: bool = True, auto_close_limit: Optional[int] = None) -> Dict[str, Any]:
        """获取当前屏幕信息"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # 更新分析轮次
            try:
                self._analysis_round = int(self._analysis_round) + 1
            except Exception:
                self._analysis_round = 1
            # 计算自动关广告是否启用（仅前N次）
            limit = int(auto_close_limit) if auto_close_limit is not None else int(getattr(self, 'auto_close_ads_limit', 3))
            should_auto_close = bool(auto_close_ads) and (self._analysis_round <= max(0, limit))

            screen_info = {
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "current_screen",
                "analysis_round": self._analysis_round,
                "auto_close_ads_enabled": should_auto_close,
                "auto_close_limit": limit
            }
            
            # 获取前台应用（避免主机侧管道与grep兼容问题，直接拉取并在本地解析）
            import subprocess, re
            adb_cmd = ["adb"] + (["-s", self.device_id] if self.device_id else []) + ["shell", "dumpsys", "window", "windows"]
            result = subprocess.run(adb_cmd, capture_output=True, text=True)
            current_pkg = "Unknown"
            current_activity = "Unknown"
            if result.returncode == 0 and result.stdout:
                out = result.stdout
                # 优先匹配 mCurrentFocus=Window{... u0 package/Activity}
                m = re.search(r"mCurrentFocus=Window\{[^}]*\s([\w\.]+)/([\w\.]+)\}", out)
                if m:
                    current_pkg = m.group(1)
                    current_activity = m.group(2)
                else:
                    # 备选: mFocusedApp=AppWindowToken{... package/Activity}
                    m2 = re.search(r"mFocusedApp=.*?\s([\w\.]+)\/([\w\.]+)", out)
                    if m2:
                        current_pkg = m2.group(1)
                        current_activity = m2.group(2)
                    else:
                        # 再备选: 仅提取包名片段
                        m3 = re.search(r"([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+){1,})", out)
                        if m3:
                            current_pkg = m3.group(1)
            screen_info["current_app"] = current_pkg
            screen_info["current_activity"] = current_activity

            # 业务页面名推断（简单启发式，若无法推断则为 unknown）
            def _infer_page_from_activity(act: str) -> str:
                if not act or act.lower() == "unknown":
                    return "unknown"
                l = act.lower()
                if "searchresult" in l or "result" in l:
                    return "search_result"
                if "search" in l:
                    return "search"
                if ("vod" in l and ("detail" in l or "playing" in l)) or ("play" in l and ("detail" in l or "player" in l)):
                    return "vod_playing_detail"
                if "player" in l:
                    return "vod_playing"
                if "detail" in l:
                    return "vod_detail"
                if "main" in l or "home" in l or "launcher" in l:
                    return "home"
                return "unknown"

            screen_info["current_page"] = _infer_page_from_activity(current_activity)

            # 兼容 step_validator 期望字段：page 优先 current_page
            screen_info.setdefault("page", screen_info["current_page"])
            
            # 在分析前，按默认参数尝试自动连续关闭广告（仅限前N轮；可关闭）
            if should_auto_close:
                try:
                    _ = await self.close_ads(mode="continuous", consecutive_no_ad=3, max_duration=10.0)
                except Exception as _e:
                    logger.info(f"预关闭广告失败（忽略）：{_e}")

            # 获取元素信息（XML-only）
            elements = await self._get_elements_xml(clickable_only=clickable_only)
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
            all_elements = elements if not clickable_only else await self._get_elements_xml(clickable_only=False)
            ads_info = await self._auto_handle_ads(all_elements, allow_click=should_auto_close)
            if should_auto_close and ads_info.get("auto_close_attempts", 0) > 0:
                elements = await self._get_elements_xml(clickable_only=clickable_only)

            # 播放状态检测（音频/会话）
            playing = await self._is_media_playing()
            screen_info["media_playing"] = playing
            
            # 如果需要包含元素列表
            if include_elements:
                # 限制元素数量避免响应过大
                limited_elements = elements[:50] if len(elements) > 50 else elements
                screen_info["elements"] = [
                    {
                        "text": elem.get("text", "")[:50],  # 限制文本长度
                        "resource_id": elem.get("resource_id", ""),
                        "content_desc": elem.get("content_desc", ""),
                        "package": elem.get("package", ""),
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
        logger.info(f"开始广告关闭流程 - 模式: {mode}, 连续无广告阈值: {consecutive_no_ad}, 最大时长: {max_duration}s")

        if not self._initialized:
            await self.initialize()

        # 单次：调用一次自动关闭
        if mode == "single":
            logger.info("执行单次广告关闭")
            elements = await self._get_elements_xml(clickable_only=False)
            logger.info(f"获取到 {len(elements)} 个界面元素")
            info = await self._auto_handle_ads(elements)
            logger.info(f"单次关闭结果: {info}")
            return {"mode": mode, "rounds": 1, "last_ads_info": info}

        # 连续：直到连续N次未检测到广告或达到最大时长
        logger.info("执行连续广告关闭模式")
        rounds = 0
        closes = 0
        no_ad_streak = 0
        import time as _t
        start_time = _t.time()
        end_t = start_time + float(max_duration)
        last_info = {}

        no_ad_conf_threshold = 0.35

        while _t.time() < end_t:
            current_time = _t.time()
            remaining_time = end_t - current_time
            rounds += 1

            logger.info(f"第 {rounds} 轮广告检测开始 (剩余时间: {remaining_time:.1f}s)")

            elements = await self._get_elements_xml(clickable_only=False)
            logger.info(f"第 {rounds} 轮获取到 {len(elements)} 个界面元素")

            info = await self._auto_handle_ads(elements)
            last_info = info

            conf = float(info.get("confidence", 0.0) or 0.0)
            attempts = int(info.get("auto_close_attempts", 0))
            closed = info.get("auto_closed", False)

            logger.info(f"第 {rounds} 轮结果: 置信度={conf:.2f}, 关闭尝试={attempts}, 成功关闭={closed}")

            if closed:
                closes += 1
                no_ad_streak = 0
                logger.info(f"第 {rounds} 轮成功关闭广告! 总关闭次数: {closes}")
            else:
                is_no_ad_round = False
                if len(elements) == 0:
                    is_no_ad_round = True
                elif attempts == 0 and conf <= no_ad_conf_threshold:
                    is_no_ad_round = True

                if is_no_ad_round:
                    no_ad_streak += 1
                    logger.info(
                        "第 %s 轮未发现广告 (置信度 %.2f <= %.2f, 尝试=%s), 无广告连续次数: %s",
                        rounds,
                        conf,
                        no_ad_conf_threshold,
                        attempts,
                        no_ad_streak,
                    )
                else:
                    no_ad_streak = 0
                    logger.warning(
                        "第 %s 轮检测到疑似广告 (置信度 %.2f, 尝试=%s) 未能关闭",
                        rounds,
                        conf,
                        attempts,
                    )

            logger.info(f"当前统计: 轮次={rounds}, 成功关闭={closes}, 连续无广告={no_ad_streak}")

            if no_ad_streak >= max(1, int(consecutive_no_ad)):
                logger.info(f"达到连续无广告阈值 ({no_ad_streak} >= {consecutive_no_ad}), 提前结束")
                break

            logger.info(f"等待 0.2s 后进入下一轮...")
            await asyncio.sleep(0.2)

        elapsed_time = _t.time() - start_time
        timed_out = _t.time() >= end_t

        result = {
            "mode": mode,
            "rounds": rounds,
            "close_count": closes,
            "no_ad_streak": no_ad_streak,
            "last_ads_info": last_info,
            "timed_out": timed_out,
            "elapsed_time": elapsed_time
        }

        # 输出最终统计信息
        logger.info(f"广告关闭流程结束:")
        logger.info(f"   模式: {mode}")
        logger.info(f"   总轮次: {rounds}")
        logger.info(f"   成功关闭: {closes} 次")
        logger.info(f"   连续无广告: {no_ad_streak} 次")
        logger.info(f"   用时: {elapsed_time:.1f}s / {max_duration}s")
        logger.info(f"   是否超时: {timed_out}")

        if closes > 0:
            logger.info(f"广告关闭成功! 共关闭了 {closes} 次广告")
        elif timed_out:
            logger.warning(f"广告关闭超时! 在 {max_duration}s 内未能连续 {consecutive_no_ad} 次确认无广告")
            if last_info.get("confidence", 0) > 0.2:
                logger.warning(f"最后一轮仍检测到疑似广告 (置信度: {last_info.get('confidence', 0):.2f})")
        else:
            logger.info(f"未检测到广告，流程正常结束")

        return result

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
            # 记录目标应用，用于后续操作范围限制
            try:
                self.target_app_package = pkg
            except Exception:
                pass
            result = unified_start_app(application=pkg, device_id=self.device_id, force_restart=force_restart)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _belongs_to_scope(self, elem: Dict[str, Any]) -> bool:
        try:
            rid = (elem.get('resource_id') or '').strip()
            pkg = (elem.get('package') or '').strip()
            # 未设置目标包时，默认放宽（保持向后兼容）
            if not self.target_app_package:
                return True
            rid_lower = rid.lower() if rid else ''
            target_prefix = (self.target_app_package + ":") if self.target_app_package else ''
            if rid and rid_lower.startswith(target_prefix.lower()):
                return True
            if rid_lower.startswith('id/'):
                if not pkg or pkg == self.target_app_package or pkg in getattr(self, 'allowed_external_packages', set()):
                    return True
            if pkg and (pkg == self.target_app_package or pkg in getattr(self, 'allowed_external_packages', set())):
                return True
            return False
        except Exception:
            return True

    # === 广告自动处理相关 ===
    def _elem_center(self, bounds: list) -> tuple:
        try:
            left, top, right, bottom = bounds
            return ((left + right) / 2.0, (top + bottom) / 2.0)
        except Exception:
            return (0.5, 0.5)

    async def _auto_handle_ads(self, elements: List[Dict[str, Any]], allow_click: bool = True) -> Dict[str, Any]:
        """检测广告并尝试自动关闭。最多尝试3次。

        置信度计算因子：
        - 元素数量偏少（<=20）: +0.25
        - 存在含 'ad/ads/广告' 的元素: +0.35
        - 存在含 'close/关闭/跳过/ivClose/mIvClose' 的元素: +0.25
        - 特征 close id（ivClose/mIvClose）且可点击: +0.30
        - 'ad' 与 'close' 的中心距离较近（<0.2 相对阈值）: +0.20
        """
        logger.info(f"开始广告检测 - 元素数量: {len(elements)}, 允许点击: {allow_click}")
        logger.info(f"优先关闭ID模式: {PRIORITY_CLOSE_IDS}")
        logger.info(f"通用关闭关键词: {GENERIC_CLOSE_KEYWORDS}")
        info = {"auto_close_attempts": 0, "auto_closed": False, "confidence": 0.0, "warnings": []}
        if not elements:
            logger.info("元素列表为空，跳过广告检测")
            return info

        def keywords(elem: Dict[str, Any]) -> Dict[str, str]:
            return {
                'text': (elem.get('text') or '').lower(),
                'rid': (elem.get('resource_id') or '').lower(),
                'desc': (elem.get('content_desc') or '').lower(),
                'cls': (elem.get('class_name') or '').lower(),
            }

        def _belongs_to_target(elem: Dict[str, Any]) -> bool:
            try:
                return self._belongs_to_scope(elem)
            except Exception:
                return True

        def detect_conf(elements: List[Dict[str, Any]]):
            n = len(elements)
            score = 0.0
            ad_elems = []
            close_elems = []
            logger.debug(f"检测广告置信度 - 元素数量: {n}")
            # 使用统一常量

            for i, e in enumerate(elements):
                # 仅处理目标应用元素，避免误点系统桌面等其他APK
                if not _belongs_to_target(e):
                    continue

                kw = keywords(e)
                resource_id = e.get('resource_id', '')
                text = e.get('text', '')

                # 首先检查是否在排除列表中
                is_excluded = any(excluded_id in kw['rid'] for excluded_id in EXCLUDED_CLOSE_IDS)
                if is_excluded:
                    continue

                # 检测广告相关元素
                ad_keywords = ['ad', 'ads', '广告', 'sponsor', 'upgrade', 'version', 'update', '升级', '更新']
                is_ad = any(k in kw['text'] or k in kw['rid'] for k in ad_keywords)
                if is_ad:
                    ad_elems.append(e)
                    logger.debug(f"发现广告元素: '{text}' [{resource_id}]")

                # 优先检测强制广告关闭按钮（但要确保不在排除列表中）
                force_close = False
                matched_priority_id = None
                for ad_id in PRIORITY_CLOSE_IDS:
                    if ad_id in kw['rid']:
                        # 再次确认不在排除列表中（双重检查）
                        if not is_excluded:
                            close_elems.append(e)
                            force_close = True
                            matched_priority_id = ad_id
                            logger.info(f"发现优先关闭按钮: [{resource_id}] - 匹配: {ad_id}")
                        else:
                            logger.info(f"跳过排除的优先按钮: [{resource_id}] - 匹配: {ad_id} (在EXCLUDED_CLOSE_IDS中)")
                        break


                # 常规关闭按钮检测（同样需要确保不在排除列表中）
                if not force_close:
                    generic_matches = [k for k in GENERIC_CLOSE_KEYWORDS if k in kw['text'] or k in kw['rid'] or k in kw['desc']]
                    if generic_matches:
                        # 再次确认不在排除列表中
                        if not is_excluded:
                            close_elems.append(e)
                            logger.debug(f"发现通用关闭元素: '{text}' [{resource_id}] - 匹配: {generic_matches}")
                        else:
                            logger.debug(f"跳过排除的通用按钮: '{text}' [{resource_id}] - 匹配: {generic_matches} (在EXCLUDED_CLOSE_IDS中)")
            # 置信度评分计算
            score_details = []

            if n <= 20:
                score += 0.25
                score_details.append(f"元素较少({n}<=20): +0.25")

            if ad_elems:
                score += 0.35
                score_details.append(f"发现广告元素({len(ad_elems)}个): +0.35")

            if close_elems:
                score += 0.25
                score_details.append(f"发现关闭元素({len(close_elems)}个): +0.25")

            # 检查是否有特征关闭ID且可点击
            special_close = any('ivclose' in keywords(e)['rid'] or 'mivclose' in keywords(e)['rid'] for e in close_elems) and any(e.get('clickable') for e in close_elems)
            if special_close:
                score += 0.30
                score_details.append("特征关闭ID且可点击: +0.30")
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
                        score_details.append(f"广告-关闭距离近({dmin:.3f}): +0.20")
                except Exception:
                    pass

            final_score = min(1.0, score)

            # 仅在检测到广告时输出关键信息
            if final_score >= 0.5:
                logger.info(f"广告检测: 置信度={final_score:.2f}, 广告={len(ad_elems)}, 关闭={len(close_elems)}")
                if close_elems:
                    logger.info(f"找到关闭按钮: {[elem.get('resource_id', '') for elem in close_elems[:3]]}")
            else:
                logger.debug(f"广告检测: 置信度={final_score:.2f} (未检测到明显广告)")

            return final_score, ad_elems, close_elems

        # 若仅做检测，不进行任何点击尝试
        if allow_click is False:
            conf_only, _, _ = detect_conf(elements)
            info['confidence'] = conf_only
            if conf_only >= 0.70:
                info['warnings'].append('可能存在未关闭的广告')
            return info

        async def try_close(close_elems: List[Dict[str, Any]]) -> bool:
            # 使用poco直接关闭广告
            logger.debug(f"开始尝试关闭广告 - 候选元素: {len(close_elems)} 个")
            try:
                # 使用本地自定义的Poco库
                from ..poco_utils import get_android_poco
                poco = get_android_poco()

                success_count = 0
                attempted_count = 0

                # 遍历所有关闭元素，使用poco直接点击
                for i, e in enumerate(close_elems, 1):
                    resource_id = e.get('resource_id', '')
                    text_val = (e.get('text') or '').strip()
                    clickable = e.get('clickable', False)

                    if not resource_id and not text_val:
                        continue

                    rid_lower = (resource_id or '').lower()

                    # 检查是否在排除列表中
                    is_excluded = any(excluded_id in rid_lower for excluded_id in EXCLUDED_CLOSE_IDS)
                    if is_excluded:
                        continue

                    # 检查是否是优先级广告按钮或一般关闭按钮
                    is_priority = any(ad_id in rid_lower for ad_id in PRIORITY_CLOSE_IDS)
                    is_generic = any(keyword in rid_lower for keyword in GENERIC_CLOSE_KEYWORDS) or \
                                 any(keyword in (text_val or '').lower() for keyword in GENERIC_CLOSE_KEYWORDS)
                    should_click = is_priority or is_generic

                    if should_click:
                        attempted_count += 1
                        elem_type = "优先级" if is_priority else "通用"
                        logger.debug(f"尝试点击 {elem_type} 关闭按钮: [{resource_id}]")

                        try:

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
                                    logger.info(f"poco点击成功: [{resource_id}]")

                                    # 点击后稍等一下让界面更新
                                    try:
                                        import asyncio as _aio
                                        await _aio.sleep(0.5)
                                    except Exception:
                                        pass
                                    continue
                                except Exception as click_error:
                                    logger.debug(f"poco点击失败: [{resource_id}] - {click_error}")
                                    continue
                            else:
                                logger.debug(f"元素不存在或不可点击: [{resource_id}]")

                        except Exception as e:
                            logger.debug(f"poco处理异常: [{resource_id}] - {e}")
                            continue

                # 汇总poco点击结果
                if success_count > 0:
                    logger.info(f"poco点击成功: {success_count}/{attempted_count} 个")
                else:
                    logger.debug(f"poco点击失败: 尝试 {attempted_count} 个, 成功 0 个")

                # 若poco可用但未成功，继续走坐标兜底
                if success_count > 0:
                    return True
                else:
                    logger.info("poco点击未成功，尝试坐标兜底方案")
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
                    # 仅处理目标应用元素
                    if not _belongs_to_target(e):
                        continue
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
        logger.info(f"开始自动关闭循环，最大尝试次数: {max_attempts}")

        for attempt in range(1, max_attempts + 1):
            logger.info(f"第 {attempt} 次尝试关闭广告")

            # 每次尝试前都重新获取最新UI状态
            if attempt > 1:
                logger.info(f"第 {attempt} 次: 重新获取最新UI状态")
                elements = await self._get_elements_xml(clickable_only=False)
                logger.info(f"重新获取后得到 {len(elements)} 个元素")

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

            logger.info(f"第 {attempt} 次评估: 置信度={conf:.2f}, 优先关闭={has_priority_close}, 关闭元素={len(close_es)}个")

            if (has_priority_close or conf >= 0.50) and close_es:
                logger.info(f"第 {attempt} 次: 满足关闭条件(优先={has_priority_close}, 置信度={conf:.2f}), 开始尝试点击")
                clicked = await try_close(close_es)
                info['auto_close_attempts'] += 1

                if not clicked:
                    logger.warning(f"第 {attempt} 次: 关闭尝试失败，终止循环")
                    break

                logger.info(f"第 {attempt} 次: 点击成功，等待界面更新")
                # 点击后等待界面更新
                try:
                    import asyncio as _aio
                    await _aio.sleep(1.0)  # 增加等待时间确保界面完全更新
                except Exception:
                    pass

                # 刷新元素以便下一轮判断
                elements = await self._get_elements_xml(clickable_only=False)
                logger.info(f"刷新后获得 {len(elements)} 个元素")

                # 若置信度下降则退出
                conf2, _, _ = detect_conf(elements)
                logger.info(f"关闭后置信度变化: {conf:.2f} -> {conf2:.2f}")

                if conf2 < 0.70:
                    info['auto_closed'] = True
                    logger.info(f"置信度降至 {conf2:.2f} < 0.70，广告已成功关闭")
                    break
                else:
                    logger.info(f"置信度仍为 {conf2:.2f} >= 0.70，继续下一轮")
            else:
                logger.info(f"第 {attempt} 次: 不满足关闭条件(优先={has_priority_close}, 置信度={conf:.2f} < 0.50), 跳过")
                break

        # 若多次后仍>=0.70，发出警告
        conf_final, _, _ = detect_conf(elements)
        info['confidence'] = conf_final

        logger.info(f"关闭循环结束: 最终置信度={conf_final:.2f}, 尝试次数={info['auto_close_attempts']}")

        if conf_final >= 0.70 and not info.get('auto_closed', False):
            warning_msg = f'仍检测到疑似广告(置信度={conf_final:.2f})'
            info['warnings'].append(warning_msg)
            logger.warning(f"{warning_msg}")

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
        """执行单步UI动作。
        策略：优先使用选择器（resource_id > content_desc > text）；仅当选择器失败时再使用 bounds_px。
        同时内置“容器→子输入框”启发式：若点击容器失败，尝试点击其子 EditText。
        """
        if not self._initialized:
            await self.initialize()
        import subprocess, time as _time
        exec_log = []
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

            sel_type, sel_value = pick_selector(target)
            used_selector = {"type": sel_type, "value": sel_value}
            # 选择器包名限制：若提供 resource_id 但不属于目标包，直接判为无效选择器
            if sel_type == 'resource_id' and sel_value and self.target_app_package:
                rid = str(sel_value)
                # Accept fully-qualified Android resource form "<pkg>:id/<name>" or generic "id/<name>"
                if not (rid.startswith(f"{self.target_app_package}:id/") or rid.startswith("id/")):
                    return {"success": False, "error": "selector_not_in_target_app", "used": used_selector}

            # 通过 ElementRecognizer 执行动作
            if not self.visual_integration:
                self.visual_integration = VisualIntegration(IntegrationConfig(device_id=self.device_id))
                await self.visual_integration.initialize()

            if action == 'click':
                # 1) 首选按选择器点击（Poco/XML-only）
                ok = False
                # 内容/文本选择器：先验证属于目标包
                if sel_type in ('content_desc', 'text') and sel_value and self.target_app_package:
                    try:
                        elems = await self._get_elements_xml(clickable_only=False)
                        found_in_target = False
                        for e in elems:
                            if sel_type == 'content_desc' and (e.get('content_desc') == sel_value):
                                if self._belongs_to_scope(e):
                                    found_in_target = True; break
                            if sel_type == 'text' and (e.get('text') == sel_value):
                                if self._belongs_to_scope(e):
                                    found_in_target = True; break
                        if not found_in_target:
                            return {"success": False, "error": "selector_not_in_target_app", "used": used_selector}
                    except Exception:
                        pass
                if sel_type in ('resource_id', 'content_desc', 'text') and sel_value:
                    try:
                        from ..poco_utils import get_android_poco
                        poco = get_android_poco()
                        obj = None
                        if sel_type == 'resource_id':
                            obj = poco(resourceId=sel_value)
                            if not obj.exists() and '/' in str(sel_value):
                                # 后缀匹配（兼容包名前缀差异）
                                rid_suffix = str(sel_value).split('/')[-1]
                                try:
                                    exec_log.append(f"poco(resourceIdMatches=.*:id/{rid_suffix}$).click()")
                                    obj = poco(resourceIdMatches=f".*:id/{rid_suffix}$")
                                except Exception:
                                    obj = poco(name=rid_suffix)
                        elif sel_type == 'text':
                            obj = poco(text=sel_value)
                        elif sel_type == 'content_desc':
                            # 多种别名尝试
                            for key in ('desc', 'description', 'contentDescription', 'name'):
                                try:
                                    obj = poco(**{key: sel_value})
                                    if obj.exists():
                                        break
                                except Exception:
                                    obj = None
                        if obj and obj.exists():
                            try:
                                try:
                                    obj.wait_for_appearance(timeout=2.0)
                                except Exception:
                                    pass
                                exec_log.append(f"poco.click({sel_type}={sel_value})")
                                obj.click()
                                ok = True
                            except Exception:
                                ok = False
                    except Exception:
                        ok = False
                # 2) 若失败，尝试“容器→子输入框”启发式
                if not ok and sel_type == 'resource_id' and sel_value:
                    try:
                        elems = await self._get_elements_xml(clickable_only=False)
                        container = None
                        for e in elems:
                            if e.get('resource_id') == sel_value:
                                container = e; break
                        if container and isinstance(container.get('bounds'), (list, tuple)) and len(container['bounds']) == 4:
                            cb = container['bounds']
                            # 尝试在容器内寻找 EditText 类或带 'searchEt' 的输入框
                            child = None
                            for e in elems:
                                cls = (e.get('class_name') or '').lower()
                                rid = (e.get('resource_id') or '').lower()
                                eb = e.get('bounds') or []
                                def _inside(inner, outer):
                                    try:
                                        return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]
                                    except Exception:
                                        return False
                                if _inside(eb, cb) and ('edittext' in cls or 'searchet' in rid):
                                    child = e; break
                            if child and isinstance(child.get('bounds'), (list, tuple)) and len(child['bounds']) == 4:
                                # 点击子输入框中心
                                b = child['bounds']
                                # 转换归一化->像素（如有必要）。尝试获取屏幕尺寸
                                def _screen_size():
                                    out = subprocess.run(
                                        f"adb {'-s ' + self.device_id if self.device_id else ''} shell wm size".split(), capture_output=True, text=True
                                    )
                                    if out.returncode == 0 and 'Physical size:' in out.stdout:
                                        sz = out.stdout.split('Physical size:')[-1].strip().split('\n')[0].strip()
                                        w, h = sz.split('x')
                                        return int(w), int(h)
                                    return 1080, 1920
                                sw, sh = _screen_size()
                                if max(b) <= 1.0:
                                    x = int(((b[0] + b[2]) / 2.0) * sw)
                                    y = int(((b[1] + b[3]) / 2.0) * sh)
                                else:
                                    x = int((b[0] + b[2]) / 2.0)
                                    y = int((b[1] + b[3]) / 2.0)
                                cmd = f"adb {'-s ' + self.device_id + ' ' if self.device_id else ''}shell input tap {x} {y}"
                                exec_log.append(cmd)
                                subprocess.run(cmd.split(), capture_output=True, text=True)
                                ok = True
                    except Exception:
                        pass
                # 3) 若仍失败，且给定 bounds_px，则用坐标兜底（需验证属于目标包/白名单）
                if not ok:
                    bp = target.get('bounds_px') if isinstance(target, dict) else None
                    if bp and isinstance(bp, (list, tuple)) and len(bp) == 4:
                        if self.target_app_package:
                            try:
                                elems = await self._get_elements_xml(clickable_only=False)
                                # 统一为像素坐标进行重叠判断
                                def _screen_size():
                                    out = subprocess.run(
                                        f"adb {'-s ' + self.device_id if self.device_id else ''} shell wm size".split(), capture_output=True, text=True
                                    )
                                    if out.returncode == 0 and 'Physical size:' in out.stdout:
                                        sz = out.stdout.split('Physical size:')[-1].strip().split('\n')[0].strip()
                                        w, h = sz.split('x')
                                        return int(w), int(h)
                                    return 1080, 1920
                                sw, sh = _screen_size()
                                def _to_px(b):
                                    if max(b) <= 1.0:
                                        return [int(b[0]*sw), int(b[1]*sh), int(b[2]*sw), int(b[3]*sh)]
                                    return [int(b[0]), int(b[1]), int(b[2]), int(b[3])]
                                bb = _to_px(bp)
                                def _iou(a, b):
                                    ax1, ay1, ax2, ay2 = a; bx1, by1, bx2, by2 = b
                                    inter_w = max(0, min(ax2,bx2) - max(ax1,bx1))
                                    inter_h = max(0, min(ay2,by2) - max(ay1,by1))
                                    inter = inter_w * inter_h
                                    if inter == 0:
                                        return 0.0
                                    area_a = max(0, ax2-ax1) * max(0, ay2-ay1)
                                    area_b = max(0, bx2-bx1) * max(0, by2-by1)
                                    union = max(1, area_a + area_b - inter)
                                    return inter / union
                                found_ok = False
                                for e in elems:
                                    eb = e.get('bounds') or []
                                    if not (isinstance(eb, (list, tuple)) and len(eb) == 4):
                                        continue
                                    ebp = _to_px(eb)
                                    if _iou(bb, ebp) >= 0.5 and self._belongs_to_scope(e):
                                        found_ok = True
                                        break
                                if not found_ok:
                                    return {"success": False, "error": "bounds_not_in_target_app", "used": used_selector}
                            except Exception:
                                pass

                        x = int((bp[0] + bp[2]) / 2)
                        y = int((bp[1] + bp[3]) / 2)
                        cmd = f"adb {'-s ' + self.device_id + ' ' if self.device_id else ''}shell input tap {x} {y}"
                        exec_log.append(cmd)
                        subprocess.run(cmd.split(), capture_output=True, text=True)
                        ok = True
                _time.sleep(max(0.0, float(wait_after)))
                return {"success": bool(ok), "used": used_selector if ok else ({"type": "bounds_px", "value": target.get('bounds_px')} if target.get('bounds_px') else used_selector), "exec_log": exec_log}

            elif action == 'input':
                # 选择器范围限制
                if sel_type == 'resource_id' and sel_value and self.target_app_package:
                    if not str(sel_value).startswith(self.target_app_package + ":"):
                        return {"success": False, "error": "selector_not_in_target_app", "used": used_selector}
                if sel_type in ('content_desc', 'text') and sel_value and self.target_app_package:
                    try:
                        elems = await self._get_elements_xml(clickable_only=False)
                        found_in_target = False
                        for e in elems:
                            if sel_type == 'content_desc' and (e.get('content_desc') == sel_value) and self._belongs_to_scope(e):
                                found_in_target = True; break
                            if sel_type == 'text' and (e.get('text') == sel_value) and self._belongs_to_scope(e):
                                found_in_target = True; break
                        if not found_in_target:
                            return {"success": False, "error": "selector_not_in_target_app", "used": used_selector}
                    except Exception:
                        pass
                # 聚焦输入框（Poco）
                try:
                    from ..poco_utils import get_android_poco
                    poco = get_android_poco()
                    obj = None
                    if sel_type == 'resource_id':
                        obj = poco(resourceId=sel_value)
                    elif sel_type == 'text':
                        obj = poco(text=sel_value)
                    elif sel_type == 'content_desc':
                        for key in ('desc', 'description', 'contentDescription', 'name'):
                            try:
                                obj = poco(**{key: sel_value})
                                if obj.exists():
                                    break
                            except Exception:
                                obj = None
                    if obj and obj.exists():
                        try:
                            obj.wait_for_appearance(timeout=2.0)
                        except Exception:
                            pass
                        exec_log.append(f"poco.click({sel_type}={sel_value})")
                        obj.click()
                except Exception:
                    pass
                # ADB 输入（空格替换为% s以兼容input）
                safe = (data or '').replace(' ', '%s')
                cmd = f"adb {'-s ' + self.device_id + ' ' if self.device_id else ''}shell input text {safe}"
                exec_log.append(cmd)
                subprocess.run(cmd.split(), capture_output=True, text=True)
                _time.sleep(max(0.0, float(wait_after)))
                return {"success": True, "used": used_selector, "exec_log": exec_log}
            elif action == 'swipe':
                # 支持 target.swipe.start_px/end_px 或通过 bounds_px 推导方向
                swipe = target.get('swipe', {}) if isinstance(target, dict) else {}
                def _screen_size():
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
                    exec_log.append(cmd)
                    subprocess.run(cmd.split(), capture_output=True, text=True)
                    _time.sleep(max(0.0, float(wait_after)))
                    return {"success": True, "used": {"type": "swipe", "start_px": start_px, "end_px": end_px, "duration_ms": dur}, "exec_log": exec_log}
                return {"success": False, "error": "invalid swipe parameters", "exec_log": exec_log}
            else:
                return {"success": False, "error": f"unsupported action: {action}", "exec_log": exec_log}
        except Exception as e:
            return {"success": False, "error": str(e), "used": used_selector, "exec_log": exec_log}

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
        """执行动作并通过前后两次 get_current_screen_info 和截图相似度对比验证是否变化。
        规则：仅当 XML 未变化 且 屏幕相似度>=98% 时，判定为无效操作。
        """
        from hashlib import md5
        import json as _json
        import tempfile, os as _os
        # 截图工具
        from only_test.lib.screen_capture import ScreenCapture
        _sc = ScreenCapture(device_id=self.device_id)
        # 前置：获取 UI 与截图
        pre = await self.get_current_screen_info(include_elements=True, clickable_only=True)
        pre_shot = None
        try:
            pre_shot = _sc.take_screenshot(save_path=str(_os.path.join(tempfile.gettempdir(), f"pre_{self.device_id or 'default'}.png")))
        except Exception:
            pre_shot = None
        # 执行动作
        r = await self.perform_ui_action(action=action, target=target, data=data, wait_after=wait_after)
        # 后置：获取 UI 与截图
        post = await self.get_current_screen_info(include_elements=True, clickable_only=True)
        post_shot = None
        try:
            post_shot = _sc.take_screenshot(save_path=str(_os.path.join(tempfile.gettempdir(), f"post_{self.device_id or 'default'}.png")))
        except Exception:
            post_shot = None
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
                        if rid and ee.get('resource_id') == rid and self._belongs_to_scope(ee):
                            return True
                        if txt and ee.get('text') == txt and self._belongs_to_scope(ee):
                            return True
                        if desc and ee.get('content_desc') == desc and self._belongs_to_scope(ee):
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
        # XML 变化签名
        def signature(d: Dict[str, Any]) -> str:
            els = d.get('elements', []) if isinstance(d, dict) else []
            sig = [f"{e.get('resource_id','')}|{e.get('text','')}|{e.get('clickable',False)}" for e in els]
            payload = "|".join(sig) + f";cnt={d.get('total_elements',0)}"
            return md5(payload.encode('utf-8', errors='ignore')).hexdigest()
        pre_sig = signature(pre)
        post_sig = signature(post)
        xml_changed = (pre_sig != post_sig)
        # 图像相似度（0~1，越大越相似）
        def _image_similarity(p1: str, p2: str) -> float:
            try:
                from PIL import Image  # type: ignore
                im1 = Image.open(p1).convert('L').resize((64,64))
                im2 = Image.open(p2).convert('L').resize((64,64))
                # 计算均方差并映射到相似度
                import numpy as _np  # type: ignore
                a1 = _np.array(im1, dtype=_np.float32)
                a2 = _np.array(im2, dtype=_np.float32)
                mse = ((a1 - a2) ** 2).mean()
                # 像素值范围0-255，归一化；简单映射到[0,1]
                sim = max(0.0, 1.0 - (mse / (255.0**2)))
                return float(sim)
            except Exception:
                # 回退：MD5 完全一致视为1.0，否则0.0
                try:
                    import hashlib
                    def _md5(fp):
                        with open(fp, 'rb') as f:
                            return hashlib.md5(f.read()).hexdigest()
                    return 1.0 if (_md5(p1) == _md5(p2)) else 0.0
                except Exception:
                    return 0.0
        visual_similarity = None
        if pre_shot and post_shot:
            visual_similarity = _image_similarity(pre_shot, post_shot)
        visual_changed = (visual_similarity is not None and visual_similarity < 0.98)
        invalid_action = (not xml_changed) and (visual_changed is False)
        return {
            "success": r.get("success", False),
            "used": r.get("used"),
            "exec_log": r.get("exec_log", []),
            "changed": xml_changed,
            "xml_changed": xml_changed,
            "visual_similarity": visual_similarity,
            "visual_changed": visual_changed,
            "invalid_action": invalid_action,
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
            search_results = {
                "search_text": search_text,
                "search_type": search_type,
                "case_sensitive": case_sensitive,
                "timestamp": datetime.now().isoformat(),
                "matches": []
            }
            
            # 获取所有元素（XML-only）
            all_elements = await self._get_elements_xml(clickable_only=False)
            
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

