#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成的测试用例: 演示智能搜索功能测试
测试ID: TC_DEMO_SMART_SEARCH_20241205
生成时间: 2025-09-05T18:23:55.938827
原始模板: smart_search_template

描述: 演示Only-Test框架的智能条件判断功能，展示如何根据搜索框状态智能选择操作路径
"""

import pytest
import allure
from only_test.core.api import *
from only_test.core.android.android import Android
from only_test.core.cv import Template
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

# 测试元数据
TESTCASE_METADATA = {
  "ai_friendly": true,
  "app_versions": [
    "\u003e=1.0.0"
  ],
  "author": "Only-Test Demo Generator",
  "category": "functional_test",
  "complexity": "conditional_logic",
  "device_types": [
    "android_phone"
  ],
  "estimated_duration": 45,
  "priority": "high",
  "tags": [
    "demo",
    "search",
    "smart_judgment",
    "conditional",
    "music"
  ]
}
VARIABLES = {
  "expected_results_count": "\u003e= 3",
  "max_wait_time": 20,
  "search_keyword": "\u5468\u6770\u4f26",
  "target_app_package": "com.example.musicapp"
}

def find_element_by_priority_selectors(selectors):
    """根据优先级选择器查找元素"""
    poco = AndroidUiautomationPoco(use_airtest_input=True)
    
    for selector in selectors:
        try:
            if "resource_id" in selector:
                element = poco(resourceId=selector["resource_id"])
            elif "text" in selector:
                element = poco(text=selector["text"])
            elif "content_desc" in selector:
                element = poco(desc=selector["content_desc"])
            elif "class" in selector:
                element = poco(type=selector["class"])
            else:
                continue
                
            if element.exists():
                return element
        except Exception:
            continue
    
    return None

def wait_for_element(selectors, timeout=10):
    """等待元素出现"""
    poco = AndroidUiautomationPoco(use_airtest_input=True)
    
    for selector in selectors:
        try:
            if "resource_id" in selector:
                poco(resourceId=selector["resource_id"]).wait_for_appearance(timeout=timeout)
                return True
        except Exception:
            continue
    
    return False

@allure.feature("functional_test")
@allure.story("演示智能搜索功能测试")
@allure.title("演示Only-Test框架的智能条件判断功能，展示如何根据搜索框状态智能选择操作路径")
@allure.description("""
目标应用: com.example.musicapp
测试优先级: high
预估时长: 45秒

