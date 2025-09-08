#!/usr/bin/env python3
"""
Only-Test 元素过滤器

核心功能:
1. 自定义元素过滤条件，减少LLM上下文数据量
2. 智能筛选可操作元素
3. 包过滤、文本过滤、可见性过滤
4. 生成适合LLM理解的精简元素描述
5. 支持多种过滤策略和优先级排序
"""

import sys
import os
import json
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("element_filter")


class FilterStrategy(Enum):
    """过滤策略枚举"""
    STRICT = "strict"           # 严格过滤，只保留最相关元素
    BALANCED = "balanced"       # 平衡过滤，保留较多有用元素
    PERMISSIVE = "permissive"   # 宽松过滤，保留大部分元素


class ElementPriority(Enum):
    """元素优先级枚举"""
    CRITICAL = 5    # 关键元素(搜索按钮、播放按钮等)
    HIGH = 4        # 高优先级(导航、主要功能)
    MEDIUM = 3      # 中优先级(一般可点击元素)
    LOW = 2         # 低优先级(装饰性元素)
    IGNORE = 1      # 可忽略(广告、无关元素)


@dataclass
class FilterRule:
    """过滤规则"""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    priority: ElementPriority
    description: str


@dataclass
class FilterResult:
    """过滤结果"""
    filtered_elements: List[Dict[str, Any]]
    original_count: int
    filtered_count: int
    filter_stats: Dict[str, int]
    strategy: FilterStrategy


