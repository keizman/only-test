# Only-Test 完整工作流程与 Prompt 设计

## 工作流程概览

```
用户描述 → LLM解析 → 屏幕元素提取 → 智能过滤 → 用例生成 → 代码生成 → 执行测试
```

## 1. 核心组件架构

### 1.1 已完成的组件

- ✅ **execute.py** - 主执行器，支持 `python execute.py -d mi9_pro_5g`
- ✅ **pure_uiautomator2_extractor.py** - 智能UI元素提取器
- ✅ **test_generator.py** - LLM驱动的测试用例生成器
- ✅ **element_filter.py** - 智能元素过滤器
- ✅ **json_to_python.py** - JSON元数据到Python代码生成器
- ✅ **example_airtest_record.py** - 示例测试用例（已添加页面注释）

### 1.2 工作流程图

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  用户自然语言   │───▶│   LLM 用例生成   │───▶│  智能元素提取   │
│     描述        │    │      器          │    │      器         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         │
┌─────────────────┐    ┌──────────────────┐            │
│   执行测试      │◀───│  Python代码生成   │◀───────────┼───┐
│     用例        │    │      器          │            │   │
└─────────────────┘    └──────────────────┘            │   │
                              ▲                         ▼   │
                              │                ┌─────────────────┐
                              │                │  智能元素过滤   │
                              └────────────────│      器         │
                                              └─────────────────┘
```

## 2. 详细工作流程

### 2.1 新用例生成流程

```bash
# 方式1: 通过 execute.py 生成并执行
python execute.py -d mi9_pro_5g --generate "搜索并播放周杰伦的歌"

# 方式2: 直接使用生成器
python airtest/lib/test_generator.py "登录后浏览视频内容"

# 方式3: 交互式生成（基于当前屏幕）
python airtest/lib/test_generator.py --interactive "点击当前屏幕上的搜索功能"
```

### 2.2 现有用例执行流程

```bash
# 执行默认用例
python execute.py -d mi9_pro_5g

# 执行指定用例
python execute.py -d mi9_pro_5g -t example_airtest_record

# 执行整个目录
python execute.py -d mi9_pro_5g -f airtest/testcases/python/
```

### 2.3 元素提取和过滤流程

```bash
# 提取当前屏幕元素
python airtest/lib/pure_uiautomator2_extractor.py

# 过滤元素数据
python airtest/lib/element_filter.py ui_elements.json -o filtered_elements.txt -s balanced

