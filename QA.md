# Only-Test 项目完整问答文档

## 📋 基于现有设计的确定答案

### Q1: 项目的核心问题是什么？
**A:** 控件名通过人工找到或录制太费时间，需要让外部LLM使用MCP监控屏幕获取当前控件状态（如 `com.mobile.brasiltvmobile:id/mImageFullScreen`），然后记录操作到JSON。

### Q2: 标准用例格式是什么？
**A:** `example_airtest_record.py` 是唯一的标准格式，是最终用例的执行格式。内部必须包含标准注释：`## [page] vod_playing_detail, [action] click, [comment] 点击全屏按钮进入全屏播放模式`。setup_hook等是辅助项，最终用例必须是airtest认可的简洁格式。

### Q3: LLM的具体作用范围？
**A:** 双重作用：
1. **元素识别和定位**：找到控件的resource_id等信息
2. **测试逻辑规划**：自驱动理解测试功能点，一步步捕获屏幕ID并写JSON用例

### Q4: JSON结构中的path字段作用？
**A:** 记录LLM使用工具生成的结果，用于追溯。包含：
- LLM使用了哪个MCP工具
- 截取了哪个屏幕  
- 分析了哪些元素
- 如何找到目标控件的
- 记录用例执行过程中相关信息

### Q5: 双模式识别机制？
**A:** 
- **uiautomator2模式**：速度快，准确率高，但在播放状态下无法获取界面控件布局
- **omniparser模式**：基于AI视觉识别，能识别播放状态下的控件，但速度慢，准确率90%，消耗GPU资源
- **自动切换**：根据播放状态自动选择合适的识别模式
- 对于外部LLM来说其可以不关注，因为当前拥有自动切换机制（播放状态下自动使用omniparser模式）
- **重要要求**：确保omniparser模式返回结果与uiautomator2模式相同

### Q6: MCP工具的具体作用？
**A:** 让外部LLM主动capture当前屏幕，并filter其需要的内容，获取id等控件信息后才能正常确认控件ID等信息，才能写用例。

## 🔧 技术实现详解

### Q7: 播放状态检测机制如何实现？
**A:** 使用ADB命令检测音频播放状态：
```bash
# 非播放状态
adb shell dumpsys media.audio_flinger | grep "Standby: no"  # 返回一条记录
adb shell dumpsys power | grep -i wake | grep Audio        # 仅AudioIn记录

# 播放状态  
adb shell dumpsys media.audio_flinger | grep "Standby: no"  # 返回两条记录
adb shell dumpsys power | grep -i wake | grep Audio        # 包含AudioOut记录
```
具体检测逻辑在 `airtest/lib/visual_recognition/playback_detector.py` 实现。

### Q8: 控件识别的fallback机制是什么？
**A:** 
**流程：**
1. 优先尝试uiautomator2获取控件
2. 如果失败或检测到播放状态，自动切换到omniparser
3. omniparser返回的结果需要转换为和uiautomator2一样的格式（resource_id、bbox等）

**处理策略：**
- **omniparser失败**：抛出警告，暂停生成流程，记录详细的警告信息
- **结果一致性**：通过代码兼容确保最终返回给外部LLM的json是相同的
- **特殊情况**：omniparser只做icon识别，不会返回id等信息，无法构造。当id等字段为空时（依靠 `airtest/templates/prompts/generate_cases.py` 进行prompt驱动外部LLM），直接使用bbox计算出的position进行点击具体坐标

### Q9: LLM工作流程是怎样的？
**A:** 
**标准流程：**
1. 分析当前需要执行的操作（如"进入全屏"）
2. 使用MCP工具capture当前屏幕
3. 自动选择识别模式（不需要LLM主动声明，MCP程序自动侦测状态并切换）
4. 分析识别结果，找到目标控件
5. 记录控件信息到JSON的path字段
6. 生成下一步的测试步骤

**智能决策：**
- **控件理解**：基于LLM对程序的理解能力，找到最像的那个id/name/text进行click
- **多控件选择**：选择概率最高的那个，在description中备注有多个可能，提示用户自己尝试
- **操作成功判断**：使用操作前后的截图进行相似度比较，如果相似度超过99%即为行为失败

### Q10: JSON到PY的转换规则？
**A:** 
**基本转换：**
- JSON中每个step对应一个标准注释 + 一行代码
- `target_element.resource_id` 转换为 `poco("resource_id").click()`
- `path` 字段不转换到PY，只用于调试和追溯
- `pre_action` 和 `post_action` 转换为额外的代码行

**特殊处理：**
- **复杂selector_path**：与多控件选择策略相同
- **坐标点击**：如果是omniparser模式，json中id等字段为空，使用 `poco.click([x,y])` 进行坐标点击
- **条件判断**：代码块使用统一的方式，转换时直接把特殊标志位的内容按顺序写入到py文件

## 🎯 设计理念与架构

