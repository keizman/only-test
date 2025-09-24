丢失

一部分写的很好, 但我想补充一些内容, # ## page: search pgae, comment: click search button-either cancel search button, judge by box have conten or not . 这时用例文件里写的, 为什么需要它, 他是否 LLM 或
  人一眼就能看到要做什么呢, 如果有更加多的 meatadata 元信息写在 用例文件会使生成用例是一个极其简单的事情, 这就是我再 README 中定义各种 meata tag 等信息的意义. 请你考虑好如何将哪些信息结合到 用例文件中,
  这一一个需要深度思考的步骤 .C:\Download\git\uni\airtest\untitled.air\untitled.py  2.在 airtest 目录下创建一个目录结构, 它将是有 部分的 phone-use 代码(用来获取屏幕信息函等, 作为lib,)
  你需要做的是先定义好目录结构, 这个过程我会不断提醒你 我们打造一个更好的测试框架
  
我还希望你能思考: json 只是一个媒介, 用来统计用例, 之后要生成 Py 也是作为用例文件
  我的想法 为什么需要json,: 1.统计用例信息, 比如用例 meta 信息, 生成的截图信息等
  为什么需要 py 最终用例文件: 这个用例可能需要特殊的 func, py 更加灵活, 并且执行和生成报告等会使用 airtest+pytest+allure 结合的方式, 我们不可能打造全新的框架, 也没必要,
  因此我希望你好好想想他们的协作模式. 比如: json 转 py? 在执行用例前使用自写工具将我们定义的数据转为 py 代码后使用 airtest 执行. 这是一个参考, 你可以思考更多方式且不局限.
  
 完善后输出这个工作流程, 我需要通俗的给他人讲解这个项目是如何工作的, 工作流程:
  1.新的 apk 新的用例, 输入一个测试点, LLM 生成用例先假设为 json 文件
  2.试跑, 此时更新设备探测道德信息到 json. 比如设备清晰度 android 版本等, 之后开始run 用例
  3.run 用例的同时因为可能用的到 视觉识别, 因此图片等信息, 以及识别到的信息需要保留好, 以相对路径方式写在 json 子 item 中, 相对路径以 pkg name 和 phone name 方便区分, 具体区分规则有 README 有写
  4.
  
  
  
好的, 我们先着手完善 视觉与元素识别系统, 实际他是一个写完并验证的系统, 具体规则你可读取 /phone-use 目录, 它使用 fallback 模式进行不同界面的元素识别(只需要发送一个消息即可获取结果), 但对外部来说是无感的,
  我们这里也要支持动态切换策略(根据播放状态), 先检查 airtest/lib 下是否存在相关逻辑, 迁移到你希望的地方, 如果没有请从 phone-use 迁移过来, 这是独立不同的项目, 你也需要确保新功能狗简洁,
  同时你需思考下如何让别人明显知道你已经实现了这个功能且实现思路, 即使这不是你的原创, 记录好以便你的后 LLM 熟练掌握全局
  

请对每点再详细一些, 有一些步骤需要将配置信息回写到 yaml 或 json , 比如 分辨率信息, 场景是, 这方面我还不清楚是怎么实现的, 请你清晰的米描述流程, 注意越详细越好, 但要足够简洁, 避免冗余


----

1.检查当前的 omniparser 输出结果是什么 ,我看到其它地方直接使用 json 了, 你可以送这张可用图过去实验世界结构, 验证当前结构是如设想"C:\Download\git\uni\zdep_OmniParser-v2-finetune\imgs\yc_vod_playing_fullscreen.png" 
2.很多注释或说明的功能是与当前项目无关的 比如 在抖音中搜索'美食视频'，如果搜索框有内容先清空, 请再遇到这些内容更改为测试 com.mobile.brasiltvmobile 的播放功能, 等, 避免引起后人对其疑惑
2.实验 MCP 功能, 尝试发送消息到 LLM, 确认其可用, 之后确认如何与我们创建的 MCP 进行交互, 你可以 mock 一段内容, 来进行尝试
3.最终那个目的是成功生成一个用例, 指定好 plan 后开始work, 注意, 不是你来生成,  而是模拟人一样使用另一个 LLM 来生成一个用例, 这才是这个项目的意义所在

---------



