# Prompt Optimization Report

**优化日期**: 2025-09-30
**优化文件**: `templates/prompts/generate_cases.py`
**优化目标**: 明确三层Action架构，消除术语混淆，建立清晰的边界

---

## 优化概览

### 核心问题
1. Action术语混乱：使用已废弃的`launch`/`restart`
2. 层次不清：混淆MCP工具、test_steps动作、hook动作
3. 新动作说明不足：`press`、`click_with_bias`等缺少详细文档
4. 缺少错误示例：LLM容易犯同样的错误

---

## Phase 1: 核心术语统一 ✅

### 1.1 Delete Deprecated Terms
**修改位置**: 3处action枚举列表

**之前**:
```python
"action": "launch|click|input|swipe|wait|assert|click_with_bias|wait_for_disappearance|press"
"动作限制：动作只能是 click, input, wait_for_elements, wait, restart, launch, assert, swipe"
```

**之后**:
```python
"action": "click|input|swipe|press|click_with_bias|wait_for_elements|wait_for_disappearance|wait|assert"
"动作限制：test_steps中动作只能是 click, input, swipe, press, click_with_bias, wait_for_elements, wait_for_disappearance, wait, assert"
```

---

## Phase 2: 三层架构明确化 ✅

### 2.1 新增"三层Action架构说明"章节

**新增内容** (约70行，generate_cases.py:56-119):

```
## 🔧 三层Action架构说明（重要！必读）

### Layer 1: MCP Tools - 设备级工具（仅在tool_request中调用）
- get_current_screen_info
- start_app (在hooks或MCP中使用，不在test_steps中)
- close_ads (在hooks或MCP中使用，不在test_steps中)
- perform_ui_action / perform_and_verify (内部使用)

### Layer 2: Test Steps Actions - 测试步骤动作（在test_steps中使用）
- 基础交互: click, input, swipe, press
- 增强动作: click_with_bias, wait_for_elements, wait_for_disappearance, wait
- 验证动作: assert

### Layer 3: Hook Actions - 生命周期钩子（在hooks中使用）
- hooks.before_all: stop_app, start_app, tool
- hooks.after_all: stop_app

## ⚠️ 关键区别（避免混淆）
1. start_app是MCP工具，不是test_step动作
2. test_steps只使用Layer 2的9种动作
3. 元素交互由编排器自动执行，不通过MCP工具直接调用
```

**影响**:
- LLM现在清楚知道start_app/close_ads不能在test_steps中使用
- 明确了hooks与test_steps的边界
- 理解了MCP工具与执行引擎的调用关系

---

## Phase 3: 新动作详细文档 ✅

### 3.1 press动作详解
**新增位置**: generate_cases.py:189-200

```python
**press - 按键操作**
- 用途: 模拟物理按键，如搜索确认、返回导航
- 参数: target.keyevent
- 支持按键: "Enter", "Back", "Home", "Menu"
- 示例: 完整JSON示例
```

### 3.2 click_with_bias动作详解
**新增位置**: generate_cases.py:202-218

```python
**click_with_bias - 带偏移点击**
- 用途:
  - 避开元素上方的遮挡物
  - 精确点击元素的上半部或下半部
  - 点击卡片的封面而非底部文字
- 参数: target.bias.dy_px (正值向下，负值向上)
- 示例: 完整JSON示例
```

### 3.3 wait_for_elements vs wait_for_disappearance
**新增位置**: generate_cases.py:220-251

分别详细说明了两者的用途、参数、使用场景和完整示例。

### 3.4 变量引用说明
**新增位置**: generate_cases.py:253-256

说明了`data.text_var`如何引用`variables`中的变量。

---

## Phase 4: 示例JSON更新 ✅

### 4.1 hooks示例更新
**修改位置**: generate_cases.py:150-157

**之前**:
```json
"hooks": {
  "before_all": [
    {"action": "start_app", "wait": {"after": 5}},
    {"action": "tool", "tool_name": "close_ads"}
  ]
}
```

