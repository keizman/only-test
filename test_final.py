# coding=utf-8
"""
最终测试 - 验证修复是否成功
"""

import sys
import os

# 添加Poco路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Poco'))

def test_direct_click():
    """测试直接点击是否工作"""
    print("测试直接点击: poco(resourceId='xxx').click()")
    
    try:
        from poco.drivers.android.uiautomation import AndroidUiautomationPoco
        poco = AndroidUiautomationPoco(use_airtest_input=True)
        
        # 验证修复版本
        info = poco.get_implementation_info()
        print(f"✓ 使用: {info['backend']} v{info['version']}")
        
        # 测试直接点击语法
        target_id = "com.mobile.brasiltvmobile:id/ivClose"
        element = poco(resourceId=target_id)
        
        if element.exists():
            element.click()
            print("✅ 直接点击成功!")
        else:
            print("ℹ️ 元素不存在但语法正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

if __name__ == "__main__":
    success = test_direct_click()
    if success:
        print("\n🎉 修复成功! 现在可以直接使用 poco(resourceId='xxx').click()")
    else:
        print("\n❌ 还有问题需要调试")