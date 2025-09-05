[TOC]

# why onlyTest(仅写一次测试)
使用 airtest 能很快的写出一份 APK 的自动化用例, 为什么还要花时间来打造这样一个自动化测试框架
对我们而言有用的 UI 自动化用例至少要能跨 apk 测试. 可即使能写出一份, 难道那么多份都要手动写吗.
这样写出来的用例不具备通用性, Airtest 有 Poco(元素 ID) 视觉 两种识别模式, 即使完全使用 Poco 定位 也会遇到跨 apk 时元素 name 改变后无法准确定位的问题.





UI 定位的缺陷
1.无法跨设备
2.无法跨 apk
更无法跨越 TV 与 手机



## 框架
框架采取 XML 元素定位, 加 视觉 LLM 模式专攻播放页的 icon 识别,



### Omniparser icon 识别
经过专对播放页的微调


### 

### 测什么
1.媒资播放. 多种格式媒资兼容-点播. 
2.主要操作 切播放器

### testcase
检查不同格式媒资能否播放
fmp4 
mp4 H264, H265
ts 

检查音频格式能否成功播放
aac


拖动
切音轨, 清晰度, 播放器


---------

## airtest
不支持数据驱动, 需结合 python code, 当前考虑使用某个框架的数据驱动, 实现根据数据量执行脚本
数据驱动的用例执行
数据驱动的节点更新


想法: 如果使用 airtest 作为框架, 可以在具有基础代码后利用 LLM + omniparser 自动生成 code
- 文本相似度提取相关 key, 按照高置信度点击, 若下一页不为期望的则返回上一页点击下一个, 若没有则手机信息停止任务


直接通过 LLM 去执行测试用例可信度依旧不高, 而如果只是生成, 执行时依旧是固定的 code

SDK 的事的先不急, 先把框架搭好后再干后期建设的事情


![](http://showdoc.cloudstream.com:4999/server/index.php?s=/api/attachment/visitFile&sign=ec6c20cc8fcedfb5a34140ccf6554001)




### 用例文件 metadata
```
some metadata
[tag] 用以分类, 限制为: search, login, signup, live, vod, playing, subtitle, chain, other
[page] search, login, signup, live, vod, vod playing detail(click program in vod go to vod playing detail), playing(click play button in vod playing detail), subtitle
[action] click/tap swipe 
[comment] 

```

1.路径, 文件最开头书写当前文件用例的执行路径. 
- 示例: `[tag] search. [page] home, [action] click searchbtn. [page] input search content, [action] input program name.[page] input search content, [action] click searchcancle to search. [page] search result, action: click program to play. [page] playing detail, [action] click play button to play `

2.使用 `## ` 后方跟当前步骤的详细解释. 
- 示例: `## [page] input search content, [comment] click search button-either cancel search button, judge by input box have conten or not `




### 前置条件
~~SDK 支持在被启动时访问策略服务器, 获取是否启动 server 开关, 策略服务器支持动态修改策略, 达到只针对测试机器开启~~

Deeplink: 通过 APP 的 URL Schema 拉取指定页面, 减少执行路径. 比如 unimob:xxx/xxx/favorite 调起收藏 page
Mock 数据: 
- 1.本地数据修改之.数据共享: 修改 app 本地 DB, 数据文件, 可能得方式: 1).SDK 修改  2).另一个伴生 app 修改(要求 - 测试, 被测 APK 签名一致 - 指定相同 SharedUserId )
- 2.VPN 转发请求. service 录制网络数据进行回放

