# 测试vod点播播放正常: 关闭广告→搜索→点击首个结果→播放并断言
# [tag] 
# [path] 

from only_test.core.api import *
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

# connect_device("android://127.0.0.1:5037/DEVICE?touch_method=ADBTOUCH&")  # 使用 airtest run --device 传入或在此填写
poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)

## [page] unknown, [action] launch, [comment] 
start_app("com.mobile.brasiltvmobile")
sleep(10.0)

## [page] unknown, [action] wait, [comment] 
sleep(10.0)

## [page] unknown, [action] click, [comment] 
try:
poco(text="None").click()
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    # 重试逻辑可在此添加

## [page] unknown, [action] wait, [comment] 
sleep(10.0)

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
sleep(10.0)

## [page] unknown, [action] click, [comment] 
try:
poco(text="None").click()
except Exception as e:
    logger.warning(f"操作失败，重试中: {e}")
    sleep(1)
    # 重试逻辑可在此添加

## [page] unknown, [action] wait, [comment] 
sleep(10.0)

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