# 自定义过滤
python airtest/lib/element_filter.py ui_elements.json --keywords 搜索 播放 --package-filter com.mobile.app
```

## 3. 核心 Prompt 设计

### 3.1 用例生成主 Prompt

```python
TESTCASE_GENERATION_PROMPT = """你是Only-Test框架的测试用例生成专家。请根据用户描述生成高质量的自动化测试用例。

## 任务描述
用户需求: {description}

## Only-Test框架规范

### 1. 元数据格式
每个测试用例都必须包含以下元数据注释：
- `# [tag] 标签1, 标签2` - 用例分类标签 
- `# [path] 页面1 -> 页面2 -> 页面3` - 完整页面流转路径

### 2. 步骤注释格式
每个操作步骤都必须使用以下格式的注释：
`## [page] 页面名称, [action] 动作类型, [comment] 详细说明`

### 3. 页面类型规范
- app_initialization: 应用初始化
- app_startup: 应用启动  
- home: 首页
- search: 搜索页面
- search_result: 搜索结果页面
- vod: 点播内容页面
- vod_playing_detail: 点播详情页面
- vod_playing_full: 点播播放全屏
- playing: 播放页面
- live: 直播页面
- live_playing_full: 直播播放全屏
- login: 登录页面
- signup: 注册页面
- settings: 设置页面
- user_center: 用户中心

### 4. 动作类型规范
- launch: 启动应用
- restart: 重启应用
- click: 点击操作
- input: 文本输入
- swipe: 滑动操作
- wait: 等待操作
- assert: 断言验证

### 5. 智能条件判断
当存在多种可能的操作路径时，请在comment中描述判断逻辑，例如：
"根据搜索框内容状态智能选择点击搜索或取消搜索按钮"

## 现有测试用例示例
{examples}

## 当前屏幕元素信息 (如果可用)
{screen_elements}

## 生成要求

1. **严格遵循Only-Test元数据格式**
2. **生成完整可执行的Python代码**
3. **包含智能条件判断逻辑**
4. **使用合适的等待时间和异常处理**
5. **添加必要的断言验证**
6. **代码结构清晰，注释详细**

请生成一个完整的Python测试用例文件，包含：
1. 文件头部的测试描述和元数据
2. 导入必要的模块
3. 设备连接配置
4. 带详细注释的测试步骤
5. 必要的断言和验证

输出格式：
```python
# 生成的完整测试用例代码
```

现在请开始生成:"""
```

### 3.2 元素定位 Prompt

```python
ELEMENT_LOCATION_PROMPT = """基于当前屏幕的元素信息，为测试步骤确定最佳的元素定位策略。

## 当前屏幕元素
{filtered_elements}

## 测试步骤需求
操作: {action_type}
目标: {target_description}
页面: {current_page}

## 定位策略优先级
1. **resource_id** - 最稳定，跨版本兼容性好
2. **text** - 直观，适合有明确文本的元素
3. **visual** - 适合播放页面或复杂布局
4. **coordinate** - 最后选择，适合固定位置元素

## 选择标准
- 优先选择有明确resource_id的元素
- 文本应该准确且不易变化
- 视觉识别用于XML无法访问的场景
- 考虑元素的可见性和可点击性

请为这个操作选择最佳的定位策略，输出格式：
```json
{
  "strategy": "resource_id|text|visual|coordinate", 
  "target": "具体的定位目标",
  "uuid": "元素UUID（如果使用）",
  "confidence": 0.9,
  "fallback": ["备选策略1", "备选策略2"],
  "reason": "选择理由"
}
```"""
```

### 3.3 智能条件判断 Prompt

```python
CONDITIONAL_LOGIC_PROMPT = """分析测试场景，生成智能条件判断逻辑。

## 场景描述
{scenario_description}

## 可能的条件分支
{possible_conditions}

## 当前屏幕状态
{screen_state}

## 条件判断类型
1. **element_state** - 基于元素存在性判断
2. **text_content** - 基于文本内容判断  
3. **visual_state** - 基于视觉状态判断
4. **app_state** - 基于应用状态判断

## 生成条件逻辑
请为以下场景生成条件判断逻辑：

场景: {current_scenario}
期望行为: {expected_behavior}

输出JSON格式：
```json
{
  "condition_type": "element_state|text_content|visual_state|app_state",
  "check_element": "要检查的元素",
  "check_condition": "具体的检查条件", 
  "true_action": "条件为真时的动作",
  "false_action": "条件为假时的动作",
  "description": "条件判断说明",
  "code_snippet": "生成的代码片段"
}
```"""
```

### 3.4 相似用例检索 Prompt

```python
SIMILAR_TESTCASE_PROMPT = """根据用户需求，从现有测试用例库中检索最相关的示例用例。

## 用户需求
{user_requirement}

## 现有测试用例库
{testcase_library}

## 相似度评估标准
1. **功能相似度** - 测试的功能模块是否相似
2. **页面路径相似度** - 操作路径是否相近
3. **操作类型相似度** - 动作类型是否匹配
4. **标签匹配度** - 标签是否重叠

## 任务要求
从测试用例库中选择3个最相关的用例作为生成新用例的参考。

输出格式：
```json
{
  "selected_testcases": [
    {
      "filename": "用例文件名",
      "similarity_score": 0.85,
      "matching_aspects": ["功能", "页面路径", "操作类型"],
      "relevant_parts": "相关的代码片段或元数据",
      "adaptation_notes": "如何适配到新需求的建议"
    }
  ],
  "generation_strategy": "基于相似用例的生成策略",
  "key_differences": "新需求与现有用例的主要差异"
}
```"""
```

## 4. 配置文件模板

### 4.1 设备配置 (device_config.json)

```json
{
  "devices": {
    "mi9_pro_5g": {
      "adb_id": "192.168.100.112:5555",
      "name": "Mi 9 Pro 5G",
      "resolution": "1080x2340", 
      "android_version": "11",
      "app_package": "com.mobile.brasiltvmobile"
    },
    "tv_box": {
      "adb_id": "192.168.100.113:5555", 
      "name": "Android TV Box",
      "resolution": "1920x1080",
      "android_version": "9",
      "app_package": "com.tv.streamingapp"
    }
  },
  "llm_config": {
    "provider": "openai|ollama|claude",
    "model": "gpt-4|qwen2.5:32b|claude-3",
    "api_key": "your-api-key",
    "base_url": "http://localhost:11434"
  }
}
```

### 4.2 过滤配置 (filter_config.json)

```json
{
  "strategy": "balanced",
  "package_whitelist": ["com.mobile.brasiltvmobile", "com.tv.streamingapp"],
  "package_blacklist": ["com.google.android.gms", "com.android.systemui"],
  "text_keywords": ["搜索", "播放", "登录", "设置"],
  "max_elements": 50,
  "export_format": "detailed",
  "priority_elements": [
    {"resource_id": "*search*", "priority": "high"},
    {"resource_id": "*play*", "priority": "high"},
    {"text": "*登录*", "priority": "high"}
  ]
}
```

## 5. 使用示例

### 5.1 完整的用例生成和执行流程

```bash
# 1. 生成新测试用例
python execute.py -d mi9_pro_5g --generate "用户打开应用后搜索周杰伦的音乐并播放第一首歌"

