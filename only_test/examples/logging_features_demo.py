"""
日志功能演示 - 展示unified_logger的新功能
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from only_test.lib.logging.unified_logger import UnifiedLogger


def demo_phase_prefix():
    """演示阶段前缀功能"""
    print("\n" + "="*60)
    print("演示1: 阶段前缀功能")
    print("="*60)

    logger = UnifiedLogger(
        session_id="demo_phase",
        log_dir="logs/demo",
        console_level=20  # INFO
    )

    # 计划阶段
    logger.set_phase("plan")
    logger.info("分析需求并制定测试计划")
    logger.info("识别关键测试场景")

    # 执行阶段 - 8轮
    for round_num in range(1, 9):
        logger.set_phase("execution", current_round=round_num, max_rounds=8)
        logger.info(f"执行第{round_num}个测试步骤")
        time.sleep(0.1)

    # 完成阶段
    logger.set_phase("completion")
    logger.info("测试执行完成，生成报告")

    logger.close()


def demo_tool_result_summary():
    """演示工具执行结果摘要"""
    print("\n" + "="*60)
    print("演示2: 工具执行结果摘要")
    print("="*60)

    logger = UnifiedLogger(
        session_id="demo_tool",
        log_dir="logs/demo",
        console_level=20
    )

    logger.set_phase("execution", current_round=1, max_rounds=3)

    # 模拟屏幕信息工具结果
    screen_result = {
        "total_elements": 45,
        "clickable_elements": 12,
        "current_page": "首页",
        "media_playing": True,
        "ads_info": {
            "confidence": 0.85,
            "auto_close_attempts": 2,
            "auto_closed": True
        }
    }

    logger.log_tool_execution(
        tool_name="get_current_screen_info",
        success=True,
        result=screen_result,
        execution_time=2.5
    )

    # 模拟应用启动结果
    start_app_result = {
        "success": True,
        "app_name": "测试应用"
    }

    logger.log_tool_execution(
        tool_name="start_app",
        success=True,
        result=start_app_result,
        execution_time=1.2
    )

    logger.close()


def demo_error_display():
    """演示错误信息内联显示"""
    print("\n" + "="*60)
    print("演示3: 错误信息内联显示")
    print("="*60)

    logger = UnifiedLogger(
        session_id="demo_error",
        log_dir="logs/demo",
        console_level=20
    )

    logger.set_phase("execution", current_round=2, max_rounds=5)

    # 详细错误日志
    logger.log_error_detailed(
        error_type="ElementNotFoundError",
        message="无法找到目标元素",
        details={
            "selector": "text='登录按钮'",
            "timeout": "10s",
            "page": "登录页"
        },
        suggestion="检查元素选择器是否正确，或增加等待时间",
        error_file="login_test.py:line 45"
    )

    # LLM操作错误
    logger.log_llm_action_error(
        intent="点击视频播放按钮",
        error_message="元素被其他元素遮挡",
        element_info={
            "text": "播放",
            "type": "Button",
            "bounds": "[100,200][300,280]"
        }
    )

    logger.close()


def demo_session_statistics():
    """演示会话统计功能"""
    print("\n" + "="*60)
    print("演示4: 会话统计功能")
    print("="*60)

    logger = UnifiedLogger(
        session_id="demo_stats",
        log_dir="logs/demo",
        console_level=20
    )

    # 设置测试用例信息
    logger.set_test_case_info("视频播放测试", total_steps=8)

    # 模拟多次工具调用
    logger.set_phase("execution")
    for i in range(5):
        screen_result = {"total_elements": 30 + i * 5}
        logger.log_tool_execution(
            tool_name=f"get_current_screen_info_round_{i+1}",
            success=True,
            result=screen_result,
            execution_time=2.0 + i * 0.5
        )

    # 模拟LLM调用
    logger.log_llm_interaction(
        prompt="生成测试步骤",
        response='{"action": "click", "target": "播放按钮"}',
        model="gpt-4",
        execution_time=1.5,
        tokens_used=350
    )

    logger.log_llm_interaction(
        prompt="验证播放状态",
        response='{"status": "success"}',
        model="gpt-4",
        execution_time=1.2,
        tokens_used=280
    )

    # 记录一些错误
    logger.track_error("timeout", "元素等待超时")
    logger.track_error("ElementNotFoundError", "无法找到元素")

    # 会话结束，输出统计
    logger.log_session_end({"status": "completed"})

    logger.close()


def demo_element_selection():
    """演示元素选择可追溯性"""
    print("\n" + "="*60)
    print("演示5: 元素选择可追溯性")
    print("="*60)

    logger = UnifiedLogger(
        session_id="demo_element",
        log_dir="logs/demo",
        console_level=20
    )

    logger.set_phase("execution", current_round=3, max_rounds=6)

    # 详细版本 - 显示所有候选元素
    candidates = [
        {"id": "elem_1", "type": "Button", "text": "登录"},
        {"id": "elem_2", "type": "Button", "text": "注册"},
        {"id": "elem_3", "type": "Button", "text": "忘记密码"},
        {"id": "elem_4", "type": "TextView", "text": "用户协议"}
    ]

    selected = candidates[0]

    logger.log_element_selection(
        intent="点击登录按钮",
        candidates=candidates,
        selected_element=selected,
        reason="文本匹配'登录'且类型为Button",
        confidence=0.95
    )

    print()

    # 简化版本 - 只显示选中元素
    logger.log_element_selection_simple(
        intent="输入用户名",
        selected_element={"type": "EditText", "text": "", "hint": "请输入用户名"},
        reason="匹配hint文本'请输入用户名'",
        confidence=0.88
    )

    logger.close()


if __name__ == "__main__":
    # 运行所有演示
    demo_phase_prefix()
    demo_tool_result_summary()
    demo_error_display()
    demo_session_statistics()
    demo_element_selection()

    print("\n" + "="*60)
    print("所有演示完成！")
    print("日志文件保存在: logs/demo/")
    print("="*60)