### Q11: 为什么要设计这个框架？
**A:** 传统测试框架存在痛点：
- ❌ **硬编码坐标**: 换个设备就失效
- ❌ **静态逻辑**: 无法处理动态UI状态  
- ❌ **复杂编程**: 需要深厚技术背景
- ❌ **维护困难**: UI变更需要重写代码

Only-Test通过**JSON + Python协作架构**解决这些问题，实现"说出你的测试需求，剩下的交给AI"。

### Q12: 核心架构设计思想是什么？
**A:** 
```
自然语言 → LLM理解 → JSON智能元数据 → Python执行代码 → 测试报告
    ↓         ↓           ↓               ↓           ↓
   意图      逻辑        存储            执行        结果
```

**JSON作为智能媒介**：统计友好、AI友好、人类可读、版本控制友好
**Python作为执行载体**：灵活强大、生态丰富、调试友好、扩展性强

### Q13: 为什么需要设备密度适配？
**A:** 同样的UI元素在不同密度设备上大小差异巨大。解决方案包括：
- 🎯 **坐标智能缩放**: 根据密度比例自动调整触摸坐标
- 📸 **截图质量优化**: 高密度设备降低质量减少存储，低密度设备提高质量保证识别
- 🔍 **识别阈值调节**: 高密度图像质量好设置高阈值，低密度图像宽松要求
- 📱 **UI元素预测**: 预测不同设备上元素的实际像素大小

## 🔄 完整工作流程

## ⚙️ 运行环境约定（Conda）

- Python 执行统一使用 Conda 环境 `orun`。
- 本地运行命令建议使用：
  - `conda run -n orun python your_script.py ...`
  - 或使用仓库提供的快捷脚本：
    - Windows PowerShell: `tools/orun.ps1 -- your_script.py --args ...`
    - Bash: `tools/orun.sh your_script.py --args ...`

这可避免全局 Python 与依赖冲突，确保截图/识别/LLM 客户端一致性。

### Q14: 完整的工作流程是什么？
**A:** 核心4步骤工作流：

**步骤1: 智能用例生成**
```bash
# 用户输入自然语言
python tools/case_generator.py --description "测试需求" --app com.mobile.brasiltvmobile
```

**步骤2: 设备信息探测与适配**
```bash
# 自动探测设备信息并更新JSON
python lib/device_adapter.py testcase.json
```

**步骤3: 智能执行与资源保存**
```bash
# 执行测试并保存完整资源
python tools/test_runner.py --file testcase.json
```

**步骤4: 数据回写与代码生成**
```bash
# JSON转换为Python代码
python lib/code_generator/json_to_python.py testcase.json
```

### Q15: 条件分支逻辑如何处理？
**A:** 用户描述"如果搜索框有内容先清空"自动转换为：
```json
{
  "action": "conditional_action",
  "condition": {
    "type": "element_content_check", 
    "target": "search_input_box",
    "check": "has_text_content"
  },
  "conditional_paths": {
    "if_has_content": {"action": "click", "target": "clear_button"},
    "if_empty": {"action": "input", "data": "搜索词"}
  }
}
```

### Q16: 资源路径管理规则是什么？
**A:** 
**命名规范**: `{pkg_name}_{device_name}`
- 示例：`com.mobile.brasiltvmobile` + `Pixel_6_Pro` = `com_mobile_brasiltvmobile_Pixel6Pro`
- 时间戳精确到毫秒: `step01_click_before_20241205_143022_123.png`
- 文件类型明确: `omni_result`, `element_screenshot`, `execution_log`

**存储结构**:
```
assets/
├── com_mobile_brasiltvmobile_Pixel6Pro/    # BrasilTVMobile+Pixel6Pro
├── com_mobile_brasiltvmobile_XiaomiPhone/  # BrasilTVMobile+小米手机
└── com_mobile_brasiltvmobile_HuaweiMate/   # BrasilTVMobile+华为Mate
```

## 🛠️ MCP工具完整清单

### Q17: MCP工具包含哪些功能？
**A:** 基于现有代码和设计，MCP工具包含：

**设备控制工具 (device)**
- **capture_screen**: 截取当前屏幕，LLM主动触发
- **analyze_ui_elements**: 分析界面元素，写json文件
- **detect_playing_state**: 检测播放状态，提供但不常用
- **click_element**: 点击指定元素
- **input_text**: 输入文本
- **swipe_screen**: 上下滑动操作，方便LLM操控设备
- **get_device_basic_info**: 获取设备基础信息
- **get_screen_info**: 获取屏幕信息
- **connect_device**: 连接目标设备

**生成工具 (generator)**  
- **generate_case_with_llm_guidance**: LLM指导的用例生成
- **convert_case_to_python**: JSON到Python转换
- **get_comprehensive_device_info**: 获取综合设备信息

**反馈工具 (feedback)**
- **execute_and_analyze**: 执行并分析测试
- **analyze_execution_result**: 分析执行结果

**工作流程工具 (workflow)**
- **start_complete_workflow**: 启动完整工作流程

