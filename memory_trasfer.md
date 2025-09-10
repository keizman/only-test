> Mission & Objectives


---

Successor Handoff — 2025-09-10

- Purpose: Capture the latest state, decisions, and a concrete plan so the next engineer can continue seamlessly.

Plan (High-Level)

1) Validate device + UI stack
2) Stabilize recognition (XML/visual)
3) Enforce prompt + JSON strictness
4) Improve per-round logging
5) Harden orchestrator paths
6) Address known env pitfalls
7) Tighten schema + conversions

What Changed Recently (Context You Need)

- Multi-round LLM→MCP orchestration added to the demo (dry-run by default)
  - New tool `llm_generate_testcase_v2` inside the demo, loops: capture UI → LLM step plan → re-sample → completion.
  - Strict JSON enforced via system messages: “Output strict JSON only. Do not use markdown fences.”
  - Selector priority clarified at the LLM boundary: resource_id > content_desc > text; no fabrication.

- Per-step execution logging
  - Appends JSONL at `logs/mcp_demo/session_<ts>/execution_log.jsonl` with: phase, round, status, next_action, recognition_strategy, timestamp.

- Import path robustness
  - Demo prioritizes repo root in `sys.path` to avoid collisions with the PyPI `airtest` package.

- Migration to `only_test`
  - `only_test/examples/mcp_llm_workflow_demo.py` mirrors the multi-round behavior and logging; outputs to `only_test/testcases/generated/`.

- XML extractor compatibility fix
  - Fixed crash: `'UnifiedElement' object has no attribute 'content_desc'`.
  - Change: in `only_test/lib/visual_recognition/element_recognizer.py`, XML branch now derives `content_desc` safely (from attribute, then metadata, else empty string).

How To Run (Current)

- Demo (only_test, multi-round, dry-run):
  - `python -X utf8 only_test/examples/mcp_llm_workflow_demo.py --requirement "验证播放页的搜索与结果展示" --target-app com.mobile.brasiltvmobile --max-rounds 2`
  - Artifacts under `logs/mcp_demo/session_<ts>/` and `only_test/testcases/generated/`.

- Integration logs:
  - See `logs/test_mcp_llm_integration_<ts>.log` if present; the multi-round demo produces its own session logs.

Environment Requirements

- LLM:
  - `LLM_PROVIDER=openai_compatible`
  - `LLM_API_URL=https://<host>/v1`
  - `LLM_API_KEY=...`
  - `LLM_MODEL=gpt-4o-mini` (or compatible)
  - Self-test: `python -X utf8 only_test/lib/llm_integration/llm_client.py`

- Device + tools:
  - ADB device connected (`adb devices`), grant permissions; pass `--device-id` if needed.
  - Install `uiautomator2` to enable XML element extraction; otherwise XML mode may return 0 elements.
  - OmniParser: set `OMNIPARSER_SERVER=http://<host>:9333`; confirm health.

Known Issues and Mitigations

- XML extractor may fail without `uiautomator2`.
  - Mitigation: `pip install uiautomator2` and ensure device connectivity.

- OmniParser instability (HTTP 500 / connection resets) reduces element quality.
  - Mitigation: stabilize server, or temporarily force XML_ONLY mode when visual fails repeatedly.

- Strategy enum mismatch (“'HYBRID' is not a valid RecognitionStrategy”).
  - Likely a casing/enum mapping mismatch; fallback currently handles it. Normalize enum mapping where the exception originates.

- Mojibake in some templates/logs.
  - UTF-8 is used; residual mojibake likely from historical text. Clean up Chinese strings in prompt templates if they hinder LLM.

Immediate Next Steps (Actionable)

1) Device/UI stack
   - Install `uiautomator2`; verify XML extraction returns elements.
   - Add a flag to force `XML_ONLY` or `VISUAL_ONLY` in demo for reproducibility while debugging.

2) Recognition stability
   - Add retry/backoff for OmniParser, and graceful fallback logging when switching modes.
   - Normalize `RecognitionStrategy` casing at the source of the invalid value.

3) Prompt + JSON hardening
   - If needed, embed strict rules directly in `only_test/templates/prompts/generate_cases.py` (not just system messages).
   - Provide a minimal, valid JSON skeleton in completion prompts to reduce missing fields.

4) Logging improvements
   - Add per-round screenshots (`only_test/lib/screen_capture.py`) and write `screenshot_path` into `execution_log.jsonl`.
   - Append execution_log.jsonl with `duration_ms` per phase and `elements_count` to aid triage.

