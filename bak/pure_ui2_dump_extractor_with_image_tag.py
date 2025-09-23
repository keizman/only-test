# coding=utf-8
"""
纯 UIAutomator2 Dump 信息提取器（带图像标记功能）

完全独立的实现，不依赖 Poco 或 Airtest 包
只使用 uiautomator2 和标准库，增加了Pillow用于图像处理

新增功能：
1. 在获取XML层次结构的同时进行截图
2. 自动标记所有有效UI元素（红框标记）
3. 在元素旁边显示文本标签（优先显示text，其次显示resourceId简化版）
4. 过滤无效元素（size和pos为原点的元素）

使用方法：
1. 直接运行脚本：python pure_ui2_dump_extractor_with_image_tag.py
2. 使用简单接口：extract_all_widgets()
3. 使用类接口：
   extractor = PureUI2DumpExtractor()
   extractor.extract_all_widgets_info()
   extractor.create_annotated_screenshot()

输出文件：
- all_widgets_complete_info_pure.json: 完整的widget信息
- original_screenshot.png: 原始截图
- annotated_screenshot.png: 带标记的截图
- raw_hierarchy_pure.xml: 原始XML层次结构

依赖：
- uiautomator2: pip install uiautomator2
- Pillow: pip install Pillow
"""

import sys
import os
import json
import xml.etree.ElementTree as ET
from typing import Union, List, Optional, Dict
import warnings

try:
    import uiautomator2 as u2
except ImportError:
    raise ImportError("uiautomator2 is required. Install with: pip install uiautomator2")

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise ImportError("Pillow is required for image processing. Install with: pip install Pillow")


