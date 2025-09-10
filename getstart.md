# Only-Test 新手上手与工作流（中文）

![Only-Test Logo](https://img.shields.io/badge/Only--Test-AI%20Powered%20Testing-blue) ![Version](https://img.shields.io/badge/Version-v1.0-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

> 文档说明：本项目的 Markdown 文档以中文为主（含少量英文术语）。新同学可从本页开始，按“工作流”一步步完成环境准备、用例生成与执行。

## 一、项目简介（一分钟）

Only-Test 是一个“AI 驱动 + 确定性执行”的移动应用自动化测试框架：
- 人类只需用自然语言给出测试需求（Plan）。
- 外部 LLM 通过 MCP 工具链生成结构化 JSON 测试用例。
- 框架将 JSON 转为 Python（Airtest/Pytest），在真实设备上稳定执行并输出报告与工件。

典型能力：
- LLM 引导的用例生成与多轮优化
- UIAutomator2（XML）+ OmniParser（视觉）的双模识别与自动切换
- 统一用例资产与过程留痕（截图、识别结果、执行日志）

更多背景与设计，请阅读：`README.md`、`WORKFLOW_GUIDE.md`、`QA.md`（中文）。

## 二、安装与环境准备（10 分钟）

1) 基本依赖
- 系统：Windows/Linux/macOS，Python 3.8+
- 设备：Android 真机或模拟器，已安装 ADB

2) 获取代码并安装依赖
```bash
git clone <your-repository-url>
cd uni

# 安装项目根依赖
pip install -r req.txt

#（可选）安装 YAML 支持
pip install pyyaml>=6.0

# 安装 airtest 子模块依赖
cd airtest
pip install -r requirements.txt
cd ..
```

3) 验证基础环境
```bash
# 验证 MCP 与 LLM（使用 Mock，不依赖外网）
python -X utf8 test_mcp_llm_integration.py
```

若看到“测试通过/成功”即表示环境可运行示例工作流。

## 三、面向新同学的一条龙工作流（强烈推荐）

这条工作流演示“由人给 Plan，调用 MCP 工具（模拟外部 LLM）生成用例 → 转换为 Python → 后续可在设备上执行”。

1) 准备设备（可选，后续执行阶段需要）
```bash
adb devices  # 确认出现一台 device
```
可提前启动目标 App 以便后续执行：
```bash
adb shell am start -n com.mobile.brasiltvmobile/.MainActivity
```

2) 以自然语言给出测试 Plan（例如）
```text
验证播放页搜索与结果展示：
- 打开搜索
- 输入关键词 “Ironheart”
- 等待结果列表出现
- 断言结果列表非空
```

3) 调用 MCP 的“模拟 LLM”工具生成用例 JSON
```bash
python -X utf8 airtest/examples/mcp_llm_workflow_demo.py \
  --requirement "验证播放页的搜索与结果展示" \
  --target-app com.mobile.brasiltvmobile
```
输出：
- 生成的 JSON 用例路径（位于 `airtest/testcases/generated/llm_generated_*.json`）
- 自动转换后的 Python 测试文件路径

4)（可选）本地转为 Python（上一步已自动执行）
```bash
python airtest/lib/code_generator/json_to_python.py airtest/testcases/generated/xxx.json
```

5) 在设备上运行生成的 Python 用例（连接真机/模拟器）
```bash
# 示例：直接用 Python 运行生成的测试文件（需已连接 Android 设备）
python airtest/testcases/python/test_xxx.py

# 或者集成到 pytest + allure 流程
pytest airtest/testcases/python/test_xxx.py --alluredir=reports/allure-results -v
```

6) 查看工件与报告
- 截图/识别结果/执行日志：`airtest/assets/{app}_{device}/`
- allure 报告：`allure open reports/allure-report`

## 四、视觉识别与服务（可选）

若需体验视觉识别（OmniParser），请先确认服务器连通性：
```bash
curl http://<omniparser-server>:9333/probe/
```
然后可用示例图片做一次识别实验（本地脚本或 `test_airtest_omniparser.py`）。

注意：若未配置 OmniParser，框架仍可通过 XML（UIAutomator2）路径运行基本流程。
