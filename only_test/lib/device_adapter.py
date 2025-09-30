#!/usr/bin/env python3
"""
设备信息探测与适配器

自动检测设备信息并更新JSON用例的设备适配部分
"""

import json
import platform
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# 使用统一配置管理器
from only_test.config.config_manager import get_config, get_config_section

# 设置日志
logger = logging.getLogger(__name__)

try:
    from airtest.core.api import device as current_device
    from airtest.core.android.adb import ADB
except ImportError:
    current_device = None
    ADB = None


class DeviceAdapter:
    """
    设备信息探测与适配器
    
    设计说明 (Design Documentation):
    ===============================
    
    核心职责:
    1. 设备信息自动探测 (detect_device_info)
    2. 适配规则生成 (generate_adaptation_rules)  
    3. JSON测试用例更新 (update_json_testcase)
    
    缓存策略:
    - device_info: 设备信息缓存，避免重复ADB调用
    - config_cache: YAML配置缓存，减少文件I/O
    
    配置优先级:
    1. YAML配置文件 (framework_config.yaml, device_config.yaml, main.yaml)
    2. 动态探测值
    3. 硬编码默认值 (最后选择)
    
    错误处理策略:
    - ADB连接失败 -> 使用模拟设备信息
    - 配置文件缺失 -> 使用默认值
    - 具体异常类型 -> 便于调试定位
    """
    
    def __init__(self):
        """初始化设备适配器"""
        self.device_info = {}
        self.adaptation_rules = {}
        self._device_info_cache = {}

        # 加载设备连接配置
        self.connection_timeout = get_config('device.connection.adb_timeout', 30)
        self.connection_retries = get_config('device.connection.connection_retries', 3)
        self.heartbeat_interval = get_config('device.connection.heartbeat_interval', 30)

        # 统一配置管理器会自动加载所有配置文件
        # 无需在此处重复加载
    
    def _get_config_value(self, path: str, default: Any = None) -> Any:
        """从统一配置管理器获取值，支持点分隔路径"""
        return get_config(path, default)
        
    def get_adb_commands(self, device_id: Optional[str] = None) -> Dict[str, str]:
        """
        获取设备特定的ADB命令配置
        
        Args:
            device_id: 设备ID，用于获取设备特定配置
            
        Returns:
            Dict: ADB命令配置
        """
        # 获取基础ADB命令配置
        base_commands = self._get_config_value("adb_connection.commands", {})
        device_info_commands = self._get_config_value("adb_connection.device_info_commands", {})
        
        # 合并所有命令
        all_commands = {**base_commands, **device_info_commands}
        
        # 如果有设备特定配置，进行覆盖
        if device_id:
            # 这里可以根据设备ID获取特定配置
            # 目前使用通用配置
            pass
            
        return all_commands
    
    def get_device_capabilities(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取设备能力配置
        
        Args:
            device_id: 设备ID
            
        Returns:
            Dict: 设备能力配置
        """
        capabilities = {
            "resolution_adaptation": self._get_config_value("resolution_adaptation", {}),
            "performance_monitoring": self._get_config_value("performance_monitoring", {}),
            "media_handling": self._get_config_value("media_handling", {}),
            "device_adaptation": self._get_config_value("device_adaptation.default_adaptation", {})
        }
        
        return capabilities
    
    def apply_device_config(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        应用设备特定配置
        
        Args:
            device_id: 设备ID
            
        Returns:
            Dict: 应用的配置信息
        """
        applied_config = {
            "adb_commands": self.get_adb_commands(device_id),
            "capabilities": self.get_device_capabilities(device_id),
            "connection_config": {
                "timeout": self._get_config_value("adb_connection.timeout", 30),
                "retry_count": self._get_config_value("adb_connection.retry_count", 3),
                "retry_delay": self._get_config_value("adb_connection.retry_delay", 2)
            }
        }
        
        return applied_config
    
    def _execute_configured_command(self, adb, command_key: str, default_value: str = "Unknown") -> str:
        """
        执行配置的ADB命令
        
        Args:
            adb: ADB连接对象
            command_key: 命令键名（在配置文件中定义）
            default_value: 默认返回值
            
        Returns:
            str: 命令执行结果
        """
        adb_commands = self.get_adb_commands()
        command = adb_commands.get(command_key)
        
        if not command:
            return default_value
            
        try:
            result = adb.shell(command).strip()
            return result if result else default_value
        except Exception as e:
            logger.warning(f"执行ADB命令失败 {command}: {e}")
            return default_value

    def detect_device_info(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        探测当前连接设备的详细信息
        
        Args:
            use_cache: 是否使用缓存的设备信息
            
        Returns:
            Dict: 设备信息
        """
        # 检查缓存
        if use_cache and self._device_info_cache:
            return self._device_info_cache.copy()
            
        device_info = {
            "detection_time": datetime.now().isoformat(),
            "host_system": platform.system(),
            "framework_available": current_device is not None
        }
        
        # 获取配置的ADB命令
        adb_commands = self.get_adb_commands()
        
        if current_device and hasattr(current_device, 'adb'):
            # 获取Android设备信息
            adb = current_device.adb if hasattr(current_device, 'adb') else None
            if adb:
                try:
                    # 使用配置的命令获取设备信息
                    device_info.update({
                        "device_name": self._execute_configured_command(adb, "model", "Unknown"),
                        "android_version": self._execute_configured_command(adb, "version", "Unknown"),
                        "sdk_version": self._execute_configured_command(adb, "sdk_version", "Unknown"),
                        "brand": self._execute_configured_command(adb, "brand", "Unknown"),
                        "manufacturer": self._get_adb_property(adb, "ro.product.manufacturer", "Unknown"),
                        "device_model": self._get_adb_property(adb, "ro.product.device", "Unknown"),
                    })
                    
                    # 屏幕信息
                    screen_info = self._get_screen_info(adb)
                    device_info["screen_info"] = screen_info
                    
                    # 性能信息
                    performance_info = self._get_performance_info(adb)
                    device_info["performance_info"] = performance_info
                    
                    # 系统特性
                    system_features = self._get_system_features(adb)
                    device_info["system_features"] = system_features
                    
                except (OSError, ConnectionError) as e:
                    device_info["detection_error"] = f"ADB连接错误: {str(e)}"
                except (AttributeError, KeyError) as e:
                    device_info["detection_error"] = f"设备属性获取错误: {str(e)}"
                except Exception as e:
                    device_info["detection_error"] = f"未知错误: {str(e)}"
        else:
            # 模拟设备信息（用于开发测试）
            device_info.update({
                "device_name": "Simulated_Device",
                "android_version": "13.0",
                "sdk_version": "33",
                "brand": "Generic",
                "manufacturer": "Android",
                "device_model": "simulator",
                "screen_info": {
                    "resolution": "1080x1920",
                    "density": 420,
                    "orientation": "portrait"
                },
                "note": "使用模拟设备信息"
            })
        
        # 保存到缓存
        self._device_info_cache = device_info.copy()
        self.device_info = device_info
        return device_info
    
    def _get_adb_property(self, adb, property_name: str, default: str = "Unknown") -> str:
        """获取ADB属性值"""
        try:
            result = adb.shell(f"getprop {property_name}")
            return result.strip() or default
        except (OSError, ConnectionError, AttributeError):
            return default
    
    def _get_screen_info(self, adb) -> Dict[str, Any]:
        """获取屏幕信息"""
        try:
            # 获取屏幕尺寸
            wm_size = adb.shell("wm size")
            size_match = wm_size.strip().split(": ")[-1] if ": " in wm_size else "1080x1920"
            width, height = map(int, size_match.split("x"))
            
            # 获取屏幕密度
            wm_density = adb.shell("wm density")
            density_match = wm_density.strip().split(": ")[-1] if ": " in wm_density else "420"
            density = int(density_match)
            
            return {
                "resolution": f"{width}x{height}",
                "width": width,
                "height": height,
                "density": density,
                "orientation": "portrait" if height > width else "landscape",
                "aspect_ratio": round(max(width, height) / min(width, height), 2)
            }
        except (OSError, ConnectionError, ValueError, AttributeError):
            return {
                "resolution": "1080x1920",
                "width": 1080,
                "height": 1920, 
                "density": 420,
                "orientation": "portrait",
                "aspect_ratio": 1.78
            }
    
    def _get_performance_info(self, adb) -> Dict[str, Any]:
        """获取性能相关信息"""
        try:
            # CPU信息
            cpu_info = adb.shell("cat /proc/cpuinfo | grep 'model name' | head -1")
            cpu_cores = adb.shell("cat /proc/cpuinfo | grep processor | wc -l")
            
            # 内存信息
            mem_info = adb.shell("cat /proc/meminfo | grep MemTotal")
            mem_total = mem_info.split()[1] if len(mem_info.split()) > 1 else "Unknown"
            
            return {
                "cpu_info": cpu_info.strip() or "Unknown",
                "cpu_cores": int(cpu_cores.strip()) if cpu_cores.strip().isdigit() else 1,
                "memory_total_kb": int(mem_total) if mem_total.isdigit() else 0,
                "memory_total_gb": round(int(mem_total) / 1024 / 1024, 1) if mem_total.isdigit() else 0
            }
        except (OSError, ConnectionError, ValueError, AttributeError):
            return {
                "cpu_info": "Unknown",
                "cpu_cores": 1,
                "memory_total_kb": 0,
                "memory_total_gb": 0
            }
    
    def _get_system_features(self, adb) -> Dict[str, Any]:
        """获取系统特性"""
        try:
            # 检查Root状态
            root_check = adb.shell("su -c 'echo rooted' 2>/dev/null || echo 'not_rooted'")
            is_rooted = "rooted" in root_check
            
            # 检查Google服务
            gms_check = adb.shell("pm list packages | grep com.google.android.gms")
            has_gms = bool(gms_check.strip())
            
            return {
                "is_rooted": is_rooted,
                "has_google_services": has_gms,
                "adb_available": True
            }
        except (OSError, ConnectionError, AttributeError):
            return {
                "is_rooted": False,
                "has_google_services": False,
                "adb_available": False
            }
    
    def generate_adaptation_rules(self, device_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        根据设备信息生成适配规则
        
        Args:
            device_info: 设备信息（可选，使用已探测的信息）
            
        Returns:
            Dict: 适配规则
        """
        if device_info is None:
            device_info = self.device_info or self.detect_device_info()
        
        screen_info = device_info.get("screen_info", {})
        width = screen_info.get("width", 1080)
        height = screen_info.get("height", 1920)
        density = screen_info.get("density", 420)
        
        # 基于屏幕尺寸的适配规则
        adaptation_rules = {
            "touch_adaptation": {
                "base_resolution": "1080x1920",
                "current_resolution": f"{width}x{height}",
                "scale_factor_x": width / 1080,
                "scale_factor_y": height / 1920,
                "touch_offset": {
                    "x": 0,
                    "y": self._calculate_status_bar_offset(height)
                }
            },
            "recognition_adaptation": {
                "preferred_mode": "xml",
                "xml_recognition": {
                    "enabled": True,
                    "timeout": 10,
                    "retry_count": 3
                }
            },
            "performance_adaptation": {
                "action_delay": self._calculate_action_delay(device_info),
                "element_wait_timeout": self._calculate_wait_timeout(device_info),
                "screenshot_quality": self._get_screenshot_quality(device_info)
            },
            "app_specific": {
                "launch_timeout": self._get_config_value("app_management.app_launch.timeout", 30),
                "page_load_timeout": self._get_config_value("execution.timeouts.page_load", 15),
                "animation_wait": self._get_config_value("global_config.playback_auto_wake.post_tap_sleep_ms", 250) / 1000
            }
        }
        
        self.adaptation_rules = adaptation_rules
        return adaptation_rules
    
    def _calculate_status_bar_offset(self, screen_height: int) -> int:
        """计算状态栏偏移量"""
        if screen_height >= 2400:  # 高分辨率设备
            return 60
        elif screen_height >= 1920:  # 标准分辨率
            return 50
        else:  # 低分辨率设备
            return 40
    
    
    def _calculate_action_delay(self, device_info: Dict) -> float:
        """计算操作延迟"""
        performance_info = device_info.get("performance_info", {})
        cpu_cores = performance_info.get("cpu_cores", 4)
        memory_gb = performance_info.get("memory_total_gb", 4)
        
        # 优先从配置获取延迟值
        base_delay = self._get_config_value("device_types.android_phone.interaction_delay", 0.5)
        
        # 根据设备性能调整延迟
        if cpu_cores >= 8 and memory_gb >= 8:
            return base_delay  # 高性能设备
        elif cpu_cores >= 4 and memory_gb >= 4:
            return base_delay * 1.5  # 中等性能设备  
        else:
            return base_delay * 2.0  # 低性能设备
    
    def _calculate_wait_timeout(self, device_info: Dict) -> int:
        """计算等待超时时间"""
        performance_info = device_info.get("performance_info", {})
        memory_gb = performance_info.get("memory_total_gb", 4)
        
        # 优先从配置获取超时值
        default_timeout = self._get_config_value("execution.timeouts.element_wait", 10)
        
        # 根据内存情况调整超时
        if memory_gb >= 8:
            return default_timeout + 5
        elif memory_gb >= 4:
            return default_timeout + 10
        else:
            return default_timeout + 20
    
    def _get_screenshot_quality(self, device_info: Dict) -> int:
        """获取截图质量设置"""
        screen_info = device_info.get("screen_info", {})
        width = screen_info.get("width", 1080)
        
        # 优先从配置获取截图质量
        default_quality = self._get_config_value("performance.screenshot.quality", 80)
        
        # 根据屏幕分辨率调整截图质量
        if width >= 1440:  # 2K+屏幕
            return max(default_quality - 10, 70)  # 适中质量，减少文件大小
        elif width >= 1080:  # 1080p屏幕
            return default_quality  # 使用配置质量
        else:  # 低分辨率屏幕
            return min(default_quality + 15, 95)  # 提高质量但不超过95
    
    def update_json_testcase(self, json_file: str, output_file: Optional[str] = None) -> str:
        """
        更新JSON测试用例的设备信息
        
        Args:
            json_file: 输入的JSON文件路径
            output_file: 输出的JSON文件路径（可选）
            
        Returns:
            str: 更新后的JSON文件路径
        """
        # 读取原始JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            testcase_data = json.load(f)
        
        # 探测设备信息
        device_info = self.detect_device_info()
        adaptation_rules = self.generate_adaptation_rules(device_info)
        
        # 更新JSON数据
        testcase_data["device_adaptation"] = {
            "detection_time": datetime.now().isoformat(),
            "detected_device": device_info,
            "adaptation_rules": adaptation_rules,
            "assets_path_pattern": self._generate_assets_path_pattern(testcase_data, device_info)
        }
        
        # 保存更新后的JSON
        if output_file is None:
            output_file = json_file
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(testcase_data, f, ensure_ascii=False, indent=2)
        
        return output_file
    
    def _generate_assets_path_pattern(self, testcase_data: Dict, device_info: Dict) -> Dict[str, str]:
        """生成资源路径模式"""
        target_app = testcase_data.get("target_app", "unknown_app")
        device_name = device_info.get("device_name", "unknown_device")
        
        # 清理文件名中的特殊字符
        clean_app_name = target_app.replace(".", "_").replace("-", "_")
        clean_device_name = device_name.replace(" ", "_").replace("-", "_")
        
        base_path = f"assets/{clean_app_name}_{clean_device_name}"
        
        return {
            "base_path": base_path,
            "screenshots_pattern": f"{base_path}/step{{step_num}}_{{action}}_{{timestamp}}.png",
            "elements_pattern": f"{base_path}/step{{step_num}}_element_{{element_type}}_{{timestamp}}.png", 
            "omniparser_pattern": f"{base_path}/step{{step_num}}_omni_result_{{timestamp}}.json",
            "execution_log": f"{base_path}/execution_log.json"
        }


def main():
    """命令行工具入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="设备信息探测与JSON用例更新工具")
    parser.add_argument("json_file", help="要更新的JSON测试用例文件")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--detect-only", action="store_true", help="仅显示设备信息")
    
    args = parser.parse_args()
    
    adapter = DeviceAdapter()
    
    if args.detect_only:
        print("🔍 探测设备信息...")
        device_info = adapter.detect_device_info()
        print("\n📱 设备信息:")
        print(json.dumps(device_info, ensure_ascii=False, indent=2))
        
        print("\n⚙️ 适配规则:")
        rules = adapter.generate_adaptation_rules(device_info)
        print(json.dumps(rules, ensure_ascii=False, indent=2))
    else:
        print(f"🔄 更新JSON用例: {args.json_file}")
        output_file = adapter.update_json_testcase(args.json_file, args.output)
        print(f"✅ 更新完成: {output_file}")


if __name__ == "__main__":
    main()