# 未完成需求（Backlog）与动机说明

更新时间：2025-09-19
维护者：Only-Test 项目

目的：将当前讨论的想法沉淀为明确的“未完成需求”，并记录每一项的动机（为什么做）、范围、设计要点、验收标准、风险与时间预估，便于后续实施与沟通。

参考文档：
- PROMPTS_OVERVIEW.md（提示词组织与阶段关系总览）
- ONLY_TEST_SCALING_AND_RUNTIME_HARDENING.md（规模化与运行时硬化指南）

---

一、背景与当前问题
- 纯“规划/Prompt”无法化解低层不确定性（输入框焦点、IME 行为、广告遮挡、页面时序）。
- 录制/回放容易在细节处失真，例如：输入框未激活直接 text()、误点取消、广告/弹窗导致步骤漂移。
- 要实现“可复现、可规模化”，需要“LLM 决策 + 执行器护栏 + 验证闭环 + 失败恢复链”。

二、目标（可量化）
- 2–4 周内在“搜索→播放”黄金链路上：
  - 单机稳定通过率 ≥ 80%
  - 平均执行时长较人工回放缩短 ≥ 30%
  - Flake 率（非确定性失败）降低 ≥ 50%
- 将这套护栏与流程沉淀为可复用资产，支持同类 APK 迁移。

---

R1. 在提示词中落地 on_fail，并让执行器识别与执行（高优先级）
1) 动机（Why）
- 将“失败恢复（重试/回退/诊断）”变成 LLM 输出的“第一公民”，执行器据此驱动“动作→验证→恢复”的闭环，显著降低时序/焦点/IME/遮挡类不确定性。
- 让“可恢复性”成为步骤级别的契约，而不是事后补救。

2) 范围（Scope）
- 扩展 Step JSON 结构：每步包含 on_fail 字段（retries、retry_delay_s、re_focus、fallbacks、diagnostics）。
- 更新 prompts：在 get_mcp_step_guidance_prompt / completion prompt 中明确 on_fail 的结构与约束，Few-shot 示例必须包含 on_fail。
- 执行器新增统一入口 execute_step_with_recovery()，逐步执行并应用 on_fail。

3) 设计要点
- 统一 on_fail 结构（示例）：
```json
{
  "retries": 2,
  "retry_delay_s": 0.3,
  "re_focus": true,
  "fallbacks": [
    {"type": "ime_text"},
    {"type": "press_enter"},
    {"type": "alt_selector", "selector": {"class_name": "android.widget.EditText"}}
  ],
  "diagnostics": ["screenshot", "dump_hierarchy"]
}
```
- 执行器流程：perform_action → verify_expected →（失败）→ re_focus → 逐个 fallback → 诊断 → 等待 → 重试；每轮可通过 MCP 刷新屏幕白名单。
- 输入动作护栏（guarded_actions）：优先 set_text，验证 get_text；失败再走 IME；可选重聚焦/清空重输。

4) 验收标准
- prompts 中能产出包含 on_fail 的规范 JSON（严格 JSON、蛇形命名）。
- 执行器对 on_fail 正常解析与执行；失败时能按策略链自愈；生成结构化日志与诊断。

5) 风险与缓解
- 风险：fallback 类型过多导致实现膨胀；缓解：优先覆盖输入/提交/广告三类高频。
- 风险：LLM 输出不一致；缓解：在 prompt 中强制字段名与列表结构，增加校验。

6) 里程碑/时间预估
- D1：prompt 文案与示例更新；定义 on_fail schema。
- D2：step_executor 与 guarded_actions 落地，打通 demo。

---

R2. 基线用例 JSON + 一键运行 + 报表（高优先级）
1) 动机（Why）
- 需要“可复现”的评估与汇报基线，便于回归与对比（改动是否改善了稳定性/时长）。
- 一键运行与报表可以让团队非代码成员也能复核与验收。

