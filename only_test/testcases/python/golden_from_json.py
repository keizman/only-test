# 测试 vod 正常播放, 点播节目名称 西语手机端720资源02
# [tag] vod, playing
# [path] app_initialization -> app_startup -> home -> search -> search_result -> vod_playing_detail

# 统一的导包方案, 其它用例直接复用即可
# -----
import sys, os
# Ensure repository root on sys.path so that 'only_test' package is importable
_here = os.path.dirname(__file__)
_repo_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# 添加项目路径，保证 from lib import ... 可用
_project_root = os.path.abspath(os.path.join(_here, "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from only_test.lib.airtest_compat import *
from lib.poco_utils import get_android_poco
from only_test.lib.ad_closer import close_ads
import asyncio
# -----

# Optional: 设置设备连接（如需）
# connect_device("android://127.0.0.1:5037/DEVICE_SERIAL?touch_method=ADBTOUCH&")

poco = get_android_poco()


## [page] app_initialization, [action] restart, [comment] 重启应用清理环境状态(多次关闭)

stop_app("com.mobile.brasiltvmobile")
stop_app("com.mobile.brasiltvmobile")
stop_app("com.mobile.brasiltvmobile")
sleep(3)  # 等待应用完全关闭


## [page] app_startup, [action] launch, [comment] 启动应用并等待加载完成
start_app("com.mobile.brasiltvmobile")
sleep(5)  # 等待应用启动完成


## [page] home, [action] close_ads, [comment] 进入 APK 后使用统一策略自动关闭广告/弹窗（连续3次未检测到广告或20秒内结束）
asyncio.run(close_ads(target_app="com.mobile.brasiltvmobile", mode="continuous", consecutive_no_ad=3, max_duration=20.0))


## [page] home, [action] click, [comment] 点击搜索按钮进入搜索页面
poco(resourceId="com.mobile.brasiltvmobile:id/mVodImageSearch").click()


## [page] search, [action] click, [comment] 点击搜索输入框激活输入状态
poco(resourceId="com.mobile.brasiltvmobile:id/searchEt").click()


## [page] search, [action] input, [comment] 输入搜索关键词

sleep(0.5)
text("西语手机端720资源02")


## [page] search, [action] click, [comment] 点击搜索按钮执行搜索操作
poco(resourceId="com.mobile.brasiltvmobile:id/searchCancel").click()


## [page] search_result, [action] click, [comment] 点击目标节目卡片
poco(resourceId="com.mobile.brasiltvmobile:id/mPosterName", text="西语手机端720资源02").click()


## [page] vod_playing_detail, [action] click, [comment] 点击播放按钮开始播放视频
poco(resourceId="com.mobile.brasiltvmobile:id/mPlayPauseIcon").click()


## [page] vod_playing_detail, [action] wait_for_elements, [comment] 等待广告播放完毕（Ads 消失）
poco(text="Ads").wait_for_disappearance(timeout=30)


sleep(0.5)


## [page] vod_playing_detail, [action] click_center_of, [comment] 点击视频中心区域唤起播控控件
miniScreenCenterX,miniScreenCenterY = poco(resourceId="com.mobile.brasiltvmobile:id/mPlayPauseIcon").get_position()
poco.click([miniScreenCenterX, miniScreenCenterY])


## [page] vod_playing_detail, [action] click, [comment] 点击全屏按钮进入全屏播放模式
poco(resourceId="com.mobile.brasiltvmobile:id/mImageFullScreen").click()



# teardown_hook()
# 这里会放置一些测之后的必要清理 
