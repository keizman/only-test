#!/usr/bin/env python3
"""
统一配置管理器使用示例
展示如何在项目中使用统一的配置访问入口
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入统一配置管理器
from lib.config_manager import get_config, get_config_section


def example_basic_usage():
    """基本使用示例"""
    print("📋 基本配置访问")
    print("-" * 30)
    
    # 获取单个配置值
    element_timeout = get_config("execution.timeouts.element_wait", 10)
    interaction_delay = get_config("device_types.android_phone.interaction_delay", 0.5)
    screenshot_quality = get_config("performance.screenshot.quality", 80)
    
    print(f"元素等待超时: {element_timeout}秒")
    print(f"交互延迟: {interaction_delay}秒")
    print(f"截图质量: {screenshot_quality}%")


def example_section_access():
    """配置段访问示例"""
    print("\n📦 配置段批量访问")
    print("-" * 30)
    
    # 获取整个配置段
    timeouts = get_config_section("execution.timeouts", {})
    device_android_phone = get_config_section("device_types.android_phone", {})
    
    print("所有超时配置:")
    for key, value in timeouts.items():
        print(f"  {key}: {value}")
    
    print("\nAndroid手机设备配置:")
    for key, value in device_android_phone.items():
        print(f"  {key}: {value}")


def example_device_adapter_integration():
    """DeviceAdapter集成示例"""
    print("\n🔗 DeviceAdapter集成")
    print("-" * 30)
    
    from lib.device_adapter import DeviceAdapter
    
    # DeviceAdapter会自动使用统一配置管理器
    adapter = DeviceAdapter()
    
    # 探测设备信息（使用缓存）
    device_info = adapter.detect_device_info()
    
    # 生成适配规则（使用配置值）
    adaptation_rules = adapter.generate_adaptation_rules()
    
    print(f"设备名称: {device_info.get('device_name', 'Unknown')}")
    print(f"操作延迟: {adaptation_rules.get('performance_adaptation', {}).get('action_delay', 'N/A')}")
    print(f"截图质量: {adaptation_rules.get('performance_adaptation', {}).get('screenshot_quality', 'N/A')}")


def example_custom_module():
    """自定义模块中使用配置的示例"""
    print("\n🛠️ 自定义模块配置使用")
    print("-" * 30)
    
    class CustomTestExecutor:
        """示例：自定义测试执行器"""
        
        def __init__(self):
            # 从配置获取执行参数
            self.default_timeout = get_config("execution.timeouts.default_step", 30)
            self.retry_count = get_config("execution.retry.max_retries", 3)
            self.retry_delay = get_config("execution.retry.retry_delay", 2)
            
        def execute_step(self, step_name: str):
            """执行测试步骤"""
            print(f"执行步骤: {step_name}")
            print(f"  超时设置: {self.default_timeout}秒")
            print(f"  重试次数: {self.retry_count}次")
            print(f"  重试间隔: {self.retry_delay}秒")
    
    # 使用自定义执行器
    executor = CustomTestExecutor()
    executor.execute_step("示例步骤")


def example_environment_override():
    """环境变量覆盖示例"""
    print("\n🌍 环境变量覆盖")
    print("-" * 30)
    
    import os
    
    # 设置环境变量覆盖配置
    os.environ["ONLY_TEST_EXECUTION_TIMEOUTS_ELEMENT_WAIT"] = "15"
    
    # 重新加载配置以应用环境变量
    from lib.config_manager import config_manager
    config_manager.reload_all_configs()
    
    # 获取被覆盖的配置值
    overridden_timeout = get_config("execution.timeouts.element_wait", 10)
    print(f"被环境变量覆盖的超时值: {overridden_timeout}")
    
    # 清理环境变量
    del os.environ["ONLY_TEST_EXECUTION_TIMEOUTS_ELEMENT_WAIT"]


if __name__ == "__main__":
    print("🔧 统一配置管理器使用示例")
    print("=" * 50)
    
    try:
        example_basic_usage()
        example_section_access()
        example_device_adapter_integration()
        example_custom_module()
        example_environment_override()
        
        print("\n🎉 所有示例运行成功！")
        print("\n💡 使用要点:")
        print("1. 使用 get_config(path, default) 获取单个配置值")
        print("2. 使用 get_config_section(section) 获取配置段")
        print("3. 支持点分隔路径访问嵌套配置")
        print("4. 自动加载多个配置文件并合并")
        print("5. 支持环境变量覆盖配置")
        print("6. 单例模式确保全局唯一配置实例")
        
    except Exception as e:
        print(f"❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()
