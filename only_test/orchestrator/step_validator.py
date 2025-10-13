#!/usr/bin/env python3
"""
Only-Test Orchestrator Step Validator

Purpose
- Validate each LLM-produced step against the latest analyze_current_screen result
- Enforce whitelist binding (no hallucinated selectors/IDs)
- Enforce bounds consistency with the chosen element's bbox
- Encourage single-step handshake (Plan → Execute → Verify → Append)

Usage (example)
----------------
from only_test.orchestrator.step_validator import validate_step, is_tool_request

ok, errors = validate_step(screen, step)
if is_tool_request(step):
    # Call analyze_current_screen, then loop back with new screen
    pass
elif ok:
    # Execute next_action, then call analyze_current_screen again
    pass
else:
    # Return errors to the LLM and ask it to repair based on the same screen
    print("Validation failed:", errors)

Screen JSON (expected minimal fields)
-------------------------------------
screen = {
    "screen_hash": "...",
    "elements": [
        {
            "uuid": "e-1",
            "resource_id": "com.app:id/btn_search",
            "text": "搜索",
            "content_desc": "search",
            "bbox": [100, 200, 300, 260],
            "clickable": True,
            "class_name": "android.widget.Button"
        },
        ...
    ]
}

Step JSON (expected minimal fields)
-----------------------------------
# Either a tool_request:
step = {
  "tool_request": {
    "name": "analyze_current_screen",
    "params": {},
    "reason": "..."
  }
}

# Or a single next_action:
step = {
  "analysis": { ... },
  "next_action": {
    "action": "click|input|wait_for_elements|wait|restart|launch|assert|swipe",
    "target": {
      "priority_selectors": [
        {"resource_id": "..."},
        {"content_desc": "..."},
        {"text": "..."}
      ],
      "bounds_px": [left, top, right, bottom]
    },
    "data": "...",
    "wait_after": 0.8,
    "expected_result": "..."
  },
  "evidence": {
    "screen_hash": "...",
    "source_element_uuid": "...",
    "source_element_snapshot": { ... }
  }
}
"""
from typing import Dict, Any, List, Tuple, Optional, Set

ALLOWED_ACTIONS: Set[str] = {
    "click", "input", "wait_for_elements", "wait", "restart", "launch", "assert", "swipe"
}

ALLOWED_SELECTOR_KEYS: Set[str] = {"resource_id", "text", "content_desc"}

# 运行期禁止出现在 test_step 中的生命周期/工具动作（保留向后兼容，不变更 ALLOWED_ACTIONS）
DISALLOWED_STEP_ACTIONS: Set[str] = {"start_app", "stop_app", "close_ads"}

PAGE_FIELD_DEFAULT = "current_page"  # 默认屏幕页面字段名，可由调用方覆盖


def is_tool_request(step: Dict[str, Any]) -> bool:
    """Return True if step is a TOOL_REQUEST block."""
    if not isinstance(step, dict):
        return False
    tr = step.get("tool_request")
    if not isinstance(tr, dict):
        return False
    return tr.get("name") == "analyze_current_screen"


