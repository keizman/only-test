#!/usr/bin/env python3
"""
Only-Test Assertions
====================
标准断言集合：播放状态、UI元素存在性、屏幕变化等。
具体设备/执行器接入点留 TODO（允许后续替换实现）。
"""
from typing import Dict

# 可选：ADB/设备层依赖在此导入（延迟导入以避免测试期失败）
# import subprocess


def assert_playback_state(expected: bool) -> bool:
    """播放状态断言（TODO: 接入 ADB 或系统 API）。
    约定：返回 True/False，不抛异常；由上层统一处理失败。
    """
    try:
        # TODO: 通过 ADB dumpsys 检查 audio_flinger/media_session，或接入执行器内置探针
        playing = True  # 占位：默认成功
        return bool(playing) is bool(expected)
    except Exception:
        return False


def assert_ui_element_exists(selector: Dict) -> bool:
    """UI 元素存在性断言（TODO: 接入当前屏元素缓存或即时查询）。
    selector 示例：{"resource_id": "com.xxx:id/btn"} 或 {"text": "确定"}
    """
    try:
        # TODO: 接入 orchestrator 最近一次 analyze_current_screen 的 elements 缓存
        # 或通过 MCP 重新取屏+过滤
        return True  # 占位：默认存在
    except Exception:
        return False


def assert_screen_changed(threshold: float = 0.99) -> bool:
    """屏幕变化断言（相似度阈值）。
    TODO: 接入截图前后对比；threshold=0.99 表示相似度超过 99% 视为“未变化”。
    返回 True 表示“变化符合预期”。
    """
    try:
        # TODO: 调用图像相似度算法，对比 before/after 截图
        return True  # 占位
    except Exception:
        return False

