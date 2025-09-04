# coding=utf-8
"""
Poco 组件提取工具 - 正确版本

使用 Poco 的选择器方式来遍历所有节点，获取完整的组件信息
"""

import sys
import os
import json
import atexit

# 添加 Poco 模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../Poco'))

from poco.drivers.android.uiautomation import AndroidUiautomationPoco


class PocoComponentsCorrect:
    """Poco 组件提取器 - 正确版本"""
    
    def __init__(self, poco_instance=None):
        """初始化"""
        if poco_instance is None:
            self.poco = AndroidUiautomationPoco(use_airtest_input=True)
        else:
            self.poco = poco_instance
        
        # 存储组件数据
        self.visible_components = []
        self.all_components = []
        
        # 注册退出清理函数
        atexit.register(self._cleanup)
    
    def _cleanup(self):
        """清理资源"""
        try:
            if hasattr(self.poco, '_agent'):
                pass
        except:
            pass
    
    def extract_components(self):
        """提取组件数据 - 使用 Poco 选择器方式"""
        print("正在提取UI组件数据...")
        
        try:
            # 清空数据
            self.visible_components = []
            self.all_components = []
            
            # 方法1: 使用 Poco 的遍历方式
            self._extract_using_poco_selector()
            
            print(f"提取完成 - 总组件: {len(self.all_components)}, 可见组件: {len(self.visible_components)}")
            
        except Exception as e:
            print(f"提取失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _extract_using_poco_selector(self):
        """使用 Poco 选择器方式提取组件"""
        try:
            # 获取根节点
            root = self.poco()
            
            # 递归遍历所有节点
            self._traverse_node(root, [])
            
        except Exception as e:
            print(f"使用选择器提取失败: {e}")
            # 如果选择器方式失败，尝试直接使用 dump 方式
            self._extract_using_dump()
    
    def _traverse_node(self, node, path):
        """递归遍历节点"""
        try:
            # 获取节点的所有子节点
            children = node.children()
            
            # 遍历每个子节点
            for i, child in enumerate(children):
                current_path = path + [i]
                
                # 提取节点信息
                component_info = self._extract_node_info(child, current_path)
                if component_info:
                    self.all_components.append(component_info)
                    
                    # 如果是可见组件，添加到可见列表
                    if component_info['payload_details']['visible']:
                        self.visible_components.append(component_info)
                
                # 递归遍历子节点
                self._traverse_node(child, current_path)
                
        except Exception as e:
            print(f"遍历节点失败: {e}")
    
    def _extract_node_info(self, node, path):
        """提取单个节点的完整信息"""
        try:
            # 获取节点的所有属性
            attrs = {}
            
            # 标准属性列表
            standard_attrs = [
                'type', 'name', 'text', 'enabled', 'visible', 'resourceId',
                'zOrders', 'package', 'anchorPoint', 'dismissable', 'checkable',
                'scale', 'boundsInParent', 'focusable', 'touchable', 'longClickable',
                'size', 'pos', 'focused', 'checked', 'editable', 'selected',
                'scrollable', 'clickable', 'bounds'
            ]
            
            # 尝试获取每个属性
            for attr_name in standard_attrs:
                try:
                    attr_value = node.attr(attr_name)
                    attrs[attr_name] = attr_value
                except:
                    # 如果获取失败，设置默认值
                    if attr_name == 'visible':
                        attrs[attr_name] = True
                    elif attr_name == 'enabled':
                        attrs[attr_name] = True
                    elif attr_name in ['anchorPoint']:
                        attrs[attr_name] = [0.5, 0.5]
                    elif attr_name in ['scale']:
                        attrs[attr_name] = [1, 1]
                    elif attr_name in ['zOrders']:
                        attrs[attr_name] = {}
                    elif attr_name in ['pos', 'size', 'bounds', 'boundsInParent']:
                        attrs[attr_name] = []
                    elif attr_name in ['dismissable', 'checkable', 'focusable', 'touchable', 
                                     'longClickable', 'focused', 'checked', 'editable', 
                                     'selected', 'scrollable', 'clickable']:
                        attrs[attr_name] = False
                    else:
                        attrs[attr_name] = ''
            
            # 获取子节点数量
            try:
                children_count = len(node.children())
            except:
                children_count = 0
            
            # 创建组件信息
            component = {
                'path_from_root': path.copy(),
                'path_string': '/'.join(map(str, path)) if path else 'root',
                'payload_details': {
                    'type': attrs.get('type', ''),
                    'name': attrs.get('name', ''),
                    'text': attrs.get('text', ''),
                    'enabled': attrs.get('enabled', True),
                    'visible': attrs.get('visible', True),
                    'resourceId': attrs.get('resourceId', ''),
                    'zOrders': attrs.get('zOrders', {}),
                    'package': attrs.get('package', ''),
                    'anchorPoint': attrs.get('anchorPoint', [0.5, 0.5]),
                    'dismissable': attrs.get('dismissable', False),
                    'checkable': attrs.get('checkable', False),
                    'scale': attrs.get('scale', [1, 1]),
                    'boundsInParent': attrs.get('boundsInParent', []),
                    'focusable': attrs.get('focusable', False),
                    'touchable': attrs.get('touchable', False),
                    'longClickable': attrs.get('longClickable', False),
                    'size': attrs.get('size', []),
                    'pos': attrs.get('pos', []),
                    'focused': attrs.get('focused', False),
                    'checked': attrs.get('checked', False),
                    'editable': attrs.get('editable', False),
                    'selected': attrs.get('selected', False),
                    'scrollable': attrs.get('scrollable', False),
                    'clickable': attrs.get('clickable', False),
                    'bounds': attrs.get('bounds', []),
                    'children_count': children_count
                },
                # 'raw_attrs': attrs
            }
            
            return component
            
        except Exception as e:
            print(f"提取节点信息失败: {e}")
            return None
    
    def _extract_using_dump(self):
        """备用方法：使用原始 dump 方式"""
        try:
            print("尝试使用备用方法...")
            hierarchy_data = self.poco._agent.hierarchy.dump()
            self._extract_from_dump(hierarchy_data, [])
        except Exception as e:
            print(f"备用方法也失败: {e}")
    
    def _extract_from_dump(self, node, path):
        """从 dump 数据中提取"""
        if not isinstance(node, dict):
            return
        
        attrs = node.get('attrs', {})
        
        component = {
            'path_from_root': path.copy(),
            'path_string': '/'.join(map(str, path)) if path else 'root',
            'payload_details': {
                'type': attrs.get('type', ''),
                'name': attrs.get('name', ''),
                'text': attrs.get('text', ''),
                'enabled': attrs.get('enabled', True),
                'visible': attrs.get('visible', True),
                'resourceId': attrs.get('resourceId', ''),
                'zOrders': attrs.get('zOrders', {}),
                'package': attrs.get('package', ''),
                'anchorPoint': attrs.get('anchorPoint', [0.5, 0.5]),
                'dismissable': attrs.get('dismissable', False),
                'checkable': attrs.get('checkable', False),
                'scale': attrs.get('scale', [1, 1]),
                'boundsInParent': attrs.get('boundsInParent', []),
                'focusable': attrs.get('focusable', False),
                'touchable': attrs.get('touchable', False),
                'longClickable': attrs.get('longClickable', False),
                'size': attrs.get('size', []),
                'pos': attrs.get('pos', []),
                'focused': attrs.get('focused', False),
                'checked': attrs.get('checked', False),
                'editable': attrs.get('editable', False),
                'selected': attrs.get('selected', False),
                'scrollable': attrs.get('scrollable', False),
                'clickable': attrs.get('clickable', False),
                'bounds': attrs.get('bounds', []),
                'children_count': len(node.get('children', []))
            },
            'raw_attrs': attrs
        }
        
        self.all_components.append(component)
        if component['payload_details']['visible']:
            self.visible_components.append(component)
        
        # 递归处理子节点
        children = node.get('children', [])
        for i, child in enumerate(children):
            self._extract_from_dump(child, path + [i])
    
    def get_visible_components(self):
        """获取所有可见组件"""
        return self.visible_components
    
    def get_all_components(self):
        """获取所有组件"""
        return self.all_components
    
    def filter_by_resource_id(self, resource_id):
        """根据 resourceId 过滤"""
        results = []
        for comp in self.visible_components:
            comp_resource_id = comp['payload_details']['resourceId']
            
            # 支持字符串和字节串匹配
            if isinstance(resource_id, str):
                if (comp_resource_id == resource_id or 
                    (isinstance(comp_resource_id, bytes) and comp_resource_id.decode() == resource_id) or
                    (isinstance(comp_resource_id, str) and comp_resource_id == resource_id)):
                    results.append(comp)
            else:
                if comp_resource_id == resource_id:
                    results.append(comp)
        
        return results
    
    def print_component(self, component):
        """按照指定格式打印组件"""
        print(f"Path from root node: {component['path_from_root']}")
        print("Payload details:")
        
        details = component['payload_details']
        for key, value in details.items():
            if key != 'children_count':
                print(f"      {key} :  {value} ")
        print()
    
    def print_components(self, components=None, max_count=10):
        """打印组件列表"""
        if components is None:
            components = self.visible_components
        
        print(f"\n找到 {len(components)} 个组件:")
        print("=" * 80)
        
        for i, comp in enumerate(components[:max_count]):
            print(f"\n组件 {i+1}:")
            self.print_component(comp)
        
        if len(components) > max_count:
            print(f"... 还有 {len(components) - max_count} 个组件")
    
    def save_to_json(self, filename="poco_components_correct.json", visible_only=True):
        """保存组件数据到JSON文件"""
        try:
            data = self.visible_components if visible_only else self.all_components
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"组件数据已保存到: {filename}")
        except Exception as e:
            print(f"保存失败: {e}")