5) Orchestrator path
   - Wire the multi-round flow into `only_test/lib/mcp_interface/workflow_orchestrator.py` so demo and orchestrator are consistent.

6) Schema + conversion
   - Ensure `execution_path` always exists (even if empty) and include path provenance via `build_step_path`.
   - Keep enforcing: selector priority (resource_id > content_desc > text), no fabrication, add wait/timeout norms.

7) Cleanup
   - Sweep for mojibake in `only_test/templates/prompts/` and logs; normalize strings where safe.

Troubleshooting Quicklist

- `ModuleNotFoundError` for local libs:
  - The demo inserts repo root into `sys.path` early to avoid PyPI collisions. Keep that pattern for new entry points.

- LLM outputs non‑JSON or fenced Markdown:
  - System prompt enforces strict JSON; add a skeleton example in the user prompt if needed.

- No elements returned:
  - Check device connectivity and `uiautomator2` installation; switch to `VISUAL_ONLY` if OmniParser is healthy.

Verification Checklist

- LLM env set; LLM client self-test succeeds.
- Device available; XML or visual extraction returns elements.
- Session logs contain: prompt_*.txt, response_*.txt, parsed_testcase.json; no parse errors.
- `execution_log.jsonl` appended per round with clear context.
- Generated testcase JSON has `execution_path` and path provenance.
- Python conversion succeeds (pytest or script-style); if a path warning occurs, fall back is automatic.

Notes

