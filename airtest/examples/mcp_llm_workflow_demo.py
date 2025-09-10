#!/usr/bin/env python3
"""
MCP + Mock LLM Workflow Demo
============================

Simulates a human specifying a plan, then calls an MCP tool that
represents an external LLM to generate a testcase JSON. Converts the
JSON to Python and prints artifact paths. This demonstrates the project’s
intended flow: not the agent writing the case directly, but invoking an
LLM via MCP to produce it.
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
import sys
import os

# Ensure repo root on sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Local imports
from airtest.lib.mcp_interface.mcp_server import MCPServer, MCPTool, MCPResponse
from airtest.lib.code_generator.json_to_python import JSONToPythonConverter
from airtest.lib.json_to_python import PythonCodeGenerator
from airtest.lib.metadata_engine.path_builder import build_step_path

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
    parser = argparse.ArgumentParser(description="Demo MCP workflow that calls a mock LLM to generate a testcase")
    parser.add_argument("--requirement", required=True, help="Human plan/requirement to pass to the LLM tool")
    parser.add_argument("--target-app", default="com.mobile.brasiltvmobile", help="Target app package")
    parser.add_argument("--outdir", default="airtest/testcases/generated", help="Where to write the generated JSON")
    args = parser.parse_args()

    # Prepare MCP server and register a mock LLM tool
    server = MCPServer()

    async def llm_generate_testcase(**kwargs):
        requirement = kwargs.get("requirement") or args.requirement
        target_app = kwargs.get("target_app") or args.target_app
        logger.info("Mock LLM generating testcase from requirement…")
        data = build_mock_llm_testcase(requirement, target_app)
        return data

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

    # Invoke the LLM tool to produce a testcase
    logger.info("Calling MCP tool: llm_generate_testcase…")
    resp = await server.execute_tool("llm_generate_testcase", {
        "requirement": args.requirement,
        "target_app": args.target_app
    })

    if not resp.success:
        raise RuntimeError(f"Generation failed: {resp.error}")

    testcase = resp.result

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

    # Convert to script-style Python (ready for airtest run)
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        gen = PythonCodeGenerator()
        py_path = outdir / f"test_{json_path.stem}_script.py"
        gen.generate_complete_testcase(json_data, py_path)
        logger.info(f"Converted to script-style Python: {py_path}")
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


