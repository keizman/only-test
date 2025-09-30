# UnifiedLogger 使用说明

统一日志管理器，支持前后台双重输出和多种日志增强功能。

## 核心特性

### 1. 前后台双重输出
自动同时输出到控制台和文件，基于Python logging的多Handler机制。

```python
from only_test.lib.logging import get_logger

logger = get_logger(session_id="test", log_dir="logs")
logger.info("消息")  # 同时输出到控制台和文件
```

**原理**：
- `StreamHandler(stdout)` → 控制台（实时显示）
- `FileHandler(session_raw.log)` → 文件（持久化）
- 一次调用，两处输出

### 2. --verbose 参数支持

```bash
# 默认：控制台显示INFO及以上
python workflow.py --requirement "测试"

# verbose模式：控制台显示DEBUG及以上
python workflow.py --requirement "测试" --verbose
```

**FileHandler始终记录DEBUG及以上所有日志**（不受--verbose影响）

### 3. 阶段前缀

```python
logger.set_phase("plan")  # [PLAN]
logger.set_phase("execution", current_round=3, max_rounds=8)  # [ROUND 3/8]
logger.set_phase("completion")  # [COMPLETION]
```

### 4. 工具执行摘要
自动以树形结构显示工具结果：
```
[ROUND 2/8] Tool get_current_screen_info executed: SUCCESS (2.5s)
[ROUND 2/8] ├─ 元素总数: 45 (可点击: 12)
[ROUND 2/8] ├─ 当前页面: 首页
[ROUND 2/8] └─ 媒体播放: 是
```

### 5. 错误详情内联显示

```python
logger.log_error_detailed(
    error_type="ElementNotFoundError",
    message="无法找到目标元素",
    details={"selector": "text='登录按钮'", "timeout": "10s"},
    suggestion="检查元素选择器是否正确"
)
```

### 6. 会话统计
自动追踪工具调用、LLM调用、错误，在会话结束时输出完整统计。

### 7. 元素选择可追溯性
记录LLM选择元素的决策过程，包括候选列表和选择原因。

## 文件结构

```
logs/session_<id>/
├── session_raw.log          # 原始日志（时间戳格式）
├── session_unified.json      # 结构化日志（JSON）
├── result_dumps/             # 工具结果分离存储
└── screenshots/              # 截图分离存储
```

## 使用示例

```python
from only_test.lib.logging import get_logger

# 初始化（支持--verbose动态控制console级别）
console_level = logging.DEBUG if args.verbose else logging.INFO
logger = get_logger(session_id="test", log_dir="logs", console_level=console_level)

# 设置阶段
logger.set_phase("plan")
logger.info("开始制定计划")

# 执行阶段
logger.set_phase("execution", current_round=1, max_rounds=5)

# 工具调用（自动追踪统计）
logger.log_tool_execution(
    tool_name="get_current_screen_info",
    success=True,
    result=screen_result,
    execution_time=2.5
)

# 会话结束
logger.log_session_end({"status": "completed"})
```

## 关键实现

### _print_and_log()方法
用于需要自定义格式的输出（如树形结构），确保前后台同步：

```python
def _print_and_log(self, message: str, level: str = "info"):
    prefix = self._get_phase_prefix()
    print(f"{prefix}{message}")  # 控制台
    self.logger.log(log_level, message)  # 文件
```

### 级别控制
- **Console Handler**：可配置（默认INFO，--verbose时DEBUG）
- **File Handler**：固定DEBUG（始终记录所有日志）

这确保了：
- 控制台不会被DEBUG信息淹没
- 文件保留完整调试信息供事后分析

## 演示代码

`only_test/examples/logging_features_demo.py` - 包含所有功能的完整演示