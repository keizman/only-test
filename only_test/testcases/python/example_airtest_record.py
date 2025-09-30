# 测试 vod 正常播放, 点播节目名称 西语手机端720资源02
# [tag] vod, playing
# [path] home -> search -> search_result -> vod_playing_detail -> playing

# 统一的导包方案, 其它用例直接复用即可
# -----
import sys, os
# Ensure repository root on sys.path so that 'only_test' package is importable
_here = os.path.dirname(__file__)
_repo_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from only_test.lib.airtest_compat import *
# 使用修复后的poco工具函数（已解决所有导入和依赖问题）

# 添加项目路径
project_root = os.path.join(os.path.dirname(__file__), '../..')
sys.path.insert(0, project_root)

from lib.poco_utils import get_android_poco
from only_test.lib.ad_closer import close_ads
import asyncio
# -----

# setup_hook()
# 这里会放置一些测之前的必要条件 
device_id = "192.168.100.112:5555"
connect_device("android://127.0.0.1:5037/{}?touch_method=ADBTOUCH&".format(device_id))
poco = get_android_poco(device_id=device_id, app_id="brav_mob")
program_name = "Peppa Pig: The Golden Boots"
# program_name = "西语手机端720资源02"


# [page] app_initialization, [action] stop_app, [comment] 重启应用清理环境状态
stop_app("com.mobile.brasiltvmobile")

sleep(3)  # 等待应用完全关闭, 后台关闭需要时间

## [page] app_startup, [action] start_app, [comment] 启动应用并等待加载完成
start_app("com.mobile.brasiltvmobile")
# wait app to start, that may take a few time based on phone performance
sleep(5) # APP 有启动动画, 需要等待

## [page] home, [action] close_ads, [comment] 进入 APK 后使用统一策略自动关闭广告/弹窗（连续 3 次未检测到广告或20秒内结束）[reason] 选用 XML resourceId mVodImageSearch 因为这是目前 XML 中唯一存在的 search 元素, 并且根据用例示例, 这是一个正确的查找一个节目的步骤
asyncio.run(close_ads(target_app="com.mobile.brasiltvmobile", mode="continuous", consecutive_no_ad=3, max_duration=20.0))

## [page] home, [action] click, [comment] 直接找到 searchbtn, 找到指定的节目名称: 点击搜索按钮进入搜索页面
poco(resourceId="com.mobile.brasiltvmobile:id/mVodImageSearch").click()
# poco.agent.hierarchy.dumper.invalidate_cache()

## [page] search, [action] input, [comment] 使用增强版 set_text, 自动校验是否成功输入, 若非则会日志 + res_for_set 有 warnning 字样
sleep(0.5)
# 现在set_text会自动刷新缓存并返回实际文本
# 注意: 点击搜索后，text属性会从占位符变成实际内容，所以只使用resourceId定位
res_for_set = poco(resourceId="com.mobile.brasiltvmobile:id/searchEt").set_text(program_name)
# 备用方案: res_for_set = poco(class_name="android.widget.EditText").set_text("西语手机端720资源02")

## [page] search, [action] click, [comment] Enter 执行搜索操作
keyevent('ENTER')
## [page] search, [action] click, [comment] 点击搜索按钮执行搜索操作---Fallback, 当成功输入内容后 searchCancel 可作为执行搜索按钮使用
## poco(resourceId="com.mobile.brasiltvmobile:id/searchCancel").click()

sleep(1)
## [page] search_result, [action] click, [comment] 双层约束, text 可能存在相同的, 但是 PosterName 名称约束后基本很少, click_with_bias 点击播放时需要使用固定传值 dy_px=-150
poco(resourceId="com.mobile.brasiltvmobile:id/mPosterName", text=program_name).click_with_bias(dy_px=-150)

## [page] vod_playing_detail, [action] click, [comment] 点击播放按钮开始播放视频（播放态下会自动唤起控件，无需手动点屏幕）
poco(resourceId="com.mobile.brasiltvmobile:id/mPlayPauseIcon").click()

## [page] vod_playing_detail, [action] wait, [comment] 通常都会有广告, 等待广告播放完毕
poco(text="Ads").wait_for_disappearance(timeout=10)
sleep(2)

## [page] vod_playing_detail, [action] click, [comment] 点击全屏按钮进入全屏播放模式
poco(resourceId="com.mobile.brasiltvmobile:id/mImageFullScreen").click()




# [page] playing, [action] assert, [comment] 断言验证节目正在正常播放
# there is assert program are already playing 
# ....

# teardown_hook()
# 这里会放置一些测之前的必要条件 






# -------------
# commente to get a position and click
#x, y = poco("com.mobile.brasiltvmobile:id/mVodImageSearch").get_position()
# Click at those coordinates 
#poco.click([x, y])

