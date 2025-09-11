#!/usr/bin/env python3
"""
Only-Test 广告自动关闭脚本入口（调用正式模块）
========================================

此脚本仅作为命令行入口，实际逻辑在 lib/ad_closer.py 内。
保留该路径以兼容现有调用：
  python -X utf8 only_test/examples/test_ad_closer.py --target-app com.mobile.brasiltvmobile --mode continuous
"""

import argparse
import asyncio
from pathlib import Path
import sys

# 添加 only_test 到 path，以便导入 lib 模块
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from lib.ad_closer import close_ads


async def main():
    parser = argparse.ArgumentParser(description="Only-Test 关闭广告入口")
    parser.add_argument("--device-id", default=None)
    parser.add_argument("--target-app", default="com.mobile.brasiltvmobile")
    parser.add_argument("--mode", choices=["single", "continuous"], default="continuous")
    parser.add_argument("--consecutive-no-ad", type=int, default=3)
    parser.add_argument("--max-duration", type=float, default=10.0)
    args = parser.parse_args()

    result = await close_ads(
        device_id=args.device_id,
        target_app=args.target_app,
        mode=args.mode,
        consecutive_no_ad=args.consecutive_no_ad,
        max_duration=args.max_duration,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