你好像误解了我的意思, 而且生成用例太复杂,  并且这应该也是你自己生成的把. uni\airtest\testcases\python\example_airtest_record.py 这就是一个标准用例的书写格式, 最终 json 会转为这种, json 中的 path 主要是为了记录, 而最终的 py 文件就是要如此简单用于执行用例测试,. 
流程控制,你应该也注意到 用例文件中是一步一步的执行的,而你也要要知道, 这个项目的作用就是让 LLM 根据已有用例 辅助生成新的功能点用例,问题只是其中的  com.mobile.brasiltvmobile:id/mImageFullScreen 或者 type anyway 这种控件名不好找, 因此需要 LLM 根据这一步, 比如当前要搜索, 那它需要找到搜索的 id/name 等元素信息记录到 json,  一步步的完成后比如全屏播放了, 此时结束任务. 我感觉你在做的内容一直是模糊不清的, 你有任务问题请问我, 因为我不知道你卡再哪一步. 这次我需要你先反思, 并把你的 plan 给我, 我修改并予以批准后再开始



  1. 当前问题定位
    - 控件名通过人工找到或录制太费时间, 让 外部 LLM 使用 MCP 监控屏幕或操纵屏幕 获取当前控件状态（如 com.mobile.brasiltvmobile:id/mImageFullScreen）之后记录操作到 json 

  1. 标准用例格式确认
    - example_airtest_record.py 是唯一的标准格式吗？ 是的, 他是最终用例的执行格式, 其内部也需要包含这种声明(## [page] vod_playing_detail, [action] click, [comment] 点击全屏按钮进入全屏播放模式). 但是 setup_hook 等可能会有额外的执行函数, 这是辅助项, 最终用例一定是 airtest 认可的这种格式, 它也是简介的用法. 你之前写的太复杂, 任何一个人都会否决你的用例文件
    - 有其他参考用例格式吗？无, 你可以先从用例文件 example_airtest_record.py 反推出一个 json 我会检查是否正确与符合要求, 以明确 用例标准格式 
  2. LLM的具体作用范围
    - 是否只负责元素识别和定位？
    - 还是还包括测试逻辑的规划？
    两者, 其需要自驱动的理解好我提供的测试功能点, 之后一步步的捕获屏幕 ID 并写一个 json 用例. 
  3. JSON结构定义
    - JSON中需要记录哪些具体信息？
    - path字段的具体作用是什么？ *path* 主要记录这个记录生成时 LLM 使用工具生成的结果, 你应该能想明白为什么需要记录对吗, 补充他. testcases\generated\tc_com_ss_android_ugc_aweme_20250905_184738.json  这里有一个之前自动生成的内容,但是它是不符合要求的, 你需要反推后生成一个符合要求的内容
  4. 目标应用和功能
    - 当前主要针对 com.mobile.brasiltvmobile 应用？ 是的, 我们目前的目标是打造框架后使用现有框架 only-test 写一个用例
    - 主要测试哪些功能点（搜索、播放、全屏等）？ 目前要测
  5. 现有工具集成
    - Omniparser的识别结果如何与LLM结合？ 这个问题你需要先了解 uiautomator2 是如何工作的, 他是直接对当前 android 界面元素做 captrue 之后计算详细位置对吗, 之后你可以尝试请求 Omniparser 获取其结果, 其有两个重要信息, content 和 bbox, 你应该知道这些是什么, 而剩下的内容可以解决你的疑惑, 模式:  dumo_ui + omniparser 模式
作用: dump_ui 使用 uiautomator2 , 即使如此, 在使用 APK 播放状态依旧无法获取界面控件布局, 只有当暂停播放视频时才可以, 此时需要 omniparser 进行基于 AI 的 UI 视觉识别, 其能感知当前屏幕的 app 空间位置, 之后, 返回给外部 LLM 的是与 Dump_ui 一样的元素位置等详细信息, 使用者并不知道两者的区别 只需要关注空间是否成功点击, 达成操控目的. 
既然  uiautomator2 有问题为什么不全部使用 omniparser: omniparser 识别速度没有 uiautomator2 快, 准确率 90%, 即使如此也有错误率, 其使用 GPU 资源消耗

下一步, 对于外部 LLM 而言其不需要知道内部逻辑, 因此code 需要自动根据当前播放状态来确认使用哪个进行屏幕识别, 比如可以通过当前媒体播放状态, 音频使用状态, player 使用状态来确认播放状态, 之后使用正确的识别模式, 精准切换

    - MCP工具在这个流程中的具体作用？ MCP 是为了让外部 LLM 主动capture 当前屏幕, 并 filter 其需要的内容, 获取 id 等控件信息后其才能正常确认控件 ID 等信息, 才能写用例, 对吗


我需要你做这些事情
1.反推 json 文件
2.补充我们的问题记录后记录到 QA.md 之后生成更多问题, 以及你的猜想, 我来检查, 并可能会纠正你的猜想, 我希望能通过这份文档纠正你的想法



-----



请你再生成当前 airtest 目录下的结构信息,补充每一个文件的作用到其中,我会在你补充后统一纠正
(感悟: 当 vibecoding 到迷茫怎么办, 离目标很远, 但是不知道下一步要做什么 
这就是再教导一个 mem 有限的孩童做事情, 你需要知道它的记忆有限, 因此要尽可能的简单又清晰的做好一切描述, 才能确保走在正确的路上, 否则只是原地
这个问答过程也是让你自己更了解这个项目内容的过程)

+------


1.检查当前的 omniparser 输出结果是什么 ,我看到其它地方直接使用 json 了, 你可以送这张可用图过去实验世界结构, 验证当前结构是如设想"C:\Download\git\uni\zdep_OmniParser-v2-finetune\imgs\yc_vod_playing_fullscreen.png" 
2.实验 MCP 功能, 尝试发送消息到 LLM, 确认其可用, 之后确认如何与我们创建的 MCP 进行交互, 你可以 mock 一段内容, 来进行尝试
3.最终那个目的是成功生成一个用例, 指定好 plan 后开始work, 注意, 不是你来生成,  而是模拟人一样使用另一个 LLM 来生成一个用例, 这才是这个项目的意义所在

-*--

▌你可尝试使用真实方式验证, env 中包含了 请求 LLM 的apikey , 与 URL 等信息, 你可直接接入后请求, adb 目前已链接设备 192.168.100.112:5555   device product:crux model:Mi9_Pro_5G device:crux transport_id:2 这是目前
▌的测试设备, airtest run C:\Download\git\uni\airtest\testcases\python\example_airtest_record.py  是我手动录制的文件, 也是期望的生成后的 py文件样式, 我期望的是你打通整个流程, 最终直接输入功能点生成一条用例, 如
▌果有任何不明白的请记录并问题, QA.md 是一个值得信赖的我想说的话.
还有一点重要的需要你明确, 外部 LLM 根本不知道如何生成一个用例, 不知道要做什么, 不知道如何编排使用 MCP,  请你善用C:\Download\git\uni\airtest\templates\prompts\generate_cases.py  prompt 定义和标签定义, 目前可能并不完善, 我需要你精通掌握后修改它们到最优 C:\Download\git\uni\airtest\templates\prompts\

---


▌C:\Download\git\uni\logs\test_mcp_llm_integration_20250910_103732.log 我已经执行但只有一个日志文件, 代表你并未让所有内容都输出日志, 这时我不期望的, 你一定要再做任务的过程中学会输出日志, 更容易 debug, 以及留存
▌征集, 并且 LLM 的输出也要记录, 这可以针对他们的输出针对性调整,比如其输出可能不符合期望上部署因为我们的 prompt 不够精准描述之类的问题. 请你先探查 log 确认是否正常, 之后我期望暂时去掉所有 mock 数据, 直接使用真
▌实环境, 之后详细记录生成用例过程中的日志便于分析问题, 这时请你想下哪里容易出问题, 比如 LLM 未连续调用 MCP, 无法监控屏幕, 或者 LLM 书写 json 用例内容异常等等都需要考虑好, 如果有任何问题请参展 QA.md 或者写问题
▌到其中, 我会时刻更新它, 说出我心中的项目的规划

----

接下来我希望你考虑到 yaml 文件 , 他们是什么
总控 文件, 包括设备, 配置等信息, 还有 main.yaml, 具体内容你可以参照 QA.md 


---

vibecoding 思考: 过长上下文只是自我欺骗其有 memory, 实际那些都是没用的它生成的记忆, 并且很可能已经忘了你刚开始说的话, 而且此时即使你有多个文档写好了哪件事的规范其也无法注意到, 因此 memroy 是负担, 不要意味过长上下文有用, 请善用重开窗口这项技能

---



现在输出你的 plan和要说的内容给你的后人, 我会复制给他, 在你说完后我会关闭当前窗口, 请你谨慎传递, 更新你的想法到 C:\Download\git\uni\memory_trasfer.md
---

If U are captrue a screen on lock screen it's a black, pls check the screen stat when u wantto excute a action 


---

▌好, 除此外我还希望你对比下我手动生成的示例文件, 已经 LLM 生成的, 他们的区别, 据我观察, 目前生成的脚本根本不是一个可用的, test_llm_generated_20250910_140553_script.py  C:
▌\Download\git\uni\only_test\testcases\python\example_airtest_record.py , 需要你分析是什么造成了差距,我的 requirement 还不够清晰吗,还是你的prompt 传入的不够, 是否传传入了相似 script (目前样本少, 考虑不过滤直接▌将现有的录制样本传进去) 还需要从源头分析, 我以前让你从 录制的 py 文件中溯源过 json,  你是否尝试过 那个 json 再生成一个 py 文件是否有格式问题, LLM 生成的是 json,  因此要从 json 和 py 两层去考虑  python -X utf8▌only_test/examples/mcp_llm_workflow_demo.py --requirement "测试vod点播播放正常: 1.进入APK后就是首页，执行关闭广告函数，2.找到searchbtn点击，直到可输入状态后输入节目名称'720'点击第一个节目，3.播放节目，断言:  ▌验证设备是否处于播放状态" --target-app com.mobile.brasiltvmobile --max-rounds 2  




*-----


动态录制, 先说下我发现的问题, LLM 和 MCP 交互只有一轮, 就是只获取一次当前屏幕状态, 但我想说的是, 我们有好几个步骤, 是否需要 LLM 实际去到那个页面才能获取下一个 Page 的id 这个去页面的过程也是验证 外部 LLM 的判断是否合理, 避免书写无效用例.  但目前为什么 LLM 直接生成了用例呢, 这是一个问题, 你可能需要增加 prompt 让外部 LLM 直到应该怎么做 要做到行为的执行必须要做好关于行为判断的 prompt, 比如 LLM 参照之前用例直到下一步要点击搜索, 那么它一定要找到这个搜索 btn的 name/id (这里你也要详细设计, 究竟是什么选取策略更稳定, 比如有限选择 ID, 有 text 则 text? omniparser 则无脑直接 tap position? 都需要你设计好)等实际可信的内容后一定要使用 MCP 提供的 tap 或滑动工具执行这个操作, 之后重新分析屏幕元素, 外部 LLM 也需要自己知道 如果执行了行为 截图前后变化不大 并且 前后的 uiautomator2 的json 输出数据也没变化, 是否意味着动作未成功, 这时是否需要警告呢, (这一步 QA.md 有提到, 需要确保外部 LLM 知道自己是否成功执行操作, 具体的逻辑自己用代码书写) 这样一步步操作手机的过程并录制点击的过程生成一个测试用例 才是这个项目的正确期望



> 你的观察完全正确：之前只是“看一眼屏幕→直接整案”，没有“边执行边取证”的动态录制路径。我已经把流水线改成“多轮交互 + 真机执行 + 重新识别 + 结果判断”的方式，并把这些约束写进了 Prompt 与工具链里。

  做了什么

  - 新增 MCP 交互工具（真机执行）
      - perform_ui_action：基于 selector 或坐标执行 click/input。
      - perform_and_verify：执行动作前后各抓取一次 get_current_screen_info，对比元素签名，返回是否“发生变化”（changed=true/false），并回传使用的 selector。
  - 强化多轮动态录制（逐步推进页面）
      - llm_generate_testcase_v2 现在每一轮都：
      - 读取真实屏幕元素 → 让 LLM 选“下一步原子动作 + 选择器” → 用 MCP 工具真机执行 → 再次抓屏校验 UI 是否改变。
      - 将每步执行与校验写入 `logs/mcp_demo/session_<ts>/execution_log.jsonl`，同时输出 `execution_log_step_*.json` 与告警文件（若前后签名无变化）。
  - 明确“行为判断与选择器策略”的 Prompt 约束
      - 只能用原子动作：click|input|wait_for_elements|wait|restart|launch|assert。
      - 必须给出 priority_selectors（优先 resource_id，次之 content_desc，再之 text）；若无法提供，给 bounds_px（像素坐标，OmniParser 场景可兜底）。
      - 每步都要执行 MCP 动作后重新分析屏幕；若前后变化很小，要求发出告警并调整策略。
      - 注入了你手工脚本与“黄金 JSON”作为 few-shot 示例，强引导生成可执行选择器。
  - 选择器与转换修复
      - 转换器现在优先吃 target.resource_id/text/content_desc（不再仅依赖 priority_selectors），并用 target_app 作为 start_app() 包名。
      - 缺失选择器的点击/输入会显式报错，推动上游 LLM 修正 JSON。

  你关注的问题 → 现在的行为

  - 多轮：每一轮都“看屏→决策→真机执行→再看屏→是否变化”，避免 LLM 空想一步到位。
  - 必须到目标页面再拿 ID：通过每步“执行→复测”的强约束与工具机制达成；页面没变则视为可能失败，日志告警。
  - 选择器稳定性策略：resource_id > content_desc > text；视觉（OmniParser）才兜底坐标点击。
  - 执行成败判断：用 UI 元素签名 hash（元素 resource_id/text/clickable 汇总+计数）做“前后对比”；后续可再加“等待出现/消失”增强。

  文件与入口

  - 新工具（已自动注册）: only_test/lib/mcp_interface/device_inspector.py
      - perform_ui_action, perform_and_verify
  - Prompt 模板：only_test/templates/prompts/generate_cases.py（few-shot 和原子动作/selector 强约束）
  - 多轮 demo：only_test/examples/mcp_llm_workflow_demo.py（每轮执行+校验+记录）
  - 黄金示例：only_test/testcases/generated/golden_example_airtest_record.json（由你的 example_airtest_record.py 反推）
  - 运行（orun 环境）:
      - conda run -n orun python -X utf8 only_test/examples/mcp_llm_workflow_demo.py --requirement "..." --target-app com.mobile.brasiltvmobile --max-rounds 2 --device-id 192.168.100.112:5555

  接下来我可以继续

  - 用“出现/消失等待”替换/补充签名对比（更强的成功判据）。
  - 扩展 swipe 与更稳健的输入（中文/特殊字符）。
  - 让 LLM 在 step 输出时同时给出“期望出现/消失的元素”，MCP 工具内直接做 wait 校验。
  - 把这条动态录制链路纳入 YAML 套件控制器，按套件一键跑。             




添加自动关闭广告模块让 外部 LLM  在录制过程中不被广告干扰,
1. 当LLM 触发使用 uiautomator2 的MCP 分析模块时
2. 系统自动检测 是否存在广告 1.元素数量若较少则广告存在的情况升高 2.存在 ad 关键词 3.同时存在 close 4.  AD 和 close 原点之间距离, 若过近则代表是也会存在  ivClose mIvClose 为 click 状态 则置信度上升 必然存在广告 需点击, 阈值默认 90% 确信才点击
3. 如果检测到广告 → 自动尝试关闭 -> 自动重新 dump_ui -> 尝试检测广告（最多3次循环)
4. 3次后仍有广告, 阈值 70%  → 返回最终UI状态给外部 LLM ，标注可能存在未关闭的广告
5. 外部LLM 看到UI状态 + 广告提示 → 根据prompt指导手动判断和关闭
6. 如果手动也失败 → 我们可以收集反馈，了解是什么原因导致检测或关闭失败

  设计原则:

  - 自动处理: 再 LLM 期望查看屏幕时自动检测+关闭（3次循环）
  - 手动补充: 自动失败后，prompt引导外部LLM手动处理
  - 反馈机制: 收集失败案例，优化检测逻辑

  关键分工:

  - 函数: 检测广告、自动关闭、返回状态
  - Prompt: 引导外部LLM识别广告特征、手动关闭广告


