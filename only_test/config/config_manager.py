#!/usr/bin/env python3
"""
Only-Test 统一配置管理器 (Unified Configuration Manager)

负责加载和管理所有YAML配置文件，作为全局统一的配置访问入口
- 多配置文件支持: framework_config.yaml, device_config.yaml, main.yaml, metadata.yaml
- 配置合并和优先级管理
- 点分隔路径访问 (如: "device.android_phone.timeout")
- 环境变量覆盖
- 配置缓存和热重载
- 单例模式确保全局唯一实例

设计原则：
- 统一入口：所有模块通过此模块获取配置
- 向下兼容：保持原有API不变
- 扩展支持：新增通用配置访问方法
"""

import os
import threading
from pathlib import Path

try:
    import yaml
except ImportError:
    print("⚠️ 警告: PyYAML 未安装，请运行: pip install pyyaml>=6.0")
    print("⚠️ 当前使用简化配置加载模式")
    yaml = None
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime
import logging

# 设置日志
logger = logging.getLogger(__name__)


@dataclass
class DeviceConfig:
    """设备配置数据类"""
    device_id: str
    phone_type: str
    custom_name: str
    android_version: str
    screen_info: Dict[str, Any]
    hardware_info: Dict[str, Any]
    execution_config: Dict[str, Any]
    recognition_config: Dict[str, Any]
    connection: Dict[str, Any]
    description: str = ""


@dataclass
class ApplicationConfig:
    """应用配置数据类"""
    app_id: str
    package_name: str
    app_name: str
    category: str
    version: str
    description: str
    app_config: Dict[str, Any]
    common_scenarios: List[str]
    # 新增字段 - 从 YAML 中实际读取
    ui_activity: Optional[str] = None
    playback_auto_wake: Dict[str, Any] = None

    def __post_init__(self):
        """后处理，确保字段不为None"""
        if self.playback_auto_wake is None:
            self.playback_auto_wake = {}


@dataclass
class TestSuiteConfig:
    """测试套件配置数据类"""
    suite_id: str
    description: str
    devices: List[str]
    applications: List[str]
    test_scenarios: List[Dict[str, Any]]
    focus: str = ""


