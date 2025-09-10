# Airtest / Only-Test — Overview and Completion Plan

## What This Project Wants To Do
- AI-assisted mobile app testing: let an external LLM “drive” Android devices through MCP tools to explore UI, plan steps, and generate executable tests.
- Dual-mode element recognition: combine UIAutomator2 (XML, fast/precise) with OmniParser/YOLO (visual, works in dynamic or DRM/video states). Auto-switch when XML is incomplete (e.g., during playback).
- Structured test generation: record minimal human intent once, have the LLM harvest device/UI context, then output standardized JSON testcases with a `path` field to trace tools, screens, elements, and actions used.
- Deterministic execution with recovery: convert JSON to Python and run via an execution engine that logs, screenshots, handles conditional branches, retries/fallbacks, and summarizes results.

## How It Works (Happy Path)
1) Connect device and gather basics (`get_device_basic_info`, `get_screen_info`).
2) Capture screen and detect state (e.g., playback) to choose recognition mode.
3) Recognize elements: prefer UIAutomator2; fallback to OmniParser; normalize outputs to a common format (`resource_id`, `bbox`).
4) LLM plans steps and writes JSON with `execution_path` and `path` provenance.
5) Convert JSON → Python (`airtest/lib/code_generator/json_to_python.py`).
6) Execute steps with `SmartTestExecutor`, capture screenshots, assert outcomes.
7) Feedback loop analyzes errors and iterates case generation until pass or max tries.

## Key Components (By Area)
- MCP interface: `airtest/lib/mcp_interface/`
  - `mcp_server.py`, `tool_registry.py`, `device_inspector.py`, `case_generator.py`, `feedback_loop.py`, `workflow_orchestrator.py` (entry for end-to-end flow).
- Visual recognition: `airtest/lib/visual_recognition/`
  - `omniparser_client.py`, `element_recognizer.py`, `strategy_manager.py`, `playback_detector.py` (ADB-based playback detection), `visual_integration.py`.
- Execution engine: `airtest/lib/execution_engine/smart_executor.py` for running steps, conditional logic (`metadata_engine/conditional_logic.py`), screenshots, and recovery.
- Codegen: `airtest/lib/code_generator/json_to_python.py` with Jinja templates (`templates/pytest_airtest_template.py.j2`).
- Phone/device ops: `airtest/lib/phone_use_core/` (e.g., `screen_capture.py`).
- Config and examples: `airtest/config/*.yaml`, `airtest/examples/*`, `test_*.py` for LLM + MCP integration.

## Highlights From QA.md (Essentials)
- Standard record/spec: `example_airtest_record.py` shows the canonical annotation style; setup hooks bridge Airtest-friendly steps.
- LLM scope: (1) element recognition + localization; (2) reasoning/planning into structured JSON.
- `path` in JSON: provenance of which tools/screens/elements led to the final action; supports traceability and re-execution.
- Dual recognition: UIAutomator2 (fast, precise) vs OmniParser (visual, 90%+ in playback UIs). Must normalize OmniParser results to UIA2-like fields.
- MCP tools cover device ops, generator (create cases, convert to Python), feedback, and end-to-end workflow.
- Failure & recovery: attempt fallback recognition, explain LLM failures, and keep workflows resumable with state files.
- Assets & naming: `assets/{pkg_device}/` with timestamped screenshots and folders like `omni_result`, `element_screenshot`, `execution_log`.
- Success criteria: image-similarity thresholds for post-action verification, plus explicit assertions.

## Current Status (Quick Read)
- Core modules and scaffolding exist for recognition, workflow, codegen, and execution.
- Tests and examples present; some parts are stubs or need integration and normalization glue.
- QA.md defines conventions, states, and tool lists that should be enforced in code.

## Completion Plan (Phased)

1) Baseline E2E (Single App/Device)
- Wire minimal MCP tools: `capture_screen`, `analyze_ui_elements`, `click_element`, `input_text`.
- Configure OmniParser endpoint and a toggle for recognition strategy.
- Finalize JSON schema (actions, `path`, conditional blocks) and validate with a sample case.
- Implement JSON→Python conversion and run via `SmartTestExecutor` end-to-end.
- Deliverable: one green test from prompt → JSON → Python → executed.

2) Robust Recognition + Auto-Switch
- Implement `playback_detector.py` in workflow to decide mode automatically.
- Normalize OmniParser outputs to UIAutomator2-like fields (`resource_id`, `bbox`).
- Add fallback and error taxonomy; surface actionable messages to LLM.
- Deliverable: scenarios switching between modes without manual intervention.

3) Orchestrator + Feedback Loop
- Complete `workflow_orchestrator.py` phases (collect → generate → convert → execute → analyze).
- Persist `workflow_state.json`, `execution_progress.json`, `iteration_config.json` for resume.
- Add structured logs, screenshots, and metrics for each step.
- Deliverable: iterative improvement over up to N runs with actionable feedback.

4) Data & Assets Hygiene
- Enforce naming convention `{pkg}_{device}` and folder structure under `assets/`.
- Save `omni_result`, `element_screenshot`, `execution_log` consistently per step.
- Config hardening: `device_config.yaml`, `framework_config.yaml`, `execution_config.json`.
- Deliverable: reproducible artifacts and clear run history per workflow.

5) Quality & Docs
- Unit tests for: strategy manager, playback detection, JSON→Python codegen, executor conditionals.
- Integration tests: mock MCP server + visual recognizer for deterministic CI.
- Update `getstart.md` with one-command quickstart and troubleshooting; link to QA.md conventions.
- Deliverable: passing tests and newcomer-friendly docs.

6) Stretch Goals
- SDK-based probing where available for media state.
- Broader device coverage (Android TV, emulators with varied DPI/resolutions).
- Light UI (e.g., Gradio) to visualize screens, elements, and step-by-step execution.

## Minimal Next Actions
- Lock JSON schema and finalize converter behavior with examples in `airtest/testcases/generated/`.
- Implement normalization glue in `visual_recognition/element_recognizer.py` + `strategy_manager.py`.
- Finish `start_complete_workflow` happy path and add basic state persistence.
- Add a sample workflow script and document the exact run command in `getstart.md`.
