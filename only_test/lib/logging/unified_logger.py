"""
统一日志管理器 - 支持命令行+文件双重输出
同时保持时序性和完整的XML信息保留
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from threading import Lock


class UnifiedLogger:
    """统一日志管理器 - 支持双重输出和结构化日志"""

    def __init__(self, session_id: str, log_dir: str, console_level: int = logging.INFO):
        self.session_id = session_id
        self.log_dir = Path(log_dir)
        self.session_dir = self.log_dir / f"session_{session_id}"

        # 创建必要的目录（按需创建，不创建空目录）
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # 日志文件路径
        self.unified_json_path = self.session_dir / "session_unified.json"
        self.raw_log_path = self.session_dir / "session_raw.log"

        # 分离存储目录
        self.result_dumps_dir = self.session_dir / "result_dumps"
        self.screenshots_dir = self.session_dir / "screenshots"
        self.artifacts_dir = self.session_dir / "artifacts"

        # 计数器用于生成文件名
        self._result_counter = 0
        self._screenshot_counter = 0

        # 结构化日志数据（JSON数组）
        self.structured_logs: List[Dict[str, Any]] = []
        self._lock = Lock()

        # 阶段追踪
        self.current_phase: Optional[str] = None
        self.current_round: Optional[int] = None
        self.max_rounds: Optional[int] = None

        # 会话统计
        self.session_stats = {
            "tool_calls": [],
            "llm_calls": [],
            "errors": [],
            "test_case_info": {}
        }

        # 设置Python logging
        self._setup_python_logging(console_level)

        # 初始化统一日志文件
        self._init_unified_log()
    
    def _setup_python_logging(self, console_level: int):
        """设置Python标准logging - 支持控制台+文件双重输出"""
        
        # 创建logger
        self.logger = logging.getLogger(f"only_test_session_{self.session_id}")
        self.logger.setLevel(logging.DEBUG)
        
        # 清除已有handlers
        self.logger.handlers.clear()
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 1. 控制台输出handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 2. 文件输出handler
        file_handler = logging.FileHandler(self.raw_log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 防止重复输出到root logger
        self.logger.propagate = False
    
    def _init_unified_log(self):
        """初始化统一日志文件为JSON数组格式"""
        if not self.unified_json_path.exists():
            with open(self.unified_json_path, 'w', encoding='utf-8') as f:
                f.write('[]')  # 空JSON数组
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().isoformat()

    def set_phase(self, phase: str, current_round: Optional[int] = None, max_rounds: Optional[int] = None):
        """设置当前执行阶段"""
        self.current_phase = phase
        self.current_round = current_round
        self.max_rounds = max_rounds

    def _get_phase_prefix(self) -> str:
        """获取阶段前缀"""
        if not self.current_phase:
            return ""

        if self.current_phase == "plan":
            return "[PLAN] "
        elif self.current_phase == "completion":
            return "[COMPLETION] "
        elif self.current_phase == "execution":
            if self.current_round and self.max_rounds:
                return f"[ROUND {self.current_round}/{self.max_rounds}] "
            elif self.current_round:
                return f"[ROUND {self.current_round}] "
            return "[EXECUTION] "
        else:
            return f"[{self.current_phase.upper()}] "

    def _print_and_log(self, message: str, level: str = "info"):
        """输出到控制台并记录到文件（不带时间戳前缀）"""
        prefix = self._get_phase_prefix()
        full_message = f"{prefix}{message}"

        # 输出到控制台（通过logger以保持一致性）
        # 使用_log方法直接记录，避免重复的时间戳
        import logging
        log_level = getattr(logging, level.upper(), logging.INFO)

        # 创建不带格式的输出
        print(full_message)

        # 同时写入文件（带完整格式）
        self.logger.log(log_level, message)
    
    def _save_structured_log(self, log_entry: Dict[str, Any]):
        """保存结构化日志到JSON文件"""
        with self._lock:
            # 读取现有数据
            try:
                with open(self.unified_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = []
            
            # 添加新条目
            data.append(log_entry)
            
            # 写回文件
            with open(self.unified_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def info(self, message: str, **kwargs):
        """INFO级别日志 - 双重输出"""
        prefix = self._get_phase_prefix()
        self.logger.info(f"{prefix}{message}")
        if kwargs:
            self._log_structured('info', message, **kwargs)

    def warning(self, message: str, **kwargs):
        """WARNING级别日志 - 双重输出"""
        prefix = self._get_phase_prefix()
        self.logger.warning(f"{prefix}{message}")
        if kwargs:
            self._log_structured('warning', message, **kwargs)

    def error(self, message: str, **kwargs):
        """ERROR级别日志 - 双重输出"""
        prefix = self._get_phase_prefix()
        self.logger.error(f"{prefix}{message}")
        if kwargs:
            self._log_structured('error', message, **kwargs)

    def debug(self, message: str, **kwargs):
        """DEBUG级别日志 - 双重输出"""
        prefix = self._get_phase_prefix()
        self.logger.debug(f"{prefix}{message}")
        if kwargs:
            self._log_structured('debug', message, **kwargs)
    
    def _log_structured(self, level: str, message: str, **kwargs):
        """记录结构化日志"""
        log_entry = {
            "timestamp": self._get_timestamp(),
            "level": level,
            "message": message,
            **kwargs
        }
        self._save_structured_log(log_entry)
    
    def log_session_start(self, metadata: Dict[str, Any]):
        """记录会话开始"""
        self.info(f"Session {self.session_id} started")
        
        log_entry = {
            "timestamp": self._get_timestamp(),
            "type": "session_start",
            "session_id": self.session_id,
            "metadata": metadata
        }
        self._save_structured_log(log_entry)
    
    def log_tool_execution(self, tool_name: str, success: bool, result: Any,
                          execution_time: float, error: Optional[str] = None,
                          screenshot_data: Optional[bytes] = None):
        """记录工具执行 - 支持result和截图分离存储"""

        status = "SUCCESS" if success else "FAILED"
        self.info(f"Tool {tool_name} executed: {status} ({execution_time:.3f}s)")

        # 追踪工具调用
        self.track_tool_call(tool_name, execution_time, success)

        # 显示工具执行摘要
        if success and result:
            self._log_tool_result_summary(tool_name, result)

        # 创建简化的result用于主日志（移除大型数据）
        simplified_result = self._simplify_result_for_main_log(result)
        
        log_entry = {
            "timestamp": self._get_timestamp(),
            "type": "tool_execution",
            "tool_name": tool_name,
            "success": success,
            "execution_time": execution_time,
            "result_summary": simplified_result,  # 简化的result摘要
            "error": error
        }
        
        # 处理完整result分离存储
        if result:
            result_path = self.save_result_dump(result, tool_name)
            if result_path:
                log_entry["result_dump_path"] = result_path
                log_entry["metadata"] = log_entry.get("metadata", {})
                # 计算result大小
                import json
                result_json = json.dumps(result, ensure_ascii=False)
                log_entry["metadata"]["result_size"] = len(result_json)
        
        # 处理截图分离存储
        if screenshot_data:
            screenshot_path = self.save_screenshot(screenshot_data, tool_name)
            log_entry["screenshot_path"] = screenshot_path
            log_entry["metadata"] = log_entry.get("metadata", {})
            log_entry["metadata"]["screenshot_size"] = len(screenshot_data)
        
        self._save_structured_log(log_entry)
    
    def _log_tool_result_summary(self, tool_name: str, result: Any):
        """显示工具执行结果摘要"""
        if not isinstance(result, dict):
            return

        if "get_current_screen_info" in tool_name or "screen_info" in tool_name:
            self._log_screen_info_summary(result)
        elif "start_app" in tool_name:
            self._log_start_app_summary(result)
        elif "perform_ui_action" in tool_name or "perform_and_verify" in tool_name:
            self._log_ui_action_summary(result)

    def _log_screen_info_summary(self, result: Dict[str, Any]):
        """显示屏幕信息摘要"""
        total_elements = result.get("total_elements", 0)
        clickable_elements = result.get("clickable_elements", 0)
        current_page = result.get("current_page", "未知页面")
        media_playing = result.get("media_playing", False)

        self._print_and_log(f"├─ 元素总数: {total_elements} (可点击: {clickable_elements})")
        self._print_and_log(f"├─ 当前页面: {current_page}")
        self._print_and_log(f"└─ 媒体播放: {'是' if media_playing else '否'}")

        # 广告信息
        if "ads_info" in result:
            ads_info = result["ads_info"]
            if isinstance(ads_info, dict):
                has_ads = ads_info.get("confidence", 0) > 0.5
                if has_ads:
                    self._print_and_log(f"   └─ 广告检测: 检测到广告 (置信度: {ads_info.get('confidence', 0):.2f})")

    def _log_start_app_summary(self, result: Dict[str, Any]):
        """显示应用启动摘要"""
        success = result.get("success", False)
        app_name = result.get("app_name", "未知应用")

        status = "成功" if success else "失败"
        self._print_and_log(f"└─ 启动{app_name}: {status}")

    def _log_ui_action_summary(self, result: Dict[str, Any]):
        """显示UI操作摘要"""
        action = result.get("action", "未知操作")
        success = result.get("success", False)
        reason = result.get("reason", "")

        status = "成功" if success else "失败"
        self._print_and_log(f"├─ 操作: {action}")
        self._print_and_log(f"├─ 状态: {status}")
        if reason:
            self._print_and_log(f"└─ 原因: {reason}")

    def _simplify_result_for_main_log(self, result: Any) -> Any:
        """简化result内容用于主日志显示"""
        if not isinstance(result, dict):
            return result

        simplified = {}

        # 保留关键的摘要信息
        key_fields = [
            "timestamp", "analysis_type", "analysis_round", "current_app",
            "current_activity", "current_page", "total_elements", "clickable_elements",
            "media_playing", "success", "error", "confidence"
        ]

        for key in key_fields:
            if key in result:
                simplified[key] = result[key]

        # 如果有elements数组，只保留数量信息
        if "elements" in result and isinstance(result["elements"], list):
            simplified["elements_count"] = len(result["elements"])
            # 可选：保留前3个元素作为示例
            if result["elements"]:
                simplified["elements_sample"] = result["elements"][:3]

        # 保留ads_info但简化
        if "ads_info" in result:
            ads_info = result["ads_info"]
            if isinstance(ads_info, dict):
                simplified["ads_info"] = {
                    "confidence": ads_info.get("confidence"),
                    "auto_close_attempts": ads_info.get("auto_close_attempts"),
                    "auto_closed": ads_info.get("auto_closed")
                }

        return simplified if simplified else result
    
    def log_screen_analysis(self, analysis_result: Dict[str, Any], 
                           xml_dump: Optional[str] = None, 
                           screenshot_path: Optional[str] = None):
        """记录屏幕分析结果"""
        
        elements_count = len(analysis_result.get('elements_detected', []))
        self.info(f"Screen analyzed: {elements_count} elements detected")
        
        log_entry = {
            "timestamp": self._get_timestamp(),
            "type": "screen_analysis",
            "analysis_result": analysis_result
        }
        
        if xml_dump:
            log_entry["xml_dump"] = xml_dump
            self.debug(f"XML dump included in screen analysis (length: {len(xml_dump)})")
        
        if screenshot_path:
            log_entry["screenshot_path"] = screenshot_path
        
        self._save_structured_log(log_entry)
    
    def log_error_detailed(self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None,
                          suggestion: Optional[str] = None, error_file: Optional[str] = None):
        """详细错误日志 - 内联显示错误信息"""
        self._print_and_log(f"ERROR: {error_type}", level="error")
        self._print_and_log(f"├─ 消息: {message}", level="error")

        if details:
            self._print_and_log(f"├─ 详情:", level="error")
            for key, value in details.items():
                self._print_and_log(f"│  ├─ {key}: {value}", level="error")

        if suggestion:
            self._print_and_log(f"├─ 建议: {suggestion}", level="error")

        if error_file:
            self._print_and_log(f"└─ 错误文件: {error_file}", level="error")
        else:
            self._print_and_log(f"└─ (无额外信息)", level="error")

        # 记录到统计
        self.track_error(error_type, message)

        # 记录结构化日志
        self._log_structured('error', message, error_type=error_type, details=details,
                            suggestion=suggestion, error_file=error_file)

    def log_llm_action_error(self, intent: str, error_message: str, element_info: Optional[Dict[str, Any]] = None):
        """LLM操作错误日志"""
        self._print_and_log(f"LLM ACTION ERROR", level="error")
        self._print_and_log(f"├─ 意图: {intent}", level="error")
        self._print_and_log(f"├─ 错误: {error_message}", level="error")

        if element_info:
            self._print_and_log(f"└─ 目标元素:", level="error")
            for key, value in element_info.items():
                self._print_and_log(f"   ├─ {key}: {value}", level="error")

        self.track_error("llm_action_error", error_message)

    def log_llm_interaction(self, prompt: str, response: str, model: str,
                           execution_time: float, tokens_used: Optional[int] = None):
        """记录LLM交互"""

        self.info(f"LLM {model} responded ({execution_time:.3f}s, tokens: {tokens_used or 'N/A'})")

        # 追踪统计
        self.track_llm_call(model, execution_time, tokens_used)

        log_entry = {
            "timestamp": self._get_timestamp(),
            "type": "llm_interaction",
            "model": model,
            "execution_time": execution_time,
            "tokens_used": tokens_used,
            "prompt": prompt,
            "response": response
        }
        self._save_structured_log(log_entry)
    
    def log_test_step(self, step_number: int, action: str, target: Dict[str, Any],
                     success: bool, reason: str, xml_dump: Optional[str] = None):
        """记录测试步骤执行"""
        
        status = "SUCCESS" if success else "FAILED"
        self.info(f"Step {step_number}: {action} - {status}")
        self.info(f"Reason: {reason}")
        
        log_entry = {
            "timestamp": self._get_timestamp(),
            "type": "test_step",
            "step_number": step_number,
            "action": action,
            "target": target,
            "success": success,
            "reason": reason
        }
        
        if xml_dump:
            log_entry["xml_dump"] = xml_dump
        
        self._save_structured_log(log_entry)
    
    def save_result_dump(self, result_content: Any, step_name: str = None) -> Optional[str]:
        """保存result内容并返回相对路径"""
        if not result_content:
            return None
            
        if not self.result_dumps_dir.exists():
            self.result_dumps_dir.mkdir(exist_ok=True)
        
        self._result_counter += 1
        if step_name:
            filename = f"step_{self._result_counter:03d}_{step_name}.json"
        else:
            filename = f"step_{self._result_counter:03d}_result.json"
        
        result_path = self.result_dumps_dir / filename
        
        # 将result内容序列化为JSON
        import json
        result_json = json.dumps(result_content, ensure_ascii=False, indent=2)
        with open(result_path, 'w', encoding='utf-8') as f:
            f.write(result_json)
        
        # 返回相对于session目录的路径
        relative_path = f"result_dumps/{filename}"
        self.debug(f"Result dump saved: {relative_path} (size: {len(result_json)})")
        return relative_path
    
    def save_screenshot(self, screenshot_data: bytes, step_name: str = None) -> str:
        """保存截图并返回相对路径"""
        if not self.screenshots_dir.exists():
            self.screenshots_dir.mkdir(exist_ok=True)
        
        self._screenshot_counter += 1
        if step_name:
            filename = f"step_{self._screenshot_counter:03d}_{step_name}.png"
        else:
            filename = f"step_{self._screenshot_counter:03d}_screenshot.png"
        
        screenshot_path = self.screenshots_dir / filename
        with open(screenshot_path, 'wb') as f:
            f.write(screenshot_data)
        
        # 返回相对于session目录的路径
        relative_path = f"screenshots/{filename}"
        self.debug(f"Screenshot saved: {relative_path} (size: {len(screenshot_data)})")
        return relative_path
    
    def track_tool_call(self, tool_name: str, execution_time: float, success: bool):
        """追踪工具调用"""
        self.session_stats["tool_calls"].append({
            "tool_name": tool_name,
            "execution_time": execution_time,
            "success": success,
            "timestamp": self._get_timestamp()
        })

    def track_llm_call(self, model: str, execution_time: float, tokens_used: Optional[int] = None):
        """追踪LLM调用"""
        self.session_stats["llm_calls"].append({
            "model": model,
            "execution_time": execution_time,
            "tokens_used": tokens_used,
            "timestamp": self._get_timestamp()
        })

    def track_error(self, error_type: str, message: str):
        """追踪错误"""
        self.session_stats["errors"].append({
            "error_type": error_type,
            "message": message,
            "timestamp": self._get_timestamp()
        })

    def set_test_case_info(self, test_case_name: str, total_steps: int):
        """设置测试用例信息"""
        self.session_stats["test_case_info"] = {
            "name": test_case_name,
            "total_steps": total_steps
        }

    def log_session_summary(self):
        """输出会话统计摘要"""
        self._print_and_log(f"\n{'='*60}")
        self._print_and_log(f"会话统计摘要")
        self._print_and_log(f"{'='*60}")

        # 工具调用统计
        tool_calls = self.session_stats["tool_calls"]
        if tool_calls:
            total_tools = len(tool_calls)
            success_tools = sum(1 for t in tool_calls if t["success"])
            total_tool_time = sum(t["execution_time"] for t in tool_calls)

            self._print_and_log(f"工具调用:")
            self._print_and_log(f"├─ 总计: {total_tools} 次")
            self._print_and_log(f"├─ 成功: {success_tools} 次")
            self._print_and_log(f"├─ 失败: {total_tools - success_tools} 次")
            self._print_and_log(f"└─ 总耗时: {total_tool_time:.2f}s")

            # 按工具类型统计
            tool_stats = {}
            for t in tool_calls:
                name = t["tool_name"]
                if name not in tool_stats:
                    tool_stats[name] = {"count": 0, "time": 0}
                tool_stats[name]["count"] += 1
                tool_stats[name]["time"] += t["execution_time"]

            self._print_and_log(f"   按工具分类:")
            for name, stats in tool_stats.items():
                self._print_and_log(f"   ├─ {name}: {stats['count']}次 ({stats['time']:.2f}s)")

        # LLM调用统计
        llm_calls = self.session_stats["llm_calls"]
        if llm_calls:
            total_llm = len(llm_calls)
            total_llm_time = sum(c["execution_time"] for c in llm_calls)
            total_tokens = sum(c["tokens_used"] or 0 for c in llm_calls)

            self._print_and_log(f"LLM调用:")
            self._print_and_log(f"├─ 总计: {total_llm} 次")
            self._print_and_log(f"├─ 总耗时: {total_llm_time:.2f}s")
            self._print_and_log(f"└─ 总tokens: {total_tokens}")

        # 错误统计
        errors = self.session_stats["errors"]
        if errors:
            self._print_and_log(f"错误:")
            self._print_and_log(f"├─ 总计: {len(errors)} 个")

            # 按错误类型统计
            error_types = {}
            for e in errors:
                etype = e["error_type"]
                if etype not in error_types:
                    error_types[etype] = 0
                error_types[etype] += 1

            self._print_and_log(f"└─ 按类型:")
            for etype, count in error_types.items():
                self._print_and_log(f"   ├─ {etype}: {count}次")

        # 测试用例信息
        test_case = self.session_stats["test_case_info"]
        if test_case:
            self._print_and_log(f"测试用例:")
            self._print_and_log(f"├─ 名称: {test_case.get('name', 'N/A')}")
            self._print_and_log(f"└─ 步骤数: {test_case.get('total_steps', 'N/A')}")

        self._print_and_log(f"{'='*60}\n")

    def log_session_end(self, summary: Dict[str, Any]):
        """记录会话结束"""
        self.info(f"Session {self.session_id} completed")

        # 输出统计摘要
        self.log_session_summary()

        log_entry = {
            "timestamp": self._get_timestamp(),
            "type": "session_end",
            "session_id": self.session_id,
            "summary": summary,
            "statistics": self.session_stats
        }
        self._save_structured_log(log_entry)
    
    def get_structured_logs(self) -> List[Dict[str, Any]]:
        """获取所有结构化日志"""
        try:
            with open(self.unified_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def get_result_content(self, result_path: str) -> Optional[Dict[str, Any]]:
        """根据相对路径读取result内容"""
        try:
            full_path = self.session_dir / result_path
            if full_path.exists():
                import json
                with open(full_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.error(f"Failed to read result from {result_path}: {e}")
            return None
    
    def get_screenshot_path(self, screenshot_path: str) -> Optional[Path]:
        """根据相对路径获取截图的完整路径"""
        try:
            full_path = self.session_dir / screenshot_path
            return full_path if full_path.exists() else None
        except Exception:
            return None
    
    def log_element_selection(self, intent: str, candidates: List[Dict[str, Any]],
                             selected_element: Dict[str, Any], reason: str,
                             confidence: float):
        """记录元素选择决策 - 详细版本"""
        self._print_and_log(f"元素选择决策:")
        self._print_and_log(f"├─ 意图: {intent}")
        self._print_and_log(f"├─ 候选元素: {len(candidates)} 个")

        # 显示候选列表
        for i, candidate in enumerate(candidates):
            is_selected = candidate.get("id") == selected_element.get("id")
            marker = "[SELECTED] " if is_selected else "           "
            element_text = candidate.get("text", "")[:30]
            element_type = candidate.get("type", "unknown")
            self._print_and_log(f"│  {marker}{i+1}. {element_type}: {element_text}")

        self._print_and_log(f"├─ 选择原因: {reason}")
        self._print_and_log(f"└─ 置信度: {confidence:.2f}")

        # 记录结构化日志
        self._log_structured('info', 'Element selection', intent=intent,
                            candidates_count=len(candidates),
                            selected_element=selected_element,
                            reason=reason, confidence=confidence)

    def log_element_selection_simple(self, intent: str, selected_element: Dict[str, Any],
                                     reason: str, confidence: Optional[float] = None):
        """记录元素选择决策 - 简化版本（无候选列表）"""
        element_text = selected_element.get("text", "")[:40]
        element_type = selected_element.get("type", "unknown")

        self._print_and_log(f"选中元素: {element_type} - {element_text}")
        self._print_and_log(f"├─ 意图: {intent}")
        self._print_and_log(f"├─ 原因: {reason}")
        if confidence is not None:
            self._print_and_log(f"└─ 置信度: {confidence:.2f}")
        else:
            self._print_and_log(f"└─ (无置信度信息)")

        # 记录结构化日志
        self._log_structured('info', 'Element selection (simple)', intent=intent,
                            selected_element=selected_element, reason=reason, confidence=confidence)

    def close(self):
        """关闭日志记录器"""
        for handler in self.logger.handlers:
            handler.close()
        self.logger.handlers.clear()


# 全局日志管理器实例
_global_logger: Optional[UnifiedLogger] = None
_logger_lock = Lock()


def get_logger(session_id: str = None, log_dir: str = None, 
               console_level: int = logging.INFO) -> UnifiedLogger:
    """获取全局日志管理器实例"""
    global _global_logger
    
    with _logger_lock:
        if _global_logger is None and session_id and log_dir:
            _global_logger = UnifiedLogger(session_id, log_dir, console_level)
        elif _global_logger is None:
            raise ValueError("Logger not initialized. Call get_logger with session_id and log_dir first.")
        
        return _global_logger


def close_logger():
    """关闭全局日志管理器"""
    global _global_logger
    
    with _logger_lock:
        if _global_logger:
            _global_logger.close()
            _global_logger = None
