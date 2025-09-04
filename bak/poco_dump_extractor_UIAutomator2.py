# coding=utf-8
"""
Poco Dump 信息提取器 - 修复版本

兼容新的 UIAutomator2 驱动的版本
"""

import sys
import os
import json
from typing import Union, List, Optional, Dict

def get_poco_instance(use_airtest_input=False, use_existing_xml=False):
    """获取 Poco 实例，优先使用 UIAutomator2"""
    try:
        # 添加项目路径到 Python 路径
        sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

        if use_existing_xml and False:
            # 使用现有的XML文件进行测试
            print("使用现有的screen_dump.xml文件进行测试")
            return get_mock_poco_instance()
        else:

            from Poco.poco.drivers.android.uiautomation2 import AndroidUiautomator2Poco

            print(f"使用 AndroidUiautomator2Poco 驱动 (use_airtest_input={use_airtest_input})")
            return AndroidUiautomator2Poco(use_airtest_input=use_airtest_input)
            
    except ImportError as e:
        print(f"failed to import AndroidUiautomator2Poco: {e}")
        raise RuntimeError("AndroidUiautomator2Poco 不可用，请检查 uiautomator2 是否已安装：pip install uiautomator2")

def get_mock_poco_instance():
    """创建一个使用现有XML文件的模拟Poco实例"""
    import xml.etree.ElementTree as ET
    
    class MockDevice:
        def __init__(self):
            self.info = {'displayWidth': 1440, 'displayHeight': 2560}
        
        def dump_hierarchy(self):
            xml_file = os.path.join(os.path.dirname(__file__), 'screen_dump.xml')
            with open(xml_file, 'r', encoding='utf-8') as f:
                return f.read()
    
    class MockPoco:
        def __init__(self):
            self.device = MockDevice()
            self._agent = MockAgent(self.device)
    
    class MockAgent:
        def __init__(self, device):
            self.device = device
            self.hierarchy = MockHierarchy(device)
    
    class MockHierarchy:
        def __init__(self, device):
            self.device = device
            self._dumper = MockDumper(device)
        
        def dump(self):
            return self._dumper.dumpHierarchy()
    
    class MockDumper:
        def __init__(self, device):
            self.device = device
            self._root_node = None
        
        def getRoot(self):
            if self._root_node is None:
                xml_content = self.device.dump_hierarchy()
                root_element = ET.fromstring(xml_content)
                self._root_node = self._create_mock_node(root_element, (1440, 2560))
            return self._root_node
        
        def _create_mock_node(self, xml_element, screen_size):
            """创建模拟节点"""
            return create_uiautomator2_node_mock_local(xml_element, screen_size)
        
        def dumpHierarchy(self, onlyVisibleNode=True):
            return self.dumpHierarchyImpl(self.getRoot(), onlyVisibleNode)
        
        def dumpHierarchyImpl(self, node, onlyVisibleNode=True):
            if not node:
                return None

            payload = {}
            
            # filter out all None values
            for attrName, attrVal in node.enumerateAttrs():
                if attrVal is not None:
                    payload[attrName] = attrVal

            result = {}
            children = []
            for child in node.getChildren():
                if not onlyVisibleNode or child.getAttr('visible'):
                    children.append(self.dumpHierarchyImpl(child, onlyVisibleNode))
            if len(children) > 0:
                result['children'] = children

            result['name'] = payload.get('name') or node.getAttr('name')
            result['payload'] = payload

            return result
    
    return MockPoco()

