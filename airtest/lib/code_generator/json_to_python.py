#!/usr/bin/env python3
"""
JSON到Python测试用例转换器

将智能元数据JSON转换为可执行的Python测试文件
支持airtest + pytest + allure框架集成
"""

import json
import jinja2
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class JSONToPythonConverter:
    """JSON测试用例到Python代码转换器"""
    
    def __init__(self, templates_dir: str = "templates"):
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
        # 解析执行路径
        execution_steps = self._parse_execution_path(testcase_data.get("execution_path", []))
        
        # 解析断言
        assertions = self._parse_assertions(testcase_data.get("assertions", []))
        
        # 准备模板数据
        template_data = {
            "testcase_id": testcase_data.get("testcase_id"),
            "testcase_name": testcase_data.get("name"),
            "description": testcase_data.get("description"),
            "target_app": testcase_data.get("target_app"),
            "variables": testcase_data.get("variables", {}),
            "metadata": testcase_data.get("metadata", {}),
            "execution_steps": execution_steps,
            "assertions": assertions,
            "generation_info": {
                "generated_at": datetime.now().isoformat(),
                "original_json": testcase_data.get("generated_from_template"),
                "conversion_method": "json_to_python_converter"
            }
        }
        
        # 使用模板生成代码
        template = self.jinja_env.get_template("pytest_airtest_template.py.j2")
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

        if action == "click":
            return f"""
    # {action_data.get('reason', '执行点击操作')}
    element = find_element_by_priority_selectors({selectors})
    if element:
        element.click()
        allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
    else:
        raise Exception("未找到可点击元素")
"""
        elif action == "input":
            data = action_data.get("data", "")
            # 处理变量替换
            if data.startswith("${") and data.endswith("}"):
                var_name = data[2:-1]
                data = f"VARIABLES.get('{var_name}', '{data}')"
            else:
                data = f"'{data}'"
            return f"""
    # {action_data.get('reason', '输入数据')}
    element = find_element_by_priority_selectors({selectors})
    if element:
        element.set_text({data})
        allure.attach(screenshot(), name="输入后截图", attachment_type=allure.attachment_type.PNG)
    else:
        raise Exception("未找到输入元素")
"""
        elif action == "wait_for_elements":
            timeout = action_data.get("timeout", 10)
            return f"""
    # {action_data.get('description', '等待元素出现')}
    wait_for_element({selectors}, timeout={timeout})
    allure.attach(screenshot(), name="等待完成截图", attachment_type=allure.attachment_type.PNG)
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
from airtest.core.api import *
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