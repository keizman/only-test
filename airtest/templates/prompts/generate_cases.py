#!/usr/bin/env python3
"""
Only-Test 测试用例生成 Prompt 模板

核心功能:
1. 主测试用例生成 Prompt
2. 交互式用例生成 Prompt  
3. 增强式用例生成 Prompt
4. 相似用例适配 Prompt
"""

from typing import Dict, List, Optional, Any
from datetime import datetime


class TestCaseGenerationPrompts:
    """测试用例生成提示词模板类"""
    
    @staticmethod
    def get_main_generation_prompt(
        description: str,
        examples: List[Dict[str, Any]] = None,
        screen_elements: str = "",
        app_package: str = "com.example.app",
        device_type: str = "mobile"
    ) -> str:
        """
        主测试用例生成 Prompt
        
        Args:
            description: 用户需求描述
            examples: 示例测试用例列表
            screen_elements: 当前屏幕元素信息
            app_package: 应用包名
            device_type: 设备类型 (mobile, tablet, tv)
        """
        
        examples_text = TestCaseGenerationPrompts._format_examples(examples or [])
        screen_elements_text = TestCaseGenerationPrompts._format_screen_elements(screen_elements)
        device_specific_notes = TestCaseGenerationPrompts._get_device_specific_notes(device_type)
        
        return f"""你是Only-Test框架的测试用例生成专家。请根据用户描述生成高质量的自动化测试用例。

## 任务描述
用户需求: {description}
目标应用: {app_package}
设备类型: {device_type}

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

### 6. 设备特定注意事项
{device_specific_notes}

## 现有测试用例示例
{examples_text}

{screen_elements_text}

## 生成要求

1. **严格遵循Only-Test元数据格式**
2. **生成完整可执行的Python代码**
3. **包含智能条件判断逻辑**
4. **使用合适的等待时间和异常处理**
5. **添加必要的断言验证**
6. **代码结构清晰，注释详细**
7. **考虑设备特定的交互方式**

## 代码结构要求

```python
# 测试描述和标签
# [tag] 相关标签
# [path] 页面流转路径

from airtest.core.api import *
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

connect_device("android://127.0.0.1:5037/device_id?touch_method=ADBTOUCH&")
poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)

## [page] 页面, [action] 动作, [comment] 说明
# 具体的操作代码

# ... 更多步骤

## [page] playing, [action] assert, [comment] 最终验证
# 断言代码
```

请生成一个完整的Python测试用例文件。输出格式：

```python
# 生成的完整测试用例代码
```

现在请开始生成:"""
    
    @staticmethod
    def get_interactive_generation_prompt(
        description: str,
        current_elements: List[Dict[str, Any]],
        screen_context: Dict[str, Any],
        previous_steps: List[str] = None
    ) -> str:
        """
        交互式测试用例生成 Prompt
        基于当前屏幕的实际元素信息生成用例
        """
        
        elements_text = TestCaseGenerationPrompts._format_interactive_elements(current_elements)
        context_text = TestCaseGenerationPrompts._format_screen_context(screen_context)
        previous_text = TestCaseGenerationPrompts._format_previous_steps(previous_steps or [])
        
        return f"""基于当前屏幕的真实元素信息，为用户需求生成精确的测试用例。

## 用户需求
{description}

## 当前屏幕信息
{context_text}

## 当前屏幕可操作元素
{elements_text}

{previous_text}

## 交互式生成要求

1. **使用真实存在的元素**
   - 优先使用有明确resource_id的元素
   - 确保点击的元素确实可点击
   - 文本匹配要准确

2. **基于实际屏幕状态**
   - 考虑当前页面的实际状态
   - 识别页面类型和可能的操作
   - 预测下一步可能的页面变化

3. **生成可执行代码**
   - 使用实际的resource_id和文本
   - 添加合适的等待时间
   - 包含必要的异常处理

4. **智能路径规划**
   - 从当前状态出发规划最短路径
   - 考虑可能的中间页面
   - 添加必要的返回和重试逻辑

请生成从当前屏幕状态开始的测试用例代码：

```python
# 交互式生成的测试用例代码
```"""
    
    @staticmethod
    def get_enhancement_prompt(
        base_testcase: str,
        enhancement_requirements: List[str],
        target_scenarios: List[str] = None
    ) -> str:
        """
        测试用例增强 Prompt
        对现有测试用例进行功能增强
        """
        
        requirements_text = '\n'.join([f"- {req}" for req in enhancement_requirements])
        scenarios_text = TestCaseGenerationPrompts._format_target_scenarios(target_scenarios or [])
        
        return f"""对现有测试用例进行功能增强，提高其健壮性和覆盖范围。

## 原始测试用例
```python
{base_testcase}
```

## 增强要求
{requirements_text}

{scenarios_text}

## 增强策略

1. **异常处理增强**
   - 添加网络异常处理
   - 添加元素未找到的重试逻辑
   - 添加应用崩溃恢复机制
   - 添加弹窗自动处理

2. **断言完善**
   - 添加中间状态验证
   - 添加性能相关断言
   - 添加内容正确性验证
   - 添加用户体验相关检查

3. **路径优化**
   - 添加多条执行路径
   - 添加快捷方式支持
   - 优化等待时间
   - 添加并发执行支持

4. **数据驱动**
   - 支持多组测试数据
   - 添加参数化支持
   - 支持环境变量配置
   - 添加测试数据清理

请生成增强后的测试用例代码：

```python
# 增强后的测试用例代码
```"""
    
    @staticmethod
    def get_adaptation_prompt(
        source_testcase: str,
        target_app_info: Dict[str, str],
        adaptation_mapping: Dict[str, str] = None
    ) -> str:
        """
        测试用例适配 Prompt
        将测试用例适配到新的应用或环境
        """
        
        app_info_text = TestCaseGenerationPrompts._format_app_info(target_app_info)
        mapping_text = TestCaseGenerationPrompts._format_adaptation_mapping(adaptation_mapping or {})
        
        return f"""将现有测试用例适配到新的应用环境。

## 源测试用例
```python
{source_testcase}
```

## 目标应用信息
{app_info_text}

{mapping_text}

## 适配要求

1. **包名和连接信息更新**
   - 更新应用包名
   - 更新设备连接信息
   - 更新启动参数

2. **元素定位适配**
   - 根据新应用更新resource_id
   - 适配文本内容（语言、措辞）
   - 调整坐标和布局相关信息

3. **页面流程适配**
   - 适配页面名称和层级
   - 调整页面跳转逻辑
   - 更新操作序列

4. **业务逻辑适配**
   - 适配特定功能模块
   - 更新测试数据
   - 调整验证逻辑

5. **设备特性适配**
   - 适配屏幕分辨率
   - 适配交互方式
   - 调整性能预期

请生成适配后的测试用例代码：

```python
# 适配后的测试用例代码
```"""
    
    @staticmethod
    def _format_examples(examples: List[Dict[str, Any]]) -> str:
        """格式化示例测试用例"""
        if not examples:
            return "暂无示例测试用例。"
        
        formatted_examples = []
        for i, example in enumerate(examples[:3], 1):  # 只显示前3个
            example_text = f"""
### 示例 {i}: {example.get('file', f'example_{i}')}
**标签**: {', '.join(example.get('metadata', {}).get('tags', []))}
**路径**: {' -> '.join(example.get('metadata', {}).get('path', []))}

**代码片段**:
```python
{example.get('content', '')[:800]}...
```
"""
            formatted_examples.append(example_text)
        
        return '\n'.join(formatted_examples)
    
    @staticmethod
    def _format_screen_elements(screen_elements: str) -> str:
        """格式化屏幕元素信息"""
        if not screen_elements:
            return ""
        
        return f"""
## 当前屏幕元素信息
{screen_elements}

请基于以上真实的屏幕元素信息生成测试用例，确保：
- 使用实际存在的resource_id
- 点击的元素确实可点击
- 文本匹配准确无误
"""
    
    @staticmethod
    def _get_device_specific_notes(device_type: str) -> str:
        """获取设备特定注意事项"""
        notes_map = {
            "mobile": """
**手机设备特定注意事项**:
- 屏幕尺寸较小，注意元素可见性
- 支持触摸手势和滑动操作
- 考虑竖屏和横屏切换
- 注意软键盘弹出对布局的影响""",
            
            "tablet": """
**平板设备特定注意事项**:
- 屏幕尺寸较大，布局可能不同
- 可能支持分屏操作
- 横屏模式较常用
- 元素间距和大小可能不同""",
            
            "tv": """
**TV设备特定注意事项**:
- 使用遥控器导航，主要是方向键和确认键
- 播放状态下可能无法获取XML信息，需要视觉识别
- DRM保护可能阻止截图，需要白盒测试
- 全屏播放是主要使用场景
- 焦点移动和高亮显示很重要"""
        }
        
        return notes_map.get(device_type, "通用设备注意事项")
    
    @staticmethod
    def _format_interactive_elements(elements: List[Dict[str, Any]]) -> str:
        """格式化交互式元素信息"""
        if not elements:
            return "未获取到当前屏幕元素信息。"
        
        formatted_elements = []
        for i, elem in enumerate(elements[:15], 1):  # 只显示前15个
            elem_info = f"""
{i}. **元素信息**:
   - UUID: {elem.get('uuid', 'N/A')}
   - Resource ID: {elem.get('resource_id', 'N/A')}
   - 文本: "{elem.get('text', '')}"
   - 类型: {elem.get('class_name', 'N/A')}
   - 可点击: {'是' if elem.get('clickable') else '否'}
   - 坐标: ({elem.get('center_x', 0):.3f}, {elem.get('center_y', 0):.3f})
"""
            formatted_elements.append(elem_info)
        
        return '\n'.join(formatted_elements)
    
    @staticmethod
    def _format_screen_context(context: Dict[str, Any]) -> str:
        """格式化屏幕上下文信息"""
        return f"""
**屏幕尺寸**: {context.get('screen_size', 'Unknown')}
**提取模式**: {context.get('extraction_mode', 'Unknown')}
**元素总数**: {context.get('total_count', 0)}
**播放状态**: {context.get('playback_state', 'Unknown')}
**时间戳**: {context.get('timestamp', 'Unknown')}
"""
    
    @staticmethod
    def _format_previous_steps(steps: List[str]) -> str:
        """格式化之前的执行步骤"""
        if not steps:
            return ""
        
        steps_text = '\n'.join([f"- {step}" for step in steps])
        return f"""
## 之前的执行步骤
{steps_text}

请基于这些已执行的步骤，生成后续的测试步骤。
"""
    
    @staticmethod
    def _format_target_scenarios(scenarios: List[str]) -> str:
        """格式化目标场景"""
        if not scenarios:
            return ""
        
        scenarios_text = '\n'.join([f"- {scenario}" for scenario in scenarios])
        return f"""
## 目标测试场景
{scenarios_text}
"""
    
    @staticmethod
    def _format_app_info(app_info: Dict[str, str]) -> str:
        """格式化应用信息"""
        info_lines = []
        for key, value in app_info.items():
            info_lines.append(f"**{key}**: {value}")
        
        return '\n'.join(info_lines)
    
    @staticmethod
    def _format_adaptation_mapping(mapping: Dict[str, str]) -> str:
        """格式化适配映射信息"""
        if not mapping:
            return ""
        
        mapping_lines = []
        for old_value, new_value in mapping.items():
            mapping_lines.append(f"- `{old_value}` → `{new_value}`")
        
        mapping_text = '\n'.join(mapping_lines)
        return f"""
## 元素映射关系
{mapping_text}
"""


