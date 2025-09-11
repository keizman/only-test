#!/usr/bin/env python3
"""
YAML Monitor
============

读取 only_test/testcases/main.yaml 并提供统一的查询与解析能力：
- 通过 app_id / package_name 任意一个解析应用
- 通过 device_id / adb_serial 任意一个解析设备
- 提供便捷的 ui_activity 查询

未来可扩展到 test_suites 等。
"""

from typing import Optional, Dict, Any
from dataclasses import asdict
from .config_manager import ConfigManager, ApplicationConfig, DeviceConfig


class YamlMonitor:
    def __init__(self, config_file: str = "testcases/main.yaml"):
        self.cm = ConfigManager(config_file=config_file)

    def resolve_application(self, identifier: str) -> Optional[Dict[str, Any]]:
        """根据 app_id 或 package_name 解析应用配置，返回字典。"""
        cfg = self.cm.get_config()
        apps = cfg.get('applications', {}) or {}
        # 1) 直接按 app_id 命中
        if identifier in apps:
            ac = self.cm.get_application_config(identifier)
            return asdict(ac) if ac else None
        # 2) 遍历按 package_name 命中
        ident_l = (identifier or '').strip().lower()
        for app_id, data in apps.items():
            if (data or {}).get('package_name', '').lower() == ident_l:
                ac = self.cm.get_application_config(app_id)
                return asdict(ac) if ac else None
        return None

    def resolve_device(self, identifier: str) -> Optional[Dict[str, Any]]:
        """根据 device_id 或 adb_serial 解析设备配置，返回字典。"""
        cfg = self.cm.get_config()
        devices = cfg.get('devices', {}) or {}
        # 1) 直接按 device_id 命中
        if identifier in devices:
            dc = self.cm.get_device_config(identifier)
            return asdict(dc) if dc else None
        # 2) 遍历按 adb_serial 命中
        ident_l = (identifier or '').strip().lower()
        for dev_id, data in devices.items():
            serial = ((data or {}).get('connection') or {}).get('adb_serial')
            if serial and str(serial).lower() == ident_l:
                dc = self.cm.get_device_config(dev_id)
                return asdict(dc) if dc else None
        return None

    def get_ui_activity(self, application_identifier: str) -> Optional[str]:
        """获取应用的 ui_activity（如配置存在）。"""
        cfg = self.cm.get_config()
        apps = cfg.get('applications', {}) or {}
        # 按 app_id 优先
        if application_identifier in apps:
            return (apps[application_identifier].get('ui_activity'))
        # 其次按 package_name
        ident_l = (application_identifier or '').strip().lower()
        for _, data in apps.items():
            if (data or {}).get('package_name', '').lower() == ident_l:
                return data.get('ui_activity')
        return None

    def get_package_name(self, application_identifier: str) -> Optional[str]:
        """获取应用的 package_name。"""
        app = self.resolve_application(application_identifier)
        return (app or {}).get('package_name')


if __name__ == '__main__':
    ym = YamlMonitor()
    print('apps:', ym.cm.list_applications())
    print('devices:', ym.cm.list_devices())
    print('resolve brav_mob:', ym.resolve_application('brav_mob'))
    print('resolve com.mobile.brasiltvmobile:', ym.resolve_application('com.mobile.brasiltvmobile'))
