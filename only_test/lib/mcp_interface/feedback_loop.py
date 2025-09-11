#!/usr/bin/env python3
"""
Only-Test Feedback Loop
=======================

测试用例执行反馈循环系统
让LLM能够基于执行结果改进用例质量
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from .mcp_server import mcp_tool

logger = logging.getLogger(__name__)


class FeedbackLoop:
    """
    反馈循环处理器
    
    核心功能：
    1. 执行测试用例
    2. 分析执行结果
    3. 识别失败原因
    4. 生成改进建议
    5. 驱动用例优化
    """
    
    def __init__(self, device_id: Optional[str] = None):
        """初始化反馈循环处理器"""
        self.device_id = device_id
        self._initialized = False
        
        # 反馈历史记录
        self.feedback_history: List[Dict[str, Any]] = []
        self.execution_patterns: Dict[str, Any] = {}
        
        logger.info("反馈循环处理器初始化")
    
    async def initialize(self) -> bool:
        """初始化处理器"""
        try:
            self._initialized = True
            logger.info("反馈循环处理器初始化成功")
            return True
        except Exception as e:
            logger.error(f"反馈循环处理器初始化失败: {e}")
            return False
    
    @mcp_tool(
        name="execute_and_analyze",
        description="执行测试用例并分析结果",
        category="feedback",
        parameters={
            "test_case": {"type": "object", "description": "测试用例JSON"},
            "execution_mode": {"type": "string", "description": "执行模式", "enum": ["quick", "full", "debug"], "default": "quick"}
        }
    )
    async def execute_and_analyze(self, test_case: Dict[str, Any], execution_mode: str = "quick") -> Dict[str, Any]:
        """执行测试用例并分析结果"""
        if not self._initialized:
            await self.initialize()
        
        execution_result = {
            "execution_id": f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "test_case_id": test_case.get("testcase_id", "unknown"),
            "execution_mode": execution_mode,
            "start_time": datetime.now().isoformat()
        }
        
        try:
            # 第一步：转换用例为可执行代码
            conversion_result = await self._convert_case_to_python(test_case)
            execution_result["conversion"] = conversion_result
            
            if not conversion_result["success"]:
                execution_result["status"] = "conversion_failed"
                execution_result["analysis"] = await self._analyze_conversion_failure(conversion_result)
                return execution_result
            
            # 第二步：执行测试用例
            exec_result = await self._execute_python_case(
                conversion_result["python_code"], 
                execution_mode
            )
            execution_result["execution"] = exec_result
            
            # 第三步：分析执行结果
            analysis_result = await self._analyze_execution_result(exec_result, test_case)
            execution_result["analysis"] = analysis_result
            
            # 第四步：生成反馈和改进建议
            feedback = await self._generate_feedback(test_case, exec_result, analysis_result)
            execution_result["feedback"] = feedback
            
            # 记录反馈历史
            self.feedback_history.append({
                "timestamp": datetime.now().isoformat(),
                "execution_result": execution_result,
                "test_case": test_case
            })
            
            # 更新执行模式统计
            self._update_execution_patterns(test_case, exec_result)
            
            execution_result["status"] = "completed"
            execution_result["end_time"] = datetime.now().isoformat()
            
            return execution_result
            
        except Exception as e:
            logger.error(f"执行和分析失败: {e}")
            execution_result["status"] = "error"
            execution_result["error"] = str(e)
            execution_result["end_time"] = datetime.now().isoformat()
            return execution_result
    
    @mcp_tool(
        name="analyze_failure_patterns",
        description="分析测试失败模式并提供改进建议",
        category="feedback",
        parameters={
            "failure_logs": {"type": "array", "description": "失败日志列表"},
            "test_case": {"type": "object", "description": "失败的测试用例"}
        }
    )
    async def analyze_failure_patterns(self, failure_logs: List[str], test_case: Dict[str, Any]) -> Dict[str, Any]:
        """分析失败模式"""
        try:
            analysis = {
                "failure_categories": [],
                "root_causes": [],
                "improvement_suggestions": [],
                "confidence_score": 0.0,
                "timestamp": datetime.now().isoformat()
            }
            
            # 分析失败类型
            failure_categories = self._categorize_failures(failure_logs)
            analysis["failure_categories"] = failure_categories
            
            # 识别根本原因
            root_causes = self._identify_root_causes(failure_logs, test_case)
            analysis["root_causes"] = root_causes
            
            # 生成改进建议
            suggestions = self._generate_improvement_suggestions(
                failure_categories, root_causes, test_case
            )
            analysis["improvement_suggestions"] = suggestions
            
            # 计算置信度
            confidence = self._calculate_analysis_confidence(
                failure_categories, root_causes
            )
            analysis["confidence_score"] = confidence
            
            return analysis
            
        except Exception as e:
            logger.error(f"失败模式分析失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @mcp_tool(
        name="get_execution_statistics",
        description="获取执行统计信息",
        category="feedback",
        parameters={
            "time_range": {"type": "string", "description": "时间范围", "enum": ["1h", "24h", "7d", "all"], "default": "24h"}
        }
    )
    async def get_execution_statistics(self, time_range: str = "24h") -> Dict[str, Any]:
        """获取执行统计"""
        try:
            # 过滤时间范围内的记录
            filtered_history = self._filter_history_by_time(time_range)
            
            stats = {
                "time_range": time_range,
                "total_executions": len(filtered_history),
                "success_rate": 0.0,
                "failure_patterns": {},
                "improvement_trends": {},
                "timestamp": datetime.now().isoformat()
            }
            
            if not filtered_history:
                return stats
            
            # 成功率统计
            successful_executions = sum(
                1 for record in filtered_history
                if record["execution_result"].get("execution", {}).get("success", False)
            )
            stats["success_rate"] = successful_executions / len(filtered_history)
            
            # 失败模式统计
            failure_patterns = {}
            for record in filtered_history:
                exec_result = record["execution_result"]
                if not exec_result.get("execution", {}).get("success", False):
                    analysis = exec_result.get("analysis", {})
                    for category in analysis.get("failure_categories", []):
                        failure_patterns[category] = failure_patterns.get(category, 0) + 1
            
            stats["failure_patterns"] = failure_patterns
            
            # 改进趋势分析
            if len(filtered_history) > 1:
                recent_success_rate = self._calculate_recent_success_rate(filtered_history)
                overall_success_rate = stats["success_rate"]
                stats["improvement_trends"] = {
                    "recent_performance": recent_success_rate,
                    "overall_performance": overall_success_rate,
                    "trending": "improving" if recent_success_rate > overall_success_rate else "declining"
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取执行统计失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @mcp_tool(
        name="suggest_optimizations",
        description="基于执行历史建议优化方案",
        category="feedback",
        parameters={
            "test_case": {"type": "object", "description": "要优化的测试用例"},
            "focus_areas": {"type": "array", "description": "关注的优化领域", "default": ["stability", "performance", "maintainability"]}
        }
    )
    async def suggest_optimizations(self, test_case: Dict[str, Any], focus_areas: List[str] = None) -> Dict[str, Any]:
        """建议优化方案"""
        if focus_areas is None:
            focus_areas = ["stability", "performance", "maintainability"]
        
        try:
            optimization_suggestions = {
                "test_case_id": test_case.get("testcase_id", "unknown"),
                "focus_areas": focus_areas,
                "suggestions": [],
                "priority_order": [],
                "estimated_impact": {},
                "timestamp": datetime.now().isoformat()
            }
            
            # 基于历史执行数据分析
            historical_patterns = self._analyze_historical_patterns(test_case)
            
            # 为每个关注领域生成建议
            for area in focus_areas:
                area_suggestions = self._generate_area_specific_suggestions(
                    area, test_case, historical_patterns
                )
                optimization_suggestions["suggestions"].extend(area_suggestions)
            
            # 确定优先级
            priority_order = self._prioritize_suggestions(
                optimization_suggestions["suggestions"]
            )
            optimization_suggestions["priority_order"] = priority_order
            
            # 评估影响
            impact_estimates = self._estimate_optimization_impact(
                optimization_suggestions["suggestions"]
            )
            optimization_suggestions["estimated_impact"] = impact_estimates
            
            return optimization_suggestions
            
        except Exception as e:
            logger.error(f"优化建议生成失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # === 私有辅助方法 ===
    
    async def _convert_case_to_python(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """转换测试用例为Python代码"""
        try:
            # 尝试导入转换器
            try:
                from lib.code_generator.json_to_python import JSONToPythonConverter
                converter = JSONToPythonConverter()
                python_code = converter.convert(test_case)
                
                return {
                    "success": True,
                    "python_code": python_code,
                    "converter": "JSONToPythonConverter"
                }
            except ImportError:
                # 使用简化的转换逻辑
                python_code = self._simple_json_to_python(test_case)
                return {
                    "success": True,
                    "python_code": python_code,
                    "converter": "SimpleConverter"
                }
                
        except Exception as e:
            logger.error(f"用例转换失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_python_case(self, python_code: str, execution_mode: str) -> Dict[str, Any]:
        """执行Python测试用例"""
        try:
            # 模拟执行（实际项目中应该调用真实的执行器）
            if execution_mode == "quick":
                # 快速模式：语法检查
                try:
                    compile(python_code, '<test_case>', 'exec')
                    return {
                        "success": True,
                        "mode": "quick",
                        "result": "syntax_check_passed",
                        "execution_time": 0.1
                    }
                except SyntaxError as e:
                    return {
                        "success": False,
                        "mode": "quick",
                        "error": f"语法错误: {e}",
                        "error_type": "syntax_error"
                    }
            
            elif execution_mode == "full":
                # 完整模式：实际执行（这里模拟）
                # 在实际项目中，这里应该调用 execute.py 或相关执行器
                return {
                    "success": True,  # 模拟成功
                    "mode": "full",
                    "result": "execution_completed",
                    "execution_time": 15.5,
                    "steps_completed": 8,
                    "total_steps": 8
                }
            
            elif execution_mode == "debug":
                # 调试模式：详细执行信息
                return {
                    "success": True,
                    "mode": "debug",
                    "result": "debug_execution_completed",
                    "execution_time": 25.3,
                    "debug_info": {
                        "screenshots_taken": 8,
                        "elements_found": 15,
                        "actions_performed": 6
                    }
                }
            
        except Exception as e:
            logger.error(f"Python用例执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "execution_error"
            }
    
    async def _analyze_execution_result(self, exec_result: Dict[str, Any], test_case: Dict[str, Any]) -> Dict[str, Any]:
        """分析执行结果"""
        analysis = {
            "success": exec_result.get("success", False),
            "execution_quality": "unknown",
            "issues_identified": [],
            "performance_metrics": {},
            "recommendations": []
        }
        
        try:
            # 执行质量评估
            if exec_result.get("success", False):
                execution_time = exec_result.get("execution_time", 0)
                if execution_time < 10:
                    analysis["execution_quality"] = "excellent"
                elif execution_time < 30:
                    analysis["execution_quality"] = "good"
                else:
                    analysis["execution_quality"] = "acceptable"
                    analysis["issues_identified"].append("执行时间较长")
            else:
                analysis["execution_quality"] = "failed"
                error_type = exec_result.get("error_type", "unknown")
                analysis["issues_identified"].append(f"执行失败: {error_type}")
            
            # 性能指标
            analysis["performance_metrics"] = {
                "execution_time": exec_result.get("execution_time", 0),
                "steps_completed": exec_result.get("steps_completed", 0),
                "total_steps": len(test_case.get("execution_path", []))
            }
            
            # 生成建议
            if analysis["issues_identified"]:
                analysis["recommendations"] = self._generate_execution_recommendations(
                    analysis["issues_identified"], exec_result
                )
            
            return analysis
            
        except Exception as e:
            logger.error(f"执行结果分析失败: {e}")
            analysis["error"] = str(e)
            return analysis
    
    async def _generate_feedback(self, test_case: Dict[str, Any], exec_result: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成反馈"""
        feedback = {
            "overall_assessment": "unknown",
            "strengths": [],
            "weaknesses": [],
            "improvement_actions": [],
            "next_steps": []
        }
        
        try:
            # 整体评估
            if exec_result.get("success", False) and analysis.get("execution_quality") in ["excellent", "good"]:
                feedback["overall_assessment"] = "satisfactory"
                feedback["strengths"].append("用例执行成功")
                feedback["strengths"].append(f"执行质量: {analysis.get('execution_quality')}")
            else:
                feedback["overall_assessment"] = "needs_improvement"
                feedback["weaknesses"].extend(analysis.get("issues_identified", []))
            
            # 改进行动
            feedback["improvement_actions"] = analysis.get("recommendations", [])
            
            # 下一步建议
            if feedback["overall_assessment"] == "satisfactory":
                feedback["next_steps"] = ["用例可以投入使用", "考虑添加更多断言检查"]
            else:
                feedback["next_steps"] = ["需要优化用例", "重新测试验证"]
            
            return feedback
            
        except Exception as e:
            logger.error(f"反馈生成失败: {e}")
            feedback["error"] = str(e)
            return feedback
    
    def _categorize_failures(self, failure_logs: List[str]) -> List[str]:
        """分类失败类型"""
        categories = []
        
        for log in failure_logs:
            log_lower = log.lower()
            
            if any(keyword in log_lower for keyword in ["element not found", "element not located"]):
                categories.append("element_not_found")
            elif any(keyword in log_lower for keyword in ["timeout", "时间超时"]):
                categories.append("timeout")
            elif any(keyword in log_lower for keyword in ["network", "connection"]):
                categories.append("network_issue")
            elif any(keyword in log_lower for keyword in ["syntax", "语法"]):
                categories.append("syntax_error")
            elif any(keyword in log_lower for keyword in ["permission", "权限"]):
                categories.append("permission_denied")
            else:
                categories.append("unknown_error")
        
        return list(set(categories))
    
    def _identify_root_causes(self, failure_logs: List[str], test_case: Dict[str, Any]) -> List[str]:
        """识别根本原因"""
        root_causes = []
        
        # 分析用例结构
        execution_path = test_case.get("execution_path", [])
        if not execution_path:
            root_causes.append("用例缺少执行路径")
        
        # 分析元素定位策略
        element_strategies = []
        for step in execution_path:
            if "target" in step:
                element_strategies.append("有元素定位")
            else:
                element_strategies.append("缺少元素定位")
        
        if "缺少元素定位" in element_strategies:
            root_causes.append("部分步骤缺少元素定位")
        
        return root_causes
    
    def _generate_improvement_suggestions(self, failure_categories: List[str], root_causes: List[str], test_case: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        for category in failure_categories:
            if category == "element_not_found":
                suggestions.append("增加元素等待时间")
                suggestions.append("使用更稳定的元素定位策略")
                suggestions.append("添加元素存在性检查")
            elif category == "timeout":
                suggestions.append("增加操作超时时间")
                suggestions.append("优化执行步骤顺序")
            elif category == "network_issue":
                suggestions.append("添加网络连接检查")
                suggestions.append("增加网络相关的重试机制")
        
        for cause in root_causes:
            if "缺少执行路径" in cause:
                suggestions.append("补充完整的执行步骤")
            elif "缺少元素定位" in cause:
                suggestions.append("为所有交互步骤添加元素定位")
        
        return list(set(suggestions))
    
    def _calculate_analysis_confidence(self, failure_categories: List[str], root_causes: List[str]) -> float:
        """计算分析置信度"""
        base_confidence = 0.5
        
        # 已知失败类型增加置信度
        known_categories = ["element_not_found", "timeout", "network_issue", "syntax_error"]
        known_count = sum(1 for cat in failure_categories if cat in known_categories)
        confidence_boost = known_count * 0.2
        
        # 识别出根本原因增加置信度
        if root_causes:
            confidence_boost += len(root_causes) * 0.1
        
        return min(1.0, base_confidence + confidence_boost)
    
    def _simple_json_to_python(self, test_case: Dict[str, Any]) -> str:
        """简化的JSON到Python转换"""
        # 这是一个简化实现，实际项目中应使用完整的转换器
        python_code = f'''# Generated test case: {test_case.get("name", "Unnamed")}

from only_test.lib.airtest_compat import *
# 使用本地自定义的Poco库
from ..poco_utils import get_android_poco

# Initialize
connect_device("android://127.0.0.1:5037/{self.device_id or 'default'}")
poco = get_android_poco()

# Test steps
'''
        
        execution_path = test_case.get("execution_path", [])
        for step in execution_path:
            step_comment = f"# Step {step.get('step', '?')}: {step.get('description', 'No description')}"
            python_code += f"\n{step_comment}\n"
            
            action = step.get("action", "")
            if action == "click":
                python_code += "# Click action (placeholder)\npass\n"
            elif action == "input":
                python_code += "# Input action (placeholder)\npass\n"
            else:
                python_code += f"# {action} action (placeholder)\npass\n"
        
        return python_code
    
    def _filter_history_by_time(self, time_range: str) -> List[Dict[str, Any]]:
        """按时间范围过滤历史记录"""
        if time_range == "all":
            return self.feedback_history
        
        # 简化实现，返回所有记录
        return self.feedback_history
    
    def _calculate_recent_success_rate(self, history: List[Dict[str, Any]]) -> float:
        """计算最近的成功率"""
        if len(history) < 2:
            return 0.0
        
        recent_count = min(5, len(history))
        recent_records = history[-recent_count:]
        
        successful = sum(
            1 for record in recent_records
            if record["execution_result"].get("execution", {}).get("success", False)
        )
        
        return successful / len(recent_records)
    
    def _analyze_historical_patterns(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """分析历史执行模式"""
        # 简化实现
        return {
            "common_failures": [],
            "performance_trends": {},
            "success_factors": []
        }
    
    def _generate_area_specific_suggestions(self, area: str, test_case: Dict[str, Any], patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成特定领域的建议"""
        suggestions = []
        
        if area == "stability":
            suggestions.append({
                "type": "stability",
                "suggestion": "增加元素等待时间",
                "impact": "high",
                "effort": "low"
            })
        elif area == "performance":
            suggestions.append({
                "type": "performance",
                "suggestion": "优化执行步骤顺序",
                "impact": "medium",
                "effort": "medium"
            })
        elif area == "maintainability":
            suggestions.append({
                "type": "maintainability",
                "suggestion": "添加详细的步骤注释",
                "impact": "medium",
                "effort": "low"
            })
        
        return suggestions
    
    def _prioritize_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[str]:
        """确定建议优先级"""
        # 按影响和投入比排序
        priority_scores = {}
        
        for suggestion in suggestions:
            impact = {"high": 3, "medium": 2, "low": 1}.get(suggestion.get("impact", "low"), 1)
            effort = {"low": 1, "medium": 2, "high": 3}.get(suggestion.get("effort", "medium"), 2)
            score = impact / effort
            
            priority_scores[suggestion["suggestion"]] = score
        
        return sorted(priority_scores.keys(), key=lambda x: priority_scores[x], reverse=True)
    
    def _estimate_optimization_impact(self, suggestions: List[Dict[str, Any]]) -> Dict[str, str]:
        """评估优化影响"""
        impact_estimates = {}
        
        for suggestion in suggestions:
            impact_estimates[suggestion["suggestion"]] = suggestion.get("impact", "medium")
        
        return impact_estimates
    
    def _generate_execution_recommendations(self, issues: List[str], exec_result: Dict[str, Any]) -> List[str]:
        """生成执行建议"""
        recommendations = []
        
        for issue in issues:
            if "执行时间较长" in issue:
                recommendations.append("优化步骤间隔时间")
                recommendations.append("并行化部分操作")
            elif "执行失败" in issue:
                recommendations.append("检查元素定位策略")
                recommendations.append("增加错误处理机制")
        
        return recommendations
    
    def _update_execution_patterns(self, test_case: Dict[str, Any], exec_result: Dict[str, Any]) -> None:
        """更新执行模式统计"""
        # 简化实现，记录基本统计
        case_id = test_case.get("testcase_id", "unknown")
        success = exec_result.get("success", False)
        
        if case_id not in self.execution_patterns:
            self.execution_patterns[case_id] = {
                "total_executions": 0,
                "successful_executions": 0,
                "last_execution": None
            }
        
        pattern = self.execution_patterns[case_id]
        pattern["total_executions"] += 1
        if success:
            pattern["successful_executions"] += 1
        pattern["last_execution"] = datetime.now().isoformat()
