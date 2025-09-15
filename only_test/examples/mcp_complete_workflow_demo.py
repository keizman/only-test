#!/usr/bin/env python3
"""
Only-Test MCP Complete Workflow Demo
====================================

完整演示AI驱动的测试用例生成和执行工作流程

这个示例展示了用户设想的完整工作流程：
1. 新用例生成需求 → 使用生成器
2. 生成器使用LLM生成，告诉它如何使用工具获取当前设备信息和状态
3. LLM筛选设备信息用于每一步 (它已读过类似用例，知道如何编写用例)
4. 将JSON转换为Python
5. 尝试运行，给LLM反馈。如果成功，完成

运行方式:

python "C:\Download\git\uni\only_test\examples\mcp_llm_workflow_demo.py" --requirement "测试 vod 点播播放正常((h264)): 1.进入APK后就是首页，执行关闭广告函数，2.找到searchbtn点击，直到可输入状态后输入节目名称'英语和西语音轨'点击节目，3.播放节目，断言: 验证设备是否处于播放状态" --target-app com.mobile.brasiltvmobile --max-rounds 1 --auto-close-limit 2 --logdir logs/mcp_demo --outdir only_test/testcases/generated
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from only_test.lib.mcp_interface import (
    WorkflowOrchestrator,
    MCPServer,
    DeviceInspector, 
    InteractiveCaseGenerator,
    FeedbackLoop
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPWorkflowDemo:
    """MCP工作流程演示类"""
    
    def __init__(self, device_id: str = "emulator-5554"):
        self.device_id = device_id
        self.orchestrator = None
        self.demo_results = []
    
    async def setup(self):
        """初始化演示环境"""
        print("🚀 初始化MCP工作流程演示...")
        
        try:
            self.orchestrator = WorkflowOrchestrator(self.device_id)
            await self.orchestrator.initialize()
            
            print(f"✅ MCP服务器初始化成功")
            print(f"📱 目标设备: {self.device_id}")
            print(f"🔧 已注册工具数量: {len(self.orchestrator.tool_registry.get_all_tools())}")
            return True
            
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            return False
    
    async def demo_1_quick_workflow(self):
        """演示1: 快速工作流程"""
        print("\n" + "="*60)
        print("📋 演示1: 快速工作流程 (单次迭代)")
        print("="*60)
        
        test_requirement = "打开设置应用，点击关于手机选项，验证页面显示正确的设备信息"
        
        print(f"🎯 测试需求: {test_requirement}")
        print("⏱️  工作流程模式: quick")
        print("🔄 最大迭代次数: 1")
        
        try:
            result = await self.orchestrator.start_complete_workflow(
                test_requirement=test_requirement,
                target_app="com.android.settings",
                workflow_mode="quick",
                max_iterations=1
            )
            
            self._print_workflow_result("快速工作流程", result)
            self.demo_results.append(("demo_1_quick_workflow", result))
            return True
            
        except Exception as e:
            print(f"❌ 快速工作流程执行失败: {e}")
            return False
    
    async def demo_2_standard_workflow(self):
        """演示2: 标准工作流程"""
        print("\n" + "="*60)
        print("📋 演示2: 标准工作流程 (多次迭代)")
        print("="*60)
        
        test_requirement = "测试微信登录功能：打开微信应用，输入手机号和密码，点击登录按钮，验证登录成功"
        
        print(f"🎯 测试需求: {test_requirement}")
        print("⏱️  工作流程模式: standard") 
        print("🔄 最大迭代次数: 3")
        
        try:
            result = await self.orchestrator.start_complete_workflow(
                test_requirement=test_requirement,
                target_app="com.tencent.mm",
                workflow_mode="standard",
                max_iterations=3
            )
            
            self._print_workflow_result("标准工作流程", result)
            self.demo_results.append(("demo_2_standard_workflow", result))
            return True
            
        except Exception as e:
            print(f"❌ 标准工作流程执行失败: {e}")
            return False
    
    async def demo_3_comprehensive_workflow(self):
        """演示3: 全面工作流程"""
        print("\n" + "="*60)
        print("📋 演示3: 全面工作流程 (详细调试)")
        print("="*60)
        
        test_requirement = "测试电商应用购物流程：搜索商品'手机'，选择第一个商品，加入购物车，查看购物车"
        
        print(f"🎯 测试需求: {test_requirement}")
        print("⏱️  工作流程模式: comprehensive")
        print("🔄 最大迭代次数: 5")
        
        try:
            result = await self.orchestrator.start_complete_workflow(
                test_requirement=test_requirement,
                target_app="com.example.shopping",
                workflow_mode="comprehensive",
                max_iterations=5
            )
            
            self._print_workflow_result("全面工作流程", result)
            self.demo_results.append(("demo_3_comprehensive_workflow", result))
            return True
            
        except Exception as e:
            print(f"❌ 全面工作流程执行失败: {e}")
            return False
    
    async def demo_4_component_usage(self):
        """演示4: 分步使用组件"""
        print("\n" + "="*60)
        print("📋 演示4: 分步使用MCP组件")
        print("="*60)
        
        try:
            # 步骤1: 获取设备信息
            print("🔍 步骤1: 获取设备信息...")
            device_inspector = self.orchestrator.device_inspector
            device_info = await device_inspector.get_comprehensive_device_info()
            
            if device_info.get("success"):
                print(f"✅ 设备信息获取成功，包含 {len(device_info['result'])} 项信息")
                print(f"   - 设备型号: {device_info['result'].get('device_model', '未知')}")
                print(f"   - 系统版本: {device_info['result'].get('android_version', '未知')}")
                print(f"   - 屏幕分辨率: {device_info['result'].get('screen_size', '未知')}")
            else:
                print(f"❌ 设备信息获取失败: {device_info.get('error')}")
                return False
            
            # 步骤2: 生成测试用例
            print("\n🎯 步骤2: 生成测试用例...")
            case_generator = self.orchestrator.case_generator
            
            test_case_result = await case_generator.generate_case_with_llm_guidance(
                "点击返回按钮并验证页面跳转",
                {
                    "device_info": device_info["result"],
                    "target_app": "com.android.chrome",
                    "context": "当前在浏览器页面"
                }
            )
            
            if test_case_result.get("success"):
                test_case = test_case_result["result"]
                print(f"✅ 测试用例生成成功")
                print(f"   - 用例ID: {test_case.get('testcase_id')}")
                print(f"   - 用例名称: {test_case.get('name')}")
                print(f"   - 执行步骤: {len(test_case.get('execution_path', []))} 步")
            else:
                print(f"❌ 测试用例生成失败: {test_case_result.get('error')}")
                return False
            
            # 步骤3: 执行并获取反馈
            print("\n⚡ 步骤3: 执行测试用例...")
            feedback_loop = self.orchestrator.feedback_loop
            
            execution_result = await feedback_loop.execute_and_analyze(
                test_case,
                execution_mode="full"
            )
            
            print(f"📊 执行结果状态: {execution_result.get('status')}")
            
            if execution_result.get("status") == "completed":
                exec_success = execution_result.get("execution", {}).get("success", False)
                feedback = execution_result.get("feedback", {})
                
                print(f"   - 执行成功: {'✅' if exec_success else '❌'}")
                print(f"   - 整体评估: {feedback.get('overall_assessment', '未知')}")
                print(f"   - 改进建议数: {len(feedback.get('improvement_actions', []))}")
            
            # 步骤4: 获取统计信息
            print("\n📈 步骤4: 获取执行统计...")
            stats = await feedback_loop.get_execution_statistics("24h")
            
            print(f"   - 总执行次数: {stats.get('total_executions', 0)}")
            print(f"   - 成功率: {stats.get('success_rate', 0):.2%}")
            print(f"   - 失败模式数: {len(stats.get('failure_patterns', {}))}")
            
            self.demo_results.append(("demo_4_component_usage", {
                "device_info": device_info,
                "test_case": test_case_result,
                "execution": execution_result,
                "statistics": stats
            }))
            
            return True
            
        except Exception as e:
            print(f"❌ 组件使用演示失败: {e}")
            return False
    
    async def demo_5_workflow_monitoring(self):
        """演示5: 工作流程监控"""
        print("\n" + "="*60)
        print("📋 演示5: 工作流程监控和管理")
        print("="*60)
        
        try:
            # 获取当前工作流程状态
            print("📊 获取工作流程统计信息...")
            status = await self.orchestrator.get_workflow_status()
            
            print(f"   - 活跃工作流程: {status.get('active_workflows', 0)}")
            print(f"   - 历史工作流程: {len(self.orchestrator.workflow_history)}")
            
            stats = status.get('workflow_stats', {})
            print(f"   - 总工作流程: {stats.get('total_workflows', 0)}")
            print(f"   - 成功工作流程: {stats.get('successful_workflows', 0)}")
            print(f"   - 失败工作流程: {stats.get('failed_workflows', 0)}")
            print(f"   - 平均完成时间: {stats.get('average_completion_time', 0):.2f}秒")
            
            # 启动一个工作流程用于监控演示
            print("\n🚀 启动工作流程用于监控演示...")
            workflow_task = asyncio.create_task(
                self.orchestrator.start_complete_workflow(
                    test_requirement="简单的点击测试用于监控演示",
                    workflow_mode="quick",
                    max_iterations=1
                )
            )
            
            # 等待一点时间让工作流程启动
            await asyncio.sleep(1)
            
            # 检查活跃工作流程
            print("🔍 检查活跃工作流程...")
            status = await self.orchestrator.get_workflow_status()
            
            if status.get('active_workflows', 0) > 0:
                workflow_ids = status.get('active_workflow_ids', [])
                if workflow_ids:
                    workflow_id = workflow_ids[0]
                    print(f"   - 发现活跃工作流程: {workflow_id}")
                    
                    # 获取详细状态
                    detailed_status = await self.orchestrator.get_workflow_status(workflow_id)
                    if detailed_status.get("found"):
                        workflow = detailed_status["workflow"]
                        print(f"   - 当前状态: {workflow.get('status')}")
                        print(f"   - 当前迭代: {workflow.get('current_iteration')}")
                        print(f"   - 已完成阶段: {len(workflow.get('phases', []))}")
            
            # 等待工作流程完成
            print("⏳ 等待工作流程完成...")
            workflow_result = await workflow_task
            
            print(f"✅ 监控演示完成，工作流程结果: {workflow_result.get('status')}")
            
            self.demo_results.append(("demo_5_workflow_monitoring", {
                "initial_status": status,
                "workflow_result": workflow_result
            }))
            
            return True
            
        except Exception as e:
            print(f"❌ 工作流程监控演示失败: {e}")
            return False
    
    def _print_workflow_result(self, demo_name: str, result: Dict):
        """打印工作流程结果"""
        print(f"\n📊 {demo_name} 结果:")
        print(f"   - 工作流程ID: {result.get('workflow_id')}")
        print(f"   - 状态: {result.get('status')} {'✅' if result.get('status') == 'completed' else '❌'}")
        print(f"   - 执行时间: {result.get('execution_time', 0):.2f}秒")
        print(f"   - 完成阶段: {result.get('phases_completed')}")
        print(f"   - 迭代次数: {result.get('iterations')}")
        
        if result.get('message'):
            print(f"   - 消息: {result['message']}")
    
    async def generate_demo_report(self):
        """生成演示报告"""
        print("\n" + "="*60)
        print("📋 生成演示报告")
        print("="*60)
        
        report = {
            "demo_session": {
                "timestamp": datetime.now().isoformat(),
                "device_id": self.device_id,
                "total_demos": len(self.demo_results)
            },
            "demo_results": self.demo_results,
            "system_stats": await self.orchestrator.get_workflow_status() if self.orchestrator else {}
        }
        
        # 保存报告到文件
        report_file = f"mcp_demo_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(os.path.dirname(__file__), "..", "reports", report_file)
        
        # 确保报告目录存在
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"📄 演示报告已保存: {report_path}")
            
            # 打印总结
            successful_demos = sum(1 for _, result in self.demo_results 
                                 if isinstance(result, dict) and result.get('status') == 'completed')
            
            print(f"\n📈 演示总结:")
            print(f"   - 总演示数: {len(self.demo_results)}")
            print(f"   - 成功演示: {successful_demos}")
            print(f"   - 成功率: {successful_demos / len(self.demo_results) * 100:.1f}%" if self.demo_results else "0%")
            
        except Exception as e:
            print(f"❌ 报告生成失败: {e}")
    
    async def cleanup(self):
        """清理资源"""
        print(f"\n🧹 清理演示资源...")
        
        if self.orchestrator:
            # 清理缓存
            if self.orchestrator.device_inspector:
                self.orchestrator.device_inspector.clear_cache()
            
            if self.orchestrator.feedback_loop:
                self.orchestrator.feedback_loop.feedback_history.clear()
        
        print(f"✅ 资源清理完成")


async def main():
    """主函数"""
    print("🎭 Only-Test MCP Complete Workflow Demo")
    print("=" * 50)
    
    # 检查命令行参数
    device_id = sys.argv[1] if len(sys.argv) > 1 else "emulator-5554"
    
    demo = MCPWorkflowDemo(device_id)
    
    try:
        # 初始化
        if not await demo.setup():
            return
        
        print(f"\n🎯 开始演示，使用设备: {device_id}")
        print("提示: 确保设备已连接并可用")
        
        demos = [
            ("快速工作流程", demo.demo_1_quick_workflow),
            ("标准工作流程", demo.demo_2_standard_workflow), 
            ("全面工作流程", demo.demo_3_comprehensive_workflow),
            ("组件使用", demo.demo_4_component_usage),
            ("工作流程监控", demo.demo_5_workflow_monitoring)
        ]
        
        # 执行所有演示
        for demo_name, demo_func in demos:
            print(f"\n▶️  开始执行: {demo_name}")
            success = await demo_func()
            
            if success:
                print(f"✅ {demo_name} 完成")
            else:
                print(f"❌ {demo_name} 失败")
            
            # 短暂等待
            await asyncio.sleep(2)
        
        # 生成报告
        await demo.generate_demo_report()
        
    except KeyboardInterrupt:
        print(f"\n⏹️  演示被用户中断")
    except Exception as e:
        print(f"\n💥 演示执行异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        await demo.cleanup()
        print(f"\n🎉 MCP工作流程演示结束")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())