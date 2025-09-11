# -*- encoding=utf8 -*-
__author__ = "zard"

from airtest.core.api import *
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)
poco.click(0.4996527777777778,0.8701171875)
import pytest
import allure

connect_device("android://127.0.0.1:5037/192.168.100.112:5555?touch_method=ADBTOUCH&")

# touch(Template(r"tpl1750822620009.png", record_pos=(-0.179, -0.669), resolution=(1440, 2560)))

auto_setup(__file__)
driver.get("Write your test web address!")

stop_app("com.msandroid.mobile")

sleep(1.0)
start_app("com.msandroid.mobile")
sleep(2.0)

poco(text="Next").click()
poco(text="OK").click()


# poco.wait_for_all(UIObjectProxy.wait_for_appearance("com.msandroid.mobile:id/tv_tab_title"))
# poco.wait_for_appearance("com.msandroid.mobile:id/tv_tab_title")

# poco("android.widget.FrameLayout").child("android.widget.LinearLayout").offspring("android.widget.LinearLayout").child("android.widget.RelativeLayout")[1].child("com.msandroid.mobile:id/tv_tab_title").click

# poco("android.widget.FrameLayout").child("android.widget.LinearLayout").offspring("android.widget.LinearLayout").child("android.widget.RelativeLayout")[0]

# poco("com.msandroid.mobile:id/mVodImageSearch").click()
# ## click inputable box
# poco("com.msandroid.mobile:id/searchEt").click()
# ## input certain program name to input box
# text("creature")
# ## page: search pgae, comment: click search button-either cancel search button, judge by box have conten or not 
# poco("com.msandroid.mobile:id/searchCancel").click()


# (Template(r"C:\work\project\pyproject\mgs_home.png", record_pos=(-0.179, -0.669), resolution=(1440, 2560)))poco("com.unitvnet.tvod:id/mButton")


# # conda activate droidrun
# touch((0.2078125,  0.17916666666666667))

# touch((0.1015625, 0.0625))
# touch((0.1015625, 0.05694444444444444))
# 	  type :  android.widget.TextView 
# 	  name :  com.integration.unitvsiptv:id/mTextTitle 
# 	  text :  FEATURED 
# 	  enabled :  True 
# 	  visible :  True 
# 	  checkable :  False 
# 	  pos :  [0.2078125, 0.17916666666666667] 
# 	  resourceId :  b'com.integration.unitvsiptv:id/mTextTitle' 
# 	  scrollable :  False 
# 	  boundsInParent :  [0.1015625, 0.0625] 
# 	  selected :  True 
# 	  anchorPoint :  [0.5, 0.5] 
# 	  size :  [0.1015625, 0.05694444444444444] 
# 	  zOrders :  {'global': 0, 'local': 1} 
# 	  editalbe :  False 
# 	  checked :  False 
# 	  focused :  False 
# 	  touchable :  False 
# 	  package :  b'com.integration.unitvsiptv' 
# 	  scale :  [1, 1] 
# 	  dismissable :  False 
# 	  longClickable :  False 
# 	  focusable :  False 