2) 范围（Scope）
- 将“搜索→播放”链路保存为 sessions/baselines/TC_brasiltvmobile_search_play.json（含 on_fail）。
- 新增 CLI：only_test/tools/run_case.py 支持：读取 JSON → 执行 → 汇总 → 输出 JSON/Markdown 报表。
- 新增 reporters：json_reporter.py、markdown_reporter.py。

3) 设计要点
- 入口：`python only_test/tools/run_case.py --case <file> --report-dir <dir> --formats json,md [--device-url <adb_url>]`
- 报表字段：用例信息、每步结果（耗时/重试/fallback/诊断）、总体结论、关键失败原因 Top-N。

4) 验收标准
- 一条命令完成执行与报表产出；报表包含关键指标；路径与命名规范；失败可复核（有截图/层级）。

5) 风险与缓解
- 不同设备差异：支持 --device-url 覆盖；长期引入设备画像。

6) 里程碑/时间预估
- D2：实现 run_case 与 reporters；将基线 JSON 入库；试跑。

---

R3. 一页纸 Case Study 模板 + 自动填充关键指标（中优先级）
1) 动机（Why）
- 用“业务语言”讲清楚问题→方案→指标→风险→下一步，降低沟通成本，提升认可度与可扩展性。
- 结合报表结果自动填充关键信息，形成周更/迭代节奏。

2) 范围（Scope）
- 新增模板：docs/case_studies/CS_vod_search_play.md
- 运行后在 out/reports 中生成该一页纸的实例，填入通过率/时长/flake 率/失败 Top-N/产物链接。

3) 设计要点
- 模板字段占位符：<PASS_RATE>、<AVG_TIME>、<FLAKE_RATE>、<TOP_CAUSES>、<REPORT_LINK>

4) 验收标准
- 能生成一页纸文件，管理者可直接阅读并转发；截图/报表链接有效。

5) 风险与缓解
- 指标口径不一致：在 reporters 中统一计算逻辑与定义。

6) 里程碑/时间预估
- D3：模板与自动填充对接 run_case 输出。

---

R4. 原子操作库（guarded_actions）通用化（中优先级）
1) 动机（Why）
- 聚焦高风险动作的稳定性，减少长尾 flaky；可跨用例、跨 APK 复用。
2) 范围（Scope）
- input_safe、click_safe、wait_for_disappearance_safe、press_enter_safe 等；统一返回值与诊断。
3) 验收标准
- 将 example_airtest_record.py 中输入/点击改造为库函数后，通过率提升且日志更清晰。

---

R5. 页面签名识别与自纠偏（中优先级）
1) 动机（Why）
- 页面误跳转/未跳转时能尽早发现并回到正确轨道，减少连锁失败。
2) 范围（Scope）
- 定义每个页面的 signature（关键元素集合或规则）；验证不通过则回退/重新导航。
3) 验收标准
- 错页识别率高；自纠偏能将错误中断率降至可接受范围。

---

R6. 可观测性与数据飞轮（中优先级）
1) 动机（Why）
- 用结构化数据持续改良 prompts 与策略链；形成少量样例的“经验复用”。
2) 范围（Scope）
- 结构化日志、会话 JSONL、失败截图/层级；从报表中挖掘 Top 失败原因并回灌。
3) 验收标准
- 每周能导出一份“失败分类与改进建议”报告；Few-shot 案例库持续增长。

---

R7. 跨 APK 迁移（Profile 策略）（低/中优先级）
1) 动机（Why）
- 公司有多款“操作方式相近”的 APK；希望一套用例快速迁移。
2) 范围（Scope）
- 定义每个 APK 的 profile：canonical selectors、备选 selector、页面签名、广告策略差异。
3) 验收标准
- 同类 APK 上，迁移/适配成本显著降低（≤20% 人工调整）。

---

R8. Prompt registry / 版本化（低优先级）
1) 动机（Why）
- 当前 prompts 分散；需要中心化索引、版本与变更说明，避免“无意识破坏”。
2) 范围（Scope）
- 建立 PromptRegistry；引入版本号与 Changelog；为关键 prompt 提供测试样例。
3) 验收标准
- 变更可追踪；回滚与对比更容易；新成员易上手。

