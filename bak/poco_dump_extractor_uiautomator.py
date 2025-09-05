# coding=utf-8
"""
Poco Dump 信息提取器

基于dump方法快速获取所有UI元素的完整详细信息
"""

import sys
import os
import json
from typing import Union, List, Optional, Dict

# 添加 Poco 模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

# from poco.drivers.android.uiautomation import AndroidUiautomationPoco
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

class PocoDumpExtractor:
    """Poco Dump 信息提取器 - 基于dump数据提取所有节点完整信息"""
    
    def __init__(self, poco_instance=None):
        """初始化"""
        if poco_instance is None:
            self.poco = AndroidUiautomationPoco(use_airtest_input=True)
        else:
            self.poco = poco_instance
        
        self.dump_data = None
        self.all_nodes_info = []
    
    def extract_all_widgets_info(self) -> List[Dict]:
        """提取所有widget的完整信息"""
        print("正在获取UI层次结构...")
        
        try:
            # 获取dump数据
            self.dump_data = self.poco._agent.hierarchy.dump()
            self.all_nodes_info = []
            
            # 递归提取所有节点信息
            self._extract_node_info(self.dump_data, [])
            
            print(f"成功提取 {len(self.all_nodes_info)} 个节点的完整信息")
            return self.all_nodes_info
            
        except Exception as e:
            print(f"提取失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_node_info(self, node, path):
        """递归提取节点信息"""
        if not isinstance(node, dict):
            return
        
        # 提取节点的payload信息
        payload = node.get('payload', {})
        node_name = node.get('name', '')
        
        # 统计子节点数量
        children = node.get('children', [])
        children_count = len(children)
        
        # 构建路径字符串
        path_string = '/'.join(map(str, path)) if path else 'root'
        
        # 构建完整节点信息
        node_info = {
            # 'path_from_root': path.copy(),
            'path_string': path_string,
            'payload_details': {
                'type': payload.get('type', ''),
                'name': payload.get('name', node_name),
                'text': payload.get('text', ''),
                'enabled': payload.get('enabled', False),
                'visible': payload.get('visible', False),
                'resourceId': payload.get('resourceId', ''),
                'zOrders': payload.get('zOrders', {}),
                'package': payload.get('package', ''),
                'anchorPoint': payload.get('anchorPoint', [0.55555, 0.55555]),
                'dismissable': payload.get('dismissable', False),
                'checkable': payload.get('checkable', False),
                'scale': payload.get('scale', []),
                'boundsInParent': payload.get('boundsInParent', []),
                'focusable': payload.get('focusable', False),
                'touchable': payload.get('touchable', False),
                'longClickable': payload.get('longClickable', False),
                'size': payload.get('size', []),
                'pos': payload.get('pos', []),
                'focused': payload.get('focused', False),
                'checked': payload.get('checked', False),
                'editable': payload.get('editable', payload.get('editalbe', False)),
                'selected': payload.get('selected', False),
                'scrollable': payload.get('scrollable', False),
                'clickable': payload.get('clickable', False),
                'bounds': payload.get('bounds', []),
                'children_count': children_count
            }
            # 'extraction_method': 'dump_extractor',
            # 'timestamp': self._get_timestamp()
        }
        
        # 添加到结果列表
        self.all_nodes_info.append(node_info)
        
        # 调试信息
        node_type = payload.get('type', 'N/A')
        resource_id = payload.get('resourceId', 'N/A')
        text = payload.get('text', 'N/A')[:20] if payload.get('text') else 'N/A'
        print(f"提取节点: {path_string} | type={node_type} | resourceId={resource_id} | text={text} | 子节点数={children_count}")
        
        # 递归处理子节点
        for i, child in enumerate(children):
            self._extract_node_info(child, path + [i])
    
    def get_widget_by_path(self, target_path: Union[str, List[int]]) -> Optional[Dict]:
        """根据路径获取特定widget信息"""
        if not self.all_nodes_info:
            self.extract_all_widgets_info()
        
        # 标准化路径
        if isinstance(target_path, str):
            path_string = target_path if target_path else 'root'
        else:
            path_string = '/'.join(map(str, target_path)) if target_path else 'root'
        
        # 查找匹配的节点
        for node_info in self.all_nodes_info:
            if node_info['path_string'] == path_string:
                return node_info
        
        return None
    
    def save_all_to_json(self, filename: str = "all_widgets_info.json") -> bool:
        """保存所有widget信息到JSON文件"""
        if not self.all_nodes_info:
            self.extract_all_widgets_info()
        
        try:
            output_data = {
                'total_count': len(self.all_nodes_info),
                'extraction_timestamp': self._get_timestamp(),
                'extraction_method': 'dump_extractor',
                'widgets': self.all_nodes_info
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"所有widget信息已保存到: {filename}")
            return True
            
        except Exception as e:
            print(f"保存文件失败: {e}")
            return False
    
    def filter_widgets(self, **filters) -> List[Dict]:
        """根据条件过滤widget"""
        if not self.all_nodes_info:
            self.extract_all_widgets_info()
        
        results = []
        for widget in self.all_nodes_info:
            match = True
            details = widget['payload_details']
            
            for key, value in filters.items():
                if key in details:
                    if details[key] != value:
                        match = False
                        break
            
            if match:
                results.append(widget)
        
        return results
    
    def find_widgets_by_type(self, widget_type: str) -> List[Dict]:
        """根据类型查找widget"""
        return self.filter_widgets(type=widget_type)
    
    def find_widgets_by_resource_id(self, resource_id: str) -> List[Dict]:
        """根据resourceId查找widget"""
        return self.filter_widgets(resourceId=resource_id)
    
    def find_widgets_with_text(self, text_contains: str = None) -> List[Dict]:
        """查找包含文本的widget"""
        if not self.all_nodes_info:
            self.extract_all_widgets_info()
        
        results = []
        for widget in self.all_nodes_info:
            widget_text = widget['payload_details'].get('text', '')
            if widget_text:  # 有文本内容
                if text_contains is None or text_contains in widget_text:
                    results.append(widget)
        
        return results
    
    def print_summary(self):
        """打印摘要信息"""
        if not self.all_nodes_info:
            return
        
        print(f"\n=== Widget摘要信息 ===")
        print(f"总节点数: {len(self.all_nodes_info)}")
        
        # 统计类型
        type_count = {}
        text_widgets = 0
        clickable_widgets = 0
        
        for widget in self.all_nodes_info:
            details = widget['payload_details']
            widget_type = details.get('type', 'N/A')
            type_count[widget_type] = type_count.get(widget_type, 0) + 1
            
            if details.get('text'):
                text_widgets += 1
            if details.get('clickable'):
                clickable_widgets += 1
        
        print(f"包含文本的widget: {text_widgets}")
        print(f"可点击的widget: {clickable_widgets}")
        print(f"\n类型统计:")
        for widget_type, count in sorted(type_count.items()):
            print(f"  {widget_type}: {count}")
    
    def _get_timestamp(self):
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """主函数"""
    print("Poco Dump 信息提取器")
    print("=" * 50)
    
    # 创建提取器
    extractor = PocoDumpExtractor()
    
    # 提取所有widget信息
    all_widgets = extractor.extract_all_widgets_info()
    
    if not all_widgets:
        print("未能提取到widget信息，退出")
        return
    
    # 保存到JSON文件
    extractor.save_all_to_json("./all_widgets_complete_info.json")
    
    # 显示摘要
    extractor.print_summary()
    
    # 显示前5个节点预览
    # print(f"\n前5个节点预览:")
    # for i, widget in enumerate(all_widgets[:5]):
    #     details = widget['payload_details']
    #     text_preview = details.get('text', 'N/A')
    #     if len(text_preview) > 50:
    #         text_preview = text_preview[:50] + "..."
        
    #     print(f"{i+1}. Path: {widget['path_string']}")
    #     print(f"   Type: {details.get('type', 'N/A')}")
    #     print(f"   ResourceId: {details.get('resourceId', 'N/A')}")
    #     print(f"   Text: {text_preview}")
    #     print()
    
    print("脚本执行完成!")


# 提供简单的函数接口
def extract_all_widgets(output_file: str = "all_widgets_info.json", 
                       poco_instance=None) -> List[Dict]:
    """
    快速提取所有widget信息的简单接口
    
    Args:
        output_file: 输出JSON文件名
        poco_instance: Poco实例，如果不提供则自动创建
    
    Returns:
        所有widget信息的列表
    """
    extractor = PocoDumpExtractor(poco_instance)
    widgets = extractor.extract_all_widgets_info()
    
    if widgets and output_file:
        extractor.save_all_to_json(output_file)
    
    return widgets


if __name__ == "__main__":
    main()