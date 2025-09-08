#!/usr/bin/env python3
"""
集成测试执行工具

支持JSON转Python + Airtest + Pytest + Allure的完整工作流
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from lib.config_manager import ConfigManager
from lib.code_generator.json_to_python import JSONToPythonConverter


class IntegratedTestExecutor:
    """集成测试执行器"""
    
    def __init__(self, project_root: Optional[str] = None):
        """
        初始化执行器
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.json_dir = self.project_root / "testcases" / "generated"
        self.python_dir = self.project_root / "testcases" / "python"
        self.reports_dir = self.project_root / "reports"
        
        # 确保目录存在
        self.python_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        (self.reports_dir / "allure-results").mkdir(exist_ok=True)
        
        # 初始化配置管理器和转换器
        self.config_manager = ConfigManager()
        self.converter = JSONToPythonConverter(self.config_manager)
        
    def execute_workflow(self, 
                        json_files: List[str] = None,
                        run_tests: bool = True,
                        generate_report: bool = True,
                        verbose: bool = True) -> dict:
        """
        执行完整的测试工作流
        
        Args:
            json_files: JSON测试用例文件列表
            run_tests: 是否执行测试
            generate_report: 是否生成Allure报告
            verbose: 是否输出详细信息
            
        Returns:
            dict: 执行结果
        """
        results = {
            "conversion": {},
            "execution": {},
            "report": {}
        }
        
        # 1. JSON转换为Python
        if verbose:
            print("🔄 步骤1: JSON转Python转换")
            print("="*60)
        
        if json_files is None:
            json_files = list(self.json_dir.glob("*.json"))
        else:
            json_files = [Path(f) for f in json_files]
        
        python_files = []
        for json_file in json_files:
            try:
                python_file = self._convert_json_to_python(json_file, verbose)
                python_files.append(python_file)
                results["conversion"][str(json_file)] = {"status": "success", "output": python_file}
                
                if verbose:
                    print(f"✅ 转换成功: {json_file.name} → {Path(python_file).name}")
                    
            except Exception as e:
                results["conversion"][str(json_file)] = {"status": "error", "error": str(e)}
                if verbose:
                    print(f"❌ 转换失败: {json_file.name} - {e}")
        
        if not python_files:
            print("❌ 没有成功转换的Python文件，退出执行")
            return results
        
        # 2. 执行pytest测试
        if run_tests:
            if verbose:
                print(f"\n⚡ 步骤2: 执行pytest测试")
                print("="*60)
            
            test_result = self._run_pytest_tests(python_files, verbose)
            results["execution"] = test_result
        
        # 3. 生成Allure报告
        if generate_report and run_tests:
            if verbose:
                print(f"\n📊 步骤3: 生成Allure报告")
                print("="*60)
            
            report_result = self._generate_allure_report(verbose)
            results["report"] = report_result
        
        return results
    
    def _convert_json_to_python(self, json_file: Path, verbose: bool = True) -> str:
        """
        转换单个JSON文件
        
        Args:
            json_file: JSON文件路径
            verbose: 是否输出详细信息
            
        Returns:
            str: 生成的Python文件路径
        """
        output_file = self.python_dir / f"test_{json_file.stem}.py"
        
        # 读取JSON文件获取测试信息
        with open(json_file, 'r', encoding='utf-8') as f:
            testcase_data = json.load(f)
        
        python_file = self.converter.convert_json_to_python(str(json_file), str(output_file))
        
        if verbose:
            testcase_name = testcase_data.get("name", "Unknown")
            target_app = testcase_data.get("target_app", "Unknown")
            print(f"   📝 测试用例: {testcase_name}")
            print(f"   📱 目标应用: {target_app}")
            print(f"   📄 输出文件: {Path(python_file).name}")
        
        return python_file
    
    def _run_pytest_tests(self, python_files: List[str], verbose: bool = True) -> dict:
        """
        执行pytest测试
        
        Args:
            python_files: Python测试文件列表
            verbose: 是否输出详细信息
            
        Returns:
            dict: 执行结果
        """
        cmd = [
            "python", "-m", "pytest",
            "--alluredir", str(self.reports_dir / "allure-results"),
            "--tb=short",
            "-v" if verbose else "-q"
        ] + python_files
        
        if verbose:
            print(f"执行命令: {' '.join(cmd)}")
            print("-" * 60)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=not verbose,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            return {
                "status": "success" if result.returncode == 0 else "failure",
                "return_code": result.returncode,
                "stdout": result.stdout if not verbose else "",
                "stderr": result.stderr if not verbose else "",
                "files_tested": len(python_files)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": "测试执行超时（5分钟）"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _generate_allure_report(self, verbose: bool = True) -> dict:
        """
        生成Allure报告
        
        Args:
            verbose: 是否输出详细信息
            
        Returns:
            dict: 报告生成结果
        """
        allure_results = self.reports_dir / "allure-results"
        allure_report = self.reports_dir / "allure-report"
        
        if not allure_results.exists() or not list(allure_results.glob("*")):
            return {
                "status": "skipped",
                "reason": "没有找到测试结果文件"
            }
        
        cmd = [
            "allure", "generate",
            str(allure_results),
            "--output", str(allure_report),
            "--clean"
        ]
        
        if verbose:
            print(f"生成报告命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                report_url = f"file://{allure_report.absolute()}/index.html"
                if verbose:
                    print(f"✅ 报告生成成功")
                    print(f"📊 报告地址: {report_url}")
                    print(f"   打开命令: allure open {allure_report}")
                
                return {
                    "status": "success",
                    "report_path": str(allure_report),
                    "report_url": report_url
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr
                }
                
        except FileNotFoundError:
            return {
                "status": "error",
                "error": "Allure命令未找到，请安装Allure报告工具"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def list_available_tests(self) -> dict:
        """列出可用的测试用例"""
        json_files = list(self.json_dir.glob("*.json"))
        tests = {}
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                tests[json_file.name] = {
                    "testcase_id": data.get("testcase_id"),
                    "name": data.get("name"),
                    "target_app": data.get("target_app"),
                    "description": data.get("description"),
                    "priority": data.get("metadata", {}).get("priority", "medium"),
                    "tags": data.get("metadata", {}).get("tags", [])
                }
            except Exception as e:
                tests[json_file.name] = {"error": str(e)}
        
        return tests


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="集成测试执行工具 - JSON转Python + Airtest + Pytest + Allure")
    
    parser.add_argument("--list", action="store_true", help="列出可用的测试用例")
    parser.add_argument("--files", nargs="+", help="指定要执行的JSON文件")
    parser.add_argument("--no-run", action="store_true", help="只转换，不执行测试")
    parser.add_argument("--no-report", action="store_true", help="不生成Allure报告")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--project-root", help="项目根目录")
    
    args = parser.parse_args()
    
    executor = IntegratedTestExecutor(args.project_root)
    
    if args.list:
        print("📋 可用的测试用例:")
        print("=" * 80)
        tests = executor.list_available_tests()
        
        for filename, info in tests.items():
            if "error" in info:
                print(f"❌ {filename}: {info['error']}")
            else:
                print(f"📝 {filename}")
                print(f"   ID: {info.get('testcase_id', 'Unknown')}")
                print(f"   名称: {info.get('name', 'Unknown')}")
                print(f"   应用: {info.get('target_app', 'Unknown')}")
                print(f"   优先级: {info.get('priority', 'medium')}")
                print(f"   标签: {', '.join(info.get('tags', []))}")
                print()
        return
    
    # 执行测试工作流
    print("🚀 启动Only-Test集成执行器")
    print("=" * 60)
    
    results = executor.execute_workflow(
        json_files=args.files,
        run_tests=not args.no_run,
        generate_report=not args.no_report,
        verbose=not args.quiet
    )
    
    # 总结结果
    print(f"\n📋 执行总结")
    print("=" * 60)
    
    # 转换结果
    conversion_success = sum(1 for r in results["conversion"].values() if r.get("status") == "success")
    conversion_total = len(results["conversion"])
    print(f"🔄 JSON转换: {conversion_success}/{conversion_total} 成功")
    
    # 执行结果
    if "execution" in results and results["execution"]:
        exec_result = results["execution"]
        status_icon = "✅" if exec_result.get("status") == "success" else "❌"
        print(f"⚡ 测试执行: {status_icon} {exec_result.get('status', 'unknown')}")
        if exec_result.get("files_tested"):
            print(f"   测试文件数: {exec_result['files_tested']}")
    
    # 报告结果
    if "report" in results and results["report"]:
        report_result = results["report"]
        if report_result.get("status") == "success":
            print(f"📊 报告生成: ✅ 成功")
            print(f"   报告路径: {report_result['report_path']}")
        else:
            print(f"📊 报告生成: ❌ {report_result.get('status', 'failed')}")
    
    # 返回码
    if results.get("execution", {}).get("return_code", 0) != 0:
        sys.exit(1)


if __name__ == "__main__":
    main()