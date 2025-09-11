#!/usr/bin/env python3
"""
Select up to N example testcases to include in prompts, following these rules:
- Prefer curated Python examples (only_test/testcases/python/*.py)
- Exclude generated artifacts (filenames containing 'from_json' or located under 'generated')
- If total curated examples < min_examples, include all (to help LLM even with small corpus)
- If total curated examples >= min_examples, pick exactly min_examples of the same type (py by default)
- Optionally trim content length for prompt inclusion

Usage:
  python only_test/tools/select_examples.py --root C:/Download/git/uni --type py --max 3 --trim 1200
Outputs JSON with an array of {"file": path, "content": "..."}
"""
import argparse
import json
import os
from typing import List, Dict


def is_generated_py(name: str) -> bool:
    lower = name.lower()
    return ("from_json" in lower) or ("generated" in lower)


def find_py_examples(root: str) -> List[str]:
    py_dir = os.path.join(root, "only_test", "testcases", "python")
    if not os.path.isdir(py_dir):
        return []
    files = []
    for entry in os.scandir(py_dir):
        if not entry.is_file():
            continue
        if not entry.name.endswith(".py"):
            continue
        if is_generated_py(entry.name):
            continue
        files.append(entry.path)
    # Stable order: by name
    files.sort()
    return files


def read_and_trim(path: str, trim: int) -> str:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if trim and len(content) > trim:
        return content[:trim] + "\n# ... (truncated in prompt examples)\n"
    return content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--type", choices=["py"], default="py")
    ap.add_argument("--max", type=int, default=3)
    ap.add_argument("--trim", type=int, default=1200)
    args = ap.parse_args()

    selected: List[Dict[str, str]] = []

    if args.type == "py":
        candidates = find_py_examples(args.root)
        if len(candidates) <= args.max:
            chosen = candidates
        else:
            chosen = candidates[:args.max]
        for p in chosen:
            selected.append({
                "file": p,
                "content": read_and_trim(p, args.trim)
            })

    print(json.dumps(selected, ensure_ascii=False))


if __name__ == "__main__":
    main()