## 📊 错误处理和重试机制

### Q18: 重试策略是什么？
**A:** 
- **控件找不到**：重置状态后重新进行到当前这一步后定位
- **omniparser识别错误**：可能fallback到预设坐标
- **操作失败**：LLM分析失败原因并调整策略

### Q19: 失败恢复机制是什么？
**A:** 
- **用例生成失败**：重置状态后重试一次
- **控件无法找到**：尝试重置状态（比如重新进入应用后尝试）
- **系统弹窗拦截**：外部LLM可能无法探查到下层控件信息时的处理

### Q20: 如何判断操作成功？
**A:** 使用操作前后的截图进行相似度比较，如果相似度超过99%即为行为失败。实现要求：找一个库进行相似度判断，一定要留下debug日志，如果行为失败抛出异常。

## 📁 测试数据管理

### Q21: 测试数据如何组织和存储？
**A:** 
**存储组织**
- **统一存储文件**：`testcases/main.yaml` 是设备和testsuits统一存储文件
- **资产路径规则**：`assets/{app}_{device}/` 按应用+设备分类存储
- **命名规范**：遵循 `airtest/README.md` 中定义的资源路径管理规则

### Q22: 状态管理和断点续传如何实现？
**A:** 
**断电续传任务设计：**
- 如果功能点输入被分为5个步骤，外部LLM操作，每完成一个都要记录一次状态
- 下次能查阅history并继续任务
- 状态文件：`workflow_state.json`, `execution_progress.json`, `iteration_config.json`
- 支持工作流程的暂停和恢复

### Q23: 配置回写机制是什么？
**A:** 
**动态配置更新：**
- `device_config.yaml`: 设备连接状态、基础信息、屏幕参数
- `framework_config.yaml`: 屏幕配置、识别参数
- `execution_config.json`: 执行环境配置
- `execution_stats.yaml`: 全局统计信息

**学习积累：**
- 应用UI模式学习数据库
- 元素选择器成功率统计
- 性能参数动态优化记录

## 🎯 测试用例可维护性

### Q24: 如何处理UI变化？
**A:** 
- **小变化**：LLM可以自动适应小的UI变化
- **重大改版**：定向重新生成用例，先不处理自动化更新
- **稳定性保证**：将用例文件转换为代码执行就是在增加稳定性

### Q25: 追溯支持如何实现？
**A:** 
- **path字段**：提供足够的信息用于调试，是一个统称，json中可能包含多个信息
- **执行轨迹**：完整记录每个操作步骤的执行过程
- **资产关联**：截图、分析结果、日志文件的完整关联

## 📁 目录结构说明

### Q26: 核心执行流程文件有哪些？
**A:** 
- **`example_airtest_record.py`** - 🔥 **最重要**：标准用例格式模板，所有生成的用例都要转换成这种格式
- **`json_to_python.py`** - JSON用例到Python执行脚本的转换器
- **`smart_executor.py`** - 智能执行引擎，处理复杂的执行逻辑

### Q27: LLM和MCP集成文件包括什么？
**A:** 
- **`mcp_server.py`** - 为外部LLM提供设备操作能力的MCP服务器
- **`llm_client.py`** - 与外部LLM通信的客户端
- **`workflow_orchestrator.py`** - 协调整个LLM驱动的测试生成流程

### Q28: 视觉识别核心文件是什么？
**A:** 
- **`omniparser_client.py`** - 与Omniparser服务器通信，处理播放状态下的视觉识别
- **`pure_uiautomator2_extractor.py`** - 提取uiautomator2的UI层次结构
- **`strategy_manager.py`** - 管理uiautomator2和Omniparser的智能切换
- **`playback_detector.py`** - 检测播放状态，决定使用哪种识别方式

## 📋 当前架构状态

## 🧭 统一约定与决策（2025-09-10）
- 暂缓处理 wait_for_appearance：录制文件的关键动作，不纳入当前日志与执行硬化范围，后续单独规格化再接入。
- 目录与依赖约定：only_test 为项目根目录，Airtest 为外部 Python 库；代码引用统一使用 airtest.core.*（例如：from airtest.core.api import *）。
- 视觉/XML 一致性：对外统一元素字段集（uuid, text, content_desc, resource_id, class_name, package, clickable, bounds_px[left,top,right,bottom], source, confidence）。视觉侧缺失字段使用空字符串/缺省值但保证字段存在。
- 录制链路：维持“多轮执行→取证→回写工件”的策略，但先不将 wait_for_appearance 纳入强判据，仍以前后对比与必要断言为主。
- 如需调整以上决策，请在本节追加新日期的变更记录。

### Q29: 已实现功能有哪些？
**A:** 基于现有代码：
- ✅ **MCP服务器框架** (`mcp_server.py`)
- ✅ **LLM客户端通信** (`llm_client.py`)  
- ✅ **Omniparser客户端** (`omniparser_client.py`)
- ✅ **设备适配器** (`device_adapter.py`)
- ✅ **JSON到Python转换器** (`json_to_python.py`)
- ✅ **提示词模板系统** (`generate_cases.py`)
- ✅ **工作流程编排** (`workflow_orchestrator.py`)
- ✅ **配置管理系统** (`config_manager.py`)
- ✅ **标准用例格式** (`example_airtest_record.py`)

