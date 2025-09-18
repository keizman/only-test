# Only-Test Prompts Overview and Management Guide

## Introduction

This document provides a comprehensive overview of prompt templates, their storage locations, usage phases, and management strategies within the Only-Test MCP+LLM workflow. The prompt system is designed to guide LLM interactions through various testing phases, from initial planning to final test case generation.

## Prompt Storage Locations

### 1. Core Prompt Template Files
Located in `only_test/templates/prompts/`:

- **`generate_cases.py`** - Main test case generation prompts
  - Primary generation prompt with MCP tool guidance
  - Step-by-step guidance prompts
  - Completion and integration prompts
  - Interactive generation prompts

- **`element_location.py`** - Element location strategy prompts
  - Location strategy selection
  - Location failure recovery
  - Cross-device adaptation
  - Fallback strategy generation

- **`similar_cases.py`** - Similar test case retrieval prompts
  - Similar case matching and scoring
  - Test case adaptation guidance
  - Template recommendations
  - Quality assessment prompts

- **`conditional_logic.py`** - Conditional logic generation prompts
  - Smart condition judgment logic
  - Multi-branch decision trees
  - State machine logic
  - Exception handling patterns

- **`code_optimization.py`** - Code optimization prompts
  - Code refactoring suggestions
  - Performance optimization
  - Maintainability improvements
  - Best practices application

### 2. Prompt Engineering and Orchestration
- **`phone_mcp/tools/prompt_engineering.py`** - Orchestration and prompt engineering logic
  - Prompt template management
  - Dynamic prompt generation
  - Context injection mechanisms

### 3. Demo and Integration Files
- **`only_test/examples/mcp_llm_workflow_demo.py`** - Main demo file
  - Prompt integration points
  - Phase-specific prompt calls
  - Fallback prompt logic

### 4. Documentation Files
- **`all_prompt.md`** - Detailed prompt examples and usage
- **`phone-use/all_prompt.md`** - Additional prompt documentation
- **`getstart.md`**, **`AIRTEST_OVERVIEW_AND_PLAN.md`**, **`COMPREHENSIVE_DOCS.md`**, **`QA.md`** - Related documentation with prompt sections

## Phase-wise Prompt Roles and Characteristics

### Phase 1: Planning and Analysis
**Purpose**: Generate high-level test plans without specific selectors
**Key Files**: `generate_cases.py` (main generation prompt)
**Characteristics**:
- Requests structured JSON output only (仅输出严格JSON)
- No markdown formatting allowed
- Creates initial test objectives and flow
- Does not require screen element details

**Example Prompt Structure**:
```python
TestCaseGenerationPrompts.get_main_generation_prompt(
    description="user requirement",
    examples=[...],
    screen_elements="",
    app_package="com.example.app",
    device_type="mobile"
)
```

### Phase 2: Step Execution and Action Selection
**Purpose**: Guide specific UI actions based on current screen state
**Key Files**: 
- `generate_cases.py` (step guidance prompt)
- `element_location.py` (element selection strategies)

**Characteristics**:
- Enforces strict selector validation (resource_id, content_desc, text)
- Requires screen_analysis_result with elements whitelist
- Implements TOOL_REQUEST protocol for missing data
- Single-step handshake pattern (Plan → Execute → Verify → Append)

**Key Features**:
- Whitelist binding: selectors must come from current screen elements
- Bounds validation: pixel coordinates must match element bbox exactly
- Evidence tracking: screen_hash, source_element_uuid, element_snapshot

**Example Output Format**:
```json
{
  "tool_request": {
    "name": "analyze_current_screen",
    "params": {},
    "reason": "需要最新的真实屏幕元素"
  }
}
```
or
```json
{
  "next_action": {
    "action": "click",
    "target": {
      "priority_selectors": [
        {"resource_id": "..."},
        {"content_desc": "..."},
        {"text": "..."}
      ],
      "bounds_px": [left, top, right, bottom]
    }
  },
  "evidence": {
    "screen_hash": "...",
    "source_element_uuid": "...",
    "source_element_snapshot": {...}
  }
}
```

