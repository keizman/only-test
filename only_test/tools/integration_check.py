#!/usr/bin/env python3
"""
Only-Test 架构集成检查工具

验证所有组件是否正确集成并可以协同工作
检查配置文件、LLM连接、设备适配等核心功能
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from lib.config_manager import ConfigManager
from lib.llm_integration.llm_client import LLMClient, LLMMessage


class IntegrationChecker:
    """架构集成检查器"""
    
    def __init__(self):
        self.results = {}
        self.config_manager = None
        self.llm_client = None
    
    def check_configuration_system(self) -> bool:
        """检查配置系统"""
        print("🔧 检查配置系统...")
        
        try:
            # 检查配置管理器初始化
            self.config_manager = ConfigManager()
            self.results["config_manager"] = {"status": "success", "details": "初始化成功"}
            
            # 检查主配置文件
            config = self.config_manager.get_config()
            if not config:
                self.results["main_config"] = {"status": "error", "details": "main.yaml加载失败"}
                return False
            
            self.results["main_config"] = {
                "status": "success", 
                "details": f"配置节数量: {len(config.keys())}"
            }
            
            # 检查设备配置
            devices = self.config_manager.list_devices()
            self.results["devices"] = {
                "status": "success" if devices else "warning",
                "details": f"可用设备: {len(devices)}个 - {devices}"
            }
            
            # 检查应用配置
            applications = self.config_manager.list_applications()
            self.results["applications"] = {
                "status": "success" if applications else "warning",
                "details": f"可用应用: {len(applications)}个 - {applications}"
            }
            
            # 检查LLM配置
            llm_config = self.config_manager.get_llm_config()
            llm_enabled = llm_config.get('enabled', False)
            self.results["llm_config"] = {
                "status": "success" if llm_enabled else "warning",
                "details": f"LLM启用: {llm_enabled}, 提供商: {llm_config.get('provider', 'unknown')}"
            }
            
            print("✅ 配置系统检查完成")
            return True
            
        except Exception as e:
            self.results["config_system"] = {"status": "error", "details": str(e)}
            print(f"❌ 配置系统检查失败: {e}")
            return False
    
    def check_llm_integration(self) -> bool:
        """检查LLM集成"""
        print("🤖 检查LLM集成...")
        
        try:
            # 初始化LLM客户端
            self.llm_client = LLMClient(self.config_manager)
            
            # 检查LLM可用性
            if not self.llm_client.is_available():
                self.results["llm_availability"] = {
                    "status": "warning", 
                    "details": "LLM服务不可用 - 可能是配置问题或网络问题"
                }
                print("⚠️ LLM服务不可用")
                return False
            
            # 测试简单聊天
            test_messages = [LLMMessage("user", "Hello, test connection")]
            response = self.llm_client.chat_completion(test_messages, max_tokens=10)
            
            if response.success:
                self.results["llm_connection"] = {
                    "status": "success",
                    "details": f"连接成功 - 模型: {response.model}, 耗时: {response.response_time:.2f}s"
                }
                print("✅ LLM连接测试成功")
                return True
            else:
                self.results["llm_connection"] = {
                    "status": "error",
                    "details": f"连接失败: {response.error}"
                }
                print(f"❌ LLM连接测试失败: {response.error}")
                return False
                
        except Exception as e:
            self.results["llm_integration"] = {"status": "error", "details": str(e)}
            print(f"❌ LLM集成检查失败: {e}")
            return False
    
    def check_device_app_combinations(self) -> bool:
        """检查设备-应用组合配置"""
        print("📱 检查设备-应用组合...")
        
        try:
            devices = self.config_manager.list_devices()
            applications = self.config_manager.list_applications()
            
            valid_combinations = []
            invalid_combinations = []
            
            for device_id in devices:
                for app_id in applications:
                    if self.config_manager.validate_device_app_combination(device_id, app_id):
                        combination_config = self.config_manager.get_device_app_config(device_id, app_id)
                        if combination_config:
                            valid_combinations.append(f"{device_id}+{app_id}")
                        else:
                            invalid_combinations.append(f"{device_id}+{app_id}")
                    else:
                        invalid_combinations.append(f"{device_id}+{app_id}")
            
            self.results["device_app_combinations"] = {
                "status": "success" if valid_combinations else "warning",
                "details": {
                    "valid": valid_combinations,
                    "invalid": invalid_combinations,
                    "total_valid": len(valid_combinations)
                }
            }
            
            print(f"✅ 有效组合: {len(valid_combinations)}个")
            print(f"⚠️ 无效组合: {len(invalid_combinations)}个")
            return True
            
        except Exception as e:
            self.results["device_app_combinations"] = {"status": "error", "details": str(e)}
            print(f"❌ 设备-应用组合检查失败: {e}")
            return False
    
    def check_path_templates(self) -> bool:
        """检查路径模板"""
        print("🗂️ 检查路径模板...")
        
        try:
            # 测试各种路径模板
            template_tests = [
                ("assets_path", {"app_package": "com.test.app", "device_model": "TestDevice"}),
                ("testcase_path", {"app_name": "TestApp", "device_name": "Test_Device"}),
                ("report_path", {"suite_name": "smoke_test"}),
                ("python_path", {"app_name": "TestApp", "scenario": "login"})
            ]
            
            template_results = {}
            
            for template_name, kwargs in template_tests:
                try:
                    path = self.config_manager.get_path_template(template_name, **kwargs)
                    template_results[template_name] = {"status": "success", "path": path}
                except Exception as e:
                    template_results[template_name] = {"status": "error", "error": str(e)}
            
            success_count = len([r for r in template_results.values() if r["status"] == "success"])
            
            self.results["path_templates"] = {
                "status": "success" if success_count == len(template_tests) else "warning",
                "details": template_results,
                "success_count": success_count,
                "total_count": len(template_tests)
            }
            
            print(f"✅ 路径模板测试: {success_count}/{len(template_tests)} 成功")
            return success_count > 0
            
        except Exception as e:
            self.results["path_templates"] = {"status": "error", "details": str(e)}
            print(f"❌ 路径模板检查失败: {e}")
            return False
    
    def check_test_case_generation(self) -> bool:
        """检查测试用例生成"""
        print("🧪 检查测试用例生成...")
        
        if not self.llm_client or not self.llm_client.is_available():
            print("⚠️ LLM不可用，跳过测试用例生成检查")
            self.results["test_case_generation"] = {
                "status": "skipped", 
                "details": "LLM服务不可用"
            }
            return True
        
        try:
            # 测试用例生成
            test_description = "测试应用启动功能"
            test_package = "com.example.app"
            
            test_case = self.llm_client.generate_test_case(
                test_description, 
                test_package, 
                "android_phone"
            )
            
            if test_case:
                self.results["test_case_generation"] = {
                    "status": "success",
                    "details": {
                        "description": test_description,
                        "generated": True,
                        "case_id": test_case.get('testcase_id', 'unknown'),
                        "steps_count": len(test_case.get('execution_path', []))
                    }
                }
                print("✅ 测试用例生成成功")
                return True
            else:
                self.results["test_case_generation"] = {
                    "status": "error",
                    "details": "LLM返回空结果"
                }
                print("❌ 测试用例生成失败")
                return False
                
        except Exception as e:
            self.results["test_case_generation"] = {"status": "error", "details": str(e)}
            print(f"❌ 测试用例生成检查失败: {e}")
            return False
    
    def run_complete_check(self) -> Dict[str, Any]:
        """运行完整的集成检查"""
        print("=" * 60)
        print("🎯 Only-Test 架构集成检查")
        print("=" * 60)
        
        checks = [
            ("配置系统", self.check_configuration_system),
            ("LLM集成", self.check_llm_integration),
            ("设备-应用组合", self.check_device_app_combinations),
            ("路径模板", self.check_path_templates),
            ("测试用例生成", self.check_test_case_generation)
        ]
        
        passed_checks = 0
        total_checks = len(checks)
        
        for check_name, check_func in checks:
            print(f"\n📋 检查项目: {check_name}")
            print("-" * 30)
            
            try:
                success = check_func()
                if success:
                    passed_checks += 1
                    print(f"✅ {check_name} - 通过")
                else:
                    print(f"⚠️ {check_name} - 部分问题")
            except Exception as e:
                print(f"❌ {check_name} - 失败: {e}")
        
        # 生成摘要报告
        success_rate = (passed_checks / total_checks) * 100
        
        summary = {
            "overall_status": "success" if passed_checks == total_checks else "partial" if passed_checks > 0 else "failed",
            "success_rate": success_rate,
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "detailed_results": self.results
        }
        
        print("\n" + "=" * 60)
        print("📊 检查摘要")
        print("=" * 60)
        print(f"总体状态: {'✅ 全部通过' if passed_checks == total_checks else '⚠️ 部分问题' if passed_checks > 0 else '❌ 存在问题'}")
        print(f"成功率: {success_rate:.1f}% ({passed_checks}/{total_checks})")
        
        # 显示具体问题
        errors = []
        warnings = []
        
        for key, result in self.results.items():
            if result.get("status") == "error":
                errors.append(f"{key}: {result.get('details', 'Unknown error')}")
            elif result.get("status") == "warning":
                warnings.append(f"{key}: {result.get('details', 'Unknown warning')}")
        
        if errors:
            print("\n❌ 错误:")
            for error in errors:
                print(f"  • {error}")
        
        if warnings:
            print("\n⚠️ 警告:")
            for warning in warnings:
                print(f"  • {warning}")
        
        if passed_checks == total_checks:
            print("\n🎉 架构集成检查完成！所有组件工作正常。")
        else:
            print("\n🔧 请根据上述问题进行相应的配置调整。")
        
        return summary
    
    def save_report(self, report_path: str = None) -> str:
        """保存检查报告"""
        if report_path is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = f"integration_check_report_{timestamp}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        return report_path


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Only-Test 架构集成检查工具")
    parser.add_argument("--save-report", help="保存检查报告到指定文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    checker = IntegrationChecker()
    summary = checker.run_complete_check()
    
    # 保存报告
    if args.save_report:
        report_path = checker.save_report(args.save_report)
        print(f"\n📄 详细报告已保存到: {report_path}")
    
    # 退出码
    if summary["overall_status"] == "success":
        sys.exit(0)
    elif summary["overall_status"] == "partial":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()