### Q30: 核心工作流程是什么？
**A:** 
```
外部LLM → MCP工具 → 播放状态检测 → 策略选择 → 
(uiautomator2 或 omniparser) → 生成JSON用例 → 转换为标准Python执行脚本
```

### Q31: 测试用例的自动化程度如何？
**A:** 
**用户输入要求：**
- 提供具体的功能点描述，足够清晰，不是大而泛的描述
- 示例：\"测试vod点播播放正常: 1.进入APK后就是首页，执行关闭广告函数，2.找到searchbtn点击，直到可输入状态后输入节目名称'720'点击第一个节目，3.播放节目，断言: 验证设备是否处于播放状态\"

**自动化能力：**
- LLM自动规划测试路径（启动应用→搜索→播放→全屏）  
- LLM自动找到每个步骤需要的控件
- 最终生成完整可执行的测试用例

**异常处理：** 异常情况目前不考虑，直接设计为抛出并记录异常情况即可

### Q32: 性能和准确性如何平衡？
**A:** 
**策略：**
- 优先使用快速的uiautomator2
- 只在播放状态时使用omniparser  
- omniparser的90%准确率的10%错误无需理会，后期会确保准确率
- 暂不考虑缓存机制和性能监控

---

## 📝 最终总结

**Only-Test项目基于现有设计已经具备了完整的架构框架，核心理念是：**

1. **让外部LLM通过MCP工具实时感知设备状态**
2. **智能选择最合适的UI识别策略**  
3. **生成符合airtest标准格式的可执行测试用例**
4. **提供完整的执行追溯和状态管理能力**

**下一步重点是完善播放状态检测、策略切换逻辑和MCP工具的具体实现。**

---

*基于airtest目录现有代码和设计文档整理*  
*最后更新: 2025-09-09*  
*状态: 基于现有架构的确定答案*


## Addendum: Insights and Aggregated Q&A

### My Insights (from code + QA.md)
- Dual recognition must normalize to a single element schema (uuid, resource_id, text, content_desc, clickable, bounds, class, package, source). Current code converts OmniParser bbox to bounds; ensure ScreenCapture screen size is used for correct scaling.
- Playback detection drives strategy; fallback from visual→XML or XML→visual should return identical shape so the executor remains agnostic.
- JSON ‘path’ provenance is critical for reproducibility; prefer storing tool, screen hash, selectors, and decision rationale per step.
- Persist workflow state (workflow_state.json, execution_progress.json) to resume iterations and inform LLM on the next pass.
- Asset layout and timestamps are part of debuggability; align with assets/{pkg}_{device}/ and store omni_result and step screenshots consistently.

### Q&A from airtest/README.md
- Q: What’s the core value proposition?
  A: ‘Write Once, Test Everywhere’ using JSON as a planning medium and Python (Airtest+Pytest+Allure) for deterministic execution.
- Q: Why JSON + Python?
  A: JSON is LLM- and diff-friendly; Python executes complex logic with strong tooling.
- Q: Why care about screen density?
  A: Element sizes vary by device; density affects scaling, OCR thresholds, and visual heuristics.
- Q: What’s the typical flow?
  A: Natural language → LLM JSON → device probing → execution & artifact writing → JSON→Python → run → report.
- Q: Where are artifacts stored?
  A: assets/{pkg}_{device}/ with stepNN_before/after screenshots, omni_result, logs.

### Q&A from airtest/WORKFLOW_GUIDE.md
- Q: What does the MCP workflow orchestrate?
  A: Device connection, screen capture, UI extraction, LLM planning, conversion, execution, feedback, and iteration.
- Q: How are MCP tools categorized?
  A: device, generator, feedback, workflow, custom.
- Q: What gets persisted?
  A: Device/screen info in configs, workflow_state.json, current_ui_elements.json, and generated testcases under testcases/generated.
- Q: What’s required from LLM?
  A: Generate structured steps with selectors, reasons, and conditions; adhere to schema and include provenance.

### Open Questions for You
- Do we have a canonical JSON schema for ‘execution_path’ and ‘path’ fields (final keys, allowed actions), or should I lock one in now?  I dontknow you question 
- What is the official Omniparser server endpoint(s) for CI/dev (IPs change across docs)? just use 100. prefix IP, it's a server depoloyed Omniparser, 
- Should screenshots come from ADB or the ScreenCapture abstraction by default (to avoid platform differences)? anyway pls U confime this things 无需问我
- Any specific success thresholds for image similarity and when to fall back to alternative verification? 99% is cureent thresholds for determine is screen change, 
-  Preferred language for documentation (current files mix Chinese/English; I can unify if desired). yeah pls use chinese, only for document, codeing also english 
## ✅ 实现状态总览（复核）
- MCP + LLM（外部）生成用例
  - 已实现：通过 `test_mcp_llm_integration.py`（Mock）与 `airtest/examples/mcp_llm_workflow_demo.py` 跑通“人给 Plan → MCP 工具（模拟外部 LLM）→ 生成 JSON → 转 Python”。
  - 待改进：接入真实 LLM Provider（按 `lib/llm_integration/llm_client.py` 配置），规范工具入参/回参。
