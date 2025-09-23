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


def get_android_poco(use_airtest_input=False, screenshot_each_action=False, disable_cache=True):
    """获取AndroidPoco实例，使用与example_airtest_record.py相同的导入方式"""
    try:
        print("正在初始化Poco...")

        # 路径已在模块导入时设置，直接导入
        from poco.drivers.android.uiautomation2 import AndroidUiautomator2Poco
        print("✓ 成功导入AndroidUiautomator2Poco类")

        # 禁用缓存机制 (解决缓存导致的元素定位问题)
        if disable_cache:
            disable_poco_cache()
            disable_dumper_cache()

        # 应用set_text增强补丁
        patch_poco_set_text()

        # 使用您要求的参数设置: use_airtest_input=False, screenshot_each_action=False
        poco = AndroidUiautomator2Poco(use_airtest_input=use_airtest_input, screenshot_each_action=screenshot_each_action)
        print("✓ 使用本地Poco库成功创建AndroidUiautomator2Poco实例")
        print(f"✓ 设置: use_airtest_input={use_airtest_input}, screenshot_each_action={screenshot_each_action}")

        if disable_cache:
            print("✓ 缓存已禁用 - 每次查询都获取最新UI状态")

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


def force_refresh_ui_cache(poco_instance):
    """
    强制刷新Poco/UIAutomator2的UI缓存

    Args:
        poco_instance: Poco实例

    Returns:
        bool: 刷新是否成功
    """
    try:
        # 方法1: 尝试刷新dumper缓存（最彻底）
        if hasattr(poco_instance, 'agent') and hasattr(poco_instance.agent, 'hierarchy'):
            if hasattr(poco_instance.agent.hierarchy, 'dumper'):
                if hasattr(poco_instance.agent.hierarchy.dumper, 'invalidate_cache'):
                    poco_instance.agent.hierarchy.dumper.invalidate_cache()
                    print("✓ 已刷新dumper缓存")
                    return True
                elif hasattr(poco_instance.agent.hierarchy.dumper, '_root_node'):
                    # 如果没有invalidate_cache方法，直接清除根节点缓存
                    poco_instance.agent.hierarchy.dumper._root_node = None
                    print("✓ 已清除根节点缓存")
                    return True

        print("⚠ 无法访问dumper缓存，刷新可能不完整")
        return False

    except Exception as e:
        print(f"❌ 缓存刷新失败: {e}")
        return False


def get_text_with_refresh(selector, max_retries=2):
    """
    获取文本时自动处理缓存刷新

    Args:
        selector: Poco选择器
        max_retries: 最大重试次数

    Returns:
        str: 元素文本
    """
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"尝试第{attempt}次刷新...")
                selector.refresh()  # 使用Poco内置刷新

            return selector.get_text()

        except Exception as e:
            if attempt < max_retries:
                print(f"获取文本失败，重试中... ({e})")
                continue
            else:
                raise


# 重写UIObjectProxy的set_text方法，让它返回实际文本
def enhanced_set_text_method(self, text):
    """
    增强版的set_text方法 - 返回实际文本内容

    由于缓存已被禁用，不需要手动刷新缓存

    Args:
        text: 要设置的文本

    Returns:
        str: 实际设置后的文本内容
    """
    # 1. 执行原始的文本设置
    self.setattr('text', text)

    # 2. 由于缓存已被禁用，get_text()会自动获取最新状态
    actual_text = self.get_text()

    # 3. 验证是否输入成功
    if actual_text == text:
        return text
    else:
        print(f"Warning: 输入可能失败: 期望'{text}', 实际'{actual_text}'")
        return f"Warning: 输入可能失败: 期望'{text}', 实际'{actual_text}'"
    