---


  - 在 perform_and_verify 内引入“等待条件”：支持 wait_for_disappearance("Ads") 或等待 close 按钮消失，作为更强的成功判据（已留好位置）。
  - swipe 的实装：现在未实现，视觉复杂页面可补齐。
  - 广告检测特征扩展：加入倒计时层（文本包含 s），背板遮罩（半透明层）等。
  - 将这条动态录制链接入 YAML 控制器：按 main.yaml 的 suite 编排一键执行。

  以上改动已完成、可直接试跑。如要我继续把“等待出现/消失”的强判据集成到 MCP 工具里，或将用例按 YAML 控制器编排并执行，请告诉我。  


  ------
raed all md file, talking about this project 距离可应用状态还差什么,  给我你的想法
----
你提出了重要的问题, 选择我补充一些内容, 之后需要你开始修复. 1.wait_for_appearance 先不处理, 因为他是一个录制文件的关键动作, 可能他人搞错了将它写道了日志里, 2.airtest 以前是目录名称, 但我发现冲突, 就改为了选择的 only_test, airtest.core现在应该是一个 python 库, 有任何问题请向我提问, 有关键信息请写入 QA.md 文档, 我会检阅或答疑.另外我也希望你在修改任何内容前阅读代码思考其设计路径, 你会有更多了解: 比如其设计确实有道理 但是确实多余 直接修改. 还有刚刚我也进行了代码修改.  你给出的内容较多, 我推荐你重新根据我的补充写一个具体执行plan, 你严格按照 plan 执行, 并完成后勾选, 避免重复或漏  现在开始工作 