- JSON 结构与转换
  - 已实现：`lib/code_generator/json_to_python.py` 支持常规步骤与 `conditional_action` 条件分支；转换可执行 Python。
  - 待改进：补齐 `path` 溯源字段（工具、屏幕哈希、选择器、决策理由）并在执行期保存。
- 视觉/XML 双模识别
  - 已实现：`strategy_manager.py` + `element_recognizer.py` 基于播放状态选择策略，XML→视觉 fallback；视觉 bbox 已按屏幕尺寸转换为像素 bounds。
  - 待改进：当前 OmniParser 样例输出为 `coordinates` 且无 `uuid/interactivity`；需增加 Normalizer 统一产出（uuid/content/bbox/interactivity）。
- 播放检测与恢复
  - 已实现：`visual_recognition/playback_detector.py` 的 ADB 检测；`execution_engine/smart_executor.py` 的基础恢复与截图日志。
  - 待改进：错误分类与上报、相似度阈值配置化（现参考 99% 判定屏幕变化）。
- 资产与命名规范
  - 已实现：`assets/{pkg}_{device}/` 命名与工件落库（步骤截图、omni 结果、执行日志）。
  - 待改进：工作流状态类文件 `workflow_state.json`、`execution_progress.json`、`iteration_config.json` 的落盘与续跑逻辑。

> 结论：核心闭环已跑通；为完全对齐本 QA 文档，需要补齐溯源字段、视觉输出归一化、工作流状态落盘与错误分类。



  - 用例最终输出样式：是否明确要求“脚本式（与 example_airtest_record.py 基本一致）”？若是，我就为 JSON→Python 新增“脚本式模板”并切换。
  首先 答案是 是, 这个收工写的脚本解基本就是我理想样子, 也便于使用 airtest run.而 这个请先检查是否已存在转换的脚本, 如果不能使用则需要你来check 为什么, 打造一个完整的
  - OmniParser 服务：你前面允许使用 100.* 段内网地址；我会按此默认配置（后续可提到 framework_config）。
  - 截图来源：目前执行器路径使用 ADB 截图；若要统一用 ScreenCapture 抽象（避免平台差异），我可以切换。
  可以统一使用 ScreenCapture, 请把它迁移到 airtest 目录下,  因为 airtest 就是 only-test, 其它目录是给你参考的数据
  - path 溯源字段：请确认字段内容（工具名/屏幕哈希/选择器/理由）是否按 QA.md 示例固定下来。
  path 你先按照你想的来, 便于追溯与方便阅读的, 如果有问题我再纠正
  还有一点重要的需要你明确, 外部 LLM 根本不知道如何生成一个用例, 不知道要做什么, 不知道如何编排使用 MCP,  请你善用C:\Download\git\uni\airtest\templates\prompts\generate_cases.py  prompt 定义和标签定义, 目前可能并不完善, 我需要你精通掌握后修改它们到最优 C:\Download\git\uni\airtest\templates\prompts\


  - 接入“脚本式模板”，使生成的 Python 更接近 example_airtest_record.py。
  - 加入 OmniParser Normalizer（coordinates→标准字段：uuid/content/bbox[0-1]/interactivity+像素 bounds），保证 XML/视觉统一结构。
  - 实现 path 溯源与工作流状态落盘（workflow_state.json、execution_progress.json、iteration_config.json），并在 Orchestrator 中串起来。
  - 固化 MCP 工具的入参/出参协议，以便真实 LLM 长期可用。


## 🆕 统一约定与决策（2025-09-11）

本节记录最近一轮关于“如何让外部 LLM 使用 MCP 生成真实、可执行用例而非臆造”的问答结论与落地改动。

### 背景问题
- 用外部 LLM 生成的用例经常“幻想 ID/选择器”，没有基于真实屏幕元素；一次性吐出多步；不做执行后的验证与回灌，导致不可执行。

### 选用方案与理由（核心）
1) TOOL_REQUEST 协议（拒绝臆造）
- 无屏幕数据/不可信时，LLM 只能返回 `tool_request: analyze_current_screen`，而不是凭空编造 ID。
- 理由：把“数据获取权”交还给 MCP/Orchestrator，让 LLM 没法凭空生成元素。

2) 单步握手（Plan → Execute → Verify → Append）
- LLM 每次“只产出一个下一步”，Orchestrator 执行并再次分析屏幕，然后进入下一轮。
- 理由：把“录制式”的节奏还原为一步一取证，避免一次性长文本偏离现实。

