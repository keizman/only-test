#!/usr/bin/env python3
"""
Digest curated Python examples into compact [page]/[action] lines for prompt few-shot.

Usage:
  python only_test/tools/digest_examples.py --files <file1.py> <file2.py> --max-lines 80
Outputs a JSON list of objects: {"file": path, "digest": "..."}
"""
import argparse
import json


def digest_file(path: str, max_lines: int) -> str:
    out_lines = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if s.startswith('## [page]') or s.startswith('# [page]'):
                out_lines.append(s)
                if len(out_lines) >= max_lines:
                    break
    return "\n".join(out_lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--files', nargs='+', required=True)
    ap.add_argument('--max-lines', type=int, default=80)
    args = ap.parse_args()

    results = []
    for f in args.files:
        results.append({
            'file': f,
            'digest': digest_file(f, args.max_lines)
        })
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()