def disable_poco_cache():
    """
    彻底禁用Poco的缓存机制，让每次查询都重新获取UI状态
    """
    try:
        from poco.proxy import UIObjectProxy

        # 1. 重写_do_query方法，强制每次都刷新
        def no_cache_do_query(self, multiple=True, refresh=True):
            """无缓存的查询方法 - 每次都重新获取"""
            # 强制refresh=True，忽略_evaluated状态
            raw = self.poco.agent.hierarchy.select(self.query, multiple)
            if multiple:
                self._nodes = raw
                self._nodes_proxy_is_list = True
            else:
                if isinstance(raw, list):
                    self._nodes = raw[0] if len(raw) > 0 else None
                else:
                    self._nodes = raw
                self._nodes_proxy_is_list = False

            if not self._nodes:
                self.invalidate()
                from poco.exceptions import PocoNoSuchNodeException
                raise PocoNoSuchNodeException(self)

            # 不设置_evaluated=True，让下次查询继续刷新
            self._query_multiple = multiple
            return self._nodes

        # 2. 重写exists方法，每次都刷新
        def no_cache_exists(self):
            """无缓存的exists检查"""
            try:
                self._do_query(multiple=False, refresh=True)
                return True
            except:
                return False

        # 3. 重写get_text方法，每次都刷新
        def no_cache_get_text(self):
            """无缓存的get_text"""
            nodes = self._do_query(multiple=False, refresh=True)
            return self.poco.agent.hierarchy.getAttr(nodes, 'text') or ''

        # 备份原始方法
        if not hasattr(UIObjectProxy, '_original_do_query'):
            UIObjectProxy._original_do_query = UIObjectProxy._do_query
            UIObjectProxy._original_exists = UIObjectProxy.exists
            UIObjectProxy._original_get_text = UIObjectProxy.get_text

        # 替换为无缓存版本
        UIObjectProxy._do_query = no_cache_do_query
        UIObjectProxy.exists = no_cache_exists
        UIObjectProxy.get_text = no_cache_get_text

        print("✓ Poco缓存已完全禁用 (每次查询都重新获取UI状态)")
        return True

    except Exception as e:
        print(f"⚠ 禁用Poco缓存失败: {e}")
        return False


def disable_dumper_cache():
    """
    禁用UIAutomator2Dumper的缓存机制
    """
    try:
        from poco.drivers.android.uiautomation2 import UIAutomator2Dumper

        # 重写getRoot方法，每次都重新获取
        def no_cache_getRoot(self):
            """无缓存的getRoot - 每次都刷新"""
            self._root_node = None  # 强制清除缓存
            self._update_hierarchy()
            return self._root_node

        # 备份原始方法
        if not hasattr(UIAutomator2Dumper, '_original_getRoot'):
            UIAutomator2Dumper._original_getRoot = UIAutomator2Dumper.getRoot

        # 替换为无缓存版本
        UIAutomator2Dumper.getRoot = no_cache_getRoot

        print("✓ UIAutomator2Dumper缓存已禁用 (每次都重新获取UI层次)")
        return True

    except Exception as e:
        print(f"⚠ 禁用Dumper缓存失败: {e}")
        return False


def patch_poco_set_text():
    """
    替换Poco的set_text方法为增强版本
    """
    try:
        from poco.proxy import UIObjectProxy
        # 备份原始方法
        if not hasattr(UIObjectProxy, '_original_set_text'):
            UIObjectProxy._original_set_text = UIObjectProxy.set_text

        # 替换为增强版本
        UIObjectProxy.set_text = enhanced_set_text_method
        # print("✓ Poco set_text方法已增强 (自动刷新缓存并返回实际文本)")
        return True
    except Exception as e:
        print(f"⚠ 增强set_text方法失败: {e}")
        return False


if __name__ == "__main__":
    # 测试导入
    try:
        setup_local_poco_path()
        print("本地Poco库路径设置成功")
        
        # 只测试路径设置，不创建poco实例（需要airtest环境）
        print("路径设置测试通过")
        
    except Exception as e:
        print(f"测试失败: {e}")