业务描述: 演示Only-Test框架的智能条件判断功能，展示如何根据搜索框状态智能选择操作路径
""")
class TestTC_DEMO_SMART_SEARCH_20241205:
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self):
        """测试前后置处理"""
        # 连接设备
        auto_setup(__file__)
        
        # 启动应用
        start_app("com.example.musicapp")
        sleep(3)
        
        # 拍摄初始截图
        allure.attach(screenshot(), name="测试开始截图", attachment_type=allure.attachment_type.PNG)
        
        yield
        
        # 清理工作
        allure.attach(screenshot(), name="测试结束截图", attachment_type=allure.attachment_type.PNG)
    
    @allure.severity(allure.severity_level.CRITICAL)
    def test_tc_demo_smart_search_20241205_execution(self):
        """执行智能测试用例"""
        
        with allure.step("测试用例基本信息"):
            allure.attach(
                f"测试ID: TC_DEMO_SMART_SEARCH_20241205\n"
                f"测试名称: 演示智能搜索功能测试\n"
                f"目标应用: com.example.musicapp\n"
                f"生成方式: json_to_python_converter",
                name="测试基本信息"
            )

        with allure.step("Step 1: 点击音乐应用首页搜索按钮"):
            allure.attach("成功进入搜索页面，显示搜索输入框", name="成功标准")
            
                # 执行点击操作
                element = find_element_by_priority_selectors([{'resource_id': 'com.example.musicapp:id/search_btn'}, {'resource_id': 'search_button'}, {'content_desc': '搜索音乐'}, {'text': '搜索'}, {'xpath': "//android.widget.ImageView[@content-desc='搜索']"}, {'visual_hint': '搜索图标或放大镜'}])
                if element:
                    element.click()
                    allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
                else:
                    raise Exception("未找到可点击元素")

            sleep(1)  # 操作间隔

        with allure.step("Step 2: 🧠 智能判断搜索框状态并选择相应操作：有内容则清空，无内容则直接输入"):
            allure.attach("确保搜索框处于正确状态，避免新旧搜索词混合导致搜索结果错误", name="业务逻辑说明")
            allure.attach("智能判断提示", name="AI提示")
            
            # 执行条件检查
                # 智能检查搜索框状态
                element = find_element_by_priority_selectors([{'resource_id': 'com.example.musicapp:id/search_edit'}, {'resource_id': 'search_input'}, {'class': 'android.widget.EditText'}, {'xpath': "//android.widget.EditText[contains(@hint,'搜索')]"}])
                has_content = bool(element and element.get_text() and len(element.get_text().strip()) > 0)
                allure.attach(f"搜索框内容检查: {'has_content': has_content, 'element_found': bool(element)}", name="条件判断结果")

            
            # 根据条件选择执行路径
            if has_content:
                with allure.step("条件分支: True时的处理"):
                        # 搜索框已有历史搜索内容，需要先清空才能输入新的搜索词'周杰伦'
                        element = find_element_by_priority_selectors([{'resource_id': 'com.example.musicapp:id/search_clear'}, {'resource_id': 'clear_text'}, {'content_desc': '清除搜索'}, {'xpath': "//android.widget.ImageView[@content-desc='清除']"}, {'visual_hint': '×符号或清除按钮'}])
                        if element:
                            element.click()
                            allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
                        else:
                            raise Exception("未找到可点击元素")

            else:
                with allure.step("条件分支: False时的处理"):
                        # 搜索框为空，可以直接输入搜索关键词'周杰伦'
                        element = find_element_by_priority_selectors([{'resource_id': 'search_input_box'}])
                        if element:
                            element.set_text(VARIABLES.get('search_keyword', '${search_keyword}'))
                            allure.attach(screenshot(), name="输入后截图", attachment_type=allure.attachment_type.PNG)
                        else:
                            raise Exception("未找到输入元素")


        with allure.step("Step 3: 确保搜索关键词正确输入到搜索框中"):
            allure.attach("执行条件判断", name="业务逻辑说明")
            allure.attach("验证搜索框中的内容是否为目标搜索词", name="AI提示")
            
            # 执行条件检查
                # 检查搜索框是否为空
                element = find_element_by_priority_selectors([{'resource_id': 'search_input_box'}])
                is_empty = not bool(element and element.get_text() and len(element.get_text().strip()) > 0)
                allure.attach(f"搜索框空值检查: {'is_empty': is_empty, 'element_found': bool(element)}", name="条件判断结果")

            
            # 根据条件选择执行路径
            if is_empty:
                with allure.step("条件分支: True时的处理"):
                        # 搜索框已清空，现在输入目标搜索词'周杰伦'
                        element = find_element_by_priority_selectors([{'resource_id': 'com.example.musicapp:id/search_edit'}, {'resource_id': 'search_input'}, {'class': 'android.widget.EditText'}])
                        if element:
                            element.set_text(VARIABLES.get('search_keyword', '${search_keyword}'))
                            allure.attach(screenshot(), name="输入后截图", attachment_type=allure.attachment_type.PNG)
                        else:
                            raise Exception("未找到输入元素")

            else:
                with allure.step("条件分支: False时的处理"):# skip 动作代码待实现

        with allure.step("Step 4: 点击搜索按钮执行搜索操作"):
            allure.attach("搜索请求成功发送，页面开始加载搜索结果", name="成功标准")
            
                # 执行点击操作
                element = find_element_by_priority_selectors([{'resource_id': 'com.example.musicapp:id/search_submit'}, {'resource_id': 'search_button'}, {'content_desc': '开始搜索'}, {'text': '搜索'}, {'xpath': "//android.widget.Button[contains(@text,'搜索')]"}, {'visual_hint': '搜索按钮或确认图标'}])
                if element:
                    element.click()
                    allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
                else:
                    raise Exception("未找到可点击元素")

            sleep(1)  # 操作间隔

        with allure.step("Step 5: 等待搜索结果加载完成"):
            allure.attach("搜索结果列表显示，包含周杰伦相关的音乐内容", name="成功标准")
            
                # 等待搜索结果加载完成
                wait_for_element([{'resource_id': 'com.example.musicapp:id/search_results'}, {'class': 'androidx.recyclerview.widget.RecyclerView'}, {'xpath': '//android.widget.ListView'}, {'visual_hint': '搜索结果列表'}], timeout=${max_wait_time})
                allure.attach(screenshot(), name="等待完成截图", attachment_type=allure.attachment_type.PNG)

            sleep(1)  # 操作间隔

        with allure.step("Step 6: 点击第一个周杰伦相关的搜索结果"):
            allure.attach("成功进入歌曲详情页或开始播放", name="成功标准")
            
                # 执行点击操作
                element = find_element_by_priority_selectors([{'xpath': "//android.widget.TextView[contains(@text,'周杰伦')][1]"}, {'resource_id': 'com.example.musicapp:id/song_item'}, {'visual_hint': '第一个搜索结果项'}])
                if element:
                    element.click()
                    allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
                else:
                    raise Exception("未找到可点击元素")

            sleep(1)  # 操作间隔

        
        # 执行断言验证
        with allure.step("断言验证: 验证搜索结果正常显示"):
                # 验证搜索结果正常显示
                poco = AndroidUiautomationPoco(use_airtest_input=True)
                results_exist = poco("搜索结果").exists()
                assert results_exist, "搜索结果不存在"
                allure.attach(f"搜索结果验证: 预期=True, 实际={results_exist}", name="断言结果")

        with allure.step("断言验证: 验证搜索结果数量符合预期"):
                # 验证搜索结果数量符合预期
                poco = AndroidUiautomationPoco(use_airtest_input=True)
                results_count = len(poco("result_item"))
                assert results_count >= ${expected_results_count}, f"搜索结果数量不足: 实际={results_count}, 预期>=${expected_results_count}"

        with allure.step("断言验证: 验证搜索结果与搜索关键词相关"):
                # 验证搜索结果与搜索关键词相关
                poco = AndroidUiautomationPoco(use_airtest_input=True)
                content_found = poco(text="周杰伦").exists()
                assert content_found, f"未找到相关内容: 周杰伦"
                allure.attach(f"内容相关性验证: 关键词=周杰伦, 找到={content_found}", name="断言结果")

        
        allure.attach(screenshot(), name="测试执行完成截图", attachment_type=allure.attachment_type.PNG)

if __name__ == "__main__":
    pytest.main([__file__, "--alluredir=../../reports/allure-results", "-v"])