----



python -X utf8 only_test/examples/mcp_llm_workflow_demo.py --requirement "测试vod点播播放正常: 1.进入APK后就是首页，执行关闭广告函数，2.找到searchbtn点击，直到可输入状态后输入节目名称'720'点击第一个节目，3.播放节目，断言: 验证设备是否处于播放状态" --target-app com.mobile.brasiltvmobile --max-rounds 2 直接请你尝试生成用例观察输出,修复 error , 发现不合理, 最终完成外部 LLM 的用例自主生成


----

过滤设计
用例过滤规则

XML json filter 规则: 在我们拥有海量数据过后根本不需要再使用笨方法去送个 LLM 分析, 可以直接搜索 直接使用之前的 btn name 再 XML 中搜寻, 搜索不到时再使用老版本过滤即可
举个例子, 比如目前的 search 是 com.mobile.brasiltvmobile:id/searchEt 但如果换个应用可能叫 searchbtn or any things, 我们唯一知道的是目前需要点击的是 search 相关的内容,我们直接对用例库进行关键字搜寻, 找到经常使用的方式 比如 id (根据搜索出来的数据量) 假设确实都是使用 ID 则推测这次 ID 概率较大, 直接使用 grep id  + search from json , 这时过滤出了所有 id 后 比如有两个, 这时直接从 json 中过滤这条数据即可查看json 体. 如果过滤结果 0 则考虑更换过滤方式或者使用旧的方式直接过滤 clickable 的送给 LLM 进行确认即可. 


----


▌好应用它 •  提高 LLM 输出一致性：在模板 prompt 中把 priority_selectors 固化为 list[dict]，键名统一使用 resource_id / content_desc / text（避免 resource-id 这类连字符，减少转换歧义）。 .  除此外我还希望你对比下我手动生成的示例文件, 已经 LLM 生成的, 他们的区别, 据我观察, 目前生成的脚本根本不是一个可用的, LLM 生成的是 json,  因此要从 json 和 py 两层去考虑  C:\Download\git\uni\only_test\testcases\generated\test_llm_generated_20250910_154634_script.py  \uni\only_test\testcases\python\example_airtest_record.py , 需要你分析是什么造成了差距,我的 requirement 还不够清晰吗,还是你的prompt 传入的不够, 是否传传入了相似 script (目前样本少, 考虑不过滤直接▌将现有的录制样本传进去) 还需要从源头分析 . 最后, 我发现你在执行录制时屏幕根本无变化, 证明并不是实施录制, 还需要你再检查以下原因, 可以从代码/日志层面触发, 

-----

我要测试自动关闭广告功能, 给我一个可以直接执行的 python 命令, 我会让手机保留广告以验证广告关闭模块


---


Ok 你已经知道了他们的作用, 那你认为目前的prompt 健壮吗, 有什么优化的地方吗, 比如我目前就遇到一个问题, 比如让 LLM 结合 MCP 生成用例, 其生成的用例全是幻想的,而不是实际的, 我的期望. 其像 提供的示例文件一样 C:\Download\git\uni\only_test\testcases\python\example_airtest_record.py 一步步的点击, 确认每一个 ID 的内容写入json, 模拟人录制用例, 结果是其并未进行任何屏幕操作, 只是生成了一堆的不存在的 ID, 


-----

我觉得还可以在 llm_generated*json 产物 增加一项 chain, 你觉得如何, 比如 ## [page] app_initialization, [action] restart, [comment] 重启应用清理环境状态(多次关闭) 这条内容我之前就是像记录链路, 而如果 LLM 或谁也记录了更详细的这将是更有参考意义的, 比如 可以直接记录 ID.   [page] search, [action] click com.mobile.brasiltvmobile:id/ivClose  --> (next cicle) , 不急着添加 我们先讨论是否有必要 
---


