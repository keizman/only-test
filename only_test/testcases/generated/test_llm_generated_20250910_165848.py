#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成的测试用例: VOD点播播放正常
测试ID: TC_brasiltvmobile_20250910_165846
生成时间: 2025-09-10T16:59:10.474480
原始模板: None

描述: 测试vod点播播放正常: 关闭广告→搜索→点击首个结果→播放并断言
"""

import pytest
import allure
from only_test.lib.airtest_compat import *
from airtest.core.android.android import Android
from airtest.core.cv import Template
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

# 测试元数据
TESTCASE_METADATA = {}
VARIABLES = {}

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
@allure.story("VOD点播播放正常")
@allure.title("测试vod点播播放正常: 关闭广告→搜索→点击首个结果→播放并断言")
@allure.description("""
目标应用: com.mobile.brasiltvmobile
测试优先级: medium
预估时长: 30秒

业务描述: 测试vod点播播放正常: 关闭广告→搜索→点击首个结果→播放并断言
""")
class TestTC_brasiltvmobile_20250910_165846:
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self):
        """测试前后置处理"""
        # 连接设备
        auto_setup(__file__)
        
        # 启动应用
        start_app("com.mobile.brasiltvmobile")
        sleep(3)
        
        # 拍摄初始截图
        allure.attach(screenshot(), name="测试开始截图", attachment_type=allure.attachment_type.PNG)
        
        yield
        
        # 清理工作
        allure.attach(screenshot(), name="测试结束截图", attachment_type=allure.attachment_type.PNG)
    
    @allure.severity(allure.severity_level.NORMAL)
    def test_tc_brasiltvmobile_20250910_165846_execution(self):
        """执行智能测试用例"""
        
        with allure.step("测试用例基本信息"):
            allure.attach(
                f"测试ID: TC_brasiltvmobile_20250910_165846\n"
                f"测试名称: VOD点播播放正常\n"
                f"目标应用: com.mobile.brasiltvmobile\n"
                f"生成方式: json_to_python_converter",
                name="测试基本信息"
            )

        with allure.step("Step 1: 关闭启动广告弹窗"):
            allure.attach("广告弹窗消失，页面恢复至首页", name="成功标准")
            
                # 执行点击操作
                element = find_element_by_priority_selectors([{'resource_id': 'com.mobile.brasiltvmobile:id/close_ad_button'}, {'content_desc': '关闭'}])
                if element:
                    element.click()
                    allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
                else:
                    raise Exception("未找到可点击元素（缺少有效选择器），请确保 JSON 中提供 priority_selectors 或 bounds_px")

            sleep(1)  # 操作间隔

        with allure.step("Step 2: 点击搜索框以准备输入关键词"):
            allure.attach("搜索框获得焦点并弹出键盘", name="成功标准")
            
                # 执行点击操作
                element = find_element_by_priority_selectors([{'resource_id': 'com.mobile.brasiltvmobile:id/search_input'}, {'content_desc': '搜索框'}])
                if element:
                    element.click()
                    allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
                else:
                    raise Exception("未找到可点击元素（缺少有效选择器），请确保 JSON 中提供 priority_selectors 或 bounds_px")

            sleep(1)  # 操作间隔

        with allure.step("Step 3: 在搜索框中输入关键词“电影”"):
            allure.attach("搜索框内显示输入的文字“电影”", name="成功标准")
            
                # 输入数据
                element = find_element_by_priority_selectors([{'resource_id': 'com.mobile.brasiltvmobile:id/search_input'}])
                if element:
                    element.set_text('电影')
                    allure.attach(screenshot(), name="输入后截图", attachment_type=allure.attachment_type.PNG)
                else:
                    raise Exception("未找到输入元素（缺少有效选择器），请确保 JSON 中提供 priority_selectors 或 bounds_px")

            sleep(1)  # 操作间隔

        with allure.step("Step 4: 点击搜索结果列表的第一条结果"):
            allure.attach("进入视频详情页，页面标题为所选结果名称", name="成功标准")
            
                # 执行点击操作
                element = find_element_by_priority_selectors([{'content_desc': '第一条结果'}, {'resource_id': 'com.mobile.brasiltvmobile:id/result_item_0'}])
                if element:
                    element.click()
                    allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
                else:
                    raise Exception("未找到可点击元素（缺少有效选择器），请确保 JSON 中提供 priority_selectors 或 bounds_px")

            sleep(1)  # 操作间隔

        with allure.step("Step 5: 点击播放按钮开始播放视频"):
            allure.attach("视频播放器状态变为playing，出现播放进度条", name="成功标准")
            
                # 执行点击操作
                element = find_element_by_priority_selectors([{'resource_id': 'com.mobile.brasiltvmobile:id/play_button'}, {'content_desc': '播放'}])
                if element:
                    element.click()
                    allure.attach(screenshot(), name="点击后截图", attachment_type=allure.attachment_type.PNG)
                else:
                    raise Exception("未找到可点击元素（缺少有效选择器），请确保 JSON 中提供 priority_selectors 或 bounds_px")

            sleep(1)  # 操作间隔

        with allure.step("Step 6: 断言视频正在播放，播放进度大于0秒"):
            allure.attach("播放计时器显示的时间大于0秒", name="成功标准")
            # assert 动作代码待实现
            sleep(1)  # 操作间隔

        
        # 执行断言验证
        
        allure.attach(screenshot(), name="测试执行完成截图", attachment_type=allure.attachment_type.PNG)

if __name__ == "__main__":
    pytest.main([__file__, "--alluredir=../../reports/allure-results", "-v"])