![](http://showdoc.cloudstream.com:4999/server/index.php?s=/api/attachment/visitFile&sign=870c8bf8a47f887c9254a59b5d178279)

**减少步骤的意义: 缩短测试时间, 减少未知风险. 但也要考虑收益比**

![](http://showdoc.cloudstream.com:4999/server/index.php?s=/api/attachment/visitFile&sign=b069ae839ac19b23ab9a48e913379e30)


### 用例执行
不仅仅依靠一种识别方式, 
增加Icon识别功能： 尽管当前基于文本检测和相对坐标定位的解决方案已能应对多数测试场景，但仍存在控件覆盖不全的问题。通过增加Icon识别能力进一步提升用户体验。


### 异常恢复能力
- 支持系统弹窗后关闭
- 支持应用内广告关闭
 > 视频广告

- 支持路径异常后恢复

- 未知弹窗/异常,  初始化环境后重新执行当前用例


## 断言

### Get element
Get_id_by_coordinate()
Get_xpath_by_coordinate()


### check

check_is_playing()
- check_screenshot_similarity(screenshot1, screenshot2 ,Threshold: float=0.9) return True, Flase
- check_has_audio()

check_content_similarity(text1: str,text2: str ,Threshold: float=0.9) return True, Flase
check_content_language_by_screenshot()
check_content_language_by_content()

check_is_crash()

fallback()

translate_to_eng()



### popup
close_popup()
is_popup() return True or False

popup_watcher(interval: float) # 独立 timer 运行, 监测是否有弹窗, 出现时自动关闭, 设置 interval 用于监测周期


### Log
record_log(log_file_name: str = format device_name + cureent_time )
- start_record_log()
- stop_record_log()

extract_apk_report(report_log_file_name: str)

take_screenshot(screenshot_name: str: =random_string + cureent_time)
take_screenshot_by_bbox(screenshot_name: str: =random_string + cureent_time, coordinate)

get_click_coordinate_by_bbox(bbox: List[float], screen_width: int = 1920, screen_height: int = 1080) -> Tuple[int, int]:

bbox_to_co



## 回放报告
![](http://showdoc.cloudstream.com:4999/server/index.php?s=/api/attachment/visitFile&sign=986b85271e8e7f3b74cf1c06272a505c)

## 更新篇

### 训练模型
- 训练 YOLO 识别模型识别自有 apk 图标划分能力, Banner、menus、tabs、input 的识别
	>  使用 YOLOX 为底, 或者 Omniparser 原始 YOLO 模型. 之后利用 Omni 输出所有图片的标注后图后手动矫正训练数据
- 训练 LLM Agent 处理能力, 提高定位目标的准确率

### 收集数据

- 收集用例执行结果数据, 计算失败比
- 支持用户更新失败原因, 增加下次用例执行准确度




## airtest use
```
pip install airtest
pip install pocoui
```


### env
```sh
device_id=192.168.100.123
app_id=com.integration.unitvsiptv


```



## uni

逻辑
1.根据这些信息查找 folder, `{MD5Hash(app_id, )[:5]}_{ro.product.model}_{app_id}`
2.对比分辨率是否一致, 不一致时 只使用 poco id 匹配, 匹配不到时重录(旧文件备份, 写新 json 文件), 不尝试图片匹配(分辨率变化后图片匹配不再成功)
3.若同设备+同分辨率+同 appid 代表用例可复用, 通过 poco_id 


### json 组成

file_name: `{device_id}_{app_id}_{time} `
file content: 

```json
{
"resolution": "1920*1080"
"app_id": "com.integration.unitvsiptv",
"app_ver": "30201",
"device_info": "H96_Max_V11",
"android_ver": "11"
"{action1}": {
  "poco_identical_selection": "resourceId or text....", 
  "image_path": "imags/{file_name}/action1.png", 
  "pos": [0.2078125, 0.17916666666666667],
  "poco_metadata": [#     type :  android.widget.TextView 
#     name :  com.integration.unitvsiptv:id/mTextTitle 
#     text :  FEATURED 
#     enabled :  True 
#     visible :  True 
#     checkable :  False 
#     pos :  [0.2078125, 0.17916666666666667] 
#     resourceId :  b'com.integration.unitvsiptv:id/mTextTitle' 
#     scrollable :  False 
#     boundsInParent :  [0.1015625, 0.0625] 
#     selected :  True 
#     anchorPoint :  [0.5, 0.5] 
#     size :  [0.1015625, 0.05694444444444444] 
#     zOrders :  {'global': 0, 'local': 1} 
#     editalbe :  False 
#     checked :  False 
#     focused :  False 
#     touchable :  False 
#     package :  b'com.integration.unitvsiptv' 
#     scale :  [1, 1] 
#     dismissable :  False 
#     longClickable :  False 
#     focusable :  False 
],
  },
  
"{action2}": {
  "poco_identical_id": "", 
  "image_path": "imags/{file_name}/action2.png", 
  "pos": "",
  "poco_metadata": 
 }
}
```




对比
![](http://showdoc.cloudstream.com:4999/server/index.php?s=/api/attachment/visitFile&sign=b076db2d9bbd4e2e58d680ef925f21bf)





## 降低错误率之路
分 step, 减少排错难度

### 为什么不是直接输入一句话来执行任务
制造一个 phone_use (= Phone_mcp + omniparser 结合) 的自动执行输入的自然语言, 达到使用自然语言控制 Android 行为的一种方式
传统的 Computer use(指使用 LLM + windows 屏幕识别的方式) 方式, 如果输入是一个需要很多操作步骤才能获取结果的操作, 完成率很低, 这也是为什么这类应用目前还没有变的更加流行的原因(magma)

而对于测试用例来说这个操作长短都存在, 为了提高执行的稳定性, 无法像 computer use 一样希望仅输入简短的一段话就能实现一系列操作. 预想一个最简单的输入示例: 1.get current foucus pkg name 2.clear cache and restart . 明确要执行哪些步骤才能稳定执行输入的操作. 而更进阶的用例方式则是更加定制化的输入 参照 `/用例文件 metadata`, 这些内容后期规划作为训练数据, 帮助 LLM 能更加熟悉我们产品而提升执行质量, 降低错误率


## AI 驱动的 UI 自动化测试
随着技术发展, 对 UI 平台自动化执行也成为了最新的研究方向, 且有部分 demo 已经初具能力, 比如 Magma-ui, AppAgentX, DroidRun, 再 比如各头部 LLM 公司开发的 Computer use 工具, 但都有一个缺点, 成功率不高, 复杂任务的完成率降低.
其大致原理是让 LLM 模拟人执行的步骤, 发出指令指挥操作, 之后根据截图或元素等信息判断下一步执行.
而自动化测试需要极度的稳定, 否则一个黑盒并且成功率不高的自动化测试只是一个烂摊子.
为了有效利用目前 LLM 的能力, 提出以下想法
1.LLM 可以辅助我们根据新用例和以前的用例范本生成新的用例
2.让 LLM 根据截图判断元素位置, 获取坐标点后更新 path, 用于兜底的场景. 

由 AI 驱动的自动化测试最终形态都应该是不变的代码, 才具有稳定与执行测试的意义

而有了 fallback 能力

## 建议
### 手机云: 
手机集群管理, 平台监控使用状态, 一个人负责启停(比如手机陷入某种异常状态). 一部分手机 POCOX3 无法通过 投屏 操控则手动操作即可.
大致设想
1.一个网站或 win 软件来实现
2.支持登录(邮箱), 支持显示使用状态, 支持预约使用时间, 支持结束使用
3.支持 session 过期自动结束使用, 支持客户手动配置是否 60m 后过期

## 工具
### packagemanage 工具:
- fetch from 39 and 37
- split by debug and release 
- support search by commit


### phone-use 工具, 支持使用自然语言操控 android 设备
说明: 从 phone_mcp 该来, 其本身使用 uiautomator dump ui 控件树来寻找元素并点击, 但有一个问题, 播放状态下 `使用adb shell uiautomator dump /sdcard/app.uix命令返回ERROR: could not get idle state`, 导致其无法应用到我们的产品上
改写后的工具使用 Omniparser 元素识别, 精准定位控件进行点击等操作
- 且支持 MCP 的方式让其能与多数大模型兼容使用. 目前依旧在精准控制上进行迭代
- 结合 Omniparser, 根据 UI 识别结果进行操作

### 需要的支持
- APK 支持指令关闭 debug 面板
- 中间件支持接口调用返回节目数据(ddebug 面板 + program name)

精准定位: 
where am i, 若需获知位置信息需要声明状态
- 可重置: 直接回到首页, 从头执行
- 不可重置: 获取当前位置 1.识别当前 focus pkg name. 2.识别 当前路径: poco path? 元素识别后的总结. 考虑到 APK 内容简单, 只使用相对路径, 简化结构




## reference 

多款自动化测试工具评测
https://blog.csdn.net/weixin_39810558/article/details/130156521

自动化测试在美团外卖的实践与落地, SDK 与架构, ViewPath + 图像 + 坐标的多重定位方案
https://cloud.tencent.com/developer/article/2113563

货拉拉App录制回放的探索与实践, SIFT算法图像匹配, 文本匹配, `am broadcast -a ADB_INPUT_B64 --es msg "xxx"` 模拟用户键盘输入, YOLOX.
https://juejin.cn/post/7306331307477794867

爱奇艺APP DIFF自动化解决方案, Deeplink, MocK 数据, 测试框架流程优化
https://juejin.cn/post/7001018350327463943

基于 AI 的移动端自动化测试框架的设计与实践, 训练
https://www.iqiyi.com/common/20190125/d5e434d41a41bdff.html

货拉拉 PaddleOCR 数据标注. 云真机多机同步探索与实践, 扩大点击区域, 系统弹窗处理
https://juejin.cn/post/7430902939316109312

Appium 使用科普
https://juejin.cn/post/6962062105105317895

反向学习, 预测, YOLOv3 weights 模型 转换 Keras 模型。
https://juejin.cn/post/6903756921602326542

UI 自动化前因后果, `通过率的定义：（成功数 / 成功+失败+跳过数 ）* 100%`
https://cloud.tencent.com/developer/article/1170543?policyId=1004

如何使用GPT-4进行UI自动化测试？---示例
https://juejin.cn/post/7365443527076282409

创建指向应用内容的深层链接
https://developer.android.com/training/app-links/deep-linking?hl=zh-cn

Pix2Code 根据截图生成稳定的一套视图树。目前感觉不够多层保障靠谱
https://www.iqiyi.com/common/20190125/d5e434d41a41bdff.html

自动化测试原则
https://cloud.tencent.com/developer/article/1471454?policyId=1004

批评自动化测试方式	
https://cloud.tencent.com/developer/article/1552159?policyId=1004

云端 IDE, 设备全局控制思路, APP管理安装工具
https://juejin.cn/post/6945729335080779806?from=search-suggest

多语言, 时间等断言判定, 训练 LLM 进行识别
https://juejin.cn/post/7316540469320597539

vivo 流量录制回放, 月光宝盒
https://juejin.cn/post/7064757558812246053?from=search-suggest

全链路压测自动化的探索与实践
https://juejin.cn/post/7360512664316936226?from=search-suggest

Airtest 使用
https://www.cnblogs.com/sdcjc/p/14583847.html

货拉拉流量回放方案
https://juejin.cn/post/7373577112220483593#heading-15

投入产出数据
https://juejin.cn/post/7376231612440887335?searchId=202506261757192F23FCC72B90D724440E#heading-13

货拉拉精选文章 index
https://juejin.cn/post/7315850963343360039?from=search-suggest

ava 直播流异常检测
http://showdoc.cloudstream.com:4999/web/#/2/14876


https://github.com/Westlake-AGI-Lab/AppAgentX
https://github.com/microsoft/OmniParser
https://github.com/droidrun/droidrun
https://huggingface.co/spaces/microsoft/Magma-UI
https://github.com/browser-use/workflow-use

货拉拉云真机平台的演进与实践	
https://juejin.cn/post/7217851001087803453

基于图像识别框架Airtest的Windows项目自动化测试实践
https://cloud.tencent.com/developer/article/2161557?policyId=1004

---

问答形式

### DOM 树是什么
DOM（Document Object Model，文档对象模型）是一种跨平台、语言无关的 API，用于表示 HTML 或 XML 文档的树状结构。DOM 树将文档分解为一个由节点组成的层次结构，其中每个节点代表文档的一部分（如元素、属性、文本内容）。根节点是整个文档，子节点可以是元素、文本或属性，元素节点可以包含其他子节点，形成树状结构。

在 Android 自动化测试的上下文中，DOM 树的概念被借用到 UI 层次结构中。Android 应用的 UI 控件树类似于 DOM 树，每个控件（如按钮、文本框）是一个节点，节点之间通过父子关系组织起来。Uiautomator2 通过解析这种 UI 树（通常以 XML 格式表示）来实现元素定位，XPath 就是基于这种树状结构进行路径查询的工具。
https://www.perplexity.ai/search/uiautomator2-dui-bi-airtest-po-BwHL1_CHTTKK2W67Vz2uMA




无论如何, android 测试都离不开 UI click 驱动
对于底层就是元素识别

结论: 
即使使用数据训练得出的也是是个小一号的 omniparser, 具体还是没什么应用场景

Omniparser
专用于电脑的图标识别工具, Microsoft 打造的原因也是辅助 Agent 进行 windows U 操作, 提高识别准确率, 降低计算延迟. 
目前还不是可商用程度, 识别慢, 准确率勉强够用的水平

YOLO
物体检测, 框出比如 person, bed 等物体, 并给出位置, 置信度等数据

最新稳定 v11 版本
v12 基于 attention, 不好安装. 据介绍实时检测效果好


https://www.reddit.com/r/LocalLLaMA/comments/1itbszy/new_yolo_model_yolov12/
YOLO 目前基本上是一个通用术语。原作者 Joseph Redmon 创建的最后一个版本是 YOLOv3。此后，YOLO 的开发工作都由不同的研究人员团队进行。每当有人认为自己提出了改进方案，他们就会将其发布为下一个 Yolo 版本。这也是为什么过去几年 YOLO 发布了如此多版本的原因之一。其中大多数版本在实际应用中的改进程度尚有争议。



### 为什么需要这个 SDK， 如果不做这个 SDK 需要做多少冗余工作， 两者对比哪个更好

<table><tbody><tr><td><p><strong><span class="selected">对比维度</span></strong></p></td><td><p><strong><span class="selected">方案一：传统黑盒自动化 (无SDK)</span></strong></p></td><td><p><strong><span class="selected">方案二：白盒测试SDK方案</span></strong></p></td></tr><tr><td><p><strong><span class="selected">前置条件准备</span></strong><span class="selected">(登录/数据)</span></p></td><td><p><span class="selected">❌ </span><strong><span class="selected">繁琐且脆弱</span></strong><span class="selected">- </span><strong><span class="selected">登录</span></strong><span class="selected">: 依赖UI模拟输入，速度慢，对界面改动敏感。- </span><strong><span class="selected">数据</span></strong><span class="selected">: 强依赖后端真实数据，或需</span><strong><span class="selected">额外搭建和维护Mock服务器</span></strong><span class="selected">。</span></p></td><td><p><span class="selected">✅ </span><strong><span class="selected">精准高效</span></strong><span class="selected">- </span><strong><span class="selected">登录</span></strong><span class="selected">: 通过指令</span><strong><span class="selected">瞬间注入</span></strong><span class="selected">任意身份凭证(Token)。- </span><strong><span class="selected">数据</span></strong><span class="selected">: 在App</span><strong><span class="selected">内部拦截</span></strong><span class="selected">并伪造网络响应，无需外部依赖。</span></p></td></tr><tr><td><p><strong><span class="selected">核心权限测试</span></strong><span class="selected">(门户/栏目)</span></p></td><td><p><span class="selected">❌ </span><strong><span class="selected">几乎无法实现</span></strong><span class="selected">- 难以伪造</span><strong><span class="selected">全链路</span></strong><span class="selected">数据（门户→栏目→媒资），通不过后台校验。</span></p></td><td><p><span class="selected">✅ </span><strong><span class="selected">轻松胜任</span></strong><span class="selected">- 通过指令链，可同时伪造多个关联接口，</span><strong><span class="selected">完美保障数据一致性</span></strong><span class="selected">。</span></p></td></tr><tr><td><p><strong><span class="selected">应对DRM限制</span></strong><span class="selected">(TV端无法截图)</span></p></td><td><p><span class="selected">❌ </span><strong><span class="selected">完全失效</span></strong><span class="selected">- 无法通过截图/录屏验证播放画面，自动化测试</span><strong><span class="selected">链路中断</span></strong><span class="selected">，退化为人工监控。</span></p></td><td><p><span class="selected">✅ </span><strong><span class="selected">绕过限制</span></strong><span class="selected">- 无需“看见”画面，直接</span><strong><span class="selected">查询播放器内核状态</span></strong><span class="selected">（如帧率、缓冲、错误码）来断言结果。</span></p></td></tr><tr><td><p><strong><span class="selected">异常场景模拟</span></strong><span class="selected">(网络错误/超时)</span></p></td><td><p><span class="selected">❌ </span><strong><span class="selected">困难且不稳定</span></strong><span class="selected">- 依赖操作手机网络或外部工具，难以精确、稳定地复现。</span></p></td><td><p><span class="selected">✅ </span><strong><span class="selected">稳定可控</span></strong><span class="selected">- 一条指令即可让App</span><strong><span class="selected">精准模拟</span></strong><span class="selected">任何网络错误，稳定测试异常处理逻辑。</span></p></td></tr><tr><td><p><strong><span class="selected">稳定性与维护</span></strong></p></td><td><p><span class="selected">❌ </span><strong><span class="selected">低稳定性，高维护成本</span></strong><span class="selected">- 测试脚本与UI强耦合，界面稍有改动即需修复，</span><strong><span class="selected">极其脆弱</span></strong><span class="selected">。</span></p></td><td><p><span class="selected">✅ </span><strong><span class="selected">高稳定性，低维护成本</span></strong><span class="selected">- 测试逻辑与UI解耦，只要核心业务不变，</span><strong><span class="selected">脚本可长期复用</span></strong><span class="selected">。</span></p></td></tr><tr><td><p><strong><span class="selected">执行效率</span></strong></p></td><td><p><span class="selected">🐌 </span><strong><span class="selected">缓慢</span></strong><span class="selected">- 大量时间耗费在UI渲染、动画和等待上。</span></p></td><td><p><span class="selected">🚀 </span><strong><span class="selected">极速</span></strong><span class="selected">- 基于内存和函数调用，执行效率通常有</span><strong><span class="selected">数量级</span></strong><span class="selected">的提升。</span></p></td></tr><tr><td><p><strong><span class="selected">投入成本</span></strong></p></td><td><p><span class="selected">📉 </span><strong><span class="selected">初期投入低</span></strong><span class="selected">- 可直接使用开源框架。</span></p></td><td><p><span class="selected">📈 </span><strong><span class="selected">初期投入高</span></strong><span class="selected">- 需要投入研发资源进行SDK的设计与开发。</span></p></td></tr><tr><td><p><strong><span class="selected">结论</span></strong></p></td><td><p><span class="selected">💼 </span><strong><span class="selected">短期捷径，长期技术负债</span></strong></p></td><td><p><span class="selected">💎 </span><strong><span class="selected">前期投资，长期核心资产</span></strong></p></td></tr></tbody></table>






## 思考

监测是否是首页
1.Home 界面一般只有一个动态栏目, 在首页停留 3s 前后截图两张后对比变化区域, 去掉变化区域即是 Home page image, 作为一个 断言依据

`poco(text="知乎").click()`
方式是否可用, 考虑到多语言
常见的基本上不会变化的属性包含但不限于：name type resourceId package。


alphaTest = airtest + appium, 录制操作后根据. 三大定位方法 ViewPath + 图像 + 录制时坐标(同机)

is palying on TV: 媒资保护如何解决
is palying on android: 图像对比 + 音频采集





# 影视类 APP 自动化测试构思
如何开展 mobile 和 tv 都适配的自动化测试

按断言项对要进行自动化测试的内容分以下几类
- 1.辅助断言, 根据 ranger 面板信息，断言操作结果。 比如卡顿， 切源都是现有的可断言项. 可验证操作是否正常执行
- 2.依赖人员实施监控的 UI 操作， 比如拖动/播放/且播放器等操作， 需要人员监控视频播放正常
- 3.自 ... 版本后接管了激活/获取栏目等接口， 除了在服务器对这些接口测试外， 还需要在 apk 上对这些接口进行自动化测试
- 日志上报测试, 对比 apk 上报的日志与实际操作

方法:
1.SDK
2.mock server
3.get element location
4.UI identify


**难点：**
高版本 TV 有媒资保护， 截屏投屏等操作被禁止， 无法看到媒资画面



**探讨：**
SDK 级别的前置数据手法， 是否可以实现？



**测试方法：**
白盒测试：从代码层面进行测试， 通过获取 SDK 调用信息， 之后判断调用是否正常
黑盒测试：从 UI 层面进行测试， 播放后测试人员观测测试结果确认播放正常， 判断用例结果




**查询： **
1.是否能获取页面元素返回， 根据坐标 click， 提升精准度, - droidrun


### 前置条件解析：
能做什么
- 1.拦截登录请求自动获取认证信息
- 2.拦截业务请求, 固定返回指定点播数据, 方便进行数据准备

```
具体操作构思
1.启动: Debug APK 启动，自动初始化SDK。
2.监听: SDK启动一个后台服务器，等待指令。
3.指令: 测试脚本发送“拦截登录”指令。
4.拦截: App调用登录功能的.so库时，SDK的Hook被触发。
5.伪造: SDK中断了对.so的真实调用，直接返回一个预设好的（内置的）Token。
结果: App拿到Token，完成“伪登录”，进入内置账号的登录态。
```

困难： 后台校验了用户所属门户， 若伪造了门户栏目数据， 则往后的播放数据都需要伪造




### 补充
**portal 门户， 栏目权限分析**
关系-- 1门户： 多栏目， 1栏目： 多媒资
门户有对应葡语，英语门户， 根据策略划分用户所在门户， 策略有 SN， 用户语言等（比如 YC 旧根据语言来切换门户）相同 uid 能请求不同门户的栏目时对方属于这个 appid
有一个通用栏目的属性， 若 portal 能查到用户请求的门户关联的通用门户则可访问媒资数据。


### 问题
uiautomator 不支持在视频播放状态获取 xml(poco 底层使用它因此也无法工作). uiautomator2 能获取, 但是播放状态下获取不到控件和播放相关信息, 有作用的只有面板的数据, 但是项目本身希望能通过 ranger API 获取 debug 等验证信息
- poco dump 元素在 mobile 似乎有些问题, 导致自动小屏, 获取不到播放页(暂停播放状态元素). 考虑到兼容问题, 完全使用 uiautomator2 获取元素, 并采用 poco 计算 pos 的方法用于传递参数
```
https://stackoverflow.com/questions/33807604/how-to-check-if-video-player-is-launched-in-appium
How to check if video player is launched in appium

Timer is one option - Check if the timer loads and its greater than 0:00. Second option is to check for sound. If sound is being played, it means that video is loaded. Use dumpsys command to check sound status.
```

新的 apk 支持粗浅的判断播放状态, 比如 播放器使用, 或者 isMusicActive. 
- 支持使用 `adb shell am start -n com.github.metacubex.clash.meta/com.github.kr328.clash.ExternalControlActivity -a com.github.metacubex.clash.meta.action.START_CLASH` 方式获取鉴定结果
- 支持通过 API 获取状态检测结果

```
https://developer.android.com/reference/android/media/AudioManager.html#isMusicActive()
AudioManager.isMusicActive();

and for video , The SurfaceFlinger process can know that it is receiving frames at a consistent rate, but it can't know if it's a video or just app animation.
```


问题核心：
- Poco的dump逻辑存在bug，原始XML包含完整package信息，但经过Poco处理后package统计为空{}
- UIAutomator2可正确提取95个com.unitvnet.mobs节点，但Poco层丢失了所有package信息

解决方案：
创建pure_uiautomator2_extractor.py新模块，直接处理 UIAutomator2 XML，完全绕过Poco的有问题dump逻辑。

新方式优势：
1. 100%保留package信息 - 成功提取所有目标节点
2. 属性真实性保证 - 用特殊值(-9999, -8888.8888)标记代码默认值vs XML原生值
3. 完全独立 - 不依赖有bug的Poco中间层
4. 性能优异 - 直接XML解析，无数据丢失






UiAutomator 运行后 再启动 UiAutomator2 会报错, 貌似不能同时使用.
UiAutomator findObject is throwing IllegalStateException: UiAutomation not connected!
Possible workaround is restarting adb before the test run with adb kill-server; adb start-server. That worked for me on another project.

----------


# Task
- 完成 phone-use mcp 工具编写, 增强其通用能力, 支持使用 UIAutomator2 identify by resourceId 模式, 与 Omniparser 识别模式共同协作
- Omniparser 进一步微调, 方向: 播放页微调优化, 增加其识别正确率, 扩展 YOLO 识别的 icon 区域类型
- 完善文档, 包括具体模块的文档
- Airetest IDE 打包, Poco 底层改为使用 uiautomator2 方式. 





