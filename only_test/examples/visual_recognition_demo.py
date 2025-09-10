#!/usr/bin/env python3
"""
Only-Test 视觉识别系统使用演示
===============================

展示如何使用新的视觉识别系统进行元素识别和交互
从phone-use迁移而来的完整视觉识别能力
"""

import asyncio
import sys
import logging
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from lib.visual_recognition import (
    VisualIntegration, 
    IntegrationConfig,
    RecognitionStrategy,
    # 便捷函数
    tap_by_text,
    tap_by_resource_id, 
    smart_tap,
    get_all_elements,
    is_media_playing
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("visual_demo")


async def demo_basic_usage():
    """演示基本用法"""
    print("\n" + "="*60)
    print("🎯 基本用法演示")
    print("="*60)
    
    # 1. 简单的点击操作
    print("1. 简单点击演示...")
    
    # 通过文本点击
    success = await tap_by_text("搜索")
    print(f"   通过文本点击 '搜索': {'✅ 成功' if success else '❌ 失败'}")
    
    # 通过资源ID点击  
    success = await tap_by_resource_id("com.example.app:id/search_button")
    print(f"   通过资源ID点击: {'✅ 成功' if success else '❌ 失败'}")
    
    # 智能点击（自动尝试多种匹配方式）
    success = await smart_tap("播放")
    print(f"   智能点击 '播放': {'✅ 成功' if success else '❌ 失败'}")
    
    # 2. 获取所有元素
    print("\n2. 元素识别演示...")
    elements = await get_all_elements(clickable_only=True)
    print(f"   识别到 {len(elements)} 个可点击元素")
    
    # 显示前5个元素的信息
    for i, element in enumerate(elements[:5]):
        text = element.get('text', '')[:20] + "..." if len(element.get('text', '')) > 20 else element.get('text', '')
        print(f"   - 元素{i+1}: {text} [{element.get('source', 'unknown')}]")
    
    # 3. 播放状态检测
    print("\n3. 播放状态检测...")
    playing = await is_media_playing()
    print(f"   当前播放状态: {'🎵 播放中' if playing else '⏸️ 非播放状态'}")


async def demo_advanced_usage():
    """演示高级用法"""
    print("\n" + "="*60)
    print("🚀 高级用法演示")
    print("="*60)
    
    # 1. 创建自定义配置
    config = IntegrationConfig(
        omniparser_server="http://100.122.57.128:9333",
        device_id=None,  # 使用默认设备
        cache_enabled=True,
        debug_mode=True,
        auto_strategy_enabled=True,
        fallback_enabled=True
    )
    
    # 2. 创建集成实例
    visual = VisualIntegration(config)
    await visual.initialize()
    
    # 3. 系统状态查询
    print("1. 系统状态查询...")
    status = await visual.get_system_status()
    print(f"   初始化状态: {'✅ 已初始化' if status['initialized'] else '❌ 未初始化'}")
    print(f"   当前策略: {status['current_strategy']['current_strategy']}")
    print(f"   Omniparser可用: {'✅ 可用' if status['current_strategy']['omniparser_available'] else '❌ 不可用'}")
    print(f"   媒体播放状态: {'🎵 播放中' if status['current_strategy']['is_media_playing'] else '⏸️ 空闲'}")
    
    # 4. 智能元素识别
    print("\n2. 智能元素识别...")
    result = await visual.smart_recognize(clickable_only=True)
    print(f"   识别成功: {'✅ 成功' if result['success'] else '❌ 失败'}")
    print(f"   使用策略: {result['strategy_used']}")
    print(f"   执行时间: {result['execution_time']:.2f}s")
    print(f"   Fallback次数: {result['fallback_attempts']}")
    print(f"   元素数量: {result['total_count']}")
    
    # 5. 自适应查找
    print("\n3. 自适应元素查找...")
    element = await visual.adaptive_find_element("播放", ["text", "content_desc", "resource_id"])
    if element:
        print("   ✅ 找到播放元素:")
        print(f"     文本: {element.get('text', '')}")
        print(f"     资源ID: {element.get('resource_id', '')}")
        print(f"     来源: {element.get('source', '')}")
    else:
        print("   ❌ 未找到播放元素")
    
    # 6. 健康检查
    print("\n4. 系统健康检查...")
    health = await visual.health_check()
    print(f"   系统健康: {'✅ 健康' if health['overall_healthy'] else '❌ 异常'}")
    
    for component, info in health['components'].items():
        status_icon = "✅" if info['healthy'] else "❌"
        print(f"   - {component}: {status_icon} {'健康' if info['healthy'] else '异常'}")
    
    if health['issues']:
        print("   发现问题:")
        for issue in health['issues']:
            print(f"   ⚠️ {issue}")


async def demo_strategy_switching():
    """演示策略切换"""
    print("\n" + "="*60)
    print("🔄 策略切换演示")
    print("="*60)
    
    visual = VisualIntegration()
    await visual.initialize()
    
    print("1. 自动策略选择...")
    
    # 模拟不同场景下的策略选择
    scenarios = [
        {"name": "静态界面", "playing": False, "expected": "XML或混合模式"},
        {"name": "视频播放", "playing": True, "expected": "视觉识别模式"},
        {"name": "音频播放", "playing": True, "expected": "视觉识别模式"}
    ]
    
    for scenario in scenarios:
        print(f"\n   场景: {scenario['name']}")
        result = await visual.smart_recognize()
        print(f"   选择策略: {result['strategy_used']}")
        print(f"   预期策略: {scenario['expected']}")
        print(f"   执行时间: {result['execution_time']:.2f}s")
    
    # 2. 强制策略切换演示
    print("\n2. 强制策略切换...")
    strategies_to_try = ["xml_only", "visual_only", "hybrid"]
    
    for strategy in strategies_to_try:
        try:
            success = await visual.force_strategy(strategy)
            print(f"   强制切换到 {strategy}: {'✅ 成功' if success else '❌ 失败'}")
        except Exception as e:
            print(f"   强制切换到 {strategy}: ❌ 异常 - {e}")


async def demo_performance_monitoring():
    """演示性能监控"""
    print("\n" + "="*60)
    print("📊 性能监控演示")
    print("="*60)
    
    visual = VisualIntegration()
    await visual.initialize()
    
    # 执行一些操作来生成性能数据
    print("1. 执行测试操作...")
    
    test_operations = [
        {"type": "recognize", "desc": "识别所有元素"},
        {"type": "find_tap", "target": "搜索", "desc": "查找并点击搜索"},
        {"type": "find_tap", "target": "播放", "desc": "查找并点击播放"},
        {"type": "recognize", "desc": "再次识别元素"}
    ]
    
    for i, op in enumerate(test_operations):
        print(f"   执行操作 {i+1}: {op['desc']}")
        
        if op["type"] == "recognize":
            await visual.smart_recognize()
        elif op["type"] == "find_tap":
            await visual.find_and_tap(text=op["target"])
        
        await asyncio.sleep(1)  # 模拟操作间隔
    
    # 获取性能统计
    print("\n2. 性能统计报告...")
    status = await visual.get_system_status()
    performance = status.get('performance', {})
    
    print(f"   总识别次数: {performance.get('total_recognitions', 0)}")
    print(f"   成功识别次数: {performance.get('successful_recognitions', 0)}")
    print(f"   识别成功率: {performance.get('recognition_success_rate', 0):.2%}")
    
    print(f"   总交互次数: {performance.get('total_interactions', 0)}")
    print(f"   成功交互次数: {performance.get('successful_interactions', 0)}")
    print(f"   交互成功率: {performance.get('interaction_success_rate', 0):.2%}")
    
    print(f"   策略切换次数: {performance.get('strategy_switches', 0)}")
    print(f"   Fallback使用次数: {performance.get('fallback_uses', 0)}")


async def demo_media_scenarios():
    """演示媒体场景处理"""
    print("\n" + "="*60)
    print("🎵 媒体场景处理演示")
    print("="*60)
    
    visual = VisualIntegration()
    await visual.initialize()
    
    # 1. 检测播放状态
    print("1. 播放状态检测...")
    playing = await is_media_playing()
    print(f"   当前播放状态: {'🎵 播放中' if playing else '⏸️ 非播放状态'}")
    
    # 2. 模拟媒体操作
    print("\n2. 媒体操作演示...")
    
    media_operations = [
        {"action": "play", "target": "播放", "bias": False},
        {"action": "pause", "target": "暂停", "bias": False},
        {"action": "seek", "target": "进度条", "bias": True},  # 使用偏移修正
        {"action": "volume", "target": "音量", "bias": False}
    ]
    
    for op in media_operations:
        print(f"   执行 {op['action']} 操作...")
        success = await visual.find_and_tap(
            text=op["target"], 
            bias_correction=op["bias"]
        )
        bias_info = " (使用偏移修正)" if op["bias"] else ""
        print(f"   {op['action']} 操作{bias_info}: {'✅ 成功' if success else '❌ 失败'}")
    
    # 3. 播放状态变化检测
    print("\n3. 播放状态变化检测...")
    for i in range(3):
        playing = await is_media_playing()
        print(f"   检测 {i+1}: {'🎵 播放中' if playing else '⏸️ 非播放状态'}")
        await asyncio.sleep(2)


async def main():
    """主演示函数"""
    print("🎯 Only-Test 视觉识别系统演示")
    print("=" * 80)
    print("展示从phone-use迁移而来的完整视觉识别能力")
    print("支持XML识别、视觉识别和智能fallback机制")
    print("=" * 80)
    
    try:
        # 基本用法演示
        await demo_basic_usage()
        
        # 高级用法演示
        await demo_advanced_usage()
        
        # 策略切换演示
        await demo_strategy_switching()
        
        # 性能监控演示
        await demo_performance_monitoring()
        
        # 媒体场景演示
        await demo_media_scenarios()
        
        print("\n" + "="*60)
        print("✅ 演示完成！")
        print("="*60)
        print("📚 使用说明:")
        print("1. 确保Omniparser服务器在运行 (http://100.122.57.128:9333)")
        print("2. 确保Android设备已连接且开启USB调试")
        print("3. 使用便捷函数进行快速开发")
        print("4. 使用VisualIntegration类进行高级控制")
        
    except Exception as e:
        logger.error(f"演示执行异常: {e}")
        print(f"\n❌ 演示执行失败: {e}")
        print("\n🔧 故障排除:")
        print("1. 检查Omniparser服务器是否运行")
        print("2. 检查设备连接状态")
        print("3. 检查USB调试是否开启")
        print("4. 查看详细日志信息")


if __name__ == "__main__":
    asyncio.run(main())