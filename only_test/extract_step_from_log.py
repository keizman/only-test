#!/usr/bin/env python3
"""
从 mcp_execution_log.json 提取指定 round 的步骤并保存为文件

用法:
  python only_test/extract_step_from_log.py <log_file> <round_number> [output_file]

示例:
  # 提取 round 3 的步骤，保存到 step_round_3.json
  python only_test/extract_step_from_log.py logs/mcp_demo/session_20251022_165120/mcp_execution_log.json 3

  # 提取 round 3 的步骤，保存到指定文件
  python only_test/extract_step_from_log.py logs/mcp_demo/session_20251022_165120/mcp_execution_log.json 3 my_step.json

然后可以用 debug_execute_step.py 测试:
  python only_test/debug_execute_step.py "192.168.100.112:5555" --file step_round_3.json
"""

import sys
import json
from pathlib import Path


def extract_step(log_file: str, round_number: int, output_file: str = None):
    """从日志文件提取指定 round 的步骤"""
    
    # 读取日志文件
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # 尝试作为 JSON 数组读取
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                # 如果不是数组，尝试按行读取（旧格式）
                f.seek(0)
                logs = []
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
    except FileNotFoundError:
        print(f"[ERROR] 文件不存在: {log_file}")
        return False
    except Exception as e:
        print(f"[ERROR] 读取文件失败: {e}")
        return False
    
    if not logs:
        print("[ERROR] 日志文件为空或格式不正确")
        return False
    
    print(f"[LOG FILE] {log_file}")
    print(f"[RECORDS] 共有 {len(logs)} 条记录")
    print()
    
    # 查找指定 round 的 execute_step_json 记录
    target_entry = None
    for entry in logs:
        if (entry.get("tool") == "execute_step_json" and 
            entry.get("round") == round_number):
            target_entry = entry
            break
    
    if not target_entry:
        print(f"[ERROR] 未找到 round {round_number} 的 execute_step_json 记录")
        print("\n可用的 rounds:")
        rounds = set()
        for entry in logs:
            if entry.get("tool") == "execute_step_json" and "round" in entry:
                rounds.add(entry["round"])
        if rounds:
            for r in sorted(rounds):
                print(f"  - round {r}")
        else:
            print("  (无)")
        return False
    
    # 提取 step
    step = None
    parameters = target_entry.get("parameters", {})
    if isinstance(parameters, dict) and "step" in parameters:
        step = parameters["step"]
    
    if not step:
        print(f"[ERROR] round {round_number} 的记录中没有 step 数据")
        return False
    
    print(f"[OK] 找到 round {round_number} 的步骤:")
    print(f"   动作: {step.get('action')}")
    print(f"   成功: {target_entry.get('success')}")
    print()
    
    # 确定输出文件名
    if output_file is None:
        output_file = f"step_round_{round_number}.json"
    
    # 保存到文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(step, f, ensure_ascii=False, indent=2)
        print(f"[OK] 步骤已保存到: {output_file}")
        print()
        print("[STEP JSON] 完整内容:")
        print(json.dumps(step, ensure_ascii=False, indent=2))
        print()
        print("[USAGE] 使用以下命令测试:")
        print(f'   python only_test/debug_execute_step.py "YOUR_DEVICE_ID" --file {output_file}')
        return True
    except Exception as e:
        print(f"[ERROR] 保存文件失败: {e}")
        return False


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\n[ERROR] 参数不足!")
        print(f"Usage: {sys.argv[0]} <log_file> <round_number> [output_file]")
        sys.exit(1)
    
    log_file = sys.argv[1]
    try:
        round_number = int(sys.argv[2])
    except ValueError:
        print(f"[ERROR] round_number 必须是整数: {sys.argv[2]}")
        sys.exit(1)
    
    output_file = sys.argv[3] if len(sys.argv) >= 4 else None
    
    success = extract_step(log_file, round_number, output_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

