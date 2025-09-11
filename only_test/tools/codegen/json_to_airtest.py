#!/usr/bin/env python3
"""
Only-Test: JSON -> Airtest/Poco code generator

Usage:
  python only_test/tools/codegen/json_to_airtest.py --in <test.json> --out <test.py>

Goal:
- Generate Python scripts that closely match recorded style in
  only_test/testcases/python/example_airtest_record.py
- Preserve comments: [page], [action], [comment]
- Map ui steps (click/input/wait/launch/restart/wait_for_elements/assert/swipe)
  and tool steps (e.g., close_ads) into executable Python

Notes:
- This generator assumes your project has:
  * only_test/lib/airtest_compat.py providing Airtest APIs
  * lib/poco_utils.get_android_poco()
  * only_test/lib/ad_closer.close_ads (optional; used when step.type == 'tool' and tool_name == 'close_ads')
- For content_desc mapping, this generator uses 'description' selector key in poco(),
  which may need adjustment depending on your Poco driver.
"""
import argparse
import json
import os
from typing import Dict, Any, List, Optional

HEADER_TEMPLATE = """# {title}
# [tag] {tags}
# [path] {path}

# 统一的导包方案, 其它用例直接复用即可
# -----
import sys, os
# Ensure repository root on sys.path so that 'only_test' package is importable
_here = os.path.dirname(__file__)
_repo_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# 添加项目路径，保证 from lib import ... 可用
_project_root = os.path.abspath(os.path.join(_here, "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from only_test.lib.airtest_compat import *
from lib.poco_utils import get_android_poco
from only_test.lib.ad_closer import close_ads
import asyncio
# -----

# Optional: 设置设备连接（如需）
# connect_device("android://127.0.0.1:5037/DEVICE_SERIAL?touch_method=ADBTOUCH&")
"""

FOOTER_TEMPLATE = """
# teardown_hook()
# 这里会放置一些测之后的必要清理 
"""


def _selector_to_pairs(selector: Dict[str, Any]) -> List[str]:
    pairs = []
    if "resource_id" in selector:
        pairs.append(f'resourceId="{selector["resource_id"]}"')
    if "text" in selector:
        pairs.append(f'text="{selector["text"]}"')
    if "content_desc" in selector:
        # Adjust key if your Poco driver expects a different kw
        pairs.append(f'description="{selector["content_desc"]}"')
    return pairs


