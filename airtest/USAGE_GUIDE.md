# 🎯 Only-Test Airtest 使用指南

欢迎使用 Only-Test 智能化 APK 自动化测试框架！本指南将帮助你快速上手并充分利用框架的智能化特性。

## 📋 目录

- [🚀 快速开始](#-快速开始)
- [🧠 智能元数据详解](#-智能元数据详解)
- [📝 测试用例生成](#-测试用例生成)
- [⚡ 执行测试用例](#-执行测试用例)
- [📊 查看测试报告](#-查看测试报告)
- [🔧 高级配置](#-高级配置)
- [❓ 常见问题](#-常见问题)
- [🎮 实践案例](#-实践案例)

---

## 🚀 快速开始

### 1. **环境准备**

```bash
# 确保你在 airtest 目录下
cd /path/to/uni/airtest

# 检查目录结构
ls -la
# 应该看到: lib/, testcases/, tools/, config/, reports/ 等目录
```

### 2. **第一次运行演示**

```bash
# 运行内置演示用例
python tools/test_runner.py --demo

# 查看生成的演示用例
cat testcases/generated/demo_smart_search.json
```

### 3. **生成你的第一个测试用例**

```bash
# 基于自然语言生成用例
python tools/case_generator.py \
  --description "在爱奇艺APP中搜索电影复仇者联盟，点击第一个结果播放" \
  --app "com.qiyi.video" \
  --device "android_phone"

# 查看生成的用例
ls testcases/generated/
```

### 4. **运行生成的测试用例**

```bash
# 运行单个测试用例
python tools/test_runner.py --file testcases/generated/tc_com_qiyi_video_*.json

# 查看HTML报告
open reports/test_report_*.html
```

---

## 🧠 智能元数据详解

### 🎯 **核心设计理念**

传统测试用例只描述"做什么"，Only-Test 的智能元数据描述"为什么这样做"和"如何智能判断"。

```yaml
传统方式:
  - 点击搜索按钮
  - 输入搜索词
  - 点击确认

Only-Test 方式:
  - 🧠 检查搜索框状态
  - 📋 如果有内容 → 先清空再输入
  - 📋 如果无内容 → 直接输入
  - ✅ 智能确认搜索执行
```

### 🔑 **关键元数据字段**

#### 1. **条件分支逻辑**
```json
{
  "action": "conditional_action",
  "condition": {
    "type": "element_content_check",
    "target": "search_input_box",
    "check": "has_text_content"
  },
  "conditional_paths": {
    "if_has_content": { "action": "click", "target": "clear_button" },
    "if_empty": { "action": "input", "data": "搜索词" }
  }
}
```

#### 2. **AI友好描述**
```json
{
  "description": "根据搜索框状态智能选择操作",
  "ai_hint": "寻找输入框右侧的清除按钮，通常是×符号",
  "business_logic": "确保搜索框处于正确状态",
  "reason": "搜索框已有内容，需要先清空"
}
```

#### 3. **上下文感知**
```json
{
  "context_awareness": {
    "current_app_state": "launched",
    "expected_page": "search_page",
    "user_session": "anonymous",
    "network_status": "connected"
  }
}
```

---

## 📝 测试用例生成

### 🤖 **方法一：LLM 辅助生成**

```bash
# 自然语言描述生成
python tools/case_generator.py \
  --description "在网易云音乐中搜索周杰伦的歌，如果搜索框有内容先清空" \
  --app "com.netease.cloudmusic" \
  --device "android_phone"

# 更复杂的描述
python tools/case_generator.py \
  --description "打开抖音，搜索'搞笑视频'，点击第一个视频播放，检查是否正常播放" \
  --app "com.ss.android.ugc.aweme" \
  --device "android_phone"
```

### 📄 **方法二：基于模板生成**

```bash
# 查看可用模板
python tools/case_generator.py --list

# 使用智能搜索模板
python tools/case_generator.py \
  --template "smart_search_template" \
  --app "com.example.app" \
  --keyword "测试内容"
```

### ✏️ **方法三：手动编写**

创建文件 `testcases/manual/my_custom_test.json`：

```json
{
  "testcase_id": "TC_CUSTOM_001",
  "name": "我的自定义测试",
  "execution_path": [
    {
      "step": 1,
      "action": "conditional_action",
      "condition": {
        "type": "element_content_check",
        "target": {"resource_id": "input_field"},
        "check": "has_text_content"
      },
      "conditional_paths": {
        "if_has_content": {
          "action": "click",
          "target": {"resource_id": "clear_btn"},
          "reason": "清空已有内容"
        },
        "if_empty": {
          "action": "input",
          "target": {"resource_id": "input_field"},
          "data": "新内容"
        }
      }
    }
  ]
}
```

---

## ⚡ 执行测试用例

### 🎯 **单个用例执行**

```bash
# 运行指定用例
python tools/test_runner.py --file testcases/generated/my_test.json

# 指定设备
python tools/test_runner.py --file testcases/generated/my_test.json --device "emulator-5554"

# 只生成JSON报告
python tools/test_runner.py --file testcases/generated/my_test.json --report json
```

### 📁 **批量执行**

```bash
# 运行目录中所有用例
python tools/test_runner.py --dir testcases/generated/

# 运行手动编写的用例
python tools/test_runner.py --dir testcases/manual/

# 生成HTML和JSON报告
python tools/test_runner.py --dir testcases/generated/ --report both
```

### 🔍 **执行过程监控**

执行时你会看到详细的智能决策过程：

```
📋 测试用例信息
============================================================
📝 名称: 智能搜索功能测试
🧠 智能条件步骤: 2个
   1. 根据搜索框状态智能选择操作
      └─ 条件: element_content_check - has_text_content
   2. 确保搜索词正确输入

🚀 开始执行测试用例: 智能搜索功能测试
▶️  Step 1: 点击首页搜索按钮
▶️  Step 2: 根据搜索框状态智能选择操作
🧠 执行条件分支逻辑
🎯 条件评估结果: True
📍 选择路径: click -> clear_button
💡 选择原因: 搜索框已有内容，需要先清空

✅ 测试用例执行完成: 智能搜索功能测试
📊 整体状态: success
⏱️  总耗时: 15.32 秒
🔄 恢复次数: 0
```

---

## 📊 查看测试报告

### 🌐 **HTML 报告**

HTML报告提供可视化的测试结果展示：

- **统计概览**：成功率、执行时间、用例数量
- **智能决策展示**：条件判断过程和选择路径
- **步骤详情**：每个步骤的执行状态和截图
- **异常恢复记录**：自动恢复的详细过程

```bash
# 在浏览器中打开报告
open reports/test_report_20241205_143022.html
```

### 📄 **JSON 报告**

JSON报告适合程序化处理和集成：

```json
{
  "report_metadata": {
    "framework": "Only-Test v1.0",
    "success_rate": "100.0%"
  },
  "test_results": [
    {
      "testcase_id": "TC_DEMO_SMART_SEARCH",
      "overall_status": "success",
      "steps": [
        {
          "step_number": 2,
          "action": "conditional_action",
          "conditional_info": {
            "condition_result": true,
            "selected_path": "click(clear_button)"
          }
        }
      ]
    }
  ]
}
```

---

## 🔧 高级配置

### ⚙️ **框架配置**

编辑 `config/framework_config.yaml`：

```yaml
# 执行引擎配置
execution:
  timeouts:
    default_step: 30
    element_wait: 10
  retry:
    max_retries: 3
    retry_delay: 2

# 元素识别配置
recognition:
  default_mode: "hybrid"  # xml, visual, hybrid
  visual_recognition:
    server_url: "http://your-omniparser-server:9333"
    confidence_threshold: 0.8
```

### 📱 **设备配置**

编辑 `config/device_config.yaml`：

```yaml
# 设备类型定义
device_types:
  android_phone:
    default_resolution: "1920x1080"
    interaction_delay: 0.5
  android_tv:
    default_resolution: "3840x2160"
    touch_type: "remote"
    interaction_delay: 1.0
```

### 🤖 **LLM 配置**

设置环境变量：

```bash
# OpenAI API Key
export OPENAI_API_KEY="your-api-key"

# 或使用 Claude
export CLAUDE_API_KEY="your-claude-key"
```

---

## ❓ 常见问题

### Q: 什么时候使用条件分支逻辑？

**A:** 当测试步骤需要根据界面状态动态选择操作时：

- 搜索框可能有历史内容需要清空
- 登录状态不确定需要判断
- 弹窗出现与否需要处理
- 不同设备的界面布局差异

### Q: 如何提高元素识别的准确性？

**A:** 使用多重选择器策略：

```json
{
  "target": {
    "priority_selectors": [
      {"resource_id": "precise_id"},           // 最准确
      {"content_desc": "描述文字"},            // 次选
      {"text": "显示文字"},                    // 备选
      {"xpath": "//xpath/expression"},        // 降级
      {"visual_hint": "视觉识别描述"}          // 兜底
    ]
  }
}
```

### Q: 执行失败时如何调试？

**A:** 检查以下几点：

1. **查看截图**：`reports/debug_step_*.png`
2. **检查日志**：执行时的详细日志输出
3. **验证选择器**：确认元素选择器是否正确
4. **测试条件逻辑**：检查条件判断是否符合预期

### Q: 如何集成到 CI/CD？

**A:** 创建自动化脚本：

```bash
#!/bin/bash
# run_tests.sh

# 生成测试用例
python tools/case_generator.py --dir testcases/templates/ --output testcases/generated/

# 执行所有用例
python tools/test_runner.py --dir testcases/generated/ --report json

# 检查结果
if [ $? -eq 0 ]; then
  echo "✅ All tests passed"
  exit 0
else
  echo "❌ Some tests failed"
  exit 1
fi
```

---

## 🎮 实践案例

### 🎵 **案例1：音乐APP智能搜索**

```bash
# 生成用例
python tools/case_generator.py \
  --description "在网易云音乐中搜索'告白气球'，如果搜索历史有内容先清空" \
  --app "com.netease.cloudmusic"

# 执行用例
python tools/test_runner.py --file testcases/generated/tc_com_netease_cloudmusic_*.json
```

**智能特性展示**：
- 自动检测搜索框状态
- 智能选择清空或直接输入
- 验证搜索结果相关性

### 📺 **案例2：视频APP条件导航**

```bash
# 生成复杂导航用例
python tools/case_generator.py \
  --description "打开爱奇艺，如果有登录弹窗就关闭，搜索'流浪地球'并播放第一个结果" \
  --app "com.qiyi.video"
```

**智能特性展示**：
- 弹窗检测和处理
- 多层条件判断
- 智能异常恢复

### 🛒 **案例3：电商APP购物流程**

创建 `testcases/manual/smart_shopping.json`：

```json
{
  "name": "智能购物流程测试",
  "execution_path": [
    {
      "step": 1,
      "action": "conditional_action",
      "condition": {
        "type": "element_exists",
        "target": {"text": "登录"}
      },
      "conditional_paths": {
        "if_true": {
          "action": "click",
          "target": {"text": "登录"},
          "reason": "用户未登录，需要先登录"
        },
        "if_false": {
          "action": "click", 
          "target": {"resource_id": "search_box"},
          "reason": "用户已登录，直接搜索商品"
        }
      }
    }
  ]
}
```

### 📱 **案例4：跨设备适配测试**

```bash
# 手机版本
python tools/case_generator.py \
  --template "smart_search_template" \
  --app "com.example.app" \
  --device "android_phone"

# TV版本  
python tools/case_generator.py \
  --template "smart_search_template" \
  --app "com.example.app.tv" \
  --device "android_tv"
```

---

## 🎯 总结

Only-Test 框架的核心价值：

1. **🧠 智能化**：真正理解UI状态，智能选择操作路径
2. **🔄 自适应**：自动适配不同应用和设备
3. **📋 标准化**：统一的元数据格式，便于维护
4. **🤖 AI驱动**：LLM辅助生成，提高开发效率
5. **🛡️ 可靠性**：多层异常恢复，确保执行稳定

通过智能元数据和条件分支逻辑，真正实现了"**Write Once, Test Everywhere**"的理念！

---

## 📞 技术支持

- **文档问题**：查看项目 README.md
- **配置问题**：参考 config/ 目录下的示例配置
- **案例参考**：查看 testcases/templates/ 目录
- **开发调试**：启用 debug 模式查看详细日志

🎉 **开始你的智能化测试之旅吧！**