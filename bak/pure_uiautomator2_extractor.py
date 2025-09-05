#!/usr/bin/env python3
"""
Pure UIAutomator2 Widget Extractor
直接基于UIAutomator2的XML数据提取widget信息，绕过Poco的dump逻辑
完全兼容UIAutomator2，确保package信息不丢失
"""

import sys
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

class PureUIAutomator2Extractor:
    """纯UIAutomator2提取器，直接处理XML数据"""
    
    def __init__(self, device_id=None):
        """初始化提取器
        
        Args:
            device_id: 设备ID，None为默认设备
        """
        self.device_id = device_id
        self.device = None
        self.xml_content = None
        self.widgets = []
        self.screen_size = (1440, 2560)  # 默认屏幕尺寸
        
    def connect_device(self):
        """连接设备"""
        try:
            import uiautomator2 as u2
            
            if self.device_id:
                self.device = u2.connect(self.device_id)
                print(f"已连接到设备: {self.device_id}")
            else:
                self.device = u2.connect()
                print("已连接到默认设备")
            
            # 获取屏幕尺寸
            info = self.device.info
            self.screen_size = (info.get('displayWidth', 1440), info.get('displayHeight', 2560))
            print(f"屏幕尺寸: {self.screen_size[0]}x{self.screen_size[1]}")
            
            return True
            
        except Exception as e:
            print(f"连接设备失败: {e}")
            return False
    
    def get_xml_from_device(self):
        """从设备获取XML"""
        if not self.device:
            if not self.connect_device():
                return False
        
        try:
            print("正在获取设备UI层次结构XML...")
            self.xml_content = self.device.dump_hierarchy()
            
            if not self.xml_content:
                print("❌ 获取XML失败")
                return False
            
            print(f"✅ 获取XML成功，长度: {len(self.xml_content)} 字符")
            return True
            
        except Exception as e:
            print(f"获取XML失败: {e}")
            return False
    
    def get_xml_from_file(self, xml_file_path):
        """从文件读取XML"""
        try:
            with open(xml_file_path, 'r', encoding='utf-8') as f:
                self.xml_content = f.read()
            
            print(f"✅ 从文件读取XML成功: {xml_file_path}")
            return True
            
        except Exception as e:
            print(f"从文件读取XML失败: {e}")
            return False
    
    def parse_bounds(self, bounds_str):
        """解析bounds字符串 '[54,34][592,75]' -> (54, 34, 592, 75)"""
        try:
            bounds_str = bounds_str.replace('[', '').replace(']', ',')
            coords = [int(x) for x in bounds_str.split(',') if x]
            if len(coords) >= 4:
                return coords[0], coords[1], coords[2], coords[3]
        except (ValueError, IndexError):
            pass
        return 0, 0, 0, 0
    
    def get_normalized_pos(self, bounds_str):
        """获取规范化位置 [x, y]"""
        x1, y1, x2, y2 = self.parse_bounds(bounds_str)
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        return [center_x / self.screen_size[0], center_y / self.screen_size[1]]
    
    def get_normalized_size(self, bounds_str):
        """获取规范化尺寸 [width, height]"""
        x1, y1, x2, y2 = self.parse_bounds(bounds_str)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        return [width / self.screen_size[0], height / self.screen_size[1]]
    
    def get_bounds_array(self, bounds_str):
        """获取边界数组 [x1, y1, x2, y2] 规范化"""
        x1, y1, x2, y2 = self.parse_bounds(bounds_str)
        return [
            x1 / self.screen_size[0],
            y1 / self.screen_size[1],
            x2 / self.screen_size[0],
            y2 / self.screen_size[1]
        ]
    
    def extract_node_attributes(self, node_elem):
        """提取节点的所有属性"""
        attrib = node_elem.attrib
        bounds_str = attrib.get('bounds', '[0,0][0,0]')
        
        # 特殊标记值，表示这是代码赋予的默认值
        CODE_DEFAULT_BOOL = -9999
        CODE_DEFAULT_NUM = -8888.8888
        
        # 基础属性
        text = attrib.get('text', '').strip()
        class_name = attrib.get('class', '')
        resourceId = attrib.get('resource-id', '')
        # 安全获取布尔值的函数，如果XML中没有该属性则返回特殊标记
        def get_bool_attr(attr_name, default_if_missing='false'):
            if attr_name in attrib:
                return attrib[attr_name].lower() == 'true'
            else:
                return CODE_DEFAULT_BOOL  # 标记为代码默认值
        
        # 安全获取数值属性
        def get_numeric_attr(attr_name, default_value):
            if attr_name in attrib:
                try:
                    return int(attrib[attr_name])
                except (ValueError, TypeError):
                    return default_value
            else:
                return CODE_DEFAULT_NUM  # 标记为代码默认值
        
        # 构建完整属性字典
        attributes = {
            # 基本信息
            'type': class_name if class_name else '<UNKNOWN_TYPE>',
            'name': resourceId if resourceId else text if text else class_name if class_name else '<UNKNOWN_NAME>',
            'text': text,
            'package': attrib.get('package', ''),
            'resourceId': resourceId,
            
            # 状态属性 - 如果XML中没有该属性，返回特殊标记值
            'enabled': get_bool_attr('enabled', 'true'),
            'visible': get_bool_attr('visible-to-user', 'true'),
            'clickable': get_bool_attr('clickable', 'false'),
            'focusable': get_bool_attr('focusable', 'false'),
            'focused': get_bool_attr('focused', 'false'),
            'scrollable': get_bool_attr('scrollable', 'false'),
            'selected': get_bool_attr('selected', 'false'),
            'checkable': get_bool_attr('checkable', 'false'),
            'checked': get_bool_attr('checked', 'false'),
            'longClickable': get_bool_attr('long-clickable', 'false'),
            
            # 位置和尺寸
            'pos': self.get_normalized_pos(bounds_str),
            'size': self.get_normalized_size(bounds_str),
            'bounds': self.get_bounds_array(bounds_str),
            
            # 兼容属性
            'touchable': get_bool_attr('clickable', 'false'),  # touchable通常等同于 clickable
            'editable': 'EditText' in class_name,
            'dismissable': CODE_DEFAULT_BOOL,  # 这个属性通常不在XML中
            'scale': [1.0, 1.0],  # 代码默认值
            'anchorPoint': [0.5, 0.5],  # 代码默认值
            'zOrders': {
                'local': get_numeric_attr('drawing-order', 0), 
                'global': get_numeric_attr('drawing-order', 0)
            },
            'boundsInParent': self.get_normalized_size(bounds_str),
            
            # 元数据：标记哪些属性是XML原生的，哪些是代码赋予的
            # '_xml_attributes': list(attrib.keys()),  # XML中实际存在的属性
            # '_code_defaults': {
            #     'scale': True,
            #     'anchorPoint': True,
            #     'dismissable': True,
            #     'boundsInParent': True,
            #     'editable': True,  # 基于class推断
            # }
        }
        
        return attributes
    
    def extract_widgets_from_xml(self):
        """从XML提取所有widget信息"""
        if not self.xml_content:
            print("❌ 没有XML内容")
            return False
        
        try:
            print("正在解析XML...")
            root = ET.fromstring(self.xml_content)
            
            self.widgets = []
            self._extract_node_recursive(root, [])
            
            print(f"✅ 成功提取 {len(self.widgets)} 个widget")
            return True
            
        except Exception as e:
            print(f"解析XML失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _extract_node_recursive(self, node_elem, path):
        """递归提取节点信息"""
        # 跳过hierarchy根节点
        if node_elem.tag == 'hierarchy':
            for i, child in enumerate(node_elem):
                self._extract_node_recursive(child, [i])
            return
        
        # 提取当前节点属性
        attributes = self.extract_node_attributes(node_elem)
        
        # 统计子节点
        children_count = len(list(node_elem))
        
        # 构建路径字符串
        path_string = '/'.join(map(str, path)) if path else 'root'
        
        # 构建widget信息
        widget_info = {
            'path_string': path_string,
            'payload_details': {
                **attributes,
                'children_count': children_count
            }
        }
        
        self.widgets.append(widget_info)
        
        # 调试输出
        node_type = attributes.get('type', 'N/A')
        package = attributes.get('package', 'N/A')
        resource_id = attributes.get('resourceId', 'N/A')
        text = attributes.get('text', 'N/A')[:20] if attributes.get('text') else 'N/A'
        
        print(f"提取节点: {path_string} | type={node_type} | package={package} | resourceId={resource_id} | text={text} | 子节点数={children_count}")
        
        # 递归处理子节点
        for i, child in enumerate(node_elem):
            self._extract_node_recursive(child, path + [i])
    
    def get_package_statistics(self):
        """获取包名统计"""
        package_count = {}
        for widget in self.widgets:
            package = widget['payload_details'].get('package', '')
            if package:
                package_count[package] = package_count.get(package, 0) + 1
        return package_count
    
    def filter_widgets_by_package(self, package_name):
        """根据包名过滤widget"""
        return [w for w in self.widgets if package_name in w['payload_details'].get('package', '')]
    
    def filter_widgets_by_resource_id(self, resource_id):
        """根据resourceId过滤widget"""
        return [w for w in self.widgets if resource_id in w['payload_details'].get('resourceId', '')]

    
    def save_to_json(self, filename):
        """保存到JSON文件"""
        try:
            self.widgets = self.filter_widgets_by_package('com.unitvnet.mobs')
            output_data = {
                'total_count': len(self.widgets),
                'extraction_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'extraction_method': 'pure_uiautomator2',
                'screen_size': self.screen_size,
                'widgets': self.widgets
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 数据已保存到: {filename}")
            return True
            
        except Exception as e:
            print(f"保存文件失败: {e}")
            return False
    
    def save_xml(self, filename):
        """保存XML文件"""
        if not self.xml_content:
            return False
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.xml_content)
            print(f"✅ XML已保存到: {filename}")
            return True
        except Exception as e:
            print(f"保存XML失败: {e}")
            return False
    def del_xml(self, filename):
        """删除XML文件"""
        if os.path.exists(filename):
            os.remove(filename)
            print(f"✅ XML已删除: {filename}")
            return True
        else:
            print(f"❌ XML不存在: {filename}")
            return False
    
    def analyze_attribute_authenticity(self):
        """分析属性的真实性统计"""
        CODE_DEFAULT_BOOL = -9999
        CODE_DEFAULT_NUM = -8888.8888
        
        total_widgets = len(self.widgets)
        authenticity_stats = {
            'xml_attributes_count': {},  # 各属性在XML中出现的次数
            'code_defaults_count': {},   # 各属性使用代码默认值的次数
            'special_values': {
                'bool_defaults': 0,
                'num_defaults': 0
            }
        }
        
        bool_attrs = ['enabled', 'visible', 'clickable', 'focusable', 'focused', 
                     'scrollable', 'selected', 'checkable', 'checked', 'longClickable', 
                     'touchable', 'dismissable']
        
        for widget in self.widgets:
            details = widget['payload_details']
            xml_attrs = details.get('_xml_attributes', [])
            
            # 统计XML中实际存在的属性
            for attr in xml_attrs:
                authenticity_stats['xml_attributes_count'][attr] = \
                    authenticity_stats['xml_attributes_count'].get(attr, 0) + 1
            
            # 统计布尔属性的真实性
            for attr in bool_attrs:
                value = details.get(attr)
                if value == CODE_DEFAULT_BOOL:
                    authenticity_stats['special_values']['bool_defaults'] += 1
                    authenticity_stats['code_defaults_count'][attr] = \
                        authenticity_stats['code_defaults_count'].get(attr, 0) + 1
            
            # 统计数值属性的真实性
            z_orders = details.get('zOrders', {})
            if z_orders.get('local') == CODE_DEFAULT_NUM:
                authenticity_stats['special_values']['num_defaults'] += 1
        
        return authenticity_stats, total_widgets
    
    def print_summary(self):
        """打印摘要信息"""
        if not self.widgets:
            print("没有widget数据")
            return
        
        print(f"\n=== Widget摘要信息 ===")
        print(f"总节点数: {len(self.widgets)}")
        print(f"屏幕尺寸: {self.screen_size[0]}x{self.screen_size[1]}")
        
        # 包名统计
        package_count = self.get_package_statistics()
        print(f"\n包名统计 ({len(package_count)} 种):")
        for package, count in sorted(package_count.items()):
            print(f"  {package}: {count}")
        
        # 检查目标包
        unitvnet_count = sum(count for pkg, count in package_count.items() if 'unitvnet' in pkg)
        if unitvnet_count > 0:
            print(f"\n✅ 成功检测到 {unitvnet_count} 个com.unitvnet.mobs应用的UI元素!")
        else:
            print(f"\n❌ 未检测到com.unitvnet.mobs应用的UI元素")
        
        # 类型统计
        type_count = {}
        clickable_count = 0
        text_count = 0
        
        for widget in self.widgets:
            details = widget['payload_details']
            widget_type = details.get('type', 'N/A')
            type_count[widget_type] = type_count.get(widget_type, 0) + 1
            
            clickable = details.get('clickable')
            if clickable is True:  # 只统计真正的True，不包括-9999
                clickable_count += 1
            if details.get('text'):
                text_count += 1
        
        print(f"\n其他统计:")
        print(f"  可点击元素: {clickable_count}")
        print(f"  有文本元素: {text_count}")
        print(f"  元素类型数: {len(type_count)}")
        
        # 属性真实性分析
        auth_stats, total = self.analyze_attribute_authenticity()
        print(f"\n=== 属性真实性分析 ===")
        print(f"特殊标记值统计:")
        print(f"  布尔默认值(-9999)出现次数: {auth_stats['special_values']['bool_defaults']}")
        print(f"  数值默认值(-8888.8888)出现次数: {auth_stats['special_values']['num_defaults']}")
        
        print(f"\nXML中实际存在的属性TOP10:")
        xml_attrs_sorted = sorted(auth_stats['xml_attributes_count'].items(), 
                                 key=lambda x: x[1], reverse=True)
        for attr, count in xml_attrs_sorted[:10]:
            percentage = (count / total) * 100
            print(f"  {attr}: {count}/{total} ({percentage:.1f}%)")
        
        print(f"\n代码默认值使用统计:")
        code_defaults_sorted = sorted(auth_stats['code_defaults_count'].items(), 
                                    key=lambda x: x[1], reverse=True)
        for attr, count in code_defaults_sorted:
            percentage = (count / total) * 100
            print(f"  {attr}: {count}/{total} ({percentage:.1f}%) 使用代码默认值")


def extract_from_device(device_id=None, output_file="pure_ui2_widgets.json"):
    """从设备提取widget信息的简单接口"""
    extractor = PureUIAutomator2Extractor(device_id)
    
    # 获取设备XML
    if not extractor.get_xml_from_device():
        return None
    
    # 提取widget信息
    if not extractor.extract_widgets_from_xml():
        return None
    
    # 保存结果
    extractor.save_to_json(output_file)
    extractor.save_xml(output_file.replace('.json', '.xml'))
    
    # 显示摘要
    extractor.print_summary()
    
    return extractor.widgets

def extract_from_file(xml_file_path, output_file="pure_ui2_widgets.json"):
    """从XML文件提取widget信息的简单接口"""
    extractor = PureUIAutomator2Extractor()
    
    # 从文件读取XML
    if not extractor.get_xml_from_file(xml_file_path):
        return None
    
    # 提取widget信息
    if not extractor.extract_widgets_from_xml():
        return None
    
    # 保存结果
    extractor.save_to_json(output_file)
    
    # 显示摘要
    extractor.print_summary()
    
    return extractor.widgets

def main():
    """主函数"""
    print("Pure UIAutomator2 Widget Extractor")
    print("=" * 60)
    
    try:
        # 创建提取器
        extractor = PureUIAutomator2Extractor()
        
        # 优先尝试从设备获取
        print("尝试从设备获取实时数据...")
        if extractor.get_xml_from_device():
            print("✅ 成功获取设备数据")
        else:
            print("❌ 设备获取失败，尝试使用现有XML文件...")
            if not extractor.get_xml_from_file('screen_dump.xml'):
                print("❌ 也无法从文件获取XML")
                return
        
        # 保存当前XML
        extractor.save_xml('pure_ui2_current.xml')
        
        # 提取widget信息
        if not extractor.extract_widgets_from_xml():
            print("❌ 提取widget信息失败")
            return
        
        # 保存结果
        extractor.save_to_json('pure_ui2_widgets_complete.json')
        #
        # 显示摘要
        extractor.print_summary()
        extractor.del_xml('pure_ui2_current.xml')  # 删除当前XML
        print("✅ 提取完成!")
        
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()