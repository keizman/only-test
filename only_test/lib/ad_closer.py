#!/usr/bin/env python3
"""
Ad closer module
================

提供可复用的关闭广告能力，可在用例与CLI中直接调用。

默认策略：continuous 模式，连续 3 次未检测到广告或 10 秒内退出。
"""

from typing import Optional, Dict, Any
import asyncio

try:
    # 运行于仓库上下文（only_test）
    from .mcp_interface.device_inspector import DeviceInspector
except ImportError:
    # 允许从仓库根目录直接运行
    from only_test.lib.mcp_interface.device_inspector import DeviceInspector


async def close_ads(
    device_id: Optional[str] = None,
    target_app: str = "com.mobile.brasiltvmobile",
    mode: str = "continuous",
    consecutive_no_ad: int = 3,
    max_duration: float = 20.0,
) -> Dict[str, Any]:
    """关闭广告入口（可复用）。

    - mode="continuous": 连续监控；连续 N 次未检测到广告或达到最大时长即结束。
    - mode="single": 单次尝试。
    返回统计信息字典。
    """
    inspector = DeviceInspector(device_id=device_id)
    await inspector.initialize()
    if target_app:
        try:
            inspector.target_app_package = target_app
        except Exception:
            pass
    return await inspector.close_ads(
        mode="continuous" if mode == "continuous" else "single",
        consecutive_no_ad=consecutive_no_ad,
        max_duration=max_duration,
    )


if __name__ == "__main__":
    import argparse
    import logging

    # 设置DEBUG级别以显示详细日志
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description="Close ads helper")
    parser.add_argument("--device-id", default=None)
    parser.add_argument("--target-app", default="com.mobile.brasiltvmobile")
    parser.add_argument("--mode", choices=["single", "continuous"], default="continuous")
    parser.add_argument("--consecutive-no-ad", type=int, default=3)
    parser.add_argument("--max-duration", type=float, default=20.0)
    args = parser.parse_args()

    async def _run():
        result = await close_ads(
            device_id=args.device_id,
            target_app=args.target_app,
            mode=args.mode,
            consecutive_no_ad=args.consecutive_no_ad,
            max_duration=args.max_duration,
        )
        print(result)

    asyncio.run(_run())

