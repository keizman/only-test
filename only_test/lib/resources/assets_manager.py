#!/usr/bin/env python3
"""
测试资源管理器

负责保存截图、识别结果等测试执行过程中的资源文件
按照 {pkg_name}_{phone_name} 规则组织文件结构
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import base64


class AssetsManager:
    """测试资源管理器"""
    
    def __init__(self, base_assets_dir: str = "assets"):
        """
        初始化资源管理器
        
        Args:
            base_assets_dir: 资源文件基础目录
        """
        self.base_assets_dir = Path(base_assets_dir)
        self.base_assets_dir.mkdir(exist_ok=True)
        
        self.current_session = None
        self.session_path = None
        
    def start_session(self, app_package: str, device_name: str, testcase_id: str) -> str:
        """
        启动新的测试会话
        
        Args:
            app_package: 应用包名
            device_name: 设备名称  
            testcase_id: 测试用例ID
            
        Returns:
            str: 会话目录路径
        """
        # 清理名称中的特殊字符
        clean_app = app_package.replace(".", "_").replace("-", "_")
        clean_device = device_name.replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
        
        # 创建会话目录
        session_dir = f"{clean_app}_{clean_device}"
        self.session_path = self.base_assets_dir / session_dir
        self.session_path.mkdir(exist_ok=True)
        
        # 初始化会话信息
        self.current_session = {
            "session_id": f"{testcase_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "app_package": app_package,
            "device_name": device_name,
            "testcase_id": testcase_id,
            "start_time": datetime.now().isoformat(),
            "session_path": str(self.session_path),
            "assets_saved": []
        }
        
        # 保存会话信息
        session_info_file = self.session_path / "session_info.json"
        with open(session_info_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_session, f, ensure_ascii=False, indent=2)
        
        return str(self.session_path)
    
    def save_screenshot(self, 
                       screenshot_data: bytes, 
                       step_number: int,
                       action_type: str,
                       timing: str = "after",
                       metadata: Optional[Dict] = None) -> str:
        """
        保存步骤截图
        
        Args:
            screenshot_data: 截图二进制数据
            step_number: 步骤编号
            action_type: 动作类型 (click, input, wait等)
            timing: 执行时机 (before, after)
            metadata: 额外元数据
            
        Returns:
            str: 截图文件相对路径
        """
        if not self.current_session:
            raise RuntimeError("请先调用 start_session() 启动会话")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 毫秒精度
        filename = f"step{step_number:02d}_{action_type}_{timing}_{timestamp}.png"
        
        # 保存截图文件
        screenshot_path = self.session_path / filename
        with open(screenshot_path, 'wb') as f:
            f.write(screenshot_data)
        
        # 生成相对路径
        relative_path = f"{self.session_path.name}/{filename}"
        
        # 记录资源信息
        asset_info = {
            "type": "screenshot",
            "step_number": step_number,
            "action_type": action_type,
            "timing": timing,
            "filename": filename,
            "relative_path": relative_path,
            "absolute_path": str(screenshot_path),
            "timestamp": timestamp,
            "file_size": len(screenshot_data),
            "metadata": metadata or {}
        }
        
        self.current_session["assets_saved"].append(asset_info)
        self._update_session_info()
        
        return relative_path
    
    def save_element_screenshot(self,
                               screenshot_data: bytes,
                               step_number: int,
                               element_type: str,
                               element_info: Dict,
                               recognition_method: str = "xml") -> str:
        """
        保存元素识别截图
        
        Args:
            screenshot_data: 截图数据
            step_number: 步骤编号
            element_type: 元素类型 (button, input, text等)
            element_info: 元素信息 (坐标、文本等)
            recognition_method: 识别方法 (xml, visual, hybrid)
            
        Returns:
            str: 截图文件相对路径
        """
        if not self.current_session:
            raise RuntimeError("请先调用 start_session() 启动会话")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"step{step_number:02d}_element_{element_type}_{timestamp}.png"
        
        # 保存截图文件
        screenshot_path = self.session_path / filename
        with open(screenshot_path, 'wb') as f:
            f.write(screenshot_data)
        
        # 生成相对路径
        relative_path = f"{self.session_path.name}/{filename}"
        
        # 记录资源信息
        asset_info = {
            "type": "element_screenshot",
            "step_number": step_number,
            "element_type": element_type,
            "recognition_method": recognition_method,
            "filename": filename,
            "relative_path": relative_path,
            "absolute_path": str(screenshot_path),
            "timestamp": timestamp,
            "file_size": len(screenshot_data),
            "element_info": element_info
        }
        
        self.current_session["assets_saved"].append(asset_info)
        self._update_session_info()
        
        return relative_path
    
    def save_omniparser_result(self,
                              omniparser_data: Dict,
                              step_number: int,
                              original_image_path: Optional[str] = None) -> str:
        """
        保存Omniparser识别结果
        
        Args:
            omniparser_data: Omniparser识别结果数据
            step_number: 步骤编号
            original_image_path: 原始图片路径
            
        Returns:
            str: 结果文件相对路径
        """
        if not self.current_session:
            raise RuntimeError("请先调用 start_session() 启动会话")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"step{step_number:02d}_omni_result_{timestamp}.json"
        
        # 准备保存的数据
        save_data = {
            "step_number": step_number,
            "timestamp": timestamp,
            "original_image": original_image_path,
            "recognition_result": omniparser_data,
            "metadata": {
                "elements_count": len(omniparser_data.get("elements", [])),
                "confidence_avg": self._calculate_avg_confidence(omniparser_data),
                "recognition_time": omniparser_data.get("processing_time", 0)
            }
        }
        
        # 保存结果文件
        result_path = self.session_path / filename
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        # 生成相对路径
        relative_path = f"{self.session_path.name}/{filename}"
        
        # 记录资源信息
        asset_info = {
            "type": "omniparser_result",
            "step_number": step_number,
            "filename": filename,
            "relative_path": relative_path,
            "absolute_path": str(result_path),
            "timestamp": timestamp,
            "file_size": result_path.stat().st_size,
            "elements_recognized": len(omniparser_data.get("elements", []))
        }
        
        self.current_session["assets_saved"].append(asset_info)
        self._update_session_info()
        
        return relative_path
    
    def save_execution_log(self, step_number: int, step_data: Dict, result: Dict) -> str:
        """
        保存步骤执行日志
        
        Args:
            step_number: 步骤编号
            step_data: 步骤配置数据
            result: 执行结果
            
        Returns:
            str: 日志文件相对路径
        """
        if not self.current_session:
            raise RuntimeError("请先调用 start_session() 启动会话")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        log_entry = {
            "step_number": step_number,
            "timestamp": timestamp,
            "step_configuration": step_data,
            "execution_result": result,
            "execution_time": result.get("execution_time", 0),
            "status": result.get("status", "unknown"),
            "error_info": result.get("error", None)
        }
        
        # 追加到执行日志文件（JSON 对象 + entries 数组）
        log_file = self.session_path / "execution_log.json"
        if log_file.exists():
            try:
                data = json.loads(log_file.read_text(encoding='utf-8'))
            except Exception:
                data = {}
        else:
            data = {}

        if not isinstance(data, dict):
            data = {}
        data.setdefault("session_id", self.current_session.get("session_id"))
        entries = data.get("entries")
        if not isinstance(entries, list):
            entries = []
        entries.append(log_entry)
        data["entries"] = entries

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return f"{self.session_path.name}/execution_log.json"
    
    def update_json_testcase_with_assets(self, json_file: str, output_file: Optional[str] = None) -> str:
        """
        将保存的资源信息更新到JSON测试用例中
        
        Args:
            json_file: 原始JSON文件路径
            output_file: 输出JSON文件路径
            
        Returns:
            str: 更新后的JSON文件路径
        """
        if not self.current_session:
            raise RuntimeError("请先调用 start_session() 启动会话")
        
        # 读取原始JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            testcase_data = json.load(f)
        
        # 按步骤组织资源
        assets_by_step = self._organize_assets_by_step()
        
        # 更新执行路径中的资源信息
        execution_path = testcase_data.get("execution_path", [])
        for step in execution_path:
            step_num = step.get("step", 0)
            if step_num in assets_by_step:
                step["execution_assets"] = assets_by_step[step_num]
        
        # 添加会话级别的资源信息
        testcase_data["session_assets"] = {
            "session_info": self.current_session,
            "assets_summary": self._generate_assets_summary(),
            "total_screenshots": len([a for a in self.current_session["assets_saved"] if a["type"] == "screenshot"]),
            "total_elements": len([a for a in self.current_session["assets_saved"] if a["type"] == "element_screenshot"]),
            "total_omni_results": len([a for a in self.current_session["assets_saved"] if a["type"] == "omniparser_result"])
        }
        
        # 保存更新后的JSON
        if output_file is None:
            output_file = json_file
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(testcase_data, f, ensure_ascii=False, indent=2)
        
        return output_file
    
    def generate_assets_report(self) -> Dict[str, Any]:
        """
        生成资源使用报告
        
        Returns:
            Dict: 资源报告
        """
        if not self.current_session:
            return {"error": "没有活跃会话"}
        
        assets = self.current_session["assets_saved"]
        
        # 统计信息
        stats = {
            "total_assets": len(assets),
            "screenshots": len([a for a in assets if a["type"] == "screenshot"]),
            "element_screenshots": len([a for a in assets if a["type"] == "element_screenshot"]),
            "omniparser_results": len([a for a in assets if a["type"] == "omniparser_result"]),
            "total_size_bytes": sum(a.get("file_size", 0) for a in assets),
            "session_duration": self._calculate_session_duration()
        }
        
        # 按步骤分组
        steps_assets = self._organize_assets_by_step()
        
        # 识别方法统计
        recognition_stats = {}
        for asset in assets:
            if asset["type"] == "element_screenshot":
                method = asset.get("recognition_method", "unknown")
                recognition_stats[method] = recognition_stats.get(method, 0) + 1
        
        return {
            "session_info": self.current_session,
            "statistics": stats,
            "assets_by_step": steps_assets,
            "recognition_methods": recognition_stats,
            "storage_path": str(self.session_path),
            "generated_at": datetime.now().isoformat()
        }
    
    def cleanup_old_assets(self, keep_days: int = 7) -> Dict[str, Any]:
        """
        清理旧的资源文件
        
        Args:
            keep_days: 保留天数
            
        Returns:
            Dict: 清理结果
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        cleaned_dirs = []
        cleaned_size = 0
        
        for session_dir in self.base_assets_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            session_info_file = session_dir / "session_info.json"
            if not session_info_file.exists():
                continue
            
            try:
                with open(session_info_file, 'r', encoding='utf-8') as f:
                    session_info = json.load(f)
                
                session_time = datetime.fromisoformat(session_info.get("start_time", ""))
                if session_time < cutoff_date:
                    # 计算目录大小
                    dir_size = sum(f.stat().st_size for f in session_dir.rglob('*') if f.is_file())
                    cleaned_size += dir_size
                    
                    # 删除目录
                    shutil.rmtree(session_dir)
                    cleaned_dirs.append({
                        "session_id": session_info.get("session_id"),
                        "app_package": session_info.get("app_package"),
                        "size_bytes": dir_size
                    })
                    
            except Exception as e:
                print(f"清理目录 {session_dir} 时出错: {e}")
        
        return {
            "cleaned_sessions": len(cleaned_dirs),
            "cleaned_size_bytes": cleaned_size,
            "cleaned_size_mb": round(cleaned_size / 1024 / 1024, 2),
            "cleaned_directories": cleaned_dirs
        }
    
    def _calculate_avg_confidence(self, omniparser_data: Dict) -> float:
        """计算平均置信度"""
        elements = omniparser_data.get("elements", [])
        if not elements:
            return 0.0
        
        confidences = [elem.get("confidence", 0) for elem in elements]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _organize_assets_by_step(self) -> Dict[int, List[Dict]]:
        """按步骤组织资源"""
        assets_by_step = {}
        for asset in self.current_session["assets_saved"]:
            step_num = asset.get("step_number", 0)
            if step_num not in assets_by_step:
                assets_by_step[step_num] = []
            assets_by_step[step_num].append(asset)
        return assets_by_step
    
    def _generate_assets_summary(self) -> Dict[str, Any]:
        """生成资源摘要"""
        assets = self.current_session["assets_saved"]
        
        return {
            "first_asset": assets[0]["timestamp"] if assets else None,
            "last_asset": assets[-1]["timestamp"] if assets else None,
            "asset_types": list(set(a["type"] for a in assets)),
            "steps_covered": list(set(a.get("step_number", 0) for a in assets)),
            "total_file_size": sum(a.get("file_size", 0) for a in assets),
            "avg_file_size": sum(a.get("file_size", 0) for a in assets) / len(assets) if assets else 0
        }
    
    def _calculate_session_duration(self) -> float:
        """计算会话持续时间（秒）"""
        if not self.current_session["assets_saved"]:
            return 0.0
        
        start_time = datetime.fromisoformat(self.current_session["start_time"])
        last_asset = self.current_session["assets_saved"][-1]
        last_time = datetime.strptime(last_asset["timestamp"], "%Y%m%d_%H%M%S_%f")
        
        return (last_time - start_time).total_seconds()
    
    def _update_session_info(self):
        """更新会话信息文件"""
        session_info_file = self.session_path / "session_info.json"
        with open(session_info_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_session, f, ensure_ascii=False, indent=2)