▌这是用例文件, 其是否需要兼容你的新方式使其能正常执行, 另外, 我希望将 python -X utf8 only_test/examples/test_ad_closer.py --target-app com.mobile.brasiltvmobile --mode continuous 作为一个入口为一个关闭广告函
▌数, 随时调用, 用例中也可调用, 模式为当 continuous 连续 3 次未检测到 广告则直接结束, 并限制最长执行时长为 10s 函数可传值. 支持在 MCP 中调用分析屏幕元素时自动调用这个工具, 默认值也如上所述, 我说了多个修改点修改
▌前请先 Plan 怕你不懂就直接修改, 记得改为正式模块 test_ad_closer 是一个测试 name


---


添加一个功能 你可以看到main.yaml中提供了  ui_activity  请你在任何启动 pkg 的时候查看是否又关联关系, 如果有配置 ui_activity 代表有特殊的启动方式, 没必要用 monkey 启动, 因此可能需要一个统一的 start app 模块供所▌有启动时请求, 你需要检查所有使用启动 apk 的地方进行统一入口化, 包括 MCP. 我希望你在修改前先统计, 评估修改项, 另外 main.yaml 可以说也是一个入口, 其内部会定义很多元数据, 当任何传入 application 的地方都需要通过 ▌这个地方 因此还需要一个yaml monitor 之类的 py 模块供查询和返回, 比如 brav_mob = com.mobile.brasiltvmobile contains app_name description ui_activity, 当我输入  brav_mob com.mobile.brasiltvmobile 任意一个时都应▌该知道我指的是谁, 这个文件以后会随着用例而填入很多的 applications test_suites devices 内容, 因此请考虑靠扩展性不止与   applications 还包括 devices 应该也有扩展性, 
可以使用统一的 start_app func, 但我希望对于 Airtest 的 start_app 进行重写, 使用我们刚刚规划的方式, 支持回退的启动方式, 这样用例任意地方只要需要启动 start_app即可, 而用例文件引入 airtest 也改为一个 lib 下边的固定模块, 固定模块中重写 start_app, 这样能作为公共入口, 而且兼容了 除 start_app 其它 airtest 正常使用


---- 


这里能否加 bias poco(text="西语手机端720资源02").click() ,比如我想向上偏移 5px, 要在本地 Poco 包上做一个轻量扩展
请检查下 click_with_bias 确认计算没问题, 比如增加相关打印日志, 打印原点与 + bias 后的点, 我观察到好像偏离很远
能打印因为 xy 轴的方式 这样好对比, 比如我目前开启了 andrid coordinate 确认我希望点击位置再 x:285 y:940 处

---

1.查看下这个 json 文件, 虽然有很多遗漏, 但我们正是要找出他的问题, 它使用了特殊的格式来放置用例, 但你觉得这是一个好方式吗, 我们本身用例也不多, 是否只需要放在 code block 里边 直接复制过过去 py 文件呢, 还是你有什么更好的办法,我们一起讨论下,  再找出一些不合理的问题
是的, 请按照你的想法约束json , 并思考如何把 函数, 参数, 直接映射到 py 文件, 你认为如果现在让你生成后的 json 能和目前录制的 py 文件大差不差吗, 我觉得是个问题, 因此我们呢还需要规范好 py 生成的方式. 你认为呢

1.确认是否附带了相似用例文件比如 json or py 你觉得哪个好. 自动过滤规则是否生效, 比如总用例库数量小于 3 直接附带所有用例文件作为示例(注意刨除我们生成的数据避免prompt 过多.)大于3 则进行定向过滤文件类型后传入相同类型的 3 个文件作为思路学习(辅助 LLM知道操作过程, 因为所有 APK 即使 resourceid name 不同, 但路径是可以借鉴的, 并无本质不同). 如何让他很好的结合呢, 这是个很苦恼的问题  2.试着反思找出现存问题. 


将最近我的提问和你的回答, 我们选用方案的理由, 更新到 QA.md 让后人知道我们这样设计的原因. 

----
from now on , our destnation is complete this project last step, try to generate a  case and fix bugs in this journey. now pls generate a real case, the devices and omniparser server and the LLM server already start. the action should be:  requirement "测试 vod 点播播放正常-(h264): 1.进入APK后就是首页，执行关闭广告函数，2.找到searchbtn点击，直到可输入状态后输入节目名称'英语和西语音轨'点击节目，3.播放节目，断言: 验证设备是否处于播放状态 
使用这个 project 的 外部 LLM 生成或者用例而不是你自己生成, pls add a prompt let 外部 LLM ignore ((忽略的内容)) 双括号中你的内容, 以便我自定义标注一些东西

python -X utf8 only_test/examples/mcp_llm_workflow_demo.py --requirement "测试vod点播播放正常: 1.进入APK后就是首页，执行关闭广告函数，2.找到searchbtn点击，直到可输入状态后输入节目名称'720'点击第一个节目，3.播放节目，断言: 验证设备是否处于播放状态" --target-app com.mobile.brasiltvmobile --max-rounds 2 直接请你尝试生成用例观察输出,修复 error , 发现不合理, 最终完成外部 LLM 的用例自主生成

----

now pls generate a real case, the devices and omniparser server and the LLM server already start. the action should be:  requirement "测试 vod 点播播放正常-(h264): 1.进入APK后就是首页，执行关闭广告函数，2.找到searchbtn点击，直到可输入状态后输入节目名称'英语和西语音轨'点击节目，3.播放节目，断言: 验证设备是否处于播放状态 . 请使用 python 执行脚本与 外部 LLM 发送指令让其成功生成用例



----------

改写自动关闭广告逻辑, 加一个 round 标识或者采用已有标识, 限制只有前三次(可配置) 调用 MCP 分析屏幕时才自动 close ad, round 主要用于判断这个, 避免每次都进行不必要的关闭, 

---

除此外我希望你添加 执行 UI 操作完成后自动探测页面元素是否改变, 目前两种方式, 1.XML 元素无变化 2.屏幕前后的截图变化小于 98%(差距过小代表页面操作无效) 这里确认后反馈给 外部 LLM 让他知道操作无效, 使不进行 无效录制, (相关规则你可自行完善, 相关算法你可自行思考). 两种方式必须同时为 false 时才会反馈给 外部 LLM 操作无效 避免算法上引起的问题导致误认为无效
---

我想做以下修改, 1.防止选择器漂移: 通过 prompt  强制外部 LLM 只能在返回的 XML 中选择进行操作, 禁止自行制造resourceID or其它字段内容 2.在用例生成前提供示例样本, 让外部 LLM 先进性一轮规划, step by stp 的 这有助于框定后续 LLM 流程中的步骤方向. 这个 plan 可能具体到调用什么工具, 怎么做等内容, 之后这次生成用例时每次 prompt 都把 plan 附带, 你之前说的都太固定了, 我们需要打造一个具有适配性的, 你提出的都是具体的场景吗, 有缺陷, 出来我提出的这两点你觉的滑油其它方向进行优化吗

