# Only-Test 快速开始指南

![Only-Test Logo](https://img.shields.io/badge/Only--Test-AI%20Powered%20Testing-blue) ![Version](https://img.shields.io/badge/Version-v1.0-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## 🎯 项目简介

**Only-Test** 是一个革命性的移动应用AI驱动自动化测试框架，让您通过自然语言描述就能生成专业级的测试用例！

### 核心特色
- 🧠 **AI智能生成**: 使用LLM自动分析需求并生成测试用例
- 👁️ **视觉识别**: 基于Omniparser的强大UI元素识别
- 🔧 **MCP集成**: 提供LLM与设备的实时交互能力
- 📱 **跨平台支持**: 支持Android设备的全面测试
- 🚀 **零代码生成**: 从自然语言需求到可执行测试用例

### 使用场景
- 移动应用功能测试自动化
- UI/UX测试验证
- 回归测试和性能测试
- 视频播放应用专项测试

---

## 🚀 快速安装

### 1. 环境要求

**系统要求：**
- Python 3.8+ 
- Android设备或模拟器
- ADB工具已安装并配置

**硬件要求：**
- 内存: 4GB+ RAM
- 存储: 2GB+ 可用空间
- 网络: 稳定的互联网连接

### 2. 克隆项目

```bash
git clone <your-repository-url>
cd uni
```

### 3. 安装依赖

```bash
# 安装Python依赖
pip install -r req.txt

# 如果需要完整YAML支持
pip install pyyaml>=6.0

# 安装airtest依赖
cd airtest
pip install -r requirements.txt
cd ..
```

### 4. 验证安装

```bash
# 验证MCP和LLM集成
python test_mcp_llm_integration.py

# 验证LLM驱动测试生成
python test_llm_driven_generation.py
```

如果看到 `🎉 所有测试通过！` 说明安装成功！

---

## 🎮 第一次使用

### 步骤1: 准备设备

**连接Android设备：**
```bash
# 确保ADB可用
adb devices

# 应该看到类似输出：
# emulator-5554   device
# 或
# YOUR_DEVICE_ID  device
```

**启动目标应用：**
```bash
# 启动BrasilTVMobile应用
adb shell am start -n com.mobile.brasiltvmobile/.MainActivity
```

### 步骤2: 配置Omniparser服务

**检查服务状态：**
```bash
curl http://100.122.57.128:9333/probe/
```

如果返回正常响应，说明Omniparser服务可用。

**测试视觉识别：**
```bash
# 使用测试图片验证
python misc/omniparser_tools.py \
  --input zdep_OmniParser-v2-finetune/imgs/yc_vod_playing_fullscreen.png \
  --server 100.122.57.128:9333 \
  -t file \
  -o test_output.json
```

### 步骤3: 生成你的第一个测试用例

**方式1: 使用AI智能生成** (推荐)

```bash
# 运行LLM驱动的测试生成
python test_llm_driven_generation.py
```

这会模拟完整的AI生成流程，生成智能测试用例到 `airtest/testcases/generated/` 目录。

**方式2: 使用现有模板**

```bash
# 运行预定义的播放功能测试
python airtest/testcases/python/brasiltvmobile_playback_test.py
```

---

## 🛠️ 详细使用流程

### 流程1: AI驱动测试生成 (核心功能)

#### 1.1 描述您的测试需求

在代码中或通过界面输入您的自然语言需求，例如：

```text
我需要对BrasilTVMobile应用的视频播放功能进行全面测试：
- 验证播放/暂停功能
- 测试快进快退控制
- 检查画质和字幕设置
- 验证全屏播放模式
```

#### 1.2 AI自动分析和生成

系统会自动：
1. **需求理解**: 分析测试意图和范围
2. **屏幕分析**: 使用Omniparser识别UI元素
3. **策略制定**: 确定测试优先级和方法
4. **用例生成**: 创建结构化的测试定义

#### 1.3 获得智能测试用例

生成的测试用例包含：
- 📋 完整的测试场景定义
- 🎯 基于真实UI元素的操作步骤
- 🧠 LLM推理和自适应逻辑
- ✅ 智能验证和异常处理

#### 1.4 执行测试

```bash
# 执行生成的测试用例
python airtest/testcases/python/[生成的测试文件].py

# 或指定特定场景
python airtest/testcases/python/[测试文件].py --scenario playback
```

### 流程2: 传统测试开发

#### 2.1 创建测试用例定义

```json
{
  "testcase_id": "TC_CUSTOM_TEST",
  "name": "自定义测试用例",
  "target_app": "com.mobile.brasiltvmobile",
  "test_scenarios": [
    {
      "scenario_id": "CUSTOM_SCENARIO",
      "name": "自定义测试场景",
      "steps": [
        {
          "step": 1,
          "action": "tap_element_by_uuid",
          "target_element": {
            "uuid": "your_element_uuid"
          }
        }
      ]
    }
  ]
}
```

#### 2.2 使用测试生成工具

```bash
# 从JSON生成Python执行脚本
python airtest/lib/code_generator/json_to_python.py \
  --input your_test.json \
  --output generated_test.py
```

#### 2.3 执行和调试

```bash
# 执行测试
python generated_test.py

# 查看详细日志
python generated_test.py --verbose

# 生成测试报告
python generated_test.py --report
```

---

## 📊 测试报告和结果

### 查看测试结果

**实时日志：**
```bash
# 测试执行过程中会显示：
2024-12-09 11:52:27 - INFO - ✅ LLM测试用例生成完成
2024-12-09 11:52:27 - INFO - 🎯 开始执行测试场景: 智能播放控制验证
2024-12-09 11:52:28 - INFO - ✅ 步骤1完成: LLM分析当前播放状态
```

**测试报告：**
- 📁 `airtest/reports/` - 测试报告目录
- 📊 HTML格式的详细测试报告
- 📸 失败步骤的自动截图
- 📈 执行时间和性能指标

**结果文件：**
- `tmp.json` - Omniparser分析结果
- `*.log` - 详细执行日志
- `screenshots/` - 测试过程截图

---

## 🔧 配置选项

### 设备配置

编辑 `airtest/config/device_config.yaml`：
```yaml
device:
  connect_method: "USB"
  device_id: "emulator-5554"
  wait_timeout: 30
  screenshot_quality: 80
```

### Omniparser配置

编辑 `airtest/config/framework_config.yaml`：
```yaml
omniparser:
  server_url: "http://100.122.57.128:9333"
  confidence_threshold: 0.8
  use_paddleocr: true
  cache_enabled: true
```

### LLM配置

```yaml
llm:
  model: "mock_llm"  # 或配置真实的LLM
  temperature: 0.7
  max_tokens: 2048
  timeout: 30
```

---

## 🎯 常见使用场景

### 场景1: 视频播放应用测试

```bash
# 1. 启动应用到播放界面
adb shell am start -n com.mobile.brasiltvmobile/.VideoPlayerActivity

# 2. 生成播放功能测试
python test_llm_driven_generation.py

# 3. 执行生成的测试
python airtest/testcases/python/llm_generated_test_*.py
```

### 场景2: UI界面功能验证

```bash
# 1. 获取当前界面元素
python airtest/lib/pure_uiautomator2_extractor.py

# 2. 基于元素生成测试用例
python airtest/tools/case_generator.py --ui-dump ui_dump.json

# 3. 执行测试
python generated_ui_test.py
```

### 场景3: 回归测试自动化

```bash
# 1. 批量运行所有测试用例
python airtest/tools/test_runner.py --suite all

# 2. 生成回归测试报告
python airtest/tools/test_runner.py --report regression
```

---

## 🚨 常见问题解决

### 问题1: Omniparser连接失败
```bash
# 症状: 
# ERROR: Omniparser 集成测试失败: Retry.__init__() got an unexpected keyword argument 'method_whitelist'

# 解决方案:
curl http://100.122.57.128:9333/probe/  # 检查服务状态
pip install requests urllib3 --upgrade   # 更新依赖
```

### 问题2: ADB设备无法连接
```bash
# 症状: adb devices 显示 unauthorized

# 解决方案:
adb kill-server
adb start-server
# 在设备上允许USB调试授权
```

### 问题3: 测试用例执行失败
```bash
# 症状: ElementNotFound 或元素定位失败

# 解决方案:
# 1. 重新获取UI dump
python airtest/lib/pure_uiautomator2_extractor.py

# 2. 更新元素UUID
# 编辑测试用例中的uuid值

# 3. 使用Omniparser重新分析
python misc/omniparser_tools.py --input current_screen.png
```

### 问题4: PyYAML警告
```bash
# 症状: ⚠️ 警告: PyYAML 未安装

# 解决方案:
pip install pyyaml>=6.0
```

---

## 📚 进阶使用

### 自定义LLM提供商

```python
# airtest/lib/llm_integration/custom_llm.py
class CustomLLMClient:
    def __init__(self, api_key, model_name):
        self.api_key = api_key
        self.model = model_name
    
    async def send_message(self, message, context=None):
        # 实现您的LLM调用逻辑
        pass
```

### 扩展MCP工具

```python
# 创建自定义MCP工具
from airtest.lib.mcp_interface.mcp_server import MCPTool

async def custom_device_action(**kwargs):
    # 实现自定义设备操作
    return MCPResponse(success=True, result="操作完成")

custom_tool = MCPTool(
    name="custom_action",
    description="自定义设备操作",
    parameters={"type": "object"},
    function=custom_device_action
)

mcp_server.register_tool(custom_tool)
```

### 批量测试执行

```bash
# 创建测试套件配置
# test_suite.yaml
test_suite:
  name: "完整功能测试"
  tests:
    - "playback_test.py"
    - "ui_test.py" 
    - "performance_test.py"
  
# 执行测试套件  
python airtest/tools/test_runner.py --suite test_suite.yaml
```

---

## 🔗 相关资源

### 文档链接
- 📖 [完整技术文档](COMPREHENSIVE_DOCS.md)
- 🔧 [开发者指南](Fordeveloper.md)
- 📊 [验证报告](FINAL_LLM_GENERATION_VERIFICATION_REPORT.md)
- 🛠️ [工作流程指南](airtest/WORKFLOW_GUIDE.md)

### 示例代码
- 📁 `airtest/examples/` - 完整示例代码
- 📁 `airtest/testcases/templates/` - 测试模板
- 📁 `airtest/testcases/generated/` - 生成的测试用例

### 社区支持
- 🐛 [问题报告](https://github.com/your-repo/issues)
- 💬 [讨论区](https://github.com/your-repo/discussions)
- 📧 技术支持: support@only-test.com

---

## 🎉 开始您的AI测试之旅！

现在您已经掌握了Only-Test的基本使用方法，可以开始体验AI驱动的自动化测试了！

**记住Only-Test的核心理念：**
> **"说出你的测试需求，剩下的交给AI！"** 

🚀 **立即开始：**
```bash
# 运行您的第一个AI生成测试
python test_llm_driven_generation.py
```

**期待看到：**
- 🤖 LLM智能理解您的需求
- 📊 自动生成专业级测试用例
- ⚡ 一键执行完整测试流程

**这就是测试自动化的未来！** ✨