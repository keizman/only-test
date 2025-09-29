#!/usr/bin/env python3
"""
JSON到Python测试用例转换器

将智能元数据JSON转换为可执行的Python测试文件
支持only_test + pytest + allure框架集成
"""

import json
import jinja2
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class JSONToPythonConverter:
    """JSON测试用例到Python代码转换器"""
    
    def __init__(self, templates_dir: str = "templates"):
        self._target_app: Optional[str] = None
        self._device_serial: Optional[str] = None
        self._style: str = "pytest"  # 默认风格：pytest+allure
        """
        初始化转换器
        
        Args:
            templates_dir: Jinja2模板文件目录
        """
        self.templates_dir = Path(__file__).parent / templates_dir
        self.templates_dir.mkdir(exist_ok=True)
        
        # 初始化Jinja2环境
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # 创建默认模板
        self._create_default_templates()
    
    def convert_json_to_python(self, json_file: str, output_file: Optional[str] = None) -> str:
        """
        转换JSON测试用例为Python文件
        
        Args:
            json_file: 输入的JSON文件路径
            output_file: 输出的Python文件路径（可选）
            
        Returns:
            str: 生成的Python文件路径
        """
        # 加载JSON数据
        with open(json_file, 'r', encoding='utf-8') as f:
            testcase_data = json.load(f)
        
        # 生成输出文件名
        if output_file is None:
            json_path = Path(json_file)
            output_file = str(json_path.parent / f"test_{json_path.stem}.py")
        
        # 转换为Python代码
        python_code = self._generate_python_code(testcase_data)
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(python_code)
            
        return output_file
    
    def _generate_python_code(self, testcase_data: Dict[str, Any]) -> str:
        """
        根据JSON数据生成Python代码
        
        Args:
            testcase_data: JSON测试用例数据
            
        Returns:
            str: 生成的Python代码
        """
        # 保存上下文：target_app 与 device adb serial（若提供）
        self._target_app = testcase_data.get("target_app")
        dev_info = testcase_data.get("device_info") or {}
        if isinstance(dev_info, dict):
            self._device_serial = dev_info.get("adb_serial") or dev_info.get("device_id")
        else:
            self._device_serial = None
        # 兼容历史：若顶层误放置 device_id，也兜底使用
        if not self._device_serial and isinstance(testcase_data.get("device_id"), str):
            self._device_serial = testcase_data.get("device_id")

        # 风格选择：pytest（默认）或 recorded（Airtest录制风格）
        metadata = testcase_data.get("metadata", {}) if isinstance(testcase_data.get("metadata"), dict) else {}
        presentation = testcase_data.get("presentation_hints", {}) if isinstance(testcase_data.get("presentation_hints"), dict) else {}
        # 优先使用 presentation_hints.style，其次 metadata.style，再次顶层 style
        self._style = (presentation.get("style") or metadata.get("style") or testcase_data.get("style") or "pytest").lower()

        # 解析执行路径
        execution_steps = self._parse_execution_path(testcase_data.get("execution_path", []))
        
        # 解析断言
        assertions = self._parse_assertions(testcase_data.get("assertions", []))
        
        # 准备模板数据
        # 设备连接URI（若提供adb_serial）
        device_connection = ""
        if isinstance(self._device_serial, str) and self._device_serial.strip():
            device_connection = f"android://127.0.0.1:5037/{self._device_serial}?touch_method=ADBTOUCH&"

        # path 与 tags（用于 recorded 风格注释）
        page_scope = metadata.get("page_scope") if isinstance(metadata.get("page_scope"), list) else []
        path_scope = " -> ".join(page_scope) if page_scope else None
        tags = ", ".join(metadata.get("tags", [])) if isinstance(metadata.get("tags"), list) else ""

        # app_id（仅在 recorded 风格中用于 get_android_poco）
        app_id = "brav_mob" if (self._target_app == "com.mobile.brasiltvmobile") else None

        template_data = {
            "testcase_id": testcase_data.get("testcase_id"),
            "testcase_name": testcase_data.get("name"),
            "description": testcase_data.get("description"),
            "target_app": testcase_data.get("target_app"),
            "variables": testcase_data.get("variables", {}),
            "metadata": metadata,
            "device_connection": device_connection,
            "device_serial": self._device_serial or "",
            "path_scope": path_scope,
            "tags": tags,
            "app_id": app_id,
            "execution_steps": execution_steps,
            "assertions": assertions,
            "generation_info": {
                "generated_at": datetime.now().isoformat(),
                "original_json": testcase_data.get("generated_from_template"),
                "conversion_method": "json_to_python_converter"
            }
        }
        
        # 使用模板生成代码
        # 若提供 v2 结构（hooks/test_steps），使用新解析流程
        if isinstance(testcase_data.get("test_steps"), list) or isinstance(testcase_data.get("hooks"), dict):
            execution_steps = self._generate_from_v2(testcase_data)
            template_data["execution_steps"] = execution_steps

        template_name = "pytest_airtest_template.py.j2" if self._style != "recorded" else "airtest_record_style.py.j2"
        template = self.jinja_env.get_template(template_name)
        return template.render(**template_data)
    
    def _parse_execution_path(self, execution_path: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析执行路径，特别处理条件逻辑
        
        Args:
            execution_path: 执行路径数据
            
        Returns:
            List: 解析后的执行步骤
        """
        parsed_steps = []
        
        for step in execution_path:
            action = step.get("action")
            
            if action == "conditional_action":
                # 处理条件逻辑
                parsed_step = self._parse_conditional_action(step)
            else:
                # 处理普通操作
                parsed_step = self._parse_regular_action(step)
            
            parsed_steps.append(parsed_step)
        
        return parsed_steps
    
    def _parse_conditional_action(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析条件动作
        
        Args:
            step_data: 步骤数据
            
        Returns:
            Dict: 解析后的条件步骤
        """
        condition = step_data.get("condition", {})
        conditional_paths = step_data.get("conditional_paths", {})
        check_type = condition.get("check", "has_text_content")
        
        # 生成条件检查代码和变量名
        condition_code = self._generate_condition_code(condition)
        
        # 根据检查类型确定条件变量名
        if check_type == "has_text_content":
            condition_var = "has_content"
        elif check_type == "is_empty":
            condition_var = "is_empty"
        else:
            condition_var = "condition_result"
        
        # 生成条件分支代码
        if_branch = conditional_paths.get("if_has_content") or conditional_paths.get("if_true")
        else_branch = conditional_paths.get("if_empty") or conditional_paths.get("if_false")
        
        return {
            "type": "conditional",
            "step_number": step_data.get("step"),
            "description": step_data.get("description"),
            "condition_code": condition_code,
            "condition_var": condition_var,
            "if_branch": self._generate_action_code(if_branch) if if_branch else None,
            "else_branch": self._generate_action_code(else_branch) if else_branch else None,
            "business_logic": step_data.get("business_logic"),
            "ai_hint": step_data.get("ai_hint")
        }
    
    def _parse_regular_action(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析普通动作
        
        Args:
            step_data: 步骤数据
            
        Returns:
            Dict: 解析后的步骤
        """
        action = step_data.get("action")
        target = step_data.get("target", {})
        
        return {
            "type": "regular",
            "step_number": step_data.get("step"),
            "action": action,
            "target": target,
            "description": step_data.get("description"),
            "success_criteria": step_data.get("success_criteria"),
            "timeout": step_data.get("timeout", 10),
            "wait_after": step_data.get("wait_after", None),
            "code": self._generate_action_code(step_data)
        }
    
    def _generate_condition_code(self, condition: Dict[str, Any]) -> str:
        """
        生成条件检查的Python代码
        
        Args:
            condition: 条件配置
            
        Returns:
            str: 生成的条件代码
        """
        condition_type = condition.get("type")
        target = condition.get("target", {})
        check = condition.get("check")
        params = condition.get("params", {})
        
        # 处理target可能是字符串的情况
        if isinstance(target, str):
            selectors = [{"resource_id": target}]
        else:
            selectors = target.get("priority_selectors", [])
        
        if condition_type == "element_content_check":
            if check == "has_text_content":
                return f"""
    # 智能检查搜索框状态
    element = find_element_by_priority_selectors({selectors})
    has_content = bool(element and element.get_text() and len(element.get_text().strip()) > 0)
    allure.attach(f"搜索框内容检查: {{'has_content': has_content, 'element_found': bool(element)}}", name="条件判断结果")
"""
            elif check == "is_empty":
                return f"""
    # 检查搜索框是否为空
    element = find_element_by_priority_selectors({selectors})
    is_empty = not bool(element and element.get_text() and len(element.get_text().strip()) > 0)
    allure.attach(f"搜索框空值检查: {{'is_empty': is_empty, 'element_found': bool(element)}}", name="条件判断结果")
"""
        
        return "# 条件检查代码待实现"
    
    def _generate_action_code(self, action_data: Dict[str, Any]) -> str:
        """
        生成动作的Python代码
        
        Args:
            action_data: 动作数据
            
        Returns:
            str: 生成的Python代码
        """
        if not action_data:
            return ""
            
        action = action_data.get("action")
        target = action_data.get("target")
        
        # 处理target类型
        if isinstance(target, str):
            selectors = [{"resource_id": target}]
        elif isinstance(target, dict):
            selectors = target.get("priority_selectors", target.get("selectors", []))
        else:
            selectors = []

        # 辅助：生成 recorded 风格的 poco 调用串
        def _build_poco_selector(sel_list: List[Dict[str, Any]]) -> str:
            res_id = None
            txt = None
            desc = None
            cls = None
            if isinstance(sel_list, list):
                for s in sel_list:
                    if not isinstance(s, dict):
                        continue
                    if (not res_id) and (s.get("resource_id")):
                        res_id = s.get("resource_id")
                    if (not txt) and (s.get("text")):
                        txt = s.get("text")
                    if (not desc) and (s.get("content_desc")):
                        desc = s.get("content_desc")
                    if (not cls) and (s.get("class")):
                        cls = s.get("class")
            parts = []
            if res_id:
                parts.append(f'resourceId=\"{res_id}\"')
            if txt:
                if txt == 'program_name':
                    parts.append('text=program_name')
                else:
                    parts.append(f'text=\"{txt}\"')
            if desc and not txt:
                # 仅在未使用 text 时加入 desc 以避免歧义
                parts.append(f'desc="{desc}"')
            if cls and not res_id and not txt:
                parts.append(f'type="{cls}"')
            if not parts:
                return 'text=""'
            return ", ".join(parts)

        # recorded 风格
        if self._style == "recorded":
            # 可选的等待（严格来自 JSON）
            wait_prefix = ""
            wait_suffix = ""
            try:
                w = action_data.get("wait") or {}
                if isinstance(w, dict):
                    if w.get("before") is not None:
                        wb = float(w.get("before"))
                        wb_val = int(wb) if wb.is_integer() else wb
                        wait_prefix = f"sleep({wb_val})\n"
                    if w.get("after") is not None:
                        wa = float(w.get("after"))
                        wa_val = int(wa) if wa.is_integer() else wa
                        wait_suffix = f"\nsleep({wa_val})"
            except Exception:
                pass

            def _inject_notes(code: str) -> str:
                notes = action_data.get("notes") or []
                if isinstance(notes, list) and notes:
                    notes_block = "".join([f"\n# {str(n)}" for n in notes])
                    return f"{code}{notes_block}"
                return code

            # 将注释使用 comment 字段优先
            def _with_header(body: str, action_label: str) -> str:
                page = action_data.get('page','')
                comment = action_data.get('comment') or action_data.get('description','')
                header = f"## [page] {page}, [action] {action_label}, [comment] {comment}\n"
                # restart/launch/wait 的 sleep 已在正文实现或应由正文控制，不再在前后追加
                exclude_wait_labels = ("restart", "launch", "wait")
                pre = "" if action_label in exclude_wait_labels else wait_prefix
                post = "" if action_label in exclude_wait_labels else wait_suffix
                return f"{pre}{header}{_inject_notes(body)}{post}"

            if action == "click" or action == "click_with_bias":
                bias = {}
                try:
                    bias = (action_data.get("target") or {}).get("bias") or {}
                except Exception:
                    bias = {}
                call = "click()"
                if isinstance(bias, dict) and ("dy_px" in bias or "dx_px" in bias):
                    dy = int(bias.get("dy_px", 0))
                    dx = int(bias.get("dx_px", 0))
                    args = ", ".join([p for p in [f'dx_px={dx}' if dx else '', f'dy_px={dy}' if dy else ''] if p])
                    call = f"click_with_bias({args})" if args else "click()"
                sel = _build_poco_selector(selectors)
                # 若为首页搜索按钮，附带一次层级缓存刷新提示（注释形式），与录制风格一致
                extra = "\n# poco.agent.hierarchy.dumper.invalidate_cache()" if "mVodImageSearch" in sel else ""
                # search_result 页面点击时若有文本约束，使用 program_name 变量以贴合录制稿
                if (action_data.get('page') == 'search_result') and ('text="' in sel):
                    # 将 text="..." 替换为 text=program_name
                    import re as _re
                    sel = _re.sub(r'text=\".*?\"', 'text=program_name', sel)
                body = f"poco({sel}).{call}{extra}"
                return _with_header(body, "click")
            elif action == "input":
                data = action_data.get("data", "")
                submit_method = None
                text_value = ""
                if isinstance(data, dict):
                    submit_method = data.get("submit_method")
                    text_value = data.get("text", "")
                else:
                    text_value = data if isinstance(data, str) else ""
                # 变量占位直接渲染为字面量，符合录制风格
                text_literal = text_value
                sel = _build_poco_selector(selectors)
                submit = "\nkeyevent('ENTER')" if isinstance(submit_method, str) and submit_method.lower() == "enter" else ""
                body = f"res_for_set = poco({sel}).set_text(program_name){submit}"
                return _with_header(body, "input")
            elif action == "press":
                # 键盘事件，例如 Enter
                key = None
                try:
                    key = ((action_data.get("target") or {}).get("keyevent") or "").upper()
                except Exception:
                    key = ""
                key = key or "ENTER"
                body = f"keyevent('{key}')"
                return _with_header(body, "press")
            elif action == "wait_for_elements":
                timeout = action_data.get("timeout", 10)
                wait_after = action_data.get("wait_after", None)
                disappearance = False
                try:
                    disappearance = bool((action_data.get("target") or {}).get("disappearance", False))
                except Exception:
                    disappearance = False
                primary = (selectors[0] if selectors else {})
                if disappearance:
                    if isinstance(primary, dict) and "text" in primary:
                        sel_code = f"poco(text=\"{primary['text']}\")"
                    elif isinstance(primary, dict) and "resource_id" in primary:
                        sel_code = f"poco(resourceId=\"{primary['resource_id']}\")"
                    elif isinstance(primary, dict) and "content_desc" in primary:
                        sel_code = f"poco(desc=\"{primary['content_desc']}\")"
                    else:
                        sel_code = None
                    # 规范 sleep 数字格式（与录制稿一致：整数不带小数）
                    if isinstance(wait_after, (int, float)):
                        _af = int(wait_after) if float(wait_after).is_integer() else float(wait_after)
                        after = f"\nsleep({_af})"
                    else:
                        after = "\nsleep(2)"
                    if sel_code:
                        body = f"{sel_code}.wait_for_disappearance(timeout={int(timeout)}){after}"
                        return _with_header(body, "wait")
                # 出现等待（录制样式中少见，留作兜底）
                body = f"wait_for_element({selectors}, timeout={int(timeout)})"
                return _with_header(body, "wait")
            elif action == "launch":
                wait = action_data.get("timeout", 3)
                try:
                    w = action_data.get("wait") or {}
                    if isinstance(w, dict) and w.get("after") is not None:
                        wait = float(w.get("after"))
                except Exception:
                    pass
                app = self._target_app or ""
                body = f"start_app(\"{app}\")\n# wait app to start, that may take a few time based on phone performance\nsleep({int(wait)}) # APP 有启动动画, 需要等待"
                return _with_header(body, "launch")
            elif action == "restart":
                wait = action_data.get("timeout", 3)
                try:
                    w = action_data.get("wait") or {}
                    if isinstance(w, dict) and w.get("after") is not None:
                        wait = float(w.get("after"))
                except Exception:
                    pass
                app = self._target_app or ""
                # 注意：录制稿中该行注释固定为 app_initialization
                body = f"stop_app(\"{app}\")\n\nsleep({int(wait)})  # 等待应用完全关闭, 后台关闭需要时间"
                # 将 page 覆盖为 app_initialization 以匹配录制注释
                action_data = dict(action_data)
                action_data["page"] = action_data.get("page") or "app_initialization"
                return _with_header(body, "restart")
            # 工具类步骤（例如 close_ads）
            tool_name = action_data.get("tool_name") or action_data.get("tool")
            if isinstance(tool_name, str) and tool_name.lower() == "close_ads":
                params = action_data.get("params", {}) if isinstance(action_data.get("params"), dict) else {}
                mode = params.get("mode", "continuous")
                consecutive = int(params.get("consecutive_no_ad", 3))
                max_dur = float(params.get("max_duration", 20.0))
                tgt = (self._target_app or "")
                body = f"asyncio.run(close_ads(target_app=\"{tgt}\", mode=\"{mode}\", consecutive_no_ad={consecutive}, max_duration={max_dur}))"
                return _with_header(body, "close_ads")
            # 默认记录占位
            return f"# {action} 动作代码待实现\n"

        # pytest+allure 风格（原有实现）
        if action == "click":
            # 若提供 bias 则使用 click_with_bias
            bias = {}
            try:
                bias = (action_data.get("target") or {}).get("bias") or {}
            except Exception:
                bias = {}
            if isinstance(bias, dict) and ("dy_px" in bias or "dx_px" in bias):
                dy = int(bias.get("dy_px", 0))
                dx = int(bias.get("dx_px", 0))
                bias_call = f"element.click_with_bias({', '.join([p for p in [f'dx_px={dx}' if dx else '', f'dy_px={dy}' if dy else ''] if p])})"
            else:
                bias_call = "element.click()"
            return f"""
    # {action_data.get('reason', '执行点击操作')}
    element = find_element_by_priority_selectors({selectors})
    if element:
        {bias_call}
        allure.attach(screenshot(), name=\"点击后截图\", attachment_type=allure.attachment_type.PNG)
    else:
        raise Exception(\"未找到可点击元素（缺少有效选择器），请确保 JSON 中提供 priority_selectors 或 bounds_px\")
"""
        elif action == "input":
            data = action_data.get("data", "")
            submit_method = None
            text_value = ""
            if isinstance(data, dict):
                submit_method = data.get("submit_method")
                text_value = data.get("text", "")
                # 处理变量替换
                if isinstance(text_value, str) and text_value.startswith("${") and text_value.endswith("}"):
                    var_name = text_value[2:-1]
                    text_expr = f"VARIABLES.get('{var_name}', '{text_value}')"
                else:
                    text_expr = f"'{text_value}'"
            else:
                # 保持向后兼容：data 为字符串
                if isinstance(data, str) and data.startswith("${") and data.endswith("}"):
                    var_name = data[2:-1]
                    text_expr = f"VARIABLES.get('{var_name}', '{data}')"
                else:
                    text_expr = f"'{data}'"
            submit_code = ""
            if isinstance(submit_method, str) and submit_method.lower() == "enter":
                submit_code = "\n        keyevent('ENTER')"
            return f"""
    # {action_data.get('reason', '输入数据')}
    element = find_element_by_priority_selectors({selectors})
    if element:
        element.set_text({text_expr}){submit_code}
        allure.attach(screenshot(), name=\"输入后截图\", attachment_type=allure.attachment_type.PNG)
    else:
        raise Exception(\"未找到输入元素（缺少有效选择器），请确保 JSON 中提供 priority_selectors 或 bounds_px\")
"""
        elif action == "wait_for_elements":
            timeout = action_data.get("timeout", 10)
            # 支持 target.disappearance -> wait_for_disappearance
            disappearance = False
            try:
                disappearance = bool((action_data.get("target") or {}).get("disappearance", False))
            except Exception:
                disappearance = False
            if disappearance:
                # 选择首个selector生成消失等待
                primary = (selectors[0] if selectors else {})
                if isinstance(primary, dict) and "text" in primary:
                    sel_code = f"poco(text=\\\"{primary['text']}\\\")"
                elif isinstance(primary, dict) and "resource_id" in primary:
                    sel_code = f"poco(resourceId=\\\"{primary['resource_id']}\\\")"
                elif isinstance(primary, dict) and "content_desc" in primary:
                    sel_code = f"poco(desc=\\\"{primary['content_desc']}\\\")"
                else:
                    sel_code = None
                if sel_code:
                    return f"""
    # {action_data.get('description', '等待元素消失')}
    {sel_code}.wait_for_disappearance(timeout={timeout})
    allure.attach(screenshot(), name=\"等待完成截图\", attachment_type=allure.attachment_type.PNG)
"""
            # 默认出现等待
            return f"""
    # {action_data.get('description', '等待元素出现')}
    wait_for_element({selectors}, timeout={timeout})
    allure.attach(screenshot(), name=\"等待完成截图\", attachment_type=allure.attachment_type.PNG)
"""
        
        elif action == "launch":
            wait = action_data.get("timeout", 3)
            app = self._target_app or ""
            return f"""
    # {action_data.get('description', '启动应用')}
    start_app(\"{app}\")
    sleep({wait})
"""
        
        elif action == "restart":
            wait = action_data.get("timeout", 3)
            app = self._target_app or ""
            return f"""
    # {action_data.get('description', '重启应用')}
    stop_app(\"{app}\")
    sleep({wait})
"""
        
        # 工具类步骤（例如 close_ads）
        tool_name = action_data.get("tool_name") or action_data.get("tool")
        if isinstance(tool_name, str) and tool_name.lower() == "close_ads":
            params = action_data.get("params", {}) if isinstance(action_data.get("params"), dict) else {}
            mode = params.get("mode", "continuous")
            consecutive = int(params.get("consecutive_no_ad", 3))
            max_dur = float(params.get("max_duration", 20.0))
            dev = (self._device_serial or "")
            tgt = (self._target_app or "")
            return f"""
    # 关闭广告（工具步骤）
    import asyncio
    from only_test.lib.ad_closer import close_ads
    asyncio.run(close_ads(device_id=\"{dev}\", target_app=\"{tgt}\", mode=\"{mode}\", consecutive_no_ad={consecutive}, max_duration={max_dur}))
"""
        
        return f"# {action} 动作代码待实现"
    
    def _parse_assertions(self, assertions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析断言
        
        Args:
            assertions: 断言数据
            
        Returns:
            List: 解析后的断言
        """
        parsed_assertions = []
        
        for assertion in assertions:
            assertion_type = assertion.get("type")
            expected = assertion.get("expected")
            description = assertion.get("description")
            
            parsed_assertions.append({
                "type": assertion_type,
                "expected": expected,
                "description": description,
                "code": self._generate_assertion_code(assertion)
            })
        
        return parsed_assertions
    
    def _generate_assertion_code(self, assertion: Dict[str, Any]) -> str:
        """
        生成断言代码
        
        Args:
            assertion: 断言数据
            
        Returns:
            str: 生成的断言代码
        """
        assertion_type = assertion.get("type")
        expected = assertion.get("expected")
        description = assertion.get("description")
        
        if assertion_type == "check_search_results_exist":
            return f"""
    # {description}
    poco = AndroidUiautomationPoco(use_airtest_input=True)
    results_exist = poco("搜索结果").exists()
    assert results_exist, "搜索结果不存在"
    allure.attach(f"搜索结果验证: 预期={expected}, 实际={{results_exist}}", name="断言结果")
"""
        elif assertion_type == "check_results_count":
            expected_str = str(expected).replace('>= ', '') if isinstance(expected, str) else str(expected)
            return f"""
    # {description}
    poco = AndroidUiautomationPoco(use_airtest_input=True)
    results_count = len(poco("result_item"))
    assert results_count >= {expected_str}, f"搜索结果数量不足: 实际={{results_count}}, 预期>={expected}"
"""
        elif assertion_type == "check_content_relevance":
            return f"""
    # {description}
    poco = AndroidUiautomationPoco(use_airtest_input=True)
    content_found = poco(text="{expected}").exists()
    assert content_found, f"未找到相关内容: {expected}"
    allure.attach(f"内容相关性验证: 关键词={expected}, 找到={{content_found}}", name="断言结果")
"""
        
        return f"# {assertion_type} 断言代码待实现"
    
    def _create_default_templates(self):
        """创建默认的Jinja2模板"""
        # PyTest + Allure 模板
        template_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成的测试用例: {{ testcase_name }}
测试ID: {{ testcase_id }}
生成时间: {{ generation_info.generated_at }}
原始模板: {{ generation_info.original_json }}

描述: {{ description }}
"""

import pytest
import allure
from only_test.lib.airtest_compat import *
from airtest.core.android.android import Android
from airtest.core.cv import Template
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

# 测试元数据
TESTCASE_METADATA = {{ metadata | tojson(indent=2) }}
VARIABLES = {{ variables | tojson(indent=2) }}

def find_element_by_priority_selectors(selectors):
    """根据优先级选择器查找元素"""
    poco = AndroidUiautomationPoco(use_airtest_input=True)
    
    for selector in selectors:
        try:
            if "resource_id" in selector:
                element = poco(resourceId=selector["resource_id"])
            elif "text" in selector:
                element = poco(text=selector["text"])
            elif "content_desc" in selector:
                element = poco(desc=selector["content_desc"])
            elif "class" in selector:
                element = poco(type=selector["class"])
            else:
                continue
                
            if element.exists():
                return element
        except Exception:
            continue
    
    return None

def wait_for_element(selectors, timeout=10):
    """等待元素出现"""
    poco = AndroidUiautomationPoco(use_airtest_input=True)
    
    for selector in selectors:
        try:
            if "resource_id" in selector:
                poco(resourceId=selector["resource_id"]).wait_for_appearance(timeout=timeout)
                return True
        except Exception:
            continue
    
    return False

@allure.feature("{{ metadata.category or '功能测试' }}")
@allure.story("{{ testcase_name }}")
@allure.title("{{ description }}")
@allure.description("""
目标应用: {{ target_app }}
测试优先级: {{ metadata.priority or 'medium' }}
预估时长: {{ metadata.estimated_duration or 30 }}秒

业务描述: {{ description }}
""")
class Test{{ testcase_id.replace('-', '_').replace(' ', '_') }}:
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self):
        """测试前后置处理"""
        # 连接设备
        {% if device_connection %}
        connect_device("{{ device_connection }}")
        {% endif %}
        auto_setup(__file__)
        
        # 启动应用
        start_app("{{ target_app }}")
        sleep(3)
        
        # 拍摄初始截图
        allure.attach(screenshot(), name="测试开始截图", attachment_type=allure.attachment_type.PNG)
        
        yield
        
        # 清理工作
        allure.attach(screenshot(), name="测试结束截图", attachment_type=allure.attachment_type.PNG)
    
    @allure.severity(allure.severity_level.{% if metadata.priority == 'high' %}CRITICAL{% elif metadata.priority == 'low' %}MINOR{% else %}NORMAL{% endif %})
    def test_{{ testcase_id.lower().replace('-', '_').replace(' ', '_') }}_execution(self):
        """执行智能测试用例"""
        
        with allure.step("测试用例基本信息"):
            allure.attach(
                f"测试ID: {{ testcase_id }}\\n"
                f"测试名称: {{ testcase_name }}\\n"
                f"目标应用: {{ target_app }}\\n"
                f"生成方式: {{ generation_info.conversion_method }}",
                name="测试基本信息"
            )

        {% for step in execution_steps %}
        {% if step.type == 'conditional' %}
        with allure.step("Step {{ step.step_number }}: {{ step.description }}"):
            allure.attach("{{ step.business_logic or '执行条件判断' }}", name="业务逻辑说明")
            allure.attach("{{ step.ai_hint or '智能判断提示' }}", name="AI提示")
            
            # 执行条件检查{{ step.condition_code | indent(12, first=False) }}
            
            # 根据条件选择执行路径
            if {{ step.condition_var }}:
                with allure.step("条件分支: True时的处理"):{{ step.if_branch | indent(20, first=False) }}
            else:
                with allure.step("条件分支: False时的处理"):{{ step.else_branch | indent(20, first=False) }}

        {% else %}
        with allure.step("Step {{ step.step_number }}: {{ step.description }}"):
            allure.attach("{{ step.success_criteria or '执行标准操作' }}", name="成功标准")
            {{ step.code | indent(12, first=False) }}
            sleep(1)  # 操作间隔

        {% endif %}
        {% endfor %}
        
        # 执行断言验证
        {% for assertion in assertions %}
        with allure.step("断言验证: {{ assertion.description }}"):{{ assertion.code | indent(12, first=False) }}
        {% endfor %}
        
        allure.attach(screenshot(), name="测试执行完成截图", attachment_type=allure.attachment_type.PNG)

if __name__ == "__main__":
    pytest.main([__file__, "--alluredir=../../reports/allure-results", "-v"])
'''
        
        template_file = self.templates_dir / "pytest_airtest_template.py.j2"
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(template_content)

        # 录制风格（Airtest 直写）模板（仅使用 JSON 的注释与 notes，不注入模板内置注释）
        recorded_template = '''# {{ testcase_name }}
# [tag] {{ tags }}
# [path] {{ path_scope }}

# 统一的导包方案, 其它用例直接复用即可
# -----
import sys, os
# Ensure repository root on sys.path so that 'only_test' package is importable
_here = os.path.dirname(__file__)
_repo_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from only_test.lib.airtest_compat import *
# 使用修复后的poco工具函数（已解决所有导入和依赖问题）

# 添加项目路径
project_root = os.path.join(os.path.dirname(__file__), '../..')
sys.path.insert(0, project_root)

from lib.poco_utils import get_android_poco
from only_test.lib.ad_closer import close_ads
import asyncio
# -----

# setup_hook()
# 这里会放置一些测之前的必要条件 
{% if device_serial %}device_id = "{{ device_serial }}"
connect_device("android://127.0.0.1:5037/{}?touch_method=ADBTOUCH&".format(device_id))
{% else %}# device_id = ""
# connect_device("android://127.0.0.1:5037/{}?touch_method=ADBTOUCH&".format(device_id))
{% endif %}
{% if app_id %}poco = get_android_poco(device_id={{ 'device_id' if device_serial else 'None' }}, app_id="{{ app_id }}")
{% else %}poco = get_android_poco(device_id={{ 'device_id' if device_serial else 'None' }})
{% endif %}
{% if variables.get('program_name') or variables.get('search_keyword') %}
program_name = "{{ variables.get('program_name') or variables.get('search_keyword') }}"
{% endif %}

{% for step in execution_steps %}{{ step.code }}
{% endfor %}

{% if assertions and assertions|length > 0 %}
# [page] playing, [action] assert, [comment] {{ assertions[0].description or '断言验证' }}
# there is assert program are already playing 
# ....
{% else %}
# [page] playing, [action] assert, [comment] 断言验证节目正在正常播放
# there is assert program are already playing 
# ....
{% endif %}

# teardown_hook()
# 这里会放置一些测之前的必要条件 


# -------------
# commente to get a position and click
#x, y = poco("com.mobile.brasiltvmobile:id/mVodImageSearch").get_position()
# Click at those coordinates 
#poco.click([x, y])
'''
        
        recorded_file = self.templates_dir / "airtest_record_style.py.j2"
        with open(recorded_file, 'w', encoding='utf-8') as f:
            f.write(recorded_template)


    def _generate_from_v2(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据 v2 结构（hooks/test_steps）生成 recorded 风格的执行代码块数组"""
        steps: List[Dict[str, Any]] = []

        def normalize_selectors(target: Dict[str, Any]) -> List[Dict[str, Any]]:
            sels = []
            if not isinstance(target, dict):
                return sels
            rs = target.get('selectors') or []
            if isinstance(rs, list):
                for s in rs:
                    if isinstance(s, dict) and s.get('strategy') and s.get('value'):
                        strat = s['strategy']
                        val = s['value']
                        if strat == 'resource_id':
                            sels.append({'resource_id': val})
                        elif strat == 'text':
                            # 变量占位处理 ${var}
                            if isinstance(val, str) and val.startswith('${') and val.endswith('}'):
                                # 在生成代码时会替换为 program_name 变量
                                sels.append({'text': 'program_name'})
                            else:
                                sels.append({'text': val})
                        elif strat in ('content_desc', 'desc'):
                            sels.append({'content_desc': val})
                        elif strat in ('class', 'type'):
                            sels.append({'class': val})
                        else:
                            # 其他策略暂不渲染
                            pass
            return sels

        def to_old_action(step: Dict[str, Any]) -> Dict[str, Any]:
            # 将 v2 step 转为旧 action_data 以复用 _generate_action_code
            action = step.get('action')
            page = step.get('page')
            comment = step.get('comment')
            target = step.get('target') or {}
            bias = (target.get('bias') if isinstance(target, dict) else None) or {}
            sels = normalize_selectors(target)
            # 合并 flag
            if isinstance(target, dict) and target.get('combine_into_one_node'):
                pass  # 直接交由 _build_poco_selector 组合成单节点参数

            old_target = { 'priority_selectors': sels }
            if isinstance(bias, dict) and (bias.get('dx_px') is not None or bias.get('dy_px') is not None):
                old_target['bias'] = bias
            if isinstance(target, dict) and target.get('disappearance'):
                old_target['disappearance'] = True

            wait_block = step.get('wait') if isinstance(step.get('wait'), dict) else None
            notes = step.get('notes') if isinstance(step.get('notes'), list) else []

            # 特殊动作映射
            act = action
            if action == 'wait_for_disappearance':
                act = 'wait_for_elements'
                if isinstance(old_target, dict):
                    old_target['disappearance'] = True
            if action == 'click_with_bias':
                act = 'click'
                # 已在 bias 中体现
            if action == 'press':
                # 传递 target.keyevent
                pass

            return {
                'action': act,
                'page': page,
                'comment': comment,
                'target': old_target,
                'wait': wait_block,
                'notes': notes
            }

        # hooks.before_all
        hooks = data.get('hooks') or {}
        before_all = hooks.get('before_all') or []
        for h in before_all:
            ha = h.get('action')
            if ha in ('stop_app','restart'):
                # 用 restart 语义生成
                s = {'action': 'restart', 'page': 'app_initialization', 'comment': h.get('comment'), 'wait': h.get('wait')}
                steps.append({ 'type': 'regular', 'code': self._generate_action_code(s) })
            elif ha in ('start_app','launch'):
                s = {'action': 'launch', 'page': 'app_startup', 'comment': h.get('comment'), 'wait': h.get('wait')}
                steps.append({ 'type': 'regular', 'code': self._generate_action_code(s) })
            elif ha == 'tool' and (h.get('tool_name') == 'close_ads'):
                s = {'action': 'tool', 'tool_name': 'close_ads', 'page': 'home', 'comment': h.get('comment'), 'params': h.get('params'), 'wait': h.get('wait')}
                steps.append({ 'type': 'regular', 'code': self._generate_action_code(s) })
            else:
                # 未识别 hook，忽略或占位
                pass

        # 正式步骤
        for step in (data.get('test_steps') or []):
            oa = to_old_action(step)
            code = self._generate_action_code(oa)
            steps.append({ 'type': 'regular', 'code': code })

        # hooks.after_all（当前无动作）
        return steps

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JSON到Python测试用例转换器")
    parser.add_argument("json_file", help="输入的JSON测试用例文件")
    parser.add_argument("--output", "-o", help="输出的Python文件路径")
    parser.add_argument("--templates-dir", default="templates", help="模板文件目录")
    
    args = parser.parse_args()
    
    converter = JSONToPythonConverter(args.templates_dir)
    output_file = converter.convert_json_to_python(args.json_file, args.output)
    
    print(f"✅ 转换完成!")
    print(f"   输入文件: {args.json_file}")
    print(f"   输出文件: {output_file}")
    print(f"   执行命令: pytest {output_file} --alluredir=reports/allure-results -v")


if __name__ == "__main__":
    main()
