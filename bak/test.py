import uiautomator2 as u2
import time
# print(1)
# 连接到设备
device = u2.connect()
print(device)
# 获取当前界面的 XML
xml = device.dump_hierarchy()
# print(xml)
# 将 XML 保存到文件
with open('screen_dump.xml', 'w', encoding='utf-8') as f:
    f.write(xml)
