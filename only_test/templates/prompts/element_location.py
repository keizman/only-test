#!/usr/bin/env python3
"""
Only-Test 元素定位策略 Prompt 模板

核心功能:
1. 元素定位策略选择 Prompt
2. 定位失败修复 Prompt
3. 跨设备元素适配 Prompt
4. 智能后备策略 Prompt
"""

from typing import Dict, List, Optional, Any, Tuple


class ElementLocationPrompts:
    """元素定位策略提示词模板类"""
    
    @staticmethod
    def get_location_strategy_prompt(
        filtered_elements: List[Dict[str, Any]],
        action_type: str,
        target_description: str,
        current_page: str,
        device_type: str = "mobile"
    ) -> str:
        """
        获取元素定位策略选择 Prompt
        
        Args:
            filtered_elements: 过滤后的屏幕元素
            action_type: 动作类型 (click, input, swipe等)
            target_description: 目标描述
            current_page: 当前页面
            device_type: 设备类型
        """
        
        elements_text = ElementLocationPrompts._format_elements_for_selection(filtered_elements)
        strategy_notes = ElementLocationPrompts._get_strategy_notes(action_type, device_type)
        
        return f"""基于当前屏幕的元素信息，为测试步骤确定最佳的元素定位策略。

## 测试步骤需求
**操作类型**: {action_type}
**目标描述**: {target_description}
**当前页面**: {current_page}
**设备类型**: {device_type}

## 当前屏幕元素
{elements_text}

## 定位策略优先级和选择标准

### 1. Resource ID 定位 (推荐指数: ⭐⭐⭐⭐⭐)
- **优点**: 最稳定，跨版本兼容性好
- **适用场景**: 有明确resource_id的元素
- **选择条件**: resource_id不为空且语义清晰

### 2. Text 内容定位 (推荐指数: ⭐⭐⭐⭐)
- **优点**: 直观，用户友好
- **适用场景**: 有明确文本且文本相对稳定
- **注意事项**: 考虑多语言和文本变化

### 3. Class + 属性组合定位 (推荐指数: ⭐⭐⭐)
- **优点**: 较为稳定，适合特定元素类型
- **适用场景**: resource_id和text都不可用时
- **选择条件**: class_name清晰且有其他属性可辅助

### 4. Visual 视觉定位（已禁用）
- 项目已切换为 XML-only 模式，不再使用视觉识别/Omniparser
- 播放场景请使用“控制栏保活”后再进行 XML 定位

### 5. XPath 路径定位 (推荐指数: ⭐⭐)
- **优点**: 精确定位
- **适用场景**: 其他方式都不可用的情况
- **缺点**: 布局变化时容易失效

### 6. Coordinate 坐标定位 (推荐指数: ⭐)
- **优点**: 简单直接
- **适用场景**: 固定位置元素，最后选择
- **缺点**: 设备适配性差

{strategy_notes}

## 分析要求

请分析当前屏幕元素，为目标操作选择最佳的定位策略。考虑以下因素：

1. **稳定性**: 元素在不同版本间的稳定性
2. **唯一性**: 定位目标的唯一性和准确性
3. **可维护性**: 后续维护和调试的便利性
4. **跨设备兼容性**: 在不同设备上的兼容性
5. **执行效率**: 定位和执行的速度

## 输出格式

请输出JSON格式的定位策略建议：

```json
{{
  "primary_strategy": {{
    "type": "resource_id|text|visual|xpath|coordinate",
    "target": "具体的定位目标值",
    "uuid": "元素UUID（如果适用）",
    "confidence": 0.95,
    "code_snippet": "poco(\\\"target\\\").click()",
    "reason": "选择这个策略的详细理由"
  }},
  "fallback_strategies": [
    {{
      "type": "backup_strategy_type",
      "target": "备选定位目标",
      "confidence": 0.8,
      "code_snippet": "备选代码",
      "reason": "备选策略理由"
    }}
  ],
  "risk_assessment": {{
    "stability_score": 0.9,
    "maintenance_difficulty": "low|medium|high",
    "cross_device_compatibility": 0.85,
    "potential_issues": ["可能的问题1", "可能的问题2"]
  }},
  "optimization_suggestions": [
    "优化建议1",
    "优化建议2"
  ]
}}
```

现在请开始分析并提供定位策略建议:"""
    
    @staticmethod
    def get_location_fix_prompt(
        failed_step: Dict[str, Any],
        error_info: str,
        current_screen_elements: List[Dict[str, Any]],
        execution_context: Dict[str, Any]
    ) -> str:
        """
        获取定位失败修复 Prompt
        
        Args:
            failed_step: 失败的步骤信息
            error_info: 错误信息
            current_screen_elements: 当前屏幕元素
            execution_context: 执行上下文
        """
        
        step_info = ElementLocationPrompts._format_failed_step(failed_step)
        elements_info = ElementLocationPrompts._format_elements_for_selection(current_screen_elements)
        context_info = ElementLocationPrompts._format_execution_context(execution_context)
        
        return f"""元素定位失败，需要分析失败原因并提供修复方案。

## 失败的测试步骤
{step_info}

## 错误信息
```
{error_info}
```

## 当前屏幕实际元素
{elements_info}

## 执行上下文
{context_info}

## 失败原因分析

请分析可能的失败原因：

1. **元素不存在**
   - 页面未完全加载
   - 页面跳转失败
   - 元素被隐藏或移除

2. **定位策略失效**
   - Resource ID 改变
   - 文本内容变化
   - 布局结构调整

3. **时序问题**
   - 等待时间不足
   - 动画未完成
   - 网络加载延迟

4. **设备兼容问题**
   - 分辨率差异
   - 系统版本差异
   - 输入方式差异

5. **应用状态问题**
   - 弹窗遮挡
   - 权限请求
   - 网络错误

## 修复方案要求

请提供详细的修复方案，包括：

1. **问题诊断**: 分析具体的失败原因
2. **替代策略**: 提供新的元素定位方法
3. **代码修复**: 生成修复后的代码
4. **预防措施**: 避免类似问题的建议

## 输出格式

```json
{{
  "failure_analysis": {{
    "primary_cause": "主要失败原因",
    "contributing_factors": ["次要因素1", "次要因素2"],
    "confidence": 0.9
  }},
  "fix_solutions": [
    {{
      "solution_type": "replace_locator|add_wait|handle_popup|retry_logic",
      "description": "解决方案描述",
      "new_code": "修复后的代码",
      "success_probability": 0.85,
      "implementation_notes": "实施注意事项"
    }}
  ],
  "improved_step": {{
    "original_code": "原始代码",
    "improved_code": "改进后的代码",
    "changes_explanation": "改动说明"
  }},
  "prevention_measures": [
    "预防措施1",
    "预防措施2"
  ]
}}
```

现在请开始分析失败原因并提供修复方案:"""
    
    @staticmethod
    def get_cross_device_adaptation_prompt(
        source_elements: List[Dict[str, Any]],
        source_device: str,
        target_device: str,
        adaptation_rules: Dict[str, Any] = None
    ) -> str:
        """
        获取跨设备元素适配 Prompt
        """
        
        elements_info = ElementLocationPrompts._format_elements_for_adaptation(source_elements)
        device_diff = ElementLocationPrompts._get_device_differences(source_device, target_device)
        rules_info = ElementLocationPrompts._format_adaptation_rules(adaptation_rules or {})
        
        return f"""将元素定位策略从源设备适配到目标设备。

## 设备信息
**源设备**: {source_device}
**目标设备**: {target_device}

## 源设备元素信息
{elements_info}

## 设备差异分析
{device_diff}

{rules_info}

## 适配策略

### 1. 分辨率适配
- 坐标归一化处理
- 相对位置计算
- 缩放比例调整

### 2. 交互方式适配
- 触摸 → 遥控器导航
- 滑动 → 方向键移动
- 长按 → 菜单键

### 3. 布局适配
- 横屏 ↔ 竖屏切换
- 元素密度调整
- 导航方式变化

### 4. 功能适配
- 播放控制差异
- 菜单结构变化
- 系统集成差异

## 输出要求

请提供跨设备的元素定位适配方案：

```json
{{
  "adaptation_plan": {{
    "overall_strategy": "整体适配策略",
    "key_changes": ["主要变化点1", "主要变化点2"],
    "complexity_level": "low|medium|high"
  }},
  "element_mappings": [
    {{
      "source_locator": "源设备定位器",
      "target_locator": "目标设备定位器",
      "adaptation_type": "direct|coordinate_adjust|interaction_change|layout_change",
      "confidence": 0.9,
      "notes": "适配说明"
    }}
  ],
  "interaction_adaptations": [
    {{
      "source_action": "源设备动作",
      "target_action": "目标设备动作",
      "code_change": "代码变更",
      "reason": "适配原因"
    }}
  ],
  "validation_points": [
    "验证点1",
    "验证点2"
  ]
}}
```

现在请开始分析并提供跨设备适配方案:"""
    
    @staticmethod
    def get_fallback_strategy_prompt(
        primary_locator: Dict[str, Any],
        failure_scenarios: List[str],
        available_elements: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """
        获取智能后备策略 Prompt
        """
        
        locator_info = ElementLocationPrompts._format_primary_locator(primary_locator)
        scenarios_info = ElementLocationPrompts._format_failure_scenarios(failure_scenarios)
        elements_info = ElementLocationPrompts._format_elements_for_selection(available_elements)
        context_info = ElementLocationPrompts._format_execution_context(context)
        
        return f"""为主定位策略设计智能后备方案，提高测试用例的健壮性。

## 主定位策略
{locator_info}

## 可能的失败场景
{scenarios_info}

## 可选择的元素
{elements_info}

## 执行上下文
{context_info}

## 后备策略设计原则

### 1. 多层后备
- 第一后备：相似定位方式
- 第二后备：不同定位方式
- 第三后备：兜底策略

### 2. 智能判断
- 失败原因分析
- 动态策略选择
- 上下文感知

### 3. 渐进降级
- 精确度优先
- 稳定性保证
- 最后兜底

### 4. 性能考虑
- 快速失败检测
- 高效策略切换
- 合理重试次数

## 后备策略类型

1. **同类型后备**: 相同定位类型的不同目标
2. **跨类型后备**: 不同定位类型的相同目标
3. **语义后备**: 基于语义理解的替代方案
4. **视觉后备**: 基于视觉识别的兜底方案
5. **坐标后备**: 基于位置的最终方案

## 输出要求

请设计完整的后备策略方案：

```json
{{
  "fallback_chain": [
    {{
      "level": 1,
      "strategy_type": "similar_locator|different_type|semantic|visual|coordinate",
      "locator": "具体定位器",
      "trigger_condition": "触发条件",
      "timeout": 5.0,
      "retry_count": 2,
      "code_snippet": "代码片段",
      "success_probability": 0.8,
      "notes": "策略说明"
    }}
  ],
  "intelligent_switching": {{
    "condition_detection": "条件检测逻辑",
    "strategy_selection": "策略选择算法",
    "performance_optimization": "性能优化措施"
  }},
  "complete_code": "完整的带后备策略的代码",
  "testing_recommendations": [
    "测试建议1",
    "测试建议2"
  ]
}}
```

现在请开始设计智能后备策略:"""
    
    # 辅助方法
    @staticmethod
    def _format_elements_for_selection(elements: List[Dict[str, Any]]) -> str:
        """格式化元素信息用于选择"""
        if not elements:
            return "无可用元素信息"
        
        formatted = []
        for i, elem in enumerate(elements, 1):
            elem_info = f"""
{i}. **元素 {elem.get('uuid', f'elem_{i}')}**
   - Resource ID: `{elem.get('resource_id', 'N/A')}`
   - 文本内容: "{elem.get('text', '')}"
   - 元素类型: {elem.get('class_name', 'N/A')}
   - 可点击: {'✓' if elem.get('clickable') else '✗'}
   - 坐标: ({elem.get('center_x', 0):.3f}, {elem.get('center_y', 0):.3f})
   - 置信度: {elem.get('confidence', 1.0):.2f}
   - 数据源: {elem.get('source', 'unknown')}
"""
            formatted.append(elem_info)
        
        return '\n'.join(formatted)
    
    @staticmethod
    def _get_strategy_notes(action_type: str, device_type: str) -> str:
        """获取策略特定注意事项"""
        action_notes = {
            "click": """
## Click 操作特定注意事项
- 确保目标元素可点击 (clickable=true)
- 考虑元素可能被遮挡的情况
- 注意点击后的页面跳转或状态变化
- 对于小元素，考虑点击区域的准确性""",
            
            "input": """
## Input 操作特定注意事项
- 确保目标是输入类元素 (EditText等)
- 考虑软键盘弹出的影响
- 注意输入法状态和语言设置
- 考虑文本清空和焦点设置""",
            
            "swipe": """
## Swipe 操作特定注意事项
- 确定滑动的起点和终点
- 考虑滑动速度和距离
- 注意边界检测和循环滑动
- 考虑滑动后的惯性效果"""
        }
        
        device_notes = {
            "tv": """
## TV 设备特定注意事项
- 优先考虑焦点移动而非直接点击
- 注意遥控器按键映射
- 考虑播放状态下的特殊处理
- DRM 内容可能需要特殊方法""",
            
            "mobile": """
## 手机设备特定注意事项
- 考虑不同屏幕尺寸的适配
- 注意竖屏横屏切换
- 考虑边缘滑动手势
- 注意状态栏和导航栏影响""",
            
            "tablet": """
## 平板设备特定注意事项
- 考虑更大的屏幕空间
- 可能存在分屏模式
- 注意横屏优先的设计
- 考虑手势操作的丰富性"""
        }
        
        return action_notes.get(action_type, "") + device_notes.get(device_type, "")
    
    @staticmethod
    def _format_failed_step(step: Dict[str, Any]) -> str:
        """格式化失败步骤信息"""
        return f"""
**原始定位策略**: {step.get('strategy', 'unknown')}
**目标元素**: {step.get('target', 'N/A')}
**执行代码**: `{step.get('code', 'N/A')}`
**执行时间**: {step.get('timestamp', 'N/A')}
**重试次数**: {step.get('retry_count', 0)}
"""
    
    @staticmethod
    def _format_execution_context(context: Dict[str, Any]) -> str:
        """格式化执行上下文"""
        return f"""
**当前页面**: {context.get('current_page', 'unknown')}
**应用状态**: {context.get('app_state', 'unknown')}
**设备信息**: {context.get('device_info', 'N/A')}
**网络状态**: {context.get('network_status', 'unknown')}
**执行历史**: {', '.join(context.get('execution_history', []))}
"""
    
    @staticmethod
    def _format_elements_for_adaptation(elements: List[Dict[str, Any]]) -> str:
        """格式化元素信息用于适配"""
        return ElementLocationPrompts._format_elements_for_selection(elements)
    
    @staticmethod
    def _get_device_differences(source: str, target: str) -> str:
        """获取设备差异信息"""
        differences = {
            ("mobile", "tv"): """
**主要差异**:
- 交互方式: 触摸 → 遥控器
- 屏幕比例: 竖屏 → 横屏
- 分辨率: 1080x1920 → 1920x1080
- 导航方式: 滑动 → 焦点移动
- 播放场景: 小屏 → 全屏优先""",
            
            ("tv", "mobile"): """
**主要差异**:
- 交互方式: 遥控器 → 触摸
- 屏幕比例: 横屏 → 竖屏  
- 分辨率: 1920x1080 → 1080x1920
- 导航方式: 焦点移动 → 滑动
- 播放场景: 全屏优先 → 小屏适配""",
            
            ("mobile", "tablet"): """
**主要差异**:
- 屏幕尺寸: 较小 → 较大
- 布局密度: 紧凑 → 宽松
- 交互区域: 受限 → 宽广
- 多任务: 单任务 → 可能分屏"""
        }
        
        return differences.get((source, target), f"从 {source} 到 {target} 的设备差异分析")
    
    @staticmethod
    def _format_adaptation_rules(rules: Dict[str, Any]) -> str:
        """格式化适配规则"""
        if not rules:
            return ""
        
        rules_text = []
        for key, value in rules.items():
            rules_text.append(f"**{key}**: {value}")
        
        return f"""
## 自定义适配规则
{chr(10).join(rules_text)}
"""
    
    @staticmethod
    def _format_primary_locator(locator: Dict[str, Any]) -> str:
        """格式化主定位器信息"""
        return f"""
**定位类型**: {locator.get('type', 'unknown')}
**定位目标**: {locator.get('target', 'N/A')}
**置信度**: {locator.get('confidence', 'N/A')}
**代码**: `{locator.get('code', 'N/A')}`
**选择理由**: {locator.get('reason', 'N/A')}
"""
    
    @staticmethod
    def _format_failure_scenarios(scenarios: List[str]) -> str:
        """格式化失败场景"""
        if not scenarios:
            return "无特定失败场景"
        
        scenarios_text = '\n'.join([f"- {scenario}" for scenario in scenarios])
        return f"""
{scenarios_text}
"""