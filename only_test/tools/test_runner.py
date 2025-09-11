#!/usr/bin/env python3
"""
Only-Test 智能测试运行器

支持运行智能测试用例，展示条件分支逻辑的执行过程
生成详细的测试报告，包含智能决策过程
"""

import json
import sys
import argparse
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目路径以导入库
sys.path.append(str(Path(__file__).parent.parent))

from lib.config_manager import ConfigManager  
from lib.execution_engine.smart_executor import SmartTestExecutor, TestCaseResult


class TestReportGenerator:
    """测试报告生成器"""
    
    def __init__(self, output_dir: str = "../reports"):
        """
        初始化报告生成器
        
        Args:
            output_dir: 报告输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_json_report(self, results: List[TestCaseResult]) -> str:
        """
        生成JSON格式报告
        
        Args:
            results: 测试结果列表
            
        Returns:
            str: 报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"test_report_{timestamp}.json"
        
        # 计算汇总数据
        total_cases = len(results)
        passed_cases = len([r for r in results if r.overall_status.value == 'success'])
        failed_cases = len([r for r in results if r.overall_status.value == 'failed'])
        total_duration = sum(r.total_duration for r in results)
        
        report_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "framework": "Only-Test v1.0",
                "total_cases": total_cases,
                "passed_cases": passed_cases,
                "failed_cases": failed_cases,
                "success_rate": f"{(passed_cases/total_cases*100):.1f}%" if total_cases > 0 else "0%",
                "total_duration": f"{total_duration:.2f}s"
            },
            "test_results": []
        }
        
        for result in results:
            # 转换执行结果为可序列化格式
            result_data = {
                "testcase_id": result.testcase_id,
                "name": result.name,
                "overall_status": result.overall_status.value,
                "total_duration": result.total_duration,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "assertions": {
                    "passed": result.assertions_passed,
                    "failed": result.assertions_failed
                },
                "recovery_count": result.recovery_count,
                "steps": []
            }
            
            # 添加步骤详情
            for step_result in result.step_results:
                step_data = {
                    "step_number": step_result.step_number,
                    "action": step_result.action,
                    "target": step_result.target,
                    "status": step_result.status.value,
                    "duration": step_result.duration,
                    "recovery_attempted": step_result.recovery_attempted,
                    "error_message": step_result.error_message,
                    "screenshot_path": step_result.screenshot_path
                }
                
                # 添加条件分支信息
                if step_result.condition_result is not None:
                    step_data["conditional_info"] = {
                        "condition_result": step_result.condition_result,
                        "selected_path": step_result.selected_path
                    }
                
                result_data["steps"].append(step_data)
            
            report_data["test_results"].append(result_data)
        
        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return str(report_file)
    
    def generate_html_report(self, results: List[TestCaseResult]) -> str:
        """
        生成HTML格式报告
        
        Args:
            results: 测试结果列表
            
        Returns:
            str: 报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"test_report_{timestamp}.html"
        
        # 计算统计信息
        total_cases = len(results)
        passed_cases = len([r for r in results if r.overall_status.value == 'success'])
        failed_cases = len([r for r in results if r.overall_status.value == 'failed'])
        success_rate = (passed_cases/total_cases*100) if total_cases > 0 else 0
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Only-Test 智能测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .stat-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .stat-label {{ color: #666; font-size: 14px; }}
        .success {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        .testcase {{ background: white; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .testcase-header {{ padding: 15px; border-bottom: 1px solid #eee; }}
        .testcase-title {{ font-size: 18px; font-weight: bold; margin-bottom: 5px; }}
        .testcase-meta {{ color: #666; font-size: 14px; }}
        .steps {{ padding: 0; }}
        .step {{ padding: 10px 15px; border-left: 4px solid #ddd; margin: 5px 0; }}
        .step.success {{ border-left-color: #28a745; background-color: #f8fff9; }}
        .step.failed {{ border-left-color: #dc3545; background-color: #fff8f8; }}
        .step.recovery {{ border-left-color: #ffc107; background-color: #fffdf7; }}
        .conditional-info {{ background: #e3f2fd; padding: 10px; margin: 5px 0; border-radius: 4px; font-size: 12px; }}
        .emoji {{ font-size: 20px; margin-right: 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Only-Test 智能测试报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{total_cases}</div>
            <div class="stat-label">总用例数</div>
        </div>
        <div class="stat-card">
            <div class="stat-value success">{passed_cases}</div>
            <div class="stat-label">通过数量</div>
        </div>
        <div class="stat-card">
            <div class="stat-value failed">{failed_cases}</div>
            <div class="stat-label">失败数量</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{success_rate:.1f}%</div>
            <div class="stat-label">成功率</div>
        </div>
    </div>
"""
        
        # 添加每个测试用例的详情
        for result in results:
            status_class = "success" if result.overall_status.value == "success" else "failed"
            status_emoji = "✅" if result.overall_status.value == "success" else "❌"
            
            html_content += f"""
    <div class="testcase">
        <div class="testcase-header">
            <div class="testcase-title">
                <span class="emoji">{status_emoji}</span>
                {result.name}
            </div>
            <div class="testcase-meta">
                ID: {result.testcase_id} | 
                耗时: {result.total_duration:.2f}s | 
                断言: {result.assertions_passed}✅ {result.assertions_failed}❌ |
                恢复: {result.recovery_count}次
            </div>
        </div>
        <div class="steps">
"""
            
            # 添加步骤详情
            for step in result.step_results:
                step_class = step.status.value
                step_emoji = {
                    'success': '✅',
                    'failed': '❌', 
                    'recovery': '🔄',
                    'skipped': '⏭️'
                }.get(step.status.value, '❓')
                
                html_content += f"""
            <div class="step {step_class}">
                <div><span class="emoji">{step_emoji}</span>
                    Step {step.step_number}: {step.action} → {step.target}
                    <small style="float: right;">{step.duration:.2f}s</small>
                </div>
"""
                
                # 添加条件分支信息
                if step.condition_result is not None:
                    condition_emoji = "✅" if step.condition_result else "❌"
                    html_content += f"""
                <div class="conditional-info">
                    🧠 <strong>智能条件判断:</strong> 
                    条件结果: {condition_emoji} {step.condition_result} | 
                    选择路径: {step.selected_path}
                </div>
"""
                
                # 添加错误信息
                if step.error_message:
                    html_content += f"""
                <div style="color: #dc3545; font-size: 12px; margin-top: 5px;">
                    ❌ 错误: {step.error_message}
                </div>
"""
                
                # 添加恢复信息
                if step.recovery_attempted:
                    html_content += f"""
                <div style="color: #ffc107; font-size: 12px; margin-top: 5px;">
                    🔄 已尝试自动恢复
                </div>
"""
                
                html_content += "</div>\n"
            
            html_content += """
        </div>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        # 保存HTML报告
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(report_file)


class SmartTestRunner:
    """智能测试运行器"""
    
    def __init__(self, device_id: Optional[str] = None):
        """
        初始化测试运行器
        
        Args:
            device_id: 设备ID
        """
        self.device_id = device_id
        self.config_manager = ConfigManager()
        self.executor = SmartTestExecutor(device_id)
        self.report_generator = TestReportGenerator()
    
    def run_testcase_file(self, testcase_file: str) -> TestCaseResult:
        """
        运行单个测试用例文件
        
        Args:
            testcase_file: 测试用例文件路径
            
        Returns:
            TestCaseResult: 执行结果
        """
        testcase_path = Path(testcase_file)
        if not testcase_path.exists():
            raise FileNotFoundError(f"测试用例文件不存在: {testcase_file}")
        
        print(f"📂 加载测试用例: {testcase_path.name}")
        
        with open(testcase_path, 'r', encoding='utf-8') as f:
            testcase_data = json.load(f)
        
        # 显示用例信息
        self._print_testcase_info(testcase_data)
        
        # 执行用例
        result = self.executor.execute_testcase(testcase_data)
        
        return result
    
    def run_testcase_directory(self, directory: str) -> List[TestCaseResult]:
        """
        运行目录中的所有测试用例
        
        Args:
            directory: 测试用例目录
            
        Returns:
            List[TestCaseResult]: 执行结果列表
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        # 查找所有JSON测试用例文件
        testcase_files = list(dir_path.glob("*.json"))
        if not testcase_files:
            print(f"⚠️  目录中没有找到测试用例文件: {directory}")
            return []
        
        print(f"📂 发现 {len(testcase_files)} 个测试用例文件")
        
        results = []
        for testcase_file in testcase_files:
            try:
                result = self.run_testcase_file(str(testcase_file))
                results.append(result)
            except Exception as e:
                print(f"❌ 执行用例失败 {testcase_file.name}: {e}")
        
        return results
    
    def _print_testcase_info(self, testcase_data: Dict[str, Any]):
        """打印测试用例信息"""
        metadata = testcase_data.get('metadata', {})
        execution_path = testcase_data.get('execution_path', [])
        
        print("\n" + "="*60)
        print("📋 测试用例信息")
        print("="*60)
        print(f"📝 名称: {testcase_data.get('name', 'Unknown')}")
        print(f"🆔 ID: {testcase_data.get('testcase_id', 'Unknown')}")
        print(f"🏷️  标签: {', '.join(metadata.get('tags', []))}")
        print(f"📱 设备类型: {', '.join(metadata.get('device_types', []))}")
        print(f"⏱️  预估时长: {metadata.get('estimated_duration', 0)}秒")
        print(f"🔧 复杂度: {metadata.get('complexity', 'Unknown')}")
        
        # 显示智能特性
        conditional_steps = [step for step in execution_path if step.get('action') == 'conditional_action']
        if conditional_steps:
            print(f"🧠 智能条件步骤: {len(conditional_steps)}个")
            for i, step in enumerate(conditional_steps, 1):
                condition = step.get('condition', {})
                print(f"   {i}. {step.get('description', 'Unknown')}")
                print(f"      └─ 条件: {condition.get('type', 'Unknown')} - {condition.get('check', 'Unknown')}")
        
        # 显示生成信息
        if testcase_data.get('generation_method') == 'llm_assisted':
            print(f"🤖 LLM生成: {testcase_data.get('llm_analysis', {}).get('confidence', 0)*100:.0f}% 置信度")
        
        print("="*60 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Only-Test 智能测试运行器")
    parser.add_argument("--file", help="运行指定的测试用例文件")
    parser.add_argument("--dir", help="运行目录中的所有测试用例")
    parser.add_argument("--device", help="指定设备ID")
    parser.add_argument("--report", choices=['json', 'html', 'both'], default='both', help="报告格式")
    parser.add_argument("--demo", action="store_true", help="运行演示用例")
    
    args = parser.parse_args()
    
    if args.demo:
        print("🚀 运行演示模式...")
        # 生成一个演示用例
        from case_generator import SmartTestCaseGenerator
        generator = SmartTestCaseGenerator()
        demo_testcase = generator.generate_with_llm_description(
            "在测试应用中搜索'周杰伦'，如果搜索框有内容先清空再输入",
            "com.example.musicapp"
        )
        demo_file = generator.save_testcase(demo_testcase, "demo_smart_search.json")
        args.file = demo_file
    
    if not args.file and not args.dir:
        print("❌ 错误: 请指定要运行的测试用例文件 (--file) 或目录 (--dir)")
        print("💡 提示: 使用 --demo 参数运行演示用例")
        sys.exit(1)
    
    try:
        runner = SmartTestRunner(args.device)
        results = []
        
        if args.file:
            print(f"🎯 运行单个测试用例: {args.file}")
            result = runner.run_testcase_file(args.file)
            results.append(result)
        elif args.dir:
            print(f"🎯 运行目录中的测试用例: {args.dir}")
            results = runner.run_testcase_directory(args.dir)
        
        # 生成报告
        if results:
            print(f"\n📊 生成测试报告...")
            
            if args.report in ['json', 'both']:
                json_report = runner.report_generator.generate_json_report(results)
                print(f"📄 JSON报告: {json_report}")
            
            if args.report in ['html', 'both']:
                html_report = runner.report_generator.generate_html_report(results)
                print(f"🌐 HTML报告: {html_report}")
            
            # 显示汇总
            total = len(results)
            passed = len([r for r in results if r.overall_status.value == 'success'])
            failed = len([r for r in results if r.overall_status.value == 'failed'])
            
            print(f"\n📈 执行汇总:")
            print(f"   总用例: {total}")
            print(f"   通过: {passed}")
            print(f"   失败: {failed}")
            print(f"   成功率: {(passed/total*100):.1f}%")
            
            if failed == 0:
                print("\n🎉 所有测试用例都执行成功！")
            else:
                print(f"\n⚠️  有 {failed} 个测试用例失败，请查看详细报告")
        
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()