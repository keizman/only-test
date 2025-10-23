#!/usr/bin/env python3
"""
MCP + LLM Workflow Demo - Unified Logging & Auto-Refresh Strategy
===================================================================

核心功能模块:
1. 统一日志系统
   - session_unified.json (tag/phase/seq)
   - execution_log.json (JSONL, 每行一条记录)
   - 所有prompt/response/tool/error分离存储在 prompts/ responses/ tools/ errors/ 目录

2. 屏幕信息过滤
   - 仅展示 target_app 的元素 (resource_id 前缀或 package 匹配)
   - 仅展示有效 selector (resource_id 或 text 非空)
   - 生成 selector 清单 (resource_id/text 去重)

3. 上下文维护
   - last-N responses: 每轮包含上N轮LLM输出
   - next_round_hint: LLM给出下一轮指导（新字段名，避免与current_action混淆）
   - invalid_note: 上一轮若失败则记录失败原因

4. 自动刷新策略 (关键设计)
   - LLM 若返回 tool_request → 自动执行 refresh
   - Refresh 后在同一轮进行二次提问 (带新selector)
   - 目标: 避免首屏卡住 (广告/loading) 浪费一轮
   - 约束: 最多刷新1次; 二次提问后若仍返回tool_request则记录并继续下一轮
   - 所有refresh记录在execution_log中 (status: tool_request_executed)

5. 日志关键字段说明
   - phase: session|plan|execution
   - round: 执行轮数 (1~max_rounds)
   - status: started|parsed|completed|tool_request_executed|failed
   - step_json: LLM 解析后的完整输出 (current_action 或 tool_request)
   - refresh_used: 是否在本轮执行了屏幕刷新

运行示例:
  # 仅规划和记录（默认，不执行 UI 动作）:
  python -m only_test.workflows.mcp_llm_workflow_demo \
    --requirement "播放VOD节目" \
    --target-app com.mobile.brasiltvmobile \
    --max-rounds 10 \
    --verbose

  # 真实执行 UI 动作（默认行为）:
  python -m only_test.workflows.mcp_llm_workflow_demo \
    --requirement "播放VOD节目" \
    --target-app com.mobile.brasiltvmobile \
    --max-rounds 10

  # 生成完整 JSON → 转 PY → 直接执行生成的 Python（添加 --execute）:
  python -m only_test.workflows.mcp_llm_workflow_demo \
    --requirement "播放VOD节目" \
    --target-app com.mobile.brasiltvmobile \
    --max-rounds 10 \
    --execute  # <-- 生成完成后转换为 Python 并尝试直接执行

可选参数:
  --execute               在完成阶段：将最终 JSON 转换为 Python，并尝试直接执行
  --max-rounds N          最大轮数 (CLI > plan > 默认10, 绝对上限20)
  --history-window N      context窗口大小 (默认从config读取或10)
  --verbose / -v          DEBUG级别控制台输出
  --auto-close-limit N    广告自动关闭尝试数

调整策略(当首轮卡住时):
  关闭自动刷新: 注释或删除 "# Re-prompt once with refreshed screen info" 代码块
  改prompt强度: 调整 "生成规则" 中的措辞，如改为仅 wait/swipe
  查看selector: 检查 tool_get_current_screen_info_round_1.json 中 elements 内容
  
  check `mcp_execution_log.json` and the discrete files under `tools/` (e.g., tool_*.json).
- Entries in `mcp_execution_log.json` only reflect MCP tool invocations and their results;
  non-tool events (planning, parsing, LLM text responses) are intentionally not recorded there.

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
    parser.add_argument("--execute", action="store_true", help="After completion: convert final JSON to Python and try to execute")
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
                # tool_ 文件：先不处理，等保存文件后再调用 log_tool_execution
                pass
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
            
            # tool_ 文件：保存后调用 log_tool_execution，使用已保存的路径
            if name.startswith("tool_"):
                try:
                    tool_name = name.replace("tool_", "").replace(".json", "")
                    data = json.loads(content_str)
                    relative_path = str(p.relative_to(session_dir))
                    # 不传 result，避免重复保存
                    logger.log_tool_execution(
                        tool_name=tool_name,
                        success=bool(data.get("success")),
                        result=None,  # result 已保存在 tools/ 目录
                        execution_time=float(data.get("execution_time", 0.0)),
                        error=data.get("error"),
                        input_params=data.get("input_params") or data.get("parameters"),
                    )
                    # 记录文件路径
                    tool_result_dump_map[tool_name] = relative_path
                except Exception as tool_log_error:
                    logger.warning(f"Failed logging tool execution for {name}: {tool_log_error}")
                    
        except Exception as e:
            logger.warning(f"Failed writing {name}: {e}")

    # session start meta
    logger.log_session_start({
        "session_id": session_id,
        "args": {"requirement": args.requirement, "target_app": args.target_app, "device_id": args.device_id, "max_rounds": args.max_rounds, "execute": args.execute},
        "paths": {"session_dir": str(session_dir)},
        "timestamps": {"started_at": datetime.now().isoformat()},
    })

    # mcp_execution_log: only records MCP tool invocations and their responses.
    # Note: We intentionally do not create execution_log.json anymore.
    #       Use mcp_execution_log.json to inspect MCP call history.
    mcp_exec_log_path = session_dir / "mcp_execution_log.json"
    mcp_log_entries = []  # Collect all entries in memory for proper JSON array format
    
    # Android 交互日志（底层调试）
    android_interaction_log_path = session_dir / "android_interaction_log.json"
    ad_detection_log_path = session_dir / "ad_detection_log.json"
    from only_test.lib.android_interaction_logger import initialize_android_logger
    initialize_android_logger(android_interaction_log_path, ad_detection_log_path)
    logger.info(f"Android interaction log: {android_interaction_log_path}")
    logger.info(f"Ad detection log: {ad_detection_log_path}")
    
    def append_mcp_log(*, tool: str, parameters: dict | None, success: bool, result_dump_path: str | None, phase: str, round_idx: int | None = None, error: str | None = None, exec_log: list | None = None, result_summary: dict | None = None) -> None:
        try:
            rec = {
                "phase": phase,
                "tool": tool,
                "parameters": parameters or {},
                "success": bool(success),
                "result_dump_path": result_dump_path or "",
                "timestamp": datetime.now().isoformat(),
            }
            if round_idx is not None:
                rec["round"] = int(round_idx)
            if error:
                rec["error"] = str(error)
            if exec_log:
                rec["exec_log"] = list(exec_log)  # 记录执行日志
            if result_summary:
                rec["result_summary"] = dict(result_summary)  # 记录结果摘要
            
            # Append to in-memory list
            mcp_log_entries.append(rec)
            
            # Write complete JSON array (overwrite each time for proper format)
            with open(mcp_exec_log_path, 'w', encoding='utf-8') as f:
                json.dump(mcp_log_entries, f, ensure_ascii=False, indent=2)
            
            # Also write to combined log for convenience
            with open(combined_log_path, 'a', encoding='utf-8') as cf:
                cf.write(json.dumps({"name": "mcp_execution_log", **rec}, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # execution_log.jsonl 已移除 - 无实际用途
    # 所有重要日志已记录在 mcp_execution_log.json 和 session_combined.json 中

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
        # Enforce fail-fast: exit when start_app reports failure (either top-level or nested result.success)
        start_success = bool(getattr(start_resp, 'success', False))
        try:
            res_obj = getattr(start_resp, 'result', None)
            if isinstance(res_obj, dict) and ('success' in res_obj):
                start_success = start_success and bool(res_obj.get('success'))
        except Exception:
            pass
        if start_success:
            try:
                append_mcp_log(tool="start_app", parameters=_params_start, success=True, result_dump_path="tools/tool_start_app.json", phase="init")
            except Exception:
                pass
        if not start_success:
            err_msg = None
            try:
                err_msg = getattr(start_resp, 'error', None)
                if not err_msg and isinstance(getattr(start_resp, 'result', None), dict):
                    err_msg = start_resp.result.get('error')
            except Exception:
                pass
            err_text = f"启动应用失败{(' - ' + err_msg) if err_msg else ''}"
            dump_text("error_start_app.txt", err_text)
            try:
                logger._log_structured('error', 'start_app failed', name='start_app', content=err_text)
            except Exception:
                pass
            try:
                append_mcp_log(tool="start_app", parameters=_params_start, success=False, result_dump_path="tools/tool_start_app.json", phase="init", error=err_text)
            except Exception:
                pass
            import sys as _sys
            _sys.exit(3)
    except Exception as hook_e:
        dump_text("error_start_app_exception.txt", str(hook_e))
        try:
            append_mcp_log(tool="start_app", parameters={"application": args.target_app, "force_restart": True}, success=False, result_dump_path=None, phase="init", error=str(hook_e))
        except Exception:
            pass
        import sys as _sys
        _sys.exit(3)

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
    try:
        append_mcp_log(tool="get_current_screen_info", parameters=_params_plan, success=bool(getattr(initial_screen,'success', True)), result_dump_path="tools/tool_get_current_screen_info_plan.json", phase="plan")
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
                if fname and code:
                    rendered.append(f"{fname}:\n{code}")
            return ("往期用例示例（仅参考动作思路） [[[ START ]]]  :\n\n" + "\n\n".join(rendered) + " [[[ END ]]]") if rendered else ""
        except Exception:
            return ""

    plan_prompt = (
        "# 仅输出严格JSON，不要使用Markdown。\n\n"
        "你是 Only-Test 的用例规划助手。请先给出高层次计划（不挑具体selector），再由后续步骤基于当前XML选择器执行。\n\n"
        f"测试目标: {args.requirement}\n\n"
        + _render_examples(examples) + ("\n\n" if _render_examples(examples) else "") +
        "[[[ END ]]], 注意：计划阶段禁止编造任何 resource_id/text 值；具体selector 由后续步骤从当前XML的可选列表中选择。\n\n"
        "【严禁步骤】应用启动/重启/广告关闭已由框架自动完成，测试从应用已启动后开始：\n"
        "- 禁止: restart, launch, close_ads, start_app\n"
        "- 允许: click, input, press, wait_for_elements, wait, assert, swipe, click_with_bias, wait_for_disappearance\n"
        "- 特例: 仅当测试需求明确要求\"重启应用\"\"退出重进\"时才可使用 restart\n\n"
        "所有可用动作类别（后续步骤会用到）：click, input, press (仅支持ENTER/BACK/HOME/MENU), wait_for_elements, wait, assert, swipe, click_with_bias, wait_for_disappearance。\n"
        f"输出JSON格式（必须包含 keyword 和 max_rounds；其中 max_rounds 为本计划所需的实际轮数，且不得超过上限 {args.max_rounds}）：{{\n"
        "  \"plan_id\": \"plan_YYYYmmdd_HHMMSS\",\n"
        "  \"objective\": \"...\",\n"
        "  \"keyword\": \"(本用例关键语义标识)\",\n"
        "  \"max_rounds\": 4,\n"
        "  \"steps\": [\n"
        "    {\"intent\": \"...\", \"action\": \"click\"}\n"
        "  ]\n"
        "}\n"
        "注意：steps 中不要包含 restart/launch/close_ads 等步骤！\n"
        "框架已自动完成的操作（禁止在计划中重复）：启动应用、关闭广告、等待初始化。\n\n"
    )
    dump_text("prompt_plan.txt", plan_prompt)
    llm = LLMClient()
    plan_msgs = [{"role": "system", "content": "You are Only-Test LLM. Output strict JSON only."}, {"role": "user", "content": plan_prompt}]
    plan_resp = llm.chat_completion(plan_msgs, temperature=0.1, max_tokens=800)
    dump_text("response_plan.txt", plan_resp.content or "")
    
    # 打印 Plan Response 到命令行
    logger.info("=" * 80)
    logger.info("PLAN RESPONSE:")
    if plan_resp.content:
        logger.info(plan_resp.content)
    else:
        logger.warning("Plan response is empty!")
    logger.info("=" * 80)
    
    plan_json = {}
    if plan_resp.success:
        try:
            plan_json = _extract_json_robust(plan_resp.content, kind="plan", required_keys=["plan_id","objective","steps"]) or {}
        except Exception as e:
            dump_text("error_parse_plan.txt", f"{e}\n\nRAW:\n{plan_resp.content}")
    plan_json.setdefault("plan_id", "plan_default")
    plan_json.setdefault("objective", args.requirement)
    plan_json.setdefault("keyword", "")
    plan_json.setdefault("steps", [])
    dump_text("parsed_plan.json", json.dumps(plan_json, ensure_ascii=False, indent=2))
    
    # 轮次计算：优先采用计划里的 max_rounds，其次退回到 CLI 上限；两者取较小值；并设置绝对上限 20 与下限 1
    cap_cli = int(args.max_rounds)
    planned_rounds = None
    try:
        if 'max_rounds' in plan_json:
            planned_rounds = int(plan_json.get('max_rounds'))
    except Exception:
        planned_rounds = None

    if planned_rounds is None or planned_rounds <= 0:
        total_rounds = max(1, min(cap_cli, 20))
    else:
        total_rounds = max(1, min(planned_rounds, cap_cli, 20))

    # 提示：从此处开始仅记录 MCP 工具调用到 mcp_execution_log.json（plan 元数据不再写入 execution_log）
    generated_steps = []
    step_responses: list[dict] = []

    # ============================================================
    # EXECUTION 阶段主循环 - 每轮流程说明
    # ============================================================
    # 1. 屏幕抓取: get_current_screen_info (target_app过滤)
    # 2. Prompt构建: 计划+selector清单+上N轮输出+指导
    # 3. LLM调用: 返回 current_action 或 tool_request
    # 4. 刷新机制(若tool_request): 自动refresh → 二次提问
    # 5. 记录日志: execution_log.json + 文件分离存储
    # ============================================================
    for round_idx in range(1, total_rounds + 1):
        logger.set_phase("execution", current_round=round_idx, max_rounds=total_rounds)
        _params_round = {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit}
        screen = await server.execute_tool("get_current_screen_info", _params_round)
        dump_text(f"tool_get_current_screen_info_round_{round_idx}.json", json.dumps((screen.to_dict() if hasattr(screen,'to_dict') else screen), ensure_ascii=False, indent=2))
        try:
            append_mcp_log(tool="get_current_screen_info", parameters=_params_round, success=bool(getattr(screen,'success', True)), result_dump_path=f"tools/tool_get_current_screen_info_round_{round_idx}.json", phase="execution", round_idx=round_idx)
        except Exception:
            pass

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

        # ============================================================
        # Prompt 构建函数 - 消除 step_prompt 和 step_prompt2 的重复
        # ============================================================
        def _build_step_prompt(screen_data, last_note_text: str) -> str:
            """统一的 step prompt 构建函数，支持首次提问和刷新后二次提问"""
            return (
                "# 仅输出严格JSON。严禁Markdown。只输出一个 JSON 对象。\n\n"
                + last_note_text +
                f"测试目标: {args.requirement}\n\n"
                f"总体计划: {json.dumps(plan_json, ensure_ascii=False)}\n\n"
                f"目标应用包: {args.target_app}\n\n"
                "选择器范围规则：\n"
                f"- 仅允许目标应用元素：resource_id 以 '{args.target_app}:id/' 开头，或 package == '{args.target_app}'；\n"
                "- 系统对话白名单：android, com.android.permissioncontroller, com.google.android.permissioncontroller, com.android.packageinstaller, com.android.systemui。\n\n"
                "启动/广告处理：启动/重新启动应用/关闭启动应用广告已由框架自动处理，禁止生成任何 close_ads/关闭广告 的动作或步骤。\n\n"
                "目标应用可选选择器（JSON 概览，已过滤无效控件）：\n"
                f"{_build_screen_summary_json(screen_data, args.target_app, max_items=30)}\n\n"
                + (examples_block + "\n\n" if examples_block else "") +
                f"上 {session_history_window} 轮输出是：\n{_last_n_responses(session_history_window)}\n\n"
                f"你的任务是 step[{round_idx}] = {_current_plan_step(round_idx)}\n\n"
                f"之前步骤(摘要)[[[ START ]]]: {json.dumps(generated_steps, ensure_ascii=False)}[[[ END ]]]\n\n"
                "==== 输出要求 ====\n"
                "【默认输出】直接返回操作决策，根据上述可用选择器和当前任务生成具体动作。\n\n"
                "【标准输出格式】- 99%情况使用此格式：\n"
                "{\n"
                "  \"analysis\": {\n"
                "    \"current_page_type\": \"当前页面类型\",\n"
                "    \"available_actions\": [\"click\",\"input\",\"press\",\"wait_for_elements\",\"wait\",\"restart\",\"launch\",\"assert\",\"swipe\"],\n"
                "    \"reason\": \"分析依据\",\n"
                "    \"next_round_hint\": \"(可选)给下一轮的简短提示，帮助保持计划连贯性\"\n"
                "  },\n"
                "  \"current_action\": {  // ← 这个会被MCP立即执行\n"
                "    \"action\": \"click|input|press|wait_for_elements|wait|restart|launch|assert|swipe\",\n"
                "    \"reason\": \"选择此动作的依据(比如: \\\"往期用例示例\\\"中有相似用例, 直接遵循使用相同步骤的动作)\",\n"
                "    \"target\": {\n"
                "      // click/input/wait_for_elements 使用 priority_selectors\n"
                "      \"priority_selectors\": [{\"resource_id\": \"com.app:id/xxx\"}],\n"
                "      // press 使用 keyevent 字段，仅限ENTER/BACK/HOME/MENU四个值\n"
                "      \"keyevent\": \"ENTER|BACK|HOME|MENU (仅press动作，禁止其它值)\"\n"
                "    },\n"
                "    \"data\": \"输入文本(仅input动作需要)\",\n"
                "    \"wait_after\": 0.8,\n"
                "    \"expected_result\": \"预期结果描述\"\n"
                "  },\n"
                "  \"evidence\": {\"screen_hash\": \"...\"}\n"
                "}\n\n"
                "【选择器生成规则】：\n"
                "- priority_selectors 必须从上述「目标应用可选选择器清单」中精确复制 resource_id 或 text\n"
                "- 若清单中无完全匹配的控件，使用 wait_for_elements 等待或 swipe 滚动查找\n"
                "- 禁止编造不存在的 resource_id/text\n\n"
                "【字段说明】：\n"
                "- current_action: 本轮要立即执行的动作（必须字段）\n"
                "- next_round_hint: 给下一轮的提示，避免规划漂移（可选字段，不会被执行）\n\n"
                "【动作参数说明】：\n"
                "- click/input/wait_for_elements: 需要 priority_selectors 定位元素\n"
                "- press: 需要 target.keyevent 字段，仅支持以下4个按键（禁止使用其它值）：\n"
                "  * ENTER - 回车键，用于搜索确认、输入提交\n"
                "  * BACK - 返回键，用于退出当前页面\n"
                "  * HOME - 主屏键，用于返回桌面\n"
                "  * MENU - 菜单键，用于打开选项菜单\n"
                "  示例：{\"action\": \"press\", \"target\": {\"keyevent\": \"ENTER\"}}\n"
                "  转换为 Python: keyevent('ENTER')\n"
                "  [!] 其它按键（如RECENT/DEL/DPAD等）不支持，请勿使用\n"
                "- swipe: 需要 target 中的 start_px/end_px 坐标\n"
                "- wait/restart/launch: 不需要 target\n\n"
                "【特殊情况】仅当同时满足以下3个条件时才可返回 tool_request（极少使用）：\n"
                "1. 上述选择器清单完全为空 或 全是无关控件\n"
                "2. 当前轮次尚未使用过 tool_request\n"
                "3. 确实需要重新分析屏幕获取最新元素\n"
                "格式: {\"tool_request\": {\"name\": \"analyze_current_screen\", \"params\": {}, \"reason\": \"具体原因\"}}\n"
            )

        # inject guidance from previous round
        last_note = ""
        try:
            notes = []
            if generated_steps and isinstance(generated_steps[-1], dict):
                if generated_steps[-1].get('invalid_note'):
                    notes.append(generated_steps[-1]['invalid_note'])
                if generated_steps[-1].get('next_round_hint'):
                    notes.append("上一轮提示: " + str(generated_steps[-1]['next_round_hint']))
            last_note = ("\n\n".join(notes) + "\n\n") if notes else ""
        except Exception:
            last_note = ""

        # ============================================================
        # Step Prompt 构建 - 每轮的 LLM 输入
        # ============================================================
        # 关键要素 (scope从宽到严):
        #  ① 高层计划: plan_json (step[round_idx])
        #  ② Selector 可选: JSON 概览 + 清单 (resource_id/text 去重)
        #  ③ 上N轮上下文: 先前 step_responses 中最近 N 轮 的 response
        #  ④ 前一轮反馈: invalid_note (if 失败) + next_round_hint (if 指导)
        #  ⑤ 约束规则: 只用提供的 selector; 无刹优先 wait/swipe; 最多刷新1次 tool_request
        #
        # 三种输出之一 (LLM 必须仅输出一个 JSON):
        #  A. tool_request: {"tool_request": {"name": "analyze_current_screen", ...}}
        #  B. current_action: {"analysis": {...}, "current_action": {...}, "evidence": {...}}
        # ============================================================
        step_prompt = _build_step_prompt(screen, last_note)
        dump_text(f"prompt_step_{round_idx}.txt", step_prompt)
        msgs = [{"role": "system", "content": "You are Only-Test LLM. Output strict JSON only. Do not use markdown fences."}, {"role": "user", "content": step_prompt}]
        resp = llm.chat_completion(msgs, temperature=0.2, max_tokens=800)
        dump_text(f"response_step_{round_idx}.txt", resp.content or "")
        
        # 打印 Step Response 到命令行
        logger.info("-" * 80)
        logger.info(f"STEP {round_idx} RESPONSE:")
        if resp.content:
            logger.info(resp.content)
        else:
            logger.warning(f"Step {round_idx} response is empty!")
        logger.info("-" * 80)
        
        try:
            step_responses.append({"round": round_idx, "response": (resp.content or "")})
        except Exception:
            pass

        # parse and remember guidance
        step_json = {}
        try:
            step_json = _extract_json_robust(resp.content, kind="step", required_keys=["current_action", "tool_request"]) or {}
        except Exception as e:
            dump_text(f"error_parse_step_{round_idx}.txt", f"{e}\n\nRAW:\n{resp.content}")
            continue
        try:
            # 提取 next_round_hint（可能在顶层或 analysis 中）
            hint = step_json.get('next_round_hint') or ((step_json.get('analysis') or {}).get('next_round_hint'))
            if hint:
                step_json['next_round_hint'] = hint
        except Exception:
            pass

        generated_steps.append(step_json)
        
        # ============================================================
        # 自动刷新机制：避免首屏漂住浪费回合
        # ============================================================
        # 常规：不是每轮轮都需要 refresh（不浪费）。只在 LLM 返回 tool_request 时执行
        # 执行步骤：
        #  1. 检查 step_json 是否有 tool_request 字段
        #  2. 执行屏幕刷新 (tool_name='analyze_current_screen')
        #  3. 保存刷新后的屏幕为 _refresh.json
        #  4. 记录到 execution_log: {"status": "tool_request_executed", "refresh_used": true}
        #  5. 第二次提问: 用刷新后的屏幕重新构建 prompt、召唤 LLM、解析结果
        #
        # 二次提问的作用：
        #  - 第一次 prompt 的 selector 清单可能是广告/loading。刷新后有真实的元素
        #  - LLM 第二次提问时有更多 current_action 的选择，提高成功率
        #  - 一旦二次提问依然返回 tool_request，记录 "invalid_note"，继续下一轮
        #
        # 阻、关闭或修改此机制：
        #  - 删除整个 if 块代码: 日志中不会记录 refresh 回合
        #  - 提高阈倾: 修改 prompt 中的"优先 wait/swipe" 措辞为"底丢收所有 wait/swipe（无selector）"
        #  - 递上一次求情：修改 "max_rounds" 或 --max-rounds 参数2（实验solue 无求情）
        # ============================================================
        try:
            if isinstance(step_json, dict) and isinstance(step_json.get('tool_request'), dict):
                tr = step_json['tool_request']
                tr_name = (tr.get('name') or '').strip()
                tr_params = tr.get('params') if isinstance(tr.get('params'), dict) else {}
                if tr_name == 'analyze_current_screen':
                    _params_tr = {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit}
                    # allow prompt-provided params to override defaults safely
                    _params_tr.update({k:v for k,v in tr_params.items() if k in ("include_elements","clickable_only","auto_close_limit")})
                    tr_resp = await server.execute_tool("get_current_screen_info", _params_tr)
                    dump_text(f"tool_get_current_screen_info_round_{round_idx}_refresh.json", json.dumps((tr_resp.to_dict() if hasattr(tr_resp,'to_dict') else tr_resp), ensure_ascii=False, indent=2))
                    # Re-prompt once with refreshed screen info
                    try:
                        step_prompt2 = _build_step_prompt(tr_resp, last_note)
                        dump_text(f"prompt_step_{round_idx}_refresh.txt", step_prompt2)
                        msgs2 = [{"role": "system", "content": "You are Only-Test LLM. Output strict JSON only. Do not use markdown fences."}, {"role": "user", "content": step_prompt2}]
                        resp2 = llm.chat_completion(msgs2, temperature=0.2, max_tokens=800)
                        dump_text(f"response_step_{round_idx}_refresh.txt", resp2.content or "")
                        
                        # 打印 Refresh Response 到命令行
                        logger.info("-" * 80)
                        logger.info(f"STEP {round_idx} REFRESH RESPONSE (二次提问):")
                        if resp2.content:
                            logger.info(resp2.content)
                        else:
                            logger.warning(f"Step {round_idx} refresh response is empty!")
                        logger.info("-" * 80)
                        
                        try:
                            step_responses.append({"round": round_idx, "response": (resp2.content or "")})
                        except Exception:
                            pass
                        ok2, obj2 = _safe_json_load(resp2.content or "")
                        if ok2 and isinstance(obj2, dict) and not obj2.get('tool_request'):
                            step_json = obj2
                    except Exception:
                        pass
                else:
                    # Unknown tool request type; just log warning
                    logger.warning(f"Unsupported tool request: {tr_name} at round {round_idx}")
        except Exception as e:
            logger.warning(f"Auto-refresh handling failed at round {round_idx}: {e}")
        
        # ============================================================
        # 移除防御性检查 - 让 MCP 通过实际执行来验证有效性
        # 即使 current_action 看起来无效，也交给 MCP 处理并返回真实结果
        # ============================================================

        # ============================================================
        # 执行实际的 UI 动作
        # ============================================================
        # 统一使用 execute_step_json 工具
        # - 直接传入 LLM 输出的 current_action
        # - MCP层负责验证有效性并返回详细结果
        # - 日志统一命名为 mcp_execute_step_json.json
        # ============================================================
        action_result = None
        if isinstance(step_json, dict) and isinstance(step_json.get('current_action'), dict):
            current_action = step_json['current_action']
            action_type = current_action.get('action', '')
            
            # 跳过 tool_request（已在上面处理过）
            if not step_json.get('tool_request'):
                try:
                    # 使用统一的 MCP 工具入口
                    logger.info(f"执行 MCP 动作: {action_type or 'unknown'}")
                    
                    # execute_step_json 接受 step 字典，包含 action/target/data/wait_after
                    step_params = {
                        "step": current_action,  # 直接传入 LLM 生成的 current_action
                        "verify": True  # 启用前后验证
                    }
                    
                    # 统一调用 execute_step_json
                    action_result = await server.execute_tool("execute_step_json", step_params)
                    
                    # 记录执行结果到 mcp_execution_log（不再保存完整的 pre/post 屏幕快照，避免冗余）
                    if action_result:
                        # 追加 MCP 调用简表到 mcp_execution_log（包含 exec_log）
                        try:
                            # Unwrap response to derive success/error/exec_log for logging
                            if hasattr(action_result, 'to_dict'):
                                ar = action_result.to_dict()  # MCPResponse
                                success_flag = bool(ar.get('success', False))
                                exec_log_data = ar.get('exec_log')
                                error_msg = ar.get('error')
                                result_summary = {
                                    "changed": ar.get('changed'),
                                    "invalid_action": ar.get('invalid_action'),
                                    "used": ar.get('used'),
                                    "message": ar.get('message')
                                }
                            elif isinstance(action_result, dict):
                                success_flag = bool(action_result.get('success', False))
                                exec_log_data = action_result.get('exec_log')
                                error_msg = action_result.get('error')
                                result_summary = {
                                    "changed": action_result.get('changed'),
                                    "invalid_action": action_result.get('invalid_action'),
                                    "used": action_result.get('used'),
                                    "message": action_result.get('message')
                                }
                            else:
                                success_flag = True
                                exec_log_data = None
                                error_msg = None
                                result_summary = None
                            
                            append_mcp_log(
                                tool="execute_step_json",
                                parameters=step_params,
                                success=success_flag,
                                result_dump_path=None,  # 不再保存冗余的完整结果文件
                                phase="execution",
                                round_idx=round_idx,
                                exec_log=exec_log_data,  # 包含执行日志
                                error=error_msg,
                                result_summary=result_summary  # 包含结果摘要
                            )
                        except Exception:
                            pass
                        
                        # 提取执行状态
                        if isinstance(action_result, dict):
                            success = bool(action_result.get('success', False))
                            changed = bool(action_result.get('changed', False))
                            invalid = bool(action_result.get('invalid_action', False))
                            exec_log_display = action_result.get('exec_log', [])
                            used_selector = action_result.get('used', {})
                            error_display = action_result.get('error')
                        else:
                            success = bool(getattr(action_result, 'success', False))
                            changed = bool(getattr(action_result, 'changed', False))
                            invalid = bool(getattr(action_result, 'invalid_action', False))
                            exec_log_display = getattr(action_result, 'exec_log', [])
                            used_selector = getattr(action_result, 'used', {})
                            error_display = getattr(action_result, 'error', None)
                        
                        # 显示执行日志（实时查看执行了什么命令）
                        if exec_log_display:
                            logger.info(f"[EXEC LOG round {round_idx}]:")
                            for log_line in exec_log_display:
                                logger.info(f"  -> {log_line}")
                        
                        # 显示使用的选择器
                        if used_selector:
                            logger.info(f"[SELECTOR] {used_selector}")
                        
                        # 显示验证结果
                        status_icon = "[OK]" if success else "[FAIL]"
                        logger.info(f"{status_icon} 动作执行{'成功' if success else '失败'}: {action_type} | 屏幕{'已变化' if changed else '未变化'} | {'无效动作' if invalid else '有效'}")
                        
                        # 显示错误信息（如果有）
                        if error_display:
                            logger.warning(f"[ERROR] {error_display}")
                        
                except Exception as e:
                    # 记录异常到日志文件
                    logger.error(f"执行 MCP 动作异常: {e}")
                    dump_text(f"error_execute_step_round_{round_idx}.txt", f"Exception: {e}\n\nStep JSON:\n{json.dumps(current_action, ensure_ascii=False, indent=2)}")
                    action_result = {"success": False, "error": str(e), "exception": True}
        
        # Round execution completed (详细日志已在 MCP 层记录)

    # ============================================================
    # COMPLETION 阶段——日志记录且结束。无实际执行
    # ============================================================
    # 当前应用场景：仅执行「规划→提问」不执行动作
    # 如需真实下笔测试，需补上:
    #  - perform_and_verify 或 perform_ui_action 调用
    #  - 控制流程（根据 current_action 类型执行）
    #  - 一上轮的打岔提示、帮扶提示等
    # ============================================================
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
    
    # 打印 Completion Response 到命令行
    logger.info("=" * 80)
    logger.info("COMPLETION RESPONSE:")
    if comp_resp.content:
        logger.info(comp_resp.content)
    else:
        logger.warning("Completion response is empty!")
    logger.info("=" * 80)

    # 解析最终 JSON，并保存到 --outdir
    final_case = {}
    try:
        final_case = _extract_json_robust(comp_resp.content or "", kind="final", required_keys=["test_steps","test_steps","hooks","target_app"]) or {}
    except Exception as e:
        dump_text("error_parse_completion.txt", f"{e}\n\nRAW:\n{comp_resp.content}")
        final_case = {}

    try:
        Path(args.outdir).mkdir(parents=True, exist_ok=True)
        json_name = f"generated_case_{session_id}.json"
        json_path = Path(args.outdir) / json_name
        if final_case:
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(final_case, ensure_ascii=False, indent=2))
            dump_text("artifact_final_case_path.txt", str(json_path))
        else:
            dump_text("artifact_final_case_path.txt", "(final case empty)")
    except Exception as e:
        dump_text("error_write_final_case.txt", str(e))

    # 若传入 --execute：将最终 JSON 转为 Python，并尝试执行
    if args.execute and final_case:
        try:
            import subprocess as _subp
            py_out_dir = Path('only_test/testcases/python')
            py_out_dir.mkdir(parents=True, exist_ok=True)
            py_out = py_out_dir / f"generated_{session_id}.py"
            # 调用生成器
            _cmd = [sys.executable, 'only_test/tools/codegen/json_to_airtest.py', '--in', str(json_path), '--out', str(py_out)]
            _gen = _subp.run(_cmd, capture_output=True, text=True)
            dump_text("artifact_codegen_stdout.txt", _gen.stdout or "")
            dump_text("artifact_codegen_stderr.txt", _gen.stderr or "")
            if _gen.returncode != 0:
                logger.error("JSON→Python 转换失败")
            else:
                logger.info(f"已生成 Python 用例: {py_out}")
                # 直接尝试用 Python 执行（如需 airtest，请改用 `airtest run`）
                _run = _subp.run([sys.executable, str(py_out)], capture_output=True, text=True)
                dump_text("artifact_run_generated_stdout.txt", _run.stdout or "")
                dump_text("artifact_run_generated_stderr.txt", _run.stderr or "")
                if _run.returncode != 0:
                    logger.warning("执行生成的 Python 用例失败，请检查连接/设备/依赖，并考虑使用 airtest run")
                else:
                    logger.info("生成的 Python 用例执行完成")
        except Exception as e:
            dump_text("error_execute_generated.txt", str(e))

    # ============================================================
    # 会话结束
    # ============================================================
    # 日志已在 execution_log.json 中被逐条记录
    # 统计摘要由 unified_logger 在 session_end 输出
    logger.log_session_end({"note": "completed", "total_rounds": total_rounds, "generated_steps": len(generated_steps)})


if __name__ == "__main__":
    asyncio.run(main())
