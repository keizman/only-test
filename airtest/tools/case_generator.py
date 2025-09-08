#!/usr/bin/env python3
"""
Only-Test 智能测试用例生成工具

支持基于模板和 LLM 生成智能测试用例
展示如何利用智能元数据创建真正智能的测试用例
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class SmartTestCaseGenerator:
    """智能测试用例生成器"""
    
    def __init__(self, templates_dir: str = "../testcases/templates"):
        """
        初始化生成器
        
        Args:
            templates_dir: 模板文件目录
        """
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path("../testcases/generated")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def list_templates(self) -> List[str]:
        """
        列出可用的模板
        
        Returns:
            List[str]: 模板名称列表
        """
        templates = []
        for template_file in self.templates_dir.glob("*.json"):
            templates.append(template_file.stem)
        return templates
    
    def load_template(self, template_name: str) -> Dict[str, Any]:
        """
        加载模板文件
        
        Args:
            template_name: 模板名称
            
        Returns:
            Dict: 模板数据
        """
        template_path = self.templates_dir / f"{template_name}.json"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
            
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate_from_template(self, 
                             template_name: str,
                             app_package: str,
                             search_keyword: str = "测试内容",
                             device_type: str = "android_phone") -> Dict[str, Any]:
        """
        基于模板生成测试用例
        
        Args:
            template_name: 模板名称
            app_package: 目标应用包名
            search_keyword: 搜索关键词
            device_type: 设备类型
            
        Returns:
            Dict: 生成的测试用例
        """
        template = self.load_template(template_name)
        
        # 生成新的测试用例ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_testcase_id = f"TC_{app_package.upper().replace('.', '_')}_{timestamp}"
        
        # 更新基础信息
        testcase = template.copy()
        testcase["testcase_id"] = new_testcase_id
        testcase["name"] = f"{app_package} - 智能搜索测试"
        testcase["generated_at"] = datetime.now().isoformat()
        testcase["generated_from_template"] = template_name
        testcase["target_app"] = app_package
        
        # 更新变量
        if "variables" in testcase:
            testcase["variables"]["search_keyword"] = search_keyword
            testcase["variables"]["target_app_package"] = app_package
            
        # 更新设备类型
        if "metadata" in testcase:
            testcase["metadata"]["device_types"] = [device_type]
            testcase["metadata"]["tags"].append(f"app_{app_package}")
            
        # 更新上下文
        if "context_awareness" in testcase:
            testcase["context_awareness"]["target_app"] = app_package
            
        return testcase
    
    def generate_with_llm_description(self, 
                                    description: str,
                                    app_package: str,
                                    device_type: str = "android_phone") -> Dict[str, Any]:
        """
        基于自然语言描述生成测试用例（模拟LLM生成）
        
        Args:
            description: 自然语言描述
            app_package: 应用包名
            device_type: 设备类型
            
        Returns:
            Dict: 生成的测试用例
        """
        # 这里模拟 LLM 的处理过程
        # 实际实现中会调用 LLM API
        
        print(f"🤖 模拟 LLM 处理描述: {description}")
        print(f"📱 目标应用: {app_package}")
        print(f"🔍 分析中...")
        
        # 基于描述选择最适合的模板
        if "搜索" in description or "search" in description.lower():
            base_template = "smart_search_template"
            search_keyword = self._extract_search_keyword(description)
        else:
            # 可以扩展更多模板选择逻辑
            base_template = "smart_search_template" 
            search_keyword = "默认搜索词"
        
        print(f"✅ 选择模板: {base_template}")
        print(f"🔑 提取关键词: {search_keyword}")
        
        # 基于模板生成
        testcase = self.generate_from_template(
            base_template, 
            app_package,
            search_keyword,
            device_type
        )
        
        # 添加 LLM 生成的标记
        testcase["generation_method"] = "llm_assisted"
        testcase["original_description"] = description
        testcase["llm_analysis"] = {
            "detected_intent": "搜索功能测试",
            "key_actions": ["导航到搜索", "智能输入", "执行搜索", "验证结果"],
            "conditional_logic": ["搜索框状态判断", "清空或直接输入"],
            "confidence": 0.95
        }
        
        return testcase
    
    def _extract_search_keyword(self, description: str) -> str:
        """
        从描述中提取搜索关键词
        
        Args:
            description: 描述文本
            
        Returns:
            str: 提取的关键词
        """
        # 简单的关键词提取逻辑
        # 实际实现中可以使用更复杂的 NLP
        import re
        
        # 查找引号中的内容
        quoted_match = re.search(r'[""](.*?)[""]', description)
        if quoted_match:
            return quoted_match.group(1)
        
        # 查找"搜索xxx"模式
        search_match = re.search(r'搜索["""]?([^"""\s，。！？]+)', description)
        if search_match:
            return search_match.group(1)
            
        return "测试内容"
    
    def save_testcase(self, testcase: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        保存测试用例到文件
        
        Args:
            testcase: 测试用例数据
            filename: 文件名（可选）
            
        Returns:
            str: 保存的文件路径
        """
        if filename is None:
            filename = f"{testcase['testcase_id'].lower()}.json"
            
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(testcase, f, ensure_ascii=False, indent=2)
            
        return str(filepath)
    
    def print_testcase_summary(self, testcase: Dict[str, Any]):
        """
        打印测试用例摘要
        
        Args:
            testcase: 测试用例数据
        """
        print("\n" + "="*60)
        print("🎯 生成的测试用例摘要")
        print("="*60)
        print(f"📋 ID: {testcase['testcase_id']}")
        print(f"📝 名称: {testcase['name']}")
        print(f"🏷️  标签: {', '.join(testcase.get('metadata', {}).get('tags', []))}")
        print(f"📱 目标应用: {testcase.get('target_app', 'Unknown')}")
        print(f"⏱️  预估时长: {testcase.get('metadata', {}).get('estimated_duration', 0)}秒")
        
        # 显示条件逻辑
        execution_path = testcase.get('execution_path', [])
        conditional_steps = [step for step in execution_path if step.get('action') == 'conditional_action']
        if conditional_steps:
            print(f"🧠 智能条件步骤数量: {len(conditional_steps)}")
            for i, step in enumerate(conditional_steps, 1):
                condition = step.get('condition', {})
                print(f"   {i}. {step.get('description', 'Unknown condition')}")
                print(f"      条件类型: {condition.get('type', 'Unknown')}")
        
        # 显示 LLM 增强信息
        if "llm_analysis" in testcase:
            analysis = testcase["llm_analysis"]
            print(f"🤖 LLM 分析置信度: {analysis.get('confidence', 0)*100:.1f}%")
            print(f"🎯 检测到的意图: {analysis.get('detected_intent', 'Unknown')}")
        
        print("="*60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Only-Test 智能测试用例生成工具")
    parser.add_argument("--list", action="store_true", help="列出可用模板")
    parser.add_argument("--template", help="使用指定模板生成")
    parser.add_argument("--app", help="目标应用包名")
    parser.add_argument("--keyword", default="测试内容", help="搜索关键词")
    parser.add_argument("--device", default="android_phone", help="设备类型")
    parser.add_argument("--description", help="自然语言描述（LLM模式）")
    parser.add_argument("--output", help="输出文件名")
    
    args = parser.parse_args()
    
    generator = SmartTestCaseGenerator()
    
    if args.list:
        print("📋 可用的测试用例模板:")
        templates = generator.list_templates()
        for i, template in enumerate(templates, 1):
            print(f"  {i}. {template}")
        return
    
    if not args.app:
        print("❌ 错误: 请指定目标应用包名 (--app)")
        sys.exit(1)
    
    try:
        if args.description:
            # LLM 模式
            print("🤖 LLM 辅助生成模式")
            testcase = generator.generate_with_llm_description(
                args.description, 
                args.app,
                args.device
            )
        elif args.template:
            # 模板模式
            print(f"📄 基于模板生成: {args.template}")
            testcase = generator.generate_from_template(
                args.template,
                args.app, 
                args.keyword,
                args.device
            )
        else:
            # 默认使用智能搜索模板
            print("📄 使用默认智能搜索模板")
            testcase = generator.generate_from_template(
                "smart_search_template",
                args.app,
                args.keyword, 
                args.device
            )
        
        # 保存测试用例
        filepath = generator.save_testcase(testcase, args.output)
        
        # 显示摘要
        generator.print_testcase_summary(testcase)
        
        print(f"\n✅ 测试用例已保存到: {filepath}")
        print("\n💡 使用提示:")
        print("   - 查看生成的JSON文件了解详细的条件逻辑")
        print("   - 可以进一步自定义元素选择器和业务逻辑")
        print("   - 支持的条件类型包括：element_content_check, element_exists等")
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()