def create_uiautomator2_node_mock_local(xml_element, screen_size=(1440, 2560)):
    """创建一个UIAutomator2Node的本地模拟版本"""
    class UIAutomator2NodeMockLocal:
        def __init__(self, xml_element, screen_size):
            self.xml_element = xml_element
            self.screen_width, self.screen_height = screen_size
            self._parent = None
            self._children = None
        
        def getParent(self):
            return self._parent
        
        def setParent(self, parent):
            self._parent = parent
        
        def getChildren(self):
            if self._children is None:
                self._children = []
                for child_elem in self.xml_element:
                    child_node = UIAutomator2NodeMockLocal(child_elem, (self.screen_width, self.screen_height))
                    child_node.setParent(self)
                    self._children.append(child_node)
            return self._children
        
        def getAttr(self, attrName):
            """Get attribute value, compatible with original format"""
            attrib = self.xml_element.attrib
            
            # Handle hierarchy root element case
            if self.xml_element.tag == 'hierarchy':
                if attrName == 'name':
                    return '<Unknown>'
                elif attrName == 'type':
                    return 'Unknown'
                elif attrName == 'visible':
                    return True
                elif attrName == 'enabled':
                    return False
                elif attrName == 'pos':
                    return [0.0, 0.0]
                elif attrName == 'size':
                    return [0.0, 0.0]
                elif attrName == 'bounds':
                    return []
                elif attrName in ['text', 'resourceId', 'package']:
                    return ''
                elif attrName in ['clickable', 'touchable', 'focusable', 'focused', 'scrollable', 
                                 'selected', 'checkable', 'checked', 'longClickable', 'editable', 'dismissable']:
                    return False
                elif attrName == 'scale':
                    return [1.0, 1.0]
                elif attrName == 'anchorPoint':
                    return [0.5, 0.5]
                elif attrName == 'zOrders':
                    return {'local': 0, 'global': 0}
                elif attrName == 'boundsInParent':
                    return []
            
            if attrName == 'name':
                text = attrib.get('text', '').strip()
                if text:
                    return text
                return attrib.get('class', '<Unknown>')
            elif attrName == 'type':
                return attrib.get('class', 'Unknown')
            elif attrName == 'visible':
                visible_to_user = attrib.get('visible-to-user', 'true')
                return visible_to_user.lower() == 'true'
            elif attrName == 'enabled':
                enabled = attrib.get('enabled', 'true')
                return enabled.lower() == 'true'
            elif attrName == 'pos':
                return self._get_normalized_pos()
            elif attrName == 'size':
                return self._get_normalized_size()
            elif attrName == 'bounds':
                return self._get_bounds_array()
            elif attrName == 'text':
                return attrib.get('text', '')
            elif attrName == 'resourceId':
                return attrib.get('resource-id', '')
            elif attrName == 'package':
                return attrib.get('package', '')
            elif attrName == 'clickable':
                clickable = attrib.get('clickable', 'false')
                return clickable.lower() == 'true'
            elif attrName == 'touchable':
                clickable = attrib.get('clickable', 'false')
                return clickable.lower() == 'true'
            elif attrName == 'focusable':
                focusable = attrib.get('focusable', 'false')
                return focusable.lower() == 'true'
            elif attrName == 'focused':
                focused = attrib.get('focused', 'false')
                return focused.lower() == 'true'
            elif attrName == 'scrollable':
                scrollable = attrib.get('scrollable', 'false')
                return scrollable.lower() == 'true'
            elif attrName == 'selected':
                selected = attrib.get('selected', 'false')
                return selected.lower() == 'true'
            elif attrName == 'checkable':
                checkable = attrib.get('checkable', 'false')
                return checkable.lower() == 'true'
            elif attrName == 'checked':
                checked = attrib.get('checked', 'false')
                return checked.lower() == 'true'
            elif attrName == 'longClickable':
                long_clickable = attrib.get('long-clickable', 'false')
                return long_clickable.lower() == 'true'
            elif attrName == 'editable':
                class_name = attrib.get('class', '')
                return 'EditText' in class_name
            elif attrName == 'dismissable':
                return False
            elif attrName == 'scale':
                return [1.0, 1.0]
            elif attrName == 'anchorPoint':
                return [0.5, 0.5]
            elif attrName == 'zOrders':
                drawing_order = attrib.get('drawing-order', '0')
                try:
                    order = int(drawing_order)
                except (ValueError, TypeError):
                    order = 0
                return {'local': order, 'global': order}
            elif attrName == 'boundsInParent':
                return self._get_normalized_size()
            else:
                return None
        
        def _parse_bounds(self):
            if self.xml_element.tag == 'hierarchy':
                return 0, 0, 0, 0
            bounds_str = self.xml_element.attrib.get('bounds', '[0,0][0,0]')
            try:
                bounds_str = bounds_str.replace('[', '').replace(']', ',')
                coords = [int(x) for x in bounds_str.split(',') if x]
                if len(coords) >= 4:
                    return coords[0], coords[1], coords[2], coords[3]
            except (ValueError, IndexError):
                pass
            return 0, 0, 0, 0
        
        def _get_normalized_pos(self):
            if self.xml_element.tag == 'hierarchy':
                return [0.0, 0.0]
            x1, y1, x2, y2 = self._parse_bounds()
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            return [center_x / self.screen_width, center_y / self.screen_height]
        
        def _get_normalized_size(self):
            if self.xml_element.tag == 'hierarchy':
                return [0.0, 0.0]
            x1, y1, x2, y2 = self._parse_bounds()
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            return [width / self.screen_width, height / self.screen_height]
        
        def _get_bounds_array(self):
            if self.xml_element.tag == 'hierarchy':
                return []
            x1, y1, x2, y2 = self._parse_bounds()
            return [
                x1 / self.screen_width,
                y1 / self.screen_height,
                x2 / self.screen_width,
                y2 / self.screen_height
            ]
        
        def enumerateAttrs(self):
            """Enumerate all attributes for AbstractDumper"""
            attrs = [
                ('type', self.getAttr('type')),
                ('name', self.getAttr('name')),
                ('text', self.getAttr('text')),
                ('enabled', self.getAttr('enabled')),
                ('visible', self.getAttr('visible')),
                ('resourceId', self.getAttr('resourceId')),
                ('zOrders', self.getAttr('zOrders')),
                ('package', self.getAttr('package')),
                ('anchorPoint', self.getAttr('anchorPoint')),
                ('dismissable', self.getAttr('dismissable')),
                ('checkable', self.getAttr('checkable')),
                ('scale', self.getAttr('scale')),
                ('boundsInParent', self.getAttr('boundsInParent')),
                ('focusable', self.getAttr('focusable')),
                ('touchable', self.getAttr('touchable')),
                ('longClickable', self.getAttr('longClickable')),
                ('size', self.getAttr('size')),
                ('pos', self.getAttr('pos')),
                ('focused', self.getAttr('focused')),
                ('checked', self.getAttr('checked')),
                ('editable', self.getAttr('editable')),
                ('selected', self.getAttr('selected')),
                ('scrollable', self.getAttr('scrollable')),
                ('clickable', self.getAttr('clickable')),
                ('bounds', self.getAttr('bounds')),
            ]
            return attrs
    
    return UIAutomator2NodeMockLocal(xml_element, screen_size)