3) 白名单绑定 + 机读校验（step_validator）
- 选择器必须来自 `elements` 白名单；`bounds_px`（如提供）必须与所选元素 `bbox` 完全一致；支持 `page_check_mode`（off/soft/hard）；返回 `chosen_element` 用于链路构建。
- 理由：把“是否真实存在”从自然语言判断转为机读校验，彻底遏制幻想选择器。

4) evidence/path/chain（可追溯）
- evidence：`screen_hash`、`source_element_uuid`、`source_element_snapshot`
- chain（权威链路）：nodes 记录 step/page/action/selector/uuid/screen_hash_before/after/human_line，edges 串起路径；由 Orchestrator 执行后生成。
- 理由：把“为什么选它、前后屏幕如何变化”固化下来，便于复现与比对。

### JSON vs Python（源/工件分离）
- JSON 作为“权威源”，Python 作为“生成工件”。
- 新增 JSON Schema：`only_test/tools/json_schema/testcase.schema.json`
  - 支持 `type=ui|tool`；`priority_selectors/bounds_px/swipe` 等；每步 `expected_result`。
- 代码生成器：`only_test/tools/codegen/json_to_airtest.py`
  - 动作映射：restart→3x stop_app；launch；click；input（sleep(0.5)+text）；wait_for_elements（出现/消失）；swipe；assert(TODO)；
  - 工具映射：close_ads、connect_device、click_center_of；
  - 其它：
    - 合并选择器：`poco(resourceId="...", text="...")`
    - 输出中文：`ensure_ascii=False`
    - `--business_path` 选项：生成业务路径头 `[path]`（剔除 app_initialization/app_startup）
    - 提前 hoist connect_device 到 poco 初始化之前
    - sys.path 加入 project_root，`from lib import ...` 生效
- golden JSON 更新：`only_test/testcases/generated/golden_example_airtest_record.json`
  - 去掉 bias 点击；Ads 消失后加 `wait_after=0.5`；新增 `click_center_of`（在全屏前点击视频中心唤起控件）；连续编号
- 生成结果：
  - `only_test/testcases/python/golden_from_json.py`（完整路径头）
  - `only_test/testcases/python/golden_from_json_business.py`（业务路径头）
- 理由：结构化的 JSON 更利于校验与自动转换；Python 工件保持与录制脚本“风格一致”，降低上手成本。

### 示例文件（Few-shot）注入与过滤
- 例子选择器：`only_test/tools/select_examples.py`
  - 仅选取精心维护的 `.py` 用例；排除生成工件（文件名包含 `from_json` 或位于 `generated`）
  - 小库（≤3）全量附带；大库（>3）精确取 3 个，并支持内容裁剪（trim）
- 例子“摘要”器：`only_test/tools/digest_examples.py`
  - 从 `.py` 中提取 `## [page]/[action]` 行，作为轻量 few-shot
- Prompt 已嵌入 few-shot 区块并附带“禁止复制选择器/坐标”的硬性声明（见 `templates/prompts/generate_cases.py`）。
- 理由：用示例教授“节奏/粒度”，而不是复制“选择器”；约束+校验保证安全。

### Prompt 状态
- `get_main_generation_prompt`：已加入 TOOL_REQUEST、单步输出、白名单绑定/evidence、Few‑shot + 禁止复制声明。
- `get_mcp_step_guidance_prompt`：已具备严格结构与约束；可选再补一句“示例只用于节奏参考，严禁复制选择器”（目前非必须）。

### 其它工程细节
- `page_scope`：在 validator 中以 `soft|hard` 检查，保证步骤落在允许页面。
- `content_desc` → Poco 参数名：默认使用 `description=`，若驱动差异可在生成器里调整。
- 中文变量：生成 Python 时不再转义（ensure_ascii=False）。

### 后续可选项
- 在 golden JSON 中加入 `connect_device` 工具步，实现自动设备连接（现生成器已支持）。
- 在 Orchestrator 中自动调用 `select_examples.py` 注入示例到 Prompt。
- 提供 JSON Schema 校验 CLI，确保编写期即可发现结构问题。

> 结论：这一套“TOOL_REQUEST + 单步握手 + 白名单绑定 + 机读校验 + 证据链 + 结构化 JSON + 代码生成”的组合，既能压制 LLM 幻想，又保持了录制脚本的使用体验，后续可平滑拓展。




本节补充此前未在 QA.md 明确记录、但对工程落地至关重要的“项目逻辑”。如有不确定之处，我以「[QUERY]」标注等待确认。

