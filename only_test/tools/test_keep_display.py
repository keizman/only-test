#!/usr/bin/env python3
"""
Test keep-display for playback controls (XML-only)
=================================================

Run this script to verify the async single-instance keep-display worker.
It will:
- Dump UI XML before starting keep-display
- Start keep-display for a configurable duration
- Probe again after a few seconds to check whether control bar is visible
- Optionally probe one more time if duration allows
- Stop the keep-display worker and exit

Usage (PowerShell or CMD):
  python only_test/tools/test_keep_display.py -d 10 -i 0.2 -k Brightness

Arguments:
  -d/--duration      Total keep time in seconds (default: 10)
  -i/--interval      Detect interval in seconds (default: 0.2)
  -k/--keyword       A keyword that must appear when controls are visible (default: Brightness)
  -s/--device-id     ADB serial (optional); if omitted, uses default device
  --probe-delay      Seconds to first probe after starting keep (default: 3.0)
   python -m only_test.tools.test_keep_display -d 30 -i 0.5 -k Brightness -s 192.168.8.100 --verbose
"""

import argparse
import asyncio
import subprocess
import xml.etree.ElementTree as ET
from typing import Optional

from only_test.lib.playing_state_keep_displayed import (
    start_keep_play_controls,
    stop_keep_play_controls,
    is_full_screen,
)


def adb_prefix(device_id: Optional[str]) -> list[str]:
    return ["adb"] + (["-s", device_id] if device_id else [])


def dump_xml(device_id: Optional[str]) -> str:
    """Return current UI XML text, or empty string if unavailable."""
    # Try exec-out first (binary-safe), then fallback to sdcard file
    try:
        proc = subprocess.run(
            adb_prefix(device_id) + ["exec-out", "uiautomator", "dump", "/dev/tty"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8,
        )
        if proc.returncode == 0 and b"<hierarchy" in proc.stdout:
            txt = proc.stdout.decode("utf-8", errors="ignore")
            idx = txt.find("<hierarchy")
            if idx >= 0:
                return txt[idx:]
    except Exception:
        pass
    try:
        subprocess.run(
            adb_prefix(device_id) + ["shell", "uiautomator", "dump", "/sdcard/window_dump.xml"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8,
        )
        q = subprocess.run(
            adb_prefix(device_id) + ["shell", "cat", "/sdcard/window_dump.xml"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8,
        )
        if q.returncode == 0:
            return q.stdout.decode("utf-8", errors="ignore")
    except Exception:
        pass
    return ""


def stats(xml_text: str, keyword: str) -> tuple[int, bool]:
    """Return (rid_count, has_keyword). rid_count counts non-empty resource-id nodes."""
    if not xml_text:
        return (0, False)
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return (0, False)
    rid = 0
    has_kw = False
    k = (keyword or "").lower()
    for node in root.iter():
        if node.tag == "hierarchy":
            continue
        a = node.attrib
        if (a.get("resource-id") or "").strip():
            rid += 1
        if k and not has_kw:
            blob = (
                (a.get("text", "")
                 + a.get("content-desc", "")
                 + a.get("resource-id", "")
                 + a.get("class", ""))
            ).lower()
            if k in blob:
                has_kw = True
    return (rid, has_kw)


async def run(args) -> None:
    print("== keep-display test starting ==")
    print(f"device_id={args.device_id} duration={args.duration}s interval={args.interval}s keyword='{args.keyword}' verbose={args.verbose}")
    print(f"is_full_screen: {is_full_screen(args.device_id)}")

    print("[step] dumping xml (before)...")
    xml_before = dump_xml(args.device_id)
    rid1, has1 = stats(xml_before, args.keyword)
    print(f"[step] before: rid_count={rid1} has_kw={has1}")

    print("[step] starting keep worker (unified interval loop)...")
    await start_keep_play_controls(
        duration_s=args.duration,
        detect_interval=args.interval,
        exist_field_keyword=args.keyword,
        device_id=args.device_id,
        verbose=args.verbose,
    )

    # 直接等待到结束，由保活循环在每个 interval 自行拉取 XML 并点击/idle
    await asyncio.sleep(args.duration)

    # 最终 snapshot
    print("[step] dumping xml (final)...")
    xml_final = dump_xml(args.device_id)
    ridf, hasf = stats(xml_final, args.keyword)
    print(f"[step] final: rid_count={ridf} has_kw={hasf}")

    print("[step] stopping keep worker...")
    await stop_keep_play_controls()
    print("== keep-display test finished ==")


def main() -> None:
    p = argparse.ArgumentParser(description="Verify keep-display for playback controls (XML-only)")
    p.add_argument("-d", "--duration", type=float, default=10.0, help="Keep alive duration in seconds")
    p.add_argument("-i", "--interval", type=float, default=0.2, help="Detect interval in seconds")
    p.add_argument("-k", "--keyword", type=str, default="Brightness", help="Keyword indicating controls are visible")
    p.add_argument("-s", "--device-id", type=str, default=None, help="ADB serial (optional)")
    p.add_argument("--verbose", action="store_true", help="Print verbose keep worker logs")
    args = p.parse_args()

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        try:
            asyncio.run(stop_keep_play_controls())
        except Exception:
            pass
        print("interrupted.")


if __name__ == "__main__":
    main()


