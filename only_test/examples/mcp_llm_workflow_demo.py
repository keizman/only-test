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
# from only_test.templates.prompts.generate_cases import TestCaseGenerationPrompts  # disabled due to template syntax issues
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
    except Exception as e:
        logger.error(f"Failed to init/register DeviceInspector tools: {e}")
        dump_text("error_device_inspector.txt", str(e))
        raise

    async def llm_generate_testcase(**kwargs):
        requirement = kwargs.get("requirement") or args.requirement
        target_app = kwargs.get("target_app") or args.target_app

        # Real screen analysis via MCP
        logger.info("Calling MCP: get_current_screen_info(include_elements=True)…")
        screen_resp = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True})
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
                final_screen = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True})
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
        _ = kwargs.get("target_app") or args.target_app

        def _extract_json(content: str):
            import re, json as _json
            def sanitize(s: str) -> str:
                # remove // comments and trailing commas
                s = re.sub(r"(^|\n)\s*//.*?(?=\n|$)", "\n", s)
                s = re.sub(r",\s*([}\]])", r"\1", s)
                return s
            m = re.search(r"\{[\s\S]*\}", content or "")
            if not m:
                return {}
            s = sanitize(m.group(0))
            return _json.loads(s)

        llm = LLMClient()
        if not llm.is_available():
            raise RuntimeError("LLM provider unavailable")

        def _validate_testcase_json(tc: dict):
            try:
                from only_test.lib.schema.validator import validate_testcase_v1_1
                return validate_testcase_v1_1(tc)
            except Exception as e:
                return False, f"validator error: {e}", tc

        generated_steps = []
        for round_idx in range(1, max(1, getattr(args, 'max_rounds', 3)) + 1):
            screen = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True})
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
            step_prompt = (
                "# 仅输出严格JSON。严禁Markdown。\n\n"
                "请基于以下屏幕元素与测试目标，返回下一步 JSON 或 tool_request：\n\n"
                "测试目标: {req}\n\n"
                "当前屏幕: {screen}\n\n"
                "之前步骤: {prev}\n\n"
                "返回两种之一：\n"
                "1) tool_request: {{\"tool_request\": {{\"name\": \"analyze_current_screen\", \"params\": {{}}, \"reason\": \"需要最新/一致的屏幕元素\"}}}}\n"
                "2) 单步决策: {{\n"
                "  \"analysis\": {{\"current_page_type\": \"...\", \"available_actions\": [\"click\",\"input\",\"wait_for_elements\",\"wait\",\"restart\",\"launch\",\"assert\",\"swipe\"], \"reason\": \"...\"}},\n"
                "  \"next_action\": {{\n"
                "    \"action\": \"click|input|wait_for_elements|wait|restart|launch|assert|swipe\",\n"
                "    \"target\": {{\n"
                "      \"priority_selectors\": [{{\"resource_id\": \"...\"}}, {{\"content_desc\": \"...\"}}, {{\"text\": \"...\"}}],\n"
                "      \"bounds_px\": [100,200,300,260]\n"
                "    }},\n"
                "    \"data\": \"可选\", \"wait_after\": 0.8, \"expected_result\": \"...\"\n"
                "  }},\n"
                "  \"evidence\": {{\"screen_hash\": \"...\", \"source_element_uuid\": \"...\", \"source_element_snapshot\": {{}}}}\n"
                "}}\n"
            ).format(
                req=requirement,
                screen=json.dumps(screen.result if screen.success else {}, ensure_ascii=False)[:1000],
                prev=json.dumps(generated_steps, ensure_ascii=False)[:800]
            )
            dump_text(f"prompt_step_{round_idx}.txt", step_prompt)
            msgs = [
                {"role": "system", "content": "You are Only-Test LLM. Output strict JSON only. Do not use markdown fences. Selector priority: resource_id > content_desc > text."},
                {"role": "user", "content": step_prompt}
            ]
            resp = llm.chat_completion(msgs, temperature=0.2, max_tokens=800)
            dump_text(f"response_step_{round_idx}.txt", resp.content or "")
            try:
                step_json = _extract_json(resp.content)
            except Exception as e:
                dump_text(f"error_parse_step_{round_idx}.txt", f"{e}\n\nRAW:\n{resp.content}")
                break

            # Execute the action via MCP and verify by diffing screen state
            next_action = step_json.get('next_action', {}) if isinstance(step_json, dict) else {}
            action = (next_action.get('action') or '').lower()
            target = next_action.get('target') or {}
            data = next_action.get('data') or ''
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
                    "verification": exec_resp.to_dict() if hasattr(exec_resp, 'to_dict') else exec_resp,
                })
                # Warn if UI signature unchanged
                if exec_resp.success and isinstance(exec_resp.result, dict) and not exec_resp.result.get('changed', False):
                    dump_text(f"warning_step_{round_idx}.txt", "Action executed but UI signature did not change. Possible failure or noop.")
            else:
                append_exec_log({
                    "phase": "plan",
                    "round": round_idx,
                    "status": "planned",
                    "next_action": next_action,
                    "recognition_strategy": (screen.result or {}).get("element_analysis", {}).get("recognition_strategy", "unknown"),
                })
                generated_steps.append({"step": round_idx, "plan_only": True, "raw": step_json})

        final_screen = await server.execute_tool("get_current_screen_info", {"include_elements": True, "clickable_only": True})
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
            "# 仅输出严格JSON，整合所有步骤。严禁Markdown。\n\n"
            "测试目标: {req}\n\n"
            "最终状态: {final}\n\n"
            "请输出完整的 Only-Test JSON 测试用例（每步使用允许原子动作，包含 priority_selectors 或 bounds_px）：\n"
        ).format(req=requirement, final=json.dumps(final_state, ensure_ascii=False))
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
                    tc = _extract_json(comp_resp.content)
                    ok, why, repaired = _validate_testcase_json(tc)
                    if ok:
                        dump_text("parsed_testcase.json", json.dumps(repaired, ensure_ascii=False, indent=2))
                        return repaired
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
        raise RuntimeError(f"Completion failed or invalid: {last_err}")
        raise RuntimeError("Completion failed or invalid")

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
    logger.info("Calling MCP tool: llm_generate_testcase…")
    resp = await server.execute_tool("llm_generate_testcase", {
        "requirement": args.requirement,
        "target_app": args.target_app
    })

    if not resp.success:
        logger.warning(f"Primary generation failed: {resp.error}; falling back to v2 flow")

    testcase = resp.result
    # Use improved v2 pipeline to refine testcase (multi-round)
    try:
        resp_v2 = await server.execute_tool("llm_generate_testcase_v2", {
            "requirement": args.requirement,
            "target_app": args.target_app
        })
        if resp_v2.success and isinstance(resp_v2.result, dict):
            testcase = resp_v2.result
    except Exception:
        pass

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



