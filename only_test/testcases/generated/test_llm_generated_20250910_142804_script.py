# 测试vod点播播放正常: 1.进入APK后就是首页，执行关闭广告函数，2.找到searchbtn点击，直到可输入状态后输入节目名称'720'点击第一个节目，3.播放节目，断言: 验证设备是否处于播放状态
# [tag] 
# [path] 

from only_test.core.api import *
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

# connect_device("android://127.0.0.1:5037/DEVICE?touch_method=ADBTOUCH&")  # 使用 airtest run --device 传入或在此填写
poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)

## [page] unknown, [action] launch, [comment] 
start_app("com.example.app")
sleep(None)

## [page] unknown, [action] click, [comment] 
try:
poco(text="None").click()
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    # 重试逻辑可在此添加

## [page] unknown, [action] click, [comment] 
try:
poco(text="None").click()
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    # 重试逻辑可在此添加

## [page] unknown, [action] wait, [comment] 
sleep(None)

## [page] unknown, [action] input, [comment] 
try:
poco("input").click()
sleep(0.5)
text("")
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    # 重试逻辑可在此添加

## [page] unknown, [action] wait, [comment] 
sleep(None)

## [page] unknown, [action] click, [comment] 
try:
poco(text="None").click()
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    # 重试逻辑可在此添加

## [page] unknown, [action] wait, [comment] 
sleep(None)

## [page] unknown, [action] click, [comment] 
try:
poco(text="None").click()
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    # 重试逻辑可在此添加

## [page] unknown, [action] assert, [comment] 
assert poco(text="None").exists(), "文本 'None' 未找到"


# 测试用例执行完成
# TODO: 添加结果验证和清理代码
