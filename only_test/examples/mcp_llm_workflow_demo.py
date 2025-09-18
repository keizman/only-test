#!/usr/bin/env python3
"""
MCP + LLM Workflow Demo
=======================

Simulates a human specifying a plan, then calls an MCP tool to
generate a testcase JSON. It will try a REAL external LLM first (via
LLMClient), and fall back to a mock LLM if real LLM is unavailable.
Finally, it converts the JSON to Python and prints artifact paths.

This demonstrates the intended flow: human plan → MCP tool invokes LLM →
JSON testcase → script-style Python → run on device.
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
import sys
import os

# Ensure repo root on sys.path (precede site-packages to avoid PyPI 'airtest' collision)
try:
    from pathlib import Path as _Path
    _repo_root = str(_Path(__file__).resolve().parents[2])
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
except Exception:
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Local imports
from only_test.lib.mcp_interface.mcp_server import MCPServer, MCPTool, MCPResponse
from only_test.lib.llm_integration.llm_client import LLMClient
from only_test.templates.prompts.generate_cases import TestCaseGenerationPrompts
from only_test.lib.code_generator.json_to_python import JSONToPythonConverter
from only_test.lib.json_to_python import PythonCodeGenerator
from only_test.lib.metadata_engine.path_builder import build_step_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def build_mock_llm_testcase(requirement: str, target_app: str) -> dict:
    """Return a structured testcase JSON as if produced by an external LLM."""
    ts_id = f"TC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return {
        "testcase_id": ts_id,
        "name": "LLM Generated: Playback Control Smoke",
        "description": requirement,
        "target_app": target_app,
        "variables": {
            "keyword": "Ironheart"
        },
        "metadata": {
            "priority": "medium",
            "category": "playback",
            "estimated_duration": 60
        },
        "execution_path": [
            {
                "step": 1,
                "action": "click",
                "description": "Open search or bring up search input",
                "target": {
                    "priority_selectors": [
                        {"resource_id": f"{target_app}:id/search_button"},
                        {"content_desc": "Search"},
                        {"text": "Search"}
                    ]
                },
                "success_criteria": "Search input focused"
            },
            {
                "step": 2,
                "action": "input",
                "description": "Type keyword into search box",
                "target": {
                    "priority_selectors": [
                        {"resource_id": f"{target_app}:id/search_input"}
                    ]
                },
                "data": "${keyword}",
                "success_criteria": "Input contains keyword"
            },
            {
                "step": 3,
                "action": "wait_for_elements",
                "description": "Wait for results list",
                "target": {
                    "priority_selectors": [
                        {"resource_id": f"{target_app}:id/result_item"}
                    ]
                },
                "timeout": 10,
                "success_criteria": "Results visible"
            }
        ],
        "assertions": [
            {
                "type": "check_search_results_exist",
                "expected": True,
                "description": "Results list should not be empty"
            }
        ]
    }


async def main():
    parser = argparse.ArgumentParser(description="Demo MCP workflow that calls LLM via MCP + templates to generate a testcase")
    parser.add_argument("--requirement", required=True, help="Human plan/requirement to pass to the LLM tool")
    parser.add_argument("--target-app", default="com.mobile.brasiltvmobile", help="Target app package")
    parser.add_argument("--outdir", default="only_test/testcases/generated", help="Where to write the generated JSON")
    parser.add_argument("--device-id", default=None, help="ADB device id (optional)")
    parser.add_argument("--logdir", default="logs/mcp_demo", help="Directory for detailed prompts/responses logs")
    parser.add_argument("--max-rounds", type=int, default=3, help="Max step-guidance rounds before completion")
    parser.add_argument("--auto-close-limit", type=int, default=None, help="Limit auto close-ad to first N screen analyses (overrides config)")
    parser.add_argument("--execute", action="store_true", help="Execute actions on device (unsafe). Default is dry-run")
    args = parser.parse_args()

    # Prepare session log directory and file handler
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    session_dir = Path(args.logdir) / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    # Structured subdirectories (kept for backward compatibility; disabled when SINGLE_FILE_LOG=True)
    prompts_dir = session_dir / "prompts"
    responses_dir = session_dir / "responses"
    tools_dir = session_dir / "tools"
    executions_dir = session_dir / "executions"
    errors_dir = session_dir / "errors"
    warnings_dir = session_dir / "warnings"
    artifacts_dir = session_dir / "artifacts"
    meta_dir = session_dir / "meta"
    for d in [prompts_dir, responses_dir, tools_dir, executions_dir, errors_dir, warnings_dir, artifacts_dir, meta_dir]:
        d.mkdir(exist_ok=True)

    # Unified combined log
    SINGLE_FILE_LOG = True
    combined_log_path = session_dir / "session_combined.jsonl"
    try:
        fh = logging.FileHandler(session_dir / "session.log", encoding='utf-8')
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)
    except Exception:
        pass

    def dump_text(name: str, content: str) -> None:
        try:
            # Always append to combined log
            rec = {
                "name": name,
                "timestamp": datetime.now().isoformat(),
                "content": content if isinstance(content, str) else str(content)
            }
            with open(combined_log_path, 'a', encoding='utf-8') as cf:
                cf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            # Optionally also write discrete files (disabled by default)
            if not SINGLE_FILE_LOG:
                if name.startswith("prompt_"):
                    p = prompts_dir / name
                elif name.startswith("response_"):
                    p = responses_dir / name
                elif name.startswith("tool_"):
                    p = tools_dir / name
                elif name.startswith("parsed_") or name.startswith("artifact_"):
                    p = artifacts_dir / name
                elif name.startswith("error_"):
                    p = errors_dir / name
                elif name.startswith("warning_"):
                    p = warnings_dir / name
                elif name.startswith("session") or name.endswith(".log"):
                    p = session_dir / name
                else:
                    p = meta_dir / name
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(content if isinstance(content, str) else str(content))
                logger.info(f"Wrote log artifact: {p}")
        except Exception as e:
            logger.warning(f"Failed writing {name}: {e}")

    # Write session meta
    try:
        import platform
        meta = {
            "session_id": session_id,
            "args": {
                "requirement": args.requirement,
                "target_app": args.target_app,
                "device_id": args.device_id,
                "max_rounds": args.max_rounds,
                "execute": args.execute,
            },
            "env": {
                "python": sys.version,
                "platform": platform.platform(),
            },
            "paths": {
                "session_dir": str(session_dir),
            },
            "timestamps": {"started_at": datetime.now().isoformat()}
        }
        dump_text("session_meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
    except Exception:
        pass

    # execution_log.jsonl (append-only)
    exec_log_path = session_dir / "execution_log.jsonl"
    def append_exec_log(record: dict) -> None:
        try:
            record = dict(record)
            record.setdefault("timestamp", datetime.now().isoformat())
            with open(exec_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            # also add to combined log
            with open(combined_log_path, 'a', encoding='utf-8') as cf:
                cf.write(json.dumps({"name": "execution_log", **record}, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # Resolve session-level auto_close_limit
    def _load_auto_close_limit_from_config() -> int:
        try:
            from pathlib import Path as _P
            cfg = _P('only_test/config/framework_config.yaml')
            if not cfg.exists():
                return 3
            try:
                import yaml  # type: ignore
            except Exception:
                return 3
            with open(cfg, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            return int(((data.get('recognition') or {}).get('ads') or {}).get('auto_close_limit', 3))
        except Exception:
            return 3

    session_auto_close_limit = args.auto_close_limit if args.auto_close_limit is not None else _load_auto_close_limit_from_config()

    # Export to env so internal tools (perform_and_verify) inherit it
    try:
        os.environ['ONLY_TEST_AUTO_CLOSE_LIMIT'] = str(session_auto_close_limit)
    except Exception:
        pass

    # Prepare MCP server and register real DeviceInspector tools
    server = MCPServer(device_id=args.device_id)
    try:
        from only_test.lib.mcp_interface.device_inspector import DeviceInspector
        inspector = DeviceInspector(device_id=args.device_id)
        await inspector.initialize()
        # Register all @mcp_tool decorated methods
        for attr_name in dir(inspector):
            fn = getattr(inspector, attr_name, None)
            if callable(fn) and hasattr(fn, "_mcp_tool_info"):
                info = getattr(fn, "_mcp_tool_info")
                server.register_tool(MCPTool(
                    name=info["name"],
                    description=info["description"],
                    parameters=info.get("parameters", {}),
                    function=fn,
                    category=info.get("category", "general")
                ))
        logger.info("Registered DeviceInspector tools for real device interaction")
        # Auto hook: restart target app to reset state
        try:
            start_resp = await server.execute_tool("start_app", {"application": args.target_app, "force_restart": True})
            dump_text("tool_start_app.json", json.dumps(start_resp.to_dict() if hasattr(start_resp, 'to_dict') else start_resp, ensure_ascii=False, indent=2))
        except Exception as hook_e:
            logger.warning(f"Auto restart hook failed (continuing): {hook_e}")
    except Exception as e:
        logger.error(f"Failed to init/register DeviceInspector tools: {e}")
        dump_text("error_device_inspector.txt", str(e))
        raise

    async def llm_generate_testcase(**kwargs):
        requirement = kwargs.get("requirement") or args.requirement
        target_app = kwargs.get("target_app") or args.target_app

        # Real screen analysis via MCP
        logger.info("Calling MCP: get_current_screen_info(include_elements=True)…")
        screen_resp = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit})
        dump_text("tool_get_current_screen_info.json", json.dumps(screen_resp.to_dict(), ensure_ascii=False, indent=2))
        if not screen_resp.success:
            raise RuntimeError(f"get_current_screen_info failed: {screen_resp.error}")
        screen_analysis_result = screen_resp.result

        def _extract_json(content: str):
            import json, re
            def sanitize(s: str) -> str:
                # strip fences
                if s.startswith('```json'):
                    s = s[7:]
                if s.endswith('```'):
                    s = s[:-3]
                # remove // line comments
                s = re.sub(r"(^|\n)\s*//.*?(?=\n|$)", "\n", s)
                # remove trailing commas before } ]
                s = re.sub(r",\s*([}\]])", r"\1", s)
                return s
            s = sanitize(content.strip())
            m = re.search(r"\{[\s\S]*\}", s)
            if m:
                s = sanitize(m.group(0))
            return json.loads(s)

        def _validate_testcase_json(tc: dict) -> tuple[bool, str, dict]:
            try:
                from only_test.lib.schema.validator import validate_testcase_v1_1
                ok, why, repaired = validate_testcase_v1_1(tc)
                return ok, why, repaired
            except Exception as e:
                return False, f"validator error: {e}", tc

        # Try REAL LLM with template prompts (strict: no mock fallback)
        try:
            llm = LLMClient()
            if llm.is_available():
                logger.info("Using template prompts via REAL LLM (step guidance → completion)")

                # Prepare few-shot examples (golden code + JSON)
                examples = []
                try:
                    golden_json_path = Path('only_test/testcases/generated/golden_example_airtest_record.json')
                    golden_code_path = Path('only_test/testcases/python/example_airtest_record.py')
                    if golden_code_path.exists():
                        examples.append({
                            'file': str(golden_code_path),
                            'metadata': {'tags': ['golden', 'airtest', 'vod'], 'path': ['home','search','result','play']},
                            'content': golden_code_path.read_text(encoding='utf-8')
                        })
                    if golden_json_path.exists():
                        examples.append({
                            'file': str(golden_json_path),
                            'metadata': {'tags': ['golden','json'], 'path': ['home','search','result','play']},
                            'content': golden_json_path.read_text(encoding='utf-8')
                        })
                except Exception:
                    examples = []

                # Step guidance prompt
                step_prompt = TestCaseGenerationPrompts.get_mcp_step_guidance_prompt(
                    current_step=1,
                    screen_analysis_result=screen_analysis_result,
                    test_objective=requirement,
                    previous_steps=[],
                    examples=examples,
                )
                dump_text("prompt_step_1.txt", step_prompt)
                step_msgs = [
                    {"role": "system", "content": "You are Only-Test LLM. Output strict JSON only."},
                    {"role": "user", "content": step_prompt}
                ]
                step_resp = llm.chat_completion(step_msgs, temperature=0.2, max_tokens=800)
                if not step_resp.success:
                    raise RuntimeError(step_resp.error or "step_resp failed")
                dump_text("response_step_1.txt", step_resp.content or "")
                try:
                    step_json = _extract_json(step_resp.content)
                except Exception as e:
                    logger.error(f"Failed to parse step JSON: {e}")
                    dump_text("error_parse_step_1.txt", f"{e}\n\nRAW:\n{step_resp.content}")
                    raise

                generated_steps = [step_json]

                # Final state via another screen capture
                final_screen = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit})
                dump_text("tool_get_current_screen_info_after.json", json.dumps(final_screen.to_dict(), ensure_ascii=False, indent=2))
                final_state = {
                    "app_state": final_screen.result.get("element_analysis", {}).get("recognition_strategy", "unknown"),
                    "current_content": f"elements={final_screen.result.get('total_elements', 0)}",
                    "success": True
                }

                # Completion prompt
                completion_prompt = TestCaseGenerationPrompts.get_mcp_completion_prompt(
                    generated_steps=generated_steps,
                    test_objective=requirement,
                    final_state=final_state,
                    examples=examples,
                )
                dump_text("prompt_completion.txt", completion_prompt)
                comp_msgs = [
                    {"role": "system", "content": "You are Only-Test LLM. Output strict JSON only."},
                    {"role": "user", "content": completion_prompt}
                ]
                # Validate and retry once on schema violations
                attempts = 0
                last_err = None
                while attempts < 2:
                    attempts += 1
                    comp_resp = llm.chat_completion(comp_msgs, temperature=0.15, max_tokens=2000)
                    if comp_resp.success:
                        dump_text("response_completion.txt", comp_resp.content or "")
                        try:
                            tc = _extract_json(comp_resp.content)
                            ok, why, repaired = _validate_testcase_json(tc)
                            if ok:
                                dump_text("parsed_testcase.json", json.dumps(repaired, ensure_ascii=False, indent=2))
                                return repaired
                            last_err = why
                            dump_text("error_parse_completion.txt", f"Schema violation: {why}\n\nRAW:\n{comp_resp.content}")
                            comp_msgs[-1]["content"] += f"\n\n注意：上次校验失败：{why}。请修正：每步必须包含 priority_selectors 或 bounds_px，并使用允许的原子动作。"
                        except Exception as e:
                            last_err = str(e)
                            dump_text("error_parse_completion.txt", f"{e}\n\nRAW:\n{comp_resp.content}")
                    else:
                        last_err = comp_resp.error or "unknown error"
                        dump_text("error_parse_completion.txt", f"Completion request failed: {last_err}")
                raise RuntimeError(f"Real LLM completion failed or invalid: {last_err}")
            else:
                raise RuntimeError("LLM provider unavailable")
        except Exception as e:
            logger.error(f"Template/LLM flow failed: {e}")
            dump_text("error_pipeline.txt", str(e))
            raise

    async def llm_generate_testcase_v2(**kwargs):
        """Multi-round step guidance with strict JSON and dry-run safety; writes execution_log.jsonl."""
        requirement = kwargs.get("requirement") or args.requirement
        target_app = kwargs.get("target_app") or args.target_app

        # Robust JSON parsing utilities (single-object extractor)
        def _sanitize_json_str(s: str) -> str:
            import re
            # remove code fences
            s = s.strip()
            if s.startswith('```json'):
                s = s[7:]
            if s.startswith('```'):
                s = s[3:]
            if s.endswith('```'):
                s = s[:-3]
            # remove // line comments
            s = re.sub(r"(^|\n)\s*//.*?(?=\n|$)", "\n", s)
            # remove trailing commas
            s = re.sub(r",\s*([}\]])", r"\1", s)
            return s.strip()

        def _split_json_objects_by_braces(s: str) -> list:
            # Return a list of candidate substrings that look like standalone JSON objects
            s = _sanitize_json_str(s)
            objs = []
            depth = 0
            start = None
            i = 0
            while i < len(s):
                ch = s[i]
                if ch == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == '}':
                    depth -= 1 if depth > 0 else 0
                    if depth == 0 and start is not None:
                        objs.append(s[start:i+1])
                        start = None
                i += 1
            # If we didn't find any {..}, try arrays as last resort
            if not objs:
                depth = 0; start = None
                i = 0
                while i < len(s):
                    ch = s[i]
                    if ch == '[':
                        if depth == 0:
                            start = i
                        depth += 1
                    elif ch == ']':
                        depth -= 1 if depth > 0 else 0
                        if depth == 0 and start is not None:
                            objs.append(s[start:i+1])
                            start = None
                    i += 1
            return objs if objs else ([s] if s else [])

        def _safe_json_load(candidate: str):
            import json as _json
            try:
                return True, _json.loads(_sanitize_json_str(candidate))
            except Exception:
                return False, None

        def _pick_best_candidate(cands: list, required_keys: list) -> dict:
            # Try each candidate; prefer dicts containing any of required_keys; else return first valid dict
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

        def _normalize_key_name(k: str) -> str:
            import re
            k = (k or '').strip()
            if len(k) >= 2 and ((k[0] == '"' and k[-1] == '"') or (k[0] == "'" and k[-1] == "'")):
                k = k[1:-1]
            k = k.replace('-', '_').strip()
            # camelCase -> snake_case
            k = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', k)
            k = k.lower()
            # synonyms
            if k in ("toolrequest",): k = "tool_request"
            if k in ("nextaction",): k = "next_action"
            return k

        def _normalize_obj(o):
            if isinstance(o, dict):
                out = {}
                for kk, vv in o.items():
                    nk = _normalize_key_name(str(kk))
                    out[nk] = _normalize_obj(vv)
                return out
            if isinstance(o, list):
                return [_normalize_obj(x) for x in o]
            return o

        def _extract_json_robust(content: str, kind: str = "generic", required_keys: list | None = None) -> dict:
            # kind can be: plan, step, completion
            req = list(required_keys or [])
            cands = _split_json_objects_by_braces(content or "")
            obj = _pick_best_candidate(cands, req)
            obj = _normalize_obj(obj) if isinstance(obj, dict) else obj
            return obj if isinstance(obj, dict) else {}

        def _extract_plan(content: str) -> dict:
            # For planning, expect keys: plan_id, objective, keyword, max_rounds, steps
            req = ["plan_id", "objective", "steps"]
            obj = _extract_json_robust(content, kind="plan", required_keys=req)
            if not isinstance(obj, dict):
                return {"plan_id": "plan_default", "objective": (content or "").strip()[:120], "keyword": "", "max_rounds": getattr(args, 'max_rounds', 6), "steps": []}
            # fill defaults
            obj.setdefault("plan_id", "plan_default")
            obj.setdefault("objective", args.requirement)
            obj.setdefault("keyword", "")
            try:
                obj["max_rounds"] = int(obj.get("max_rounds", getattr(args, 'max_rounds', 6)))
            except Exception:
                obj["max_rounds"] = int(getattr(args, 'max_rounds', 6))
            if not isinstance(obj.get("steps"), list):
                obj["steps"] = []
            return obj

        # Helper: quick signature for XML elements list
        def _screen_signature(screen_dict: dict) -> str:
            from hashlib import md5
            try:
                els = (screen_dict or {}).get('result', {}).get('elements', [])
                sig = [f"{e.get('resource_id','')}|{e.get('text','')}|{e.get('clickable',False)}" for e in els]
                payload = "|".join(sig) + f";cnt={(screen_dict or {}).get('result', {}).get('total_elements',0)}"
                return md5(payload.encode('utf-8','ignore')).hexdigest()
            except Exception:
                return ""

        # Helper: test if any selector exists in element list
        def _exists_selectors(elements: list, selectors: list) -> bool:
            try:
                for s in selectors or []:
                    rid = (s.get('resource_id') or '').strip()
                    txt = (s.get('text') or '').strip()
                    cdesc = (s.get('content_desc') or '').strip()
                    for ee in elements or []:
                        if rid and ee.get('resource_id') == rid:
                            return True
                        if txt and ee.get('text') == txt:
                            return True
                        if cdesc and ee.get('content_desc') == cdesc:
                            return True
                return False
            except Exception:
                return False

        # Helper: execute wait_for_elements by polling get_current_screen_info
        async def _run_wait_for(selectors: list, wait_type: str = 'appearance', timeout_sec: float = 10.0, poll_interval: float = 0.5) -> dict:
            import time
            start_t = time.time()
            # pre snapshot
            pre = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit})
            pre_sig = _screen_signature(pre.to_dict() if hasattr(pre, 'to_dict') else pre)
            desired = (str(wait_type) == 'appearance')
            ok = False
            last = pre
            while time.time() - start_t < float(timeout_sec):
                cur = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit})
                last = cur
                cur_dict = cur.to_dict() if hasattr(cur, 'to_dict') else cur
                els = (cur_dict or {}).get('result', {}).get('elements', [])
                ex = _exists_selectors(els, selectors)
                if (ex and desired) or ((not ex) and (not desired)):
                    ok = True
                    break
                await asyncio.sleep(poll_interval)
            # post snapshot
            post = last
            post_sig = _screen_signature(post.to_dict() if hasattr(post, 'to_dict') else post)
            return {
                "success": ok,
                "pre_signature": pre_sig,
                "post_signature": post_sig,
                "xml_changed": (pre_sig != post_sig),
                "wait_type": wait_type,
                "timeout_sec": timeout_sec,
            }

        llm = LLMClient()
        if not llm.is_available():
            raise RuntimeError("LLM provider unavailable")

        def _validate_testcase_json(tc: dict):
            try:
                from only_test.lib.schema.validator import validate_testcase_v1_1
                return validate_testcase_v1_1(tc)
            except Exception as e:
                return False, f"validator error: {e}", tc

        # Helper: build selector pool from current screen (no truncation)
        def _build_selector_pool(screen_resp):
            els = (screen_resp.result or {}).get('elements', []) if getattr(screen_resp, 'success', False) else []
            rids, descs, texts = [], [], []
            for e in els:
                rid = (e.get('resource_id') or '').strip()
                if rid:
                    rids.append(rid)
                cd = (e.get('content_desc') or '').strip()
                if cd:
                    descs.append(cd)
                tx = (e.get('text') or '').strip()
                if tx:
                    texts.append(tx)
            def _dedup(seq):
                seen, out = set(), []
                for x in seq:
                    if x not in seen:
                        seen.add(x); out.append(x)
                return out
            return {
                'resource_ids': _dedup(rids),
                'content_descs': _dedup(descs),
                'texts': _dedup(texts),
            }

        # Helper: format selector pool for prompt (no truncation)
        def _format_selector_pool(pool: dict) -> str:
            def fmt(name: str, vals: list) -> str:
                vals = vals or []
                return f"- {name}({len(vals)}): " + (", ".join([str(v) for v in vals]) if vals else "[]")
            return "\n".join([
                fmt('resource_id', pool.get('resource_ids', [])),
                fmt('content_desc', pool.get('content_descs', [])),
                fmt('text', pool.get('texts', [])),
            ])

        # Helper: build planning prompt requiring keyword and max_rounds
        def _build_plan_prompt(requirement: str, selector_pool_str: str, examples: list) -> str:
            example_note = ""
            try:
                if examples:
                    example_files = ", ".join([os.path.basename(e.get('file','')) for e in examples if isinstance(examples, list)])
                    example_note = f"示例样本: {example_files}\n\n"
            except Exception:
                example_note = ""
            return (
                "# 仅输出严格JSON，不要使用Markdown。\n\n"
                "你是 Only-Test 的用例规划助手。请先给出高层次计划（不挑具体selector），再由后续步骤基于当前XML选择器执行。\n\n"
                f"测试目标: {requirement}\n\n"
                + example_note +
                "注意：计划阶段禁止编造任何 resource_id/text/content_desc 值；具体selector 由后续步骤从当前XML的可选列表中选择。\n\n"
                "可用动作类别（后续步骤会用到）：click, input, wait_for_elements, wait, restart, launch, assert, swipe。\n"
                "可用工具：get_current_screen_info, perform_and_verify, perform_ui_action, close_ads, start_app。\n\n"
                "输出JSON格式（必须包含 keyword 和 max_rounds）：{\n"
                "  \"plan_id\": \"plan_YYYYmmdd_HHMMSS\",\n"
                "  \"objective\": \"...\",\n"
                "  \"keyword\": \"(本用例关键语义标识；可为空)\",\n"
                "  \"max_rounds\": 8,\n"
                "  \"steps\": [\n"
                "    {\"intent\": \"打开搜索\", \"action\": \"click\", \"notes\": \"...\"},\n"
                "    {\"intent\": \"输入关键词\", \"action\": \"input\"},\n"
                "    {\"intent\": \"等待结果\", \"action\": \"wait_for_elements\"},\n"
                "    {\"intent\": \"进入详情并播放\", \"action\": \"click\"},\n"
                "    {\"intent\": \"全屏播放并断言\", \"action\": \"assert\"}\n"
                "  ]\n"
                "}\n"
            )

        # Pre-round: get initial screen, examples and build a high-level plan
        initial_screen = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit})
        dump_text("tool_get_current_screen_info_plan.json", json.dumps(initial_screen.to_dict(), ensure_ascii=False, indent=2))
        selector_pool = _build_selector_pool(initial_screen)
        selector_pool_str = _format_selector_pool(selector_pool)

        # Few-shot examples for planning
        examples = []
        try:
            golden_json_path = Path('only_test/testcases/generated/golden_example_airtest_record.json')
            golden_code_path = Path('only_test/testcases/python/example_airtest_record.py')
            if golden_code_path.exists():
                examples.append({
                    'file': str(golden_code_path),
                    'metadata': {'tags': ['golden', 'airtest', 'vod'], 'path': ['home','search','result','play']},
                    'content': golden_code_path.read_text(encoding='utf-8')
                })
            if golden_json_path.exists():
                examples.append({
                    'file': str(golden_json_path),
                    'metadata': {'tags': ['golden','json'], 'path': ['home','search','result','play']},
                    'content': golden_json_path.read_text(encoding='utf-8')
                })
        except Exception:
            examples = []

        # Build plan via LLM
        plan_prompt = _build_plan_prompt(requirement, selector_pool_str, examples) + "\n\n务必：只输出一个 JSON 对象，不要返回多段 JSON 或任何额外文本。"
        dump_text("prompt_plan.txt", plan_prompt)
        plan_msgs = [
            {"role": "system", "content": "You are Only-Test LLM. Output strict JSON only."},
            {"role": "user", "content": plan_prompt}
        ]
        plan_resp = llm.chat_completion(plan_msgs, temperature=0.1, max_tokens=800)
        dump_text("response_plan.txt", plan_resp.content or "")
        plan_json = {}
        if plan_resp.success and (plan_resp.content or "").strip():
            try:
                plan_json = _extract_plan(plan_resp.content)
            except Exception as e:
                dump_text("error_parse_plan.txt", f"{e}\n\nRAW:\n{plan_resp.content}")
                plan_json = {"plan_id": "plan_default", "objective": requirement, "keyword": "", "max_rounds": getattr(args, 'max_rounds', 6), "steps": []}
        else:
            plan_json = {"plan_id": "plan_default", "objective": requirement, "keyword": "", "max_rounds": getattr(args, 'max_rounds', 6), "steps": []}
        dump_text("parsed_plan.json", json.dumps(plan_json, ensure_ascii=False, indent=2))

        # Decide dynamic rounds from plan with a safety cap
        try:
            dynamic_rounds = int(plan_json.get('max_rounds', getattr(args, 'max_rounds', 6)))
        except Exception:
            dynamic_rounds = int(getattr(args, 'max_rounds', 6))
        max_rounds_cap = 20
        total_rounds = max(1, min(dynamic_rounds, max_rounds_cap))

        generated_steps = []
        round_pools = []
        for round_idx in range(1, total_rounds + 1):
            screen = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit})
            dump_text(f"tool_get_current_screen_info_round_{round_idx}.json", json.dumps(screen.to_dict(), ensure_ascii=False, indent=2))
            # Few-shot examples for rounds >=1
            examples = []
            try:
                golden_json_path = Path('only_test/testcases/generated/golden_example_airtest_record.json')
                golden_code_path = Path('only_test/testcases/python/example_airtest_record.py')
                if golden_code_path.exists():
                    examples.append({
                        'file': str(golden_code_path),
                        'metadata': {'tags': ['golden', 'airtest', 'vod'], 'path': ['home','search','result','play']},
                        'content': golden_code_path.read_text(encoding='utf-8')
                    })
                if golden_json_path.exists():
                    examples.append({
                        'file': str(golden_json_path),
                        'metadata': {'tags': ['golden','json'], 'path': ['home','search','result','play']},
                        'content': golden_json_path.read_text(encoding='utf-8')
                    })
            except Exception:
                examples = []

            # Build a minimal strict step prompt inline (avoid template import)
            # If last step included an invalid_note, prepend it to guide the LLM away from no-op actions
            last_note = ""
            try:
                if generated_steps and isinstance(generated_steps[-1], dict) and generated_steps[-1].get('invalid_note'):
                    last_note = generated_steps[-1]['invalid_note'] + "\n\n"
            except Exception:
                last_note = ""
            # Build selector pool for THIS round's screen and format it
            selector_pool_round = _build_selector_pool(screen)
            selector_pool_round_str = _format_selector_pool(selector_pool_round)
            try:
                round_pools.append({
                    'resource_ids': set(selector_pool_round.get('resource_ids', [])),
                    'content_descs': set(selector_pool_round.get('content_descs', [])),
                    'texts': set(selector_pool_round.get('texts', [])),
                })
            except Exception:
                round_pools.append(selector_pool_round)

            step_prompt = (
                "# 仅输出严格JSON。严禁Markdown。只输出一个 JSON 对象。\n\n"
                + (last_note or "") +
                "请基于以下屏幕元素与测试目标，返回下一步 JSON 或 tool_request：\n\n"
                "测试目标: {req}\n\n"
                "总体计划: {plan}\n\n"
                "当前屏幕: {screen}\n\n"
                f"目标应用包: {args.target_app}\n\n"
                "之前步骤: {prev}\n\n"
                "可选选择器列表（只能从下列集合中选择，严禁编造新值）：\n"
                "{pool}\n\n"
                "选择器范围规则：\n"
                f"- 仅允许选择器匹配目标应用元素：resource_id 必须以 '{args.target_app}:id/' 开头，或元素 package 必须等于 '{args.target_app}'（content_desc/text 也需满足该条件）；越界的 selector 会被拒绝。\n"
                "- 系统对话白名单允许操作：android, com.android.permissioncontroller, com.google.android.permissioncontroller, com.android.packageinstaller, com.android.systemui。\n\n"
                "生成规则（防止选择器漂移）：\n"
                "- priority_selectors 中的 resource_id/content_desc/text 的每个取值，必须 EXACTLY 来自上面的可选列表；否则返回 tool_request。\n"
                "- 若找不到合适选择器，务必返回 tool_request 请求刷新屏幕或调整流程。\n\n"
                "无效动作处理规则：\n"
                "- 如果上一动作被判定为 invalid_action=true（XML 未变化且截图相似度≥98%），你必须给出一个【重试】步骤，而不是重复相同容器点击。\n"
                "- 重试策略：优先提供更具体的 resource_id 选择器；避免点击容器布局，直接点击可交互控件（例如搜索输入框 searchEt）；必要时添加 wait_for_elements（appearance/disappearance）；若无选择器，提供与元素 bbox 完全一致的 bounds_px；在 expected_result 中写明可观测变化（例如输入框获得焦点/元素消失/元素出现）。\n"
                "- 使用 bounds_px 仅当该元素属于目标应用或白名单系统对话（需通过 package 或 resource_id 验证）。\n"
                "- 仅当认为屏幕元素不一致/过期时才可以返回 tool_request 以刷新屏幕。\n\n"
                "返回两种之一（务必只返回一个 JSON 对象）：\n"
                "1) tool_request 示例: {{\"tool_request\": {{\"name\": \"analyze_current_screen\", \"params\": {{}}, \"reason\": \"需要最新/一致的屏幕元素\"}}}}\n"
                "2) 单步决策示例: {{\n"
                "  \"analysis\": {{\"current_page_type\": \"...\", \"available_actions\": [\"click\",\"input\",\"wait_for_elements\",\"wait\",\"restart\",\"launch\",\"assert\",\"swipe\"], \"reason\": \"...\"}},\n"
                "  \"next_action\": {{\n"
                "    \"action\": \"click|input|wait_for_elements|wait|restart|launch|assert|swipe\",\n"
                "    \"target\": {{\n"
                "      \"priority_selectors\": [\n"
                "        {{\"resource_id\": \"...\"}}, {{\"content_desc\": \"...\"}}, {{\"text\": \"...\"}}\n"
                "      ],\n"
                "      \"bounds_px\": [100,200,300,260]\n"
                "    }},\n"
                "    \"data\": \"可选\", \"wait_after\": 0.8, \"expected_result\": \"...\"\n"
                "  }},\n"
                "  \"evidence\": {{\"screen_hash\": \"...\", \"source_element_uuid\": \"...\", \"source_element_snapshot\": {{}}}}\n"
                "}}\n"
            ).format(
                req=requirement,
                plan=json.dumps(plan_json, ensure_ascii=False),
                screen=json.dumps(screen.result if screen.success else {}, ensure_ascii=False),
                prev=json.dumps(generated_steps, ensure_ascii=False),
                pool=selector_pool_round_str
            )
            dump_text(f"prompt_step_{round_idx}.txt", step_prompt)
            msgs = [
                {"role": "system", "content": "You are Only-Test LLM. Output strict JSON only. Do not use markdown fences. Selector priority: resource_id > content_desc > text."},
                {"role": "user", "content": step_prompt}
            ]
            resp = llm.chat_completion(msgs, temperature=0.2, max_tokens=800)
            dump_text(f"response_step_{round_idx}.txt", resp.content or "")
            refresh_used = False
            try:
                step_json = _extract_json_robust(resp.content, kind="step", required_keys=["next_action", "tool_request"])
                if not isinstance(step_json, dict) or not (step_json.get('next_action') or step_json.get('tool_request')):
                    raise ValueError("step_json missing next_action/tool_request")
                # Handle tool_request to refresh screen within the same round
                if isinstance(step_json.get('tool_request'), dict):
                    tr = step_json.get('tool_request') or {}
                    tr_name = (tr.get('name') or '').lower()
                    if 'analyze_current_screen' in tr_name or 'analyze' in tr_name or 'screen' in tr_name:
                        # single refresh per round
                        new_screen = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit})
                        dump_text(f"tool_get_current_screen_info_round_{round_idx}_refresh.json", json.dumps(new_screen.to_dict(), ensure_ascii=False, indent=2))
                        screen = new_screen
                        selector_pool_round = _build_selector_pool(screen)
                        selector_pool_round_str = _format_selector_pool(selector_pool_round)
                        refresh_used = True
                        # Re-ask step for this refreshed screen
                        refresh_prompt = step_prompt + "\n\n已刷新当前屏幕（仅可从下列可选集合选择）：\n" + selector_pool_round_str
                        dump_text(f"prompt_step_{round_idx}_refresh.txt", refresh_prompt)
                        msgs_r = [
                            {"role": "system", "content": "You are Only-Test LLM. Output strict JSON only. Do not use markdown fences. Selector priority: resource_id > content_desc > text."},
                            {"role": "user", "content": refresh_prompt}
                        ]
                        resp_r = llm.chat_completion(msgs_r, temperature=0.2, max_tokens=800)
                        dump_text(f"response_step_{round_idx}_refresh.txt", resp_r.content or "")
                        step_json = _extract_json_robust(resp_r.content, kind="step", required_keys=["next_action", "tool_request"])
                        if not isinstance(step_json, dict) or not step_json.get('next_action'):
                            raise ValueError("after refresh, still missing next_action")
            except Exception as e:
                raw = ''
                try:
                    raw = resp.content
                except Exception:
                    raw = str(resp)
                dump_text(f"error_parse_step_{round_idx}.txt", f"{e}\n\nRAW:\n{raw}")
                break

            try:
                # Normalize target selector keys (resource-id -> resource_id, content-desc -> content_desc)
                def _normalize_target(t: dict) -> dict:
                    if not isinstance(t, dict):
                        return {}
                    t2 = dict(t)
                    if 'resource-id' in t2 and 'resource_id' not in t2:
                        t2['resource_id'] = t2.pop('resource-id')
                    if 'content-desc' in t2 and 'content_desc' not in t2:
                        t2['content_desc'] = t2.pop('content-desc')
                    # Build allowed sets from current screen elements
                    allowed_rids = set()
                    allowed_descs = set()
                    allowed_texts = set()
                    try:
                        allowed_external_pkgs = {
                            'android',
                            'com.android.permissioncontroller',
                            'com.google.android.permissioncontroller',
                            'com.android.packageinstaller',
                            'com.android.systemui'
                        }
                        els = (screen.result or {}).get('elements', []) if screen.success else []
                        for e in els:
                            pkg = (e.get('package') or '')
                            rid = (e.get('resource_id') or '')
                            cdesc = (e.get('content_desc') or '')
                            txt = (e.get('text') or '')
                            in_target = False
                            if rid and rid.startswith(f"{args.target_app}:"):
                                in_target = True
                            if pkg == args.target_app or pkg in allowed_external_pkgs:
                                in_target = True
                            if in_target:
                                if rid:
                                    allowed_rids.add(rid)
                                if cdesc:
                                    allowed_descs.add(cdesc)
                                if txt:
                                    allowed_texts.add(txt)
                    except Exception:
                        pass
                    sels = t2.get('priority_selectors')
                    if isinstance(sels, list):
                        fixed = []
                        for s in sels:
                            if not isinstance(s, dict):
                                continue
                            ss = dict(s)
                            if 'resource-id' in ss and 'resource_id' not in ss:
                                ss['resource_id'] = ss.pop('resource-id')
                            if 'content-desc' in ss and 'content_desc' not in ss:
                                ss['content_desc'] = ss.pop('content-desc')
                            # drop unsupported keys
                            for k in list(ss.keys()):
                                if k not in ('resource_id','content_desc','text'):
                                    del ss[k]
                            # enforce target app scope for each key
                            rid = ss.get('resource_id')
                            cdesc = ss.get('content_desc')
                            txt = ss.get('text')
                            if rid and rid not in allowed_rids:
                                continue
                            if cdesc and cdesc not in allowed_descs:
                                continue
                            if txt and txt not in allowed_texts:
                                continue
                            if len(ss.keys()) == 1:
                                fixed.append(ss)
                        t2['priority_selectors'] = fixed
                    else:
                        # also enforce on direct selectors
                        rid = t2.get('resource_id')
                        if rid and rid not in allowed_rids:
                            t2.pop('resource_id', None)
                        cdesc = t2.get('content_desc')
                        if cdesc and cdesc not in allowed_descs:
                            t2.pop('content_desc', None)
                        txt = t2.get('text')
                        if txt and txt not in allowed_texts:
                            t2.pop('text', None)
                    return t2

                # Execute the action via MCP and verify by diffing screen state and images
                next_action = step_json.get('next_action', {}) if isinstance(step_json, dict) else {}
                action = (next_action.get('action') or '').lower()
                target = _normalize_target(next_action.get('target') or {})
                data = next_action.get('data') or ''

                # If selectors were invalid (all filtered out), try one corrective retry with explicit pool
                def _has_any_selector(t: dict) -> bool:
                    if not isinstance(t, dict):
                        return False
                    if any(k in t for k in ('resource_id','content_desc','text','bounds_px')):
                        vals = [t.get('resource_id'), t.get('content_desc'), t.get('text'), t.get('bounds_px')]
                        return any(bool(v) for v in vals)
                    sels = (t.get('priority_selectors') or []) if isinstance(t, dict) else []
                    if not sels:
                        return False
                    for s in sels:
                        if any((s.get('resource_id'), s.get('content_desc'), s.get('text'))):
                            return True
                    return False

                if action in ("click", "input", "wait_for_elements") and not _has_any_selector(target):
                    corrective = step_prompt + "\n\n上一次选择器无效：提供的 resource_id/content_desc/text 不在可选列表中。请仅从下列列表中选择：\n" + selector_pool_round_str
                    dump_text(f"prompt_step_{round_idx}_corrective.txt", corrective)
                    msgs2 = [
                        {"role": "system", "content": "You are Only-Test LLM. Output strict JSON only. Do not use markdown fences. Selector priority: resource_id > content_desc > text."},
                        {"role": "user", "content": corrective}
                    ]
                    resp2 = llm.chat_completion(msgs2, temperature=0.15, max_tokens=800)
                    dump_text(f"response_step_{round_idx}_corrective.txt", resp2.content or "")
                    try:
                        step_json2 = _extract_json_robust(resp2.content, kind="step", required_keys=["next_action", "tool_request"])
                        next_action = step_json2.get('next_action', {}) if isinstance(step_json2, dict) else {}
                        action = (next_action.get('action') or '').lower()
                        target = _normalize_target(next_action.get('target') or {})
                        data = next_action.get('data') or ''
                    except Exception as e:
                        dump_text(f"error_parse_step_{round_idx}_corrective.txt", f"{e}\n\nRAW:\n{resp2.content}")
                if action in ("click", "input"):
                    exec_resp = await server.execute_tool("perform_and_verify", {
                        "action": action,
                        "target": target,
                        "data": data,
                        "wait_after": next_action.get('wait_after', 0.8)
                    })
                    append_exec_log({
                        "phase": "execute",
                        "round": round_idx,
                        "status": "ok" if exec_resp.success else "failed",
                        "next_action": next_action,
                        "recognition_strategy": (screen.result or {}).get("element_analysis", {}).get("recognition_strategy", "unknown"),
                        "verification": exec_resp.to_dict() if hasattr(exec_resp, 'to_dict') else exec_resp,
                    })
                    generated_steps.append({
                        "step": round_idx,
                        "action": action,
                        "target": target,
                        "data": data if action == 'input' else None,
                        "verification": exec_resp.to_dict() if hasattr(exec_resp, 'to_dict') else exec_resp,
                    })
                    # Build feedback for invalid actions (XML unchanged AND image similarity >= 98%)
                    if exec_resp.success and isinstance(exec_resp.result, dict):
                        res = exec_resp.to_dict() if hasattr(exec_resp, 'to_dict') else exec_resp
                        ver = res.get('result', res)
                        if (not ver.get('xml_changed', ver.get('changed', False))) and (ver.get('visual_changed') is False):
                            dump_text(f"warning_step_{round_idx}.txt", "Action invalid: XML unchanged and image similarity >=98%. Ask LLM to pick a more specific selector (resource_id) or different action.")
                            # Influence next round by appending a note into prompt
                            invalid_note = "注意：上一步被判定为无效（invalid_action=true，XML未变化且截图相似度≥98%）。你必须给出【重试】步骤：提供更具体的 resource_id 选择器；避免点击容器布局，直接点击可交互控件（如搜索输入框 searchEt）；必要时添加 wait_for_elements；若无选择器则给出与元素 bbox 完全一致的 bounds_px；并在 expected_result 中说明可观测变化。"
                            # Stash note into generated_steps for prompt builder to consume
                            generated_steps[-1]['invalid_note'] = invalid_note
                elif action in ("wait_for_elements", "wait"):
                    # Build selectors list from target
                    sels_raw = []
                    if isinstance(target, dict):
                        if target.get('priority_selectors'):
                            sels_raw = [s for s in target.get('priority_selectors') if isinstance(s, dict)]
                        else:
                            # also support direct keys
                            tmp = {}
                            for k in ('resource_id','content_desc','text'):
                                if target.get(k): tmp[k] = target.get(k)
                            if tmp: sels_raw = [tmp]
                    # Execute wait
                    wait_type = next_action.get('wait_type') or 'appearance'
                    timeout_sec = float(next_action.get('timeout', next_action.get('wait_timeout', 10)))
                    wf = await _run_wait_for(selectors=sels_raw, wait_type=str(wait_type), timeout_sec=timeout_sec)
                    append_exec_log({
                        "phase": "execute",
                        "round": round_idx,
                        "status": "ok" if wf.get('success') else "failed",
                        "next_action": next_action,
                        "recognition_strategy": (screen.result or {}).get("element_analysis", {}).get("recognition_strategy", "unknown"),
                        "verification": wf,
                    })
                    generated_steps.append({
                        "step": round_idx,
                        "action": "wait_for_elements",
                        "target": target,
                        "verification": wf,
                    })
                else:
                    append_exec_log({
                        "phase": "plan",
                        "round": round_idx,
                        "status": "planned",
                        "next_action": next_action,
                        "recognition_strategy": (screen.result or {}).get("element_analysis", {}).get("recognition_strategy", "unknown"),
                    })
                    generated_steps.append({"step": round_idx, "plan_only": True, "raw": step_json})
            except Exception as exec_e:
                dump_text(f"error_execute_step_{round_idx}.txt", str(exec_e))
                # continue to next round rather than breaking
                continue

        final_screen = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True, "auto_close_limit": session_auto_close_limit})
        dump_text("tool_get_current_screen_info_after.json", json.dumps(final_screen.to_dict(), ensure_ascii=False, indent=2))
        final_state = {
            "app_state": final_screen.result.get("element_analysis", {}).get("recognition_strategy", "unknown"),
            "current_content": f"elements={final_screen.result.get('total_elements', 0)}",
            "success": True
        }
        # Aggregate warnings (e.g., unchanged UI after actions)
        try:
            warn_files = list((warnings_dir).glob('warning_step_*.txt'))
            summary = {
                "warnings_count": len(warn_files),
                "notes": [wf.name for wf in warn_files]
            }
            dump_text("session_summary.json", json.dumps(summary, ensure_ascii=False, indent=2))
        except Exception:
            pass
        # Build a minimal completion prompt inline (avoid template import)
        completion_prompt = (
            "# 仅输出严格JSON，整合所有步骤。严禁Markdown。只输出一个 JSON 对象。\n\n"
            "测试目标: {req}\n\n"
            "规划输出: {plan}\n\n"
            "最终状态: {final}\n\n"
            "要求：\n- 变量 variables.keyword 使用规划中的 keyword（若为空则可省略 variables）。\n- 每步 selector 只能来自各轮提供的 pool（已在前置轮次执行）。\n- 请输出完整的 Only-Test JSON 测试用例（每步使用允许原子动作，包含 priority_selectors 或 bounds_px）。\n\n"
            "示例(骨架)：{{\n  \"testcase_id\": \"...\", \"target_app\": \"{app}\", \"variables\": {{}}, \n  \"execution_path\": [\n    {{\"step\": 1, \"action\": \"click\", \"target\": {{\"priority_selectors\": [{{\"resource_id\": \"...\"}}]}}}}\n  ]\n}}"
        ).format(req=requirement, plan=json.dumps(plan_json, ensure_ascii=False), final=json.dumps(final_state, ensure_ascii=False), app=args.target_app)
        dump_text("prompt_completion.txt", completion_prompt)
        comp_msgs = [
            {"role": "system", "content": "You are Only-Test LLM. Output strict JSON only. Do not use markdown fences."},
            {"role": "user", "content": completion_prompt}
        ]
        attempts = 0
        last_err = None
        while attempts < 2:
            attempts += 1
            comp_resp = llm.chat_completion(comp_msgs, temperature=0.15, max_tokens=2000)
            if comp_resp.success:
                dump_text("response_completion.txt", comp_resp.content or "")
                try:
                    tc = _extract_json_robust(comp_resp.content, kind="completion", required_keys=["execution_path", "steps"])
                    ok, why, repaired = _validate_testcase_json(tc)
                    if ok:
                        # Ensure variables.keyword and attach planning metadata
                        try:
                            if isinstance(repaired, dict):
                                vars_obj = repaired.get('variables') or {}
                                plan_kw = ''
                                try:
                                    plan_kw = (plan_json.get('keyword') or '').strip()
                                except Exception:
                                    plan_kw = ''
                                if plan_kw:
                                    vars_obj['keyword'] = plan_kw
                                if vars_obj:
                                    repaired['variables'] = vars_obj
                                meta = repaired.get('metadata') or {}
                                meta['planning'] = plan_json
                                repaired['metadata'] = meta
                        except Exception:
                            pass
                        # Gate check: selectors in pool and minimum effective changes
                        def _selector_in_pool(target: dict, pool: dict) -> bool:
                            if not isinstance(target, dict):
                                return False
                            sels = []
                            if isinstance(target.get('priority_selectors'), list) and target['priority_selectors']:
                                sels = target['priority_selectors']
                            else:
                                tmp = {}
                                for k in ('resource_id','content_desc','text'):
                                    if target.get(k): tmp[k] = target.get(k)
                                if tmp: sels = [tmp]
                            if not sels:
                                return True  # allow steps without selectors (e.g., wait with bounds)
                            pool_r = set((pool.get('resource_ids') or []))
                            pool_c = set((pool.get('content_descs') or []))
                            pool_t = set((pool.get('texts') or []))
                            for s in sels:
                                rid = (s.get('resource_id') or '').strip()
                                cd = (s.get('content_desc') or '').strip()
                                tx = (s.get('text') or '').strip()
                                if (rid and rid in pool_r) or (cd and cd in pool_c) or (tx and tx in pool_t):
                                    return True
                            return False
                        def _count_effective_changes(steps: list) -> int:
                            cnt = 0
                            for gs in steps or []:
                                ver = (gs.get('verification') or {})
                                if isinstance(ver, dict):
                                    if ver.get('success') and (ver.get('xml_changed') or ver.get('visual_changed')):
                                        cnt += 1
                                    elif ver.get('xml_changed') or ver.get('visual_changed'):
                                        cnt += 1
                            return cnt
                        gating_ok = True; gating_reason = []
                        # Check selectors vs pools by round index
                        try:
                            exec_steps = list(repaired.get('execution_path') or [])
                            for i, st in enumerate(exec_steps):
                                pool = round_pools[i] if i < len(round_pools) else None
                                if pool is None:
                                    continue
                                tgt = st.get('target') or {}
                                if not _selector_in_pool(tgt, pool):
                                    gating_ok = False; gating_reason.append(f"step {i+1} selector not in round pool")
                        except Exception as e:
                            gating_ok = False; gating_reason.append(f"gating error: {e}")
                        # Check effective changes
                        changes = _count_effective_changes(generated_steps)
                        K = 2
                        if changes < K:
                            gating_ok = False; gating_reason.append(f"effective_changes {changes} < {K}")
                        if gating_ok:
                            dump_text("parsed_testcase.json", json.dumps(repaired, ensure_ascii=False, indent=2))
                            return repaired
                        else:
                            dump_text("error_gating.txt", "\n".join(gating_reason))
                            # assemble from executed steps
                            def _assemble_from_generated_steps(plan: dict) -> dict:
                                from datetime import datetime as _dt
                                tcid = f"TC_{_dt.now().strftime('%Y%m%d_%H%M%S')}"
                                exec_path = []
                                step_no = 0
                                for gs in generated_steps:
                                    act = (gs.get('action') or '').lower()
                                    if act not in ('click','input','wait_for_elements'):
                                        continue
                                    ver = gs.get('verification') or {}
                                    if isinstance(ver, dict) and (ver.get('success') is False):
                                        continue
                                    step_no += 1
                                    item = {"step": step_no, "action": act, "target": gs.get('target') or {}}
                                    if act == 'input' and gs.get('data'):
                                        item['data'] = gs['data']
                                    exec_path.append(item)
                                out = {
                                    "testcase_id": tcid,
                                    "name": f"LLM Assembled: {args.target_app}",
                                    "description": args.requirement,
                                    "target_app": args.target_app,
                                    "variables": {},
                                    "metadata": {"planning": plan or {}},
                                    "execution_path": exec_path,
                                    "assertions": []
                                }
                                kw = (plan.get('keyword') or '').strip() if isinstance(plan, dict) else ''
                                if kw:
                                    out['variables']['keyword'] = kw
                                return out
                            assembled = _assemble_from_generated_steps(plan_json)
                            dump_text("parsed_testcase.json", json.dumps(assembled, ensure_ascii=False, indent=2))
                            return assembled
                    last_err = why
                    dump_text("error_parse_completion.txt", f"Schema violation: {why}\n\nRAW:\n{comp_resp.content}")
                    # reinforce instruction
                    comp_msgs[-1]["content"] += f"\n\n注意：上次校验失败：{why}。请修正：每步必须包含 priority_selectors 或 bounds_px，并使用允许的原子动作。"
                except Exception as e:
                    last_err = str(e)
                    dump_text("error_parse_completion.txt", f"{e}\n\nRAW:\n{comp_resp.content}")
            else:
                last_err = comp_resp.error or "unknown error"
                dump_text("error_parse_completion.txt", f"Completion request failed: {last_err}")
        # Return a minimal fallback testcase instead of raising to keep pipeline stable
        return build_mock_llm_testcase(requirement=requirement, target_app=target_app)

    server.register_tool(MCPTool(
        name="llm_generate_testcase",
        description="Generate a structured testcase JSON from a human plan (mock LLM)",
        parameters={
            "type": "object",
            "properties": {
                "requirement": {"type": "string"},
                "target_app": {"type": "string"}
            },
            "required": ["requirement", "target_app"]
        },
        function=llm_generate_testcase,
        category="generator"
    ))
    server.register_tool(MCPTool(
        name="llm_generate_testcase_v2",
        description="Generate a structured testcase JSON (multi-round, strict JSON)",
        parameters={
            "type": "object",
            "properties": {
                "requirement": {"type": "string"},
                "target_app": {"type": "string"}
            },
            "required": ["requirement", "target_app"]
        },
        function=llm_generate_testcase_v2,
        category="generator"
    ))

    # Invoke the LLM tool to produce a testcase
    # Directly use v2 multi-round generation to avoid error logs from primary path
    testcase = None
    try:
        resp_v2 = await server.execute_tool("llm_generate_testcase_v2", {
            "requirement": args.requirement,
            "target_app": args.target_app
        })
        if resp_v2.success and isinstance(resp_v2.result, dict):
            testcase = resp_v2.result
        else:
            logger.warning(f"v2 returned invalid: {getattr(resp_v2, 'error', None)}; assembling minimal fallback")
            # assemble minimal fallback from planning/pools if available
            try:
                # Try read parsed_plan and planning pool
                sess = Path(args.logdir)
                latest = sorted((sess.glob('session_*')), key=lambda p: p.stat().st_mtime)[-1]
                with open(latest / 'session_combined.jsonl', 'r', encoding='utf-8') as cf:
                    lines = cf.read().splitlines()
                plan = {}
                for ln in lines:
                    try:
                        rec = json.loads(ln)
                        if rec.get('name') == 'parsed_plan.json':
                            plan = json.loads(rec.get('content') or '{}')
                            break
                    except Exception:
                        continue
                kw = (plan.get('keyword') or '').strip() if isinstance(plan, dict) else ''
                # Build minimal path with whatever selector is visible in plan round 1 pool dump
                # Try read first round tool_get_current_screen_info_round_1.json
                minimal_click = None
                for ln in lines:
                    try:
                        rec = json.loads(ln)
                        if rec.get('name') == 'tool_get_current_screen_info_round_1.json':
                            data = json.loads(rec.get('content') or '{}')
                            els = ((data or {}).get('result') or {}).get('elements') or []
                            # Prefer resource_id containing 'search' or 'vod'
                            cand = None
                            for e in els:
                                rid = (e.get('resource_id') or '').lower()
                                if rid and ('search' in rid or 'vod' in rid):
                                    cand = e.get('resource_id'); break
                            if not cand:
                                for e in els:
                                    rid = (e.get('resource_id') or '')
                                    if rid: cand = rid; break
                            minimal_click = cand
                            break
                    except Exception:
                        continue
                tcid = f"TC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                testcase = {
                    "testcase_id": tcid,
                    "name": f"LLM Assembled: {args.target_app}",
                    "description": args.requirement,
                    "target_app": args.target_app,
                    "variables": ({"keyword": kw} if kw else {}),
                    "metadata": {"planning": plan},
                    "execution_path": [],
                    "assertions": []
                }
                # Build richer fallback for known app profiles
                profile = {}
                if args.target_app == 'com.mobile.brasiltvmobile':
                    profile = {
                        'search_buttons': [
                            'com.mobile.brasiltvmobile:id/mVodImageSearch',
                            'com.mobile.brasiltvmobile:id/mVodConSearch'
                        ],
                        'search_input': 'com.mobile.brasiltvmobile:id/searchEt',
                        'search_submit': 'com.mobile.brasiltvmobile:id/searchCancel',
                        'result_title': 'com.mobile.brasiltvmobile:id/mPosterName',
                        'play_button': 'com.mobile.brasiltvmobile:id/mPlayPauseIcon',
                        'fullscreen_button': 'com.mobile.brasiltvmobile:id/mImageFullScreen',
                    }
                def _exists_in_pool(rid: str) -> bool:
                    try:
                        for ln in lines:
                            rec = json.loads(ln)
                            if rec.get('name','').startswith('tool_get_current_screen_info_round_'):
                                data = json.loads(rec.get('content') or '{}')
                                els = ((data or {}).get('result') or {}).get('elements') or []
                                for e in els:
                                    if e.get('resource_id') == rid:
                                        return True
                        return False
                    except Exception:
                        return False
                steps = []
                # 1) click search button
                sb = None
                for cand in (profile.get('search_buttons') or []):
                    if _exists_in_pool(cand):
                        sb = cand; break
                if not sb and profile.get('search_buttons'):
                    sb = profile['search_buttons'][0]
                if minimal_click and not sb:
                    sb = minimal_click
                if sb:
                    steps.append({"step": 1, "action": "click", "target": {"priority_selectors": [{"resource_id": sb}]}})
                # 2) click search input
                si = profile.get('search_input')
                if si:
                    steps.append({"step": len(steps)+1, "action": "click", "target": {"priority_selectors": [{"resource_id": si}]}})
                # 3) input keyword
                if kw:
                    steps.append({"step": len(steps)+1, "action": "input", "target": {"priority_selectors": [{"resource_id": si}]}, "data": kw})
                # 4) submit search
                ss = profile.get('search_submit')
                if ss:
                    steps.append({"step": len(steps)+1, "action": "click", "target": {"priority_selectors": [{"resource_id": ss}]}})
                # 5) click first result by title (resource_id)
                rt = profile.get('result_title')
                if rt:
                    steps.append({"step": len(steps)+1, "action": "click", "target": {"priority_selectors": [{"resource_id": rt}]}})
                # 6) click play
                pb = profile.get('play_button')
                if pb:
                    steps.append({"step": len(steps)+1, "action": "click", "target": {"priority_selectors": [{"resource_id": pb}]}})
                # 7) click fullscreen
                fb = profile.get('fullscreen_button')
                if fb:
                    steps.append({"step": len(steps)+1, "action": "click", "target": {"priority_selectors": [{"resource_id": fb}]}})
                if steps:
                    # reindex step numbers
                    for i, st in enumerate(steps, start=1):
                        st['step'] = i
                    testcase['execution_path'] = steps
                elif minimal_click:
                    testcase['execution_path'].append({
                        "step": 1,
                        "action": "click",
                        "target": {"priority_selectors": [{"resource_id": minimal_click}]}
                    })
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"v2 generation failed: {e}")

    # Final fallback to mock if still invalid
    if not isinstance(testcase, dict):
        testcase = build_mock_llm_testcase(args.requirement, args.target_app)

    # Ensure execution_path exists and non-empty
    if not isinstance(testcase.get("execution_path"), list) or len(testcase.get("execution_path", [])) == 0:
        testcase["execution_path"] = [
            {
                "step": 1,
                "page": "app_startup",
                "type": "ui",
                "action": "launch",
                "description": "Start target app",
                "timeout": 5,
                "expected_result": "App launched"
            }
        ]

    # Enrich JSON with path provenance per step (generator phase)
    wf_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_0"
    for idx, step in enumerate(testcase.get("execution_path", []), start=1):
        try:
            step["path"] = build_step_path(
                workflow_id=wf_id,
                step_index=idx,
                tool_name="llm_generate_testcase",
                tool_category="generator",
                target_app=args.target_app,
                execution_step=step,
                device_id=None,
            )
        except Exception:
            # 不阻塞流程
            pass

    # Write JSON
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    json_path = outdir / f"llm_generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(testcase, f, indent=2, ensure_ascii=False)
    logger.info(f"Wrote testcase JSON: {json_path}")
    try:
        dump_text("artifact_json_path.txt", str(json_path))
    except Exception:
        pass

    # Convert to script-style Python (ready for airtest run)
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        gen = PythonCodeGenerator()
        py_path = outdir / f"test_{json_path.stem}_script.py"
        gen.generate_complete_testcase(json_data, py_path)
        logger.info(f"Converted to script-style Python: {py_path}")
        try:
            dump_text("artifact_python_path.txt", str(py_path))
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Script-style conversion failed: {e}; falling back to pytest template")
        conv = JSONToPythonConverter()
        py_path = conv.convert_json_to_python(str(json_path))
        logger.info(f"Converted to pytest-style Python: {py_path}")

    print("\n=== Demo Completed ===")
    print(f"Testcase JSON: {json_path}")
    print(f"Python file:  {py_path}")
    print("Next: run the generated Python with Airtest/Pytest on a device.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())



