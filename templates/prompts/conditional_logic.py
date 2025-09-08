#!/usr/bin/env python3
"""
Only-Test 条件逻辑判断 Prompt 模板

核心功能:
1. 智能条件判断逻辑生成
2. 多分支决策树生成  
3. 状态机逻辑生成
4. 异常条件处理生成
"""

from typing import Dict, List, Optional, Any, Union


class ConditionalLogicPrompts:
    """条件逻辑判断提示词模板类"""
    
    @staticmethod
    def get_conditional_logic_prompt(
        scenario_description: str,
        possible_conditions: List[Dict[str, Any]],
        screen_state: Dict[str, Any],
        expected_behavior: str,
        decision_context: Dict[str, Any] = None
    ) -> str:
        """
        获取智能条件判断逻辑 Prompt
        
        Args:
            scenario_description: 场景描述
            possible_conditions: 可能的条件列表
            screen_state: 当前屏幕状态
            expected_behavior: 期望行为
            decision_context: 决策上下文
        """
        
        conditions_text = ConditionalLogicPrompts._format_possible_conditions(possible_conditions)
        state_text = ConditionalLogicPrompts._format_screen_state(screen_state)
        context_text = ConditionalLogicPrompts._format_decision_context(decision_context or {})
        
        return f"""分析测试场景，生成智能条件判断逻辑，支持多种可能的操作路径。

## 场景描述
{scenario_description}

## 期望行为
{expected_behavior}

## 当前屏幕状态
{state_text}

## 可能的条件分支
{conditions_text}

{context_text}

## 条件判断类型说明

### 1. element_state - 元素状态判断
```python
if poco("element_id").exists():
    # 元素存在时的操作
    poco("action_button").click()
else:
    # 元素不存在时的操作
    poco("alternative_button").click()
```

### 2. text_content - 文本内容判断
```python
search_text = poco("search_box").get_text().strip()
if search_text:
    # 有内容时点击搜索
    poco("search_button").click()
else:
    # 无内容时点击取消
    poco("cancel_button").click()
```

### 3. visual_state - 视觉状态判断
```python
if is_element_visible("play_button"):
    # 播放按钮可见时
    click_play_button()
else:
    # 播放按钮不可见时，可能正在播放
    check_playing_state()
```

### 4. app_state - 应用状态判断
```python
if get_current_activity() == "MainActivity":
    # 在主页面时的操作
    navigate_to_search()
else:
    # 不在主页面时，先返回
    press_back_button()
```

### 5. multi_condition - 多条件复合判断
```python
if (poco("login_button").exists() and 
    not is_user_logged_in()):
    # 需要登录的情况
    perform_login()
elif poco("search_input").exists():
    # 已登录且在搜索页
    perform_search()
else:
    # 其他情况
    navigate_to_home()
```

## 智能判断原则

1. **优先级排序**: 按重要性排列判断条件
2. **互斥性检查**: 确保条件之间不会冲突
3. **完整性保证**: 覆盖所有可能的状态
4. **性能优化**: 优先检查快速条件
5. **错误处理**: 包含异常情况的处理

## 生成要求

请为给定场景生成智能条件判断逻辑，输出包含：

1. **条件分析**: 详细的条件分析
2. **判断逻辑**: 具体的代码实现
3. **分支处理**: 每个分支的处理逻辑
4. **异常处理**: 意外情况的处理
5. **优化建议**: 性能和维护优化建议

## 输出格式

```json
{{
  "condition_analysis": {{
    "primary_conditions": [
      {{
        "condition_type": "element_state|text_content|visual_state|app_state|multi_condition",
        "condition_description": "条件描述",
        "check_method": "检查方法",
        "probability": 0.8,
        "priority": 1
      }}
    ],
    "condition_relationships": "条件之间的关系分析",
    "decision_tree": "决策树结构"
  }},
  "generated_logic": {{
    "condition_type": "最佳条件类型",
    "check_element": "要检查的元素或状态",
    "check_condition": "具体的检查条件",
    "true_action": "条件为真时的动作",
    "false_action": "条件为假时的动作",
    "description": "条件判断说明"
  }},
  "code_implementation": {{
    "simple_version": "简化版代码",
    "complete_version": "完整版代码（包含异常处理）",
    "optimized_version": "优化版代码"
  }},
  "branch_analysis": [
    {{
      "branch_condition": "分支条件",
      "actions": ["动作1", "动作2"],
      "expected_result": "期望结果",
      "risk_level": "low|medium|high"
    }}
  ],
  "validation_strategy": {{
    "test_cases": ["测试用例1", "测试用例2"],
    "edge_cases": ["边界情况1", "边界情况2"],
    "error_scenarios": ["错误场景1", "错误场景2"]
  }}
}}
```

现在请开始分析并生成条件判断逻辑:"""
    
    @staticmethod
    def get_decision_tree_prompt(
        root_scenario: str,
        decision_points: List[Dict[str, Any]],
        possible_outcomes: List[str],
        constraints: Dict[str, Any] = None
    ) -> str:
        """
        获取多分支决策树生成 Prompt
        """
        
        points_text = ConditionalLogicPrompts._format_decision_points(decision_points)
        outcomes_text = ConditionalLogicPrompts._format_possible_outcomes(possible_outcomes)
        constraints_text = ConditionalLogicPrompts._format_constraints(constraints or {})
        
        return f"""为复杂的测试场景设计多分支决策树，支持复杂的条件判断和路径选择。

## 根场景
{root_scenario}

## 决策点
{points_text}

## 可能的结果
{outcomes_text}

{constraints_text}

## 决策树设计原则

### 1. 层次化结构
- 根节点：初始状态检查
- 中间节点：条件判断点
- 叶子节点：具体动作或结果

### 2. 最优路径优先
- 成功率最高的路径优先
- 执行时间最短的路径优先
- 维护成本最低的路径优先

### 3. 异常处理覆盖
- 每个节点都有异常出口
- 异常恢复路径设计
- 最大重试次数控制

### 4. 状态一致性
- 避免状态冲突
- 确保状态转换合理
- 维护状态历史

## 决策树模板

```
根场景检查
├── 条件A成立
│   ├── 子条件A1成立
│   │   ├── 动作序列1 → 结果1
│   │   └── 动作序列2 → 结果2
│   └── 子条件A1不成立
│       └── 异常处理A → 恢复路径
├── 条件A不成立
│   ├── 条件B检查
│   │   ├── 动作序列3 → 结果3
│   │   └── 动作序列4 → 结果4
│   └── 默认处理 → 兜底结果
└── 异常情况
    ├── 重试逻辑
    └── 失败处理
```

## 输出要求

请生成完整的决策树结构和代码实现：

```json
{{
  "decision_tree": {{
    "tree_structure": {{
      "root": {{
        "condition": "根条件",
        "children": [
          {{
            "condition": "子条件1",
            "action": "对应动作",
            "children": [],
            "probability": 0.7
          }}
        ]
      }}
    }},
    "complexity_metrics": {{
      "max_depth": 4,
      "total_nodes": 12,
      "decision_points": 5,
      "leaf_nodes": 7
    }}
  }},
  "code_implementation": {{
    "structured_version": "结构化代码实现",
    "functional_version": "函数式代码实现",
    "class_based_version": "类基础代码实现"
  }},
  "execution_paths": [
    {{
      "path_name": "主要路径",
      "conditions": ["条件1", "条件2"],
      "actions": ["动作1", "动作2"],
      "success_probability": 0.9,
      "execution_time": 15.5
    }}
  ],
  "optimization_opportunities": [
    "优化机会1",
    "优化机会2"
  ]
}}
```

现在请开始设计决策树:"""
    
    @staticmethod
    def get_state_machine_prompt(
        states: List[Dict[str, Any]],
        transitions: List[Dict[str, Any]],
        initial_state: str,
        final_states: List[str],
        context: Dict[str, Any] = None
    ) -> str:
        """
        获取状态机逻辑生成 Prompt
        """
        
        states_text = ConditionalLogicPrompts._format_states(states)
        transitions_text = ConditionalLogicPrompts._format_transitions(transitions)
        context_text = ConditionalLogicPrompts._format_decision_context(context or {})
        
        return f"""为复杂的测试流程设计状态机逻辑，确保状态转换的正确性和完整性。

## 状态定义
{states_text}

## 状态转换
{transitions_text}

## 初始状态
{initial_state}

## 最终状态
{', '.join(final_states)}

{context_text}

## 状态机设计原则

### 1. 状态完整性
- 覆盖所有可能的应用状态
- 每个状态都有明确的定义
- 状态之间无重叠和遗漏

### 2. 转换合理性  
- 转换条件清晰明确
- 转换动作正确可靠
- 异常转换处理完善

### 3. 循环检测
- 避免无限循环
- 检测死锁状态
- 设置超时机制

### 4. 状态持久化
- 状态信息保存
- 异常恢复支持
- 状态历史记录

## 状态机模板

```python
class TestStateMachine:
    def __init__(self):
        self.current_state = "{initial_state}"
        self.state_history = []
        self.transition_count = 0
        
    def transition_to(self, next_state, trigger_event=None):
        if self.is_valid_transition(self.current_state, next_state):
            self.state_history.append(self.current_state)
            self.current_state = next_state
            self.transition_count += 1
            self.on_state_changed(next_state, trigger_event)
        else:
            raise InvalidTransitionError(f"Cannot transition from {{self.current_state}} to {{next_state}}")
    
    def is_valid_transition(self, from_state, to_state):
        # 转换规则验证
        pass
        
    def on_state_changed(self, new_state, trigger_event):
        # 状态变化处理
        pass
```

## 输出要求

请生成完整的状态机设计和实现：

```json
{{
  "state_machine_design": {{
    "states": [
      {{
        "name": "状态名称",
        "description": "状态描述", 
        "entry_action": "进入状态时的动作",
        "exit_action": "离开状态时的动作",
        "internal_actions": ["内部动作1", "内部动作2"]
      }}
    ],
    "transitions": [
      {{
        "from_state": "源状态",
        "to_state": "目标状态",
        "trigger": "触发条件",
        "guard": "守卫条件",
        "action": "转换动作"
      }}
    ]
  }},
  "implementation": {{
    "state_machine_class": "状态机类代码",
    "state_definitions": "状态定义代码",
    "transition_logic": "转换逻辑代码",
    "event_handlers": "事件处理代码"
  }},
  "validation": {{
    "state_coverage": "状态覆盖度检查",
    "transition_matrix": "转换矩阵",
    "deadlock_analysis": "死锁分析",
    "reachability_analysis": "可达性分析"
  }},
  "integration_code": "集成到测试用例的代码"
}}
```

现在请开始设计状态机:"""
    
    @staticmethod
    def get_exception_handling_prompt(
        normal_flow: List[str],
        exception_scenarios: List[Dict[str, Any]],
        recovery_strategies: List[Dict[str, Any]],
        context: Dict[str, Any] = None
    ) -> str:
        """
        获取异常条件处理生成 Prompt
        """
        
        flow_text = ConditionalLogicPrompts._format_normal_flow(normal_flow)
        exceptions_text = ConditionalLogicPrompts._format_exception_scenarios(exception_scenarios)
        strategies_text = ConditionalLogicPrompts._format_recovery_strategies(recovery_strategies)
        context_text = ConditionalLogicPrompts._format_decision_context(context or {})
        
        return f"""为测试用例设计全面的异常处理逻辑，确保测试的健壮性和可靠性。

## 正常执行流程
{flow_text}

## 异常场景
{exceptions_text}

## 恢复策略
{strategies_text}

{context_text}

## 异常处理设计原则

### 1. 异常分类
- **系统异常**: 网络、设备、系统级错误
- **应用异常**: 应用崩溃、响应超时、界面异常
- **元素异常**: 元素未找到、状态异常、操作失败
- **逻辑异常**: 业务逻辑错误、数据异常、流程错误

### 2. 处理策略
- **立即重试**: 临时性错误，快速重试
- **延迟重试**: 需要等待的错误，延迟后重试
- **替代方案**: 使用备选路径或方法
- **优雅降级**: 降低期望，完成核心功能
- **快速失败**: 严重错误，立即终止

### 3. 恢复机制
- **状态恢复**: 恢复到已知的稳定状态
- **环境重置**: 重启应用或重置环境
- **数据清理**: 清理异常状态的数据
- **上下文重建**: 重新建立必要的上下文

### 4. 监控和报告
- **异常记录**: 详细记录异常信息
- **状态快照**: 保存异常时的状态
- **恢复日志**: 记录恢复过程
- **统计分析**: 异常模式分析

## 异常处理模板

```python
def execute_with_exception_handling(action_func, max_retries=3, recovery_strategies=None):
    for attempt in range(max_retries):
        try:
            return action_func()
        except ElementNotFoundException as e:
            # 元素未找到异常处理
            if attempt < max_retries - 1:
                handle_element_not_found(e, recovery_strategies)
            else:
                raise
        except NetworkException as e:
            # 网络异常处理
            if attempt < max_retries - 1:
                handle_network_error(e)
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise
        except Exception as e:
            # 通用异常处理
            handle_generic_exception(e)
            if attempt >= max_retries - 1:
                raise
```

## 输出要求

请生成完整的异常处理逻辑：

```json
{{
  "exception_analysis": {{
    "exception_categories": [
      {{
        "category": "异常类别",
        "scenarios": ["场景1", "场景2"],
        "frequency": "high|medium|low",
        "severity": "critical|high|medium|low",
        "impact": "影响描述"
      }}
    ],
    "risk_assessment": "风险评估",
    "priority_ranking": ["优先级排序"]
  }},
  "handling_strategies": [
    {{
      "exception_type": "异常类型",
      "detection_method": "检测方法",
      "handling_approach": "处理方法",
      "recovery_actions": ["恢复动作1", "恢复动作2"],
      "fallback_options": ["备选方案1", "备选方案2"],
      "code_implementation": "代码实现"
    }}
  ],
  "comprehensive_code": "完整的异常处理代码",
  "monitoring_integration": {{
    "logging_strategy": "日志策略",
    "metrics_collection": "指标收集",
    "alerting_rules": "告警规则"
  }},
  "testing_recommendations": [
    "测试建议1",
    "测试建议2"
  ]
}}
```

现在请开始设计异常处理逻辑:"""
    
    # 辅助方法
    @staticmethod
    def _format_possible_conditions(conditions: List[Dict[str, Any]]) -> str:
        """格式化可能的条件"""
        if not conditions:
            return "无明确条件信息"
        
        formatted = []
        for i, condition in enumerate(conditions, 1):
            condition_text = f"""
{i}. **{condition.get('name', f'条件{i}')}**
   - 条件类型: {condition.get('type', 'unknown')}
   - 检查对象: {condition.get('target', 'N/A')}
   - 判断逻辑: {condition.get('logic', 'N/A')}
   - 可能结果: {', '.join(condition.get('possible_results', []))}
   - 触发概率: {condition.get('probability', 'unknown')}
"""
            formatted.append(condition_text)
        
        return '\n'.join(formatted)
    
    @staticmethod
    def _format_screen_state(state: Dict[str, Any]) -> str:
        """格式化屏幕状态"""
        return f"""
**当前页面**: {state.get('current_page', 'unknown')}
**应用状态**: {state.get('app_state', 'unknown')}
**可见元素**: {len(state.get('visible_elements', []))} 个
**可操作元素**: {len(state.get('interactive_elements', []))} 个
**特殊状态**: {', '.join(state.get('special_states', []))}
"""
    
    @staticmethod
    def _format_decision_context(context: Dict[str, Any]) -> str:
        """格式化决策上下文"""
        if not context:
            return ""
        
        context_info = []
        for key, value in context.items():
            context_info.append(f"**{key}**: {value}")
        
        return f"""
## 决策上下文
{chr(10).join(context_info)}
"""
    
    @staticmethod
    def _format_decision_points(points: List[Dict[str, Any]]) -> str:
        """格式化决策点"""
        formatted = []
        for i, point in enumerate(points, 1):
            point_text = f"""
{i}. **{point.get('name', f'决策点{i}')}**
   - 判断条件: {point.get('condition', 'N/A')}
   - 可能分支: {len(point.get('branches', []))} 个
   - 默认行为: {point.get('default_action', 'N/A')}
   - 重要程度: {point.get('importance', 'medium')}
"""
            formatted.append(point_text)
        
        return '\n'.join(formatted)
    
    @staticmethod
    def _format_possible_outcomes(outcomes: List[str]) -> str:
        """格式化可能的结果"""
        outcomes_text = '\n'.join([f"- {outcome}" for outcome in outcomes])
        return f"""
{outcomes_text}
"""
    
    @staticmethod
    def _format_constraints(constraints: Dict[str, Any]) -> str:
        """格式化约束条件"""
        if not constraints:
            return ""
        
        constraints_info = []
        for key, value in constraints.items():
            constraints_info.append(f"**{key}**: {value}")
        
        return f"""
## 约束条件
{chr(10).join(constraints_info)}
"""
    
    @staticmethod
    def _format_states(states: List[Dict[str, Any]]) -> str:
        """格式化状态列表"""
        formatted = []
        for state in states:
            state_text = f"""
- **{state.get('name')}**: {state.get('description', 'N/A')}
  - 进入条件: {state.get('entry_condition', 'N/A')}
  - 退出条件: {state.get('exit_condition', 'N/A')}
  - 持续时间: {state.get('duration', 'N/A')}
"""
            formatted.append(state_text)
        
        return '\n'.join(formatted)
    
    @staticmethod
    def _format_transitions(transitions: List[Dict[str, Any]]) -> str:
        """格式化状态转换"""
        formatted = []
        for transition in transitions:
            transition_text = f"""
- **{transition.get('from')} → {transition.get('to')}**
  - 触发条件: {transition.get('trigger', 'N/A')}
  - 转换动作: {transition.get('action', 'N/A')}
  - 守卫条件: {transition.get('guard', 'N/A')}
"""
            formatted.append(transition_text)
        
        return '\n'.join(formatted)
    
    @staticmethod
    def _format_normal_flow(flow: List[str]) -> str:
        """格式化正常流程"""
        flow_text = '\n'.join([f"{i}. {step}" for i, step in enumerate(flow, 1)])
        return f"""
{flow_text}
"""
    
    @staticmethod
    def _format_exception_scenarios(scenarios: List[Dict[str, Any]]) -> str:
        """格式化异常场景"""
        formatted = []
        for scenario in scenarios:
            scenario_text = f"""
- **{scenario.get('name')}**
  - 异常类型: {scenario.get('type', 'N/A')}
  - 触发条件: {scenario.get('trigger', 'N/A')}
  - 影响范围: {scenario.get('impact', 'N/A')}
  - 发生概率: {scenario.get('probability', 'N/A')}
"""
            formatted.append(scenario_text)
        
        return '\n'.join(formatted)
    
    @staticmethod
    def _format_recovery_strategies(strategies: List[Dict[str, Any]]) -> str:
        """格式化恢复策略"""
        formatted = []
        for strategy in strategies:
            strategy_text = f"""
- **{strategy.get('name')}**
  - 适用场景: {strategy.get('applicable_to', 'N/A')}
  - 恢复动作: {strategy.get('actions', 'N/A')}
  - 成功率: {strategy.get('success_rate', 'N/A')}
  - 执行时间: {strategy.get('execution_time', 'N/A')}
"""
            formatted.append(strategy_text)
        
        return '\n'.join(formatted)