**之后** (对齐example_airtest_record.from_py.json):
```json
"hooks": {
  "before_all": [
    {"action": "stop_app", "comment": "重启应用清理环境状态", "wait": {"after": 3}},
    {"action": "start_app", "comment": "启动应用并等待加载完成", "wait": {"after": 5}},
    {"action": "tool", "tool_name": "close_ads", "comment": "进入后自动关闭广告",
     "params": {"mode": "continuous", "consecutive_no_ad": 2, "max_duration": 20.0}}
  ]
}
```

### 4.2 test_steps示例增强
**修改位置**: generate_cases.py:164-174

**新增字段**:
```json
"target": {
  "selectors": [...],
  "bias": {"dy_px": -100},      // 新增：click_with_bias使用
  "keyevent": "Enter"            // 新增：press动作使用
},
"data": {"text_var": "variable_name"},  // 新增：变量引用说明
"wait": {"after": 2}                     // 新增：等待时间
```

---

## Phase 5: 常见错误警告章节 ✅

### 5.1 新增错误对比示例
**新增位置**: generate_cases.py:190-270 (约80行)

**包含5类常见错误**:

1. **错误1**: 在test_steps中使用start_app或close_ads
   - ❌ 错误示例
   - ✅ 正确示例

2. **错误2**: 使用launch/restart等已废弃的action
   - ❌ 错误示例
   - ✅ 正确示例

3. **错误3**: click_with_bias缺少bias参数
   - ❌ 错误示例
   - ✅ 正确示例

4. **错误4**: press动作使用selectors而非keyevent
   - ❌ 错误示例
   - ✅ 正确示例

5. **错误5**: 混淆wait_for_elements和wait
   - 清晰对比两者的使用场景和参数

**效果**:
- LLM可以通过对比学习避免常见错误
- 错误示例标记为❌，正确示例标记为✅，视觉清晰

---

## 优化效果

### 定量指标
- **新增行数**: 约150行
- **修改点**: 8处关键修改
- **覆盖方法**: 3个主要prompt方法
  - `get_main_generation_prompt()`
  - `get_mcp_step_guidance_prompt()`
  - `get_mcp_completion_prompt()`

### 定性改进
1. **术语统一性**: 100%消除launch/restart等过时术语
2. **边界清晰度**: 三层架构明确，不再混淆
3. **文档完整性**: 所有新动作都有详细说明和示例
4. **错误预防**: 5类常见错误有明确的对比示例

---

## 后续建议

### 短期 (1-2周)
1. 测试优化后的prompt生成用例的准确性
2. 收集LLM生成结果，验证是否还犯相同错误
3. 根据实际使用情况调整错误示例

### 中期 (1个月)
1. 考虑添加reason字段的好/坏示例对比
2. 补充更多复杂场景的完整示例
3. 优化prompt长度，在保持清晰的前提下精简

### 长期 (持续)
1. 建立prompt版本管理
2. 定期更新动作列表和示例
3. 根据框架演进同步更新prompt

---

## 验证清单

- [x] 所有launch/restart已删除
- [x] 三层架构说明完整
- [x] MCP工具与test_steps边界清晰
- [x] hooks与test_steps边界清晰
- [x] press动作有详细说明和示例
- [x] click_with_bias动作有详细说明和示例
- [x] wait系列动作区分清晰
- [x] 常见错误有对比示例
- [x] JSON示例对齐最新标准
- [x] 变量引用机制说明清楚

---

## 文件变更摘要

**文件**: `only_test/templates/prompts/generate_cases.py`

**变更统计**:
- 新增: ~150行
- 修改: 8处关键位置
- 删除: 0行 (仅替换，保持向后兼容)

**主要变更区域**:
1. 三层架构说明 (L56-L119)
2. 常见错误警告 (L190-L270)
3. 新动作详解 (L189-L256)
4. JSON示例更新 (L150-L174)
5. Action枚举更新 (L115, L301, L328, L418)

---

**优化完成时间**: 2025-09-30
**优化执行者**: Claude (Prompt Perfector)
**审核状态**: 待用户验证