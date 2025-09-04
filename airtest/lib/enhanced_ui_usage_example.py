#!/usr/bin/env python3
"""
Enhanced UIAutomator2 Extractor Usage Example
增强版UIAutomator2提取器使用示例

展示如何使用新的智能调度器和统一接口
"""

import asyncio
import json
from pure_uiautomator2_extractor import UIAutomationScheduler, ExtractionMode

async def main():
    """主要演示函数"""
    print("Enhanced UIAutomator2 Extractor Usage Example")
    print("=" * 60)
    
    # 1. 创建智能调度器
    scheduler = UIAutomationScheduler()
    
    # 2. 初始化连接
    print("正在初始化设备连接...")
    if not await scheduler.initialize():
        print("❌ 设备连接失败")
        return
    print("✅ 设备连接成功")
    
    # 3. 获取当前模式信息
    print("\n=== 当前状态信息 ===")
    mode_info = await scheduler.get_current_mode_info()
    print(f"默认模式: {mode_info['current_mode']}")
    print(f"播放状态: {mode_info['playback_state']}")
    print(f"Omniparser可用: {mode_info['omniparser_available']}")
    print(f"屏幕尺寸: {mode_info['screen_size']}")
    print(f"设备已连接: {mode_info['device_connected']}")
    
    # 4. 演示统一接口 - 自动选择模式
    print("\n=== 演示自动模式选择 ===")
    elements_data = await scheduler.get_screen_elements()
    print(f"自动选择模式: {elements_data['extraction_mode']}")
    print(f"提取元素总数: {elements_data['total_count']}")
    print(f"统计信息: {elements_data['statistics']}")
    
    # 5. 演示查找功能
    print("\n=== 演示元素查找功能 ===")
    
    # 查找可点击元素
    clickable_elements = await scheduler.find_elements(clickable_only=True)
    print(f"找到 {len(clickable_elements)} 个可点击元素")
    
    # 显示前3个可点击元素的详细信息
    for i, element in enumerate(clickable_elements[:3]):
        print(f"\n可点击元素 {i+1}:")
        print(f"  UUID: {element['uuid']}")
        print(f"  类型: {element['element_type']}")
        print(f"  名称: {element['name']}")
        print(f"  文本: {element['text']}")
        print(f"  来源: {element['source']}")
        print(f"  边界: {element['bounds']}")
    
    # 6. 演示文本查找
    print("\n=== 演示文本查找 ===")
    # 这里可以根据实际应用界面调整搜索文本
    search_texts = ["设置", "Settings", "确定", "OK", "返回", "Back"]
    
    for search_text in search_texts:
        found_elements = await scheduler.find_elements(text=search_text)
        if found_elements:
            print(f"找到包含 '{search_text}' 的元素: {len(found_elements)} 个")
            break
    
    # 7. 演示手动模式切换
    print("\n=== 演示手动模式切换 ===")
    
    # 强制使用XML模式
    await scheduler.force_xml_mode()
    xml_data = await scheduler.get_screen_elements()
    print(f"XML模式提取元素: {xml_data['total_count']} 个")
    print(f"XML统计: {xml_data['statistics']}")
    
    # 尝试强制使用视觉模式（如果Omniparser可用）
    if mode_info['omniparser_available']:
        await scheduler.force_visual_mode()
        visual_data = await scheduler.get_screen_elements()
        print(f"视觉模式提取元素: {visual_data['total_count']} 个")
        print(f"视觉统计: {visual_data['statistics']}")
    else:
        print("Omniparser不可用，跳过视觉模式演示")
    
    # 恢复自动模式
    await scheduler.auto_mode()
    print("已恢复自动模式")
    
    # 8. 演示点击操作（请谨慎使用，确保不会对系统造成意外影响）
    print("\n=== 演示点击操作 ===")
    print("注意：实际点击操作已被注释，避免意外操作")
    
    # 示例：根据文本点击（取消注释前请确保安全）
    # if found_elements:
    #     first_element = found_elements[0]
    #     result = await scheduler.tap_element_by_uuid(first_element['uuid'])
    #     print(f"点击结果: {result}")
    
    # 示例：根据文本点击
    # result = await scheduler.tap_element_by_text("设置")
    # print(f"文本点击结果: {result}")
    
    # 9. 保存详细数据
    print("\n=== 保存数据 ===")
    from datetime import datetime
    
    # 保存完整数据
    filename = f"enhanced_ui_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    final_data = await scheduler.get_screen_elements()
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 完整数据已保存到: {filename}")
    
    # 10. 使用过滤器
    print("\n=== 演示包过滤功能 ===")
    # 过滤特定包的元素（根据实际情况调整包名）
    filtered_data = await scheduler.get_screen_elements(filter_package="com.android")
    print(f"Android系统包元素: {filtered_data['total_count']} 个")
    
    print("\n✅ 演示完成！")


async def advanced_usage_example():
    """高级使用示例"""
    print("\n" + "=" * 60)
    print("高级使用示例")
    print("=" * 60)
    
    # 创建调度器并初始化
    scheduler = UIAutomationScheduler()
    await scheduler.initialize()
    
    # 1. 演示播放状态检测
    print("\n1. 播放状态检测:")
    mode_info = await scheduler.get_current_mode_info()
    playback_state = mode_info['playback_state']
    print(f"当前播放状态: {playback_state}")
    
    if playback_state == "playing":
        print("检测到播放状态，系统会自动使用视觉识别模式")
    else:
        print("非播放状态，系统会优先使用XML模式")
    
    # 2. 演示偏差校正
    print("\n2. 偏差校正功能:")
    print("对于媒体内容（视频、节目等），可以使用bias=True进行偏差校正")
    
    # 查找可能需要偏差校正的元素
    elements = await scheduler.find_elements(text="视频")
    if not elements:
        elements = await scheduler.find_elements(text="播放")
    
    if elements:
        print(f"找到媒体相关元素: {len(elements)} 个")
        for element in elements[:2]:
            print(f"  - {element['name']}: {element['text']}")
        
        # 演示偏差校正点击（请谨慎使用）
        # result = await scheduler.tap_element_by_uuid(elements[0]['uuid'], bias=True)
        # print(f"偏差校正点击结果: {result}")
    
    # 3. 演示缓存机制
    print("\n3. 缓存机制:")
    import time
    
    start_time = time.time()
    data1 = await scheduler.get_screen_elements()
    time1 = time.time() - start_time
    
    start_time = time.time()
    data2 = await scheduler.get_screen_elements()  # 应该使用缓存
    time2 = time.time() - start_time
    
    print(f"第一次提取耗时: {time1:.2f}秒")
    print(f"第二次提取耗时: {time2:.2f}秒 (使用缓存)")
    print(f"缓存加速比: {time1/time2:.1f}x" if time2 > 0 else "N/A")


if __name__ == "__main__":
    # 运行基本演示
    asyncio.run(main())
    
    # 运行高级演示
    try:
        asyncio.run(advanced_usage_example())
    except Exception as e:
        print(f"高级演示执行失败: {e}")