------
我来指出你的问题在哪， 1.program-name（优先）或 --requirement 提取节目名称: 播放节目测试点只是一个功能测试， 我们可能包含个人中心测试， 登录测试（可续可能）， 请问你如何应对， 因此只能在 Planning 阶段提取当前用例的 keyword 作为用例文件名称这种， 2. 这条没理解， 需详细解释再评审： 每个生成的步骤在落盘前必须通过“选择器存在性 + 至少一次 perform_and_verify 成功”的校验
3.确认 max-rounds 的场景， 我们目前设计的 Planning 阶段就是单独占用了 1 个 round 对吗， 详细解释还有那些使用场景， 以此来决定合适的 设定， 并且我认为最后的 round 是否要根据 Planning 阶段来决定， 你认为呢， 让外部 LLM 自己根据 制定的 Planning 给出round。 那么就是输出， Planning 全文， keyword， max-rounds 三个字段内容
4.按需求截断（如最多 50 个/类）。 没必要做，我们之后考虑做更好的返回规则， 目前还没做好 plan 思路是像 claudecode、coding agetn 一样其有自己的过滤方式规则。 先不规划， 我后期会再谈论这个
5.对于不理解的行， 我将输出给你， 请你详细讲解我不理解的, 
我们目前需要先理解后重新制定， 先不急着开始做

----



请你自己删除之前的执行日志, 自己运行查看结果, 最后检查生成的用例对比原始录制的用例, 确认质量, 給处是否要调整的建议

--

现在我需要你帮我整理 prompt, 帮我整理并归档好 only-test 下各个 prompt 的储存位置以及关联, 我需要随时能调整 prompt 以掌控项目, 并且我希望你检查当前的prmotp 结构性, 你可以找一个合适的 MD 文档将内容写入, 比如整理好当前 Planing 阶段的 prompt 在哪, 区别是什么. 以及各个阶段的 prompt 区别.  PLS 总结我的需求输出, 并找出目前存在的问题, 

-----


跟我一起看向 C:\Download\git\uni\only_test\testcases\python\example_airtest_record.py 据我对它录制时刻的观察,  好像是卡在了这里 
'''## [page] search, [action] click, [comment] 点击搜索输入框激活输入状态
poco(resourceId="com.mobile.brasiltvmobile:id/searchEt").click()


## [page] search, [action] input, [comment] 输入搜索关键词
sleep(0.5)
text("西语手机端720资源02")''' 它可能并未再次点击 searchEt 进入激活状态旧输入 内容之后点击 searchCancel 直接退出了, 而不是进入了下一步,
我们先假设这个猜测为真, 
我们应该如何解决这种细节问题呢, 我之前以为增加 planing 阶段让其总结要做什么, 之后其能完全复刻一个新的用例, 但是目前来看不是, 因此现在我想到的 解决方法就是对 Planning 的prompt 进行优化, 提及要注意这一点, 做好应有的规划, 
这可能只是一个注意事项, 但是往后的用例呢, 肯定还是会出现这种情况的(因为一些细节导致录制失败). 这意味着这个项目很难登大雅之堂,  因为可能很多东西要一点点自己添加, 不能大范围的全自动, 这让我对这个项目感到失望, 你作为我的助手, 最熟悉这个项目的人, 你有什么思路想法呢, 让我们谈论起来
-----------+
分析并解决无法通过 class_name 点击的问题, 兼容它

好的, 我需要你执行 1.修复问题 2.检查其它字段有没有相似问题 3.列出目前支持哪些 字段的操作, 比如 resourceId..  的 click set_text....的操作, 你可找一个Poco 下的文档写入, 3.写入问题分析过程, 结果,
  与你的心得进入其中, 为什么我第一次提问你没找到问题原因


我希望你帮我重写 set_text  for only-test 项目, 改为做多项内容, 1. 当然是根据提供的元素进行设置, 当然你i需要兼容多个方式, 比如 class_name 和 resourceId.. 设置成功后 2.执行 invalidate_cache 刷新,
  之后使用相同元素 get_text . 最后返回, 这样我旧不用再代码中做多项内容,  poco(class_name="android.widget.EditText").set_text("西语手机端720资源02")

  ## [page] search, [action] get_text, [comment] 确认成功输入内容
  poco.agent.hierarchy.dumper.invalidate_cache() # 刷新, 避免使用缓存
  result = poco(class_name="android.widget.EditText").get_text()
  print(result)
  
----

看向这里 C:\Download\git\uni\only_test\testcases\python\example_airtest_record.py
我已经按你的指导和我的想法, 将用例文件重新整改, 
1.请你重新根据用例推出 json 内容, 之后再规划一下它的方案 Prompt 和用例结构的约束: 失败恢复
2.对“能否大规模自动化”的看法- 你的想法很不错,  请你想办法记录下这些想法, 让后人能清晰的看到. 
3.我目前对这个项目无信心, 请谈论一下, 让我对项目与自己有更清晰的认知: 想法: 起初做这个项目是因为我们公司有很多 APK, 操作方式基本相同, 都是这一类的 APK, 这个项目能很好的将一份用例扩展为多个 APK 都可执行的用例, 利用 LLM 的泛化能力与项目的约束一起工作, 提升用例的可复现能力, 但是我页经常看到别人说不要向领导推荐提升生产力工具, AI 类工具, 并且我之前页提过一些 LLM 在 客服, 运维, 开发上的一些应用方向, 领导也只是含糊其辞. 你说 我该何去何从 
------