def main():
    """命令行工具入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试资源管理工具")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", help="清理N天前的资源文件")
    parser.add_argument("--report", help="生成指定会话的资源报告")
    parser.add_argument("--list-sessions", action="store_true", help="列出所有会话")
    
    args = parser.parse_args()
    
    assets_manager = AssetsManager()
    
    if args.cleanup:
        print(f"🧹 清理 {args.cleanup} 天前的资源文件...")
        result = assets_manager.cleanup_old_assets(args.cleanup)
        print(f"✅ 清理完成:")
        print(f"   清理会话数: {result['cleaned_sessions']}")
        print(f"   释放空间: {result['cleaned_size_mb']} MB")
    
    elif args.list_sessions:
        print("📋 现有测试会话:")
        for session_dir in assets_manager.base_assets_dir.iterdir():
            if session_dir.is_dir():
                session_info_file = session_dir / "session_info.json"
                if session_info_file.exists():
                    try:
                        with open(session_info_file, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                        print(f"  📁 {session_dir.name}")
                        print(f"     应用: {info.get('app_package', 'Unknown')}")
                        print(f"     设备: {info.get('device_name', 'Unknown')}")
                        print(f"     时间: {info.get('start_time', 'Unknown')}")
                        print(f"     资源数: {len(info.get('assets_saved', []))}")
                        print()
                    except Exception as e:
                        print(f"  ❌ {session_dir.name}: 读取失败 - {e}")


if __name__ == "__main__":
    main()
