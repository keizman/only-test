#!/usr/bin/env python3
"""
Only-Test 相似测试用例检索 Prompt 模板

核心功能:
1. 相似用例检索和匹配
2. 用例适配和改进建议
3. 模板库管理和推荐
4. 用例质量评估和优化
"""

from typing import Dict, List, Optional, Any, Tuple
import re
from datetime import datetime


class SimilarTestCasePrompts:
    """相似测试用例检索提示词模板类"""
    
    @staticmethod
    def get_similar_testcase_prompt(
        user_requirement: str,
        testcase_library: List[Dict[str, Any]],
        similarity_threshold: float = 0.6,
        max_results: int = 5,
        context: Dict[str, Any] = None
    ) -> str:
        """
        获取相似测试用例检索 Prompt
        
        Args:
            user_requirement: 用户需求描述
            testcase_library: 测试用例库
            similarity_threshold: 相似度阈值
            max_results: 最大返回结果数
            context: 上下文信息
        """
        
        library_text = SimilarTestCasePrompts._format_testcase_library(testcase_library)
        context_text = SimilarTestCasePrompts._format_context(context or {})
        
        return f"""根据用户需求，从现有测试用例库中检索最相关的示例用例，为生成新用例提供参考。

## 用户需求
{user_requirement}

## 现有测试用例库
{library_text}

{context_text}

## 相似度评估标准

### 1. 功能相似度 (权重: 40%)
- **核心功能匹配**: 搜索、播放、登录等主要功能
- **业务逻辑相似**: 操作流程和业务规则
- **目标一致性**: 测试目标和验证点

评估方法:
```python
functional_similarity = (
    core_function_match * 0.5 +
    business_logic_match * 0.3 + 
    target_consistency * 0.2
)
```

### 2. 页面路径相似度 (权重: 25%)
- **路径长度对比**: 操作步骤数量对比
- **页面序列匹配**: 页面跳转序列相似性
- **关键节点覆盖**: 重要页面节点匹配

评估方法:
```python
path_similarity = (
    path_length_similarity * 0.3 +
    sequence_match_ratio * 0.4 +
    key_nodes_coverage * 0.3
)
```

### 3. 操作类型相似度 (权重: 20%)
- **动作类型匹配**: click, input, swipe等操作类型
- **交互模式相似**: 用户交互方式和模式
- **元素定位策略**: 元素识别和定位方法

评估方法:
```python
operation_similarity = (
    action_type_match * 0.4 +
    interaction_pattern_match * 0.3 +
    locator_strategy_match * 0.3
)
```

### 4. 标签匹配度 (权重: 15%)
- **直接标签匹配**: 完全相同的标签
- **语义标签匹配**: 语义相近的标签
- **标签权重**: 不同标签的重要程度

评估方法:
```python
tag_similarity = (
    direct_tag_match * 0.6 +
    semantic_tag_match * 0.4
)
```

## 相似度计算公式

```python
overall_similarity = (
    functional_similarity * 0.40 +
    path_similarity * 0.25 +
    operation_similarity * 0.20 +
    tag_similarity * 0.15
)
```

## 检索和排序规则

### 1. 多维度评分
- 分别计算各维度相似度分数
- 加权合并得到总体相似度
- 按总体相似度排序

### 2. 阈值过滤
- 只返回相似度高于 {similarity_threshold} 的用例
- 最多返回 {max_results} 个结果
- 避免重复和冗余

### 3. 多样性保证
- 确保返回结果的多样性
- 覆盖不同的实现方案
- 平衡相似度和差异性

## 适配性分析

对于每个相似用例，分析其适配到新需求的可行性：

1. **直接复用**: 可以直接使用的部分
2. **简单修改**: 需要小幅修改的部分
3. **重构适配**: 需要重构的部分
4. **完全重写**: 无法复用的部分

## 输出要求

请从测试用例库中选择最相关的用例作为生成新用例的参考：

```json
{{
  "requirement_analysis": {{
    "key_functions": ["核心功能1", "核心功能2"],
    "expected_path": ["页面1", "页面2", "页面3"],
    "required_actions": ["动作1", "动作2"],
    "target_tags": ["标签1", "标签2"],
    "complexity_level": "low|medium|high"
  }},
  "selected_testcases": [
    {{
      "filename": "用例文件名",
      "similarity_score": 0.85,
      "similarity_breakdown": {{
        "functional": 0.9,
        "path": 0.8,
        "operation": 0.85,
        "tag": 0.9
      }},
      "matching_aspects": [
        {{
          "aspect": "功能匹配",
          "details": "搜索功能完全匹配",
          "confidence": 0.95
        }}
      ],
      "relevant_parts": {{
        "reusable_code": "可复用的代码片段",
        "adaptable_logic": "可适配的逻辑",
        "reference_patterns": "参考模式"
      }},
      "adaptation_analysis": {{
        "direct_reuse": ["直接复用部分1", "直接复用部分2"],
        "simple_modification": ["简单修改部分1", "简单修改部分2"], 
        "major_refactoring": ["重构部分1", "重构部分2"],
        "complete_rewrite": ["重写部分1", "重写部分2"]
      }},
      "adaptation_effort": "low|medium|high",
      "adaptation_notes": "适配说明和建议"
    }}
  ],
  "generation_strategy": {{
    "primary_reference": "主要参考用例",
    "supplementary_references": ["补充参考用例1", "补充参考用例2"],
    "novel_requirements": ["新需求1", "新需求2"],
    "implementation_approach": "基于相似用例的生成策略"
  }},
  "gap_analysis": {{
    "missing_features": ["缺失功能1", "缺失功能2"],
    "additional_requirements": ["额外需求1", "额外需求2"],
    "innovation_opportunities": ["创新点1", "创新点2"]
  }},
  "recommendation_summary": "基于相似度分析的推荐总结"
}}
```

现在请开始分析并提供相似用例推荐:"""
    
    @staticmethod
    def get_testcase_adaptation_prompt(
        source_testcase: Dict[str, Any],
        target_requirement: str,
        adaptation_constraints: Dict[str, Any] = None,
        quality_requirements: Dict[str, str] = None
    ) -> str:
        """
        获取测试用例适配建议 Prompt
        """
        
        source_text = SimilarTestCasePrompts._format_source_testcase(source_testcase)
        constraints_text = SimilarTestCasePrompts._format_adaptation_constraints(adaptation_constraints or {})
        quality_text = SimilarTestCasePrompts._format_quality_requirements(quality_requirements or {})
        
        return f"""基于选定的相似测试用例，提供详细的适配建议，生成符合新需求的测试用例。

## 源测试用例
{source_text}

## 目标需求
{target_requirement}

{constraints_text}

{quality_text}

## 适配分析维度

### 1. 结构适配
- **元数据适配**: 标签、路径、描述信息
- **步骤序列调整**: 增删改测试步骤
- **页面流程适配**: 页面跳转和导航调整

### 2. 元素适配
- **元素定位更新**: resource_id、文本、选择器
- **交互方式调整**: 不同的操作方法
- **设备特性适配**: 不同设备的交互差异

### 3. 逻辑适配
- **条件判断调整**: 修改或增加条件逻辑
- **分支处理更新**: 调整分支和异常处理
- **验证点调整**: 修改断言和验证逻辑

### 4. 数据适配
- **测试数据更新**: 输入数据和期望结果
- **环境配置调整**: 设备、网络、权限配置
- **依赖关系调整**: 前置条件和后置处理

## 适配策略模式

### 1. 保守适配 (Minimal Changes)
```python
# 最小改动原则
# 1. 保留主要结构和流程
# 2. 只修改必要的元素定位
# 3. 调整输入数据和验证点
# 4. 保持原有的异常处理逻辑
```

### 2. 增强适配 (Enhanced Version)
```python
# 功能增强适配
# 1. 基于原有流程增加新功能
# 2. 提升异常处理能力
# 3. 增加更多验证点
# 4. 优化性能和稳定性
```

### 3. 重构适配 (Refactored Version)
```python
# 重构优化适配
# 1. 重新设计测试流程
# 2. 使用更好的定位策略
# 3. 重构条件判断逻辑
# 4. 采用新的最佳实践
```

## 质量保证要求

1. **功能完整性**: 确保所有需求功能都被覆盖
2. **健壮性**: 增强异常处理和错误恢复
3. **可维护性**: 代码结构清晰，易于维护
4. **可扩展性**: 便于后续功能扩展
5. **性能优化**: 执行效率和资源使用优化

## 输出要求

请提供详细的适配方案和实现代码：

```json
{{
  "adaptation_analysis": {{
    "similarity_assessment": {{
      "structural_similarity": 0.85,
      "functional_similarity": 0.90,
      "complexity_comparison": "源用例复杂度 vs 目标需求复杂度"
    }},
    "change_impact": {{
      "low_impact_changes": ["低影响变更1", "低影响变更2"],
      "medium_impact_changes": ["中影响变更1", "中影响变更2"],
      "high_impact_changes": ["高影响变更1", "高影响变更2"]
    }},
    "adaptation_feasibility": "feasible|challenging|difficult"
  }},
  "detailed_adaptation_plan": {{
    "metadata_changes": {{
      "tags_update": "标签更新说明",
      "path_modification": "路径修改说明",
      "description_rewrite": "描述重写内容"
    }},
    "step_modifications": [
      {{
        "original_step": "原始步骤",
        "modified_step": "修改后步骤", 
        "change_type": "add|modify|remove|replace",
        "change_reason": "修改原因",
        "impact_level": "low|medium|high"
      }}
    ],
    "element_adaptations": [
      {{
        "original_locator": "原始定位器",
        "new_locator": "新定位器",
        "adaptation_method": "适配方法",
        "confidence": 0.9
      }}
    ],
    "logic_enhancements": [
      {{
        "enhancement_type": "condition|exception|validation",
        "description": "增强描述",
        "implementation": "实现代码"
      }}
    ]
  }},
  "generated_testcase": {{
    "complete_code": "完整的适配后测试用例代码",
    "key_improvements": ["关键改进1", "关键改进2"],
    "quality_metrics": {{
      "code_quality": "A|B|C",
      "maintainability": "high|medium|low",
      "robustness": "excellent|good|fair"
    }}
  }},
  "validation_plan": {{
    "test_scenarios": ["测试场景1", "测试场景2"],
    "edge_cases": ["边界情况1", "边界情况2"],
    "performance_benchmarks": ["性能基准1", "性能基准2"]
  }},
  "maintenance_guide": {{
    "common_issues": ["常见问题1", "常见问题2"],
    "troubleshooting": ["故障排除1", "故障排除2"],
    "update_guidelines": ["更新指南1", "更新指南2"]
  }}
}}
```

现在请开始分析并提供适配方案:"""
    
    @staticmethod
    def get_template_recommendation_prompt(
        requirement_category: str,
        specific_needs: List[str],
        complexity_level: str,
        template_library: List[Dict[str, Any]],
        customization_preferences: Dict[str, Any] = None
    ) -> str:
        """
        获取模板推荐 Prompt
        """
        
        needs_text = SimilarTestCasePrompts._format_specific_needs(specific_needs)
        templates_text = SimilarTestCasePrompts._format_template_library(template_library)
        prefs_text = SimilarTestCasePrompts._format_customization_preferences(customization_preferences or {})
        
        return f"""基于需求特征和复杂度，从模板库中推荐最适合的测试用例模板。

## 需求分类
{requirement_category}

## 具体需求
{needs_text}

## 复杂度等级
{complexity_level}

## 模板库
{templates_text}

{prefs_text}

## 模板匹配策略

### 1. 分类匹配
- **精确匹配**: 需求分类完全对应的模板
- **上级匹配**: 需求分类的父类模板
- **相关匹配**: 功能相关的其他分类模板

### 2. 复杂度匹配
- **同级匹配**: 复杂度完全相同的模板
- **降级匹配**: 复杂度略高，可简化使用
- **升级匹配**: 复杂度较低，需要增强

### 3. 特性匹配
- **核心特性**: 必须支持的核心功能
- **可选特性**: 如果支持会更好的功能
- **扩展特性**: 未来可能需要的功能

## 模板评估标准

### 1. 适配度评分 (0-1)
```python
adaptation_score = (
    category_match * 0.4 +
    complexity_match * 0.3 +
    feature_coverage * 0.2 +
    customization_ease * 0.1
)
```

### 2. 开发效率评分 (0-1)
```python
efficiency_score = (
    template_completeness * 0.4 +
    documentation_quality * 0.3 +
    example_richness * 0.2 +
    maintenance_ease * 0.1
)
```

### 3. 质量评分 (0-1)
```python
quality_score = (
    code_quality * 0.3 +
    robustness * 0.3 +
    best_practices * 0.2 +
    test_coverage * 0.2
)
```

## 推荐算法

### 1. 多维度评分
- 分别计算适配度、效率、质量评分
- 加权合并得到综合评分
- 按综合评分排序

### 2. 多样性保证
- 确保推荐结果的多样性
- 覆盖不同的实现方案
- 提供多种复杂度选择

### 3. 个性化调整
- 根据用户偏好调整权重
- 考虑历史使用记录
- 适应团队标准和规范

## 输出要求

请推荐最适合的模板并提供使用指导：

```json
{{
  "requirement_analysis": {{
    "category_classification": "需求分类结果",
    "complexity_assessment": "复杂度评估",
    "key_features": ["关键特性1", "关键特性2"],
    "constraint_analysis": ["约束1", "约束2"]
  }},
  "template_recommendations": [
    {{
      "template_name": "模板名称",
      "template_type": "模板类型",
      "match_score": {{
        "adaptation": 0.9,
        "efficiency": 0.85,
        "quality": 0.88,
        "overall": 0.87
      }},
      "pros": ["优点1", "优点2"],
      "cons": ["缺点1", "缺点2"],
      "best_for": ["最适合场景1", "最适合场景2"],
      "customization_required": {{
        "minimal": ["最小定制1", "最小定制2"],
        "moderate": ["中等定制1", "中等定制2"],
        "extensive": ["大量定制1", "大量定制2"]
      }},
      "usage_guide": {{
        "setup_steps": ["设置步骤1", "设置步骤2"],
        "configuration": "配置说明",
        "best_practices": ["最佳实践1", "最佳实践2"]
      }}
    }}
  ],
  "comparison_matrix": {{
    "templates": ["模板1", "模板2", "模板3"],
    "criteria": ["适配度", "效率", "质量", "学习曲线"],
    "scores": "评分矩阵"
  }},
  "implementation_roadmap": {{
    "quick_start": "快速开始方案",
    "progressive_enhancement": "渐进增强方案",
    "full_customization": "完全定制方案"
  }},
  "support_resources": {{
    "documentation_links": ["文档链接1", "文档链接2"],
    "example_projects": ["示例项目1", "示例项目2"],
    "community_resources": ["社区资源1", "社区资源2"]
  }}
}}
```

现在请开始分析并提供模板推荐:"""
    
    @staticmethod
    def get_quality_assessment_prompt(
        testcase_code: str,
        quality_criteria: Dict[str, Any],
        benchmark_cases: List[Dict[str, Any]] = None,
        improvement_focus: List[str] = None
    ) -> str:
        """
        获取用例质量评估 Prompt
        """
        
        criteria_text = SimilarTestCasePrompts._format_quality_criteria(quality_criteria)
        benchmark_text = SimilarTestCasePrompts._format_benchmark_cases(benchmark_cases or [])
        focus_text = SimilarTestCasePrompts._format_improvement_focus(improvement_focus or [])
        
        return f"""对测试用例进行全面的质量评估，识别问题并提供改进建议。

## 待评估测试用例
```python
{testcase_code}
```

## 质量评估标准
{criteria_text}

{benchmark_text}

{focus_text}

## 评估维度

### 1. 代码质量 (Code Quality)
- **可读性**: 代码结构清晰，命名规范，注释充分
- **可维护性**: 模块化设计，低耦合，易于修改
- **一致性**: 遵循编码规范，风格统一
- **简洁性**: 避免冗余代码，逻辑简洁明了

评估指标:
```python
code_quality_score = (
    readability * 0.3 +
    maintainability * 0.3 +
    consistency * 0.2 +
    conciseness * 0.2
)
```

### 2. 功能完整性 (Functional Completeness)
- **需求覆盖**: 所有功能需求都有对应的测试步骤
- **边界情况**: 覆盖边界值和异常情况
- **路径完整**: 测试路径完整，无遗漏
- **验证充分**: 关键步骤都有相应的验证

评估指标:
```python
completeness_score = (
    requirement_coverage * 0.4 +
    edge_case_coverage * 0.3 +
    path_completeness * 0.2 +
    validation_sufficiency * 0.1
)
```

### 3. 健壮性 (Robustness)
- **异常处理**: 完善的异常处理机制
- **错误恢复**: 有效的错误恢复策略
- **重试机制**: 合理的重试逻辑
- **容错能力**: 对环境变化的适应能力

评估指标:
```python
robustness_score = (
    exception_handling * 0.3 +
    error_recovery * 0.3 +
    retry_mechanism * 0.2 +
    fault_tolerance * 0.2
)
```

### 4. 执行效率 (Execution Efficiency)
- **执行时间**: 测试用例执行时间合理
- **资源使用**: CPU和内存使用效率
- **等待优化**: 等待时间设置合理
- **并发能力**: 支持并发执行

评估指标:
```python
efficiency_score = (
    execution_time * 0.4 +
    resource_usage * 0.3 +
    wait_optimization * 0.2 +
    concurrency_support * 0.1
)
```

### 5. 可扩展性 (Scalability)
- **参数化**: 支持参数化配置
- **数据驱动**: 支持数据驱动测试
- **模块复用**: 模块可以复用
- **平台适配**: 跨平台适配能力

评估指标:
```python
scalability_score = (
    parameterization * 0.3 +
    data_driven * 0.3 +
    module_reusability * 0.2 +
    platform_adaptability * 0.2
)
```

## 问题识别清单

### 1. 代码问题
- [ ] 硬编码值过多
- [ ] 缺少异常处理
- [ ] 等待时间不合理
- [ ] 命名不规范
- [ ] 注释不充分

### 2. 逻辑问题
- [ ] 条件判断不完整
- [ ] 分支覆盖不全
- [ ] 循环可能无限
- [ ] 资源未及时释放
- [ ] 状态管理混乱

### 3. 设计问题
- [ ] 过度耦合
- [ ] 职责不清
- [ ] 接口设计不合理
- [ ] 缺少抽象
- [ ] 违反设计原则

## 输出要求

请提供全面的质量评估报告和改进建议：

```json
{{
  "overall_assessment": {{
    "quality_grade": "A|B|C|D",
    "total_score": 0.85,
    "score_breakdown": {{
      "code_quality": 0.9,
      "completeness": 0.8,
      "robustness": 0.85,
      "efficiency": 0.88,
      "scalability": 0.82
    }},
    "assessment_summary": "整体评估总结"
  }},
  "detailed_analysis": {{
    "strengths": [
      {{
        "category": "优势类别",
        "description": "优势描述",
        "evidence": "支持证据",
        "impact": "影响程度"
      }}
    ],
    "weaknesses": [
      {{
        "category": "问题类别", 
        "severity": "high|medium|low",
        "description": "问题描述",
        "location": "代码位置",
        "impact": "影响分析"
      }}
    ],
    "improvement_opportunities": [
      {{
        "area": "改进领域",
        "priority": "high|medium|low",
        "effort": "改进工作量",
        "benefit": "改进收益",
        "suggestion": "具体建议"
      }}
    ]
  }},
  "improvement_plan": {{
    "immediate_fixes": [
      {{
        "issue": "问题描述",
        "solution": "解决方案", 
        "code_change": "代码修改",
        "estimated_effort": "预估工作量"
      }}
    ],
    "short_term_improvements": ["短期改进1", "短期改进2"],
    "long_term_enhancements": ["长期改进1", "长期改进2"]
  }},
  "improved_code": {{
    "refactored_version": "重构后的代码",
    "key_changes": ["关键变更1", "关键变更2"],
    "improvement_notes": "改进说明"
  }},
  "best_practices_recommendations": [
    "最佳实践建议1",
    "最佳实践建议2"
  ]
}}
```

现在请开始质量评估和改进建议:"""
    
    # 辅助方法
    @staticmethod
    def _format_testcase_library(library: List[Dict[str, Any]]) -> str:
        """格式化测试用例库"""
        if not library:
            return "测试用例库为空"
        
        formatted = []
        for i, testcase in enumerate(library, 1):
            case_info = f"""
{i}. **{testcase.get('name', f'TestCase_{i}')}**
   - 文件名: {testcase.get('filename', 'N/A')}
   - 标签: {', '.join(testcase.get('tags', []))}
   - 页面路径: {' -> '.join(testcase.get('path', []))}
   - 主要功能: {testcase.get('main_functions', ['未知'])}
   - 复杂度: {testcase.get('complexity', 'medium')}
   - 最后更新: {testcase.get('last_updated', '未知')}
   - 描述: {testcase.get('description', '无描述')[:200]}...
"""
            formatted.append(case_info)
        
        return '\n'.join(formatted)
    
    @staticmethod
    def _format_context(context: Dict[str, Any]) -> str:
        """格式化上下文信息"""
        if not context:
            return ""
        
        context_info = []
        for key, value in context.items():
            context_info.append(f"**{key}**: {value}")
        
        return f"""
## 上下文信息
{chr(10).join(context_info)}
"""
    
    @staticmethod
    def _format_source_testcase(testcase: Dict[str, Any]) -> str:
        """格式化源测试用例"""
        return f"""
**文件名**: {testcase.get('filename', 'N/A')}
**标签**: {', '.join(testcase.get('tags', []))}
**页面路径**: {' -> '.join(testcase.get('path', []))}
**复杂度**: {testcase.get('complexity', 'medium')}
**相似度评分**: {testcase.get('similarity_score', 'N/A')}

**代码片段**:
```python
{testcase.get('code_snippet', '无代码片段')[:1000]}...
```

**主要功能**: {', '.join(testcase.get('main_functions', []))}
**适配分析**: {testcase.get('adaptation_analysis', '未提供')}
"""
    
    @staticmethod
    def _format_adaptation_constraints(constraints: Dict[str, Any]) -> str:
        """格式化适配约束"""
        if not constraints:
            return ""
        
        constraints_info = []
        for key, value in constraints.items():
            constraints_info.append(f"**{key}**: {value}")
        
        return f"""
## 适配约束
{chr(10).join(constraints_info)}
"""
    
    @staticmethod
    def _format_quality_requirements(requirements: Dict[str, str]) -> str:
        """格式化质量要求"""
        if not requirements:
            return ""
        
        requirements_info = []
        for key, value in requirements.items():
            requirements_info.append(f"**{key}**: {value}")
        
        return f"""
## 质量要求
{chr(10).join(requirements_info)}
"""
    
    @staticmethod
    def _format_specific_needs(needs: List[str]) -> str:
        """格式化具体需求"""
        needs_text = '\n'.join([f"- {need}" for need in needs])
        return f"""
{needs_text}
"""
    
    @staticmethod
    def _format_template_library(templates: List[Dict[str, Any]]) -> str:
        """格式化模板库"""
        formatted = []
        for template in templates:
            template_info = f"""
- **{template.get('name')}**
  - 类型: {template.get('type', 'N/A')}
  - 复杂度: {template.get('complexity', 'N/A')}
  - 适用场景: {template.get('suitable_for', 'N/A')}
  - 特性: {', '.join(template.get('features', []))}
"""
            formatted.append(template_info)
        
        return '\n'.join(formatted)
    
    @staticmethod
    def _format_customization_preferences(prefs: Dict[str, Any]) -> str:
        """格式化定制偏好"""
        if not prefs:
            return ""
        
        prefs_info = []
        for key, value in prefs.items():
            prefs_info.append(f"**{key}**: {value}")
        
        return f"""
## 定制偏好
{chr(10).join(prefs_info)}
"""
    
    @staticmethod
    def _format_quality_criteria(criteria: Dict[str, Any]) -> str:
        """格式化质量标准"""
        criteria_info = []
        for key, value in criteria.items():
            criteria_info.append(f"**{key}**: {value}")
        
        return '\n'.join(criteria_info)
    
    @staticmethod
    def _format_benchmark_cases(cases: List[Dict[str, Any]]) -> str:
        """格式化基准测试用例"""
        if not cases:
            return ""
        
        benchmark_info = []
        for case in cases:
            case_info = f"- **{case.get('name')}**: {case.get('description', 'N/A')}"
            benchmark_info.append(case_info)
        
        return f"""
## 基准测试用例
{chr(10).join(benchmark_info)}
"""
    
    @staticmethod
    def _format_improvement_focus(focus: List[str]) -> str:
        """格式化改进重点"""
        if not focus:
            return ""
        
        focus_text = '\n'.join([f"- {item}" for item in focus])
        return f"""
## 改进重点
{focus_text}
"""