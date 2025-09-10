#!/usr/bin/env python3
"""
Path 溯源字段构建器
提供在生成阶段/执行阶段为每个步骤构建可追溯、便于阅读的 path 字段。
"""

from datetime import datetime
from typing import Dict, Any, List, Optional


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _extract_selector_candidates(target: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    if not isinstance(target, dict):
        return []
    selectors = target.get("priority_selectors") or target.get("selectors") or []
    if isinstance(selectors, list):
        # 仅保留可读的键
        cleaned = []
        for sel in selectors:
            if isinstance(sel, dict):
                item = {}
                for k in ("resource_id", "content_desc", "desc", "text", "class"):
                    if sel.get(k):
                        item[k] = sel[k]
                if item:
                    cleaned.append(item)
        return cleaned
    return []


def build_step_path(
    workflow_id: str,
    step_index: int,
    tool_name: str,
    tool_category: str,
    target_app: str,
    execution_step: Dict[str, Any],
    device_id: Optional[str] = None,
) -> Dict[str, Any]:
    """为单个 execution_path 步骤构造 path 字段（生成阶段）。"""

    action = execution_step.get("action")
    target = execution_step.get("target", {})
    selector_candidates = _extract_selector_candidates(target)

    path = {
        "schema": {"version": "v1", "timestamp": _now_iso()},
        "workflow": {"workflow_id": workflow_id, "iteration": 1, "step_index": step_index},
        "tool": {"name": tool_name, "category": tool_category, "version": "1.0"},
        "device": {"id": device_id or "unknown"},
        "app": {"package": target_app},
        "recognition": {
            "strategy": None,
            "playback_state": None,
            "source": None,
            "fallback_used": False,
            "screen_hash": None,
            "screenshot_path": None,
        },
        "element": {
            "uuid": None,
            "resource_id": None,
            "content_desc": None,
            "text": None,
            "class_name": None,
            "bbox_norm": None,
            "bounds_px": None,
            "selector_used": None,
            "selector_candidates": selector_candidates,
            "confidence": None,
        },
        "decision": {
            "reasoning": execution_step.get("description"),
            "score": None,
        },
        "action": {
            "action_type": action,
            "input_data": execution_step.get("data"),
            "success_criteria": execution_step.get("success_criteria"),
        },
    }
    return path

