#!/usr/bin/env python3
"""
Only-Test JSON元数据到Python代码生成器

核心功能:
1. 从JSON元数据生成可执行的Python测试代码
2. 支持智能条件判断逻辑
3. 元素定位策略优化  
4. 异常处理和重试机制
5. 断言和验证代码生成
6. 模板化代码生成，保证代码风格一致
"""

import sys
import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("json_to_python")


class ActionType(Enum):
    """动作类型枚举"""
    LAUNCH = "launch"
    CLICK = "click"
    INPUT = "input"
    SWIPE = "swipe"
    WAIT = "wait"
    ASSERT = "assert"
    RESTART = "restart"


class ElementLocateStrategy(Enum):
    """元素定位策略"""
    RESOURCE_ID = "resource_id"
    TEXT = "text"
    UUID = "uuid"
    XPATH = "xpath"
    COORDINATE = "coordinate"


@dataclass
class ActionStep:
    """动作步骤数据结构"""
    action_type: ActionType
    page: str
    comment: str
    target_element: Optional[str] = None
    element_uuid: Optional[str] = None
    locate_strategy: Optional[ElementLocateStrategy] = None
    input_text: Optional[str] = None
    wait_time: Optional[float] = None
    coordinates: Optional[tuple] = None
    conditions: Optional[Dict[str, Any]] = None
    retry_count: int = 3
    timeout: float = 10.0