# 预定义的常用Prompt模板
class PredefinedPrompts:
    """预定义的常用提示词模板"""
    
    # 常见测试场景的模板
    SEARCH_AND_PLAY_TEMPLATE = """
## 搜索播放类测试用例模板

用户需求: 在{app_name}中搜索"{search_keyword}"并播放第一个结果

标准流程:
1. 启动应用并处理初始弹窗
2. 进入搜索页面
3. 输入搜索关键词
4. 执行搜索操作
5. 选择搜索结果
6. 开始播放
7. 验证播放状态

请基于此模板生成具体的测试用例代码。
"""
    
    LOGIN_TEMPLATE = """
## 登录类测试用例模板

用户需求: 使用{login_method}登录{app_name}

标准流程:
1. 启动应用
2. 进入登录页面
3. 选择登录方式
4. 输入凭证信息
5. 执行登录操作
6. 验证登录成功
7. 检查用户状态

请基于此模板生成具体的测试用例代码。
"""
    
    NAVIGATION_TEMPLATE = """
## 导航浏览类测试用例模板

用户需求: 在{app_name}中浏览{content_type}内容

标准流程:
1. 启动应用
2. 导航到目标页面
3. 浏览内容列表
4. 进入详情页面
5. 执行相关操作
6. 验证结果
7. 返回或继续浏览

请基于此模板生成具体的测试用例代码。
"""