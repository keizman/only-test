#!/usr/bin/env python3
"""
Build a lightweight Playground for a session by merging unified logs and
recording steps, and emitting a simple HTML to visualize steps with bounds.

Usage:
  python only_test/tools/playground/build_playground.py \
      --session-dir logs/mcp_demo/session_YYYYMMDD_HHMMSS \
      [--recording only_test/testcases/generated/record_session_*.json]

Outputs:
  - <session-dir>/session_unified_with_recording.json
  - <session-dir>/playground.html

Notes:
  - Recording accepts JSON (preferred) or JSONL for backward compatibility.
  - Screenshots are matched by pattern: screenshots/step_###_*.png
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_json_or_jsonl(p: Path) -> List[Dict[str, Any]]:
    """Load recording steps from JSON (object with steps[]) or JSONL.

    Returns a list of step dicts.
    """
    text = p.read_text(encoding="utf-8").strip()
    # JSON array/object path
    if text.startswith("{") or text.startswith("["):
        data = json.loads(text)
        if isinstance(data, dict) and "steps" in data:
            return list(data.get("steps") or [])
        if isinstance(data, list):
            return data
        # Fallback
        return []
    # JSONL path
    steps: List[Dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            steps.append(json.loads(line))
        except Exception:
            # skip
            pass
    return steps


def _find_latest_recording(default_dir: Path) -> Optional[Path]:
    files = sorted(default_dir.glob("record_session_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    if files:
        return files[0]
    # Fallback to JSONL
    files = sorted(default_dir.glob("record_session_*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _collect_screenshots(session_dir: Path) -> Dict[int, str]:
    shots: Dict[int, str] = {}
    shot_dir = session_dir / "screenshots"
    if not shot_dir.exists():
        return shots
    pat = re.compile(r"^step_(\d{3})_.*\.png$")
    for file in sorted(shot_dir.glob("*.png")):
        m = pat.match(file.name)
        if not m:
            continue
        try:
            idx = int(m.group(1))
            shots[idx] = f"screenshots/{file.name}"
        except Exception:
            continue
    return shots


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session-dir", required=True, help="Path to a unified_logger session directory")
    ap.add_argument("--recording", default=None, help="Path to recording JSON/JSONL (optional)")
    args = ap.parse_args()

    session_dir = Path(args.session_dir).resolve()
    if not session_dir.exists():
        raise SystemExit(f"Session dir not found: {session_dir}")

    # Load session_unified.json if present
    unified_path = session_dir / "session_unified.json"
    unified_data: Dict[str, Any]
    if unified_path.exists():
        try:
            unified_data = json.loads(unified_path.read_text(encoding="utf-8"))
        except Exception:
            unified_data = {}
    else:
        unified_data = {}

    # Resolve recording file
    recording_path: Optional[Path]
    if args.recording:
        recording_path = Path(args.recording).resolve()
    else:
        default_rec_dir = Path(__file__).resolve().parents[3] / "only_test" / "testcases" / "generated"
        recording_path = _find_latest_recording(default_rec_dir)

    recording_steps: List[Dict[str, Any]] = []
    if recording_path and recording_path.exists():
        recording_steps = _load_json_or_jsonl(recording_path)

    # Gather screenshots
    screenshots = _collect_screenshots(session_dir)

    combined = {
        "session": unified_data.get("session_id") or session_dir.name,
        "unified": unified_data,
        "recording_steps": recording_steps,
        "screenshots": screenshots,
    }

    out_json = session_dir / "session_unified_with_recording.json"
    out_json.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    # Emit minimal viewer
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>Only-Test Playground</title>
  <style>
    body {{ font-family: sans-serif; display: flex; gap: 16px; }}
    #left {{ width: 35%; max-height: 95vh; overflow: auto; border-right: 1px solid #ddd; padding-right: 8px; }}
    #right {{ flex: 1; }}
    .step {{ padding: 6px; border-bottom: 1px solid #eee; cursor: pointer; }}
    .step:hover {{ background: #f5f5f5; }}
    .meta {{ color: #666; font-size: 12px; }}
    canvas {{ max-width: 100%; border: 1px solid #ddd; }}
  </style>
  </head>
<body>
  <div id=\"left\"></div>
  <div id=\"right\">
    <div class=\"meta\" id=\"meta\"></div>
    <img id=\"shot\" style=\"max-width:100%; display:none;\" />
    <canvas id=\"cv\"></canvas>
  </div>
  <script>
    async function load() {{
      const resp = await fetch('session_unified_with_recording.json');
      const data = await resp.json();
      const left = document.getElementById('left');
      const meta = document.getElementById('meta');
      const cv = document.getElementById('cv');
      const shot = document.getElementById('shot');
      const steps = data.recording_steps || [];
      const shots = data.screenshots || {{}};

      function rowText(s) {{
        const sel = (s.target && s.target.priority_selectors || []).map(o => Object.entries(o).map(([k,v])=>`${{k}}=${{v}}`).join(':')).join(' | ');
        const b = s.target && s.target.bounds_px ? s.target.bounds_px.join(',') : '';
        return `[${{s.action||''}}] ${{sel}} ${{b}}`;
      }}

      steps.forEach((s, idx) => {{
        const div = document.createElement('div');
        div.className = 'step';
        div.textContent = rowText(s);
        div.onclick = async () => {{
          // Find screenshot by index (1-based in logger)
          const shotPath = shots[idx+1];
          meta.textContent = `Step #${{idx+1}} ` + rowText(s) + (shotPath? ` | ${shotPath}`: '');
          if (!shotPath) {{ cv.style.display='none'; shot.style.display='none'; return; }}
          shot.src = shotPath;
          await new Promise(r=> shot.onload=r);
          // Draw to canvas
          cv.width = shot.naturalWidth; cv.height = shot.naturalHeight; cv.style.display='block'; shot.style.display='none';
          const ctx = cv.getContext('2d');
          ctx.drawImage(shot, 0, 0);
          const b = s.target && s.target.bounds_px; if (b && b.length===4) {{
            const [l,t,r,bm] = b; ctx.strokeStyle='#ff3b30'; ctx.lineWidth=3; ctx.strokeRect(l, t, r-l, bm-t);
          }}
        }};
        left.appendChild(div);
      }});
    }}
    load();
  </script>
</body>
</html>
"""
    (session_dir / "playground.html").write_text(html, encoding="utf-8")
    print(f"Playground generated: {out_json}")
    print(f"Open in browser: {(session_dir / 'playground.html').as_posix()}")


if __name__ == "__main__":
    main()