---

三、时间轴（建议）
- 第 1 周：R1（on_fail + 执行器闭环）
- 第 2 周：R2（一键运行+报表）
- 第 3 周：R3（一页纸 Case Study）+ R4（原子操作库覆盖高频动作）
- 第 4 周：R5（页面签名）+ R6（数据飞轮）

四、成功判定
- 指标达标（通过率/时长/flake 率）
- 基线用例一键运行可复现，报表/一页纸可对外展示
- 在另一个同类 APK 上完成首条链路迁移并可稳定运行

五、已知风险与应对
- 设备/ROM 差异：引入设备画像与可配置超时/偏移参数
- 广告/弹窗黑名单不全：建立动态规则与人工标注通道
- LLM 输出漂移：prompt 加强结构约束与校验、反馈数据回灌 Few-shot

—— 以上为“未完成需求”清单，将按优先级推进。

---

新增：你已确认采纳与需讨论的项（2025-09-19）


B. 需进一步讨论后再立项（设计取舍）
B1) 将播放/广告/全屏等常见判定包装为复用校验器，并暴露 MCP 工具
- 你的担忧：工具过多会让 LLM 混淆“何时用何工具”，解耦也难。
- 建议设计（不增加 LLM 端工具复杂度）：
  - 双通道策略：
    - LLM 通道（对外最小集）：仅 expose analyze_current_screen（+ start_app/close_ads 可选）。
    - 执行器通道（内部使用）：提供“探针聚合”接口 probe_app_state(probes=["playback","ads","fullscreen"])；由执行器在验证 validators 时自动调用，LLM 不直接感知。
  - 优点：LLM 工具面保持极简；验证层获得所需信号；避免“何时用何工具”的心智负担。
  - 取舍：先实现最少 3 个探针（playback/ads/fullscreen），其余按需补充。
- 结论/实现方式（已同意）：
  - 以“validator 方式”实现内部探针，单一类型配参数调用。例如：
    ```json
    {
      "type": "app_state",
      "checks": { "playback": "playing", "ads": "absent", "fullscreen": true },
      "timeout_s": 8,
      "poll_interval_s": 0.5
    }
    ```
    - 执行器在校验 validators 时根据 checks 触发内部探针，无需在 LLM 工具面暴露新的 MCP 工具。
  - LLM 工具面保持极简（analyze_current_screen 等），避免“何时用何工具”的认知负担。
- 待确认点：后续是否需要拆分为多种语义化 validator（如 playback_state/ads_absent/fullscreen_state）以便更细粒度统计；当前先用 app_state 聚合型。

B2) “相似度计算/评分规则/输出 JSON 片段”抽到共享模板是做什么？
- 问题澄清：现在多个 prompt 文件里存在重复的评分规则、标准 JSON 片段与规范声明，长期会产生漂移与矛盾。
- 建议做法：
  - 新增 only_test/templates/constants/prompt_fragments.py，集中维护：
    - 严格 JSON 输出片段（TOOL_REQUEST、next_action、on_fail、validators 示例）
    - 相似度/评分公式的统一文案
    - 关键约束（蛇形命名/白名单/坐标整数化）
  - 各 prompt 通过占位符拼接这些常量。目的不是改变功能，而是“消重与一致化”。
- 成本/收益：改动小、收益在中长期（维护与一致性）。
- 待确认点：是否接受先抽离最常用片段（TOOL_REQUEST/next_action+on_fail/validators）？

B3) 强化 uiautomator2 与 omniparser 的对齐器（canonical element 的意义）
- 你的疑问：两者交集只有 bbox→position，其他字段很多场景不存在（视觉侧无 resource_id 等），为何要统一？
- 解释目的：不是“虚构”字段，而是统一“元素对象的外观”与“证据载体”，便于：
  - 白名单绑定：当存在 XML 信息时，selectors 可直接来源于 resource_id/text/content_desc；当仅有视觉信息时，允许 bounds_px + evidence.source_element_snapshot（含 bbox、source:"vision"、confidence）。
  - 校验一致性：执行器能统一校验“bounds 与元素 bbox 一致”“来源/置信度记录”，而不需要两套分支逻辑。
