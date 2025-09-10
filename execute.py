#!/usr/bin/env python3
"""
Only-Test 测试执行器
支持设备参数执行指定测试用例

用法:
    python execute.py -d mi9_pro_5g                    # 执行默认测试用例
    python execute.py -d mi9_pro_5g -t search_vod      # 执行指定测试用例
    python execute.py -d mi9_pro_5g -f testcases/      # 执行指定目录下所有用例
    python execute.py -d mi9_pro_5g --generate         # 先生成测试用例再执行
"""

import sys
import os
import argparse
import json
import subprocess
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), './'))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'execute_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("only_test_executor")

class OnlyTestExecutor:
    """Only-Test 执行器"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.base_dir = Path(__file__).parent
        self.testcases_dir = self.base_dir / "airtest" / "testcases" / "python"
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # 设备配置映射
        self.device_configs = {
            "mi9_pro_5g": {
                "adb_id": "192.168.100.112:5555",
                "name": "Mi 9 Pro 5G", 
                "resolution": "1080x2340",
                "android_version": "11"
            },
            "tv_box": {
                "adb_id": "192.168.100.113:5555",
                "name": "TV Box",
                "resolution": "1920x1080", 
                "android_version": "9"
            }
        }
    
    def get_device_config(self) -> Dict[str, Any]:
        """获取设备配置"""
        if self.device_id in self.device_configs:
            return self.device_configs[self.device_id]
        else:
            logger.warning(f"未找到设备 {self.device_id} 的配置，使用默认配置")
            return {
                "adb_id": self.device_id,
                "name": self.device_id,
                "resolution": "1080x1920",
                "android_version": "unknown"
            }
    
    def list_available_testcases(self) -> List[str]:
        """列出可用的测试用例"""
        testcases = []
        if self.testcases_dir.exists():
            for py_file in self.testcases_dir.glob("*.py"):
                if py_file.name != "__init__.py":
                    testcases.append(py_file.stem)
        return testcases
    
    def execute_testcase(self, testcase_name: str) -> Dict[str, Any]:
        """执行单个测试用例"""
        testcase_file = self.testcases_dir / f"{testcase_name}.py"
        
        if not testcase_file.exists():
            logger.error(f"测试用例文件不存在: {testcase_file}")
            return {"success": False, "error": f"测试用例文件不存在: {testcase_file}"}
        
        # 获取设备配置
        device_config = self.get_device_config()
        
        logger.info(f"开始执行测试用例: {testcase_name}")
        logger.info(f"目标设备: {device_config['name']} ({device_config['adb_id']})")
        
        # 创建结果目录
        result_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = self.results_dir / f"{testcase_name}_{self.device_id}_{result_timestamp}"
        result_dir.mkdir(exist_ok=True)
        
        # 修改测试用例中的设备连接信息
        modified_testcase = self._modify_testcase_for_device(testcase_file, device_config)
        modified_file = result_dir / f"{testcase_name}_modified.py"
        
        with open(modified_file, 'w', encoding='utf-8') as f:
            f.write(modified_testcase)
        
        # 执行测试用例
        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, str(modified_file)],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            execution_time = time.time() - start_time
            
            # 保存执行结果
            execution_result = {
                "testcase": testcase_name,
                "device": device_config,
                "timestamp": result_timestamp,
                "execution_time": execution_time,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            # 保存结果到JSON文件
            result_file = result_dir / "execution_result.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(execution_result, f, indent=2, ensure_ascii=False)
            
            # 保存日志
            log_file = result_dir / "execution.log"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== STDOUT ===\n{result.stdout}\n")
                f.write(f"=== STDERR ===\n{result.stderr}\n")
            
            if result.returncode == 0:
                logger.info(f"✅ 测试用例 {testcase_name} 执行成功 (耗时: {execution_time:.2f}s)")
            else:
                logger.error(f"❌ 测试用例 {testcase_name} 执行失败 (返回码: {result.returncode})")
                logger.error(f"错误信息: {result.stderr}")
            
            return execution_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ 测试用例 {testcase_name} 执行超时")
            return {
                "success": False, 
                "error": "执行超时",
                "testcase": testcase_name,
                "device": device_config,
                "timestamp": result_timestamp
            }
        except Exception as e:
            logger.error(f"❌ 执行测试用例时发生异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "testcase": testcase_name, 
                "device": device_config,
                "timestamp": result_timestamp
            }
    
    def _modify_testcase_for_device(self, testcase_file: Path, device_config: Dict[str, Any]) -> str:
        """为指定设备修改测试用例"""
        with open(testcase_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换设备连接字符串
        # 查找 connect_device 行
        lines = content.split('\n')
        modified_lines = []
        
        for line in lines:
            if 'connect_device(' in line and line.strip().startswith('connect_device('):
                # 替换为新的设备连接
                new_connect_line = f'connect_device("android://127.0.0.1:5037/{device_config["adb_id"]}?touch_method=ADBTOUCH&")'
                modified_lines.append(new_connect_line)
                logger.info(f"修改设备连接: {new_connect_line}")
            else:
                modified_lines.append(line)
        
        return '\n'.join(modified_lines)
    
    def execute_testcases_in_directory(self, directory: Path) -> List[Dict[str, Any]]:
        """执行目录下所有测试用例"""
        results = []
        
        if not directory.exists():
            logger.error(f"目录不存在: {directory}")
            return results
        
        testcase_files = list(directory.glob("*.py"))
        testcase_files = [f for f in testcase_files if f.name != "__init__.py"]
        
        logger.info(f"找到 {len(testcase_files)} 个测试用例文件")
        
        for testcase_file in testcase_files:
            testcase_name = testcase_file.stem
            result = self.execute_testcase(testcase_name)
            results.append(result)
        
        return results
    
    def generate_testcase(self, description: str) -> Optional[str]:
        """生成新的测试用例"""
        logger.info("正在调用 LLM 生成测试用例...")
        
        try:
            # 调用测试用例生成器
            from only_test.lib.test_generator import TestCaseGenerator
            
            generator = TestCaseGenerator(device_id=self.device_id)
            testcase_name = generator.generate_from_description(description)
            
            logger.info(f"✅ 成功生成测试用例: {testcase_name}")
            return testcase_name
            
        except ImportError:
            logger.error("❌ 测试用例生成器模块未找到")
            return None
        except Exception as e:
            logger.error(f"❌ 生成测试用例失败: {e}")
            return None
    
    def print_execution_summary(self, results: List[Dict[str, Any]]):
        """打印执行摘要"""
        print("\n" + "="*60)
        print("Only-Test 执行摘要")
        print("="*60)
        
        successful = len([r for r in results if r.get('success', False)])
        failed = len(results) - successful
        
        print(f"总共执行: {len(results)} 个测试用例")
        print(f"成功: {successful} 个")
        print(f"失败: {failed} 个")
        print(f"成功率: {(successful/len(results)*100):.1f}%" if results else "0%")
        
        print(f"\n设备信息:")
        if results:
            device = results[0].get('device', {})
            print(f"  设备: {device.get('name', 'Unknown')}")
            print(f"  ADB ID: {device.get('adb_id', 'Unknown')}")
            print(f"  分辨率: {device.get('resolution', 'Unknown')}")
        
        print(f"\n详细结果:")
        for i, result in enumerate(results, 1):
            status = "✅ 成功" if result.get('success', False) else "❌ 失败"
            testcase = result.get('testcase', 'Unknown')
            exec_time = result.get('execution_time', 0)
            print(f"  {i}. {testcase}: {status} ({exec_time:.2f}s)")
        
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Only-Test 测试执行器')
    parser.add_argument('-d', '--device', required=True, help='设备ID (如: mi9_pro_5g)')
    parser.add_argument('-t', '--testcase', help='指定测试用例名称')
    parser.add_argument('-f', '--folder', help='指定测试用例目录')
    parser.add_argument('--generate', help='生成新测试用例的描述')
    parser.add_argument('--list', action='store_true', help='列出所有可用测试用例')
    
    args = parser.parse_args()
    
    executor = OnlyTestExecutor(args.device)
    
    # 列出可用测试用例
    if args.list:
        testcases = executor.list_available_testcases()
        print("可用的测试用例:")
        for i, testcase in enumerate(testcases, 1):
            print(f"  {i}. {testcase}")
        return
    
    results = []
    
    # 生成新测试用例
    if args.generate:
        testcase_name = executor.generate_testcase(args.generate)
        if testcase_name:
            print(f"✅ 生成测试用例: {testcase_name}")
            # 执行新生成的测试用例
            result = executor.execute_testcase(testcase_name)
            results.append(result)
        else:
            print("❌ 测试用例生成失败")
            return
    
    # 执行指定测试用例
    elif args.testcase:
        result = executor.execute_testcase(args.testcase)
        results.append(result)
    
    # 执行指定目录下所有测试用例
    elif args.folder:
        folder_path = Path(args.folder)
        if not folder_path.is_absolute():
            folder_path = executor.base_dir / folder_path
        results = executor.execute_testcases_in_directory(folder_path)
    
    # 执行默认测试用例
    else:
        # 执行 example_airtest_record.py
        result = executor.execute_testcase("example_airtest_record")
        results.append(result)
    
    # 打印执行摘要
    if results:
        executor.print_execution_summary(results)


if __name__ == "__main__":
    main()