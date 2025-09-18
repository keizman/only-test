import json, re

def _sanitize_json_str(s: str) -> str:
    s = s.strip()
    if s.startswith('```json'):
        s = s[7:]
    if s.startswith('```'):
        s = s[3:]
    if s.endswith('```'):
        s = s[:-3]
    s = re.sub(r"(^|\n)\s*//.*?(?=\n|$)", "\n", s)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s.strip()

def _split_json_objects_by_braces(s: str) -> list:
    s = _sanitize_json_str(s)
    objs = []
    depth = 0
    start = None
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            if depth > 0:
                depth -= 1
            if depth == 0 and start is not None:
                objs.append(s[start:i+1])
                start = None
        i += 1
    if not objs:
        depth = 0; start = None
        i = 0
        while i < len(s):
            ch = s[i]
            if ch == '[':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == ']':
                if depth > 0:
                    depth -= 1
                if depth == 0 and start is not None:
                    objs.append(s[start:i+1])
                    start = None
            i += 1
    return objs if objs else ([s] if s else [])

def _safe_json_load(candidate: str):
    try:
        return True, json.loads(_sanitize_json_str(candidate))
    except Exception as e:
        return False, str(e)

def _pick_best_candidate(cands: list, required_keys: list) -> dict:
    best = None
    errors = []
    for c in cands:
        ok, obj = _safe_json_load(c)
        if not ok:
            errors.append((c[:60], obj))
            continue
        if isinstance(obj, dict):
            if any((k in obj) for k in (required_keys or [])):
                return obj
            if best is None:
                best = obj
    return best or {}

def _extract_json_robust(content: str, kind: str = "generic", required_keys: list | None = None) -> dict:
    req = list(required_keys or [])
    cands = _split_json_objects_by_braces(content or "")
    obj = _pick_best_candidate(cands, req)
    return obj if isinstance(obj, dict) else {}

def _extract_plan(content: str, fallback_max_rounds: int = 6, objective: str = "") -> dict:
    req = ["plan_id", "objective", "steps"]
    obj = _extract_json_robust(content, kind="plan", required_keys=req)
    if not isinstance(obj, dict) or not obj:
        return {"plan_id": "plan_default", "objective": objective[:120], "keyword": "", "max_rounds": fallback_max_rounds, "steps": []}
    obj.setdefault("plan_id", "plan_default")
    obj.setdefault("objective", objective)
    obj.setdefault("keyword", "")
    try:
        obj["max_rounds"] = int(obj.get("max_rounds", fallback_max_rounds))
    except Exception:
        obj["max_rounds"] = int(fallback_max_rounds)
    if not isinstance(obj.get("steps"), list):
        obj["steps"] = []
    return obj

def test_case(name, content, kind, required_keys=None, is_plan=False):
    print(f"\n=== {name} ===")
    if is_plan:
        obj = _extract_plan(content, fallback_max_rounds=6, objective="OBJ")
    else:
        obj = _extract_json_robust(content, kind=kind, required_keys=required_keys or [])
    print(json.dumps(obj, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    # 1) 正常单对象
    test_case("single_object", '{"a":1}', kind="generic")
    # 2) fenced + 注释 + 尾逗号
    test_case("fenced_comments_trailing", """```json
    { // hi
      ""k"": [1,2,],
      ""v"": ""ok"", 
    }
    ```""".replace('""', '"'), kind="generic")
    # 3) 串联两个对象（先plan，后step）
    concatenated = '{"plan_id":"p1","objective":"OBJ","steps":[]}{"next_action":{"action":"click","target":{"priority_selectors":[{"resource_id":"rid"}]}}}'
    test_case("concatenated_plan_then_step", concatenated, kind="step", required_keys=["next_action","tool_request"])
    # 4) 串联两个对象（先step，后垃圾文本）
    concatenated2 = '{"next_action":{"action":"input","target":{"priority_selectors":[{"text":"abc"}]}}} EXTRA JUNK'
    test_case("concatenated_step_then_junk", concatenated2, kind="step", required_keys=["next_action","tool_request"])
    # 5) 只有数组顶层
    test_case("array_top", '[{"x":1},{"y":2}]', kind="generic")
    # 6) plan 完整
    plan_ok = '{"plan_id":"plan_1","objective":"OBJ","keyword":"K","max_rounds":8,"steps":[{"intent":"s","action":"click"}]}'
    test_case("plan_ok", plan_ok, kind="plan", is_plan=True)
    # 7) plan 缺字段
    plan_missing = '{"plan_id":"plan_2"}'
    test_case("plan_missing", plan_missing, kind="plan", is_plan=True)
    # 8) completion 含 execution_path
    completion = '{"execution_path":[{"step":1,"action":"click"}],"assertions":[]}'
    test_case("completion_exec_path", completion, kind="completion", required_keys=["execution_path","steps"])
    # 9) step 带 tool_request
    step_tool = '{"tool_request":{"name":"analyze_current_screen","params":{},"reason":"need refresh"}}'
    test_case("step_with_tool_request", step_tool, kind="step", required_keys=["next_action","tool_request"]) 
