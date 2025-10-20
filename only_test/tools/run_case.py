#!/usr/bin/env python3
"""
Only-Test run_case utility with dry-run validator

Usage examples:
  # Dry-run schema + semantic validation only (no device required)
  python only_test/tools/run_case.py --case only_test/testcases/generated/vod_playing_test_corrected.json --dry-run

  # Dry-run with historical whitelist directories (approximate selector existence check)
  python only_test/tools/run_case.py --case path/to/case.json --dry-run \
      --whitelist-dir logs/mcp_demo --whitelist-dir only_test/assets

Exit code: 0 on success, non-zero on failure.
"""
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Tuple, Set

try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None

ALLOWED_ACTIONS: Set[str] = {
    "launch", "restart", "click", "click_with_bias", "input", "wait", "wait_for_elements", "assert", "swipe"
}
ALLOWED_SELECTOR_KEYS: Set[str] = {"resource_id", "text", "content_desc"}


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_schema(schema_path: str) -> Dict[str, Any]:
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_schema(case: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    if jsonschema is None:
        return False, ["jsonschema not installed. Please install it to run schema validation."]
    validator = jsonschema.Draft202012Validator(schema)  # type: ignore
    errors = []
    for e in validator.iter_errors(case):
        # Build a readable path
        loc = "/".join([str(p) for p in e.path])
        errors.append(f"schema: {loc}: {e.message}")
    return (len(errors) == 0), errors


def _is_single_key_selector(sel: Dict[str, Any]) -> bool:
    return isinstance(sel, dict) and len(sel.keys()) == 1 and next(iter(sel.keys())) in ALLOWED_SELECTOR_KEYS


def semantic_checks(case: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(case, dict):
        return False, ["root must be an object"], warnings

    path = case.get("execution_path")
    if not isinstance(path, list) or len(path) == 0:
        return False, ["execution_path must be a non-empty array"], warnings

    last_step_num = 0
    for idx, step in enumerate(path):
        ctx = f"step[{idx}]"
        if not isinstance(step, dict):
            errors.append(f"{ctx}: step must be an object")
            continue

        step_num = step.get("step")
        if isinstance(step_num, int):
            if step_num < last_step_num:
                warnings.append(f"{ctx}: step number not strictly increasing: {step_num} < {last_step_num}")
            last_step_num = step_num

        step_type = step.get("type")
        if step_type not in ("ui", "tool"):
            errors.append(f"{ctx}: type must be 'ui' or 'tool'")
            continue

        if step_type == "ui":
            action = step.get("action")
            if action not in ALLOWED_ACTIONS:
                errors.append(f"{ctx}: invalid or missing action: {action}")
                continue
            target = step.get("target", {}) if isinstance(step.get("target"), dict) else {}
            selectors = target.get("priority_selectors")
            bounds_px = target.get("bounds_px")

            # selector structure
            if selectors is not None:
                if not isinstance(selectors, list):
                    errors.append(f"{ctx}: target.priority_selectors must be a list")
                else:
                    for j, sel in enumerate(selectors):
                        if not _is_single_key_selector(sel):
                            errors.append(f"{ctx}: priority_selectors[{j}] must be a single-key object with one of {sorted(ALLOWED_SELECTOR_KEYS)}")

            # dependencies (duplicate with schema, but we enforce here too with clearer messages)
            if action == "input":
                data = step.get("data", {}) if isinstance(step.get("data"), dict) else {}
                text = data.get("text")
                if not isinstance(text, str) or text.strip() == "":
                    errors.append(f"{ctx}: input requires non-empty data.text")
                if not selectors:
                    errors.append(f"{ctx}: input requires target.priority_selectors")

            if action == "swipe":
                swipe = target.get("swipe") if isinstance(target, dict) else None
                if not (isinstance(swipe, dict) and isinstance(swipe.get("start_px"), list) and isinstance(swipe.get("end_px"), list)):
                    errors.append(f"{ctx}: swipe requires target.swipe.start_px and end_px")

            if action == "wait_for_elements":
                if not selectors:
                    errors.append(f"{ctx}: wait_for_elements requires target.priority_selectors")

            if action in ("click", "click_with_bias", "input"):
                if not selectors and not bounds_px:
                    errors.append(f"{ctx}: click/input requires either priority_selectors or bounds_px")

        else:  # tool step
            tool_name = step.get("tool_name")
            if not isinstance(tool_name, str) or not tool_name:
                errors.append(f"{ctx}: tool step requires tool_name")

    return (len(errors) == 0), errors, warnings


def collect_whitelist_from_dirs(dirs: List[str]) -> Dict[str, Set[str]]:
    """Collect approximate selector whitelists from logs or saved snapshots.
    Accepts JSON or JSONL files that contain objects with an 'elements' array.
    """
    wl = {"resource_id": set(), "text": set(), "content_desc": set()}

    def _ingest_elements(elems: List[Dict[str, Any]]):
        for e in elems:
            for k in wl.keys():
                v = e.get(k)
                if isinstance(v, str) and v:
                    wl[k].add(v)

    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for fn in files:
                if not (fn.endswith(".json") or fn.endswith(".jsonl")):
                    continue
                path = os.path.join(root, fn)
                try:
                    if fn.endswith(".jsonl"):
                        with open(path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    obj = json.loads(line)
                                except Exception:
                                    continue
                                elems = obj.get("elements") or obj.get("post", {}).get("elements") or []
                                if isinstance(elems, list):
                                    _ingest_elements(elems)
                    else:
                        obj = load_json(path)
                        # try multiple common nesting patterns
                        candidates: List[List[Dict[str, Any]]] = []
                        if isinstance(obj.get("elements"), list):
                            candidates.append(obj.get("elements"))
                        if isinstance(obj.get("screen_analysis"), dict) and isinstance(obj["screen_analysis"].get("elements"), list):
                            candidates.append(obj["screen_analysis"]["elements"])
                        if isinstance(obj.get("post"), dict) and isinstance(obj["post"].get("elements"), list):
                            candidates.append(obj["post"]["elements"])
                        for elems in candidates:
                            _ingest_elements(elems)
                except Exception:
                    continue
    return wl


def approximate_selector_existence(case: Dict[str, Any], whitelist: Dict[str, Set[str]], strict: bool = False) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    if not whitelist or all(len(s) == 0 for s in whitelist.values()):
        return errors, warnings

    for idx, step in enumerate(case.get("execution_path", [])):
        if not isinstance(step, dict) or step.get("type") != "ui":
            continue
        target = step.get("target") or {}
        selectors = target.get("priority_selectors") or []
        for j, sel in enumerate(selectors):
            if not _is_single_key_selector(sel):
                continue
            k, v = list(sel.items())[0]
            if v and isinstance(v, str) and v not in whitelist.get(k, set()):
                msg = f"step[{idx}].priority_selectors[{j}]: {k}={v} not found in historical whitelist"
                if strict:
                    errors.append(f"approx: {msg}")
                else:
                    warnings.append(f"approx: {msg}")
    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Only-Test run_case with dry-run validator")
    parser.add_argument("--case", required=True, help="Path to testcase JSON")
    parser.add_argument("--dry-run", action="store_true", help="Validate schema + semantics without device")
    parser.add_argument("--schema", default=os.path.join("only_test", "tools", "json_schema", "testcase.schema.json"), help="Path to JSON schema")
    parser.add_argument("--whitelist-dir", action="append", default=[], help="Directory containing historical elements (json/jsonl) for approximate selector checks")
    parser.add_argument("--strict", action="store_true", help="Treat approximate selector misses as errors")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    case = load_json(args.case)

    # Always do schema + semantic validation if --dry-run
    if args.dry_run:
        ok_all = True
        messages: List[str] = []

        # Schema validation
        try:
            schema = load_schema(args.schema)
            ok_schema, schema_errs = validate_schema(case, schema)
        except Exception as e:
            ok_schema, schema_errs = False, [f"schema loading error: {e}"]
        if not ok_schema:
            ok_all = False
            messages.extend(schema_errs)

        # Semantic checks
        ok_sem, sem_errs, sem_warns = semantic_checks(case)
        if not ok_sem:
            ok_all = False
        messages.extend(sem_errs)
        messages.extend([f"WARN: {w}" for w in sem_warns])

        # Approximate whitelist selector check
        approx_errs: List[str] = []
        approx_warns: List[str] = []
        wl_dirs = list(args.whitelist_dir or [])
        # Auto-include known logs dir if exists
        auto_dir = os.path.join("logs", "mcp_demo")
        if os.path.isdir(auto_dir) and auto_dir not in wl_dirs:
            wl_dirs.append(auto_dir)
        if wl_dirs:
            wl = collect_whitelist_from_dirs(wl_dirs)
            e2, w2 = approximate_selector_existence(case, wl, strict=args.strict)
            approx_errs.extend(e2)
            approx_warns.extend(w2)
            if e2:
                ok_all = False
        messages.extend(approx_errs)
        messages.extend([f"WARN: {w}" for w in approx_warns])

        if ok_all:
            print("Dry-run validation PASSED")
            if args.verbose and messages:
                print("\nNotes:\n" + "\n".join(messages))
            sys.exit(0)
        else:
            print("Dry-run validation FAILED")
            print("\n".join(messages))
            sys.exit(2)

    # Non-dry-run path (placeholder)
    print("Execution mode is not yet implemented. Use --dry-run for static validation.")
    sys.exit(1)


if __name__ == "__main__":
    main()