class PocoDumpExtractor:
    """Poco Dump 信息提取器 - 兼容多种驱动"""
    
    def __init__(self, poco_instance=None, use_airtest_input=True, use_existing_xml=False):
        """初始化"""
        if poco_instance is None:
            self.poco = get_poco_instance(use_airtest_input=use_airtest_input, use_existing_xml=use_existing_xml)
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
            
            print(f"Dump数据类型: {type(self.dump_data)}")
            
            if self.dump_data is None:
                print("获取的dump数据为空")
                return []
            
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
            print(f"警告: 节点不是字典类型: {type(node)}")
            return
        
        # 检查节点结构
        if 'payload' not in node:
            print(f"警告: 节点缺少payload字段: {list(node.keys())}")
            # 如果是新格式，尝试适配
            if 'name' in node and 'children' in node:
                # 可能是新的格式，尝试处理
                pass
            else:
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
                'anchorPoint': payload.get('anchorPoint', [0.5, 0.5]),
                'dismissable': payload.get('dismissable', False),
                'checkable': payload.get('checkable', False),
                'scale': payload.get('scale', [1.0, 1.0]),
                'boundsInParent': payload.get('boundsInParent', []),
                'focusable': payload.get('focusable', False),
                'touchable': payload.get('touchable', False),
                'longClickable': payload.get('longClickable', False),
                'size': payload.get('size', []),
                'pos': payload.get('pos', []),
                'focused': payload.get('focused', False),
                'checked': payload.get('checked', False),
                'editable': payload.get('editable', payload.get('editalbe', False)),  # 兼容拼写错误
                'selected': payload.get('selected', False),
                'scrollable': payload.get('scrollable', False),
                'clickable': payload.get('clickable', False),
                'bounds': payload.get('bounds', []),
                'children_count': children_count
            }
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
                'extraction_method': 'dump_extractor_fixed',
                'widgets': self.all_nodes_info
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"所有widget信息已保存到: {filename}")
            return True
            
        except Exception as e:
            print(f"保存文件失败: {e}")
            return False
    
    def save_raw_dump(self, filename: str = "raw_dump_data.json") -> bool:
        """保存原始dump数据到JSON文件"""
        if self.dump_data is None:
            print("没有dump数据，请先调用 extract_all_widgets_info()")
            return False
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.dump_data, f, indent=2, ensure_ascii=False)
            
            print(f"原始dump数据已保存到: {filename}")
            return True
            
        except Exception as e:
            print(f"保存原始数据失败: {e}")
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
    print("Poco Dump 信息提取器 - 修复版本")
    print("=" * 50)
    
    try:
        # 先尝试使用现有XML文件进行测试
        print("使用现有screen_dump.xml文件进行测试...")
        extractor = PocoDumpExtractor(use_existing_xml=True)
        
        # 提取所有widget信息
        all_widgets = extractor.extract_all_widgets_info()
        
        if not all_widgets:
            print("未能提取到widget信息")
            # 尝试保存原始dump数据以便调试
            print("尝试保存原始dump数据...")
            extractor.save_raw_dump("debug_raw_dump.json")
            return
        
        # 保存到JSON文件
        extractor.save_all_to_json("all_widgets_complete_info_fixed.json")
        
        # 保存原始dump数据
        extractor.save_raw_dump("raw_dump_data_fixed.json")
        
        # 显示摘要
        extractor.print_summary()
        
        # 统计包名
        package_count = {}
        for widget in all_widgets:
            package = widget['payload_details']['package']
            if package:
                package_count[package] = package_count.get(package, 0) + 1
        
        print(f"\n包名统计:")
        for package, count in sorted(package_count.items()):
            print(f"  {package}: {count}")
        
        # 检查是否包含目标包
        if any('unitvnet' in pkg for pkg in package_count.keys()):
            print(f"\n✅ 成功检测到 com.unitvnet.mobs 应用的UI元素!")
        else:
            print(f"\n❌ 未检测到 com.unitvnet.mobs 应用的UI元素")
        
        print("\n脚本执行完成!")
        
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()


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