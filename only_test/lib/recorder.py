#!/usr/bin/env python3
"""
Only-Test Action Recorder
=========================

Purpose
- Hook common interaction APIs (Poco UIObjectProxy.click, Poco.click_px/norm, Airtest touch/text/swipe)
- Persist robust, replayable step evidence: selectors + bounds + coordinates
- Improve recording stability by capturing multiple fallback strategies

Design
- Global, opt-in recorder (enable via ONLY_TEST_RECORD=1 or programmatic start())
- Output format: JSON array file by default (steps[]). Backward compatible reader for JSONL if needed.
- Best-effort context enrichment without heavy dependencies

Usage
-----
from only_test.lib.recorder import start_recording, install_poco_hooks, install_airtest_hooks
start_recording(device_id="192.168.0.101:5555")
install_poco_hooks(poco_instance)
install_airtest_hooks()  # after importing only_test.lib.airtest_compat

Notes
- Hooks are idempotent; repeated installs are no-ops
- Recording adds minimal latency and avoids screenshots by default
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---- Recorder core ---------------------------------------------------------


_RECORDER_LOCK = threading.Lock()
_RECORDER: Optional["ActionRecorder"] = None


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _norm_coord_from_px(x_px: float, y_px: float, screen: Tuple[int, int]) -> Tuple[float, float]:
    w, h = screen
    if w <= 0 or h <= 0:
        return 0.0, 0.0
    return max(0.0, min(1.0, x_px / float(w))), max(0.0, min(1.0, y_px / float(h)))


def _px_from_norm(x: float, y: float, screen: Tuple[int, int]) -> Tuple[int, int]:
    w, h = screen
    return int(max(0.0, min(1.0, x)) * max(1, w)), int(max(0.0, min(1.0, y)) * max(1, h))


@dataclass
class RecordedTarget:
    priority_selectors: List[Dict[str, str]]
    bounds_px: Optional[List[int]]
    center_norm: Optional[List[float]]
    center_px: Optional[List[int]]
    element_class: Optional[str] = None
    clickable: Optional[bool] = None


@dataclass
class RecordedStep:
    ts: str
    action: str  # click|input|swipe|press|wait|launch|restart|...
    page: Optional[str]
    success: Optional[bool]
    target: Optional[RecordedTarget]
    data: Optional[Any] = None
    source: Optional[str] = None  # uiobject|poco|airtest
    reason: Optional[str] = None


class ActionRecorder:
    def __init__(self, output_dir: Path, device_id: Optional[str] = None) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.device_id = device_id
        self.session_name = f"record_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # Default JSON array file
        self.json_path = self.output_dir / f"{self.session_name}.json"
        # Optional JSONL mirror if enabled by env
        self._write_jsonl = str(os.getenv("ONLY_TEST_RECORD_JSONL", "")).strip() in ("1", "true", "True")
        self.jsonl_path = self.output_dir / f"{self.session_name}.jsonl"
        # In-memory steps buffer
        self._steps: List[Dict[str, Any]] = []
        self._file_lock = threading.Lock()

    # ---- persist
    def append(self, obj: Dict[str, Any]) -> None:
        with self._file_lock:
            # Update in-memory list
            self._steps.append(obj)
            # Write JSON array (canonical)
            try:
                tmp = {"session": self.session_name, "device_id": self.device_id, "steps": self._steps}
                self.json_path.write_text(json.dumps(tmp, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                # Never break the main flow on recording failure
                pass
            # Optional JSONL mirror
            if self._write_jsonl:
                try:
                    line = json.dumps(obj, ensure_ascii=False)
                    with open(self.jsonl_path, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                except Exception:
                    pass

    # ---- public record APIs
    def record_click_from_proxy(self, proxy: Any, poco: Any, *, success: Optional[bool] = None, reason: Optional[str] = None) -> None:
        try:
            # Extract selectors & geometry from UIObjectProxy
            selectors: List[Dict[str, str]] = []
            try:
                rid = proxy.attr("resourceId")
                if rid:
                    selectors.append({"resource_id": str(rid)})
            except Exception:
                pass
            try:
                txt = proxy.get_text()
                if txt:
                    selectors.append({"text": str(txt)})
            except Exception:
                pass
            # Some ROMs expose content-desc as "description" or "contentDescription"
            for key in ("description", "contentDescription"):
                try:
                    val = proxy.attr(key)
                    if val:
                        selectors.append({"content_desc": str(val)})
                        break
                except Exception:
                    pass

            # Geometry
            try:
                w, h = (poco.get_screen_size() if hasattr(poco, "get_screen_size") else (1080, 1920))
            except Exception:
                w, h = 1080, 1920
            try:
                cx, cy = proxy.get_position("center")
            except Exception:
                cx, cy = 0.5, 0.5
            try:
                bounds_norm = proxy.get_bounds()  # [t, r, b, l] in norm per poco impl
                # Convert to px [left, top, right, bottom]
                # Poco bounds is [t,r,b,l]; convert ordering
                t, r, b, l = bounds_norm
                bounds_px = [int(l * w), int(t * h), int(r * w), int(b * h)]
            except Exception:
                bounds_px = None

            element_class = None
            clickable = None
            try:
                element_class = proxy.attr("type")
            except Exception:
                pass
            try:
                clickable = proxy.attr("clickable")
            except Exception:
                pass

            target = RecordedTarget(
                priority_selectors=selectors,
                bounds_px=bounds_px,
                center_norm=[float(cx), float(cy)],
                center_px=list(_px_from_norm(cx, cy, (w, h))),
                element_class=str(element_class) if element_class else None,
                clickable=bool(clickable) if clickable is not None else None,
            )

            step = RecordedStep(
                ts=_now_iso(),
                action="click",
                page=None,
                success=success,
                target=target,
                data=None,
                source="uiobject",
                reason=reason,
            )
            self.append(asdict(step))
        except Exception:
            # Recording must never crash the main flow
            return

    def record_click_by_coord(self, *, x: float, y: float, coord_type: str, poco: Optional[Any] = None,
                               success: Optional[bool] = None, reason: Optional[str] = None) -> None:
        try:
            w, h = (poco.get_screen_size() if (poco and hasattr(poco, "get_screen_size")) else (1080, 1920))
        except Exception:
            w, h = 1080, 1920

        if coord_type == "px":
            nx, ny = _norm_coord_from_px(float(x), float(y), (w, h))
            cx_px = (int(x), int(y))
        else:
            nx, ny = float(x), float(y)
            cx_px = _px_from_norm(nx, ny, (w, h))

        selectors: List[Dict[str, str]] = []
        bounds_px: Optional[List[int]] = None
        # Best-effort element attribution (optional)
        try:
            if poco is not None:
                # Lazy import local helper to avoid heavy dependencies if not installed
                from Poco.tool import CoordElementFinder  # type: ignore

                finder = CoordElementFinder(poco)
                info = finder.get_element_by_coord([nx, ny], coord_type="normalized")
                if info:
                    rid = info.get("resourceId")
                    txt = info.get("text")
                    name = info.get("name")
                    if rid:
                        selectors.append({"resource_id": str(rid)})
                    if txt:
                        selectors.append({"text": str(txt)})
                    # Some dumps map name->content_desc; include as content_desc if available
                    if name:
                        selectors.append({"content_desc": str(name)})
                    # bounds
                    pos = info.get("pos") or [nx, ny]
                    size = info.get("size") or [0.0, 0.0]
                    l = (pos[0] - size[0] / 2.0) * w
                    t = (pos[1] - size[1] / 2.0) * h
                    r = (pos[0] + size[0] / 2.0) * w
                    b = (pos[1] + size[1] / 2.0) * h
                    bounds_px = [int(l), int(t), int(r), int(b)]
        except Exception:
            pass

        target = RecordedTarget(
            priority_selectors=selectors,
            bounds_px=bounds_px,
            center_norm=[nx, ny],
            center_px=list(cx_px),
        )
        step = RecordedStep(
            ts=_now_iso(),
            action="click",
            page=None,
            success=success,
            target=target,
            data=None,
            source="poco" if poco is not None else "airtest",
            reason=reason,
        )
        self.append(asdict(step))

    def record_input(self, text_value: str, *, success: Optional[bool] = None, reason: Optional[str] = None) -> None:
        step = RecordedStep(
            ts=_now_iso(),
            action="input",
            page=None,
            success=success,
            target=None,
            data={"text": text_value},
            source="airtest",
            reason=reason,
        )
        self.append(asdict(step))


# ---- Public control --------------------------------------------------------


def start_recording(device_id: Optional[str] = None, output_dir: Optional[str] = None) -> ActionRecorder:
    """Initialize and enable the global recorder (idempotent)."""
    global _RECORDER
    with _RECORDER_LOCK:
        if _RECORDER is not None:
            return _RECORDER
        out_dir = Path(output_dir or "only_test/testcases/generated").resolve()
        _RECORDER = ActionRecorder(out_dir, device_id=device_id)
        return _RECORDER


def get_recorder() -> Optional[ActionRecorder]:
    return _RECORDER


# ---- Hook installers -------------------------------------------------------


_POCO_HOOKED = False


def install_poco_hooks(poco_instance: Any) -> None:
    """Patch Poco UIObjectProxy.click and Poco.click methods to record actions.

    Safe to call multiple times.
    """
    global _POCO_HOOKED
    if _POCO_HOOKED:
        return

    try:
        from Poco.poco.proxy import UIObjectProxy  # local vendored Poco
        from Poco.poco.pocofw import Poco as PocoFW
    except Exception:
        # If local Poco path is not in sys.path, user may not rely on our local copy
        try:
            from poco.proxy import UIObjectProxy  # type: ignore
            from poco.pocofw import Poco as PocoFW  # type: ignore
        except Exception:
            return

    # UIObjectProxy.click
    if not hasattr(UIObjectProxy, "_onlytest_orig_click"):
        UIObjectProxy._onlytest_orig_click = UIObjectProxy.click  # type: ignore[attr-defined]

        def _wrapped_click(self, focus=None, sleep_interval=None):  # type: ignore[override]
            rec = get_recorder()
            success = None
            try:
                result = UIObjectProxy._onlytest_orig_click(self, focus, sleep_interval)  # type: ignore[attr-defined]
                success = True
                return result
            except Exception:
                success = False
                raise
            finally:
                if rec is not None:
                    try:
                        rec.record_click_from_proxy(self, getattr(self, "poco", None), success=success)
                    except Exception:
                        pass

        UIObjectProxy.click = _wrapped_click  # type: ignore[assignment]

    # Poco.click (normalized coords) and Poco.click_px
    if not hasattr(PocoFW, "_onlytest_orig_click"):
        PocoFW._onlytest_orig_click = PocoFW.click  # type: ignore[attr-defined]

        def _wrapped_poco_click(self, pos_in_percentage):  # type: ignore[override]
            rec = get_recorder()
            success = None
            try:
                result = PocoFW._onlytest_orig_click(self, pos_in_percentage)  # type: ignore[attr-defined]
                success = True
                return result
            except Exception:
                success = False
                raise
            finally:
                if rec is not None:
                    try:
                        x, y = pos_in_percentage
                        rec.record_click_by_coord(x=float(x), y=float(y), coord_type="norm", poco=self, success=success)
                    except Exception:
                        pass

        PocoFW.click = _wrapped_poco_click  # type: ignore[assignment]

    if not hasattr(PocoFW, "_onlytest_orig_click_px"):
        PocoFW._onlytest_orig_click_px = getattr(PocoFW, "click_px", None)
        if PocoFW._onlytest_orig_click_px is not None:
            def _wrapped_poco_click_px(self, x_px, y_px):  # type: ignore[override]
                rec = get_recorder()
                success = None
                try:
                    result = PocoFW._onlytest_orig_click_px(self, x_px, y_px)  # type: ignore[attr-defined]
                    success = True
                    return result
                except Exception:
                    success = False
                    raise
                finally:
                    if rec is not None:
                        try:
                            rec.record_click_by_coord(x=float(x_px), y=float(y_px), coord_type="px", poco=self, success=success)
                        except Exception:
                            pass

            PocoFW.click_px = _wrapped_poco_click_px  # type: ignore[assignment]

    _POCO_HOOKED = True


_AIRTEST_HOOKED = False


def install_airtest_hooks() -> None:
    """Patch Airtest touch/text/swipe imported via our compatibility layer.

    Safe to call multiple times.
    """
    global _AIRTEST_HOOKED
    if _AIRTEST_HOOKED:
        return

    try:
        # Our compat layer re-exports airtest.core.api symbols
        from only_test.lib import airtest_compat as ap
    except Exception:
        return

    # touch
    if not hasattr(ap, "_onlytest_orig_touch") and hasattr(ap._air_api, "touch"):
        ap._onlytest_orig_touch = ap._air_api.touch  # type: ignore[attr-defined]

        def _wrapped_touch(v, times=1, **kwargs):  # noqa: ANN001 - match Airtest API
            rec = get_recorder()
            success = None
            # Attempt to resolve coordinates when tuple/list provided; Templates are opaque (skip selector inference)
            is_xy = isinstance(v, (list, tuple)) and len(v) >= 2
            try:
                res = ap._onlytest_orig_touch(v, times=times, **kwargs)  # type: ignore[attr-defined]
                success = True
                return res
            except Exception:
                success = False
                raise
            finally:
                if rec is not None and is_xy:
                    try:
                        x, y = float(v[0]), float(v[1])
                        # Heuristic: treat <=1 as normalized coordinate
                        coord_type = "norm" if (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0) else "px"
                        poco = _resolve_default_poco_for_record()
                        rec.record_click_by_coord(x=x, y=y, coord_type=coord_type, poco=poco, success=success)
                    except Exception:
                        pass

        ap.touch = _wrapped_touch  # type: ignore[assignment]

    # text
    if not hasattr(ap, "_onlytest_orig_text") and hasattr(ap._air_api, "text"):
        ap._onlytest_orig_text = ap._air_api.text  # type: ignore[attr-defined]

        def _wrapped_text(v: str, **kwargs):
            rec = get_recorder()
            success = None
            try:
                res = ap._onlytest_orig_text(v, **kwargs)  # type: ignore[attr-defined]
                success = True
                return res
            except Exception:
                success = False
                raise
            finally:
                if rec is not None:
                    try:
                        rec.record_input(str(v), success=success)
                    except Exception:
                        pass

        ap.text = _wrapped_text  # type: ignore[assignment]

    _AIRTEST_HOOKED = True


_DEFAULT_POCO_FOR_RECORD_LOCK = threading.Lock()
_DEFAULT_POCO_FOR_RECORD: Optional[Any] = None


def _resolve_default_poco_for_record() -> Optional[Any]:
    global _DEFAULT_POCO_FOR_RECORD
    with _DEFAULT_POCO_FOR_RECORD_LOCK:
        if _DEFAULT_POCO_FOR_RECORD is not None:
            return _DEFAULT_POCO_FOR_RECORD
        try:
            # Lazy import; avoid hard dependency if Poco not available
            from only_test.lib.poco_utils import get_android_poco

            _DEFAULT_POCO_FOR_RECORD = get_android_poco()
            return _DEFAULT_POCO_FOR_RECORD
        except Exception:
            return None


# ---- Auto-enable on env flag ----------------------------------------------


def _auto_enable_from_env() -> None:
    if os.getenv("ONLY_TEST_RECORD", "").strip() not in ("1", "true", "True"):  # opt-in only
        return
    dev = os.getenv("ONLY_TEST_DEVICE_ID") or None
    rec = start_recording(device_id=dev)
    # Persist a session header line for visibility
    try:
        rec.append({
            "ts": _now_iso(),
            "type": "recording_session",
            "session": rec.session_name,
            "device_id": rec.device_id,
            "pid": os.getpid(),
        })
    except Exception:
        pass


_auto_enable_from_env()