class ElementFilter:
    """元素过滤器"""
    
    def __init__(self, strategy: FilterStrategy = FilterStrategy.BALANCED):
        self.strategy = strategy
        self.filter_rules = self._initialize_filter_rules()
        self.package_whitelist = set()  # 包白名单
        self.package_blacklist = set()  # 包黑名单
        self.text_keywords = []  # 文本关键词
        
    def _initialize_filter_rules(self) -> List[FilterRule]:
        """初始化过滤规则"""
        rules = [
            # 关键功能元素
            FilterRule(
                "critical_buttons",
                lambda el: self._is_critical_element(el),
                ElementPriority.CRITICAL,
                "搜索、播放、登录等关键按钮"
            ),
            
            # 导航元素
            FilterRule(
                "navigation",
                lambda el: self._is_navigation_element(el),
                ElementPriority.HIGH,
                "导航菜单、标签页等"
            ),
            
            # 可点击有文本的元素
            FilterRule(
                "clickable_with_text",
                lambda el: el.get('clickable', False) and bool(el.get('text', '').strip()),
                ElementPriority.HIGH,
                "有文本内容的可点击元素"
            ),
            
            # 输入框
            FilterRule(
                "input_fields",
                lambda el: self._is_input_element(el),
                ElementPriority.HIGH,
                "文本输入框"
            ),
            
            # 有resource_id的可点击元素  
            FilterRule(
                "clickable_with_id",
                lambda el: el.get('clickable', False) and bool(el.get('resource_id', '')),
                ElementPriority.MEDIUM,
                "有资源ID的可点击元素"
            ),
            
            # 视觉识别的交互元素
            FilterRule(
                "visual_interactive",
                lambda el: el.get('element_type', '') == 'visual' and el.get('clickable', False),
                ElementPriority.MEDIUM,
                "视觉识别的可交互元素"
            ),
            
            # 广告和无关元素(需要过滤掉)
            FilterRule(
                "ads_and_irrelevant",
                lambda el: self._is_irrelevant_element(el),
                ElementPriority.IGNORE,
                "广告和无关元素"
            ),
            
            # 空白或无意义元素
            FilterRule(
                "empty_elements",
                lambda el: self._is_empty_element(el),
                ElementPriority.IGNORE,
                "空白或无意义元素"
            )
        ]
        
        return rules
    
    def _is_critical_element(self, element: Dict[str, Any]) -> bool:
        """判断是否为关键元素"""
        text = element.get('text', '').lower()
        resource_id = element.get('resource_id', '').lower()
        
        critical_keywords = [
            'search', 'play', 'login', 'register', 'sign',
            '搜索', '播放', '登录', '注册', '确定', '确认',
            'ok', 'confirm', 'submit', '提交', 'next', '下一步'
        ]
        
        return any(keyword in text or keyword in resource_id for keyword in critical_keywords)
    
    def _is_navigation_element(self, element: Dict[str, Any]) -> bool:
        """判断是否为导航元素"""
        text = element.get('text', '').lower()
        resource_id = element.get('resource_id', '').lower()
        class_name = element.get('class_name', '').lower()
        
        nav_keywords = [
            'tab', 'menu', 'nav', 'home', 'back',
            '首页', '菜单', '导航', '返回', '设置'
        ]
        
        nav_classes = [
            'tablayout', 'navigationview', 'actionbar', 'toolbar'
        ]
        
        return (any(keyword in text or keyword in resource_id for keyword in nav_keywords) or
                any(nav_class in class_name for nav_class in nav_classes))
    
    def _is_input_element(self, element: Dict[str, Any]) -> bool:
        """判断是否为输入元素"""
        class_name = element.get('class_name', '').lower()
        resource_id = element.get('resource_id', '').lower()
        
        input_classes = [
            'edittext', 'textview', 'autocompletetextview'
        ]
        
        input_ids = [
            'edit', 'input', 'search', 'text'
        ]
        
        return (any(input_class in class_name for input_class in input_classes) or
                any(input_id in resource_id for input_id in input_ids))
    
    def _is_irrelevant_element(self, element: Dict[str, Any]) -> bool:
        """判断是否为无关元素"""
        text = element.get('text', '').lower()
        resource_id = element.get('resource_id', '').lower()
        
        irrelevant_keywords = [
            'ad', 'ads', 'advertisement', 'banner',
            '广告', '推广', 'sponsor', '赞助'
        ]
        
        return any(keyword in text or keyword in resource_id for keyword in irrelevant_keywords)
    
    def _is_empty_element(self, element: Dict[str, Any]) -> bool:
        """判断是否为空元素"""
        text = element.get('text', '').strip()
        resource_id = element.get('resource_id', '').strip()
        name = element.get('name', '').strip()
        
        # 没有任何有意义内容的元素
        return not (text or resource_id or name)
    
    def set_package_filter(self, whitelist: List[str] = None, blacklist: List[str] = None):
        """设置包过滤器"""
        if whitelist:
            self.package_whitelist = set(whitelist)
        if blacklist:
            self.package_blacklist = set(blacklist)
        
        logger.info(f"设置包过滤器 - 白名单: {len(self.package_whitelist)}, 黑名单: {len(self.package_blacklist)}")
    
    def set_text_keywords(self, keywords: List[str]):
        """设置文本关键词过滤"""
        self.text_keywords = [kw.lower() for kw in keywords]
        logger.info(f"设置文本关键词: {self.text_keywords}")
    
    def _apply_package_filter(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """应用包过滤"""
        if not self.package_whitelist and not self.package_blacklist:
            return elements
        
        filtered = []
        for element in elements:
            package = element.get('package', '')
            
            # 白名单过滤
            if self.package_whitelist:
                if not any(wp in package for wp in self.package_whitelist):
                    continue
            
            # 黑名单过滤
            if self.package_blacklist:
                if any(bp in package for bp in self.package_blacklist):
                    continue
            
            filtered.append(element)
        
        return filtered
    
    def _apply_text_keyword_filter(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """应用文本关键词过滤"""
        if not self.text_keywords:
            return elements
        
        filtered = []
        for element in elements:
            text = element.get('text', '').lower()
            resource_id = element.get('resource_id', '').lower()
            name = element.get('name', '').lower()
            
            # 如果包含关键词则保留
            if any(kw in text or kw in resource_id or kw in name for kw in self.text_keywords):
                filtered.append(element)
        
        return filtered
    
    def _calculate_element_priority(self, element: Dict[str, Any]) -> ElementPriority:
        """计算元素优先级"""
        max_priority = ElementPriority.IGNORE
        
        for rule in self.filter_rules:
            if rule.condition(element):
                if rule.priority.value > max_priority.value:
                    max_priority = rule.priority
        
        return max_priority
    
    def _filter_by_strategy(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """根据策略过滤元素"""
        # 为每个元素计算优先级
        elements_with_priority = []
        for element in elements:
            priority = self._calculate_element_priority(element)
            elements_with_priority.append((element, priority))
        
        # 根据策略选择阈值
        if self.strategy == FilterStrategy.STRICT:
            min_priority = ElementPriority.HIGH
            max_elements = 20
        elif self.strategy == FilterStrategy.BALANCED:
            min_priority = ElementPriority.MEDIUM  
            max_elements = 50
        else:  # PERMISSIVE
            min_priority = ElementPriority.LOW
            max_elements = 100
        
        # 过滤并排序
        filtered = [
            (elem, priority) for elem, priority in elements_with_priority
            if priority.value >= min_priority.value
        ]
        
        # 按优先级排序
        filtered.sort(key=lambda x: x[1].value, reverse=True)
        
        # 限制数量
        filtered = filtered[:max_elements]
        
        return [elem for elem, _ in filtered]
    
    def _simplify_element_for_llm(self, element: Dict[str, Any], index: int) -> Dict[str, Any]:
        """为LLM简化元素信息"""
        simplified = {
            "index": index,
            "uuid": element.get('uuid', ''),
            "type": element.get('element_type', 'xml'),
            "clickable": element.get('clickable', False),
        }
        
        # 保留有意义的文本
        text = element.get('text', '').strip()
        if text and len(text) <= 50:  # 限制文本长度
            simplified["text"] = text
        elif text:
            simplified["text"] = text[:47] + "..."
        
        # 保留resource_id的关键部分
        resource_id = element.get('resource_id', '')
        if resource_id:
            # 提取ID的最后一部分
            id_parts = resource_id.split(':')
            if len(id_parts) > 1:
                simplified["id"] = id_parts[-1].split('/')[-1]
            else:
                simplified["id"] = resource_id
        
        # 保留类名的简化版本
        class_name = element.get('class_name', '')
        if class_name:
            simplified["class"] = class_name.split('.')[-1]
        
        # 保留坐标信息(归一化)
        simplified["center"] = {
            "x": round(element.get('center_x', 0), 3),
            "y": round(element.get('center_y', 0), 3)
        }
        
        # 保留置信度
        if element.get('confidence'):
            simplified["confidence"] = round(element.get('confidence', 1.0), 2)
        
        return simplified
    
    def filter_elements(self, elements_data: Dict[str, Any]) -> FilterResult:
        """主过滤方法"""
        original_elements = elements_data.get('elements', [])
        original_count = len(original_elements)
        
        logger.info(f"开始过滤 {original_count} 个元素，策略: {self.strategy.value}")
        
        # 应用各种过滤器
        filtered = original_elements
        filter_stats = {"original": original_count}
        
        # 1. 包过滤
        if self.package_whitelist or self.package_blacklist:
            filtered = self._apply_package_filter(filtered)
            filter_stats["after_package"] = len(filtered)
            logger.info(f"包过滤后剩余: {len(filtered)} 个元素")
        
        # 2. 文本关键词过滤
        if self.text_keywords:
            filtered = self._apply_text_keyword_filter(filtered)
            filter_stats["after_keywords"] = len(filtered)
            logger.info(f"关键词过滤后剩余: {len(filtered)} 个元素")
        
        # 3. 策略过滤
        filtered = self._filter_by_strategy(filtered)
        filter_stats["after_strategy"] = len(filtered)
        logger.info(f"策略过滤后剩余: {len(filtered)} 个元素")
        
        # 4. 为LLM简化元素信息
        simplified_elements = []
        for i, element in enumerate(filtered, 1):
            simplified = self._simplify_element_for_llm(element, i)
            simplified_elements.append(simplified)
        
        filter_stats["final"] = len(simplified_elements)
        
        result = FilterResult(
            filtered_elements=simplified_elements,
            original_count=original_count,
            filtered_count=len(simplified_elements),
            filter_stats=filter_stats,
            strategy=self.strategy
        )
        
        logger.info(f"过滤完成: {original_count} -> {len(simplified_elements)} 个元素")
        return result
    
    def export_for_llm(self, filter_result: FilterResult, format_type: str = "detailed") -> str:
        """导出适合LLM理解的格式"""
        elements = filter_result.filtered_elements
        
        if format_type == "minimal":
            return self._export_minimal_format(elements)
        elif format_type == "structured":
            return self._export_structured_format(elements)
        else:
            return self._export_detailed_format(elements, filter_result)
    
    def _export_minimal_format(self, elements: List[Dict[str, Any]]) -> str:
        """最简格式 - 适合token限制严格的场景"""
        lines = ["可操作元素列表:"]
        
        for elem in elements:
            if elem.get('clickable', False):
                text = elem.get('text', '')
                elem_id = elem.get('id', '')
                uuid = elem.get('uuid', '')
                
                desc = f"{elem['index']}. "
                if text:
                    desc += f'"{text}"'
                elif elem_id:
                    desc += f'#{elem_id}'
                else:
                    desc += f'[{elem.get("class", "element")}]'
                
                desc += f' (uuid:{uuid[:8]})'
                lines.append(desc)
        
        return '\n'.join(lines)
    
    def _export_structured_format(self, elements: List[Dict[str, Any]]) -> str:
        """结构化格式 - JSON格式"""
        return json.dumps({
            "elements": elements,
            "count": len(elements),
            "timestamp": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)
    
    def _export_detailed_format(self, elements: List[Dict[str, Any]], filter_result: FilterResult) -> str:
        """详细格式 - 适合详细分析"""
        lines = [
            f"=== 屏幕元素分析 (策略: {filter_result.strategy.value}) ===",
            f"原始元素: {filter_result.original_count} 个",
            f"过滤后: {filter_result.filtered_count} 个",
            f"过滤率: {(1 - filter_result.filtered_count/max(filter_result.original_count, 1))*100:.1f}%",
            "",
            "可操作元素详情:"
        ]
        
        clickable_count = 0
        for elem in elements:
            lines.append(f"\n{elem['index']}. 元素信息:")
            
            if elem.get('text'):
                lines.append(f"   文本: \"{elem['text']}\"")
            
            if elem.get('id'):
                lines.append(f"   ID: {elem['id']}")
            
            if elem.get('class'):
                lines.append(f"   类型: {elem['class']}")
            
            lines.append(f"   坐标: ({elem['center']['x']}, {elem['center']['y']})")
            lines.append(f"   可点击: {'是' if elem.get('clickable') else '否'}")
            lines.append(f"   UUID: {elem.get('uuid', 'N/A')}")
            
            if elem.get('clickable'):
                clickable_count += 1
        
        lines.extend([
            f"\n=== 统计信息 ===",
            f"可点击元素: {clickable_count} 个",
            f"不可点击元素: {len(elements) - clickable_count} 个"
        ])
        
        return '\n'.join(lines)


class ConfigurableFilter:
    """可配置过滤器 - 支持配置文件"""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path(__file__).parent / "filter_config.json"
        self.config = self._load_config()
        self.filter = ElementFilter(FilterStrategy(self.config.get('strategy', 'balanced')))
        self._apply_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"加载配置文件: {self.config_file}")
                return config
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}, 使用默认配置")
        
        # 默认配置
        return {
            "strategy": "balanced",
            "package_whitelist": [],
            "package_blacklist": ["com.google.android.gms", "com.android.systemui"],
            "text_keywords": [],
            "max_elements": 50,
            "export_format": "detailed"
        }
    
    def _apply_config(self):
        """应用配置"""
        config = self.config
        
        # 设置包过滤
        self.filter.set_package_filter(
            config.get('package_whitelist', []),
            config.get('package_blacklist', [])
        )
        
        # 设置关键词
        self.filter.set_text_keywords(config.get('text_keywords', []))
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def update_config(self, **kwargs):
        """更新配置"""
        self.config.update(kwargs)
        self._apply_config()
    
    def filter_and_export(self, elements_data: Dict[str, Any], output_file: Optional[Path] = None) -> str:
        """过滤并导出"""
        result = self.filter.filter_elements(elements_data)
        
        export_format = self.config.get('export_format', 'detailed')
        exported_content = self.filter.export_for_llm(result, export_format)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(exported_content)
            logger.info(f"过滤结果已保存到: {output_file}")
        
        return exported_content


# CLI工具
def main():
    """CLI主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Only-Test 元素过滤器')
    parser.add_argument('input_file', help='输入的元素数据JSON文件')
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('-s', '--strategy', choices=['strict', 'balanced', 'permissive'], 
                       default='balanced', help='过滤策略')
    parser.add_argument('-f', '--format', choices=['minimal', 'structured', 'detailed'],
                       default='detailed', help='输出格式')
    parser.add_argument('--package-filter', nargs='*', help='包名过滤(白名单)')
    parser.add_argument('--keywords', nargs='*', help='文本关键词过滤')
    parser.add_argument('--config', help='配置文件路径')
    
    args = parser.parse_args()
    
    try:
        # 加载输入数据
        with open(args.input_file, 'r', encoding='utf-8') as f:
            elements_data = json.load(f)
        
        # 创建过滤器
        if args.config:
            filter_tool = ConfigurableFilter(Path(args.config))
        else:
            filter_tool = ConfigurableFilter()
        
        # 更新配置
        config_updates = {}
        if args.strategy:
            config_updates['strategy'] = args.strategy
        if args.format:
            config_updates['export_format'] = args.format
        if args.package_filter:
            config_updates['package_whitelist'] = args.package_filter
        if args.keywords:
            config_updates['text_keywords'] = args.keywords
        
        if config_updates:
            filter_tool.update_config(**config_updates)
        
        # 过滤和导出
        output_file = Path(args.output) if args.output else None
        result = filter_tool.filter_and_export(elements_data, output_file)
        
        if not args.output:
            print(result)
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()