def _build_selector_index(elements: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """Build a whitelist index of selector values from elements."""
    index = {"resource_id": set(), "text": set(), "content_desc": set()}
    for e in elements:
        rid = e.get("resource_id")
        if rid:
            index["resource_id"].add(str(rid))
        txt = e.get("text")
        if txt:
            index["text"].add(str(txt))
        cdesc = e.get("content_desc")
        if cdesc:
            index["content_desc"].add(str(cdesc))
    return index


def _match_selector(elem: Dict[str, Any], key: str, value: str) -> bool:
    """Check whether a single selector matches the element."""
    if key not in ALLOWED_SELECTOR_KEYS:
        return False
    v = elem.get(key)
    return str(v) == str(value)


def _find_element_by_selectors(elements: List[Dict[str, Any]], selectors: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Try to find one element that matches any of provided selectors (OR semantics)."""
    for sel in selectors:
        if not isinstance(sel, dict) or len(sel.keys()) != 1:
            continue
        key, value = list(sel.items())[0]
        if key not in ALLOWED_SELECTOR_KEYS:
            continue
        for e in elements:
            if _match_selector(e, key, value):
                return e
    return None


def _normalize_bounds(bounds: Any) -> Optional[List[int]]:
    try:
        vals = [int(x) for x in bounds]
        if len(vals) != 4:
            return None
        return vals
    except Exception:
        return None


def validate_step(
    screen: Dict[str, Any],
    step: Dict[str, Any],
    *,
    page_check_mode: str = "off",  # "off" | "soft" | "hard"
    page_field: str = PAGE_FIELD_DEFAULT,
    allowed_pages: Optional[List[str]] = None,
    require_evidence: bool = False,
    enforce_hooks_boundary: bool = False,
) -> Tuple[bool, List[str], Optional[Dict[str, Any]]]:
    """
    Validate a single LLM-produced step against the given screen.

    Args:
        screen: 最新的屏幕分析结果（包含 elements、screen_hash、current_page 等）
        step: LLM 产出的 JSON（TOOL_REQUEST 或 单步决策）
        page_check_mode: 页面一致性检查模式：
            - off: 不检查
            - soft: 仅告警，不阻断执行
            - hard: 作为错误，阻断执行
        page_field: 从 screen 中读取“当前页面”的字段名（默认 current_page）
        allowed_pages: 允许执行的页面白名单（如果提供，将参与一致性检查）

    Returns (ok, errors, chosen_element)
        ok: True 表示该步骤有效
        errors: 校验错误/告警（soft 模式下的页面问题以 WARN: 前缀表示）
        chosen_element: 与选择器/边界匹配到的元素（用于链路/记录）
    """
    errors: List[str] = []

    # TOOL_REQUEST is always allowed and short-circuits validation
    if is_tool_request(step):
        return True, errors, None

    if not isinstance(step, dict):
        return False, ["step 不是字典"]

    screen_hash = screen.get("screen_hash")
    elements: List[Dict[str, Any]] = screen.get("elements") or []

    next_action = step.get("next_action")
    evidence = step.get("evidence", {})

    # 页面一致性（可选）
    def _page_warn(msg: str):
        if page_check_mode == "soft":
            errors.append(f"WARN(page): {msg}")
        elif page_check_mode == "hard":
            errors.append(msg)
        # off 模式不记录

    if page_check_mode in ("soft", "hard"):
        screen_page = screen.get(page_field)
        claimed_page = step.get("analysis", {}).get("current_page_type") or step.get("page")
        if allowed_pages:
            if screen_page not in set(allowed_pages):
                _page_warn(f"当前页面 {screen_page} 不在允许的页面范围 {allowed_pages}")
        if claimed_page and screen_page and claimed_page != screen_page:
            _page_warn(f"步骤声明页面 {claimed_page} 与当前页面 {screen_page} 不一致")

    # Basic presence checks
    if not isinstance(next_action, dict):
        errors.append("缺少 next_action 或其类型不正确")
        # 页面软告警不致命，但结构错误要直接失败
        return False, errors, None

    action = next_action.get("action")
    if action not in ALLOWED_ACTIONS:
        errors.append(f"action 不合法或缺失: {action}")
    # 额外边界：禁止生命周期/工具类动作出现在 test_step（保持向后兼容，可按需开启）
    if enforce_hooks_boundary and action in DISALLOWED_STEP_ACTIONS:
        errors.append(f"动作不允许在 test_steps 中出现: {action}（请在 hooks 或 tool 调用中使用）")

    target = next_action.get("target", {})
    selectors = target.get("priority_selectors", [])

    # Enforce selector list structure
    if not isinstance(selectors, list):
        errors.append("priority_selectors 必须是列表(list)")
    else:
        for i, sel in enumerate(selectors):
            if not isinstance(sel, dict) or len(sel.keys()) != 1:
                errors.append(f"priority_selectors[{i}] 必须是仅包含一个键的对象")
                continue
            key = next(iter(sel.keys()))
            if key not in ALLOWED_SELECTOR_KEYS:
                errors.append(f"priority_selectors[{i}] 的键必须是 {sorted(ALLOWED_SELECTOR_KEYS)} 之一")

    # Whitelist binding check
    index = _build_selector_index(elements)
    for i, sel in enumerate(selectors):
        if not isinstance(sel, dict) or len(sel.keys()) != 1:
            continue
        key, value = list(sel.items())[0]
        if key in ALLOWED_SELECTOR_KEYS and str(value) not in index.get(key, set()):
            errors.append(f"selector {key}={value} 不在本屏白名单内")

    # Try to find matched element
    chosen = _find_element_by_selectors(elements, selectors) if selectors else None

    # If selectors missing, bounds must be provided
    bounds_px = target.get("bounds_px")
    if not selectors or len(selectors) == 0:
        if not bounds_px:
            errors.append("当没有选择器可用时，必须提供 bounds_px")
    
    # If bounds provided, must match the chosen element's bbox/bounds exactly
    if bounds_px is not None:
        nb = _normalize_bounds(bounds_px)
        if nb is None:
            errors.append("bounds_px 必须是包含4个整数的数组 [left, top, right, bottom]")
        else:
            def _elem_box(e: Dict[str, Any]) -> Optional[List[int]]:
                # Prefer bounds, fallback to bbox
                b = e.get("bounds")
                if b is not None:
                    nb2 = _normalize_bounds(b)
                    if nb2 is not None:
                        return nb2
                bb = e.get("bbox")
                if bb is not None:
                    return _normalize_bounds(bb)
                return None
            if chosen is None:
                # Try to find by bounds/bbox when no selectors
                found = False
                for e in elements:
                    eb = _elem_box(e)
                    if eb == nb:
                        chosen = e
                        found = True
                        break
                if not found:
                    errors.append("提供了 bounds_px，但无法在 elements 中找到完全相同边界的元素")
            else:
                eb = _elem_box(chosen)
                if eb != nb:
                    errors.append("bounds_px 必须与所选元素的边界完全一致")

    # Evidence checks
    if require_evidence and not isinstance(evidence, dict):
        errors.append("必须提供 evidence 字段，并包含必要追溯信息")
    if require_evidence and isinstance(evidence, dict):
        # 软要求：存在字段
        if evidence.get("source_element_uuid") in (None, ""):
            errors.append("evidence.source_element_uuid 缺失")
        if evidence.get("source_element_snapshot") in (None, {}):
            errors.append("evidence.source_element_snapshot 缺失")
        # screen_hash 若存在则校验一致性；未提供时不强制（保持兼容）
    if screen_hash is not None and evidence.get("screen_hash") not in (None, screen_hash):
        errors.append("evidence.screen_hash 与当前屏幕不一致")

    src_uuid = evidence.get("source_element_uuid")
    if src_uuid and chosen and src_uuid != chosen.get("uuid"):
        errors.append("evidence.source_element_uuid 与所选元素不一致")

    snapshot = evidence.get("source_element_snapshot")
    if snapshot and chosen and snapshot.get("uuid") != chosen.get("uuid"):
        errors.append("source_element_snapshot 与所选元素不一致 (uuid 不匹配)")

    # 如果只有软告警（WARN）且无真正错误，则仍然视为有效
    hard_errors = [e for e in errors if not e.startswith("WARN(")]
    ok = len(hard_errors) == 0
    return ok, errors, chosen

