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
        主测试用例生成 Prompt - 用于指导外部 LLM 使用 MCP 工具生成测试用例
        
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
        
        return f"""# Only-Test 框架专用：外部 LLM 用例生成指导

你是 Only-Test 框架的智能测试工程师。你的任务是：
1. **使用 MCP 工具**实时感知设备状态
2. **逐步生成测试用例**，每一步都基于真实的屏幕元素
3. **输出标准 JSON 格式**，供 Only-Test 框架转换为可执行的 Python 脚本

## 🔧 可用的 MCP 工具（必须按顺序使用）

### 1. analyze_current_screen - 分析当前屏幕
**用途**: 获取当前屏幕的所有UI元素和状态信息
**调用时机**: 每个测试步骤开始前
**返回**: 屏幕元素列表（包含 resource_id, text, bbox, interactivity 等）

### 2. interact_with_ui_element - 与元素交互  
**用途**: 点击、输入、滑动等操作
**参数**: 
- element_id: 从 analyze_current_screen 获得的元素ID
- action: "tap", "input", "swipe", "long_press"
**调用时机**: 需要执行操作时

### 3. generate_test_case_step - 生成测试步骤
**用途**: 基于屏幕分析结果生成单个测试步骤
**参数**:
- screen_data: 来自 analyze_current_screen 的结果
- test_objective: 当前步骤要达成的目标

## 📋 标准工作流程（外部 LLM 必须遵循）

```
第一步: 调用 analyze_current_screen 获取当前屏幕状态
第二步: 基于屏幕元素，确定下一个操作目标
第三步: 调用 interact_with_ui_element 执行操作
第四步: 再次调用 analyze_current_screen 验证操作结果
第五步: 调用 generate_test_case_step 记录这个步骤到JSON
第六步: 重复直到测试目标完成
```

## 🎯 当前测试任务
- **用户需求**: {description}
- **目标应用**: {app_package}
- **设备类型**: {device_type}

## 📐 JSON 输出格式（最终目标）

你需要逐步构建以下格式的 JSON：

```json
{{
  "testcase_id": "TC_{app_package.split('.')[-1]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
  "name": "简短的测试用例名称",
  "description": "{description}",
  "target_app": "{app_package}",
  "device_info": {{
    "type": "{device_type}",
    "detected_at": "自动填充",
    "screen_info": "自动填充"
  }},
  "execution_path": [
    {{
      "step": 1,
      "page": "从MCP工具识别的页面类型",
      "action": "launch|click|input|swipe|wait|assert",
      "description": "这一步要做什么（中文）",
      "target_element": {{
        "uuid": "从analyze_current_screen获得的真实uuid",
        "resource_id": "从屏幕分析获得的真实resource_id",
        "text": "元素的实际文本",
        "content_desc": "可访问性描述",
        "bbox": "元素边界框坐标",
        "fallback_coordinates": "如果resource_id为空时使用的坐标"
      }},
      "data": "输入的数据（如搜索词）",
      "timeout": 10,
      "success_criteria": "如何判断这步成功",
      "path": {{
        "mcp_tool_used": "使用了哪个MCP工具",
        "screen_hash": "屏幕状态的哈希值",
        "analysis_result": "分析结果摘要",
        "decision_reason": "为什么选择这个元素进行操作"
      }}
    }}
  ]
}}
```

## ⚠️ 重要约束

1. **必须使用真实元素**: 只能操作 analyze_current_screen 返回的实际元素
2. **不能虚构控件ID**: 如果 resource_id 为空，使用 bbox 计算坐标点击
3. **逐步验证**: 每个操作后都要重新分析屏幕状态
4. **记录追溯信息**: path 字段必须记录你使用的工具和决策过程
5. **播放状态适应**: 视频播放时只能使用视觉识别（omniparser），非播放时优先XML识别

## 🔄 双模式识别机制

Only-Test 会自动在两种模式间切换：
- **XML模式**: 快速、准确，但播放状态下不可用
- **视觉模式**: 基于AI识别，播放状态下可用，准确率90%

你无需关心模式切换，但要知道：
- 播放状态下可能只有 bbox 坐标，没有 resource_id
- 此时应该在JSON中设置 `"fallback_coordinates": [x, y]`

{screen_elements_text}

{device_specific_notes}

## 💡 开始指令

请按以下步骤开始：
1. 首先调用 `analyze_current_screen` 获取当前屏幕状态
2. 基于屏幕元素，制定测试计划
3. 逐步执行并记录每个步骤到JSON
4. 最终输出完整的测试用例JSON

现在开始第一步：请调用 analyze_current_screen 获取当前屏幕状态。"""

    @staticmethod
    def get_mcp_step_guidance_prompt(
        current_step: int,
        screen_analysis_result: Dict[str, Any],
        test_objective: str,
        previous_steps: List[Dict[str, Any]] = None,
        examples: List[Dict[str, Any]] = None
    ) -> str:
        """
        MCP 驱动的分步指导 Prompt - 指导外部 LLM 基于屏幕分析结果执行下一步
        
        Args:
            current_step: 当前步骤编号
            screen_analysis_result: 屏幕分析结果
            test_objective: 测试目标
            previous_steps: 之前执行的步骤
        """
        
        elements_info = TestCaseGenerationPrompts._format_mcp_elements(screen_analysis_result.get('elements', []))
        previous_steps_text = TestCaseGenerationPrompts._format_mcp_previous_steps(previous_steps or [])
        examples_text = TestCaseGenerationPrompts._format_examples(examples or [])
        
        return f"""# 步骤 {current_step}: MCP 驱动的测试步骤生成

## 📊 当前屏幕分析结果

**检测到的元素数量**: {screen_analysis_result.get('elements_found', 0)}
**可交互元素数量**: {screen_analysis_result.get('interactive_elements', 0)}
**应用状态**: {screen_analysis_result.get('app_state', 'unknown')}
**当前内容**: {screen_analysis_result.get('current_content', 'unknown')}

## 🎯 测试目标
{test_objective}

{previous_steps_text}

## 📱 可用的屏幕元素
{elements_info}

## 🧩 参考示例（Few-shot）
{examples_text}

## 🤖 下一步操作指导

基于上述屏幕分析结果，请选择合适的元素执行下一个操作：

1. **分析当前状态**: 确定当前页面类型和可能的操作
2. **选择目标元素**: 从上述元素列表中选择最合适的元素
3. **执行操作**: 使用 MCP 工具执行（perform_and_verify/perform_ui_action）
4. **生成步骤记录**: 记录动作前后的验证结果

## 📝 输出要求

请按以下格式输出你的决策（严格JSON）：

```json
{{
  "analysis": {{
    "current_page_type": "识别的页面类型",
    "available_actions": ["可能的操作列表"],
    "reason": "为什么选择该动作"
  }},
  "next_action": {{
    "action": "click|input|wait_for_elements|wait|restart|launch|assert",
    "target": {{
      "priority_selectors": [
        {{"resource_id": "..."}},
        {{"content_desc": "..."}},
        {{"text": "..."}}
      ],
      "bounds_px": [left, top, right, bottom]
    }},
    "data": "可选的输入数据",
    "wait_after": 0.8,
    "expected_result": "期望的操作结果"
  }}
}}
```

## 严格约束（必须遵守）
- 动作只能是: click, input, wait_for_elements, wait, restart, launch, assert, swipe
- 选择器必须包含: priority_selectors（优先 resource_id，其次 content_desc，再次 text）；若无法提供，必须给出 bounds_px（像素坐标）
- 禁止输出抽象动作名（如 close_ads、search_program），必须用上述原子动作表达
- 严禁返回非JSON或Markdown

## 广告处理提示
- 系统已在你查看屏幕时自动尝试关闭广告（最多3次），若返回数据包含 `ads_info.warnings`，说明可能仍有广告存在。
- 请优先使用以下策略手动关闭：
  - 选择器优先级：resource_id（含 `ivClose`/`mIvClose`/`close`）> content_desc（含“关闭/close/跳过”）> text
  - 视觉场景无法拿到id时可使用 bounds_px（点击中心点）
  - 关闭后必须重新分析屏幕，若元素签名变化不明显，则提示失败并调整策略（例如尝试其他 close 按钮或等待广告倒计时）

现在请基于屏幕分析结果，制定下一步操作计划。"""

    @staticmethod
    def get_mcp_completion_prompt(
        generated_steps: List[Dict[str, Any]],
        test_objective: str,
        final_state: Dict[str, Any],
        examples: List[Dict[str, Any]] = None
    ) -> str:
        """
        MCP 用例完成 Prompt - 指导外部 LLM 整合所有步骤生成最终JSON
        
        Args:
            generated_steps: 已生成的步骤列表
            test_objective: 测试目标
            final_state: 最终屏幕状态
        """
        
        steps_summary = TestCaseGenerationPrompts._format_steps_summary(generated_steps)
        examples_text = TestCaseGenerationPrompts._format_examples(examples or [])
        
        return f"""# 测试用例生成完成：整合所有步骤

## ✅ 测试目标
{test_objective}

## 📋 已执行的步骤
{steps_summary}

## 🎯 最终状态
**应用状态**: {final_state.get('app_state', 'unknown')}
**当前内容**: {final_state.get('current_content', 'unknown')}
**测试结果**: {"成功" if final_state.get('success', False) else "需要验证"}

## 📝 最终任务

## 🧩 参考示例（Few-shot）
{examples_text}

请将所有步骤整合成完整的 Only-Test JSON 测试用例（严格JSON，动作允许 swipe 并提供 target.swipe.start_px/end_px）：

```json
{{
  "testcase_id": "TC_brasiltvmobile_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
  "name": "基于测试目标的简短名称",
  "description": "{test_objective}",
  "target_app": "com.mobile.brasiltvmobile",
  "device_info": {{
    "type": "mobile",
    "detected_at": "{datetime.now().isoformat()}",
    "screen_info": "从最终状态获取"
  }},
  "execution_path": [
    // 仅使用 click/input/wait_for_elements/wait/restart/launch/assert 这些原子动作
  ]
}}
```

## ⚠️ 整合要求

1. **保持步骤顺序**: 按执行顺序排列所有步骤
2. **完整追溯信息**: 每步都要有完整的 path 字段
3. **真实元素信息**: 使用实际的 UUID 和元素属性
4. **执行时间记录**: 包含每步的执行时间和结果
5. **成功标准验证**: 确保每步都有明确的成功判断

请输出最终的完整 JSON 测试用例。"""

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

    @staticmethod
    def _format_mcp_elements(elements: List[Dict[str, Any]]) -> str:
        """格式化 MCP 屏幕元素信息"""
        if not elements:
            return "暂无可用元素信息。"
        
        formatted_elements = []
        for i, elem in enumerate(elements[:20], 1):  # 显示前20个元素
            elem_info = f"""
**元素 {i}**:
- UUID: `{elem.get('uuid', 'N/A')}`
- Resource ID: `{elem.get('resource_id', 'N/A')}`
- 文本内容: "{elem.get('content', elem.get('text', ''))}"
- 元素类型: {elem.get('type', elem.get('class_name', 'unknown'))}
- 可交互: {'✅' if elem.get('interactivity', elem.get('clickable', False)) else '❌'}
- 位置: {elem.get('bbox', [])}
- 中心坐标: ({elem.get('center_x', 0):.3f}, {elem.get('center_y', 0):.3f})
"""
            formatted_elements.append(elem_info)
        
        return '\n'.join(formatted_elements)

    @staticmethod
    def _format_mcp_previous_steps(previous_steps: List[Dict[str, Any]]) -> str:
        """格式化 MCP 之前执行的步骤"""
        if not previous_steps:
            return ""
        
        steps_text = []
        for i, step in enumerate(previous_steps, 1):
            step_info = f"""
**步骤 {i}**: {step.get('description', 'N/A')}
- 操作: {step.get('action', 'N/A')}
- 目标元素: {step.get('target_element', {}).get('uuid', 'N/A')}
- 执行结果: {step.get('result', 'N/A')}
"""
            steps_text.append(step_info)
        
        return f"""
## 📝 已执行的步骤
{''.join(steps_text)}
"""

    @staticmethod
    def _format_steps_summary(steps: List[Dict[str, Any]]) -> str:
        """格式化步骤摘要"""
        if not steps:
            return "暂无执行步骤。"
        
        summary_lines = []
        for i, step in enumerate(steps, 1):
            summary = f"""
**步骤 {i}**: {step.get('description', 'N/A')}
- 页面: {step.get('page', 'N/A')} 
- 操作: {step.get('action', 'N/A')}
- 目标: {step.get('target_element', {}).get('uuid', 'N/A')}
- 结果: {step.get('success', False) and '✅ 成功' or '❌ 失败'}
- 用时: {step.get('execution_time', 0):.2f}s
"""
            summary_lines.append(summary)
        
        return '\n'.join(summary_lines)


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
