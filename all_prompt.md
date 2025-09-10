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


▌现在输出你的 plan和要说的内容给你的后人, 我会复制给他, 在你说完后我会关闭当前窗口, 请你谨慎传递 

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