class PythonCodeGenerator:
    """Python代码生成器"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.parent
        self.templates_dir = self.base_dir / "templates"
        self.output_dir = self.base_dir / "only_test" / "testcases" / "python"
        
        # 确保目录存在
        self.templates_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # 代码模板
        self.code_templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, str]:
        """初始化代码模板"""
        return {
'file_header': '''# {description}
# [tag] {tags}
# [path] {path}

from airtest.core.api import *
# 使用本地自定义的Poco库
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../Poco'))
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
import logging

# 建议通过 airtest run --device 传入设备；如需直接连接，请取消下一行注释并填写设备ID
connect_device("{device_connection}")

# 基础日志器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)
''',
            
            "restart_app": '''## [page] {page}, [action] {action}, [comment] {comment}
stop_app("{app_package}")
stop_app("{app_package}")
stop_app("{app_package}")
sleep({wait_time})
''',
            
            "launch_app": '''## [page] {page}, [action] {action}, [comment] {comment}
start_app("{app_package}")
sleep({wait_time})
''',
            
            "click_by_resource_id": '''## [page] {page}, [action] {action}, [comment] {comment}
{retry_wrapper_start}
poco("{resource_id}").click()
{retry_wrapper_end}
''',
            
            "click_by_text": '''## [page] {page}, [action] {action}, [comment] {comment}
{retry_wrapper_start}
poco(text="{text}").click()
{retry_wrapper_end}
''',
            
            "click_by_uuid": '''## [page] {page}, [action] {action}, [comment] {comment}
{retry_wrapper_start}
# 通过UUID定位元素 (需要配合元素提取器使用)
element = find_element_by_uuid("{uuid}")
if element:
    poco.click([element.center_x * screen_width, element.center_y * screen_height])
else:
    logger.warning("未找到UUID为 {uuid} 的元素")
{retry_wrapper_end}
''',
            
            "click_by_coordinate": '''## [page] {page}, [action] {action}, [comment] {comment}
{retry_wrapper_start}
poco.click([{x}, {y}])
{retry_wrapper_end}
''',
            
            "input_text": '''## [page] {page}, [action] {action}, [comment] {comment}
{retry_wrapper_start}
poco("{target}").click()
sleep(0.5)
text("{input_text}")
{retry_wrapper_end}
''',
            
            "swipe_action": '''## [page] {page}, [action] {action}, [comment] {comment}
poco.swipe([{start_x}, {start_y}], [{end_x}, {end_y}])
''',
            
            "wait_action": '''## [page] {page}, [action] {action}, [comment] {comment}
sleep({wait_time})
''',
            
            "wait_for_element": '''## [page] {page}, [action] {action}, [comment] {comment}
poco("{target}").wait_for_appearance(timeout={timeout})
''',
            
            "wait_for_disappear": '''## [page] {page}, [action] {action}, [comment] {comment}
poco(text="{target}").wait_for_disappearance(timeout={timeout})
''',
            
            "assert_element_exists": '''## [page] {page}, [action] {action}, [comment] {comment}
assert poco("{target}").exists(), "元素 {target} 不存在"
''',
            
            "assert_text_exists": '''## [page] {page}, [action] {action}, [comment] {comment}
assert poco(text="{text}").exists(), "文本 '{text}' 未找到"
''',
            
            "conditional_action": '''## [page] {page}, [action] {action}, [comment] {comment}
# 条件判断逻辑: {condition_desc}
if {condition_check}:
    {action_true}
else:
    {action_false}
''',
            
            "retry_wrapper": '''try:
    {action_code}
except Exception as e:
    logger.warning(f"操作失败，重试中: {{e}}")
    sleep(1)
    {action_code}
''',
            
            "exception_handler": '''try:
    {main_action}
except Exception as e:
    logger.error(f"执行失败: {{e}}")
    # 异常恢复逻辑
    {recovery_action}
'''
        }
    
    def parse_json_metadata(self, json_data: Dict[str, Any]) -> List[ActionStep]:
        """解析JSON元数据为动作步骤"""
        steps = []
        
        metadata = json_data.get('metadata', json_data)
        variables = json_data.get('variables', {}) if isinstance(json_data.get('variables', {}), dict) else {}
        raw_steps = metadata.get('steps', [])
        
        # 兼容 LLM/MCP 生成的 execution_path 结构
        if not raw_steps and 'execution_path' in json_data:
            for ep in json_data.get('execution_path', []):
                action_str = ep.get('action', 'click').lower()
                page = ep.get('page', 'unknown')
                comment = ep.get('description', '')
                timeout = float(ep.get('timeout', 10))
                input_text = ep.get('data') if ep.get('data') is not None else ep.get('input_text')
                if isinstance(input_text, str) and input_text.startswith('${') and input_text.endswith('}'):
                    var_name = input_text[2:-1]
                    input_text = variables.get(var_name, input_text)
                target_dict = ep.get('target', {}) or {}
                target_element = self._select_best_selector(target_dict)
                # 若无稳定选择器，尝试使用 xpath/path
                if not target_element and isinstance(target_dict, dict):
                    if target_dict.get('xpath') or target_dict.get('path'):
                        target_element = target_dict.get('xpath') or target_dict.get('path')
                # 同时尝试从 bounds_px 计算坐标（不做归一化，交由执行侧/调用方适配）
                coordinates = None
                if isinstance(target_dict, dict):
                    bounds = target_dict.get('bounds_px')
                    if isinstance(bounds, list) and len(bounds) == 4:
                        left, top, right, bottom = bounds
                        cx = int((left + right) / 2)
                        cy = int((top + bottom) / 2)
                        coordinates = (cx, cy)

                action_map = {
                    'click': ActionType.CLICK,
                    'input': ActionType.INPUT,
                    'swipe': ActionType.SWIPE,
                    'wait_for_elements': ActionType.WAIT,
                    'wait': ActionType.WAIT,
                    'restart': ActionType.RESTART,
                    'launch': ActionType.LAUNCH,
                    'assert': ActionType.ASSERT,
                }
                action_type = action_map.get(action_str, ActionType.CLICK)

                step = ActionStep(
                    action_type=action_type,
                    page=page,
                    comment=comment,
                    target_element=target_element,
                    input_text=input_text,
                    timeout=timeout,
                )
                # 设置坐标定位（如果可用）
                if coordinates:
                    step.coordinates = coordinates
                step.locate_strategy = self._determine_locate_strategy(step)
                steps.append(step)

            logger.info(f"解析了 {len(steps)} 个动作步骤 (execution_path)")
            return steps
    def _select_best_selector(self, target: Dict[str, Any]) -> Optional[str]:
        """从 priority_selectors/selectors 或直接键选择最优定位（resource_id > content_desc > text）。
        兼容以下情况：
        - priority_selectors 为 dict（含 'resource-id'/'resource_id', 'content-desc'/'content_desc', 'text', 'xpath' 等）
        - priority_selectors 为 list[dict]
        - 直接在 target 上提供 resource_id/content_desc/text/path/xpath
        """
        if not isinstance(target, dict):
            return None
        # 直接键优先
        direct_keys = [
            ('resource_id', 'resource_id'),
            ('content_desc', 'content_desc'),
            ('desc', 'content_desc'),
            ('text', 'text'),
            ('xpath', 'xpath'),
            ('path', 'xpath'),  # 允许 path 作为 xpath 使用
        ]
        for key, norm in direct_keys:
            if target.get(key):
                return target.get(key)
        # 处理 priority_selectors / selectors
        selectors = target.get('priority_selectors') or target.get('selectors')
        # 如果是 dict，尝试常见命名（包含连字符写法）
        if isinstance(selectors, dict):
            # 优先 resource-id / resource_id
            if selectors.get('resource_id') or selectors.get('resource-id'):
                return selectors.get('resource_id') or selectors.get('resource-id')
            # 再 content-desc / content_desc / desc
            if selectors.get('content_desc') or selectors.get('content-desc') or selectors.get('desc'):
                return selectors.get('content_desc') or selectors.get('content-desc') or selectors.get('desc')
            # 再 text
            if selectors.get('text'):
                return selectors.get('text')
            # xpath/path
            if selectors.get('xpath') or selectors.get('path'):
                return selectors.get('xpath') or selectors.get('path')
            return None
        # 如果是 list，按优先级遍历
        if isinstance(selectors, list):
            for sel in selectors:
                if isinstance(sel, dict) and (sel.get('resource_id') or sel.get('resource-id')):
                    return sel.get('resource_id') or sel.get('resource-id')
            for sel in selectors:
                if isinstance(sel, dict) and (sel.get('content_desc') or sel.get('content-desc') or sel.get('desc')):
                    return sel.get('content_desc') or sel.get('content-desc') or sel.get('desc')
            for sel in selectors:
                if isinstance(sel, dict) and sel.get('text'):
                    return sel.get('text')
            for sel in selectors:
                if isinstance(sel, dict) and (sel.get('xpath') or sel.get('path')):
                    return sel.get('xpath') or sel.get('path')
        return None

        for step_data in raw_steps:
            # 解析动作类型
            action_str = step_data.get('action', 'click').lower()
            try:
                action_type = ActionType(action_str)
            except ValueError:
                action_type = ActionType.CLICK  # 默认为点击
            
            # 创建ActionStep对象
            step = ActionStep(
                action_type=action_type,
                page=step_data.get('page', 'unknown'),
                comment=step_data.get('comment', ''),
                target_element=step_data.get('target_element'),
                element_uuid=step_data.get('element_uuid'),
                input_text=step_data.get('input_text'),
                wait_time=step_data.get('wait_time', 1.0),
                coordinates=step_data.get('coordinates'),
                conditions=step_data.get('conditions'),
                retry_count=step_data.get('retry_count', 3),
                timeout=step_data.get('timeout', 10.0)
            )
            
            # 确定定位策略
            step.locate_strategy = self._determine_locate_strategy(step)
            
            steps.append(step)
        
        logger.info(f"解析了 {len(steps)} 个动作步骤")
        return steps
    def _select_best_selector(self, target: Dict[str, Any]) -> Optional[str]:
        """与上方实现一致：兼容 dict/list 与连字符键名。"""
        if not isinstance(target, dict):
            return None
        direct_keys = [
            ('resource_id', 'resource_id'),
            ('content_desc', 'content_desc'),
            ('desc', 'content_desc'),
            ('text', 'text'),
            ('xpath', 'xpath'),
            ('path', 'xpath'),
        ]
        for key, norm in direct_keys:
            if target.get(key):
                return target.get(key)
        selectors = target.get('priority_selectors') or target.get('selectors')
        if isinstance(selectors, dict):
            if selectors.get('resource_id') or selectors.get('resource-id'):
                return selectors.get('resource_id') or selectors.get('resource-id')
            if selectors.get('content_desc') or selectors.get('content-desc') or selectors.get('desc'):
                return selectors.get('content_desc') or selectors.get('content-desc') or selectors.get('desc')
            if selectors.get('text'):
                return selectors.get('text')
            if selectors.get('xpath') or selectors.get('path'):
                return selectors.get('xpath') or selectors.get('path')
            return None
        if isinstance(selectors, list):
            for sel in selectors:
                if isinstance(sel, dict) and (sel.get('resource_id') or sel.get('resource-id')):
                    return sel.get('resource_id') or sel.get('resource-id')
            for sel in selectors:
                if isinstance(sel, dict) and (sel.get('content_desc') or sel.get('content-desc') or sel.get('desc')):
                    return sel.get('content_desc') or sel.get('content-desc') or sel.get('desc')
            for sel in selectors:
                if isinstance(sel, dict) and sel.get('text'):
                    return sel.get('text')
            for sel in selectors:
                if isinstance(sel, dict) and (sel.get('xpath') or sel.get('path')):
                    return sel.get('xpath') or sel.get('path')
        return None
    
    def _determine_locate_strategy(self, step: ActionStep) -> ElementLocateStrategy:
        """确定元素定位策略"""
        if step.element_uuid:
            return ElementLocateStrategy.UUID
        elif step.target_element:
            # 检查是否为resource_id格式
            if ':id/' in step.target_element:
                return ElementLocateStrategy.RESOURCE_ID
            # 检查是否为XPath格式
            elif step.target_element.startswith('//') or step.target_element.startswith('/'):
                return ElementLocateStrategy.XPATH
            else:
                return ElementLocateStrategy.TEXT
        elif step.coordinates:
            return ElementLocateStrategy.COORDINATE
        else:
            return ElementLocateStrategy.TEXT
    
    def generate_step_code(self, step: ActionStep, app_package: str = "com.example.app") -> str:
        """生成单个步骤的代码"""
        template_params = {
            'page': step.page,
            'action': step.action_type.value,
            'comment': step.comment,
            'wait_time': step.wait_time if step.wait_time is not None else (step.timeout if step.timeout is not None else 1.0),
            'timeout': step.timeout,
            'app_package': app_package,
            'retry_wrapper_start': '',
            'retry_wrapper_end': ''
        }
        
# 保持模板内不直接拼装 try/except 包裹，由下层按需包装
        template_params['retry_wrapper_start'] = ''
        template_params['retry_wrapper_end'] = ''
        
        # 根据动作类型和定位策略选择模板
        if step.action_type == ActionType.RESTART:
            return self.code_templates['restart_app'].format(**template_params)
        
        elif step.action_type == ActionType.LAUNCH:
            return self.code_templates['launch_app'].format(**template_params)
        
        elif step.action_type == ActionType.CLICK:
            return self._generate_click_code(step, template_params)
        
        elif step.action_type == ActionType.INPUT:
            return self._generate_input_code(step, template_params)
        
        elif step.action_type == ActionType.SWIPE:
            return self._generate_swipe_code(step, template_params)
        
        elif step.action_type == ActionType.WAIT:
            return self._generate_wait_code(step, template_params)
        
        elif step.action_type == ActionType.ASSERT:
            return self._generate_assert_code(step, template_params)
        
        else:
            return f"# 未知动作类型: {step.action_type}\n"
    
    def _generate_click_code(self, step: ActionStep, params: Dict[str, Any]) -> str:
        def _wrap_retry(code: str) -> str:
            # 将多行代码缩进以嵌入 try 块
            stripped = code.strip().rstrip('\n')
            indented = '\n    '.join([line for line in stripped.splitlines() if line is not None])
            return self.code_templates['retry_wrapper'].format(action_code=indented)
        """生成点击操作代码"""
        if step.conditions:
            return self._generate_conditional_click(step, params)

        if step.locate_strategy == ElementLocateStrategy.RESOURCE_ID:
            params['resource_id'] = step.target_element
            base = self.code_templates['click_by_resource_id'].format(**params)
            return _wrap_retry(base) if step.retry_count > 1 else base

        elif step.locate_strategy == ElementLocateStrategy.TEXT:
            params['text'] = step.target_element
            base = self.code_templates['click_by_text'].format(**params)
            return _wrap_retry(base) if step.retry_count > 1 else base

        elif step.locate_strategy == ElementLocateStrategy.UUID:
            params['uuid'] = step.element_uuid
            base = self.code_templates['click_by_uuid'].format(**params)
            return _wrap_retry(base) if step.retry_count > 1 else base

        elif step.locate_strategy == ElementLocateStrategy.COORDINATE:
            x, y = step.coordinates if step.coordinates else (0.5, 0.5)
            params['x'] = x
            params['y'] = y
            base = self.code_templates['click_by_coordinate'].format(**params)
            return _wrap_retry(base) if step.retry_count > 1 else base

        elif step.locate_strategy == ElementLocateStrategy.XPATH:
            # XPath 直接用于 Poco 不可靠，优先回退坐标
            if step.coordinates:
                x, y = step.coordinates
                params['x'] = x
                params['y'] = y
                return self.code_templates['click_by_coordinate'].format(**params)
            else:
                # 无坐标则退化为文本点击（可能失败）
                params['text'] = step.target_element or 'unknown'
                return self.code_templates['click_by_text'].format(**params)

        else:
            params['text'] = step.target_element or 'unknown'
            base = self.code_templates['click_by_text'].format(**params)
            return _wrap_retry(base) if step.retry_count > 1 else base

    def _generate_conditional_click(self, step: ActionStep, params: Dict[str, Any]) -> str:
        """生成条件点击代码"""
        conditions = step.conditions
        condition_type = conditions.get('type', 'element_state')
        
        if condition_type == 'element_state':
            # 根据元素状态选择不同动作
            check_element = conditions.get('check_element', '')
            condition_check = f'poco("{check_element}").exists()'
            
            true_action = f'poco("{conditions.get("true_target", step.target_element)}").click()'
            false_action = f'poco("{conditions.get("false_target", step.target_element)}").click()'
            
            params.update({
                'condition_desc': conditions.get('description', '条件判断'),
                'condition_check': condition_check,
                'action_true': true_action,
                'action_false': false_action
            })
            
            return self.code_templates['conditional_action'].format(**params)
        
        elif condition_type == 'text_content':
            # 根据文本内容判断
            check_element = conditions.get('check_element', '')
            expected_text = conditions.get('expected_text', '')
            
            condition_check = f'poco("{check_element}").get_text().strip() == "{expected_text}"'
            true_action = f'poco("{conditions.get("true_target", step.target_element)}").click()'
            false_action = f'poco("{conditions.get("false_target", step.target_element)}").click()'
            
            params.update({
                'condition_desc': f'检查文本内容是否为"{expected_text}"',
                'condition_check': condition_check,
                'action_true': true_action,
                'action_false': false_action
            })
            
            return self.code_templates['conditional_action'].format(**params)
        
        else:
            # 默认处理
            return self._generate_click_code(ActionStep(
                ActionType.CLICK, step.page, step.comment, step.target_element,
                step.element_uuid, step.locate_strategy
            ), params)
    
    def _generate_input_code(self, step: ActionStep, params: Dict[str, Any]) -> str:
        def _wrap_retry(code: str) -> str:
            stripped = code.strip().rstrip('\n')
            indented = '\n    '.join([line for line in stripped.splitlines() if line is not None])
            return self.code_templates['retry_wrapper'].format(action_code=indented)
        """生成输入操作代码"""
        # 如果有坐标，先点击坐标再输入
        if step.coordinates:
            x, y = step.coordinates
            click_params = params.copy()
            click_params['x'] = x
            click_params['y'] = y
            code_click = self.code_templates['click_by_coordinate'].format(**click_params)
            input_params = params.copy()
            input_params.update({
                'target': step.target_element or 'input',
                'input_text': step.input_text or ''
            })
            base = code_click + self.code_templates['input_text'].format(**input_params)
            return _wrap_retry(base) if step.retry_count > 1 else base
        else:
            params.update({
                'target': step.target_element or 'input',
                'input_text': step.input_text or ''
            })
            base = self.code_templates['input_text'].format(**params)
            return _wrap_retry(base) if step.retry_count > 1 else base
    
    def _generate_swipe_code(self, step: ActionStep, params: Dict[str, Any]) -> str:
        """生成滑动操作代码"""
        coords = step.coordinates or [(0.5, 0.8), (0.5, 0.2)]  # 默认向上滑动
        
        if len(coords) >= 2:
            start_x, start_y = coords[0]
            end_x, end_y = coords[1]
        else:
            start_x, start_y, end_x, end_y = 0.5, 0.8, 0.5, 0.2
        
        params.update({
            'start_x': start_x,
            'start_y': start_y,
            'end_x': end_x,
            'end_y': end_y
        })
        
        return self.code_templates['swipe_action'].format(**params)
    
    def _generate_wait_code(self, step: ActionStep, params: Dict[str, Any]) -> str:
        """生成等待操作代码"""
        if step.target_element:
            # 等待元素出现或消失
            if 'disappear' in step.comment.lower() or '消失' in step.comment:
                params['target'] = step.target_element
                return self.code_templates['wait_for_disappear'].format(**params)
            else:
                params['target'] = step.target_element
                return self.code_templates['wait_for_element'].format(**params)
        else:
            # 普通等待
            return self.code_templates['wait_action'].format(**params)
    
    def _generate_assert_code(self, step: ActionStep, params: Dict[str, Any]) -> str:
        """生成断言代码"""
        if step.locate_strategy == ElementLocateStrategy.TEXT:
            params['text'] = step.target_element
            return self.code_templates['assert_text_exists'].format(**params)
        else:
            params['target'] = step.target_element or 'element'
            return self.code_templates['assert_element_exists'].format(**params)
    
    def generate_complete_testcase(self, 
                                 json_data: Dict[str, Any],
                                 output_file: Optional[Path] = None) -> str:
        """生成完整的测试用例"""
        try:
            # 提取基本信息
            metadata = json_data.get('metadata', json_data)
            testcase_info = {
                'description': metadata.get('description', '自动生成的测试用例'),
                'tags': ', '.join(metadata.get('tags', [])),
                'path': ' -> '.join(metadata.get('path', [])),
                'device_connection': metadata.get('device_connection', 
                    'android://127.0.0.1:5037/device_id?touch_method=ADBTOUCH&'),
                'app_package': metadata.get('app_package') or json_data.get('target_app') or 'com.example.app'
            }
            
            # 生成文件头
            code_lines = [self.code_templates['file_header'].format(**testcase_info)]
            
            # 解析步骤
            steps = self.parse_json_metadata(json_data)
            
            # 生成每个步骤的代码
            for step in steps:
                step_code = self.generate_step_code(step, testcase_info['app_package'])
                code_lines.append(step_code)
            
            # 添加结束部分
            code_lines.extend([
                '',
                '# 测试用例执行完成',
                '# TODO: 添加结果验证和清理代码',
                ''
            ])
            
            complete_code = '\n'.join(code_lines)
            # 若未提供真实设备连接，注释 connect_device 行，便于使用 airtest run --device
            placeholder = 'connect_device("android://127.0.0.1:5037/device_id?touch_method=ADBTOUCH&")'
            if placeholder in complete_code:
                complete_code = complete_code.replace(
                    placeholder,
                    '# connect_device("android://127.0.0.1:5037/DEVICE?touch_method=ADBTOUCH&")  # 使用 airtest run --device 传入或在此填写'
                )
            
            # 保存到文件
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(complete_code)
                logger.info(f"测试用例已生成: {output_file}")
            
            return complete_code
            
        except Exception as e:
            logger.error(f"生成测试用例失败: {e}")
            raise
    
    def enhance_with_exception_handling(self, code: str) -> str:
        """增强异常处理"""
        enhanced_lines = [
            '# 增强异常处理',
            'import logging',
            'logging.basicConfig(level=logging.INFO)',
            'logger = logging.getLogger(__name__)',
            '',
            '# 全局异常处理装饰器',
            'def handle_exceptions(func):',
            '    def wrapper(*args, **kwargs):',
            '        try:',
            '            return func(*args, **kwargs)',
            '        except Exception as e:',
            '            logger.error(f"执行失败: {e}")',
            '            # 截图保存',
            '            screenshot_name = f"error_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png"',
            '            try:',
            '                poco.snapshot(screenshot_name)',
            '                logger.info(f"错误截图已保存: {screenshot_name}")',
            '            except:',
            '                pass',
            '            raise',
            '    return wrapper',
            '',
            code
        ]
        
        return '\n'.join(enhanced_lines)


class SmartCodeOptimizer:
    """智能代码优化器"""
    
    def __init__(self):
        self.optimization_rules = [
            self._optimize_redundant_waits,
            self._optimize_element_locators,
            self._add_smart_retries,
            self._optimize_assertions
        ]
    
    def optimize_code(self, code: str) -> str:
        """优化生成的代码"""
        optimized = code
        
        for rule in self.optimization_rules:
            try:
                optimized = rule(optimized)
            except Exception as e:
                logger.warning(f"优化规则失败: {e}")
        
        return optimized
    
    def _optimize_redundant_waits(self, code: str) -> str:
        """优化冗余等待"""
        lines = code.split('\n')
        optimized_lines = []
        prev_was_sleep = False
        
        for line in lines:
            if 'sleep(' in line:
                if prev_was_sleep:
                    # 合并连续的sleep
                    continue
                prev_was_sleep = True
            else:
                prev_was_sleep = False
            
            optimized_lines.append(line)
        
        return '\n'.join(optimized_lines)
    
    def _optimize_element_locators(self, code: str) -> str:
        """优化元素定位器"""
        # 将长的资源ID替换为变量
        lines = code.split('\n')
        resource_id_map = {}
        optimized_lines = []
        
        # 第一遍：收集resource_id
        for line in lines:
            if 'poco("' in line and ':id/' in line:
                start = line.find('poco("') + 6
                end = line.find('"', start)
                resource_id = line[start:end]
                
                if len(resource_id) > 30:  # 长ID才优化
                    var_name = resource_id.split(':id/')[-1]
                    resource_id_map[resource_id] = var_name
        
        # 添加变量定义
        if resource_id_map:
            optimized_lines.append('# 元素定位器变量')
            for resource_id, var_name in resource_id_map.items():
                optimized_lines.append(f'{var_name}_id = "{resource_id}"')
            optimized_lines.append('')
        
        # 第二遍：替换使用
        for line in lines:
            optimized_line = line
            for resource_id, var_name in resource_id_map.items():
                if resource_id in line:
                    optimized_line = optimized_line.replace(f'"{resource_id}"', f'{var_name}_id')
            optimized_lines.append(optimized_line)
        
        return '\n'.join(optimized_lines)
    
    def _add_smart_retries(self, code: str) -> str:
        """添加智能重试逻辑"""
        # 为关键操作添加重试
        critical_operations = ['click()', 'wait_for_appearance', 'exists()']
        
        lines = code.split('\n')
        optimized_lines = []
        
        for line in lines:
            if any(op in line for op in critical_operations) and 'try:' not in line:
                # 添加重试包装
                indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent
                
                optimized_lines.extend([
                    f'{indent_str}# 智能重试机制',
                    f'{indent_str}retry_count = 0',
                    f'{indent_str}while retry_count < 3:',
                    f'{indent_str}    try:',
                    f'{indent_str}        {line.strip()}',
                    f'{indent_str}        break',
                    f'{indent_str}    except Exception as e:',
                    f'{indent_str}        retry_count += 1',
                    f'{indent_str}        if retry_count >= 3:',
                    f'{indent_str}            raise',
                    f'{indent_str}        sleep(1)'
                ])
            else:
                optimized_lines.append(line)
        
        return '\n'.join(optimized_lines)
    
    def _optimize_assertions(self, code: str) -> str:
        """优化断言"""
        return code  # 暂时不做修改


# CLI工具
def main():
    """CLI主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='JSON元数据到Python代码生成器')
    parser.add_argument('input_file', help='输入的JSON元数据文件')
    parser.add_argument('-o', '--output', help='输出Python文件路径')
    parser.add_argument('--optimize', action='store_true', help='启用代码优化')
    parser.add_argument('--exception-handling', action='store_true', help='增强异常处理')
    
    args = parser.parse_args()
    
    try:
        # 加载JSON数据
        with open(args.input_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # 创建生成器
        generator = PythonCodeGenerator()
        
        # 生成输出文件路径
        if args.output:
            output_file = Path(args.output)
        else:
            input_path = Path(args.input_file)
            output_file = generator.output_dir / f"{input_path.stem}_generated.py"
        
        # 生成代码
        code = generator.generate_complete_testcase(json_data, output_file)
        
        # 优化代码
        if args.optimize:
            optimizer = SmartCodeOptimizer()
            code = optimizer.optimize_code(code)
            logger.info("已应用代码优化")
        
        # 增强异常处理
        if args.exception_handling:
            code = generator.enhance_with_exception_handling(code)
            logger.info("已增强异常处理")
        
        # 重新保存优化后的代码
        if args.optimize or args.exception_handling:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(code)
        
        print(f"✅ Python代码已生成: {output_file}")
        print(f"代码行数: {len(code.split(chr(10)))}")
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

