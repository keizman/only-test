#!/usr/bin/env python3
"""
完整工作流程演示

展示从LLM生成JSON用例到最终报告的完整流程
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from lib.device_adapter import DeviceAdapter
from lib.assets_manager import AssetsManager
from lib.code_generator.json_to_python import JSONToPythonConverter


class CompleteWorkflowDemo:
    """完整工作流程演示"""
    
    def __init__(self):
        """初始化演示环境"""
        self.project_root = Path(__file__).parent.parent
        self.device_adapter = DeviceAdapter()
        self.assets_manager = AssetsManager(str(self.project_root / "assets"))
        self.converter = JSONToPythonConverter()
        
    def demonstrate_complete_workflow(self, user_description: str):
        """
        演示完整工作流程
        
        Args:
            user_description: 用户的自然语言测试需求
        """
        print("🚀 Only-Test 完整工作流程演示")
        print("=" * 80)
        print(f"📝 用户需求: {user_description}")
        print()
        
        # 步骤1: 模拟LLM生成JSON用例
        print("🧠 步骤1: LLM智能生成JSON用例")
        print("-" * 40)
        json_testcase = self._simulate_llm_generation(user_description)
        json_file = self._save_generated_json(json_testcase)
        print(f"✅ JSON用例生成完成: {json_file.name}")
        print(f"   用例ID: {json_testcase['testcase_id']}")
        print(f"   目标应用: {json_testcase['target_app']}")
        print(f"   智能步骤: {len([s for s in json_testcase['execution_path'] if s.get('action') == 'conditional_action'])}")
        print()
        
        # 步骤2: 设备信息探测与适配
        print("🔍 步骤2: 设备信息探测与适配")
        print("-" * 40)
        device_info = self.device_adapter.detect_device_info()
        adapted_json_file = self.device_adapter.update_json_testcase(str(json_file))
        print(f"✅ 设备信息探测完成")
        print(f"   设备名称: {device_info.get('device_name', 'Unknown')}")
        print(f"   Android版本: {device_info.get('android_version', 'Unknown')}")
        print(f"   屏幕分辨率: {device_info.get('screen_info', {}).get('resolution', 'Unknown')}")
        print(f"   适配模式: {self.device_adapter.adaptation_rules.get('recognition_adaptation', {}).get('preferred_mode', 'hybrid')}")
        print()
        
        # 步骤3: 启动资源管理会话
        print("📁 步骤3: 启动资源管理会话")
        print("-" * 40)
        session_path = self.assets_manager.start_session(
            json_testcase['target_app'],
            device_info.get('device_name', 'Unknown_Device'),
            json_testcase['testcase_id']
        )
        print(f"✅ 测试会话已启动")
        print(f"   会话路径: {Path(session_path).name}")
        print(f"   完整路径: {session_path}")
        print()
        
        # 步骤4: 模拟智能执行过程
        print("⚡ 步骤4: 智能执行与监控")
        print("-" * 40)
        execution_results = self._simulate_intelligent_execution(json_testcase)
        print(f"✅ 智能执行完成")
        print(f"   总步骤数: {len(execution_results)}")
        print(f"   成功步骤: {len([r for r in execution_results if r['status'] == 'success'])}")
        print(f"   条件判断: {len([r for r in execution_results if r.get('condition_executed')])}")
        print(f"   总执行时间: {sum(r.get('execution_time', 0) for r in execution_results):.1f}秒")
        print()
        
        # 步骤5: 更新JSON用例
        print("🔄 步骤5: 回写执行结果到JSON")
        print("-" * 40)
        updated_json_file = self.assets_manager.update_json_testcase_with_assets(str(json_file))
        print(f"✅ JSON用例已更新")
        print(f"   资源文件数: {len(self.assets_manager.current_session['assets_saved'])}")
        print(f"   截图数量: {len([a for a in self.assets_manager.current_session['assets_saved'] if a['type'] == 'screenshot'])}")
        print()
        
        # 步骤6: JSON转Python代码
        print("🐍 步骤6: JSON转Python转换")
        print("-" * 40)
        python_file = self.converter.convert_json_to_python(
            str(json_file),
            str(self.project_root / "testcases" / "python" / f"test_{json_file.stem}.py")
        )
        print(f"✅ Python测试文件生成完成")
        print(f"   文件路径: {Path(python_file).name}")
        print(f"   支持框架: Airtest + Pytest + Allure")
        print()
        
        # 步骤7: 生成资源报告
        print("📊 步骤7: 生成资源使用报告")
        print("-" * 40)
        assets_report = self.assets_manager.generate_assets_report()
        print(f"✅ 资源报告生成完成")
        print(f"   会话时长: {assets_report['statistics']['session_duration']:.1f}秒")
        print(f"   存储空间: {assets_report['statistics']['total_size_bytes'] / 1024 / 1024:.1f}MB")
        print(f"   涵盖步骤: {len(assets_report['assets_by_step'])}")
        print()
        
        # 输出完整工作流程总结
        self._print_workflow_summary(json_testcase, execution_results, assets_report)
        
        return {
            "json_testcase": json_testcase,
            "device_info": device_info,
            "execution_results": execution_results,
            "assets_report": assets_report,
            "python_file": python_file,
            "session_path": session_path
        }
    
    def _simulate_llm_generation(self, description: str) -> dict:
        """模拟LLM生成JSON用例"""
        # 解析描述中的关键信息
        if "抖音" in description:
            app_package = "com.mobile.brasiltvmobile"
            app_name = "抖音"
        elif "淘宝" in description:
            app_package = "com.taobao.taobao" 
            app_name = "淘宝"
        elif "网易云音乐" in description:
            app_package = "com.netease.cloudmusic"
            app_name = "网易云音乐"
        else:
            app_package = "com.example.testapp"
            app_name = "测试应用"
        
        # 提取搜索关键词
        search_keyword = "测试内容"
        if "搜索" in description:
            import re
            search_match = re.search(r"搜索['\"]([^'\"]+)['\"]", description)
            if search_match:
                search_keyword = search_match.group(1)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return {
            "testcase_id": f"TC_{app_package.upper().replace('.', '_')}_{timestamp}",
            "name": f"{app_name}智能搜索测试",
            "version": "2.0.0", 
            "description": f"基于用户需求生成的智能测试用例: {description}",
            "generated_at": datetime.now().isoformat(),
            "generation_method": "llm_assisted",
            "original_description": description,
            "target_app": app_package,
            "metadata": {
                "tags": ["llm_generated", "search", "smart_judgment", "demo"],
                "priority": "high",
                "estimated_duration": 60,
                "device_types": ["android_phone"],
                "complexity": "conditional_logic",
                "ai_friendly": True
            },
            "variables": {
                "search_keyword": search_keyword,
                "target_app_package": app_package,
                "max_wait_time": 20
            },
            "execution_path": [
                {
                    "step": 1,
                    "action": "click",
                    "target": {
                        "priority_selectors": [
                            {"resource_id": f"{app_package}:id/search_btn"},
                            {"content_desc": "搜索"},
                            {"text": "搜索"}
                        ]
                    },
                    "description": f"点击{app_name}搜索按钮",
                    "success_criteria": "成功进入搜索页面"
                },
                {
                    "step": 2,
                    "action": "conditional_action",
                    "condition": {
                        "type": "element_content_check",
                        "target": {
                            "priority_selectors": [
                                {"resource_id": f"{app_package}:id/search_edit"},
                                {"class": "android.widget.EditText"}
                            ]
                        },
                        "check": "has_text_content"
                    },
                    "conditional_paths": {
                        "if_has_content": {
                            "action": "click",
                            "target": {
                                "priority_selectors": [
                                    {"resource_id": f"{app_package}:id/search_clear"},
                                    {"content_desc": "清除"}
                                ]
                            },
                            "reason": "搜索框有历史内容，需要先清空"
                        },
                        "if_empty": {
                            "action": "input",
                            "target": {"resource_id": f"{app_package}:id/search_edit"},
                            "data": "${search_keyword}",
                            "reason": "搜索框为空，直接输入搜索词"
                        }
                    },
                    "description": "🧠 智能判断搜索框状态并选择操作",
                    "business_logic": "确保搜索框处于正确状态"
                },
                {
                    "step": 3,
                    "action": "input",
                    "target": {"resource_id": f"{app_package}:id/search_edit"},
                    "data": "${search_keyword}",
                    "description": "输入搜索关键词"
                },
                {
                    "step": 4,
                    "action": "click", 
                    "target": {
                        "priority_selectors": [
                            {"resource_id": f"{app_package}:id/search_submit"},
                            {"text": "搜索"}
                        ]
                    },
                    "description": "点击搜索按钮执行搜索"
                }
            ],
            "llm_analysis": {
                "detected_intent": "搜索功能测试",
                "key_actions": ["导航到搜索", "智能状态判断", "输入关键词", "执行搜索"],
                "conditional_logic": ["搜索框内容状态检查"],
                "confidence": 0.95
            }
        }
    
    def _save_generated_json(self, testcase_data: dict) -> Path:
        """保存生成的JSON用例"""
        filename = f"{testcase_data['testcase_id'].lower()}.json"
        json_file = self.project_root / "testcases" / "generated" / filename
        json_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(testcase_data, f, ensure_ascii=False, indent=2)
        
        return json_file
    
    def _simulate_intelligent_execution(self, testcase_data: dict) -> list:
        """模拟智能执行过程"""
        execution_results = []
        
        for step in testcase_data.get("execution_path", []):
            step_num = step.get("step", 0)
            action = step.get("action", "unknown")
            
            print(f"  执行步骤 {step_num}: {step.get('description', 'Unknown')}")
            
            # 模拟执行前截图
            screenshot_data = self._generate_mock_screenshot()
            self.assets_manager.save_screenshot(
                screenshot_data, step_num, action, "before"
            )
            
            # 模拟条件判断执行
            if action == "conditional_action":
                # 模拟条件检查
                condition_result = True  # 模拟检查结果
                selected_path = "if_has_content" if condition_result else "if_empty"
                
                # 模拟Omniparser识别结果
                omniparser_data = self._generate_mock_omniparser_result()
                omni_path = self.assets_manager.save_omniparser_result(
                    omniparser_data, step_num
                )
                
                execution_result = {
                    "step_number": step_num,
                    "action": action,
                    "status": "success", 
                    "condition_executed": True,
                    "condition_result": condition_result,
                    "selected_path": selected_path,
                    "execution_time": 2.1,
                    "recognition_mode": "visual",
                    "omniparser_result": omni_path
                }
                
                print(f"    🧠 条件判断: {condition_result} → {selected_path}")
                print(f"    🎯 视觉识别: {omniparser_data['elements_count']} 个元素")
                
            else:
                # 普通步骤执行
                execution_result = {
                    "step_number": step_num,
                    "action": action,
                    "status": "success",
                    "execution_time": 1.5,
                    "recognition_mode": "xml"
                }
                
            # 模拟执行后截图
            self.assets_manager.save_screenshot(
                screenshot_data, step_num, action, "after"
            )
            
            # 保存执行日志
            self.assets_manager.save_execution_log(step_num, step, execution_result)
            
            execution_results.append(execution_result)
            
            # 模拟执行间隔
            time.sleep(0.1)
        
        return execution_results
    
    def _generate_mock_screenshot(self) -> bytes:
        """生成模拟截图数据"""
        # 创建1x1像素的PNG数据作为模拟
        mock_png = b'\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01\\x08\\x06\\x00\\x00\\x00\\x1f\\x15\\xc4\\x89\\x00\\x00\\x00\\rIDATx\\x9cc```\\x00\\x01\\x00\\x00\\x05\\x00\\x01\\r\\n-\\xdb\\x00\\x00\\x00\\x00IEND\\xaeB`\\x82'
        return mock_png
    
    def _generate_mock_omniparser_result(self) -> dict:
        """生成模拟Omniparser识别结果"""
        return {
            "elements": [
                {
                    "type": "input_field",
                    "text": "搜索内容",
                    "confidence": 0.95,
                    "coordinates": {"x": 540, "y": 200, "width": 300, "height": 50}
                },
                {
                    "type": "button",
                    "text": "清除",
                    "confidence": 0.88,
                    "coordinates": {"x": 800, "y": 210, "width": 30, "height": 30}
                }
            ],
            "elements_count": 2,
            "processing_time": 1.2,
            "recognition_confidence": 0.92
        }
    
    def _print_workflow_summary(self, testcase_data: dict, execution_results: list, assets_report: dict):
        """打印工作流程总结"""
        print("🎉 完整工作流程总结")
        print("=" * 80)
        
        print("📋 测试用例信息:")
        print(f"   📝 用例名称: {testcase_data['name']}")
        print(f"   🏷️  用例ID: {testcase_data['testcase_id']}")
        print(f"   📱 目标应用: {testcase_data['target_app']}")
        print(f"   🧠 智能步骤: {len([s for s in testcase_data['execution_path'] if s.get('action') == 'conditional_action'])}")
        print()
        
        print("⚡ 执行统计:")
        success_count = len([r for r in execution_results if r['status'] == 'success'])
        total_time = sum(r.get('execution_time', 0) for r in execution_results)
        print(f"   ✅ 成功率: {success_count}/{len(execution_results)} ({success_count/len(execution_results)*100:.0f}%)")
        print(f"   ⏱️  执行时间: {total_time:.1f}秒")
        print(f"   🔄 条件判断: {len([r for r in execution_results if r.get('condition_executed')])}")
        print(f"   📸 生成截图: {assets_report['statistics']['screenshots']}")
        print()
        
        print("📁 资源管理:")
        print(f"   📂 会话目录: {Path(assets_report['session_info']['session_path']).name}")
        print(f"   📊 资源总数: {assets_report['statistics']['total_assets']}")
        print(f"   💾 占用空间: {assets_report['statistics']['total_size_bytes'] / 1024:.1f}KB")
        print(f"   🕐 会话时长: {assets_report['statistics']['session_duration']:.1f}秒")
        print()
        
        print("🎯 核心特性展示:")
        print("   ✅ 自然语言 → 智能JSON用例")
        print("   ✅ 设备自适应与识别模式选择")
        print("   ✅ 条件分支逻辑智能执行")
        print("   ✅ 双模式识别 (XML + 视觉)")
        print("   ✅ 完整资源跟踪与保存")
        print("   ✅ JSON → Python 无损转换") 
        print("   ✅ 多格式报告生成")
        print()
        
        print("🚀 Only-Test = 智能化 + 自动化 + 可视化!")


def main():
    """演示入口"""
    demo = CompleteWorkflowDemo()
    
    # 示例用户需求
    test_descriptions = [
        "在抖音APP中搜索'美食视频'，如果搜索框有历史记录先清空",
        "在淘宝中搜索'iPhone 15'，如果有搜索历史先清空，点击第一个商品",
        "在网易云音乐中搜索'周杰伦'，如果搜索框有内容先清空再输入"
    ]
    
    print("请选择演示场景:")
    for i, desc in enumerate(test_descriptions, 1):
        print(f"  {i}. {desc}")
    print(f"  {len(test_descriptions) + 1}. 自定义输入")
    
    try:
        choice = int(input("\\n请输入选择 (1-4): "))
        
        if 1 <= choice <= len(test_descriptions):
            description = test_descriptions[choice - 1]
        elif choice == len(test_descriptions) + 1:
            description = input("请输入您的测试需求: ")
        else:
            description = test_descriptions[0]  # 默认选择
        
        print()
        result = demo.demonstrate_complete_workflow(description)
        
        print("\\n💡 接下来您可以:")
        print(f"   - 查看生成的Python文件: {result['python_file']}")
        print(f"   - 查看会话资源: {result['session_path']}")
        print("   - 执行Python测试: pytest + allure")
        print("   - 集成到CI/CD流水线")
        
    except KeyboardInterrupt:
        print("\\n👋 演示已取消")
    except Exception as e:
        print(f"\\n❌ 演示过程中出错: {e}")


if __name__ == "__main__":
    main()