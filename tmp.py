import uiautomator2 as u2
import subprocess
import re
import json
from typing import Dict, List, Tuple, Optional


def check_system_ui_visibility(device_address=None) -> Dict[str, bool]:
    """
    检查系统UI的可见性状态
    返回: {'status_bar': bool, 'navigation_bar': bool, 'immersive': bool}
    """
    try:
        d = u2.connect(device_address) if device_address else u2.connect()
        
        # 方法1: 通过ADB检查系统UI可见性
        device_id = device_address if device_address else d.serial
        
        # 检查immersive模式
        cmd = f"adb -s {device_id} shell settings get global policy_control"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        immersive_mode = "immersive" in result.stdout.lower()
        
        # 检查状态栏
        status_bar_visible = True
        nav_bar_visible = True
        
        # 通过UI hierarchy检查系统栏
        xml_content = d.dump_hierarchy()
        
        # 查找状态栏
        if "com.android.systemui:id/status_bar" in xml_content or "StatusBar" in xml_content:
            status_bar_visible = True
        else:
            # 进一步检查是否有状态栏相关元素
            status_bar_visible = "android:id/statusBarBackground" in xml_content
        
        # 查找导航栏
        if "com.android.systemui:id/navigation_bar" in xml_content or "NavigationBar" in xml_content:
            nav_bar_visible = True
        else:
            nav_bar_visible = "android:id/navigationBarBackground" in xml_content
        
        return {
            'status_bar': status_bar_visible,
            'navigation_bar': nav_bar_visible,
            'immersive': immersive_mode
        }
        
    except Exception as e:
        print(f"检查系统UI可见性失败: {e}")
        return {'status_bar': True, 'navigation_bar': True, 'immersive': False}


def get_window_flags(device_address=None) -> Dict[str, bool]:
    """
    通过ADB获取当前窗口的标志位
    """
    try:
        device_id = device_address if device_address else u2.connect().serial
        
        # 获取当前activity的窗口信息
        cmd = f"adb -s {device_id} shell dumpsys window windows | grep -A 20 'mCurrentFocus'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        window_info = result.stdout
        
        flags = {
            'fullscreen': 'FLAG_FULLSCREEN' in window_info,
            'hide_navigation': 'FLAG_HIDE_NAVIGATION' in window_info,
            'immersive': 'FLAG_IMMERSIVE' in window_info,
            'immersive_sticky': 'FLAG_IMMERSIVE_STICKY' in window_info,
            'layout_fullscreen': 'FLAG_LAYOUT_FULLSCREEN' in window_info,
            'layout_hide_navigation': 'FLAG_LAYOUT_HIDE_NAVIGATION' in window_info
        }
        
        return flags
        
    except Exception as e:
        print(f"获取窗口标志失败: {e}")
        return {}


def check_media_app_fullscreen_adb(device_address=None) -> Dict[str, any]:
    """
    使用ADB命令检查媒体应用是否处于全屏状态
    """
    try:
        device_id = device_address if device_address else u2.connect().serial
        
        # 1. 检查当前前台应用
        cmd = f"adb -s {device_id} shell dumpsys activity activities | grep mResumedActivity"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        current_app = result.stdout.strip()
        
        # 2. 检查系统UI可见性
        cmd = f"adb -s {device_id} shell dumpsys window | grep 'mSystemUiVisibility'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        system_ui_visibility = result.stdout
        
        # 3. 检查窗口标志
        window_flags = get_window_flags(device_address)
        
        # 4. 检查屏幕方向
        cmd = f"adb -s {device_id} shell dumpsys display | grep 'mCurrentOrientation'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        orientation = result.stdout.strip()
        
        # 分析结果
        is_fullscreen = (
            window_flags.get('fullscreen', False) or
            window_flags.get('immersive', False) or
            window_flags.get('immersive_sticky', False) or
            'SYSTEM_UI_FLAG_FULLSCREEN' in system_ui_visibility or
            'SYSTEM_UI_FLAG_HIDE_NAVIGATION' in system_ui_visibility
        )
        
        return {
            'is_fullscreen': is_fullscreen,
            'current_app': current_app,
            'window_flags': window_flags,
            'system_ui_visibility': system_ui_visibility,
            'orientation': orientation,
            'detection_method': 'adb_comprehensive'
        }
        
    except Exception as e:
        print(f"ADB检测失败: {e}")
        return {'is_fullscreen': False, 'error': str(e)}


