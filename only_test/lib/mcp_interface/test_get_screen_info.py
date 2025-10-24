#!/usr/bin/env python3
"""
测试 get_current_screen_info 的 CLI 工具
直接调用 device_inspector 的方法，用于验证功能
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

# 确保 repo root 在 sys.path
_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from only_test.lib.mcp_interface.device_inspector import DeviceInspector


async def main():
    parser = argparse.ArgumentParser(description="测试 get_current_screen_info")
    parser.add_argument("--device-id", default=None, help="设备ID")
    parser.add_argument("--include-elements", action="store_true", help="包含元素列表")
    parser.add_argument("--clickable-only", action="store_true", default=True, help="只获取可点击元素")
    parser.add_argument("--auto-close-limit", type=int, default=3, help="自动关闭广告限制")
    parser.add_argument("--auto-click-playing", type=int, default=0, help="播放状态自动点击 (0=禁用, 1=启用)")
    parser.add_argument("-o", "--output", default="tmp.json", help="输出文件路径")
    args = parser.parse_args()
    
    print(f"[TEST] 初始化 DeviceInspector...")
    inspector = DeviceInspector(device_id=args.device_id)
    await inspector.initialize()
    
    print(f"[TEST] 调用 get_current_screen_info...")
    print(f"  - include_elements: {args.include_elements}")
    print(f"  - clickable_only: {args.clickable_only}")
    print(f"  - auto_close_limit: {args.auto_close_limit}")
    print(f"  - auto_click_playing: {args.auto_click_playing}")
    
    try:
        result = await inspector.get_current_screen_info(
            include_elements=args.include_elements,
            clickable_only=args.clickable_only,
            auto_close_limit=args.auto_close_limit,
            auto_click_playing=args.auto_click_playing
        )
        
        print(f"[TEST] 成功获取屏幕信息")
        print(f"  - media_playing: {result.get('media_playing')}")
        print(f"  - total_elements: {result.get('total_elements')}")
        print(f"  - elements_with_resource_id: {result.get('elements_with_resource_id')}")
        
        if args.auto_click_playing == 1:
            print(f"\n[AUTO-CLICK-PLAYING] 调试信息:")
            print(f"  - auto_click_performed: {result.get('auto_click_performed')}")
            print(f"  - controls_visible_after_click: {result.get('controls_visible_after_click')}")
            print(f"  - elements_refreshed: {result.get('elements_refreshed')}")
            if 'auto_click_error' in result:
                print(f"  - auto_click_error: {result.get('auto_click_error')}")
        
        # 保存到文件
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n[TEST] 结果已保存到: {output_path.absolute()}")
        
    except Exception as e:
        print(f"[ERROR] 获取屏幕信息失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

