# Only-Test Scaling and Runtime Hardening Guide

This guide documents patterns and guardrails that make LLM-driven UI testing robust and scalable across many similar APKs.

## 1) Why planning alone isn’t enough

High-level plans can’t resolve low-level device timing, focus, IME, overlay ads, and transient UI. Robustness must be enforced at runtime via atomic operations with verification, retries, and fallbacks.

## 2) Roles and responsibilities
- LLM: choose targets, propose next atomic action, and provide expected result + evidence.
- Executor: enforce guardrails, perform-and-verify, retry/backoff, and safe fallbacks.
- MCP/device inspector: provide ground-truth screen state and a whitelist of elements.

## 3) Guardrails (non-negotiable)
- Strict JSON schema (snake_case, atomic actions only).
- Whitelist-bound selectors (resource_id / content_desc / text from current elements only).
- Idempotent atomic ops: click, input, wait, wait_for_elements, swipe, assert, launch, restart.
- Perform-and-verify after each action; proceed only on a validated state.
- TOOL_REQUEST handshake whenever state is unknown or stale.

## 4) Runtime hardening patterns
- Input focus gating: click input box, verify focused; prefer set_text; fallback IME text; verify get_text contains value.
- Click gating: ensure visible and clickable; verify navigation or state change; retry with small bias or alternative selector.
- Popup/ads: proactive close on entry; reactive detection; bounded retries; resume flow.
- Navigation gating: verify page by signature; re-open page if needed; avoid blind BACK.
- Timeouts/backoff: short waits between retries; exponential backoff for network/ads.
- Fallback chain: alt selectors; alt action (ENTER vs button); last resort coordinate click within bounds.

## 5) Failure taxonomy and on_fail schema (per step)
- Element-not-found: refresh screen, retry, alternatives.
- Not-focused / input failed: re-focus, clear, set_text, IME fallback.
- Obstructed by overlay: close ads/popup then retry.
- Page mismatch: navigate explicitly to expected page; re-run preceding step.
- Timeout: extend once then fail fast with diagnostics.

Example on_fail:
```json
{
  "retries": 2,
  "retry_delay_s": 0.3,
  "re_focus": true,
  "fallbacks": [
    {"type": "alt_selector", "selector": {"text": "搜索"}},
    {"type": "ime_text"},
    {"type": "press_enter"}
  ],
  "diagnostics": ["screenshot", "dump_hierarchy"]
}
```

## 6) Observability
- Structured logs per step (action, target, expected_result, outcome, retries, fallbacks).
- Screenshots and hierarchy snapshots on failure.
- Session JSONL for post-mortem and training data.

## 7) Cross‑app generalization strategy
- Define invariant tasks (search, open result, play, full-screen) and map app-specific selectors.
- Maintain per-app profile (canonical selectors, alternates, page signatures).
- Keep steps atomic and verify outcomes, not exact UI sequences.

## 8) Prompt engineering
- Explicitly require evidence and whitelist selectors.
- Enforce single-step handshake; require TOOL_REQUEST on uncertainty.
- Include failure-recovery checklists for input, submission, navigation, and ads.

## 9) Data flywheel
- Convert successful sessions to few-shot snippets.
- Mine failures to enhance prompts and fallback chains.
- Track coverage and stability metrics (pass rate, flake rate, MTTR).

## 10) Adoption playbook
- Start with a single APK family; baseline a manual suite.
- Ship hardened atomic ops; measure delta (time, pass rate, flakes).
- Document ROI and risks; expand to similar APKs via profiles.

—
Maintainers: Only-Test Team