### 1) Orchestrator 总控流程（Plan → Execute → Verify → Append）
- 输入：test_objective、tags、page_scope（可选）
- 初始化：调用 `analyze_current_screen()` 获取 {screen_hash, current_page, elements}
- 循环（最多 N 步）：
  1. 构造 Prompt（带 Few-shot 示例）→ 调用 LLM → 产出两种之一：
     - tool_request（name=analyze_current_screen）
     - 单步决策（analysis/next_action/evidence）
  2. 若 tool_request：再次 `analyze_current_screen()`，继续下一轮
  3. 若单步：调用 `validate_step(screen, step, page_check_mode, allowed_pages)`
     - 白名单绑定检查、bounds 与 bbox 一致性、页面一致性（soft/hard）、结构检查
  4. 通过则执行 `perform_ui_action(step)`，记录耗时
  5. 执行后再次 `analyze_current_screen()` 得到新屏
  6. 记录 execution_path 条目与 chain node（step/page/action/selector/uuid/screen_hash_before/after/human_line/meta）
  7. 更新 screen，继续下一轮；可在达到目标或失败时中止
- 输出：
  - llm_generated*.json（包含 execution_path + chain + final_screen）
  - 可选：生成 Python（json_to_airtest.py）

### 2) Validator 规则（step_validator）
- 允许动作：click/input/wait_for_elements/wait/restart/launch/assert/swipe
- 选择器键：resource_id/text/content_desc（蛇形命名）；必须来源于 elements 白名单
- bounds 规则：如提供 bounds_px，必须与所选元素 bbox 完全一致；否则不得提供
- 页面一致性：page_check_mode = off|soft|hard；allowed_pages = page_scope
- evidence 校验：screen_hash 一致、source_element_uuid 对应 chosen_element、snapshot.uuid 一致
- 返回值：ok、errors（WARN(page): 前缀为软告警）、chosen_element（用于链路）

### 3) Evidence / Path / Chain（可追溯）
- evidence（随单步决策返回）：
  - screen_hash、source_element_uuid、source_element_snapshot（原样贴元素）
- path（可选）：mcp_tool_used、analysis_result/decision_reason、screen_hash_before 等
- chain（由 Orchestrator 生成）：
  - nodes: step/page/action/selector/element_uuid/screen_hash_before/after/result/human_line/meta(tags,page_scope)
  - edges: [{from, to}, ...]
- 建议：最终结果 JSON 中包含 chain；执行期将截图/日志落盘以便对照

### 4) JSON Schema 关键字段（简述）
- 顶层：testcase_id/name/description/target_app/metadata(tags,page_scope)/variables/execution_path/assertions
- execution_path.step：
  - type: ui|tool
  - action: launch|restart|click|input|wait|wait_for_elements|assert|swipe（ui 时必填）
  - tool_name: close_ads|connect_device|click_center_of|...（tool 时必填）
  - target: priority_selectors|bounds_px|swipe|disappearance|bias(不再推荐)
  - data/timeout/wait_after/expected_result
- 规范：去除 bias 依赖；鼓励选择器 + wait_after 细化稳定性

### 5) 代码生成映射（json_to_airtest.py）
- restart → stop_app×3 + sleep(timeout)
- launch → start_app + sleep(timeout)
- click → poco(...).click()（选择器组合：resourceId + text + description）
- input → sleep(0.5) + text("…")（变量 `${var}` 解析为 variables[var]）
- wait_for_elements → wait_for_disappearance/appearance(timeout)
- swipe → swipe([sx,sy],[ex,ey],duration)
- assert → TODO（等待规范）
- 工具：
  - close_ads → asyncio.run(close_ads(...))
  - connect_device → connect_device(uri)（poco init 前 hoist）
  - click_center_of → get_position() + poco.click([cx, cy])
- 其它：
  - 中文字符串 ensure_ascii=False
  - `--business_path` 生成业务路径头（剔除 app_* 页面）
  - sys.path: 注入 repo_root + project_root

### 6) Prompt 集成（Few-shot 示例）
- 示例选择：`only_test/tools/select_examples.py`（过滤生成工件，≤3 全量，>3 取 3 个，支持 trim）
- 示例摘要（可选）：`only_test/tools/digest_examples.py` 提取 `## [page]/[action]` 行
- Prompt 声明（已加入）：
  - 示例仅用于“节奏/粒度”参考；严禁复制选择器/坐标
  - 选择器必须来自 MCP 返回的 elements 白名单；bounds 必须等于 bbox
- 使用：把 examples 传入 `get_main_generation_prompt` / `get_mcp_step_guidance_prompt`

### 7) Tags & page_scope
- tags：用于 few-shot 选择与策略（如播放场景优先视觉识别）
- page_scope：用于限制可执行页面（validator soft|hard 检查）；同时写入 chain.meta

### 8) 失败处理与重试（基线）
- 结构/白名单/页面错误 → 返回错误给 LLM 修复（同一屏）
- 执行失败（脚本层异常）→ 暂以报错为主，可逐步加入重试（比如 wait_for_elements 的出现→消失）
- 建议后续将失败分类与重试策略配置化（per action/per page）

### 9) 命名与落盘
- JSON 源：`only_test/testcases/generated/*.json`
- Python 工件：`only_test/testcases/python/*.py`
- 业务路径头：可生成 `*_business.py` 做审阅与回放
- chain：作为结果 JSON 的一部分；截图/日志落到 assets/{pkg}_{device}/