评审一下他人对这个项目的建议, 有哪些你认为可以采纳,  哪些毫无用处
  - 规范与校验
      - 提供正式 JSON Schema（含枚举、必填、互斥/依赖、选择器模型），并在生成/执行前做校验。
      - 统一“选择器模型”与“策略优先级”的结构定义（如 selector.type/resource_id/text/...，附置信度与降级策略）。
  - 断言与可机判
      - 在步骤中引入标准化 validators 数组（如 element_exists/text_equals/image_similarity >= 0.99/playback_state=='playing'），替代/补充 expected_result 的自然语言。
      - 将播放/广告/全屏等常见判定包装为复用校验器（并暴露 MCP 工具）。
  - 提示与去重
      - 将“相似度计算/评分规则/输出 JSON 片段”抽到单独的共享模板或常量模块，避免在多文件中重复与偏差。
      - 增加少样本示例集（few-shot），构建“坏例/好例”对照，提升稳定性。
  - 工作流与观测
      - 对 MCP 工具接口输出定义 OpenAPI/JSON-Schema，供 LLM 端工具反射/自动补全，降低误调用。
      - 执行轨迹、屏幕快照、选择器命中统计沉淀为“可查询的案例库”，反哺相似检索与策略选择。
  - 生成质量闭环
      - 扩展 SimilarTestCasePrompts：将“可复用片段→模板化片段”流水化，自动替换变量/定位策略。
      - 引入轻量“静态仿真/干跑”器：对生成 JSON 做基本可达性/字段合理性/变量替换模拟校验。
  - 工具层与鲁棒性
      - 对 close_ads、detect_playing_state 等常用工具设定“重试/超时/降级”的默认策略与可配置化阈值。
      - 强化 uiautomator2 与 omniparser 的对齐器（selector/uuid/bounds 统一结构与映射规则），沉淀标准。


----------



经过对你给出更改方向的review, 我决定采取以下修改, 未采取的代表我不太认同, 无需理会. 解释  下方两点可直接实施, 还需谈论的点 需要再详细回答后做 plan. 
1) 提供正式 JSON Schema（含枚举、必填、互斥/依赖、选择器模型）
1) 在步骤中引入标准化 validators 数组（element_exists/text_equals/image_similarity>=0.99/playback_state==playing），替代/补充 expected_result


还需谈论的点
1.将播放/广告/全屏等常见判定包装为复用校验器（并暴露 MCP 工具）. 
可以提供工具, 但重要的是以什么方式, 目前如果一次给太多 MCP 工具, LLM 会模糊概念, 也就是他不知道什么时候该用什么工具, 目前问题很难解决, 除非写多个 MCP 工具应对不同的方面, 比如目前的MCP 只负责用例生成, 再写一个负责用例校验(但是好像也不好解耦). 值得深思
2.将“相似度计算/评分规则/输出 JSON 片段”抽到单独共享模板，避免多文件重复与偏差
我还是没有看懂这段内容想做什么 
3.强化 uiautomator2 与 omniparser 的对齐器（selector/uuid/bounds 统一结构与映射规则）
•  评审：建议采纳（中/高优先级）
•  为什么：双源识别一致性是降低误判的基础；也是你“白名单绑定”得以生效的前提。
•  怎么做：
•  定义统一元素对象结构（uuid/resource_id/text/content_desc/bbox/center_x/center_y/source/confidence）
•  选择器解析时优先使用 uiautomator2，播放视觉场景使用 omniparser，并保留来源与分数
没明白这点想要做什么,  的交点只有一个 bbox 转换出的 position 可以被 click. 其它的如 content 内容也是唯一存在的判定 icon 类别的东西, 其它的都是不存在的 (你可以查看返回, 都是虚拟的东西) 因此我不明白你这是想要做什么 



未来
2) 增加 few-shot 示例集，构建“坏例/好例”对照
•  评审：建议采纳（中优先级）
•  为什么：实证能够显著减少 LLM 输出结构错误；尤其“坏例→修正”能提升稳态。
•  怎么做：
•  sessions 中挑成功/失败样本，脱敏后转为示例片段，纳入 generate_cases 的 examples


2) 执行轨迹、屏幕快照、选择器命中统计沉淀为“可查询案例库”，反哺相似检索与策略选择
•  评审：建议采纳（中优先级）
•  为什么：这是 R6 数据飞轮的关键；能将失败 Top-N 与成功模板沉淀，减少重复犯错。
•  怎么做：
•  将当前 JSONL + 截图组织成可索引（简单可先 SQLite/Parquet + 目录规范）
•  run_case 结束后写入索引，SimilarTestCasePrompts 检索时可参考这些案例。



五、生成质量闭环
1) 扩展 SimilarTestCasePrompts：将“可复用片段→模板化片段”流水化，自动替换变量/定位策略
•  评审：建议采纳（中优先级）
•  为什么：适配同类 APK 时收益可观，但属于第二阶段的“效率工具”，优先级略低于“稳定性护栏”。
•  怎么做：
•  提供模板参数化占位（包名、搜索词、页面签名、主要 selectors），并定义变量来源与校验

2) 引入轻量“静态仿真/干跑”器：对生成 JSON 做基本可达性/字段合理性/变量替换模拟校验
•  评审：建议采纳（中优先级）
•  为什么：能在“连设备前”筛掉明显错误；对大规模批量生成尤为有用。
•  怎么做：
•  run_case 加 dry-run 模式：仅做 JSON Schema 校验 + 基础语义检查（互斥/依赖/选择器结构），不连设备
•  若有历史屏幕白名单缓存，可做“选择器存在性”近似匹配

六、工具层与鲁棒性
1) 对 close_ads、detect_playing_state 等工具设定“重试/超时/降级”的默认策略与可配置阈值
•  评审：立即采纳（高优先级）
•  为什么：这些是高频失败点；默认重试/超时策略是“护栏”的一部分，提升稳态。
•  怎么做：
•  统一在 tools 层加入默认参数（max_duration、interval、consecutive_no_ad 等），并允许 case 层覆盖
•  失败时写入原因码，便于统计 Top-N


---------
我同意你的方案, 但我有一些附加描述希望你再coding时记得, 1.执行器通道（内部探针） 直接以一个 valiator 方式实现, 调用方式为增加 参数, 比如希望获取 playback 直接传参即可,  2.uiautomator2 与 omniparser 点修改, 我需要你再开始之前先获取 omniparser 返回的内容确认数据结构, 根据当前代码确认合并逻辑, 阅读两者 XML+ omniparser 后才能更好的工作, 才不会错漏, 或者给出错误的逻辑. 

-----

@pure_ui2_dump_extractor_with_image_tag.py 我希望增加功能,  1.在获取 XML 树同时截图, 之后根据获取的 XML 树将所有元素以红框标记出来,框住这个元素, 规则为 1.size pos 不为原点(原点代表可能不是有效元素) 2.若有 text 请在红框右侧写上 text, 若无 text 请使用 resourceId 进行标记, 取值 / 后内容比如 com.android.systemui:id/clock 取 clock  让我指导这个元素是谁, 以此验证是否正常, 请开始coding

---


- reafactor: XML mode only

修正: 新UIAutomator2 相对于旧版 UIAutomator 在播放状态（play state）下支持了更好的元素识别，但存在一个常见缺陷：它只能识别当前可见（displayed）的元素。对于像 seekbar 这样的控件，需要先点击屏幕使其显示，然后才能识别和操作。目前 APK 设置的显示栏（bar）消失时间太短，可能会导致识别失败或点击无效. 因此需要一个 keep 函数确保元素始终展示, 兼容需要长时间显示情况显示

