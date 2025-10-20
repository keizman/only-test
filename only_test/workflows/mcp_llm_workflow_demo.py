#!/usr/bin/env python3
"""
MCP + LLM Workflow (workflows version)
- Uses unified logger (session_unified.json)
- Filters invalid selectors (resource_id and text both empty)
- Step prompt includes last-N previous responses (configurable)
- Adds next_action_guidance to improve next round
- Includes example file contents (truncated) instead of only filenames

Run:
  python -m only_test.workflows.mcp_llm_workflow_demo --requirement "..." --target-app com.xxx
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure repository root on sys.path
_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from only_test.lib.logging import get_logger
from only_test.lib.mcp_interface.mcp_server import MCPServer, MCPTool
from only_test.lib.llm_integration.llm_client import LLMClient


async def main():
    parser = argparse.ArgumentParser(description="Workflows MCP+LLM demo with improved prompts and logging")
    parser.add_argument("--requirement", required=True)
    parser.add_argument("--target-app", default="com.mobile.brasiltvmobile")
    parser.add_argument("--outdir", default="only_test/testcases/generated")
    parser.add_argument("--device-id", default=None)
    parser.add_argument("--logdir", default="logs/mcp_demo")
    parser.add_argument("--max-rounds", type=int, default=6)
    parser.add_argument("--auto-close-limit", type=int, default=None)
    parser.add_argument("--history-window", type=int, default=None, help="How many previous step responses to include (defaults from YAML or 10)")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    console_level = logging.DEBUG if args.verbose else logging.INFO
    logger = get_logger(session_id, args.logdir, console_level)

    # directories
    session_dir = logger.session_dir
    prompts_dir = session_dir / "prompts"
    responses_dir = session_dir / "responses"
    tools_dir = session_dir / "tools"
    errors_dir = session_dir / "errors"
    warnings_dir = session_dir / "warnings"
    artifacts_dir = session_dir / "artifacts"
    combined_log_path = session_dir / "session_combined.json"

    tool_result_dump_map: dict[str, str] = {}

    def dump_text(name: str, content: str) -> None:
        try:
            content_str = content if isinstance(content, str) else str(content)
            # combined jsonl
            with open(combined_log_path, 'a', encoding='utf-8') as cf:
                cf.write(json.dumps({"name": name, "timestamp": datetime.now().isoformat(), "content": content_str}, ensure_ascii=False) + "\n")
            # unified logger events
            if name.startswith("prompt_"):
                logger._log_structured('prompt', f"Prompt generated: {name}", name=name, content=content_str)
            elif name.startswith("response_"):
                logger._log_structured('response', f"Response received: {name}", name=name, content=content_str)
            elif name.startswith("tool_"):
                try:
                    tool_name = name.replace("tool_", "").replace(".json", "")
                    data = json.loads(content_str)
                    res_dump_path = logger.log_tool_execution(
                        tool_name=tool_name,
                        success=bool(data.get("success")),
                        result=data.get("result"),
                        execution_time=float(data.get("execution_time", 0.0)),
                        error=data.get("error"),
                        input_params=data.get("input_params") or data.get("parameters"),
                    )
                    if isinstance(res_dump_path, str) and res_dump_path:
                        tool_result_dump_map[tool_name] = res_dump_path
                except Exception:
                    logger._log_structured('tool_execution', f"Tool execution: {name}", name=name, content=content_str)
            elif name.startswith("error_"):
                logger._log_structured('error', f"Error: {name}", name=name, content=content_str)
            else:
                logger._log_structured('artifact', f"Artifact: {name}", name=name, content=content_str)
            # discrete files
            p = None
            if name.startswith("prompt_"):
                p = prompts_dir / name
            elif name.startswith("response_"):
                p = responses_dir / name
            elif name.startswith("tool_"):
                p = tools_dir / name
            elif name.startswith("error_"):
                p = errors_dir / name
            else:
                p = artifacts_dir / name
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(content_str)
        except Exception as e:
            logger.warning(f"Failed writing {name}: {e}")

    # session start meta
    logger.log_session_start({
        "session_id": session_id,
        "args": {"requirement": args.requirement, "target_app": args.target_app, "device_id": args.device_id, "max_rounds": args.max_rounds, "execute": args.execute},
        "paths": {"session_dir": str(session_dir)},
        "timestamps": {"started_at": datetime.now().isoformat()},
    })

    # execution_log writer with elements_path redirection
    exec_log_path = session_dir / "execution_log.json"
    def append_exec_log(record: dict) -> None:
        try:
            rec = dict(record)
            rec.setdefault("timestamp", datetime.now().isoformat())
            v = rec.get("verification")
            if isinstance(v, dict):
                rnd = rec.get("round")
                tool_key = f"perform_and_verify_round_{rnd}" if rnd is not None else None
                ver_dump_path = tool_result_dump_map.get(tool_key or "", "")
                if ver_dump_path:
                    rec["verification_dump_path"] = ver_dump_path
                else:
                    rec["verification_dump_path"] = f"tools/tool_perform_and_verify_round_{rnd}.json" if rnd is not None else ""
                pre_tool_name = f"tool_get_current_screen_info_round_{rnd}{'_refresh' if rec.get('refresh_used') else ''}.json" if rnd is not None else ""
                pre_path = f"tools/{pre_tool_name}" if pre_tool_name else ""
                tv = v.get("result") if isinstance(v.get("result"), dict) else v
                for part, path_val in (("pre", pre_path), ("post", rec.get("verification_dump_path"))):
                    try:
                        if isinstance(tv.get(part), dict):
                            if "elements" in tv[part]:
                                tv[part].pop("elements", None)
                            if path_val:
                                tv[part]["elements_path"] = path_val
                    except Exception:
                        pass
            with open(exec_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            with open(combined_log_path, 'a', encoding='utf-8') as cf:
                cf.write(json.dumps({"name": "execution_log", **rec}, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # config loaders
    def _load_yaml() -> dict:
        try:
            cfg = Path('only_test/config/framework_config.yaml')
            if not cfg.exists():
                return {}
            import yaml  # type: ignore
            with open(cfg, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _load_auto_close_limit_from_config() -> int:
        data = _load_yaml()
        return int(((data.get('recognition') or {}).get('ads') or {}).get('auto_close_limit', 3))

    def _load_history_window_from_config() -> int:
        data = _load_yaml()
        hv = ((data.get('llm') or {}).get('history_window')) or ((data.get('prompts') or {}).get('history_window'))
        try:
            return int(hv) if hv is not None else 10
        except Exception:
            return 10

    session_auto_close_limit = args.auto_close_limit if args.auto_close_limit is not None else _load_auto_close_limit_from_config()
    session_history_window = args.history_window if args.history_window is not None else _load_history_window_from_config()
    try:
        os.environ['ONLY_TEST_AUTO_CLOSE_LIMIT'] = str(session_auto_close_limit)
    except Exception:
        pass

    # MCP server and tools
    server = MCPServer(device_id=args.device_id)
    from only_test.lib.mcp_interface.device_inspector import DeviceInspector
    inspector = DeviceInspector(device_id=args.device_id)
    await inspector.initialize()
    for attr_name in dir(inspector):
        fn = getattr(inspector, attr_name, None)
        if callable(fn) and hasattr(fn, "_mcp_tool_info"):
            info = getattr(fn, "_mcp_tool_info")
            server.register_tool(MCPTool(name=info["name"], description=info["description"], parameters=info.get("parameters", {}), function=fn, category=info.get("category", "general")))

    # restart target app
    try:
        _params_start = {"application": args.target_app, "force_restart": True}
        start_resp = await server.execute_tool("start_app", _params_start)
        _start_dict = start_resp.to_dict() if hasattr(start_resp, 'to_dict') else start_resp
        try:
            _tmp = dict(_start_dict); _tmp["input_params"] = _params_start
            dump_text("tool_start_app.json", json.dumps(_tmp, ensure_ascii=False, indent=2))
        except Exception:
            pass
    except Exception as hook_e:
        dump_text("error_start_app_exception.txt", str(hook_e))

    # Utilities for JSON extraction
    def _sanitize_json_str(s: str) -> str:
        import re
        s = s.strip()
        if s.startswith('```json'):
            s = s[7:]
        if s.startswith('```'):
            s = s[3:]
        if s.endswith('```'):
            s = s[:-3]
        s = re.sub(r"(^|\n)\s*//.*?(?=\n|$)", "\n", s)
        s = re.sub(r",\s*([}\]])", r"\1", s)
        return s.strip()

    def _split_json_objects_by_braces(s: str) -> list:
        s = _sanitize_json_str(s)
        objs, depth, start = [], 0, None
        for i, ch in enumerate(s):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth = max(0, depth-1)
                if depth == 0 and start is not None:
                    objs.append(s[start:i+1]); start = None
        if not objs:
            return [s] if s else []
        return objs

    def _safe_json_load(candidate: str):
        try:
            return True, json.loads(_sanitize_json_str(candidate))
        except Exception:
            return False, None

    def _pick_best_candidate(cands: list, required_keys: list) -> dict:
        best = None
        for c in cands:
            ok, obj = _safe_json_load(c)
            if not ok:
                continue
            if isinstance(obj, dict):
                if any((k in obj) for k in (required_keys or [])):
                    return obj
                if best is None:
                    best = obj
        return best or {}

    def _extract_json_robust(content: str, kind: str = "generic", required_keys: list | None = None) -> dict:
        req = list(required_keys or [])
        cands = _split_json_objects_by_braces(content or "")
        obj = _pick_best_candidate(cands, req)
        return obj if isinstance(obj, dict) else {}

    def _build_selector_pool_for_pkg(screen_resp, target_pkg: str):
        els = (screen_resp.result or {}).get('elements', []) if getattr(screen_resp, 'success', False) else []
        rids, texts = [], []
        for e in els:
            pkg = (e.get('package') or '').strip()
            rid = (e.get('resource_id') or '').strip()
            tx = (e.get('text') or '').strip()
            if (rid and rid.startswith(f"{target_pkg}:id/")) or pkg == target_pkg:
                if rid:
                    rids.append(rid)
                if tx:
                    texts.append(tx)
        def _dedup(seq):
            seen, out = set(), []
            for x in seq:
                if x not in seen:
                    seen.add(x); out.append(x)
            return out
        return {'resource_ids': _dedup(rids), 'texts': _dedup(texts)}

    def _format_selector_pool(pool: dict) -> str:
        def fmt(name: str, vals: list) -> str:
            vals = vals or []
            return f"- {name}({len(vals)}): " + (", ".join([str(v) for v in vals]) if vals else "[]")
        return "\n".join([fmt('resource_id', pool.get('resource_ids', [])), fmt('text', pool.get('texts', []))])

    def _build_screen_summary_json(screen_resp, target_pkg: str, max_items: int = 30) -> str:
        try:
            scr = screen_resp.to_dict() if hasattr(screen_resp, 'to_dict') else screen_resp
            res = (scr or {}).get('result', scr or {})
            els = (res or {}).get('elements', []) or []
            def _in_target(e: dict) -> bool:
                rid = (e.get('resource_id') or '').strip()
                pkg = (e.get('package') or '').strip()
                return bool((rid and rid.startswith(f"{target_pkg}:id/")) or (pkg == target_pkg))
            filtered = []
            for e in els:
                if not isinstance(e, dict) or not _in_target(e):
                    continue
                rid = (e.get('resource_id') or '').strip()
                tx = (e.get('text') or '').strip()
                if not rid and not tx:
                    continue
                filtered.append({'text': tx, 'resource_id': rid, 'class_name': (e.get('class_name') or '')})
            summary = {
                'current_app': (res or {}).get('current_app') or (scr or {}).get('current_app') or 'unknown',
                'current_page': (res or {}).get('current_page') or 'unknown',
                'page': (res or {}).get('page') or 'unknown',
                'total_elements': int((res or {}).get('total_elements', 0)),
                'clickable_elements': int((res or {}).get('clickable_elements', 0)),
                'element_analysis': {'has_text': int(((res or {}).get('element_analysis') or {}).get('has_text', 0))},
                'media_playing': bool((res or {}).get('media_playing', False)),
                'elements': filtered[:max_items],
            }
            return json.dumps(summary, ensure_ascii=False, indent=2)
        except Exception:
            return "{}"

    # LLM plan
    logger.set_phase("plan")
    # initial screen for planning
    _params_plan = {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit}
    initial_screen = await server.execute_tool("get_current_screen_info", _params_plan)
    _initial_dict = initial_screen.to_dict() if hasattr(initial_screen, 'to_dict') else initial_screen
    try:
        _id2 = dict(_initial_dict); _id2["input_params"] = _params_plan
        dump_text("tool_get_current_screen_info_plan.json", json.dumps(_id2, ensure_ascii=False, indent=2))
    except Exception:
        pass

    # few-shot examples (embed contents)
    examples = []
    try:
        golden_json_path = Path('only_test/testcases/generated/golden_example_airtest_record.json')
        golden_code_path = Path('only_test/testcases/python/example_airtest_record.py')
        if golden_code_path.exists():
            examples.append({'file': str(golden_code_path), 'content': golden_code_path.read_text(encoding='utf-8')})
        if golden_json_path.exists():
            examples.append({'file': str(golden_json_path), 'content': golden_json_path.read_text(encoding='utf-8')})
    except Exception:
        examples = []

    def _render_examples(examples: list) -> str:
        try:
            import os as _os
            rendered = []
            for e in examples or []:
                if not isinstance(e, dict):
                    continue
                fname = _os.path.basename(e.get('file',''))
                code = (e.get('content') or '').strip()
                if len(code) > 6000:
                    code = code[:6000] + "\n# ...(内容已截断)"
                if fname and code:
                    rendered.append(f"{fname}:\n{code}")
            return ("往期用例示例（仅参考动作思路）:\n\n" + "\n\n".join(rendered)) if rendered else ""
        except Exception:
            return ""

    plan_prompt = (
        "# 仅输出严格JSON，不要使用Markdown。\n\n"
        "你是 Only-Test 的用例规划助手。请先给出高层次计划（不挑具体selector），再由后续步骤基于当前XML选择器执行。\n\n"
        f"测试目标: {args.requirement}\n\n"
        + _render_examples(examples) + ("\n\n" if _render_examples(examples) else "") +
        "注意：计划阶段禁止编造任何 resource_id/text 值；具体selector 由后续步骤从当前XML的可选列表中选择。\n\n"
        "重要：启动应用时框架会自动处理启动广告；播放前的插播广告也由工具自动处理。因此【不要】在计划 steps 中单独安排任何关闭广告/close_ads 的步骤。\n\n"
        "可用动作类别（后续步骤会用到）：click, input, press, wait_for_elements, wait, restart, launch, assert, swipe, click_with_bias, wait_for_disappearance。\n"
        "可用工具：get_current_screen_info, perform_and_verify, perform_ui_action, close_ads, start_app（注意：即使存在 close_ads 工具，也不要在计划中单独安排该步骤）。\n\n"
        "输出JSON格式（必须包含 keyword 和 max_rounds）：{\n"
        "  \"plan_id\": \"plan_YYYYmmdd_HHMMSS\",\n"
        "  \"objective\": \"...\",\n"
        "  \"keyword\": \"(本用例关键语义标识)\",\n"
        f"  \"max_rounds\": {args.max_rounds},\n"
        "  \"steps\": [\n"
        "    {\"intent\": \"...\", \"action\": \"click\"}\n"
        "  ]\n"
        "}\n"
    )
    dump_text("prompt_plan.txt", plan_prompt)
    llm = LLMClient()
    plan_msgs = [{"role": "system", "content": "You are Only-Test LLM. Output strict JSON only."}, {"role": "user", "content": plan_prompt}]
    plan_resp = llm.chat_completion(plan_msgs, temperature=0.1, max_tokens=800)
    dump_text("response_plan.txt", plan_resp.content or "")
    plan_json = {}
    if plan_resp.success:
        try:
            plan_json = _extract_json_robust(plan_resp.content, kind="plan", required_keys=["plan_id","objective","steps"]) or {}
        except Exception as e:
            dump_text("error_parse_plan.txt", f"{e}\n\nRAW:\n{plan_resp.content}")
    plan_json.setdefault("plan_id", "plan_default")
    plan_json.setdefault("objective", args.requirement)
    plan_json.setdefault("keyword", "")
    plan_json.setdefault("max_rounds", args.max_rounds)
    plan_json.setdefault("steps", [])
    dump_text("parsed_plan.json", json.dumps(plan_json, ensure_ascii=False, indent=2))

    total_rounds = max(1, min(int(plan_json.get('max_rounds', args.max_rounds)), 20))
    generated_steps = []
    step_responses: list[dict] = []

    # rounds
    for round_idx in range(1, total_rounds + 1):
        logger.set_phase("execution", current_round=round_idx, max_rounds=total_rounds)
        _params_round = {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit}
        screen = await server.execute_tool("get_current_screen_info", _params_round)
        dump_text(f"tool_get_current_screen_info_round_{round_idx}.json", json.dumps((screen.to_dict() if hasattr(screen,'to_dict') else screen), ensure_ascii=False, indent=2))

        # examples for rounds
        examples_r = []
        try:
            py_dir = Path('only_test/testcases/python')
            if py_dir.exists():
                for pf in sorted(py_dir.glob('*.py'))[:2]:
                    examples_r.append({'file': str(pf), 'content': pf.read_text(encoding='utf-8')})
        except Exception:
            examples_r = []
        examples_block = _render_examples(examples_r)

        # last-N responses block
        def _last_n_responses(n: int) -> str:
            if not step_responses:
                return "(无)"
            items = step_responses[-max(1, int(n)) :]
            out = []
            for it in items:
                txt = (it.get('response') or '').strip()
                if len(txt) > 1200:
                    txt = txt[:1200] + "\n...TRUNCATED..."
                out.append(f"round={it.get('round')}:\n{txt}")
            return "\n\n".join(out)

        # current expected plan step
        def _current_plan_step(idx: int) -> str:
            try:
                steps = (plan_json or {}).get('steps') or []
                if not isinstance(steps, list) or not steps:
                    return "{}"
                i = max(0, min(len(steps)-1, idx-1))
                return json.dumps(steps[i], ensure_ascii=False)
            except Exception:
                return "{}"

        # inject guidance from previous round
        last_note = ""
        try:
            notes = []
            if generated_steps and isinstance(generated_steps[-1], dict):
                if generated_steps[-1].get('invalid_note'):
                    notes.append(generated_steps[-1]['invalid_note'])
                if generated_steps[-1].get('next_action_guidance'):
                    notes.append("上一轮指导: " + str(generated_steps[-1]['next_action_guidance']))
            last_note = ("\n\n".join(notes) + "\n\n") if notes else ""
        except Exception:
            last_note = ""

        step_prompt = (
            "# 仅输出严格JSON。严禁Markdown。只输出一个 JSON 对象。\n\n"
            + last_note +
            f"测试目标: {args.requirement}\n\n"
            f"总体计划: {json.dumps(plan_json, ensure_ascii=False)}\n\n"
            f"目标应用包: {args.target_app}\n\n"
            "选择器范围规则：\n"
            f"- 仅允许目标应用元素：resource_id 以 '{args.target_app}:id/' 开头，或 package == '{args.target_app}'；\n"
            "- 系统对话白名单：android, com.android.permissioncontroller, com.google.android.permissioncontroller, com.android.packageinstaller, com.android.systemui。\n\n"
            "生成规则：\n"
            "- priority_selectors 中的 resource_id/text 必须 EXACTLY 来自下列 JSON 概览；若无匹配，请返回 tool_request 刷新屏幕。\n"
            "- 启动/播放广告已由框架自动处理，禁止生成任何 close_ads/关闭广告 的动作或步骤。\n\n"
            "目标应用可选选择器（JSON 概览，已过滤无效控件）：\n"
            f"{_build_screen_summary_json(screen, args.target_app, max_items=30)}\n\n"
            + (examples_block + "\n\n" if examples_block else "") +
            f"上 {session_history_window} 轮输出是：\n{_last_n_responses(session_history_window)}\n\n"
            f"你的任务是 step[{round_idx}] = {_current_plan_step(round_idx)}\n\n"
            f"之前步骤(摘要): {json.dumps(generated_steps, ensure_ascii=False)}\n\n"
            "返回两种之一（务必只返回一个 JSON 对象）：\n"
            "1) tool_request 示例: {\"tool_request\": {\"name\": \"analyze_current_screen\", \"params\": {}, \"reason\": \"需要最新/一致的屏幕元素\"}}\n"
            "2) 单步决策示例: {\n"
            "  \"analysis\": {\"current_page_type\": \"...\", \"available_actions\": [\"click\",\"input\",\"press\",\"wait_for_elements\",\"wait\",\"restart\",\"launch\",\"assert\",\"swipe\"], \"reason\": \"...\", \"next_action_guidance\": \"(可选) 下一轮的简短自然语言指导\"},\n"
            "  \"next_action\": {\n"
            "    \"action\": \"click|input|wait_for_elements|wait|restart|launch|assert|swipe\",\n"
            "    \"reason\": \"(简述依据)\",\n"
            "    \"target\": {\n"
            "      \"priority_selectors\": [\n"
            "        {\"resource_id\": \"...\"}, {\"text\": \"...\"}\n"
            "      ]\n"
            "    },\n"
            "    \"data\": \"可选\", \"wait_after\": 0.8, \"expected_result\": \"...\"\n"
            "  },\n"
            "  \"evidence\": {\"screen_hash\": \"...\"}\n"
            "}\n"
        )
        dump_text(f"prompt_step_{round_idx}.txt", step_prompt)
        msgs = [{"role": "system", "content": "You are Only-Test LLM. Output strict JSON only. Do not use markdown fences."}, {"role": "user", "content": step_prompt}]
        resp = llm.chat_completion(msgs, temperature=0.2, max_tokens=800)
        dump_text(f"response_step_{round_idx}.txt", resp.content or "")
        try:
            step_responses.append({"round": round_idx, "response": (resp.content or "")})
        except Exception:
            pass

        # parse and remember guidance
        step_json = {}
        try:
            step_json = _extract_json_robust(resp.content, kind="step", required_keys=["next_action", "tool_request"]) or {}
        except Exception as e:
            dump_text(f"error_parse_step_{round_idx}.txt", f"{e}\n\nRAW:\n{resp.content}")
            continue
        try:
            nag = step_json.get('next_action_guidance') or ((step_json.get('analysis') or {}).get('next_action_guidance'))
            if nag:
                step_json['next_action_guidance'] = nag
        except Exception:
            pass

        generated_steps.append(step_json)

    # completion prompt (simple pass-through for now)
    logger.set_phase("completion")
    completion_prompt = (
        "# 仅输出严格JSON，整合所有步骤。严禁Markdown。只输出一个 JSON 对象。\n\n"
        f"测试目标: {args.requirement}\n\n"
        f"规划输出: {json.dumps(plan_json, ensure_ascii=False)}\n\n"
        f"步骤输出(摘要): {json.dumps(generated_steps, ensure_ascii=False)}\n\n"
        "请输出完整的 Only-Test JSON 测试用例（每步使用允许原子动作，包含 priority_selectors 或 bounds_px）。\n"
    )
    dump_text("prompt_completion.txt", completion_prompt)
    comp_msgs = [{"role": "system", "content": "You are Only-Test LLM. Output strict JSON only."}, {"role": "user", "content": completion_prompt}]
    comp_resp = llm.chat_completion(comp_msgs, temperature=0.15, max_tokens=2000)
    dump_text("response_completion.txt", comp_resp.content or "")

    # finish
    logger.log_session_end({"note": "completed"})


if __name__ == "__main__":
    asyncio.run(main())
