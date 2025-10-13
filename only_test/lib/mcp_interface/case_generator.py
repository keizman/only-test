#!/usr/bin/env python3
"""
Only-Test Interactive Case Generator
===================================

交互式测试用例生成器
让LLM能够实时获取设备信息并生成高质量测试用例
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from lib.llm_integration.llm_client import LLMClient
from lib.test_generator import TestCaseGenerator
from .mcp_server import mcp_tool
from .device_inspector import DeviceInspector

# Additive imports for stepwise handshake
from only_test.orchestrator.step_validator import validate_step, is_tool_request
from only_test.templates.prompt_builder import OnlyTestPromptBuilder, SectionStatus

logger = logging.getLogger(__name__)


class InteractiveCaseGenerator:
    """
    交互式用例生成器
    
    核心流程：
    1. 接收用户描述
    2. 指导LLM获取设备信息
    3. LLM基于信息生成用例
    4. 验证和优化用例
    5. 输出最终结果
    """
    
    def __init__(self, device_id: Optional[str] = None):
        """初始化交互式用例生成器"""
        self.device_id = device_id
        self.device_inspector = DeviceInspector(device_id)
        self.llm_client: Optional[LLMClient] = None
        self.base_generator: Optional[TestCaseGenerator] = None
        self._initialized = False
        
        # 生成会话状态
        self.current_session = {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "description": "",
            "device_info": {},
            "generation_history": [],
            "current_case": None
        }
        
        logger.info(f"交互式用例生成器初始化 - 会话: {self.current_session['session_id']}")
    
    async def initialize(self) -> bool:
        """初始化所有组件"""
        try:
            # 初始化设备探测器
            await self.device_inspector.initialize()
            
            # 初始化LLM客户端
            self.llm_client = LLMClient()
            
            # 初始化基础生成器
            self.base_generator = TestCaseGenerator()
            
            self._initialized = True
            logger.info("交互式用例生成器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"交互式用例生成器初始化失败: {e}")
            return False
    
    @mcp_tool(
        name="start_case_generation",
        description="开始交互式用例生成流程",
        category="case_generation",
        parameters={
            "description": {"type": "string", "description": "测试需求描述"},
            "app_package": {"type": "string", "description": "目标应用包名（可选）", "default": ""},
            "complexity": {"type": "string", "description": "复杂度", "enum": ["simple", "medium", "complex"], "default": "medium"}
        }
    )
    async def start_case_generation(self, description: str, app_package: str = "", complexity: str = "medium") -> Dict[str, Any]:
        """开始用例生成流程"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # 更新会话状态
            self.current_session["description"] = description
            self.current_session["app_package"] = app_package
            self.current_session["complexity"] = complexity
            self.current_session["start_time"] = datetime.now().isoformat()
            
            # 第一步：获取设备基本信息
            device_info = await self.device_inspector.get_device_basic_info()
            self.current_session["device_info"] = device_info
            
            # 第二步：获取当前屏幕状态
            screen_info = await self.device_inspector.get_current_screen_info(include_elements=True)
            self.current_session["screen_info"] = screen_info
            
            # 第三步：分析应用状态
            app_analysis = await self.device_inspector.analyze_app_state(app_package, deep_analysis=True)
            self.current_session["app_analysis"] = app_analysis
            
            # 生成LLM引导信息
            guidance = self._create_llm_guidance(description, device_info, screen_info, app_analysis)
            
            return {
                "success": True,
                "session_id": self.current_session["session_id"],
                "description": description,
                "device_info_collected": bool(device_info),
                "screen_info_collected": bool(screen_info),
                "app_analysis_completed": bool(app_analysis),
                "next_step": "call_generate_with_context",
                "llm_guidance": guidance,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"开始用例生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @mcp_tool(
        name="generate_with_context",
        description="基于收集的设备信息生成测试用例",
        category="case_generation",
        parameters={
            "use_similar_cases": {"type": "boolean", "description": "是否参考相似用例", "default": True},
            "optimize_for_device": {"type": "boolean", "description": "是否针对设备优化", "default": True},
            "mode": {"type": "string", "description": "生成模式: batch(兼容旧方案) 或 stepwise(单步握手)", "enum": ["batch", "stepwise"], "default": "batch"},
            "max_rounds": {"type": "integer", "description": "stepwise 模式下的最大轮数", "default": 8},
            "retry_per_step": {"type": "integer", "description": "每步最多重试次数(解析/校验失败时)", "default": 2}
        }
    )
    async def generate_with_context(self, use_similar_cases: bool = True, optimize_for_device: bool = True, mode: str = "batch", max_rounds: int = 8, retry_per_step: int = 2) -> Dict[str, Any]:
        """基于上下文生成测试用例"""
        try:
            if not self.current_session["description"]:
                return {
                    "success": False,
                    "error": "请先调用 start_case_generation"
                }
            
            # 构建生成上下文
            generation_context = self._build_generation_context(use_similar_cases)

            # 新增：stepwise 单步握手模式（保持旧 batch 逻辑不变）
            if str(mode).lower() == "stepwise":
                try:
                    result = await self._run_stepwise_loop(
                        description=self.current_session["description"],
                        context=generation_context,
                        optimize_for_device=optimize_for_device,
                        max_rounds=max_rounds,
                        retry_per_step=retry_per_step,
                    )
                    return result
                except Exception as e:
                    logger.error(f"stepwise 模式失败: {e}")
                    return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

            # 兼容旧方案：一次性整案生成
            enhanced_prompt = self._create_enhanced_generation_prompt(
                self.current_session["description"],
                generation_context,
                optimize_for_device
            )
            
            # 调用LLM生成用例（batch）
            llm_response = await self._call_llm_for_generation(enhanced_prompt)
            
            if llm_response.get("success", False):
                # 解析生成的用例
                generated_case = self._parse_generated_case(llm_response["content"])
                
                # 验证和优化用例
                validation_result = await self._validate_generated_case(generated_case)
                
                # 保存生成结果
                self.current_session["current_case"] = generated_case
                self.current_session["generation_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "prompt": enhanced_prompt[:200] + "...",  # 截断保存
                    "generated_case": generated_case,
                    "validation": validation_result
                })
                
                return {
                    "success": True,
                    "session_id": self.current_session["session_id"],
                    "generated_case": generated_case,
                    "validation": validation_result,
                    "next_step": "convert_to_python" if validation_result["valid"] else "refine_case",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": llm_response.get("error", "LLM生成失败"),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"上下文生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @mcp_tool(
        name="refine_case",
        description="基于问题反馈优化测试用例",
        category="case_generation",
        parameters={
            "issues": {"type": "array", "description": "发现的问题列表"},
            "suggestions": {"type": "string", "description": "改进建议", "default": ""}
        }
    )
    async def refine_case(self, issues: List[str], suggestions: str = "") -> Dict[str, Any]:
        """优化测试用例"""
        try:
            if not self.current_session.get("current_case"):
                return {
                    "success": False,
                    "error": "没有当前用例可以优化"
                }
            
            current_case = self.current_session["current_case"]
            
            # 创建优化prompt
            refinement_prompt = self._create_refinement_prompt(
                current_case, issues, suggestions
            )
            
            # 调用LLM优化
            llm_response = await self._call_llm_for_generation(refinement_prompt)
            
            if llm_response.get("success", False):
                # 解析优化后的用例
                refined_case = self._parse_generated_case(llm_response["content"])
                
                # 验证优化结果
                validation_result = await self._validate_generated_case(refined_case)
                
                # 更新当前用例
                self.current_session["current_case"] = refined_case
                self.current_session["generation_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "action": "refinement",
                    "issues": issues,
                    "suggestions": suggestions,
                    "refined_case": refined_case,
                    "validation": validation_result
                })
                
                return {
                    "success": True,
                    "refined_case": refined_case,
                    "validation": validation_result,
                    "improvement_applied": True,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": llm_response.get("error", "优化失败")
                }
                
        except Exception as e:
            logger.error(f"用例优化失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @mcp_tool(
        name="get_generation_status",
        description="获取当前生成会话状态",
        category="session_management",
        parameters={}
    )
    async def get_generation_status(self) -> Dict[str, Any]:
        """获取生成状态"""
        return {
            "session_id": self.current_session["session_id"],
            "description": self.current_session.get("description", ""),
            "has_device_info": bool(self.current_session.get("device_info")),
            "has_screen_info": bool(self.current_session.get("screen_info")),
            "has_app_analysis": bool(self.current_session.get("app_analysis")),
            "has_current_case": bool(self.current_session.get("current_case")),
            "generation_count": len(self.current_session.get("generation_history", [])),
            "last_activity": self.current_session.get("generation_history", [{}])[-1].get("timestamp", ""),
            "timestamp": datetime.now().isoformat()
        }
    
    @mcp_tool(
        name="export_case",
        description="导出生成的测试用例",
        category="case_generation",
        parameters={
            "format": {"type": "string", "description": "导出格式", "enum": ["json", "python"], "default": "json"},
            "include_metadata": {"type": "boolean", "description": "是否包含元数据", "default": True}
        }
    )
    async def export_case(self, format: str = "json", include_metadata: bool = True) -> Dict[str, Any]:
        """导出测试用例"""
        try:
            if not self.current_session.get("current_case"):
                return {
                    "success": False,
                    "error": "没有可导出的用例"
                }
            
            current_case = self.current_session["current_case"]
            
            if format == "json":
                # JSON格式导出
                exported_case = current_case.copy()
                
                if include_metadata:
                    exported_case["_metadata"] = {
                        "generated_by": "Only-Test Interactive Generator",
                        "session_id": self.current_session["session_id"],
                        "generation_time": datetime.now().isoformat(),
                        "device_info": self.current_session.get("device_info", {}),
                        "original_description": self.current_session.get("description", "")
                    }
                
                return {
                    "success": True,
                    "format": "json",
                    "case": exported_case,
                    "filename_suggestion": f"test_case_{self.current_session['session_id']}.json"
                }
                
            elif format == "python":
                # Python格式导出（需要调用json_to_python转换器）
                try:
                    from lib.code_generator.json_to_python import JSONToPythonConverter
                    
                    converter = JSONToPythonConverter()
                    python_code = converter.convert(current_case)
                    
                    return {
                        "success": True,
                        "format": "python",
                        "code": python_code,
                        "filename_suggestion": f"test_case_{self.current_session['session_id']}.py"
                    }
                    
                except ImportError:
                    return {
                        "success": False,
                        "error": "Python代码生成器不可用"
                    }
            
        except Exception as e:
            logger.error(f"用例导出失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # === 私有辅助方法 ===
    
    def _create_llm_guidance(self, description: str, device_info: Dict, screen_info: Dict, app_analysis: Dict) -> str:
        """创建LLM引导信息"""
        guidance = f"""
# Only-Test 用例生成指导

## 用户需求
{description}

## 当前设备信息
- 设备型号: {device_info.get('model', 'Unknown')}
- Android版本: {device_info.get('android_version', 'Unknown')}
- 屏幕分辨率: {device_info.get('screen_resolution', 'Unknown')}
- 当前应用: {screen_info.get('current_app', 'Unknown')}

## 当前屏幕状态
- 总元素数: {screen_info.get('total_elements', 0)}
- 可点击元素: {screen_info.get('clickable_elements', 0)}
- 推断页面类型: {app_analysis.get('inferred_page_type', 'unknown')}
- 媒体播放状态: {app_analysis.get('media_state', {}).get('is_playing', False)}

## 可用功能分析
{json.dumps(app_analysis.get('features', {}), indent=2, ensure_ascii=False)}

## 生成建议
基于以上信息，你现在可以调用 generate_with_context 来生成针对性的测试用例。
"""
        return guidance
    
    def _build_generation_context(self, use_similar_cases: bool) -> Dict[str, Any]:
        """构建生成上下文"""
        context = {
            "device_info": self.current_session.get("device_info", {}),
            "screen_info": self.current_session.get("screen_info", {}),
            "app_analysis": self.current_session.get("app_analysis", {}),
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加相似用例（如果需要）
        if use_similar_cases:
            # TODO: 实现相似用例检索
            context["similar_cases"] = []
        
        return context
    
    def _create_enhanced_generation_prompt(self, description: str, context: Dict, optimize_for_device: bool) -> str:
        """创建增强的生成prompt"""
        
        device_optimization = ""
        if optimize_for_device:
            device_info = context.get("device_info", {})
            screen_info = context.get("screen_info", {})
            
            device_optimization = f"""
## 设备优化要求
- 目标设备: {device_info.get('model', 'Unknown')} (Android {device_info.get('android_version', 'Unknown')})
- 屏幕分辨率: {device_info.get('screen_resolution', 'Unknown')}
- 当前元素数: {screen_info.get('total_elements', 0)}
- 识别策略: {screen_info.get('element_analysis', {}).get('recognition_strategy', 'unknown')}

请根据设备特性优化生成的用例，特别注意：
1. 如果是播放状态，优先使用视觉识别
2. 根据元素数量调整等待时间
3. 考虑设备性能选择合适的操作间隔
"""
        
        # Compliance header to enforce ignoring ((...)) and MCP/tooling usage
        compliance_header = (
            "ONLY-TEST LLM CASE GENERATION DIRECTIVES\n"
            "---------------------------------------\n\n"
            "IMPORTANT COMPLIANCE RULES:\n"
            "1) Ignore any content enclosed in double parentheses like ((this is ignored)). "
            "Treat it as non-existent: do not use, quote, or act on it.\n"
            "2) Use MCP tools to analyze current screen and interact; never hallucinate elements not present in the latest analysis.\n"
            "3) Output strictly valid JSON as specified; no explanations outside code fences.\n\n"
        )

        # Refinement header: reiterate ignore rule and schema stability
        refine_header = (
            "Refinement Directives:\n"
            "1) Ignore any content enclosed in double parentheses ((...)).\n"
            "2) Keep JSON schema stable; only fix issues listed below.\n\n"
        )

        prompt = f"""
你是Only-Test框架的专业测试用例生成器。请根据以下信息生成高质量的测试用例：

## 用户需求
{description}

## 当前设备和界面信息
{json.dumps(context, indent=2, ensure_ascii=False)}

{device_optimization}

## Only-Test用例格式要求
请生成符合Only-Test框架规范的JSON格式测试用例，包含：

1. **基本信息**: testcase_id, name, description
2. **元数据**: tags, priority, device_types等
3. **执行路径**: 详细的步骤序列，每步包含page, action, target等
4. **智能判断**: 使用conditional_action处理复杂逻辑
5. **断言验证**: 必要的检查点

## 特别注意
- 基于当前屏幕信息选择合适的元素定位方式
- 如果检测到播放状态，考虑使用视觉识别策略
- 包含适当的等待时间和错误处理
- 添加有意义的注释说明每步操作的业务逻辑

请输出完整的JSON格式测试用例：
"""
        
        return compliance_header + prompt
    
    def _create_refinement_prompt(self, current_case: Dict, issues: List[str], suggestions: str) -> str:
        """创建优化prompt"""
        prompt = f"""
请优化以下Only-Test测试用例，解决发现的问题：

## 当前用例
{json.dumps(current_case, indent=2, ensure_ascii=False)}

## 发现的问题
{json.dumps(issues, indent=2, ensure_ascii=False)}

## 改进建议
{suggestions}

## 优化要求
1. 保持用例的核心功能不变
2. 修复所有标识的问题
3. 改进元素定位的准确性
4. 增强错误处理能力
5. 优化执行流程的稳定性

请输出优化后的完整JSON用例：
"""
        return refine_header + prompt
    
    async def _call_llm_for_generation(self, prompt: str) -> Dict[str, Any]:
        """调用LLM进行生成"""
        try:
            if not self.llm_client:
                return {"success": False, "error": "LLM客户端未初始化"}
            
            response = await self.llm_client.generate_completion(prompt)
            
            return {
                "success": True,
                "content": response,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_generated_case(self, llm_content: str) -> Dict[str, Any]:
        """解析LLM生成的用例内容（先严格裸 JSON，再回退提取）。"""
        try:
            # 1) 严格裸 JSON 尝试（不允许 Markdown 代码块）
            try:
                stripped = llm_content.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    return json.loads(stripped)
            except Exception:
                pass

            # 2) 回退：尝试提取代码块或包裹的大括号
            import re
            
            # 查找JSON代码块
            json_match = re.search(r'```json\n(.*?)\n```', llm_content, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                # 尝试查找大括号包围的内容
                brace_match = re.search(r'\{.*\}', llm_content, re.DOTALL)
                if brace_match:
                    json_content = brace_match.group(0)
                else:
                    json_content = llm_content
            
            # 解析JSON
            parsed_case = json.loads(json_content)
            
            return parsed_case
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return {
                "error": "JSON格式无效",
                "raw_content": llm_content[:500]  # 保存前500字符用于调试
            }
        except Exception as e:
            logger.error(f"用例解析失败: {e}")
            return {
                "error": str(e),
                "raw_content": llm_content[:500]
            }
    
    async def _validate_generated_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """验证生成的用例"""
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "score": 0
        }
        
        try:
            # 检查必需字段
            required_fields = ["testcase_id", "name", "description", "execution_path"]
            for field in required_fields:
                if field not in case:
                    validation_result["issues"].append(f"缺少必需字段: {field}")
                    validation_result["valid"] = False
            
            # 检查执行路径
            if "execution_path" in case:
                execution_path = case["execution_path"]
                if not isinstance(execution_path, list) or len(execution_path) == 0:
                    validation_result["issues"].append("执行路径为空或格式不正确")
                    validation_result["valid"] = False
                else:
                    # 检查每个步骤
                    for i, step in enumerate(execution_path):
                        if not isinstance(step, dict):
                            validation_result["issues"].append(f"步骤 {i+1} 格式不正确")
                            continue
                        
                        # 检查必需的步骤字段
                        required_step_fields = ["step", "page", "action"]
                        for field in required_step_fields:
                            if field not in step:
                                validation_result["warnings"].append(f"步骤 {i+1} 缺少字段: {field}")
            
            # 计算质量得分
            score = 100
            score -= len(validation_result["issues"]) * 20  # 每个问题扣20分
            score -= len(validation_result["warnings"]) * 5  # 每个警告扣5分
            validation_result["score"] = max(0, score)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"用例验证失败: {e}")
            return {
                "valid": False,
                "issues": [f"验证过程异常: {e}"],
                "score": 0
            }

    # === 新增：stepwise 单步握手核心实现（保持旧逻辑不变） ===
    async def _run_stepwise_loop(
        self,
        description: str,
        context: Dict[str, Any],
        optimize_for_device: bool,
        max_rounds: int = 8,
        retry_per_step: int = 2,
    ) -> Dict[str, Any]:
        """
        Plan → Execute → Verify → Append handshake.
        仅新增该路径，不影响原 batch 行为。
        """
        steps: List[Dict[str, Any]] = []
        screen = await self.device_inspector.get_current_screen_info(include_elements=True)
        errors_last_round: List[str] = []

        for i in range(1, int(max_rounds) + 1):
            # 构造核心 step prompt（使用模板模块，保持统一约束）
            core_prompt = TestCaseGenerationPrompts.get_mcp_step_guidance_prompt(
                current_step=i,
                screen_analysis_result=screen or {},
                test_objective=description,
                previous_steps=steps,
                examples=None,
            )

            # 以分区组装器注入“修复片段/brief shots”等，可按需拓展
            builder = OnlyTestPromptBuilder()
            builder.add_section("core", core_prompt, status=SectionStatus.ACTIVE)
            if errors_last_round:
                repair = "\n".join([
                    "## 故障与修复（上轮校验未通过）",
                    "请修复以下问题并重新返回单步 JSON：",
                    *[f"- {e}" for e in errors_last_round],
                ])
                builder.add_section("repair", repair, status=SectionStatus.ACTIVE)
            prompt_text = builder.build()

            # 调用 LLM 生成单步决策
            step_resp = await self._call_llm_for_generation(prompt_text)
            if not step_resp.get("success", False):
                return {"success": False, "error": step_resp.get("error", "LLM生成失败"), "timestamp": datetime.now().isoformat()}

            step_obj = self._parse_generated_case(step_resp["content"])  # 先尝试裸 JSON

            # 处理 TOOL_REQUEST
            if is_tool_request(step_obj):
                screen = await self.device_inspector.get_current_screen_info(include_elements=True)
                errors_last_round = []
                continue

            # 运行前校验（强制白名单+证据+hooks边界）
            ok, errs, chosen = validate_step(
                screen or {},
                step_obj,
                page_check_mode="soft",
                page_field="current_page",
                allowed_pages=None,
                require_evidence=True,
                enforce_hooks_boundary=True,
            )
            if not ok:
                # 在当前轮内做有限次重试
                retry = 0
                while retry < int(retry_per_step) and not ok:
                    retry += 1
                    errors_last_round = errs
                    # 重新询问（带入修复片段）
                    step_resp = await self._call_llm_for_generation(prompt_text)
                    step_obj = self._parse_generated_case(step_resp.get("content", ""))
                    ok, errs, chosen = validate_step(
                        screen or {},
                        step_obj,
                        page_check_mode="soft",
                        page_field="current_page",
                        allowed_pages=None,
                        require_evidence=True,
                        enforce_hooks_boundary=True,
                    )
                if not ok:
                    # 无法修复，退出
                    return {"success": False, "error": f"第{i}步校验失败: {errs}", "timestamp": datetime.now().isoformat()}
                errors_last_round = []

            # 执行动作
            na = (step_obj or {}).get("next_action", {})
            action = na.get("action")
            target = na.get("target", {})
            wait_after = float(na.get("wait_after", 0.8) or 0.8)
            data = na.get("data") if isinstance(na.get("data"), str) else ""

            exec_meta = await self.device_inspector.perform_ui_action(
                action=action,
                target=target,
                data=data or "",
                wait_after=wait_after,
            )

            # 验证并追加
            new_screen = await self.device_inspector.get_current_screen_info(include_elements=True)
            steps.append({
                "step": i,
                "analysis": step_obj.get("analysis", {}),
                "next_action": na,
                "evidence": step_obj.get("evidence", {}),
                "execution": {"success": bool(exec_meta.get("success", True)), "used": exec_meta.get("used"), "exec_log": exec_meta.get("exec_log", [])},
                "after_screen": {"current_page": new_screen.get("current_page"), "total_elements": new_screen.get("total_elements")},
            })

            # 准备下一轮
            screen = new_screen

        # 结束后整合为最终用例（调用 completion prompt）
        completion_prompt = TestCaseGenerationPrompts.get_mcp_completion_prompt(
            generated_steps=steps,
            test_objective=description,
            final_state=screen or {},
            examples=None,
        )
        final_resp = await self._call_llm_for_generation(completion_prompt)
        if not final_resp.get("success", False):
            return {"success": False, "error": final_resp.get("error", "LLM生成失败"), "timestamp": datetime.now().isoformat()}
        final_case = self._parse_generated_case(final_resp["content"])  # 再次优先裸 JSON

        # 可选：按 schema 校验（若依赖不存在则跳过，不报错）
        schema_validation = self._validate_final_case_schema(final_case)

        # 保存会话状态
        self.current_session["current_case"] = final_case
        self.current_session["generation_history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "stepwise_complete",
            "generated_case": final_case,
            "schema_validation": schema_validation,
        })

        return {
            "success": True,
            "session_id": self.current_session["session_id"],
            "generated_case": final_case,
            "validation": schema_validation if isinstance(schema_validation, dict) else {"valid": True},
            "next_step": "convert_to_python",
            "timestamp": datetime.now().isoformat()
        }

    def _validate_final_case_schema(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """使用 JSON Schema 验证最终用例（如果 jsonschema 可用）。保持可选、向后兼容。"""
        try:
            import json as _json
            import os as _os
            try:
                import jsonschema  # type: ignore
            except Exception:
                return {"valid": True, "note": "jsonschema 未安装，跳过严格校验"}

            schema_path = _os.path.join(_os.path.dirname(__file__), "..", "schema", "testcase_v1_1.json")
            schema_path = _os.path.abspath(schema_path)
            if not _os.path.exists(schema_path):
                return {"valid": True, "note": f"schema 文件不存在: {schema_path}"}
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = _json.load(f)
            try:
                jsonschema.validate(instance=case, schema=schema)
                return {"valid": True}
            except Exception as e:
                return {"valid": False, "error": str(e)}
        except Exception as e:
            return {"valid": False, "error": f"schema 校验异常: {e}"}
