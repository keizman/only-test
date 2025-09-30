#!/usr/bin/env python3
"""
日志分析工具 - 用于分析分离存储的日志数据
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET


class LogAnalyzer:
    """日志分析器 - 支持分离存储的日志结构"""
    
    def __init__(self, session_dir: str):
        self.session_dir = Path(session_dir)
        self.unified_json_path = self.session_dir / "session_unified.json"
        self.result_dumps_dir = self.session_dir / "result_dumps"
        self.screenshots_dir = self.session_dir / "screenshots"
    
    def load_session_data(self) -> List[Dict[str, Any]]:
        """加载会话数据"""
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
        except Exception:
            return None
    
    def analyze_tool_executions(self) -> List[Dict[str, Any]]:
        """分析工具执行情况"""
        session_data = self.load_session_data()
        tool_executions = []
        
        for entry in session_data:
            if entry.get("type") == "tool_execution":
                analysis = {
                    "timestamp": entry.get("timestamp"),
                    "tool_name": entry.get("tool_name"),
                    "success": entry.get("success"),
                    "execution_time": entry.get("execution_time"),
                    "has_result": bool(entry.get("result_dump_path")),
                    "has_screenshot": bool(entry.get("screenshot_path")),
                    "result_size": entry.get("metadata", {}).get("result_size", 0),
                    "screenshot_size": entry.get("metadata", {}).get("screenshot_size", 0)
                }
                
                # 如果需要result内容分析
                if analysis["has_result"]:
                    result_content = self.get_result_content(entry["result_dump_path"])
                    if result_content:
                        analysis["elements_count"] = len(result_content.get("elements", []))
                        analysis["current_app"] = result_content.get("current_app")
                        analysis["total_elements"] = result_content.get("total_elements")
                
                tool_executions.append(analysis)
        
        return tool_executions
    
    def _count_xml_elements(self, xml_content: str) -> int:
        """统计XML中的元素数量"""
        try:
            root = ET.fromstring(xml_content)
            return len(root.findall(".//*[@clickable='true']"))
        except Exception:
            return 0
    
    def get_elements_at_step(self, step_name: str) -> List[Dict[str, Any]]:
        """获取指定步骤的元素列表"""
        session_data = self.load_session_data()
        
        for entry in session_data:
            if (entry.get("type") == "tool_execution" and 
                entry.get("tool_name", "").endswith(step_name) and
                entry.get("result_dump_path")):
                
                result_content = self.get_result_content(entry["result_dump_path"])
                if result_content and "elements" in result_content:
                    return result_content["elements"]
        
        return []
    
    def _parse_xml_elements(self, xml_content: str) -> List[Dict[str, Any]]:
        """解析XML元素为字典列表"""
        elements = []
        try:
            root = ET.fromstring(xml_content)
            for elem in root.findall(".//*[@clickable='true']"):
                element_info = {
                    "resource_id": elem.get("resource-id", ""),
                    "text": elem.get("text", ""),
                    "class": elem.get("class", ""),
                    "bounds": elem.get("bounds", ""),
                    "clickable": elem.get("clickable") == "true",
                    "enabled": elem.get("enabled") == "true"
                }
                elements.append(element_info)
        except Exception:
            pass
        
        return elements
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """生成会话摘要报告"""
        session_data = self.load_session_data()
        tool_executions = self.analyze_tool_executions()
        
        return {
            "session_info": {
                "total_events": len(session_data),
                "tool_executions": len(tool_executions),
                "result_dumps": len([t for t in tool_executions if t["has_result"]]),
                "screenshots": len([t for t in tool_executions if t["has_screenshot"]])
            },
            "execution_summary": {
                "successful_tools": len([t for t in tool_executions if t["success"]]),
                "failed_tools": len([t for t in tool_executions if not t["success"]]),
                "total_execution_time": sum(t["execution_time"] for t in tool_executions),
                "average_execution_time": sum(t["execution_time"] for t in tool_executions) / len(tool_executions) if tool_executions else 0
            },
            "storage_info": {
                "total_result_size": sum(t["result_size"] for t in tool_executions),
                "total_screenshot_size": sum(t["screenshot_size"] for t in tool_executions),
                "result_files": len(list(self.result_dumps_dir.glob("*.json"))) if self.result_dumps_dir.exists() else 0,
                "screenshot_files": len(list(self.screenshots_dir.glob("*.png"))) if self.screenshots_dir.exists() else 0
            }
        }


# 便捷函数
def analyze_session(session_dir: str) -> Dict[str, Any]:
    """分析指定会话目录"""
    analyzer = LogAnalyzer(session_dir)
    return analyzer.generate_summary_report()


def get_result_at_step(session_dir: str, step_name: str) -> Optional[Dict[str, Any]]:
    """获取指定步骤的result内容"""
    analyzer = LogAnalyzer(session_dir)
    return analyzer.get_result_content(f"result_dumps/step_{step_name}.json")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        session_dir = sys.argv[1]
        summary = analyze_session(session_dir)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print("Usage: python log_analyzer.py <session_dir>")
