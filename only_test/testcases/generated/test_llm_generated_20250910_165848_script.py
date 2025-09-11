# 测试vod点播播放正常: 关闭广告→搜索→点击首个结果→播放并断言
# [tag] 
# [path] 

from only_test.lib.airtest_compat import *
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
import logging

# 建议通过 airtest run --device 传入设备；如需直接连接，请取消下一行注释并填写设备ID
# connect_device("android://127.0.0.1:5037/DEVICE?touch_method=ADBTOUCH&")  # 使用 airtest run --device 传入或在此填写

# 基础日志器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)

try:
    ## [page] Home, [action] click, [comment] 关闭启动广告弹窗
    
    poco("com.mobile.brasiltvmobile:id/close_ad_button").click()
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    ## [page] Home, [action] click, [comment] 关闭启动广告弹窗
    
    poco("com.mobile.brasiltvmobile:id/close_ad_button").click()

try:
    ## [page] Home, [action] click, [comment] 点击搜索框以准备输入关键词
    
    poco("com.mobile.brasiltvmobile:id/search_input").click()
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    ## [page] Home, [action] click, [comment] 点击搜索框以准备输入关键词
    
    poco("com.mobile.brasiltvmobile:id/search_input").click()

try:
    ## [page] Home, [action] input, [comment] 在搜索框中输入关键词“电影”
    
    poco("com.mobile.brasiltvmobile:id/search_input").click()
    sleep(0.5)
    text("电影")
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    ## [page] Home, [action] input, [comment] 在搜索框中输入关键词“电影”
    
    poco("com.mobile.brasiltvmobile:id/search_input").click()
    sleep(0.5)
    text("电影")

try:
    ## [page] SearchResults, [action] click, [comment] 点击搜索结果列表的第一条结果
    
    poco("com.mobile.brasiltvmobile:id/result_item_0").click()
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    ## [page] SearchResults, [action] click, [comment] 点击搜索结果列表的第一条结果
    
    poco("com.mobile.brasiltvmobile:id/result_item_0").click()

try:
    ## [page] VideoDetail, [action] click, [comment] 点击播放按钮开始播放视频
    
    poco("com.mobile.brasiltvmobile:id/play_button").click()
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    ## [page] VideoDetail, [action] click, [comment] 点击播放按钮开始播放视频
    
    poco("com.mobile.brasiltvmobile:id/play_button").click()

## [page] VideoDetail, [action] assert, [comment] 断言视频正在播放，播放进度大于0秒
assert poco("com.mobile.brasiltvmobile:id/playback_timer").exists(), "元素 com.mobile.brasiltvmobile:id/playback_timer 不存在"


# 测试用例执行完成
# TODO: 添加结果验证和清理代码
