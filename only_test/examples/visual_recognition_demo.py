#!/usr/bin/env python3
"""
该示例已废弃
=============

本项目已切换为 XML-only 模式（UIAutomator2）。视觉识别/Omniparser 演示不再提供。
请参考 README 中的“播放场景的可见性策略（控制栏保活）”与 XML 定位示例。
"""

if __name__ == "__main__":
    print("This demo has been deprecated. See README for XML-only guidance.")


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