class PureUI2DumpExtractor:
    """纯 UIAutomator2 Dump 信息提取器"""
    
    def __init__(self, device_id=None):
        """初始化"""
        try:
            if device_id:
                self.device = u2.connect(device_id)
            else:
                self.device = u2.connect()
        except Exception as e:
            raise RuntimeError("Failed to connect to Android device: {}".format(str(e)))
        
        self.dump_data = None
        self.all_nodes_info = []
        self.screen_size = None
        self.screenshot = None  # 存储截图
        
        # 获取屏幕尺寸
        try:
            info = self.device.info
            self.screen_size = (info.get('displayWidth', 1280), info.get('displayHeight', 720))
        except:
            self.screen_size = (1280, 720)
    
    def extract_all_widgets_info(self) -> List[Dict]:
        """提取所有widget的完整信息"""
        print("正在获取UI层次结构和截图...")
        
        try:
            # 同时获取XML dump数据和截图
            print("正在截图...")
            screenshot_data = self.device.screenshot(format='pillow')
            self.screenshot = screenshot_data
            print("截图完成")
            
            print("正在获取XML层次结构...")
            xml_content = self.device.dump_hierarchy()
            
            if not xml_content:
                print("获取的XML数据为空")
                return []
            
            # 解析XML
            root_element = ET.fromstring(xml_content)
            
            # 转换为兼容格式
            dump_dict = self._xml_to_poco_format(root_element)
            self.dump_data = dump_dict
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
    
    def _xml_to_poco_format(self, xml_element):
        """将XML元素转换为Poco兼容的格式"""
        attrib = xml_element.attrib
        
        # 解析bounds
        bounds_str = attrib.get('bounds', '[0,0][0,0]')
        x1, y1, x2, y2 = self._parse_bounds(bounds_str)
        
        # 计算标准化位置和尺寸
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        # 标准化坐标
        norm_center_x = center_x / self.screen_size[0]
        norm_center_y = center_y / self.screen_size[1]
        norm_width = width / self.screen_size[0]
        norm_height = height / self.screen_size[1]
        norm_bounds = [
            x1 / self.screen_size[0],
            y1 / self.screen_size[1],
            x2 / self.screen_size[0],
            y2 / self.screen_size[1]
        ]
        
        # 获取名称
        text = attrib.get('text', '').strip()
        name = text if text else attrib.get('class', '<Unknown>')
        
        # 构建payload
        payload = {
            'name': name,
            'type': attrib.get('class', 'Unknown'),
            'visible': attrib.get('visible-to-user', 'true').lower() == 'true',
            'enabled': attrib.get('enabled', 'true').lower() == 'true',
            'pos': [norm_center_x, norm_center_y],
            'size': [norm_width, norm_height],
            'bounds': norm_bounds,
            'text': attrib.get('text', ''),
            'resourceId': attrib.get('resource-id', ''),
            'package': attrib.get('package', ''),
            'clickable': attrib.get('clickable', 'false').lower() == 'true',
            'touchable': attrib.get('clickable', 'false').lower() == 'true',  # UIAutomator2 doesn't have touchable
            'focusable': attrib.get('focusable', 'false').lower() == 'true',
            'focused': attrib.get('focused', 'false').lower() == 'true',
            'scrollable': attrib.get('scrollable', 'false').lower() == 'true',
            'selected': attrib.get('selected', 'false').lower() == 'true',
            'checkable': attrib.get('checkable', 'false').lower() == 'true',
            'checked': attrib.get('checked', 'false').lower() == 'true',
            'longClickable': attrib.get('long-clickable', 'false').lower() == 'true',
            'editable': 'EditText' in attrib.get('class', ''),
            'dismissable': False,  # Not available in UIAutomator
            'scale': [1.0, 1.0],
            'anchorPoint': [0.5, 0.5],
            'boundsInParent': [norm_width, norm_height],
        }
        
        # zOrders
        drawing_order = attrib.get('drawing-order', '0')
        try:
            order = int(drawing_order)
        except (ValueError, TypeError):
            order = 0
        payload['zOrders'] = {'local': order, 'global': order}
        
        # 递归处理子节点
        children = []
        for child_elem in xml_element:
            child_dict = self._xml_to_poco_format(child_elem)
            if child_dict:
                children.append(child_dict)
        
        return {
            'name': name,
            'payload': payload,
            'children': children
        }
    
    def _parse_bounds(self, bounds_str):
        """解析bounds字符串如 '[54,34][592,75]' 为坐标"""
        try:
            bounds_str = bounds_str.replace('[', '').replace(']', ',')
            coords = [int(x) for x in bounds_str.split(',') if x]
            if len(coords) >= 4:
                return coords[0], coords[1], coords[2], coords[3]
        except (ValueError, IndexError):
            pass
        return 0, 0, 0, 0
    
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
                'editable': payload.get('editable', False),
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
                'extraction_method': 'pure_ui2_dump_extractor',
                'screen_size': self.screen_size,
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
    
    def save_raw_xml(self, filename: str = "raw_hierarchy.xml") -> bool:
        """保存原始XML数据到文件"""
        try:
            xml_content = self.device.dump_hierarchy()
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            print(f"原始XML数据已保存到: {filename}")
            return True
            
        except Exception as e:
            print(f"保存XML文件失败: {e}")
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
        print(f"屏幕尺寸: {self.screen_size}")
        
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
    
    def get_device_info(self):
        """获取设备信息"""
        return self.device.info
    
    def _get_timestamp(self):
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _is_valid_element(self, widget_info: Dict) -> bool:
        """判断元素是否有效（size和pos不为原点）"""
        details = widget_info.get('payload_details', {})
        pos = details.get('pos', [0, 0])
        size = details.get('size', [0, 0])
        
        # 检查位置和尺寸是否不为原点
        pos_valid = pos[0] > 0 or pos[1] > 0
        size_valid = size[0] > 0 and size[1] > 0
        
        return pos_valid and size_valid
    
    def _extract_resource_id_name(self, resource_id: str) -> str:
        """从resourceId中提取简化名称"""
        if not resource_id:
            return ""
        
        # 取最后一个/后的内容
        if '/' in resource_id:
            return resource_id.split('/')[-1]
        
        # 如果没有/，取最后一个:后的内容
        if ':' in resource_id:
            return resource_id.split(':')[-1]
        
        return resource_id
    
    def _get_element_label(self, widget_info: Dict) -> str:
        """获取元素的标签文本"""
        details = widget_info.get('payload_details', {})
        
        # 优先使用text
        text = details.get('text', '').strip()
        if text:
            # 限制文本长度
            return text[:20] + "..." if len(text) > 20 else text
        
        # 如果没有text，使用resourceId的简化版
        resource_id = details.get('resourceId', '')
        simplified_id = self._extract_resource_id_name(resource_id)
        if simplified_id:
            return simplified_id
        
        # 如果都没有，使用类型
        return details.get('type', 'Unknown')
    
    def create_annotated_screenshot(self, output_filename: str = "annotated_screenshot.png") -> bool:
        """创建带有元素标记的截图"""
        if self.screenshot is None:
            print("没有截图数据，请先调用 extract_all_widgets_info()")
            return False
        
        if not self.all_nodes_info:
            print("没有元素信息，请先调用 extract_all_widgets_info()")
            return False
        
        try:
            # 复制截图以避免修改原图
            annotated_image = self.screenshot.copy()
            draw = ImageDraw.Draw(annotated_image)
            
            # 尝试使用系统字体，如果失败则使用默认字体
            try:
                # Windows系统字体
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                try:
                    # Linux系统字体
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
                except:
                    # 使用默认字体
                    font = ImageFont.load_default()
            
            # 过滤有效元素并标记
            valid_elements = [widget for widget in self.all_nodes_info if self._is_valid_element(widget)]
            print(f"找到 {len(valid_elements)} 个有效元素进行标记")
            
            for widget in valid_elements:
                details = widget.get('payload_details', {})
                bounds = details.get('bounds', [])
                
                if len(bounds) >= 4:
                    # 将标准化坐标转换为像素坐标
                    x1 = int(bounds[0] * self.screen_size[0])
                    y1 = int(bounds[1] * self.screen_size[1])
                    x2 = int(bounds[2] * self.screen_size[0])
                    y2 = int(bounds[3] * self.screen_size[1])
                    
                    # 确保坐标有效
                    if x2 > x1 and y2 > y1:
                        # 绘制红色边框
                        draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
                        
                        # 获取标签文本
                        label = self._get_element_label(widget)
                        
                        if label:
                            # 在红框右侧绘制文本
                            text_x = x2 + 5
                            text_y = y1
                            
                            # 确保文本不超出屏幕边界
                            if text_x < self.screen_size[0] - 100:  # 留出100像素的边距
                                # 绘制文本背景
                                text_bbox = draw.textbbox((text_x, text_y), label, font=font)
                                draw.rectangle(text_bbox, fill="white", outline="red")
                                
                                # 绘制文本
                                draw.text((text_x, text_y), label, fill="red", font=font)
            
            # 保存标记后的图片
            annotated_image.save(output_filename)
            print(f"带标记的截图已保存到: {output_filename}")
            return True
            
        except Exception as e:
            print(f"创建标记截图失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_screenshot(self, filename: str = "screenshot.png") -> bool:
        """保存原始截图"""
        if self.screenshot is None:
            print("没有截图数据，请先调用 extract_all_widgets_info()")
            return False
        
        try:
            self.screenshot.save(filename)
            print(f"原始截图已保存到: {filename}")
            return True
        except Exception as e:
            print(f"保存截图失败: {e}")
            return False


def main():
    """主函数"""
    print("纯 UIAutomator2 Dump 信息提取器")
    print("=" * 50)
    
    try:
        # 创建提取器
        extractor = PureUI2DumpExtractor()
        
        # 显示设备信息
        device_info = extractor.get_device_info()
        print(f"设备信息: {device_info}")
        
        # 提取所有widget信息
        all_widgets = extractor.extract_all_widgets_info()
        
        if not all_widgets:
            print("未能提取到widget信息")
            # 尝试保存原始数据以便调试
            print("尝试保存原始数据...")
            extractor.save_raw_dump("debug_raw_dump_pure.json")
            extractor.save_raw_xml("debug_raw_hierarchy_pure.xml")
            return
        
        # 保存到JSON文件
        extractor.save_all_to_json("all_widgets_complete_info_pure.json")
        
        # 保存原始dump数据
        extractor.save_raw_dump("raw_dump_data_pure.json")
        
        # 保存原始XML数据
        extractor.save_raw_xml("raw_hierarchy_pure.xml")
        
        # 保存原始截图
        extractor.save_screenshot("original_screenshot.png")
        
        # 创建带标记的截图
        extractor.create_annotated_screenshot("annotated_screenshot.png")
        
        # 显示摘要
        extractor.print_summary()
        
        print("\n脚本执行完成!")
        
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()


# 提供简单的函数接口
def extract_all_widgets(output_file: str = "all_widgets_info_pure.json", 
                       device_id=None, create_annotated_image: bool = True) -> List[Dict]:
    """
    快速提取所有widget信息的简单接口
    
    Args:
        output_file: 输出JSON文件名
        device_id: 设备ID，如果不提供则使用默认设备
        create_annotated_image: 是否创建带标记的截图
    
    Returns:
        所有widget信息的列表
    """
    extractor = PureUI2DumpExtractor(device_id)
    widgets = extractor.extract_all_widgets_info()
    
    if widgets and output_file:
        extractor.save_all_to_json(output_file)
    
    # 如果需要，创建带标记的截图
    if widgets and create_annotated_image:
        extractor.save_screenshot("original_screenshot.png")
        extractor.create_annotated_screenshot("annotated_screenshot.png")
    
    return widgets


if __name__ == "__main__":
    main()


# 使用示例
"""
# 示例1: 使用简单接口
widgets = extract_all_widgets("my_widgets.json", create_annotated_image=True)
print(f"提取了 {len(widgets)} 个widget")

# 示例2: 使用类接口进行更多控制
extractor = PureUI2DumpExtractor()
widgets = extractor.extract_all_widgets_info()

# 只保存原始截图
extractor.save_screenshot("screenshot.png")

# 创建自定义名称的标记截图
extractor.create_annotated_screenshot("custom_annotated.png")

# 查找特定类型的widget
buttons = extractor.find_widgets_by_type("android.widget.Button")
text_widgets = extractor.find_widgets_with_text()

print(f"找到 {len(buttons)} 个按钮")
print(f"找到 {len(text_widgets)} 个包含文本的widget")
"""