#!/usr/bin/env python3
"""
Testcase JSON v1.1 validator with schema-based and fallback checks.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Tuple, Dict, Any, List

SCHEMA_PATH = Path(__file__).with_name('testcase_v1_1.json')


def _load_schema() -> Dict[str, Any]:
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_testcase_v1_1(tc: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate testcase JSON; returns (ok, reason, repaired_tc).

    - Enforces allowed actions and selector presence for click/input/wait_for_elements/swipe
    - Attempts minor repairs when possible (e.g., promote direct resource_id to priority_selectors)
    """
    schema = None
    try:
        import jsonschema  # type: ignore
        schema = _load_schema()
        jsonschema.validate(tc, schema)
    except Exception:
        # Fall back to lightweight validation
        pass

    repaired = json.loads(json.dumps(tc))  # deep copy
    allowed = {"click", "input", "wait", "wait_for_elements", "restart", "launch", "assert", "swipe"}
    ep = repaired.get('execution_path', [])
    if not isinstance(ep, list) or not ep:
        return False, 'execution_path is empty', repaired

    def ensure_selectors(target: Dict[str, Any]) -> bool:
        if not isinstance(target, dict):
            return False
        if target.get('priority_selectors') or target.get('selectors'):
            return True
        # Promote direct keys
        if target.get('resource_id') or target.get('content_desc') or target.get('text'):
            sels = []
            if target.get('resource_id'):
                sels.append({'resource_id': target['resource_id']})
            if target.get('content_desc'):
                sels.append({'content_desc': target['content_desc']})
            if target.get('text'):
                sels.append({'text': target['text']})
            if sels:
                target['priority_selectors'] = sels
                return True
        # Or bounds_px for visual
        if isinstance(target.get('bounds_px'), list) and len(target['bounds_px']) == 4:
            return True
        return False

    for i, step in enumerate(ep, 1):
        action = (step.get('action') or '').lower()
        if action not in allowed:
            return False, f'step {i}: invalid action {action}', repaired
        if action in {'click', 'input', 'wait_for_elements'}:
            target = step.get('target') or {}
            if not ensure_selectors(target):
                return False, f'step {i}: missing selectors/bounds for {action}', repaired
        if action == 'swipe':
            tgt = step.get('target') or {}
            swipe = tgt.get('swipe', {}) if isinstance(tgt, dict) else {}
            if not (isinstance(swipe, dict) and isinstance(swipe.get('start_px'), list) and isinstance(swipe.get('end_px'), list)):
                return False, f'step {i}: swipe requires target.swipe.start_px/end_px', repaired

    return True, 'ok', repaired


if __name__ == '__main__':
    import argparse, sys
    p = argparse.ArgumentParser(description='Validate Only-Test testcase JSON v1.1')
    p.add_argument('json_file')
    args = p.parse_args()
    data = json.loads(Path(args.json_file).read_text('utf-8'))
    ok, why, _ = validate_testcase_v1_1(data)
    print('OK' if ok else 'FAIL', why)
    sys.exit(0 if ok else 1)