### 10) [QUERY] 
- [QUERY] 屏幕“页面字段”统一使用 `current_page` 吗？若使用 Activity 名称，字段名是否约定为 `current_activity`？二者是否同时提供？
- [QUERY] Poco 对 content_desc 的参数名是否一律使用 `description=`？是否存在机型/驱动差异需要额外适配？
- [QUERY] assert 步骤的标准实现：
  - 是否以“播放检测”为主（ADB audio/相似度阈值=99%）、或加上 UI 文案存在性检查？
  - 断言模板函数名/位置（例如 only_test/lib/assertions.py）？
- [QUERY] connect_device 的 URI 规范与来源（是否从变量/配置注入），是否默认在所有用例开头自动生成该工具步？
- [QUERY] path/evidence 的最终字段集合是否固定为（tool/screen_hash/selectors/decision_reason）？是否需要记录 `screen_hash_before/after` 在 path 中，还是只在 chain 中？
- [QUERY] 示例注入策略默认使用完整代码还是摘要 digest？单轮最大 tokens 预算？
- [QUERY] 默认超时策略与全局配置：如 restart/launch/wait_for_elements 的缺省 timeout 与 wait_after 是否集中可配？
- [QUERY] 生成的 chain 是否与测试报告（Allure 等）联动？是否将 chain/截图链接到报告中？




  1. 屏幕页面字段统一规范

  ✅ 建议统一使用 current_page
  # 当前代码已使用current_page作为默认字段
  PAGE_FIELD_DEFAULT = "current_page"  # step_validator.py:88

  # 同时支持current_activity作为辅助信息
  screen_info = {
      "current_page": "home",          # 业务页面(主要)
      "current_activity": "MainActivity", # 技术Activity(辅助)
  }
  决策: 二者同时提供，current_page用于业务逻辑，current_activity用于技术调试

  2. Poco content_desc 参数名规范

  ✅ 统一使用 description=
  # 基于代码分析，使用标准参数名
  poco(resourceId="xxx", description="关闭", text="确定").click()
  决策: 一律使用 description=，如有驱动差异在转换器中适配

  3. Assert 步骤标准实现
  ✅ 建议混合策略
  # 位置: only_test/lib/assertions.py
  def assert_playback_state(expected: bool) -> bool:
      """播放状态断言 - 使用ADB检测"""

  def assert_ui_element_exists(selector: dict) -> bool:
      """UI元素存在性断言"""

  def assert_screen_changed(threshold: float = 0.99) -> bool:
      """屏幕变化断言 - 相似度阈值"""
  决策: 以播放检测为主(99%相似度)，UI文案检查为辅

  4. connect_device URI规范
  ✅ 建议配置化注入
  # 来源: yaml -> variables -> JSON
  {
    "variables": {
      "device_uri": "android://127.0.0.1:5037/192.168.100.112:5555?touch_method=ADBTOUCH&"
    }
  }
  决策: 默认在所有用例开头自动生成，URI从配置注入

  5. path/evidence 最终字段集合

  ✅ 建议精简但完整
  # path字段 (每步记录)
  "path": {
      "mcp_tool_used": "get_current_screen_info",
      "screen_hash": "abc123",
      "decision_reason": "选择搜索按钮因为...",
      "selectors_tried": ["resource_id", "text"]
  }

  # evidence字段 (单步决策)
  "evidence": {
      "screen_hash": "abc123",
      "source_element_uuid": "elem_001",
      "source_element_snapshot": {...}
  }

  # chain字段 (执行后生成)
  "chain": {
      "nodes": [...],
      "edges": [...],
      "screen_hash_before": "abc123",
      "screen_hash_after": "def456"
  }
  决策: screen_hash_before/after只在chain中，path保持轻量

  6. 示例注入策略

  ✅ 建议智能选择
  # 策略: 小库全量，大库摘要
  if len(examples) <= 3:
      use_full_code(examples)  # 完整代码
  else:
      use_digest(examples[:3])  # 前3个摘要

  # tokens预算: 单轮最大8K tokens
  MAX_EXAMPLES_TOKENS = 8000
  决策: 默认使用摘要digest，保持prompt简洁高效

  7. 默认超时策略

  ✅ 建议集中配置
  # yaml
  timeout_defaults:
    restart: 5
    launch: 10
    click: 5
    input: 3

  决策: 集中配置，支持运行时覆盖

  8. Chain与测试报告联动

  ✅ 建议深度集成
  # 生成Allure报告时自动注入
  @allure.step("执行步骤 {step_num}: {description}")
  def execute_step_with_chain(step, chain_node):
      # 自动attach截图和决策过程
      allure.attach.file(chain_node["screenshot"], "执行前截图")
      allure.attach(chain_node["decision_reason"], "决策理由", allure.attachment_type.TEXT)
  决策: 是，chain数据自动生成测试报告附件