- 建议的最小 canonical 结构（缺失即为 null，不伪造）：
```json
{
  "uuid": "hash(bbox+source+text?)",
  "resource_id": null | "com.xxx:id/...",
  "text": null | "...",
  "content_desc": null | "...",
  "bbox": [l,t,r,b],
  "center_x": 123.0,
  "center_y": 456.0,
  "source": "xml" | "vision",
  "confidence": null | 0.0-1.0
}
```
- 执行原则：
  - 优先 xml（uiautomator2）；播放/视频场景回退 vision（omn iparser）；两者并存时可合并为去重后的元素集（按 bbox IoU 与文本近似）。
  - LLM 仍然被强制从“elements 白名单”拷贝 selectors；若仅 vision，可不填 selectors，仅给 bounds_px，并在 evidence 中粘贴该元素对象用于机判。
- 交付建议：先在返回结构中统一字段（允许 null），不强行引入不可得字段，达到“统一外观，简化验证代码”的目的。
- 前置调研（已完成）：基于当前代码阅读确认现状
  - Omniparser（only_test/lib/visual_recognition/omniparser_client.py）返回元素字段：uuid, type, bbox(0~1), interactivity, content, center_x/center_y。
  - VisualIntegration._recognize_with_omniparser 将 bbox 归一化转换为像素，输出统一字段：uuid, text(=content), content_desc(=content), clickable, bounds(像素), class_name(=type), package(空), source="omniparser"。
  - XML（pure_uiautomator2_extractor.UnifiedElement）产出字段：uuid, text, resource_id, content_desc, package, class_name, clickable, bounds(归一化)，source="xml_extractor"；VisualIntegration 在使用时按需将归一化转换为像素。
  - 现存差异：有处校验逻辑使用 element.bbox（像素）对比，而大多数管线使用 element.bounds（像素/或归一）；需在校验层统一约定（建议：校验层接受 bounds 优先，若无则回退 bbox；生成 screen_info 时同时提供 bbox=像素，保持兼容）。
- 实施建议（不伪造字段）：
  - 统一对外“最小外观”：
    ```json
    {
      "uuid": "...",
      "text": "...",
      "resource_id": "" | null,
      "content_desc": "..." | "",
      "clickable": true|false,
      "bounds": [l,t,r,b],      // 像素
      "bbox": [l,t,r,b],        // 同步提供，等于 bounds，供历史校验代码使用
      "package": "..." | "",
      "class_name": "...",
      "source": "xml_extractor" | "omniparser"
    }
    ```
  - 执行/校验优先使用 bounds（像素），保留 bbox 作为兼容别名；视觉侧无 resource_id/text 时保持为空，不造假。
  - 在 device_inspector.get_current_screen_info(include_elements=True) 阶段，确保 elements 同时含 bounds 与 bbox（像素一致），减少后续环节分歧。
- 待确认点：是否同意按“最小统一外观”推进？

C. 未来（已同意纳入迭代的方向，暂不立项实施）
C1) 增加 few-shot 示例集（好/坏例对照）
- 做法：从 sessions 中挑成功/失败样本，脱敏为示例片段，纳入 generate_cases 的 examples；重点展示 on_fail + validators 的正确写法。

C2) 执行轨迹/快照/命中统计 → 可查询案例库
- 做法：JSONL + 截图以目录规范落盘；构建轻量索引（SQLite/Parquet 皆可）。run_case 结束写入索引；SimilarTestCasePrompts 检索可参考这些案例。

C3) 工具默认重试/超时/降级（close_ads / detect_playing_state 等）
- 做法：为常用工具提供统一默认参数（max_duration/interval/consecutive_no_ad），失败写入原因码；允许 case 层覆盖。

---