# 全局实例
_extractor = None

def get_extractor():
    """获取提取器实例"""
    global _extractor
    if _extractor is None:
        _extractor = PocoComponentsCorrect()
        _extractor.extract_components()
    return _extractor

def get_visible_components():
    """获取所有可见组件"""
    return get_extractor().get_visible_components()

def find_by_resource_id(resource_id):
    """根据 resourceId 查找组件"""
    return get_extractor().filter_by_resource_id(resource_id)


if __name__ == "__main__":
    print("Poco 组件提取器 - 正确版本")
    print("=" * 50)
    
    # 创建提取器
    extractor = PocoComponentsCorrect()
    
    # 提取组件
    extractor.extract_components()
    
    # 显示可见组件
    print("\n可见组件:")
    extractor.print_components(max_count=3)
    
    # 查找特定 resourceId
    target_resource_id = 'com.unitvnet.tvod:id/mStvReleaseNote'
    print(f"\n查找 resourceId: {target_resource_id}")
    filtered = extractor.filter_by_resource_id(target_resource_id)
    extractor.print_components(filtered, max_count=3)
    
    # 保存数据
    extractor.save_to_json(filename="poco_components_inspector.json")
    
    print("\n使用示例:")
    print("from poco_components_correct import get_visible_components, find_by_resource_id")
    print("components = get_visible_components()")
    print("target = find_by_resource_id('com.unitvnet.tvod:id/mStvReleaseNote')")