only_test_old 是使用 omniparser 的模式, 这个模式在目前的我看俩已不适用, 我需要 only_test 项目全部使用 XML 模式, 没有回退方案, 请直接删除相关代码, 以及各个文档中关于 omniparser 的描述都删除, 注意只处理 only_test 下方的内容, only_test_old 可保留. 另外下方是新模式的一些必须用品, 在你处理完上述内容后执行

此函数需要支持, 1.再想要点击之前确保播放导航栏 icon 全部显示, 也就是需要不断的侦测并点击唤起展示 icon , 他需要是一个单实例的异步函数, 也就是调用后填入持续监测时长, 其需要自动工作, 单实例是因为防止多个函数同时点击, 如果有其他函数再次调用, 需要销毁前一个实例, 使用最新实例进行工作, 请完善这个函数, 写在 lib 目录下
clickable_area 设计方式, 为了兼容全屏和小屏, 需要找到一个都可点击的区域, 我决定是 当前的高的 15% 处 
`比如当前是小屏, 设 xy  = 1080x2340  . 那么点击区域为 x=1080/2 (取中心点)  y=2340*0.15=`
`现在切换到全屏 = 2340*1080 . x = 2340/2 = 原点 y= 1080*0.15 = 162`
动态替换当前设备的像素值即可获知要点击的位置, 以唤起 icon. 注意我的设计也许并不是全然正确, 你可思考不合理之处进行改正



playing_stat_keep_displayed_button(,detect_interval=0.1(每0.1检测一次是否显示控件), exist_filed_keyword="Brightness"(这里将传入一个播放状态下必然有的 icon , 以此判断是否点击后成功唤起 icon 的展示 , 之后会二次封装, 为每个不同状态传入指定的 keyword))
  clickable_area = # 需要找一个可点击区域
  clickable_area_mini_window = clickable_area # 目前的设计兼容了小屏和全屏
  if is_playing_stat: 播放状态需要特殊处理, 调出 icon 以进行侦测, 但是全屏和小屏点击位置不一样 

    
      if  exist_filed_keyword not in cureent_XML_json and len(resourceId ) < 10 : # 没有相关字段则存在于json ,and 字段过少 (代表处于播放状态 icon 不存在则字段很少, 两项都符合时点击唤起所有 icon)
        click(clickable_area) # 点击以使 icon 出现, 
      
    
播放状态页区分小屏播放状态, 目前没有处理的明显区别, 但写下来方便以后区分
def is_full_screen() return true(全屏) false(非全屏)
1.全屏 2.非全屏, 区别有 mBounds 值颠倒, port in mCurrentConfig 全屏, land in mCurrentConfig 非全屏

crux:/ $ dumpsys activity top | grep -E 'ACTIVITY|mCurrentConfig' | grep com.mobile.brasiltvmobile -A 1
  ACTIVITY com.mobile.brasiltvmobile/com.mobile.brasiltv.activity.PlayAty 3d27394 pid=26980
      mCurrentConfig={0.86 ?mcc?mnc [en_US] ldltr sw523dp w523dp h887dp 440dpi lrg long hdr widecg port finger qwerty/v/v -nav/h winConfig={ mBounds=Rect(0, 0 - 1440, 2560) mAppBounds=Rect(0, 75 - 1440, 2516) mWindowingMode=fullscreen mDisplayWindowingMode=fullscreen mActivityType=standard mAlwaysOnTop=undefined mRotation=ROTATION_0} s.7 themeChanged=0 themeChangedFlags=0 extraData = Bundle[{}]}
crux:/ $
crux:/ $
crux:/ $ dumpsys activity top | grep -E 'ACTIVITY|mCurrentConfig' | grep com.mobile.brasiltvmobile -A 1
  ACTIVITY com.mobile.brasiltvmobile/com.mobile.brasiltv.activity.PlayAty 3d27394 pid=26980
      mCurrentConfig={0.86 ?mcc?mnc [en_US] ldltr sw523dp w903dp h480dp 440dpi lrg long hdr widecg land finger qwerty/v/v -nav/h winConfig={ mBounds=Rect(0, 0 - 2560, 1440) mAppBounds=Rect(75, 0 - 2560, 1396) mWindowingMode=fullscreen mDisplayWindowingMode=fullscreen mActivityType=standard mAlwaysOnTop=undefined mRotation=ROTATION_90} s.10 themeChanged=0 themeChangedFlags=0 extraData = Bundle[{}]}



----



1.first pls check C:\Download\git\uni\only_test\templates to know what did this dir each file do
2.check example_airtest_record.py and golden_example_airtest_record.json to Know more aboout schema constrains
3.check QA.md WHY current structure.
4.IN the end pls 结合 MCP 整个工具检查下, 如果是你使用这些 MCP + prompt 驱动, 你能做好用例生成吗, dry run 一下, 目前没有环境给你实际演示 整个过程不要修改文件, 只是让你了解项目. excute step by step 最后根据你的经验, 总结下对这个项目的 judge, 说出你认可可能的改进方向


----- 


需求: 
1.支持快捷键关闭 debug 面板
使用VOLUME_UP + VOLUME_DOWN 组合按键, TV 和 手机应该都能正常监听 缺点是肯定会调起音量bar 调整音量
VOLUME_UP：adb shell input keyevent 24
VOLUME_DOWN：adb shell input keyevent 25
1s 内先 UP 再 DOWN 组合按键关闭 debug 面板

2.支持配置项延长 bar 显示时间. 比如 adb 命令? 
3.配置项允许 H7 盒子截图
4.支持接口获取 DEBUG 面板所有信息
5.支持参数配置直接再 debug 包不展示 debug 面板


---

python -X utf8 -m airtest run C:\Download\git\uni\only_test\testcases\python\example_airtest_record_fixed.py

感悟 越向底层越难解释, 比如 CDN 到 APK, 
-----
next

用例管理, tag 不想重新生成的 PY 文件?  重新生成的策略



书写测试用心得, 使用哪个方式更简单一目了然, 更重要的是步骤少, LLM 犯错的机会就少,(因此看来 Deeplink 势在必行), 一定要使用最简单的方式实现.

方式1 
poco(resourceId="com.mobile.brasiltvmobile:id/searchEt", text="Search for content title").set_text("西语手机端720资源02")

方式2
poco(resourceId="com.mobile.brasiltvmobile:id/searchEt").click()
## [page] search, [action] input, [comment] 输入搜索关键词
sleep(0.5)
text("西语手机端720资源02")