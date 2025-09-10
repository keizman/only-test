#!/usr/bin/env python3
"""
Run testcases defined in only_test/testcases/main.yaml.

Features:
- Resolves 'USE_LATEST' for JSON/Python from only_test/testcases/generated/
- Converts JSON to Python when needed
- Runs Python testcases with current Python (or conda run wrapper outside)
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except Exception:
    yaml = None

BASE = Path(__file__).resolve().parents[1]


def latest_in(pattern: str) -> Path | None:
    files = sorted(BASE.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def resolve_case_paths(case: dict) -> tuple[Path | None, Path | None]:
    json_path = case.get('json_path')
    py_path = case.get('path') or case.get('python_path')
    if json_path == 'USE_LATEST':
        p = latest_in('testcases/generated/*.json')
        json_path = str(p) if p else None
    if py_path == 'USE_LATEST_PY':
        p = latest_in('testcases/generated/*.py')
        py_path = str(p) if p else None
    jp = (BASE / json_path).resolve() if json_path else None
    pp = (BASE / py_path).resolve() if py_path else None
    return (jp if (jp and jp.exists()) else None, pp if (pp and pp.exists()) else None)


def convert_json_to_python(json_file: Path) -> Path:
    from only_test.lib.code_generator.json_to_python import JSONToPythonConverter
    conv = JSONToPythonConverter()
    out = conv.convert_json_to_python(str(json_file))
    return Path(out)


def run_py(py_file: Path) -> int:
    cmd = [sys.executable, '-X', 'utf8', str(py_file)]
    proc = subprocess.run(cmd)
    return proc.returncode


def main():
    ap = argparse.ArgumentParser(description='Run YAML-defined test suites')
    ap.add_argument('--suite', help='suite id to run (default: run all)')
    ap.add_argument('--dry-run', action='store_true', help='print plan only')
    args = ap.parse_args()

    if yaml is None:
        print('PyYAML not installed')
        sys.exit(2)

    cfg_path = BASE / 'testcases' / 'main.yaml'
    data = yaml.safe_load(cfg_path.read_text('utf-8'))
    suites = data.get('test_suites', {})
    to_run = {args.suite: suites.get(args.suite)} if args.suite else suites
    if not to_run:
        print('No suites to run')
        return

    for sid, suite in to_run.items():
        if not suite:
            continue
        cases = suite.get('cases') or []
        print(f'== Suite: {sid} ({len(cases)} cases) ==')
        for idx, case in enumerate(cases, 1):
            jp, pp = resolve_case_paths(case)
            print(f'  [{idx}] case: json={jp} py={pp}')
            if args.dry_run:
                continue
            # convert if needed
            if jp and not pp:
                pp = convert_json_to_python(jp)
                print(f'    converted → {pp}')
            if pp:
                rc = run_py(pp)
                print(f'    exit={rc}')


if __name__ == '__main__':
    main()