def check_media_fullscreen_ui_analysis(device_address=None) -> Dict[str, any]:
    """
    通过UI分析检测媒体播放全屏状态
    """
    try:
        d = u2.connect(device_address) if device_address else u2.connect()
        
        # 获取屏幕尺寸
        screen_width, screen_height = d.window_size()
        
        # 获取UI层次结构
        xml_content = d.dump_hierarchy()
        
        # 检查常见的媒体播放器类名
        media_classes = [
            "android.widget.VideoView",
            "com.google.android.exoplayer2.ui.PlayerView",
            "android.webkit.WebView",  # 网页播放器
            "SurfaceView",  # 视频渲染表面
            "TextureView",  # 视频纹理视图
        ]
        
        found_players = []
        for class_name in media_classes:
            elements = d(className=class_name)
            if elements.exists:
                for i in range(elements.count):
                    try:
                        info = elements[i].info
                        bounds = info.get('bounds', {})
                        if bounds:
                            player_info = {
                                'class': class_name,
                                'bounds': bounds,
                                'visible': info.get('visible', False),
                                'index': i
                            }
                            found_players.append(player_info)
                    except:
                        continue
        
        # 分析是否全屏
        is_fullscreen = False
        fullscreen_threshold = 0.9  # 90%屏幕覆盖率认为是全屏
        
        for player in found_players:
            bounds = player['bounds']
            if bounds:
                width = bounds.get('right', 0) - bounds.get('left', 0)
                height = bounds.get('bottom', 0) - bounds.get('top', 0)
                
                # 计算覆盖率
                coverage_ratio = (width * height) / (screen_width * screen_height)
                
                if coverage_ratio >= fullscreen_threshold:
                    is_fullscreen = True
                    break
        
        # 检查系统UI状态
        system_ui_info = check_system_ui_visibility(device_address)
        
        return {
            'is_fullscreen': is_fullscreen,
            'found_players': found_players,
            'screen_size': (screen_width, screen_height),
            'system_ui': system_ui_info,
            'detection_method': 'ui_analysis'
        }
        
    except Exception as e:
        print(f"UI分析检测失败: {e}")
        return {'is_fullscreen': False, 'error': str(e)}


def is_media_fullscreen_comprehensive(device_address=None, verbose=True) -> Dict[str, any]:
    """
    综合多种方法检测媒体播放全屏状态
    """
    results = {
        'final_result': False,
        'confidence': 0.0,
        'methods': {}
    }
    
    try:
        # 方法1: ADB检测
        if verbose:
            print("🔍 使用ADB方法检测...")
        adb_result = check_media_app_fullscreen_adb(device_address)
        results['methods']['adb'] = adb_result
        
        # 方法2: UI分析检测
        if verbose:
            print("🔍 使用UI分析方法检测...")
        ui_result = check_media_fullscreen_ui_analysis(device_address)
        results['methods']['ui_analysis'] = ui_result
        
        # 综合判断
        adb_fullscreen = adb_result.get('is_fullscreen', False)
        ui_fullscreen = ui_result.get('is_fullscreen', False)
        
        # 计算置信度
        confidence = 0
        if adb_fullscreen and ui_fullscreen:
            confidence = 0.95
            results['final_result'] = True
        elif adb_fullscreen or ui_fullscreen:
            confidence = 0.7
            results['final_result'] = True
        else:
            confidence = 0.1
            results['final_result'] = False
        
        results['confidence'] = confidence
        
        if verbose:
            print(f"📊 检测结果: {'全屏' if results['final_result'] else '非全屏'} (置信度: {confidence:.1%})")
        
        return results
        
    except Exception as e:
        print(f"综合检测失败: {e}")
        results['error'] = str(e)
        return results


