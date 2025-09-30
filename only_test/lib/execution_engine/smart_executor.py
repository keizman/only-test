"""
智能测试执行器

集成条件逻辑处理、phone-use功能和异常恢复的智能执行引擎
支持智能元数据驱动的测试用例执行
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# 导入自定义模块（实际使用时需要确保导入路径正确）
from ..metadata_engine.conditional_logic import ConditionalLogicEngine
from ..screen_capture import ScreenCapture
from ...config.config_manager import get_config

# 可选导入 - 如果模块不存在则使用None
try:
    from ..visual_recognition.element_recognizer import ElementRecognizer
except Exception:
    ElementRecognizer = None


class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running" 
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RECOVERY = "recovery"


@dataclass
class ExecutionResult:
    """执行结果"""
    status: ExecutionStatus
    step_number: int
    action: str
    target: str
    duration: float
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    recovery_attempted: bool = False
    condition_result: Optional[bool] = None
    selected_path: Optional[str] = None


@dataclass
class TestCaseResult:
    """测试用例结果"""
    testcase_id: str
    name: str
    overall_status: ExecutionStatus
    total_duration: float
    step_results: List[ExecutionResult]
    assertions_passed: int
    assertions_failed: int
    recovery_count: int
    start_time: str
    end_time: str


class SmartTestExecutor:
    """智能测试执行器"""
    
    def __init__(self, device_id: Optional[str] = None):
        """
        初始化智能执行器

        Args:
            device_id: 设备ID
        """
        self.device_id = device_id
        self.logger = self._setup_logger()

        # 加载框架配置
        self.timeouts = {
            'default_step': get_config('execution.timeouts.default_step', 30),
            'element_wait': get_config('execution.timeouts.element_wait', 10),
            'page_load': get_config('execution.timeouts.page_load', 15),
            'assertion': get_config('execution.timeouts.assertion', 10),
            'recovery': get_config('execution.timeouts.recovery', 5)
        }

        self.retry_config = {
            'enabled': get_config('execution.retry.enabled', True),
            'max_retries': get_config('execution.retry.max_retries', 3),
            'retry_delay': get_config('execution.retry.retry_delay', 2),
            'exponential_backoff': get_config('execution.retry.exponential_backoff', True)
        }

        self.recovery_config = {
            'enabled': get_config('execution.recovery.enabled', True),
            'auto_screenshot': get_config('execution.recovery.auto_screenshot', True),
            'strategies': get_config('execution.recovery.recovery_strategies', [])
        }

        # 初始化核心组件
        self.screen_capture = ScreenCapture(device_id)
        self.element_recognizer = ElementRecognizer() if ElementRecognizer else None
        self.conditional_engine = ConditionalLogicEngine()

        # 执行上下文
        self.current_page = None
        self.current_app = None
        self.execution_context = {}
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"SmartExecutor_{self.device_id}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def execute_testcase(self, testcase_data: Dict[str, Any]) -> TestCaseResult:
        """
        执行智能测试用例
        
        Args:
            testcase_data: 测试用例数据
            
        Returns:
            TestCaseResult: 执行结果
        """
        testcase_id = testcase_data.get('testcase_id', 'Unknown')
        testcase_name = testcase_data.get('name', 'Unknown')
        
        self.logger.info(f"🚀 开始执行测试用例: {testcase_name}")
        
        start_time = time.time()
        step_results = []
        recovery_count = 0
        
        try:
            # 准备执行环境
            self._prepare_execution_context(testcase_data)
            
            # 执行测试步骤
            execution_path = testcase_data.get('execution_path', [])
            for step_data in execution_path:
                step_result = self._execute_step(step_data)
                step_results.append(step_result)
                
                if step_result.recovery_attempted:
                    recovery_count += 1
                
                # 如果步骤失败且是关键步骤，终止执行
                if (step_result.status == ExecutionStatus.FAILED and 
                    step_data.get('critical', True)):
                    self.logger.error(f"❌ 关键步骤失败，终止执行: Step {step_result.step_number}")
                    break
            
            # 执行断言
            assertions = testcase_data.get('assertions', [])
            assertions_passed, assertions_failed = self._execute_assertions(assertions)
            
            # 确定整体状态
            overall_status = self._determine_overall_status(step_results, assertions_failed)
            
        except Exception as e:
            self.logger.error(f"❌ 测试用例执行异常: {e}")
            overall_status = ExecutionStatus.FAILED
            assertions_passed = assertions_failed = 0
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        result = TestCaseResult(
            testcase_id=testcase_id,
            name=testcase_name,
            overall_status=overall_status,
            total_duration=total_duration,
            step_results=step_results,
            assertions_passed=assertions_passed,
            assertions_failed=assertions_failed,
            recovery_count=recovery_count,
            start_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)),
            end_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))
        )
        
        self._log_execution_summary(result)
        return result
    
    def _prepare_execution_context(self, testcase_data: Dict[str, Any]):
        """
        准备执行上下文
        
        Args:
            testcase_data: 测试用例数据
        """
        context_awareness = testcase_data.get('context_awareness', {})
        variables = testcase_data.get('variables', {})
        
        self.execution_context = {
            'variables': variables,
            'context': context_awareness,
            'target_app': testcase_data.get('target_app'),
            'device_type': testcase_data.get('metadata', {}).get('device_types', ['android_phone'])[0]
        }
        
        self.logger.info(f"📋 执行上下文已准备: {self.execution_context}")
    
    def _execute_step(self, step_data: Dict[str, Any]) -> ExecutionResult:
        """
        执行单个测试步骤
        
        Args:
            step_data: 步骤数据
            
        Returns:
            ExecutionResult: 步骤执行结果
        """
        step_number = step_data.get('step', 0)
        action = step_data.get('action', 'unknown')
        page = step_data.get('page', 'unknown')
        description = step_data.get('description', 'No description')
        
        self.logger.info(f"▶️  Step {step_number}: {description}")
        
        start_time = time.time()
        screenshot_path = None
        error_message = None
        recovery_attempted = False
        condition_result = None
        selected_path = None
        
        try:
            # 更新当前页面
            self.current_page = page
            
            # 截图（用于调试和报告）
            screenshot_path = self._take_debug_screenshot(step_number)
            
            if action == 'conditional_action':
                # 处理条件分支逻辑
                result = self._execute_conditional_action(step_data)
                condition_result = result.get('condition_result')
                selected_path = result.get('selected_path')
                status = ExecutionStatus.SUCCESS if result.get('success', False) else ExecutionStatus.FAILED
                error_message = result.get('error_message')
                
            else:
                # 处理普通动作
                success = self._execute_simple_action(step_data)
                status = ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILED
        
        except Exception as e:
            self.logger.error(f"❌ Step {step_number} 执行失败: {e}")
            status = ExecutionStatus.FAILED
            error_message = str(e)
            
            # 尝试恢复
            try:
                recovery_result = self._attempt_recovery(step_data, e)
                if recovery_result:
                    status = ExecutionStatus.SUCCESS
                    recovery_attempted = True
                    self.logger.info(f"✅ Step {step_number} 恢复成功")
            except Exception as recovery_error:
                self.logger.error(f"❌ Step {step_number} 恢复失败: {recovery_error}")
        
        duration = time.time() - start_time
        
        return ExecutionResult(
            status=status,
            step_number=step_number,
            action=action,
            target=step_data.get('target', 'unknown'),
            duration=duration,
            screenshot_path=screenshot_path,
            error_message=error_message,
            recovery_attempted=recovery_attempted,
            condition_result=condition_result,
            selected_path=selected_path
        )
    
    def _execute_conditional_action(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行条件分支动作
        
        Args:
            step_data: 步骤数据
            
        Returns:
            Dict: 执行结果
        """
        self.logger.info(f"🧠 执行条件分支逻辑")
        
        try:
            # 解析条件动作
            conditional_action = self.conditional_engine.parse_conditional_action(step_data)
            
            # 生成执行计划
            execution_plan = self.conditional_engine.generate_execution_plan(conditional_action)
            
            selected_path = execution_plan['selected_path']
            condition_result = execution_plan['condition_result']
            
            self.logger.info(f"🎯 条件评估结果: {condition_result}")
            self.logger.info(f"📍 选择路径: {selected_path.action} -> {selected_path.target}")
            self.logger.info(f"💡 选择原因: {selected_path.reason}")
            
            # 执行选择的路径
            path_step_data = {
                'action': selected_path.action,
                'target': selected_path.target,
                'data': selected_path.data,
                'ai_hint': selected_path.ai_hint
            }
            
            success = self._execute_simple_action(path_step_data)
            
            return {
                'success': success,
                'condition_result': condition_result,
                'selected_path': f"{selected_path.action}({selected_path.target})",
                'execution_reason': selected_path.reason
            }
            
        except Exception as e:
            return {
                'success': False,
                'error_message': f"条件分支执行失败: {e}",
                'condition_result': None,
                'selected_path': None
            }
    
    def _execute_simple_action(self, step_data: Dict[str, Any]) -> bool:
        """
        执行简单动作
        
        Args:
            step_data: 步骤数据
            
        Returns:
            bool: 执行是否成功
        """
        action = step_data.get('action')
        target = step_data.get('target')
        data = step_data.get('data')
        ai_hint = step_data.get('ai_hint', '')
        
        self.logger.info(f"🎯 执行动作: {action}")
        if ai_hint:
            self.logger.info(f"💡 AI提示: {ai_hint}")
        
        try:
            if action == 'click':
                return self._perform_click(target)
            elif action == 'input':
                return self._perform_input(target, data)
            elif action == 'swipe':
                return self._perform_swipe(target)
            elif action == 'wait':
                return self._perform_wait(step_data)
            elif action == 'skip':
                self.logger.info("⏭️  跳过当前步骤")
                return True
            else:
                self.logger.warning(f"⚠️  未知动作类型: {action}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 动作执行失败: {e}")
            return False
    
    def _perform_click(self, target: Union[str, Dict]) -> bool:
        """执行点击操作"""
        # 这里将集成 phone-use 的实际点击实现
        # 暂时返回模拟结果
        self.logger.info(f"👆 点击元素: {target}")
        time.sleep(0.5)  # 模拟操作时间
        return True
    
    def _perform_input(self, target: Union[str, Dict], data: str) -> bool:
        """执行输入操作"""
        # 处理变量替换
        if data and data.startswith('${') and data.endswith('}'):
            var_name = data[2:-1]
            data = self.execution_context.get('variables', {}).get(var_name, data)
        
        self.logger.info(f"⌨️  输入文本到 {target}: {data}")
        time.sleep(0.3)  # 模拟输入时间
        return True
    
    def _perform_swipe(self, target: Union[str, Dict]) -> bool:
        """执行滑动操作"""
        self.logger.info(f"👆 滑动: {target}")
        time.sleep(0.5)
        return True
    
    def _perform_wait(self, step_data: Dict[str, Any]) -> bool:
        """执行等待操作"""
        timeout = step_data.get('timeout', 5)
        self.logger.info(f"⏳ 等待 {timeout} 秒")
        time.sleep(min(timeout, 2))  # 模拟等待，但限制最大时间
        return True
    
    def _attempt_recovery(self, step_data: Dict[str, Any], error: Exception) -> bool:
        """
        尝试异常恢复
        
        Args:
            step_data: 失败的步骤数据
            error: 异常信息
            
        Returns:
            bool: 恢复是否成功
        """
        self.logger.info(f"🔄 尝试恢复步骤: {step_data.get('step', 'unknown')}")
        
        # 这里将实现实际的恢复逻辑
        # 包括切换识别模式、重新截图、重试等
        
        # 模拟恢复逻辑
        time.sleep(1)
        
        # 简单的重试机制
        try:
            return self._execute_simple_action(step_data)
        except:
            return False
    
    def _execute_assertions(self, assertions: List[Dict[str, Any]]) -> tuple:
        """
        执行断言
        
        Args:
            assertions: 断言列表
            
        Returns:
            tuple: (通过数量, 失败数量)
        """
        if not assertions:
            return 0, 0
        
        passed = failed = 0
        self.logger.info(f"✅ 开始执行断言，共 {len(assertions)} 个")
        
        for assertion in assertions:
            try:
                result = self._execute_single_assertion(assertion)
                if result:
                    passed += 1
                    self.logger.info(f"✅ 断言通过: {assertion.get('description', 'Unknown')}")
                else:
                    failed += 1
                    self.logger.error(f"❌ 断言失败: {assertion.get('description', 'Unknown')}")
            except Exception as e:
                failed += 1
                self.logger.error(f"❌ 断言执行异常: {e}")
        
        return passed, failed
    
    def _execute_single_assertion(self, assertion: Dict[str, Any]) -> bool:
        """执行单个断言"""
        assertion_type = assertion.get('type')
        expected = assertion.get('expected')
        
        # 这里将实现实际的断言逻辑
        # 暂时返回模拟结果
        if assertion_type == 'check_search_results_exist':
            # 模拟检查搜索结果
            return True
        
        return True
    
    def _determine_overall_status(self, step_results: List[ExecutionResult], assertions_failed: int) -> ExecutionStatus:
        """确定整体执行状态"""
        if assertions_failed > 0:
            return ExecutionStatus.FAILED
        
        failed_steps = [r for r in step_results if r.status == ExecutionStatus.FAILED]
        if failed_steps:
            return ExecutionStatus.FAILED
        
        return ExecutionStatus.SUCCESS
    
    def _take_debug_screenshot(self, step_number: int) -> str:
        """为调试目的截图"""
        try:
            screenshot_path = f"/tmp/debug_step_{step_number}_{int(time.time())}.png"
            return self.screen_capture.take_screenshot(screenshot_path)
        except:
            return None
    
    def _log_execution_summary(self, result: TestCaseResult):
        """记录执行摘要"""
        status_emoji = {
            ExecutionStatus.SUCCESS: "✅",
            ExecutionStatus.FAILED: "❌",
            ExecutionStatus.SKIPPED: "⏭️"
        }
        
        emoji = status_emoji.get(result.overall_status, "❓")
        
        self.logger.info("\n" + "="*60)
        self.logger.info(f"{emoji} 测试用例执行完成: {result.name}")
        self.logger.info("="*60)
        self.logger.info(f"📊 整体状态: {result.overall_status.value}")
        self.logger.info(f"⏱️  总耗时: {result.total_duration:.2f} 秒")
        self.logger.info(f"📝 步骤数量: {len(result.step_results)}")
        self.logger.info(f"✅ 断言通过: {result.assertions_passed}")
        self.logger.info(f"❌ 断言失败: {result.assertions_failed}")
        self.logger.info(f"🔄 恢复次数: {result.recovery_count}")
        self.logger.info("="*60)
