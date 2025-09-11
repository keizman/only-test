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
    - Enforces strict selector schema: priority_selectors must be a list[dict] with only snake_case keys
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

    def _has_bad_key_name(k: str) -> bool:
        # Reject dashed or camelCase selector keys explicitly
        bad = {"resource-id", "content-desc", "contentDesc", "prioritySelectors", "priority-selectors"}
        return k in bad or ("-" in k) or any(c.isupper() for c in k)

    def _validate_selector_item(d: Dict[str, Any]) -> bool:
        if not isinstance(d, dict):
            return False
        # Reject bad keys
        for k in d.keys():
            if _has_bad_key_name(k):
                return False
        # Must contain exactly one of the allowed keys
        allowed_keys = {"resource_id", "content_desc", "text"}
        present = [k for k in d.keys() if k in allowed_keys]
        if len(present) != 1:
            return False
        # Value must be non-empty string
        v = d[present[0]]
        return isinstance(v, str) and len(v.strip()) > 0

    def _validate_priority_selectors(name: str, ps: Any) -> Tuple[bool, str]:
        if isinstance(ps, dict):
            return False, f'{name} must be a list, not an object'
        if not isinstance(ps, list) or not ps:
            return False, f'{name} must be a non-empty list of selector dicts'
        for idx, item in enumerate(ps, 1):
            if not _validate_selector_item(item):
                return False, f'{name}[{idx}] must be a dict with exactly one of resource_id|content_desc|text (snake_case only)'
        return True, 'ok'

    def ensure_selectors(target: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(target, dict):
            return False, 'target must be an object'
        # Strictly validate priority_selectors or selectors if present
        if 'priority_selectors' in target:
            ok, why = _validate_priority_selectors('priority_selectors', target['priority_selectors'])
            if not ok:
                return False, why
            return True, 'ok'
        if 'selectors' in target:
            ok, why = _validate_priority_selectors('selectors', target['selectors'])
            if not ok:
                return False, why
            return True, 'ok'
        # Promote direct keys (snake_case only)
        if target.get('resource_id') or target.get('content_desc') or target.get('text'):
            # reject dashed/camelCase direct keys
            for k in target.keys():
                if _has_bad_key_name(k):
                    return False, f'illegal selector key {k} (use snake_case)'
            sels = []
            if target.get('resource_id'):
                sels.append({'resource_id': target['resource_id']})
            if target.get('content_desc'):
                sels.append({'content_desc': target['content_desc']})
            if target.get('text'):
                sels.append({'text': target['text']})
            if sels:
                target['priority_selectors'] = sels
                return True, 'ok'
        # Or bounds_px for visual (must be integer pixel coordinates)
        bp = target.get('bounds_px')
        if isinstance(bp, list) and len(bp) == 4 and all(isinstance(x, int) for x in bp):
            return True, 'ok'
        return False, 'missing valid selectors/bounds'

    for i, step in enumerate(ep, 1):
        action = (step.get('action') or '').lower()
        if action not in allowed:
            return False, f'step {i}: invalid action {action}', repaired
        if action in {'click', 'input', 'wait_for_elements'}:
            target = step.get('target') or {}
            ok, why = ensure_selectors(target)
            if not ok:
                return False, f'step {i}: {why} for {action}', repaired
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