class ConfigManager:
    """统一配置管理器 - 单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_file: str = "testcases/main.yaml", env_file: str = ".env"):
        """
        初始化统一配置管理器
        
        Args:
            config_file: 主配置文件路径
            env_file: 环境变量文件路径
        """
        if self._initialized:
            return
            
        self.project_root = Path(__file__).parent.parent
        self.config_dir = Path(__file__).parent  # 现在就在config目录中
        self.testcases_dir = self.project_root / "testcases"
        
        # 主配置文件
        self.config_file = self.project_root / config_file
        self.env_file = self.project_root / env_file
        
        # 多配置文件支持 (按优先级排序，后加载的覆盖先加载的)
        self._config_files = [
            self.config_dir / "framework_config.yaml",
            self.config_dir / "device_config.yaml", 
            self.config_file,  # main.yaml
            self.testcases_dir / "metadata.yaml"
        ]
        
        # 配置缓存
        self._config_cache = None
        self._config_mtime = None
        self._multi_config_cache: Dict[str, Any] = {}
        self._file_mtimes: Dict[str, float] = {}
        self._merged_config: Dict[str, Any] = {}
        
        # 环境变量前缀
        self._env_prefix = "ONLY_TEST_"
        
        # 加载环境变量
        self._load_env_file()
        
        # 验证配置文件
        self._validate_config_files()
        
        # 加载所有配置文件
        self._load_all_configs()
        
        self._initialized = True
        logger.info(f"统一配置管理器已初始化，加载了 {len(self._multi_config_cache)} 个配置文件")
    
    def _load_all_configs(self) -> None:
        """加载所有配置文件"""
        self._multi_config_cache.clear()
        self._file_mtimes.clear()
        
        for config_file in self._config_files:
            if config_file.exists():
                try:
                    mtime = config_file.stat().st_mtime
                    self._file_mtimes[str(config_file)] = mtime
                    
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f) or {} if yaml else {}
                        self._multi_config_cache[str(config_file)] = config_data
                        
                    logger.debug(f"加载配置文件: {config_file.name}")
                    
                except (yaml.YAMLError if yaml else Exception, IOError, OSError) as e:
                    logger.warning(f"无法加载配置文件 {config_file}: {e}")
                    
        # 合并所有配置
        self._merge_all_configs()
    
    def _merge_all_configs(self) -> None:
        """合并所有配置文件为单一配置字典"""
        self._merged_config.clear()
        
        # 按优先级合并配置 (后面的覆盖前面的)
        for config_file in self._config_files:
            config_data = self._multi_config_cache.get(str(config_file), {})
            self._deep_merge_dict_inplace(self._merged_config, config_data)
        
        # 应用环境变量覆盖
        self._apply_env_overrides()
    
    def _deep_merge_dict_inplace(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """就地深度合并两个字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge_dict_inplace(target[key], value)
            else:
                target[key] = value
    
    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        for key, value in os.environ.items():
            if key.startswith(self._env_prefix):
                # 转换环境变量名为配置路径
                # 例: ONLY_TEST_DEVICE_TIMEOUT -> device.timeout
                config_path = key[len(self._env_prefix):].lower().replace('_', '.')
                
                # 尝试转换数据类型
                converted_value = self._convert_env_value(value)
                self._set_config_value(config_path, converted_value)
    
    def _convert_env_value(self, value: str) -> Any:
        """转换环境变量值的数据类型"""
        # 布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 整数
        try:
            return int(value)
        except ValueError:
            pass
        
        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass
        
        # 字符串
        return value
    
    def _set_config_value(self, path: str, value: Any) -> None:
        """设置配置值（支持点分隔路径）"""
        keys = path.split('.')
        current = self._merged_config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _check_multi_file_changes(self) -> bool:
        """检查多配置文件是否有变化"""
        for config_file in self._config_files:
            if config_file.exists():
                current_mtime = config_file.stat().st_mtime
                cached_mtime = self._file_mtimes.get(str(config_file), 0)
                
                if current_mtime > cached_mtime:
                    return True
        return False
    
    def _load_env_file(self):
        """加载环境变量文件"""
        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
    
    def _validate_config_files(self):
        """验证配置文件存在性"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"主配置文件不存在: {self.config_file}")
        
        if not self.env_file.exists():
            logger.warning(f"环境配置文件不存在: {self.env_file}")
    
    def _should_reload_config(self) -> bool:
        """检查是否需要重新加载配置"""
        if self._config_cache is None:
            return True
        
        current_mtime = self.config_file.stat().st_mtime
        return current_mtime != self._config_mtime
    
    def _load_config(self) -> Dict[str, Any]:
        """加载YAML配置文件"""
        if yaml is None:
            # 提供基本的配置结构以防止系统崩溃
            config = {
                'global_config': {'framework_version': '2.0.0', 'debug_mode': True},
                'devices': {},
                'applications': {},
                'test_suites': {},
                'llm_config': {'enabled': True, 'provider': 'openai_compatible'},
                'path_templates': {
                    'assets_path': 'assets/{app_package}_{device_model}',
                    'testcase_path': 'testcases/generated/{app_name}_{device_name}',
                    'report_path': 'reports/{suite_name}_{timestamp}',
                    'python_path': 'testcases/python/test_{app_name}_{scenario}.py'
                }
            }
        else:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        
        # 更新缓存
        self._config_cache = config
        self._config_mtime = self.config_file.stat().st_mtime
        
        # 应用环境变量覆盖
        config = self._apply_environment_overrides(config)
        
        return config
    
    def _apply_environment_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖"""
        # 获取当前环境
        env = os.getenv('ENVIRONMENT', 'development')
        
        # 应用环境特定配置
        if 'environments' in config and env in config['environments']:
            env_config = config['environments'][env]
            config = self._deep_merge_dict(config, env_config)
        
        # 应用环境变量中的LLM配置覆盖
        llm_config = config.get('llm_config', {})
        
        if os.getenv('LLM_PROVIDER'):
            llm_config['provider'] = os.getenv('LLM_PROVIDER')
        
        if os.getenv('LLM_TEMPERATURE'):
            llm_config.setdefault('generation_params', {})['temperature'] = float(os.getenv('LLM_TEMPERATURE'))
        
        config['llm_config'] = llm_config
        
        return config
    
    def _deep_merge_dict(self, base: Dict, override: Dict) -> Dict:
        """深度合并字典"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_dict(result[key], value)
            else:
                result[key] = value
        
        return result
    
    # ==================== 新增：统一配置访问方法 ====================
    
    def get(self, path: str, default: Any = None, auto_reload: bool = True) -> Any:
        """
        获取配置值 - 统一配置访问入口
        
        Args:
            path: 配置路径，支持点分隔 (如: "device.android_phone.timeout")
            default: 默认值
            auto_reload: 是否自动重载配置文件
            
        Returns:
            配置值或默认值
            
        Examples:
            config.get("execution.timeouts.element_wait", 10)
            config.get("device_types.android_phone.interaction_delay", 0.5)
            config.get("performance.screenshot.quality", 80)
        """
        # 检查是否需要重载配置
        if auto_reload and self._check_multi_file_changes():
            logger.info("检测到配置文件变化，重新加载配置")
            self._load_all_configs()
        
        # 解析配置路径
        keys = path.split('.')
        current = self._merged_config
        
        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current
        except (KeyError, TypeError):
            return default
    
    def get_section(self, section: str, default: Optional[Dict] = None) -> Dict[str, Any]:
        """
        获取配置段
        
        Args:
            section: 配置段名称 (如: "device_types", "execution.timeouts")
            default: 默认值
            
        Returns:
            配置段字典
        """
        result = self.get(section, default or {})
        return result if isinstance(result, dict) else (default or {})
    
    def set_runtime_config(self, path: str, value: Any) -> None:
        """
        设置运行时配置值（不会保存到文件）
        
        Args:
            path: 配置路径
            value: 配置值
        """
        self._set_config_value(path, value)
    
    def reload_all_configs(self) -> None:
        """强制重载所有配置文件"""
        logger.info("强制重载所有配置文件")
        self._load_all_configs()
    
    def get_loaded_config_files(self) -> List[str]:
        """获取已加载的配置文件列表"""
        return [str(f) for f in self._config_files if str(f) in self._multi_config_cache]
    
    def get_merged_config(self) -> Dict[str, Any]:
        """获取合并后的完整配置（调试用）"""
        return self._merged_config.copy()
    
    def add_config_file(self, config_file: Union[str, Path]) -> None:
        """
        动态添加配置文件
        
        Args:
            config_file: 配置文件路径
        """
        config_path = Path(config_file)
        if config_path not in self._config_files:
            self._config_files.append(config_path)
            self._load_all_configs()
            logger.info(f"添加配置文件: {config_path}")
    
    # ==================== 原有方法保持不变 ====================
    
    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        if self._should_reload_config():
            self._config_cache = self._load_config()
        
        return self._config_cache.copy()
    
    def get_global_config(self) -> Dict[str, Any]:
        """获取全局配置"""
        config = self.get_config()
        return config.get('global_config', {})
    
    def get_device_config(self, device_id: str) -> Optional[DeviceConfig]:
        """
        获取设备配置
        
        Args:
            device_id: 设备ID
            
        Returns:
            DeviceConfig: 设备配置对象
        """
        config = self.get_config()
        devices = config.get('devices', {})
        
        if device_id not in devices:
            return None
        
        device_data = devices[device_id]
        
        return DeviceConfig(
            device_id=device_id,
            phone_type=device_data.get('phone_type', 'android_phone'),
            custom_name=device_data.get('custom_name', device_id),
            android_version=device_data.get('android_version', 'Unknown'),
            screen_info=device_data.get('screen_info', {}),
            hardware_info=device_data.get('hardware_info', {}),
            execution_config=device_data.get('execution_config', {}),
            recognition_config=device_data.get('recognition_config', {}),
            connection=device_data.get('connection', {}),
            description=device_data.get('description', '')
        )
    
    def get_application_config(self, app_id: str) -> Optional[ApplicationConfig]:
        """
        获取应用配置
        
        Args:
            app_id: 应用ID
            
        Returns:
            ApplicationConfig: 应用配置对象
        """
        config = self.get_config()
        applications = config.get('applications', {})
        
        if app_id not in applications:
            return None
        
        app_data = applications[app_id]
        
        return ApplicationConfig(
            app_id=app_id,
            package_name=app_data.get('package_name', ''),
            app_name=app_data.get('app_name', app_id),
            category=app_data.get('category', 'unknown'),
            version=app_data.get('version', 'latest'),
            description=app_data.get('description', ''),
            app_config=app_data,  # 保留完整的原始配置
            common_scenarios=app_data.get('common_scenarios', []),
            # 新增字段读取
            ui_activity=app_data.get('ui_activity'),
            playback_auto_wake=app_data.get('playback_auto_wake', {})
        )
    
    def get_test_suite_config(self, suite_id: str) -> Optional[TestSuiteConfig]:
        """
        获取测试套件配置
        
        Args:
            suite_id: 套件ID
            
        Returns:
            TestSuiteConfig: 测试套件配置对象
        """
        config = self.get_config()
        test_suites = config.get('test_suites', {})
        
        if suite_id not in test_suites:
            return None
        
        suite_data = test_suites[suite_id]
        
        return TestSuiteConfig(
            suite_id=suite_id,
            description=suite_data.get('description', ''),
            devices=suite_data.get('devices', []),
            applications=suite_data.get('applications', []),
            test_scenarios=suite_data.get('test_scenarios', []),
            focus=suite_data.get('focus', '')
        )
    
    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        config = self.get_config()
        llm_config = config.get('llm_config', {})

        # 从环境变量获取敏感信息
        if os.getenv('LLM_API_KEY'):
            llm_config['api_key'] = os.getenv('LLM_API_KEY')
        if os.getenv('LLM_API_URL'):
            llm_config['api_url'] = os.getenv('LLM_API_URL')
        if os.getenv('LLM_MODEL'):
            llm_config['model'] = os.getenv('LLM_MODEL')

        return llm_config

    def get_playback_auto_wake_config(self) -> Dict[str, Any]:
        """获取全局播放自动唤起配置"""
        config = self.get_config()
        global_config = config.get('global_config', {})
        return global_config.get('playback_auto_wake', {})

    def get_merged_playback_config(self, app_id: str) -> Dict[str, Any]:
        """获取合并后的播放配置（全局配置 + 应用特定配置）"""
        # 获取全局配置
        global_playback = self.get_playback_auto_wake_config()

        # 获取应用特定配置
        app_config = self.get_application_config(app_id)
        app_playback = app_config.playback_auto_wake if app_config else {}

        # 深度合并配置，应用配置覆盖全局配置
        merged = self._deep_merge_dict(global_playback.copy(), app_playback)
        return merged
    
    def get_path_template(self, template_name: str, **kwargs) -> str:
        """
        获取路径模板并填充变量
        
        Args:
            template_name: 模板名称
            **kwargs: 模板变量
            
        Returns:
            str: 填充后的路径
        """
        config = self.get_config()
        templates = config.get('path_templates', {})
        
        if template_name not in templates:
            raise ValueError(f"路径模板不存在: {template_name}")
        
        template = templates[template_name]
        
        # 添加时间戳
        kwargs.setdefault('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"路径模板缺少变量: {e}")
    
    def list_devices(self) -> List[str]:
        """列出所有设备ID"""
        config = self.get_config()
        return list(config.get('devices', {}).keys())
    
    def list_applications(self) -> List[str]:
        """列出所有应用ID"""
        config = self.get_config()
        return list(config.get('applications', {}).keys())
    
    def list_test_suites(self) -> List[str]:
        """列出所有测试套件ID"""
        config = self.get_config()
        return list(config.get('test_suites', {}).keys())
    
    def validate_device_app_combination(self, device_id: str, app_id: str) -> bool:
        """
        验证设备和应用组合的有效性
        
        Args:
            device_id: 设备ID
            app_id: 应用ID
            
        Returns:
            bool: 是否有效
        """
        device_config = self.get_device_config(device_id)
        app_config = self.get_application_config(app_id)
        
        if not device_config or not app_config:
            return False
        
        # 可以添加更多验证逻辑，比如：
        # - 检查应用是否支持设备的Android版本
        # - 检查设备类型是否适合应用类别
        
        return True
    
    def get_device_app_config(self, device_id: str, app_id: str) -> Optional[Dict[str, Any]]:
        """
        获取设备-应用组合的完整配置
        
        Args:
            device_id: 设备ID
            app_id: 应用ID
            
        Returns:
            Dict: 组合配置
        """
        if not self.validate_device_app_combination(device_id, app_id):
            return None
        
        device_config = self.get_device_config(device_id)
        app_config = self.get_application_config(app_id)
        
        return {
            'device': device_config,
            'application': app_config,
            'assets_path': self.get_path_template(
                'assets_path',
                app_package=app_config.package_name.replace('.', '_'),
                device_model=device_config.hardware_info.get('model', 'Unknown')
            ),
            'testcase_path': self.get_path_template(
                'testcase_path',
                app_name=app_config.app_name,
                device_name=device_config.custom_name.replace(' ', '_')
            )
        }
    
    def save_device_info_cache(self, device_id: str, detected_info: Dict[str, Any]):
        """
        保存设备探测信息到配置缓存
        
        Args:
            device_id: 设备ID
            detected_info: 探测到的设备信息
        """
        # 这里可以实现将探测到的信息保存到缓存文件
        # 避免每次都重新探测
        cache_file = self.project_root / "cache" / f"{device_id}_info.json"
        cache_file.parent.mkdir(exist_ok=True)
        
        import json
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'device_id': device_id,
                'detected_info': detected_info,
                'cached_at': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"设备信息已缓存: {cache_file}")
    
    def get_cached_device_info(self, device_id: str, max_age_hours: int = 24) -> Optional[Dict[str, Any]]:
        """
        获取缓存的设备信息
        
        Args:
            device_id: 设备ID
            max_age_hours: 缓存有效期(小时)
            
        Returns:
            Dict: 缓存的设备信息
        """
        cache_file = self.project_root / "cache" / f"{device_id}_info.json"
        
        if not cache_file.exists():
            return None
        
        import json
        from datetime import timedelta
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 检查缓存是否过期
        cached_at = datetime.fromisoformat(cache_data['cached_at'])
        if datetime.now() - cached_at > timedelta(hours=max_age_hours):
            logger.info(f"设备缓存已过期: {cache_file}")
            return None
        
        return cache_data.get('detected_info')


def main():
    """Configuration manager test"""
    config_manager = ConfigManager()

    print("Only-Test Configuration Manager Test")
    print("=" * 50)

    devices = config_manager.list_devices()
    print(f"Available devices: {devices}")

    applications = config_manager.list_applications()
    print(f"Available applications: {applications}")

    if devices:
        device_config = config_manager.get_device_config(devices[0])
        print(f"Device config example:")
        print(f"  device_id: {device_config.device_id}")
        print(f"  custom_name: {device_config.custom_name}")
        print(f"  resolution: {device_config.screen_info.get('resolution', 'Unknown')}")
        print(f"  density: {device_config.screen_info.get('density', 'Unknown')}")

    if applications:
        app_config = config_manager.get_application_config(applications[0])
        print(f"Application config example:")
        print(f"  app_id: {app_config.app_id}")
        print(f"  app_name: {app_config.app_name}")
        print(f"  package_name: {app_config.package_name}")
        print(f"  ui_activity: {app_config.ui_activity}")
        print(f"  playback_auto_wake: {app_config.playback_auto_wake}")
        print(f"  app_config_fields: {len(app_config.app_config)}")

        merged_playback = config_manager.get_merged_playback_config(applications[0])
        print(f"Merged playback config: {merged_playback}")

    global_playback = config_manager.get_playback_auto_wake_config()
    print(f"Global playback config: {global_playback}")

    if devices and applications:
        path = config_manager.get_path_template(
            'assets_path',
            app_package='com_example_app',
            device_model='Test_Device'
        )
        print(f"Assets path example: {path}")

    llm_config = config_manager.get_llm_config()
    print(f"LLM config provider: {llm_config.get('provider', 'None')}")


# ==================== 全局配置实例和便捷函数 ====================

# 全局配置管理器实例（单例）
config_manager = ConfigManager()

# 便捷函数 - 统一配置访问入口
def get_config(path: str, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    return config_manager.get(path, default)

def get_config_section(section: str, default: Optional[Dict] = None) -> Dict[str, Any]:
    """获取配置段的便捷函数"""
    return config_manager.get_section(section, default)

def reload_config() -> None:
    """重载配置的便捷函数"""
    config_manager.reload_all_configs()

def set_runtime_config(path: str, value: Any) -> None:
    """设置运行时配置的便捷函数"""
    config_manager.set_runtime_config(path, value)

# 向下兼容的别名
get_unified_config = get_config
get_unified_config_section = get_config_section


if __name__ == "__main__":
    main()
    
    # 测试统一配置功能
    print("\n" + "=" * 50)
    print("🔧 统一配置管理器测试")
    print("=" * 50)
    
    # 基本使用
    print(f"元素等待超时: {get_config('execution.timeouts.element_wait', 10)}")
    print(f"交互延迟: {get_config('device_types.android_phone.interaction_delay', 0.5)}")
    print(f"截图质量: {get_config('performance.screenshot.quality', 80)}")
    
    # 获取配置段
    timeouts = get_config_section("execution.timeouts")
    print(f"所有超时配置: {timeouts}")
    
    # 配置信息
    print(f"已加载配置文件: {len(config_manager.get_loaded_config_files())}")
    print(f"配置文件列表: {[Path(f).name for f in config_manager.get_loaded_config_files()]}")
    print(f"配置实例: {config_manager}")