# 2. 执行生成的用例  
python execute.py -d mi9_pro_5g -t generated_search_music_20241208_143022

# 3. 批量执行所有生成的用例
python execute.py -d mi9_pro_5g -f airtest/testcases/python/generated_*

# 4. 查看执行结果
ls results/
```

### 5.2 交互式用例生成流程

```bash
# 1. 连接设备并获取当前屏幕
python airtest/lib/pure_uiautomator2_extractor.py

# 2. 过滤屏幕元素
python airtest/lib/element_filter.py enhanced_ui_elements.json -o current_screen.txt

# 3. 基于当前屏幕生成用例
python airtest/lib/test_generator.py --interactive "点击当前屏幕的搜索功能并搜索内容"

# 4. 执行生成的用例
python execute.py -d mi9_pro_5g -t interactive_search_20241208_143022
```

### 5.3 调试和优化流程

```bash
# 1. 启用详细日志
export PYTHONPATH=/mnt/c/Download/git/uni
python execute.py -d mi9_pro_5g -t example_airtest_record --verbose

# 2. 生成优化的代码
python airtest/lib/json_to_python.py testcase_metadata.json --optimize --exception-handling

# 3. 分析执行结果
python -c "
import json
with open('results/latest/execution_result.json') as f:
    result = json.load(f)
    print(f'成功率: {result[\"success\"]}')
    print(f'执行时间: {result[\"execution_time\"]:.2f}s')
"
```

## 6. 扩展点

### 6.1 自定义 LLM 集成

```python
class CustomLLMClient(LLMClient):
    def __init__(self, api_endpoint: str):
        self.api_endpoint = api_endpoint
    
    async def generate_completion(self, prompt: str, temperature: float = 0.7) -> str:
        # 实现自定义 LLM 调用逻辑
        pass
```

### 6.2 自定义过滤规则

```python
# 在 element_filter.py 中添加自定义规则
def custom_filter_rule(element):
    # 自定义过滤逻辑
    return element.get('custom_property') == 'target_value'

filter_rules.append(FilterRule(
    "custom_rule",
    custom_filter_rule,
    ElementPriority.HIGH,
    "自定义过滤规则"
))
```

### 6.3 自定义断言

```python
# 在 json_to_python.py 中添加自定义断言模板
custom_assertions = {
    "check_media_playing": '''## [page] {page}, [action] assert, [comment] {comment}
# 检查媒体播放状态
import subprocess
audio_check = subprocess.run(['adb', 'shell', 'dumpsys', 'audio'], capture_output=True, text=True)
assert 'state: PLAYING' in audio_check.stdout, "音频未在播放"
''',
    
    "check_network_connected": '''## [page] {page}, [action] assert, [comment] {comment}
# 检查网络连接状态
network_check = subprocess.run(['adb', 'shell', 'ping', '-c', '1', '8.8.8.8'], capture_output=True)
assert network_check.returncode == 0, "网络连接异常"
'''
}
```

这个完整的工作流程文档提供了：

1. ✅ **清晰的组件架构**和工作流程图
2. ✅ **详细的使用命令**和参数说明  
3. ✅ **核心 Prompt 设计**，可直接用于 LLM 调用
4. ✅ **配置文件模板**，支持自定义配置
5. ✅ **完整的使用示例**，从生成到执行
6. ✅ **扩展机制**，支持自定义开发

现在你的 Only-Test 框架具备了完整的工作流程，可以支持 `python execute.py -d mi9_pro_5g` 这样的命令来执行测试用例了！