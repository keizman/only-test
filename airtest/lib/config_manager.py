#!/usr/bin/env python3
"""
Only-Test 总控配置管理器

负责加载和管理main.yaml配置文件
提供配置访问、验证、合并等功能
支持环境变量覆盖和动态配置更新
"""

import os
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
    """总控配置管理器"""
    
    def __init__(self, config_file: str = "testcases/main.yaml", env_file: str = ".env"):
        """
        初始化配置管理器
        
        Args:
            config_file: 主配置文件路径
            env_file: 环境变量文件路径
        """
        self.project_root = Path(__file__).parent.parent
        self.config_file = self.project_root / config_file
        self.env_file = self.project_root / env_file
        
        # 配置缓存
        self._config_cache = None
        self._config_mtime = None
        
        # 加载环境变量
        self._load_env_file()
        
        # 验证配置文件
        self._validate_config_files()
    
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
            app_config=app_data.get('app_config', {}),
            common_scenarios=app_data.get('common_scenarios', [])
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
    """测试配置管理器"""
    config_manager = ConfigManager()
    
    print("🔧 Only-Test 配置管理器测试")
    print("=" * 50)
    
    # 测试设备列表
    devices = config_manager.list_devices()
    print(f"📱 可用设备: {devices}")
    
    # 测试应用列表
    applications = config_manager.list_applications()
    print(f"📦 可用应用: {applications}")
    
    # 测试设备配置获取
    if devices:
        device_config = config_manager.get_device_config(devices[0])
        print(f"🔍 设备配置示例: {device_config.custom_name}")
        print(f"   分辨率: {device_config.screen_info.get('resolution', 'Unknown')}")
        print(f"   密度: {device_config.screen_info.get('density', 'Unknown')}")
    
    # 测试应用配置获取
    if applications:
        app_config = config_manager.get_application_config(applications[0])
        print(f"📱 应用配置示例: {app_config.app_name}")
        print(f"   包名: {app_config.package_name}")
    
    # 测试路径模板
    if devices and applications:
        path = config_manager.get_path_template(
            'assets_path',
            app_package='com_example_app',
            device_model='Test_Device'
        )
        print(f"🗂️  资源路径示例: {path}")
    
    # 测试LLM配置
    llm_config = config_manager.get_llm_config()
    print(f"🤖 LLM配置: {llm_config.get('provider', 'None')}")


if __name__ == "__main__":
    main()