# 测试 vod 正常播放
# [tag] vod, playing
# [path] home -> search -> search_result -> vod_playing_detail -> playing

from airtest.core.api import *
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

connect_device("android://127.0.0.1:5037/192.168.100.112:5555?touch_method=ADBTOUCH&")
poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)

## [page] app_initialization, [action] restart, [comment] 重启应用清理环境状态
stop_app("com.mobile.brasiltvmobile")
stop_app("com.mobile.brasiltvmobile")
stop_app("com.mobile.brasiltvmobile")
sleep(1.5)

## [page] app_startup, [action] launch, [comment] 启动应用并等待加载完成
start_app("com.mobile.brasiltvmobile")
# wait app to start, that may take a few time based on phone performance
sleep(5)

## [page] home, [action] click, [comment] 处理首页弹窗 - 关闭升级提示弹窗
poco("com.mobile.brasiltvmobile:id/ivClose").click()

## [page] home, [action] click, [comment] 处理首页弹窗 - 关闭广告弹窗
poco("com.mobile.brasiltvmobile:id/mIvClose").click()

## [page] home, [action] click, [comment] 处理首页弹窗 - 再次确保关闭所有弹窗
poco("com.mobile.brasiltvmobile:id/ivClose").click()

## [page] home, [action] click, [comment] 点击搜索按钮进入搜索页面
poco("com.mobile.brasiltvmobile:id/mVodImageSearch").click()

## [page] search, [action] click, [comment] 点击搜索输入框激活输入状态
sleep(0.5)
poco("com.mobile.brasiltvmobile:id/searchEt").click()

## [page] search, [action] input, [comment] 输入搜索关键词
sleep(0.5)
text("西语手机端720资源02")

## [page] search, [action] click, [comment] 点击搜索按钮执行搜索操作
poco("com.mobile.brasiltvmobile:id/searchCancel").click()

## [page] search_result, [action] click, [comment] 点击搜索结果中第一个节目的封面图片
poco("android.widget.FrameLayout").child("android.widget.LinearLayout").offspring("android:id/content").offspring("com.mobile.brasiltvmobile:id/searchResultList").child("com.mobile.brasiltvmobile:id/mLinearLayout")[0].offspring("com.mobile.brasiltvmobile:id/posterImageView").click()

## [page] vod_playing_detail, [action] click, [comment] 点击播放按钮开始播放视频
miniScreenCenterX,miniScreenCenterY = poco("com.mobile.brasiltvmobile:id/mPlayPauseIcon").get_position()
poco("com.mobile.brasiltvmobile:id/mPlayPauseIcon").click()

## [page] vod_playing_detail, [action] wait, [comment] 等待广告播放完毕
poco(text="Ads").wait_for_disappearance(timeout=30)
sleep(0.5)

## [page] vod_playing_detail, [action] click, [comment] 点击视频中心区域唤起播控控件
poco.click([miniScreenCenterX, miniScreenCenterY])

## [page] vod_playing_detail, [action] click, [comment] 点击全屏按钮进入全屏播放模式
poco("com.mobile.brasiltvmobile:id/mImageFullScreen").click()

## [page] playing, [action] assert, [comment] 断言验证节目正在正常播放
# there is assert program are already playing 
#....







# -------------
# commente to get a position and click
#x, y = poco("com.mobile.brasiltvmobile:id/mVodImageSearch").get_position()
# Click at those coordinates 
#poco.click([x, y])