### Phase 3: Conditional Logic and Decision Making
**Purpose**: Handle complex flows and conditional branches
**Key Files**: `conditional_logic.py`
**Characteristics**:
- Multi-condition compound judgments
- Decision tree generation
- State machine logic
- Exception scenario handling

### Phase 4: Test Case Completion and Generation
**Purpose**: Integrate all steps into final test case JSON
**Key Files**: `generate_cases.py` (completion prompt)
**Characteristics**:
- Consolidates executed steps
- Generates complete Only-Test JSON format
- Includes execution paths and validation criteria
- Supports swipe actions with start_px/end_px

### Phase 5: Correction and Retry
**Purpose**: Handle failures and invalid actions
**Key Files**: 
- `element_location.py` (location fix prompt)
- `prompt_engineering.py` (retry logic)

**Characteristics**:
- Analyzes failure causes
- Provides alternative strategies
- Implements fallback mechanisms
- Maintains test flow continuity

## Prompt Management and Relationships

### Call Flow Hierarchy
```
1. Demo/Orchestrator (mcp_llm_workflow_demo.py)
   ├── Planning Phase
   │   └── generate_cases.get_main_generation_prompt()
   ├── Execution Phase (Loop)
   │   ├── generate_cases.get_mcp_step_guidance_prompt()
   │   ├── element_location.get_location_strategy_prompt()
   │   └── conditional_logic.get_conditional_logic_prompt()
   ├── Failure Recovery
   │   └── element_location.get_location_fix_prompt()
   └── Completion Phase
       └── generate_cases.get_mcp_completion_prompt()
```

### Common Conventions Across Prompts

1. **Response Format**:
   - Strict JSON output only
   - No markdown formatting in responses
   - Chinese instructions: "仅输出严格JSON"

2. **Selector Rules**:
   - Must use snake_case naming (resource_id, content_desc, text)
   - No camelCase or kebab-case variants
   - priority_selectors must be a list of single-key objects

3. **Coordinate Format**:
   - Integer pixel coordinates only [left, top, right, bottom]
   - No normalized 0-1 float coordinates
   - bounds_px must match element bbox exactly

4. **Action Constraints**:
   - Limited to atomic actions: click, input, wait_for_elements, wait, restart, launch, assert, swipe
   - No abstract action names (e.g., close_ads, search_program)

5. **Annotation Handling**:
   - Text within `(( ... ))` is treated as author notes
   - Must be ignored and not included in output

## Current Issues and Improvement Suggestions

### Identified Problems

1. **Fragmented Organization**:
   - Prompts distributed across many files without central index
   - No clear mapping between files and usage stages
   - Difficult onboarding for new team members

2. **Inconsistent Formatting**:
   - JSON embedded in Python strings with manual escaping
   - Prone to formatting errors
   - Mix of f-strings and .format() causing issues

3. **Lack of Documentation**:
   - No versioning or changelog for prompt changes
   - Insufficient clarity on phase differences
   - Missing best practices guide

4. **Error Handling Gaps**:
   - Inconsistent fallback logic
   - Key normalization issues (quoted keys, camelCase)
   - Silent failures in some scenarios

### Proposed Improvements

1. **Centralized Prompt Registry**:
   ```python
   class PromptRegistry:
       def __init__(self):
           self.prompts = {}
           self.load_all_prompts()
       
       def get_prompt(self, phase, type):
           return self.prompts.get(f"{phase}.{type}")
   ```

2. **Template Extraction**:
   - Move prompt strings to separate template files
   - Use Jinja2 or similar templating engine
   - Separate logic from content

3. **Version Control**:
   - Add prompt versioning system
   - Track changes and compatibility
   - Maintain changelog

4. **Validation Layer**:
   - Add prompt output validation
   - Enforce consistent formatting
   - Catch errors early

5. **Testing Framework**:
   ```python
   class PromptTester:
       def test_prompt_output(self, prompt, expected_format):
           # Validate JSON structure
           # Check required fields
           # Verify selector formats
   ```

## How to Edit and Test Prompts

