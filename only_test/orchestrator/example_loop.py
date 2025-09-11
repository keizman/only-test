#!/usr/bin/env python3
"""
Example Orchestrator Loop (Pseudo-code)

This demonstrates the Plan → Execute → Verify → Append handshake using the
step_validator to prevent hallucinated selectors and enforce bounds correctness.

NOTE: Replace the placeholders (call_llm, analyze_current_screen, perform_ui_action)
with your real MCP tool integrations.
"""
from typing import Dict, Any, List, Tuple
import time

from only_test.orchestrator.step_validator import validate_step, is_tool_request


def analyze_current_screen() -> Dict[str, Any]:
    """Placeholder: integrate your MCP tool here to collect live screen info."""
    # return {
    #     "screen_hash": "...",
    #     "elements": [...],
    # }
    raise NotImplementedError


def perform_ui_action(step: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder: execute the action (tap/input/swipe/etc) using your tool."""
    # Use step["next_action"] to drive the device
    # Return execution metadata, e.g. {"success": True, "elapsed": 0.75}
    raise NotImplementedError


def call_llm(prompt: str) -> Dict[str, Any]:
    """Placeholder: call your LLM and parse JSON output into dict."""
    raise NotImplementedError


def _pick_matching_selector(chosen: Dict[str, Any], selectors: List[Dict[str, Any]]) -> Any:
    """Return the first selector that matches the chosen element, else None."""
    for sel in selectors or []:
        if len(sel.keys()) != 1:
            continue
        k, v = list(sel.items())[0]
        if str(chosen.get(k)) == str(v):
            return sel
    # fallback to resource_id if present
    rid = chosen.get("resource_id")
    if rid:
        return {"resource_id": rid}
    # otherwise try text/content_desc
    if chosen.get("content_desc"):
        return {"content_desc": chosen.get("content_desc")}
    if chosen.get("text"):
        return {"text": chosen.get("text")}
    return None


def run_testcase(objective: str, max_steps: int = 20, *, tags: List[str] = None, page_scope: List[str] = None) -> Dict[str, Any]:
    steps: List[Dict[str, Any]] = []
    chain_nodes: List[Dict[str, Any]] = []
    screen = analyze_current_screen()

    for i in range(1, max_steps + 1):
        # 1) Build step prompt (use your existing prompt builder)
        # prompt = TestCaseGenerationPrompts.get_mcp_step_guidance_prompt(
        #     current_step=i,
        #     screen_analysis_result=screen,
        #     test_objective=objective,
        #     previous_steps=steps,
        # )
        prompt = "..."

        # 2) Ask LLM for next step (must be either tool_request or single step)
        step = call_llm(prompt)

        # 3) Handle TOOL_REQUEST
        if is_tool_request(step):
            screen = analyze_current_screen()
            continue

        # 4) Validate step against current screen (enable soft page checks with optional page_scope)
        ok, errors, chosen = validate_step(
            screen,
            step,
            page_check_mode="soft" if page_scope else "off",
            page_field="current_page",
            allowed_pages=page_scope,
        )
        if not ok:
            # Feed errors back to the LLM in the next round to repair
            print(f"Validation errors at step {i}: {errors}")
            continue

        # 5) Execute and measure
        t0 = time.perf_counter()
        meta = perform_ui_action(step)
        elapsed = time.perf_counter() - t0
        success = bool(meta.get("success", True))

        # 6) Verify by re-analyzing the screen
        new_screen = analyze_current_screen()

        # 7) Append step with execution metadata
        steps.append({
            "step": i,
            "action": step.get("next_action", {}).get("action"),
            "page": step.get("analysis", {}).get("current_page_type", screen.get("current_page")),
            "description": step.get("analysis", {}).get("reason", ""),
            "target_element": step.get("evidence", {}).get("source_element_snapshot"),
            "success": success,
            "execution_time": elapsed,
            "after_screen_hash": new_screen.get("screen_hash"),
            "meta": {"tags": tags or [], "page_scope": page_scope or []},
        })

        # 7.1) Build authoritative chain node
        selectors = step.get("next_action", {}).get("target", {}).get("priority_selectors", [])
        chosen_selector = _pick_matching_selector(chosen or {}, selectors)
        chain_nodes.append({
            "step": i,
            "page": step.get("analysis", {}).get("current_page_type", screen.get("current_page")),
            "action": step.get("next_action", {}).get("action"),
            "selector": chosen_selector,
            "element_uuid": (chosen or {}).get("uuid") or step.get("evidence", {}).get("source_element_uuid"),
            "screen_hash_before": screen.get("screen_hash"),
            "screen_hash_after": new_screen.get("screen_hash"),
            "result": "success" if success else "failure",
            "human_line": f"[page] {screen.get('current_page')}, [action] {step.get('next_action', {}).get('action')} "
                           f"{(chosen_selector or {}).get('resource_id') or (chosen_selector or {}).get('content_desc') or (chosen_selector or {}).get('text') or ''}  --> (next)",
            "meta": {"tags": tags or [], "page_scope": page_scope or []}
        })

        # 8) Prepare for next round
        screen = new_screen

        # Optional: termination condition if objective is met
        # if objective_satisfied(screen):
        #     break

    # Build edges and human_readable chain summary
    edges = []
    for idx in range(1, len(chain_nodes)):
        edges.append({"from": chain_nodes[idx-1]["step"], "to": chain_nodes[idx]["step"]})
    human_readable = [f"[{n['step']}] {n['page']}: {n['action']}" + (
        f" {(n.get('selector') or {}).get('resource_id') or (n.get('selector') or {}).get('content_desc') or (n.get('selector') or {}).get('text') or ''}"
        if n.get('selector') else ""
    ) for n in chain_nodes]

    return {
        "objective": objective,
        "steps": steps,
        "final_screen": screen,
        "chain": {
            "version": "1.0",
            "nodes": chain_nodes,
            "edges": edges,
            "human_readable": human_readable,
        },
        "metadata": {"tags": tags or [], "page_scope": page_scope or []}
    }

