#!/usr/bin/env python3
"""
检查当前UI结构，了解为什么ivClose不可点击
"""

import sys
import os
import asyncio

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'only_test/lib'))

from pure_uiautomator2_extractor import UIAutomationScheduler

async def check_ui_structure():
    """检查UI结构"""
    print("🔍 检查ivClose元素的UI结构")
    print("=" * 50)
    
    try:
        scheduler = UIAutomationScheduler()
        
        if not await scheduler.initialize():
            print("❌ 初始化失败")
            return
        
        # 获取所有元素
        all_elements = await scheduler.find_elements()
        
        # 找到目标元素
        target_resource_id = "com.mobile.brasiltvmobile:id/ivClose"
        target_element = None
        
        for element in all_elements:
            if element['resource_id'] == target_resource_id:
                target_element = element
                break
        
        if not target_element:
            print("❌ 未找到目标元素，可能界面已变化")
            return
        
        print(f"🎯 目标元素详情:")
        print(f"   Resource ID: {target_element['resource_id']}")
        print(f"   类名: {target_element['class_name']}")
        print(f"   可点击: {target_element['clickable']}")
        print(f"   路径: {target_element['metadata'].get('path', 'unknown')}")
        print(f"   边界: {target_element['bounds']}")
        print(f"   元数据: {target_element['metadata']}")
        
        # 分析路径结构
        target_path = target_element['metadata'].get('path', '')
        if target_path:
            path_parts = target_path.split('/')
            print(f"\n🌳 UI层次结构分析 (路径: {target_path}):")
            
            # 找到各级父元素
            for i in range(len(path_parts) - 1, 0, -1):
                parent_path = '/'.join(path_parts[:i])
                
                # 查找该路径的元素
                for element in all_elements:
                    if element['metadata'].get('path', '') == parent_path:
                        level = len(path_parts) - i
                        indent = "  " * level
                        clickable_status = "✅可点击" if element['clickable'] else "❌不可点击"
                        
                        print(f"{indent}📁 父级 {level}: {element['class_name']} {clickable_status}")
                        print(f"{indent}   Resource ID: {element['resource_id']}")
                        print(f"{indent}   边界: {element['bounds']}")
                        
                        if element['clickable']:
                            print(f"{indent}   🎯 这个父级可以点击!")
                        
                        break
        
        print(f"\n📊 为什么现在不可点击的分析:")
        print(f"   1. 这是Android UI设计的进化:")
        print(f"      - ImageView通常只负责显示图片")
        print(f"      - 点击事件由包含它的布局容器处理")
        print(f"      - 这样可以提供更大的触摸区域")
        
        print(f"\n   2. 现代Android开发最佳实践:")
        print(f"      - 分离显示和交互逻辑")
        print(f"      - 更好的可访问性支持")
        print(f"      - 更精确的语义化描述")
        
        print(f"\n   3. 我们的修复方案:")
        print(f"      - 自动检测不可点击的元素")
        print(f"      - 智能找到可点击的父级容器")
        print(f"      - 使用原始坐标进行精确点击")
        print(f"      - 完全透明，用户无需改变代码")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_ui_structure())