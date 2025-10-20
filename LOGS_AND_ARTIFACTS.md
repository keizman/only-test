Only-Test Logs and Artifacts

Overview
- Each demo/session writes a structured folder under `logs/mcp_demo/session_<timestamp>/`.
- This layout makes it easy to inspect prompts, responses, tool outputs, executions, and final artifacts.

Tree
- session.log — high-level flow
- meta/
  - session_meta.json — requirement, target_app, device_id, env, timestamps
- prompts/
  - prompt_step_<n>.txt, prompt_completion.txt
- responses/
  - response_step_<n>.txt, response_completion.txt
- tools/
  - tool_get_current_screen_info_round_<n>.json
  - tool_get_current_screen_info_after.json
- executions/
  - execution_log.json — JSON object with an entries array (append by rewrite)
  - execution_log_step_<n>.json — structured result of perform_and_verify
- artifacts/
  - parsed_testcase.json — final JSON produced by LLM
  - artifact_json_path.txt — path to written testcase JSON
  - artifact_python_path.txt — path to generated Python
- errors/
  - error_parse_step_<n>.txt, error_parse_completion.txt, error_pipeline.txt, etc.
- warnings/
  - warning_step_<n>.txt — e.g., action executed but UI signature did not change

How to Triage
- Start with `session.log` for the big picture and timestamps.
- Open `meta/session_meta.json` for arguments and environment.
- Look at `tools/*.json` for what the device returned.
- Compare `prompts/*` and `responses/*` to see what the LLM received and produced.
- Check `executions/execution_log.json` and `execution_log_step_*.json` to verify that each step executed and whether the UI changed.
- If parsing/validation failed, `errors/*` contains why.
- `artifacts/` contains the final JSON and Python paths for quick access.

Archiving
- A session folder is self-contained; you can zip it and attach to bug reports.
- Recommended: include `artifacts/parsed_testcase.json` and the latest `tools/*.json` when reporting selector issues.
