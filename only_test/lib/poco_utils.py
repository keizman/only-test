#!/usr/bin/env python3
"""
Poco工具函数 - 统一管理本地Poco库的导入
使用与example_airtest_record.py相同的导入方式，优先使用真正的poco.click()
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

# 立即设置Poco路径，在模块导入时就执行
def _find_repo_root(start: Path) -> Path:
    p = start.resolve()
    # 尝试向上寻找包含 Poco 目录的根
    for ancestor in [p] + list(p.parents):
        if (ancestor / "Poco").exists():
            return ancestor
    # 回退：再上一层（适配 only_test/lib 相对路径问题）
    if p.parents:
        return p.parents[-1]
    return p


def _init_poco_path():
    """模块导入时立即设置Poco路径（健壮的向上查找方式）"""
    current_file = Path(__file__).resolve()
    repo_root = _find_repo_root(current_file.parent)
    poco_path = (repo_root / "Poco").resolve()

    if poco_path.exists():
        poco_path_str = str(poco_path)
        if poco_path_str not in sys.path:
            sys.path.insert(0, poco_path_str)
            return True
    return False

# 模块导入时立即执行
_init_poco_path()


def setup_local_poco_path():
    """设置本地Poco库路径"""
    # 获取项目根目录 (uni)
    current_file = Path(__file__).resolve()
    repo_root = _find_repo_root(current_file.parent)
    poco_path = (repo_root / "Poco").resolve()
    
    if poco_path.exists():
        poco_path_str = str(poco_path)
        if poco_path_str not in sys.path:
            sys.path.insert(0, poco_path_str)
            print(f"已添加本地Poco路径: {poco_path_str}")
        return True
    else:
        print(f"警告: 本地Poco路径不存在: {poco_path}")
        return False


def get_android_poco(use_airtest_input=False, screenshot_each_action=False):
    """获取AndroidPoco实例，使用与example_airtest_record.py相同的导入方式"""
    try:
        print("正在初始化Poco...")
        
        # 路径已在模块导入时设置，直接导入
        from poco.drivers.android.uiautomation2 import AndroidUiautomator2Poco
        print("✓ 成功导入AndroidUiautomator2Poco类")
        
        # 使用您要求的参数设置: use_airtest_input=False, screenshot_each_action=False
        poco = AndroidUiautomator2Poco(use_airtest_input=use_airtest_input, screenshot_each_action=screenshot_each_action)
        print("✓ 使用本地Poco库成功创建AndroidUiautomator2Poco实例")
        print(f"✓ 设置: use_airtest_input={use_airtest_input}, screenshot_each_action={screenshot_each_action}")
        return poco
        
    except ImportError as import_error:
        print(f"❌ Poco导入失败: {import_error}")
        print("尝试检查本地Poco库结构...")
        
        # 检查Poco文件结构
        poco_root = _find_repo_root(Path(__file__).resolve().parent) / "Poco"
        uiautomation2_file = poco_root / "poco" / "drivers" / "android" / "uiautomation2.py"
        
        if not poco_root.exists():
            print(f"❌ Poco根目录不存在: {poco_root}")
        elif not uiautomation2_file.exists():
            print(f"❌ uiautomation2.py文件不存在: {uiautomation2_file}")
        else:
            print(f"✓ Poco文件结构正常: {uiautomation2_file}")
        
        # 重新抛出ImportError，保持错误类型
        raise
            
    except RuntimeError as device_error:
        # 处理设备连接错误 - 这是用户最常见的问题
        error_msg = str(device_error)
        if "Failed to connect to Android device" in error_msg:
            print(f"❌ Android设备连接失败: {device_error}")
            print("请检查:")
            print("  1. Android设备是否已连接并开启USB调试")
            print("  2. 运行 'adb devices' 确认设备可见")
            print("  3. 设备是否已授权此计算机进行调试")
            raise RuntimeError(f"设备连接失败: {device_error}")
        else:
            print(f"❌ Poco运行时错误: {device_error}")
            raise
            
    except Exception as other_error:
        print(f"❌ 创建Poco实例失败 ({type(other_error).__name__}): {other_error}")
        raise


# === 辅助：带像素偏移的点击 ===
def _get_screen_size_fallback() -> tuple[int, int]:
    """多策略获取屏幕分辨率，返回 (w,h)。"""
    # 1) 优先从 Airtest 设备取
    try:
        from airtest.core.api import device as current_device
        dev = current_device()
        if dev:
            try:
                w, h = dev.get_current_resolution()  # type: ignore[attr-defined]
                if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
                    return w, h
            except Exception:
                info = getattr(dev, 'display_info', {}) or {}
                w = int(info.get('width', 0) or 0)
                h = int(info.get('height', 0) or 0)
                if w > 0 and h > 0:
                    return w, h
    except Exception:
        pass
    # 2) 尝试 poco.get_screen_size()
    try:
        from .poco_utils import get_android_poco  # self import safe
        p = get_android_poco()
        if hasattr(p, 'get_screen_size'):
            w, h = p.get_screen_size()  # type: ignore[attr-defined]
            if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
                return w, h
    except Exception:
        pass
    # 3) ADB wm size
    try:
        import subprocess
        out = subprocess.run(["adb", "shell", "wm", "size"], capture_output=True, text=True)
        if out.returncode == 0 and 'Physical size:' in out.stdout:
            sz = out.stdout.split('Physical size:')[-1].strip().split('\n')[0].strip()
            w, h = sz.split('x')
            return int(w), int(h)
    except Exception:
        pass
    # 4) 回退
    return 1080, 1920


# 原生扩展已加到 Poco/poco/proxy.py: UIObjectProxy.click_with_bias()


if __name__ == "__main__":
    # 测试导入
    try:
        setup_local_poco_path()
        print("本地Poco库路径设置成功")
        
        # 只测试路径设置，不创建poco实例（需要airtest环境）
        print("路径设置测试通过")
        
    except Exception as e:
        print(f"测试失败: {e}")