# 使用示例和测试
if __name__ == "__main__":
    print("🎬 媒体播放全屏状态检测")
    print("=" * 50)
    
    # 综合检测
    result = is_media_fullscreen_comprehensive(verbose=True)
    
    print("\n📋 详细结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 简单调用
    print(f"\n✅ 简单结果: {'当前处于全屏播放状态' if result['final_result'] else '当前未处于全屏播放状态'}")


def quick_fullscreen_check_adb_only(device_address=None) -> bool:
    """
    纯ADB方式快速检查全屏状态（不依赖uiautomator2）
    """
    try:
        device_id = device_address if device_address else ""
        device_param = f"-s {device_id}" if device_id else ""
        
        # 检查系统UI可见性标志
        cmd = f"adb {device_param} shell dumpsys window | grep -E '(mSystemUiVisibility|FLAG_FULLSCREEN|FLAG_IMMERSIVE)'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = result.stdout.lower()
        
        # 检查全屏相关标志
        fullscreen_indicators = [
            'flag_fullscreen',
            'flag_immersive',
            'system_ui_flag_fullscreen',
            'system_ui_flag_hide_navigation'
        ]
        
        for indicator in fullscreen_indicators:
            if indicator in output:
                return True
        
        return False
        
    except Exception as e:
        print(f"纯ADB检测失败: {e}")
        return False


def get_current_app_info(device_address=None) -> Dict[str, str]:
    """
    获取当前前台应用信息
    """
    try:
        device_id = device_address if device_address else ""
        device_param = f"-s {device_id}" if device_id else ""
        
        # 获取当前前台Activity
        cmd = f"adb {device_param} shell dumpsys activity activities | grep mResumedActivity"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        resumed_activity = result.stdout.strip()
        
        # 获取当前包名
        cmd = f"adb {device_param} shell dumpsys activity activities | grep mFocusedActivity"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        focused_activity = result.stdout.strip()
        
        return {
            'resumed_activity': resumed_activity,
            'focused_activity': focused_activity
        }
        
    except Exception as e:
        print(f"获取应用信息失败: {e}")
        return {}


# 简化的使用接口
def is_fullscreen(method='comprehensive', device_address=None) -> bool:
    """
    简化的全屏检测接口
    
    Args:
        method: 检测方法 ('comprehensive', 'adb_only', 'ui_only')
        device_address: 设备地址
    
    Returns:
        bool: 是否全屏
    """
    if method == 'adb_only':
        return quick_fullscreen_check_adb_only(device_address)
    elif method == 'ui_only':
        result = check_media_fullscreen_ui_analysis(device_address)
        return result.get('is_fullscreen', False)
    else:  # comprehensive
        result = is_media_fullscreen_comprehensive(device_address, verbose=False)
        return result.get('final_result', False)


# 命令行测试
def test_all_methods(device_address=None):
    """
    测试所有检测方法
    """
    print("🧪 测试所有检测方法")
    print("=" * 50)
    
    methods = [
        ('纯ADB方法', 'adb_only'),
        ('UI分析方法', 'ui_only'),
        ('综合方法', 'comprehensive')
    ]
    
    for method_name, method_key in methods:
        print(f"\n🔍 {method_name}:")
        try:
            result = is_fullscreen(method_key, device_address)
            print(f"   结果: {'✅ 全屏' if result else '❌ 非全屏'}")
        except Exception as e:
            print(f"   错误: {e}")
    
    # 显示当前应用信息
    print(f"\n📱 当前应用信息:")
    app_info = get_current_app_info(device_address)
    for key, value in app_info.items():
        print(f"   {key}: {value}")


# 添加命令行参数支持
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        device_id = sys.argv[2] if len(sys.argv) > 2 else None
        
        if command == 'test':
            test_all_methods(device_id)
        elif command == 'quick':
            result = is_fullscreen('adb_only', device_id)
            print(f"快速检测: {'全屏' if result else '非全屏'}")
        elif command == 'app':
            app_info = get_current_app_info(device_id)
            print("当前应用信息:")
            for key, value in app_info.items():
                print(f"  {key}: {value}")
        else:
            print("用法:")
            print("  python tmp.py test [device_id]     - 测试所有方法")
            print("  python tmp.py quick [device_id]    - 快速ADB检测")
            print("  python tmp.py app [device_id]      - 显示当前应用")
    else:
        # 默认运行综合检测
        print("🎬 媒体播放全屏状态检测")
        print("=" * 50)
        
        result = is_media_fullscreen_comprehensive(verbose=True)
        
        print("\n📋 详细结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print(f"\n✅ 简单结果: {'当前处于全屏播放状态' if result['final_result'] else '当前未处于全屏播放状态'}")