def _poco_expr_from_selectors(priority_selectors: List[Dict[str, Any]]) -> str:
    if not priority_selectors:
        return "poco()"  # fallback placeholder
    # Combine available constraints (resourceId, text, description)
    parts: List[str] = []
    for sel in priority_selectors:
        parts.extend(_selector_to_pairs(sel))
    # de-duplicate while preserving order
    seen = set()
    args: List[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            args.append(p)
    args_str = ", ".join(args)
    return f"poco({args_str})" if args_str else "poco()"


def _emit_comment(page: str, action: str, description: str) -> str:
    return f"## [page] {page}, [action] {action}, [comment] {description}\n"


def _emit_restart(step: Dict[str, Any], target_app: str) -> str:
    timeout = step.get("timeout", 3)
    lines = [
        _emit_comment(step["page"], step["action"], step.get("description", "")),
        f'stop_app("{target_app}")',
        f'stop_app("{target_app}")',
        f'stop_app("{target_app}")',
        f'sleep({timeout})  # 等待应用完全关闭'
    ]
    return "\n".join(lines) + "\n\n"


def _emit_launch(step: Dict[str, Any], target_app: str) -> str:
    timeout = step.get("timeout", 5)
    return (
        _emit_comment(step["page"], step["action"], step.get("description", "")) +
        f'start_app("{target_app}")\n' +
        f'sleep({timeout})  # 等待应用启动完成\n\n'
    )


def _emit_wait(step: Dict[str, Any]) -> str:
    timeout = step.get("timeout", 1)
    return (
        _emit_comment(step["page"], step["action"], step.get("description", "")) +
        f'sleep({timeout})\n\n'
    )


def _emit_click(step: Dict[str, Any]) -> str:
    target = step.get("target", {})
    selectors = target.get("priority_selectors", [])
    bias = (target.get("bias") or {})
    bounds = target.get("bounds_px")

    if bounds and not selectors:
        # Click by center of bounds
        left, top, right, bottom = bounds
        cx = int((left + right) / 2)
        cy = int((top + bottom) / 2)
        code = (
            _emit_comment(step["page"], step["action"], step.get("description", "")) +
            f'poco.click([{cx}, {cy}])\n\n'
        )
        return code

    poco_expr = _poco_expr_from_selectors(selectors)
    if bias:
        dx = bias.get("dx_px")
        dy = bias.get("dy_px")
        args = []
        if dx is not None:
            args.append(f"dx_px={dx}")
        if dy is not None:
            args.append(f"dy_px={dy}")
        args_str = ", ".join(args)
        action_line = f"{poco_expr}.click_with_bias({args_str})" if args_str else f"{poco_expr}.click()"
    else:
        action_line = f"{poco_expr}.click()"

    return _emit_comment(step["page"], step["action"], step.get("description", "")) + action_line + "\n\n"


def _emit_input(step: Dict[str, Any], variables: Dict[str, Any]) -> str:
    data = step.get("data")
    # Example pattern uses text() directly after clicking input
    lines = [_emit_comment(step["page"], step["action"], step.get("description", ""))]
    # Optional small wait to stabilize
    lines.append("sleep(0.5)")
    if isinstance(data, str):
        # Resolve ${var} placeholders using testcase.variables
        if data.startswith("${") and data.endswith("}"):
            var_name = data[2:-1]
            if var_name in variables:
                resolved = variables[var_name]
                lines.append(f'text({json.dumps(str(resolved), ensure_ascii=False)})')
            else:
                # Fallback: emit literal string
                lines.append(f'text({json.dumps(data, ensure_ascii=False)})  # WARN: variable {var_name} not found')
        else:
            lines.append(f'text({json.dumps(data, ensure_ascii=False)})')
    else:
        lines.append("# TODO: Unsupported data type for input")
    return "\n".join(lines) + "\n\n"


def _emit_wait_for_elements(step: Dict[str, Any]) -> str:
    target = step.get("target", {})
    selectors = target.get("priority_selectors", [])
    timeout = step.get("timeout", 10)
    disappearance = bool(target.get("disappearance"))

    poco_expr = _poco_expr_from_selectors(selectors)
    if disappearance:
        action_line = f"{poco_expr}.wait_for_disappearance(timeout={timeout})"
    else:
        action_line = f"{poco_expr}.wait_for_appearance(timeout={timeout})"

    return _emit_comment(step["page"], step["action"], step.get("description", "")) + action_line + "\n\n"


def _emit_swipe(step: Dict[str, Any]) -> str:
    target = step.get("target", {})
    swipe = target.get("swipe", {})
    sx, sy = swipe.get("start_px", [0, 0])
    ex, ey = swipe.get("end_px", [0, 0])
    dur = swipe.get("duration_ms")
    dur_arg = f", duration={dur/1000.0}" if isinstance(dur, (int, float)) else ""
    return (
        _emit_comment(step["page"], step["action"], step.get("description", "")) +
        f"swipe([{sx}, {sy}], [{ex}, {ey}]{dur_arg})\n\n"
    )


def _emit_assert(step: Dict[str, Any]) -> str:
    return (
        _emit_comment(step["page"], step["action"], step.get("description", "")) +
        "# TODO: 添加具体断言实现\n\n"
    )


def _emit_tool(step: Dict[str, Any], target_app: str) -> str:
    tool_name = step.get("tool_name")
    params = step.get("params", {})
    if tool_name == "close_ads":
        # Map known close_ads signature
        mode = json.dumps(params.get("mode", "continuous"))
        consecutive_no_ad = params.get("consecutive_no_ad", 3)
        max_duration = params.get("max_duration", 20.0)
        return (
            _emit_comment(step["page"], "close_ads", step.get("description", "")) +
            f'asyncio.run(close_ads(target_app="{target_app}", mode={mode}, consecutive_no_ad={int(consecutive_no_ad)}, max_duration={float(max_duration)}))\n\n'
        )
    if tool_name == "connect_device":
        uri = params.get("uri") or params.get("device_uri") or ""
        return (
            _emit_comment(step["page"], "connect_device", step.get("description", "")) +
            f'connect_device({json.dumps(uri, ensure_ascii=False)})\n\n'
        )
    if tool_name == "click_center_of":
        # Accept either params.priority_selectors (list) or params.selector (single)
        selectors = params.get("priority_selectors") or []
        selector = params.get("selector")
        selector_list = selectors if selectors else ([selector] if selector else [])
        poco_expr = _poco_expr_from_selectors(selector_list)
        var_x, var_y = "miniScreenCenterX", "miniScreenCenterY"
        return (
            _emit_comment(step["page"], "click_center_of", step.get("description", "")) +
            f"{var_x},{var_y} = {poco_expr}.get_position()\n" +
            f"poco.click([{var_x}, {var_y}])\n\n"
        )
    # Generic tool placeholder
    return (
        _emit_comment(step["page"], "tool", step.get("description", "")) +
        f"# TODO: 未知工具 {tool_name}，请自行实现。参数: {json.dumps(params, ensure_ascii=False)}\n\n"
    )


def _derive_path_from_pages(steps: List[Dict[str, Any]], *, exclude: Optional[set] = None) -> str:
    exclude = exclude or set()
    pages = []
    for s in steps:
        p = s.get("page")
        if p in exclude:
            continue
        if p and (not pages or pages[-1] != p):
            pages.append(p)
    return " -> ".join(pages)


def generate_py(tc: Dict[str, Any], *, business_path: bool = False) -> str:
    title = tc.get("name") or tc.get("description") or tc.get("testcase_id")
    tags = ", ".join(tc.get("metadata", {}).get("tags", []))
    exclude_pages = {"app_initialization", "app_startup"} if business_path else set()
    path = _derive_path_from_pages(tc.get("execution_path", []), exclude=exclude_pages)

    lines: List[str] = [HEADER_TEMPLATE.format(title=title, tags=tags, path=path)]

    target_app = tc.get("target_app", "")
    variables = tc.get("variables", {})
    steps = sorted(tc.get("execution_path", []), key=lambda s: s.get("step", 0))

    # Hoist connect_device if present, so it appears before poco initialization
    hoisted_connect = None
    remaining_steps: List[Dict[str, Any]] = []
    for step in steps:
        if step.get("type") == "tool" and step.get("tool_name") == "connect_device" and hoisted_connect is None:
            hoisted_connect = _emit_tool(step, target_app)
        else:
            remaining_steps.append(step)

    if hoisted_connect:
        lines.append(hoisted_connect)
    # Initialize poco after possible connect_device
    lines.append("poco = get_android_poco()\n\n")

    for step in remaining_steps:
        stype = step.get("type", "ui")
        if stype == "tool":
            lines.append(_emit_tool(step, target_app))
            continue

        action = step.get("action")
        if action == "restart":
            lines.append(_emit_restart(step, target_app))
        elif action == "launch":
            lines.append(_emit_launch(step, target_app))
        elif action == "wait":
            lines.append(_emit_wait(step))
        elif action == "click":
            lines.append(_emit_click(step))
        elif action == "input":
            lines.append(_emit_input(step, variables))
        elif action == "wait_for_elements":
            lines.append(_emit_wait_for_elements(step))
        elif action == "swipe":
            lines.append(_emit_swipe(step))
        elif action == "assert":
            lines.append(_emit_assert(step))
        else:
            lines.append(_emit_comment(step.get("page", ""), action or "unknown", step.get("description", "")))
            lines.append(f"# TODO: 未支持的动作: {action}\n\n")

        # Optional wait_after
        if isinstance(step.get("wait_after"), (int, float)):
            lines.append(f"sleep({float(step['wait_after'])})\n\n")

    lines.append(FOOTER_TEMPLATE)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input_path", required=True)
    ap.add_argument("--out", dest="output_path", required=True)
    ap.add_argument("--business_path", action="store_true", help="Exclude technical pages from [path] header")
    args = ap.parse_args()

    with open(args.input_path, "r", encoding="utf-8") as f:
        tc = json.load(f)

    py_code = generate_py(tc, business_path=bool(args.business_path))

    out_dir = os.path.dirname(args.output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output_path, "w", encoding="utf-8") as f:
        f.write(py_code)

    print(f"Generated: {args.output_path}")


if __name__ == "__main__":
    main()