- Keep the system strict (no mock fallback) to surface real integration issues early.
- Preserve path provenance and per-step artifacts; evolve schemas additively.
- Maintain the selector priority rule and avoid fabrications; include waits and timeouts in steps.
  - Establish end-to-end “human plan → LLM via MCP → JSON testcase → script-style Python → run on device”.
  - Enforce template-driven prompting so external LLM “knows what to do”.
  - Use real device and real LLM (no mock fallback) and record full logs for forensics and prompt iteration.
  - Preserve “path” provenance and per-step artifacts to support auditing and QA.

  Current State

  - Demo uses template prompts and real MCP tools:
      - airtest/examples/mcp_llm_workflow_demo.py calls DeviceInspector via MCP, then LLM via TestCaseGenerationPrompts (step-guidance → completion).
      - Strict mode: no mock fallback. Any failure logs artifacts and raises.
      - Artifacts written to logs/mcp_demo/session_<ts>/ including prompts, raw LLM responses, parsed JSON, tool responses, errors, and session.log.
  - Integration test enhanced:
      - test_llm_driven_generation.py registers real DeviceInspector tools, calls get_current_screen_info, drives LLM with the step-guidance prompt, and writes consolidated logs at logs/
  test_mcp_llm_integration_<ts>.log.
  - Prompt templates:
      - Primary: airtest/templates/prompts/generate_cases.py (main/step/completion).
      - Temporarily disabled heavy template import to avoid unrelated syntax errors: airtest/templates/prompts/__init__.py no longer imports code_optimization.py.

  How To Run

  - Demo (strict real env; logs+artifacts):
      - python -X utf8 airtest/examples/mcp_llm_workflow_demo.py --requirement "验证播放页的搜索与结果展示" --target-app com.mobile.brasiltvmobile [--device-id <id>]
      - Outputs to logs/mcp_demo/session_<ts>/ and airtest/testcases/generated/.
  - Integration test (logs only):
      - python -X utf8 test_llm_driven_generation.py
      - Outputs logs/test_mcp_llm_integration_<ts>.log.
  - Device:
      - adb devices and optionally --device-id <id>.

  LLM Configuration

  - Required env:
      - LLM_PROVIDER=openai_compatible
      - LLM_API_URL=https://<host>/v1 (base “/v1”, not “/chat/completions”)
      - LLM_API_KEY=...
      - LLM_MODEL=gpt-4o-mini (or your compatible model)
  - Self test:
      - python -X utf8 airtest/lib/llm_integration/llm_client.py (expects “✅ LLM服务可用”).

  MCP Tools (Real)

  - DeviceInspector (airtest/lib/mcp_interface/device_inspector.py) provides:
      - get_device_basic_info, get_current_screen_info(include_elements), find_elements_by_content, analyze_app_state, get_system_status, etc.
  - Registration in demo and test is automatic via reflection on @mcp_tool.

  Data Flow

  1. Human requirement passed as --requirement.
  2. Demo calls MCP get_current_screen_info(include_elements=True) to capture real UI state.
  3. Build step-guidance prompt (template).
  4. Call LLM (LLMClient.chat_completion) with strict JSON constraint; persist raw response and parsed JSON.
  5. Re-sample screen; build completion prompt and call LLM to produce final testcase JSON; persist raw/parsed.
  6. Convert JSON → script-style Python; persist artifact paths.

  Logging & Artifacts

  - Demo session dir: logs/mcp_demo/session_<ts>/
      - session.log: high-level flow, errors.
      - tool_get_current_screen_info.json, tool_get_current_screen_info_after.json: MCP responses.
      - prompt_step_1.txt, response_step_1.txt, parsed_step_1.json, error_parse_step_1.txt (if any).
      - prompt_completion.txt, response_completion.txt, parsed_testcase.json, error_parse_completion.txt (if any).
      - artifact_json_path.txt, artifact_python_path.txt.
      - error_* files with details on failure cause.
  - Integration test:
      - logs/test_mcp_llm_integration_<ts>.log includes prompts/response snippets via logger.

  Path Provenance (v1)

  - Each generated execution_path step should include a path object built via build_step_path(...):
      - Keys: workflow_id, tool_name/category, step_index, target_app, device_id, screen_hash (if available), decision_reason.
  - Persist for generation phase; extend in execution phase with: status, error, screenshot_path, selector_used, bounds_px.

  Common Pitfalls & What To Log

  - LLM unavailable or misconfigured:
      - Symptom: error_llm_unavailable.txt or session.log with provider unavailable; check LLM_API_URL and API key.
  - MCP get_current_screen_info fails (no adb/permissions):
      - Symptom: tool response success=false; fix device connection; optionally specify --device-id.
  - LLM outputs non-JSON or fenced Markdown:
      - Symptom: parse error files; keep raw response; adjust prompt to enforce “strict JSON only”.
  - Missing keys in produced JSON (no execution_path, missing path):
      - Symptom: JSON parsing fine but schema invalid; add explicit instructions in completion prompt for required fields.
  - Python conversion fails:
      - Symptom: error_python_conversion.txt; inspect parsed JSON and generator expectations; adjust generator or output format.

  Immediate Next Steps

  - Multi-round orchestration (LLM drives MCP repeatedly):
      - Loop: LLM step plan → MCP execute (e.g., click/input) → re-analyze → LLM next step → … → completion.
      - Strict logging per round: prompt_step_N.txt, response_step_N.txt, tool_exec_*.json, parsed_step_N.json.
      - Safety gate for actions: limit to a white-list of actions or “dry-run” mode initially.
  - Prompt refinement:
      - Enforce selector priority (resource_id > content_desc > text), “no fabrication” rule, and wait_for_elements norms.
      - Add schema snippet examples and minimal-valid JSON skeleton in prompt; include “Do not wrap in markdown fences.”
  - Execution-phase logging:
      - Implement per-step JSONL execution_log.jsonl with appended entries; include status, duration_ms, screenshot_path, recognition.strategy, selector_used.
  - Normalizer integration:
      - Wire visual_recognition/normalizer.py into element collection so OmniParser/UIA outputs unify to bounds_px, uuid, interactivity.
  - OmniParser config path:
      - Respect OMNIPARSER_SERVER and surface base_url in logs (omniparser_client logs base_url, health).

  Conventions

  - Commands/paths/code identifiers use backticks.
  - Logs under logs/ with session/time-based subfolders.
  - Do not re-introduce mock fallback in demo; keep it strict to expose issues early.
  - Keep JSON outputs minimal and valid; avoid markdown code fences when not asked.

  Open Questions (track in QA.md)

  - How much autonomy should LLM have to execute device actions? Introduce a policy (read-only → controlled actions → full actions).
  - Minimal required schema for testcase (which keys are mandatory; what are default fallbacks).
  - When to switch recognition modes (XML vs vision) and how to signal that in prompts/results.
  - Standard for path fields and per-step execution logging schema (lock v1).

  Verification Checklist

  - LLM env variables set; airtest/lib/llm_integration/llm_client.py reports available.
  - Device available via adb; MCP get_current_screen_info returns elements.
  - Demo produces: prompt_*.txt, response_*.txt, parsed_*.json; no parse errors.
  - Generated testcase JSON includes execution_path with path fields per step.
  - Python conversion succeeds; run against connected device if appropriate.

  Hand-off Notes

  - Focus your iterations on “observe logs → tweak prompt → re-run”. Each session folder contains everything you need to compare LLM behavior against expectations.
  - If you touch any code that outputs or consumes testcase JSON, maintain the path provenance and avoid breaking existing keys; evolve it via additive changes.
  - When adding multi-round LLM+MCP, keep “dry-run mode” and per-round artifacts as first-class citizens to ensure safe, iterative debugging.
