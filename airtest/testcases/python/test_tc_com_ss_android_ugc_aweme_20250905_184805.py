#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成的测试用例: 抖音智能搜索测试
测试ID: TC_COM_SS_ANDROID_UGC_AWEME_20250905_184805
生成时间: 2025-09-05T18:48:05.621668
原始模板: None

描述: 基于用户需求生成的智能测试用例: 在抖音APP中搜索'美食视频'，如果搜索框有历史记录先清空
"""

import pytest
import allure
from airtest.core.api import *
from airtest.core.android.android import Android
from airtest.core.cv import Template
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

# 测试元数据
TESTCASE_METADATA = {
  "ai_friendly": true,
  "complexity": "conditional_logic",
  "device_types": [
    "android_phone"
  ],
  "estimated_duration": 60,
  "priority": "high",
  "tags": [
    "llm_generated",
    "search",
    "smart_judgment",
    "demo"
  ]
}
VARIABLES = {
  "max_wait_time": 20,
  "search_keyword": "\u7f8e\u98df\u89c6\u9891",
  "target_app_package": "com.ss.android.ugc.aweme"
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

@allure.feature("功能测试")
@allure.story("抖音智能搜索测试")
@allure.title("基于用户需求生成的智能测试用例: 在抖音APP中搜索'美食视频'，如果搜索框有历史记录先清空")
@allure.description("""
目标应用: com.ss.android.ugc.aweme
测试优先级: high
预估时长: 60秒

业务描述: 基于用户需求生成的智能测试用例: 在抖音APP中搜索'美食视频'，如果搜索框有历史记录先清空
""")
class TestTC_COM_SS_ANDROID_UGC_AWEME_20250905_184805:
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self):
        """测试前后置处理"""
        # 连接设备
        auto_setup(__file__)
        
        # 启动应用
        start_app("com.ss.android.ugc.aweme")
        sleep(3)
        
        # 拍摄初始截图
        allure.attach(screenshot(), name="测试开始截图", attachment_type=allure.attachment_type.PNG)
        
        yield
        
        # 清理工作
        allure.attach(screenshot(), name="测试结束截图", attachment_type=allure.attachment_type.PNG)
    
    @allure.severity(allure.severity_level.CRITICAL)
    def test_tc_com_ss_android_ugc_aweme_20250905_184805_execution(self):
        """执行智能测试用例"""
        
        with allure.step("测试用例基本信息"):
            allure.attach(
                f"测试ID: TC_COM_SS_ANDROID_UGC_AWEME_20250905_184805\n"
                f"测试名称: 抖音智能搜索测试\n"
                f"目标应用: com.ss.android.ugc.aweme\n"
                f"生成方式: json_to_python_converter",
                name="测试基本信息"
            )

        with allure.step("Step 1: 点击抖音搜索按钮"):
            allure.attach("成功进入搜索页面", name="成功标准")
            
                # 执行点击操作
                element = find_element_by_priority_selectors([{'resource_id': 'com.ss.android.ugc.aweme:id/search_btn'}, {'content_desc': '搜索'}, {'text': '搜索'}])
                if element:
                    element.click()
                    allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
                else:
                    raise Exception("未找到可点击元素")

            sleep(1)  # 操作间隔

        with allure.step("Step 2: 🧠 智能判断搜索框状态并选择操作"):
            allure.attach("确保搜索框处于正确状态", name="业务逻辑说明")
            allure.attach("智能判断提示", name="AI提示")
            
            # 执行条件检查
                # 智能检查搜索框状态
                element = find_element_by_priority_selectors([{'resource_id': 'com.ss.android.ugc.aweme:id/search_edit'}, {'class': 'android.widget.EditText'}])
                has_content = bool(element and element.get_text() and len(element.get_text().strip()) > 0)
                allure.attach(f"搜索框内容检查: {'has_content': has_content, 'element_found': bool(element)}", name="条件判断结果")

            
            # 根据条件选择执行路径
            if has_content:
                with allure.step("条件分支: True时的处理"):
                        # 搜索框有历史内容，需要先清空
                        element = find_element_by_priority_selectors([{'resource_id': 'com.ss.android.ugc.aweme:id/search_clear'}, {'content_desc': '清除'}])
                        if element:
                            element.click()
                            allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
                        else:
                            raise Exception("未找到可点击元素")

            else:
                with allure.step("条件分支: False时的处理"):
                        # 搜索框为空，直接输入搜索词
                        element = find_element_by_priority_selectors([])
                        if element:
                            element.set_text(VARIABLES.get('search_keyword', '${search_keyword}'))
                            allure.attach(screenshot(), name="输入后截图", attachment_type=allure.attachment_type.PNG)
                        else:
                            raise Exception("未找到输入元素")


        with allure.step("Step 3: 输入搜索关键词"):
            allure.attach("执行标准操作", name="成功标准")
            
                # 输入数据
                element = find_element_by_priority_selectors([])
                if element:
                    element.set_text(VARIABLES.get('search_keyword', '${search_keyword}'))
                    allure.attach(screenshot(), name="输入后截图", attachment_type=allure.attachment_type.PNG)
                else:
                    raise Exception("未找到输入元素")

            sleep(1)  # 操作间隔

        with allure.step("Step 4: 点击搜索按钮执行搜索"):
            allure.attach("执行标准操作", name="成功标准")
            
                # 执行点击操作
                element = find_element_by_priority_selectors([{'resource_id': 'com.ss.android.ugc.aweme:id/search_submit'}, {'text': '搜索'}])
                if element:
                    element.click()
                    allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
                else:
                    raise Exception("未找到可点击元素")

            sleep(1)  # 操作间隔

        
        # 执行断言验证
        
        allure.attach(screenshot(), name="测试执行完成截图", attachment_type=allure.attachment_type.PNG)

if __name__ == "__main__":
    pytest.main([__file__, "--alluredir=../../reports/allure-results", "-v"])