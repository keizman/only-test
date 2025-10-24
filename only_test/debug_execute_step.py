#!/usr/bin/env python3
"""
调试工具：命令行测试 execute_step_json 的单个步骤

用法 1: 直接传入 JSON
  python only_test/debug_execute_step.py <device_id> '<step_json>'

用法 2: 从文件读取 JSON
  python only_test/debug_execute_step.py <device_id> --file <json_file>

示例（Bash/Linux）:
  python only_test/debug_execute_step.py "192.168.100.112:5555" '{"action":"click","target":{"priority_selectors":[{"resource_id":"com.mobile.brasiltvmobile:id/mVodSearch"}]},"wait_after":0.8}'

示例（PowerShell - 推荐使用文件）:
  # 1. 先把 JSON 保存到文件（从 mcp_execution_log.json 中提取一行）
  echo '{"action":"press","target":{"keyevent":"ENTER"},"wait_after":0.8}' > step.json
  
  # 2. 使用文件路径
  python only_test/debug_execute_step.py "192.168.100.112:5555" --file step.json

注意：支持两种 JSON 格式：
  1. 直接的 step: {"action":"click",...}
  2. 完整日志条目: {"tool":"execute_step_json","parameters":{"step":{...}}}
"""

import sys
import os
import json
import asyncio

# 添加项目路径
_here = os.path.dirname(__file__)
_repo_root = os.path.abspath(os.path.join(_here, ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from only_test.lib.mcp_interface.device_inspector import DeviceInspector


async def test_execute_step(device_id: str, step_json_str: str):
    """测试单个步骤的执行"""
    # 显示接收到的原始字符串（用于调试 PowerShell 引号问题）
    print(f"[INPUT] 接收到的参数长度: {len(step_json_str)} 字符")
    if len(step_json_str) < 200:
        print(f"[INPUT] 原始内容: {step_json_str}")
    else:
        print(f"[INPUT] 原始内容（前200字符）: {step_json_str[:200]}...")
    print()
    
    try:
        data = json.loads(step_json_str)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失败: {e}")
        print(f"\n[DEBUG] 错误位置: 第 {e.lineno} 行, 第 {e.colno} 列")
        if e.pos and e.pos < len(step_json_str):
            start = max(0, e.pos - 20)
            end = min(len(step_json_str), e.pos + 20)
            print(f"[DEBUG] 错误附近内容: ...{step_json_str[start:end]}...")
        print("\n[HINT] 提示：")
        print("  1. 直接的 step JSON: {\"action\":\"click\",\"target\":{...}}")
        print("  2. 完整的日志条目: {\"tool\":\"execute_step_json\",\"parameters\":{\"step\":{...}}}")
        print("\n[HINT] PowerShell 用户建议使用 --file 参数从文件读取 JSON")
        return
    
    # 支持两种输入格式：
    # 1. 直接的 step JSON: {"action": "click", "target": {...}}
    # 2. 完整的日志条目: {"tool": "execute_step_json", "parameters": {"step": {...}}}
    step = data
    if isinstance(data, dict):
        # 如果是日志条目格式，提取 step
        if "tool" in data and data.get("tool") == "execute_step_json":
            if "parameters" in data and isinstance(data["parameters"], dict):
                if "step" in data["parameters"]:
                    step = data["parameters"]["step"]
                    print("[OK] 检测到日志条目格式，已提取 step 字段")
    
    print("=" * 80)
    print("[STEP] 测试步骤:")
    print(json.dumps(step, ensure_ascii=False, indent=2))
    print("=" * 80)
    
    # 初始化设备检查器
    inspector = DeviceInspector(device_id=device_id)
    await inspector.initialize()
    
    print(f"\n[OK] 设备已连接: {device_id}")
    
    # 获取设备基本信息
    try:
        device_info = await inspector.get_device_basic_info()
        if device_info.get("success"):
            print(f"[DEVICE] 设备型号: {device_info.get('model', 'unknown')}")
            print(f"[DEVICE] Android 版本: {device_info.get('android_version', 'unknown')}")
            print(f"[DEVICE] 分辨率: {device_info.get('screen_resolution', 'unknown')}")
    except Exception:
        pass  # 忽略获取设备信息的错误
    
    # 获取当前屏幕信息（用于调试）
    print("\n[INFO] 获取当前屏幕信息...")
    screen_info = await inspector.get_current_screen_info(
        include_elements=True,
        clickable_only=True,
        auto_close_limit=0  # 不自动关广告，避免干扰测试
    )
    
    foreground = screen_info.get("foreground_app", {})
    print(f"[APP] 前台应用: {foreground.get('package_name', 'unknown')}")
    print(f"[PAGE] 页面类型: {foreground.get('page_type', 'unknown')}")
    
    elements = screen_info.get("elements", [])
    print(f"[ELEMENTS] 可交互元素数量: {len(elements)}")
    
    # 执行步骤
    print("\n" + "=" * 80)
    print("[EXECUTE] 开始执行步骤...")
    print("=" * 80)
    
    action = step.get("action", "")
    target = step.get("target", {})
    data = step.get("data", "")
    wait_after = step.get("wait_after", 0.5)
    dx_px = step.get("dx_px", 0)
    dy_px = step.get("dy_px", 0)
    
    print(f"\n动作类型: {action}")
    print(f"目标参数: {json.dumps(target, ensure_ascii=False)}")
    if data:
        print(f"输入数据: {data}")
    if dx_px or dy_px:
        print(f"偏移参数: dx_px={dx_px}, dy_px={dy_px}")
    print(f"等待时间: {wait_after}s")
    
    try:
        result = await inspector.perform_ui_action(
            action=action,
            target=target,
            data=data,
            wait_after=wait_after,
            dx_px=dx_px,
            dy_px=dy_px
        )
        
        print("\n" + "=" * 80)
        print("[RESULT] 执行结果:")
        print("=" * 80)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        success = result.get("success", False)
        if success:
            print("\n[OK] 执行成功!")
        else:
            print("\n[FAIL] 执行失败!")
            print(f"失败原因: {result.get('message', 'unknown')}")
        
    except Exception as e:
        print(f"\n[ERROR] 执行异常: {e}")
        import traceback
        traceback.print_exc()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\n[ERROR] 参数不足!")
        print(f"Usage: {sys.argv[0]} <device_id> '<step_json>'")
        print(f"   or: {sys.argv[0]} <device_id> --file <json_file>")
        sys.exit(1)
    
    device_id = sys.argv[1]
    
    # 支持从文件读取
    if len(sys.argv) >= 4 and sys.argv[2] in ('--file', '-f'):
        json_file = sys.argv[3]
        print(f"[DEBUG TOOL] execute_step_json 单步测试")
        print(f"[DEVICE] {device_id}")
        print(f"[FILE] 从文件读取: {json_file}")
        print()
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                step_json_str = f.read()
        except FileNotFoundError:
            print(f"[ERROR] 文件不存在: {json_file}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] 读取文件失败: {e}")
            sys.exit(1)
    else:
        step_json_str = sys.argv[2]
        print(f"[DEBUG TOOL] execute_step_json 单步测试")
        print(f"[DEVICE] {device_id}")
        print()
    
    asyncio.run(test_execute_step(device_id, step_json_str))


if __name__ == "__main__":
    main()