### Safe Editing Guidelines

1. **Before Editing**:
   - Backup current prompt version
   - Document reason for change
   - Review dependent code

2. **During Editing**:
   - Maintain JSON structure integrity
   - Preserve existing field names
   - Test with escape character handling

3. **Testing Process**:
   ```bash
   # Run demo with specific prompt changes
   python only_test/examples/mcp_llm_workflow_demo.py \
       --test-scenario "your_scenario" \
       --max-rounds 3 \
       --enable-execution
   
   # Check logs for errors
   tail -f logs/mcp_demo_session_*.log
   
   # Verify output format
   cat sessions/latest/session_combined.jsonl
   ```

4. **Validation Checklist**:
   - [ ] JSON output is valid
   - [ ] Selectors match whitelist format
   - [ ] No markdown in output
   - [ ] Tool requests properly formatted
   - [ ] Evidence fields included

### Common Pitfalls to Avoid

1. **String Formatting**:
   ```python
   # BAD - causes KeyError with JSON
   prompt = f"Output: {json_template}"
   
   # GOOD - proper escaping
   prompt = "Output: {{json_template}}".format(json_template=json_template)
   ```

2. **Key Naming**:
   ```python
   # BAD - inconsistent naming
   {"resourceId": "...", "content-desc": "..."}
   
   # GOOD - consistent snake_case
   {"resource_id": "...", "content_desc": "..."}
   ```

3. **Selector Structure**:
   ```python
   # BAD - single object
   "priority_selectors": {"resource_id": "..."}
   
   # GOOD - list of objects
   "priority_selectors": [{"resource_id": "..."}]
   ```

## Best Practices

1. **Prompt Design**:
   - Be explicit about output format
   - Include examples for complex structures
   - Define clear constraints and rules
   - Handle edge cases explicitly

2. **Context Management**:
   - Pass minimal necessary context
   - Avoid redundant information
   - Maintain state consistency
   - Clear screen_hash tracking

3. **Error Prevention**:
   - Always include TOOL_REQUEST fallback
   - Validate against whitelist
   - Check bounds consistency
   - Handle missing elements gracefully

4. **Performance Optimization**:
   - Cache frequently used prompts
   - Minimize prompt length where possible
   - Batch similar operations
   - Reuse common prompt sections

## Appendix: Prompt Template Examples

### Minimal Tool Request Template
```json
{
  "tool_request": {
    "name": "analyze_current_screen",
    "params": {},
    "reason": "Required for next action"
  }
}
```

### Standard Action Template
```json
{
  "next_action": {
    "action": "click",
    "target": {
      "priority_selectors": [
        {"resource_id": "com.example:id/button"}
      ],
      "bounds_px": [100, 200, 300, 250]
    },
    "data": null,
    "wait_after": 0.8
  },
  "evidence": {
    "screen_hash": "hash_value",
    "source_element_uuid": "uuid_value",
    "source_element_snapshot": {}
  }
}
```

### Complete Test Case Template
```json
{
  "testcase_id": "TC_app_20240101_120000",
  "name": "Test case name",
  "description": "Test objective",
  "target_app": "com.example.app",
  "device_info": {
    "type": "mobile",
    "detected_at": "2024-01-01T12:00:00",
    "screen_info": "1080x1920"
  },
  "execution_path": [
    {
      "step": 1,
      "page": "MainActivity",
      "action": "click",
      "description": "Click search button",
      "target": {
        "priority_selectors": [
          {"resource_id": "com.example:id/search"}
        ],
        "bounds_px": [900, 100, 1000, 200]
      },
      "timeout": 10,
      "success_criteria": "Search page opened"
    }
  ]
}
```

## Conclusion

The Only-Test prompt system is a complex but well-structured framework for guiding LLM-based test generation. While there are areas for improvement, particularly in organization and documentation, the system provides comprehensive coverage of testing scenarios with strict validation and fallback mechanisms. Following the guidelines in this document will help maintain and improve the prompt system effectively.

---

*Last Updated: 2024*
*Version: 1.0*
*Maintainers: Only-Test Development Team*
