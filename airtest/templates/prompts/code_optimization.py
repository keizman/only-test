#!/usr/bin/env python3
"""
Only-Test 代码优化 Prompt 模板

核心功能:
1. 代码重构和优化建议
2. 性能优化 Prompt
3. 维护性改进 Prompt  
4. 最佳实践应用 Prompt
"""

from typing import Dict, List, Optional, Any, Union


class CodeOptimizationPrompts:
    """代码优化提示词模板类"""
    
    @staticmethod
    def get_code_refactoring_prompt(
        original_code: str,
        refactoring_goals: List[str],
        constraints: Dict[str, Any] = None,
        quality_targets: Dict[str, float] = None
    ) -> str:
        """
        获取代码重构 Prompt
        
        Args:
            original_code: 原始代码
            refactoring_goals: 重构目标
            constraints: 重构约束
            quality_targets: 质量目标
        """
        
        goals_text = CodeOptimizationPrompts._format_refactoring_goals(refactoring_goals)
        constraints_text = CodeOptimizationPrompts._format_constraints(constraints or {})
        targets_text = CodeOptimizationPrompts._format_quality_targets(quality_targets or {})
        
        return f"""对测试用例代码进行重构优化，提升代码质量和维护性。

## 原始代码
```python
{original_code}
```

## 重构目标
{goals_text}

{constraints_text}

{targets_text}

## 重构原则和模式

### 1. SOLID 原则应用
- **单一职责原则 (SRP)**: 每个函数/类只负责一个职责
- **开放封闭原则 (OCP)**: 对扩展开放，对修改封闭
- **里氏替换原则 (LSP)**: 子类能够替换父类
- **接口隔离原则 (ISP)**: 依赖于抽象而非具体
- **依赖倒置原则 (DIP)**: 高层模块不依赖低层模块

### 2. 代码坏味道识别和修复

#### 2.1 长方法 (Long Method)
```python
# 坏味道示例
def long_test_method():
    # 100+ lines of code
    pass

# 重构后
def test_main_flow():
    setup_environment()
    execute_core_actions()
    verify_results()
    cleanup_resources()
```

#### 2.2 重复代码 (Duplicated Code)
```python
# 坏味道示例
def test_search_movie():
    poco("search_button").click()
    poco("search_input").set_text("movie")
    poco("search_submit").click()

def test_search_music():
    poco("search_button").click()
    poco("search_input").set_text("music")
    poco("search_submit").click()

# 重构后
def perform_search(query):
    poco("search_button").click()
    poco("search_input").set_text(query)
    poco("search_submit").click()

def test_search_movie():
    perform_search("movie")

def test_search_music():
    perform_search("music")
```

#### 2.3 大类 (Large Class)
```python
# 坏味道示例
class TestSuite:
    def setup(self): pass
    def test_login(self): pass
    def test_search(self): pass
    def test_play(self): pass
    def verify_result(self): pass
    def cleanup(self): pass

# 重构后
class TestEnvironment:
    def setup(self): pass
    def cleanup(self): pass

class AuthenticationTests:
    def test_login(self): pass

class SearchTests:
    def test_search(self): pass

class PlaybackTests:
    def test_play(self): pass
```

### 3. 设计模式应用

#### 3.1 Page Object 模式
```python
class SearchPage:
    def __init__(self, poco):
        self.poco = poco
        
    def search(self, query):
        self.poco("search_input").set_text(query)
        self.poco("search_button").click()
        
    def get_results(self):
        return self.poco("search_results").children()
```

#### 3.2 Strategy 模式
```python
class ElementLocatorStrategy:
    def locate(self, locator): pass

class ResourceIdStrategy(ElementLocatorStrategy):
    def locate(self, locator):
        return poco(locator)

class TextStrategy(ElementLocatorStrategy):
    def locate(self, locator):
        return poco(text=locator)

class VisualStrategy(ElementLocatorStrategy):
    def locate(self, locator):
        return find_by_visual(locator)
```

#### 3.3 Builder 模式
```python
class TestCaseBuilder:
    def __init__(self):
        self.steps = []
        
    def add_setup(self, action):
        self.steps.append(('setup', action))
        return self
        
    def add_action(self, action):
        self.steps.append(('action', action))
        return self
        
    def add_assertion(self, assertion):
        self.steps.append(('assert', assertion))
        return self
        
    def build(self):
        return TestCase(self.steps)
```

### 4. 性能优化策略

#### 4.1 减少重复操作
```python
# 优化前
for i in range(10):
    poco("list_item").child(f"item_{i}").click()
    sleep(1)  # 每次都等待

# 优化后
elements = poco("list_item").children()
for element in elements:
    element.click()
    # 智能等待，只在必要时等待
    element.wait_for_appearance(timeout=5)
```

#### 4.2 批量操作
```python
# 优化前
def verify_multiple_elements():
    assert poco("element1").exists()
    assert poco("element2").exists()
    assert poco("element3").exists()

# 优化后
def verify_multiple_elements():
    elements = ["element1", "element2", "element3"]
    missing_elements = []
    for elem in elements:
        if not poco(elem).exists():
            missing_elements.append(elem)
    assert not missing_elements, f"Missing elements: {missing_elements}"
```

### 5. 维护性改进

#### 5.1 配置外部化
```python
# 优化前
def test_login():
    username = "test@example.com"
    password = "password123"
    login(username, password)

# 优化后
class TestConfig:
    USERNAME = os.getenv('TEST_USERNAME', 'test@example.com')
    PASSWORD = os.getenv('TEST_PASSWORD', 'password123')

def test_login():
    login(TestConfig.USERNAME, TestConfig.PASSWORD)
```

#### 5.2 错误处理标准化
```python
class TestExecutionError(Exception):
    def __init__(self, step, original_error):
        self.step = step
        self.original_error = original_error
        super().__init__(f"Failed at step '{step}': {original_error}")

def execute_step_with_error_handling(step_func, step_name):
    try:
        return step_func()
    except Exception as e:
        logger.error(f"Step '{step_name}' failed: {e}")
        raise TestExecutionError(step_name, e)
```

## 重构检查清单

### 1. 代码结构
- [ ] 函数长度合理（< 30 行）
- [ ] 类职责单一
- [ ] 模块耦合度低
- [ ] 接口设计清晰

### 2. 命名规范
- [ ] 变量名具有描述性
- [ ] 函数名表达意图
- [ ] 类名符合命名约定
- [ ] 常量使用大写

### 3. 注释和文档
- [ ] 复杂逻辑有注释说明
- [ ] 公共接口有文档字符串
- [ ] TODO 项目有明确时间
- [ ] 变更历史有记录

### 4. 错误处理
- [ ] 异常处理完整
- [ ] 错误信息有意义
- [ ] 资源释放及时
- [ ] 失败恢复机制

## 输出要求

请提供详细的重构方案和优化代码：

```json
{{
  "refactoring_analysis": {{
    "code_smells_identified": [
      {{
        "smell_type": "long_method|duplicated_code|large_class|long_parameter_list",
        "location": "代码位置",
        "severity": "high|medium|low",
        "description": "问题描述",
        "impact": "影响分析"
      }}
    ],
    "complexity_metrics": {{
      "cyclomatic_complexity": 8,
      "lines_of_code": 150,
      "number_of_methods": 12,
      "depth_of_inheritance": 2
    }},
    "improvement_opportunities": [
      {{
        "opportunity": "改进机会",
        "benefit": "改进收益",
        "effort": "所需工作量",
        "priority": "high|medium|low"
      }}
    ]
  }},
  "refactoring_plan": {{
    "phase_1_immediate": [
      {{
        "task": "重构任务",
        "description": "任务描述",
        "code_change": "代码变更",
        "risk_level": "low|medium|high"
      }}
    ],
    "phase_2_structural": [
      {{
        "task": "结构重构任务",
        "description": "任务描述",
        "design_pattern": "应用的设计模式",
        "code_change": "代码变更"
      }}
    ],
    "phase_3_architectural": [
      {{
        "task": "架构改进任务",
        "description": "任务描述",
        "architectural_change": "架构变更",
        "long_term_benefit": "长期收益"
      }}
    ]
  }},
  "refactored_code": {{
    "complete_code": "重构后的完整代码",
    "key_improvements": [
      {{
        "improvement": "改进内容",
        "before": "重构前代码片段",
        "after": "重构后代码片段",
        "benefit": "改进效果"
      }}
    ],
    "new_design_patterns": ["应用的设计模式1", "应用的设计模式2"],
    "performance_impact": "性能影响评估"
  }},
  "quality_metrics": {{
    "maintainability_index": 85,
    "code_coverage": 90,
    "technical_debt_ratio": 5,
    "before_after_comparison": "重构前后对比"
  }},
  "migration_guide": {{
    "breaking_changes": ["破坏性变更1", "破坏性变更2"],
    "migration_steps": ["迁移步骤1", "迁移步骤2"],
    "rollback_plan": "回滚计划"
  }}
}}
```

现在请开始代码重构分析和优化:"""
    
    @staticmethod
    def get_performance_optimization_prompt(
        code_with_performance_issues: str,
        performance_requirements: Dict[str, Union[int, float]],
        profiling_data: Dict[str, Any] = None,
        optimization_constraints: List[str] = None
    ) -> str:
        """
        获取性能优化 Prompt
        """
        
        requirements_text = CodeOptimizationPrompts._format_performance_requirements(performance_requirements)
        profiling_text = CodeOptimizationPrompts._format_profiling_data(profiling_data or {})
        constraints_text = CodeOptimizationPrompts._format_optimization_constraints(optimization_constraints or [])
        
        return f"""对测试用例进行性能优化，提升执行效率和资源利用率。

## 待优化代码
```python
{code_with_performance_issues}
```

## 性能要求
{requirements_text}

{profiling_text}

{constraints_text}

## 性能优化策略

### 1. 执行时间优化

#### 1.1 减少不必要的等待
```python
# 优化前 - 固定等待
sleep(5)  # 总是等待5秒

# 优化后 - 智能等待
def smart_wait(condition_func, timeout=5, interval=0.1):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    return False

smart_wait(lambda: poco("element").exists(), timeout=5)
```

#### 1.2 并行化操作
```python
# 优化前 - 串行执行
results = []
for item in items:
    result = process_item(item)
    results.append(result)

# 优化后 - 并行执行
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_item, items))
```

#### 1.3 缓存机制
```python
# 优化前 - 重复计算
def get_element_info(locator):
    element = poco(locator)
    return {
        'exists': element.exists(),
        'text': element.get_text() if element.exists() else '',
        'bounds': element.get_bounds() if element.exists() else None
    }

# 优化后 - 缓存结果
from functools import lru_cache

@lru_cache(maxsize=128)
def get_element_info(locator):
    element = poco(locator)
    if element.exists():
        return {
            'exists': True,
            'text': element.get_text(),
            'bounds': element.get_bounds()
        }
    return {'exists': False, 'text': '', 'bounds': None}
```

### 2. 内存优化

#### 2.1 避免内存泄漏
```python
# 优化前 - 可能的内存泄漏
class TestExecutor:
    def __init__(self):
        self.screenshots = []  # 无限增长
        
    def take_screenshot(self):
        screenshot = poco.snapshot()
        self.screenshots.append(screenshot)

# 优化后 - 资源管理
class TestExecutor:
    def __init__(self, max_screenshots=10):
        self.screenshots = deque(maxlen=max_screenshots)
        
    def take_screenshot(self):
        screenshot = poco.snapshot()
        self.screenshots.append(screenshot)
        
    def __del__(self):
        self.screenshots.clear()
```

#### 2.2 懒加载
```python
# 优化前 - 立即加载所有数据
class TestData:
    def __init__(self):
        self.large_dataset = self.load_all_data()  # 立即加载
        
# 优化后 - 按需加载
class TestData:
    def __init__(self):
        self._large_dataset = None
        
    @property
    def large_dataset(self):
        if self._large_dataset is None:
            self._large_dataset = self.load_all_data()
        return self._large_dataset
```

### 3. 网络和I/O优化

#### 3.1 连接池
```python
# 优化前 - 频繁建立连接
def make_api_call(endpoint, data):
    connection = create_connection()
    result = connection.post(endpoint, data)
    connection.close()
    return result

# 优化后 - 连接池
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

def make_api_call(endpoint, data):
    return session.post(endpoint, data)
```

#### 3.2 批量操作
```python
# 优化前 - 单个文件操作
for file_path in file_paths:
    with open(file_path, 'r') as f:
        content = f.read()
        process_content(content)

# 优化后 - 批量读取
def read_files_batch(file_paths, batch_size=10):
    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i+batch_size]
        contents = []
        for file_path in batch:
            with open(file_path, 'r') as f:
                contents.append(f.read())
        yield contents
```

### 4. 算法优化

#### 4.1 选择合适的数据结构
```python
# 优化前 - 线性查找
element_list = ["elem1", "elem2", "elem3", ...]
if "target_elem" in element_list:  # O(n) 复杂度
    process_element()

# 优化后 - 哈希查找
element_set = {"elem1", "elem2", "elem3", ...}
if "target_elem" in element_set:  # O(1) 复杂度
    process_element()
```

#### 4.2 减少循环复杂度
```python
# 优化前 - 嵌套循环
results = []
for i in range(len(list1)):
    for j in range(len(list2)):
        if list1[i] == list2[j]:
            results.append(list1[i])

# 优化后 - 集合操作
set1 = set(list1)
set2 = set(list2)
results = list(set1.intersection(set2))
```

### 5. 资源管理优化

#### 5.1 上下文管理器
```python
# 优化前 - 手动资源管理
def test_with_file():
    f = open("test_data.txt")
    data = f.read()
    # 可能忘记关闭文件
    process_data(data)
    f.close()

# 优化后 - 自动资源管理
def test_with_file():
    with open("test_data.txt") as f:
        data = f.read()
        process_data(data)
    # 自动关闭文件
```

#### 5.2 对象池
```python
class DriverPool:
    def __init__(self, size=5):
        self.size = size
        self.drivers = queue.Queue()
        self._create_drivers()
        
    def _create_drivers(self):
        for _ in range(self.size):
            driver = create_driver()
            self.drivers.put(driver)
            
    def get_driver(self):
        return self.drivers.get()
        
    def return_driver(self, driver):
        self.drivers.put(driver)
        
    @contextmanager
    def driver(self):
        driver = self.get_driver()
        try:
            yield driver
        finally:
            self.return_driver(driver)
```

## 性能测试基准

### 1. 执行时间基准
```python
import time
from functools import wraps

def benchmark(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print(f"{func.__name__} executed in {execution_time:.4f} seconds")
        return result
    return wrapper

@benchmark
def test_function():
    # 测试代码
    pass
```

### 2. 内存使用基准
```python
import psutil
import os

def memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def test_memory_usage():
    initial_memory = memory_usage()
    # 执行测试代码
    execute_test()
    final_memory = memory_usage()
    memory_increase = final_memory - initial_memory
    print(f"Memory usage increased by {memory_increase:.2f} MB")
```

## 输出要求

请提供详细的性能优化方案：

```json
{{
  "performance_analysis": {{
    "current_metrics": {{
      "execution_time": "当前执行时间",
      "memory_usage": "内存使用量",
      "cpu_utilization": "CPU利用率",
      "io_operations": "I/O操作次数"
    }},
    "bottlenecks_identified": [
      {{
        "bottleneck_type": "cpu|memory|io|network",
        "location": "性能瓶颈位置",
        "severity": "high|medium|low",
        "impact": "性能影响描述",
        "root_cause": "根本原因分析"
      }}
    ],
    "optimization_potential": {{
      "time_savings": "可节省时间",
      "memory_reduction": "可减少内存",
      "efficiency_gain": "效率提升百分比"
    }}
  }},
  "optimization_strategies": [
    {{
      "strategy_type": "algorithm|caching|parallelization|resource_management",
      "description": "优化策略描述",
      "implementation": "具体实现方法",
      "expected_improvement": "预期改进效果",
      "implementation_complexity": "实现复杂度",
      "risk_assessment": "风险评估"
    }}
  ],
  "optimized_code": {{
    "complete_optimized_code": "完整的优化后代码",
    "performance_improvements": [
      {{
        "area": "优化领域",
        "before": "优化前代码",
        "after": "优化后代码",
        "improvement_ratio": "改进倍数",
        "explanation": "优化说明"
      }}
    ],
    "new_dependencies": ["新依赖1", "新依赖2"],
    "configuration_changes": "配置变更说明"
  }},
  "performance_validation": {{
    "benchmark_tests": [
      {{
        "test_name": "基准测试名称",
        "test_code": "测试代码",
        "success_criteria": "成功标准"
      }}
    ],
    "monitoring_recommendations": [
      "监控建议1",
      "监控建议2"
    ],
    "regression_prevention": [
      "回归预防措施1",
      "回归预防措施2"
    ]
  }},
  "deployment_considerations": {{
    "rollout_strategy": "部署策略",
    "rollback_plan": "回滚计划",
    "monitoring_during_deployment": "部署期间监控"
  }}
}}
```

现在请开始性能优化分析:"""
    
    @staticmethod
    def get_maintainability_improvement_prompt(
        legacy_code: str,
        maintenance_pain_points: List[str],
        team_standards: Dict[str, Any] = None,
        future_requirements: List[str] = None
    ) -> str:
        """
        获取维护性改进 Prompt
        """
        
        pain_points_text = CodeOptimizationPrompts._format_maintenance_pain_points(maintenance_pain_points)
        standards_text = CodeOptimizationPrompts._format_team_standards(team_standards or {})
        future_text = CodeOptimizationPrompts._format_future_requirements(future_requirements or [])
        
        return f"""改进测试代码的维护性，降低维护成本，提高开发效率。

## 现有代码
```python
{legacy_code}
```

## 维护痛点
{pain_points_text}

{standards_text}

{future_text}

## 维护性改进策略

### 1. 代码可读性提升

#### 1.1 命名改进
```python
# 改进前 - 不清晰的命名
def f1(x, y):
    return x + y

def test_1():
    a = f1(2, 3)
    assert a == 5

# 改进后 - 描述性命名
def calculate_sum(first_number, second_number):
    return first_number + second_number

def test_sum_calculation():
    actual_sum = calculate_sum(2, 3)
    expected_sum = 5
    assert actual_sum == expected_sum
```

#### 1.2 代码结构化
```python
# 改进前 - 扁平结构
def test_complete_user_journey():
    # 100+ lines of mixed logic
    login_user()
    search_content()
    play_video()
    verify_playback()
    logout_user()

# 改进后 - 分层结构
class UserJourneyTest:
    def setUp(self):
        self.user_session = UserSession()
        
    def test_complete_user_journey(self):
        self._authenticate_user()
        self._search_and_select_content()
        self._verify_playback_experience()
        self._cleanup_session()
        
    def _authenticate_user(self):
        # 认证逻辑
        pass
        
    def _search_and_select_content(self):
        # 搜索选择逻辑
        pass
```

### 2. 模块化设计

#### 2.1 功能模块分离
```python
# 改进前 - 单一大文件
# test_all_features.py (1000+ lines)

# 改进后 - 模块化结构
# tests/
#   authentication/
#     test_login.py
#     test_logout.py
#   search/
#     test_search_functionality.py
#     test_search_filters.py
#   playback/
#     test_video_playback.py
#     test_audio_playback.py
```

#### 2.2 共用组件提取
```python
# 改进前 - 重复的页面对象
class TestLogin:
    def click_login_button(self):
        poco("login_button").click()
        
class TestProfile:
    def click_login_button(self):
        poco("login_button").click()

# 改进后 - 共享页面对象
class LoginPage:
    def __init__(self, poco):
        self.poco = poco
        
    def click_login_button(self):
        self.poco("login_button").click()
        
    def enter_credentials(self, username, password):
        self.poco("username").set_text(username)
        self.poco("password").set_text(password)

class TestLogin:
    def setUp(self):
        self.login_page = LoginPage(poco)
        
    def test_login(self):
        self.login_page.enter_credentials("user", "pass")
        self.login_page.click_login_button()
```

### 3. 配置管理

#### 3.1 环境配置外部化
```python
# 改进前 - 硬编码配置
def test_api_endpoint():
    response = requests.get("http://test.example.com/api")
    assert response.status_code == 200

# 改进后 - 配置文件
# config.yaml
environments:
  test:
    api_base_url: "http://test.example.com"
  staging:
    api_base_url: "http://staging.example.com"
  production:
    api_base_url: "http://api.example.com"

# test_api.py
class Config:
    def __init__(self):
        with open("config.yaml") as f:
            self.config = yaml.load(f)
    
    def get_api_url(self, env="test"):
        return self.config["environments"][env]["api_base_url"]

def test_api_endpoint():
    config = Config()
    api_url = config.get_api_url()
    response = requests.get(f"{api_url}/api")
    assert response.status_code == 200
```

#### 3.2 测试数据管理
```python
# 改进前 - 内联测试数据
def test_user_registration():
    username = "testuser123"
    email = "test@example.com"
    password = "password123"
    register_user(username, email, password)

# 改进后 - 数据文件管理
# test_data.json
{
  "users": {
    "valid_user": {
      "username": "testuser123",
      "email": "test@example.com", 
      "password": "password123"
    },
    "invalid_user": {
      "username": "",
      "email": "invalid-email",
      "password": "123"
    }
  }
}

# test_registration.py
class TestDataManager:
    def __init__(self):
        with open("test_data.json") as f:
            self.data = json.load(f)
    
    def get_user_data(self, user_type):
        return self.data["users"][user_type]

def test_user_registration():
    data_manager = TestDataManager()
    user_data = data_manager.get_user_data("valid_user")
    register_user(**user_data)
```

### 4. 错误处理和调试

#### 4.1 统一错误处理
```python
# 改进前 - 散乱的错误处理
def test_step_1():
    try:
        action_1()
    except Exception as e:
        print(f"Error: {e}")
        raise

def test_step_2():
    try:
        action_2()
    except Exception as e:
        logger.error(f"Failed: {e}")
        raise

# 改进后 - 统一错误处理
class TestExecutionError(Exception):
    def __init__(self, step_name, original_error, context=None):
        self.step_name = step_name
        self.original_error = original_error
        self.context = context or {}
        message = f"Step '{step_name}' failed: {original_error}"
        if context:
            message += f" Context: {context}"
        super().__init__(message)

def execute_with_error_handling(step_func, step_name, context=None):
    try:
        return step_func()
    except Exception as e:
        # 统一日志记录
        logger.error(f"Step '{step_name}' failed", exc_info=True)
        # 截图保存
        save_failure_screenshot(step_name)
        # 抛出统一异常
        raise TestExecutionError(step_name, e, context)
```

#### 4.2 调试信息增强
```python
# 改进前 - 缺乏调试信息
def verify_element_visible(locator):
    assert poco(locator).exists()

# 改进后 - 丰富调试信息
def verify_element_visible(locator, timeout=10):
    start_time = time.time()
    element = poco(locator)
    
    if not element.wait_for_appearance(timeout):
        # 收集调试信息
        debug_info = {
            'locator': locator,
            'timeout': timeout,
            'elapsed_time': time.time() - start_time,
            'current_page': get_current_page(),
            'visible_elements': get_visible_elements(),
            'screenshot_path': save_debug_screenshot()
        }
        
        error_msg = f"Element '{locator}' not found within {timeout}s"
        logger.error(error_msg, extra={'debug_info': debug_info})
        
        raise AssertionError(f"{error_msg}. Debug info: {debug_info}")
```

### 5. 文档和注释

#### 5.1 自文档化代码
```python
# 改进前 - 需要注释解释的代码
def calc(a, b, t):
    # t=1表示加法，t=2表示乘法
    if t == 1:
        return a + b
    elif t == 2:
        return a * b

# 改进后 - 自文档化代码
from enum import Enum

class CalculationType(Enum):
    ADD = "add"
    MULTIPLY = "multiply"

def calculate(first_number: int, second_number: int, 
             operation: CalculationType) -> int:
    if operation == CalculationType.ADD:
        return first_number + second_number
    elif operation == CalculationType.MULTIPLY:
        return first_number * second_number
```

#### 5.2 API 文档化
```python
def search_content(query: str, filters: Dict[str, Any] = None, 
                  max_results: int = 10) -> List[Dict[str, Any]]:
    '''
    搜索内容并返回结果列表
    
    Args:
        query: 搜索查询字符串
        filters: 可选的搜索过滤器，键值对形式
            - 'category': 内容分类 (str)
            - 'duration_min': 最小时长分钟数 (int)
            - 'rating_min': 最低评分 (float)
        max_results: 最大返回结果数，默认10
        
    Returns:
        搜索结果列表，每个结果包含：
            - 'title': 标题 (str)
            - 'category': 分类 (str) 
            - 'duration': 时长分钟数 (int)
            - 'rating': 评分 (float)
            
    Raises:
        SearchError: 搜索执行失败
        ValidationError: 参数验证失败
        
    Example:
        >>> results = search_content("action movie", 
        ...                         {'category': 'movie', 'rating_min': 7.0},
        ...                         max_results=5)
        >>> len(results) <= 5
        True
    '''
    pass
```

## 维护性评估指标

### 1. 代码复杂度
- **圈复杂度**: 测量代码路径复杂度
- **认知复杂度**: 测量代码理解难度
- **嵌套深度**: 测量代码层次深度

### 2. 可读性指标
- **命名质量**: 标识符命名的描述性
- **函数长度**: 函数的平均行数
- **注释覆盖**: 关键逻辑的注释比例

### 3. 耦合度
- **模块耦合**: 模块间的依赖关系
- **数据耦合**: 数据传递的复杂程度
- **接口稳定性**: API接口的变化频率

## 输出要求

请提供全面的维护性改进方案：

```json
{{
  "maintainability_assessment": {{
    "current_metrics": {{
      "cyclomatic_complexity": 8,
      "cognitive_complexity": 12,
      "code_duplication": "15%",
      "test_coverage": "75%",
      "documentation_coverage": "60%"
    }},
    "pain_points_analysis": [
      {{
        "pain_point": "维护痛点",
        "severity": "high|medium|low",
        "frequency": "daily|weekly|monthly",
        "impact": "影响描述",
        "root_cause": "根本原因"
      }}
    ],
    "improvement_priorities": [
      {{
        "area": "改进领域",
        "priority": "high|medium|low", 
        "effort": "所需工作量",
        "benefit": "预期收益"
      }}
    ]
  }},
  "improvement_plan": {{
    "immediate_improvements": [
      {{
        "improvement": "立即改进项",
        "description": "改进描述",
        "implementation": "实施方法",
        "expected_outcome": "预期结果"
      }}
    ],
    "structural_changes": [
      {{
        "change": "结构性变更",
        "rationale": "变更理由",
        "implementation_plan": "实施计划",
        "migration_strategy": "迁移策略"
      }}
    ],
    "long_term_vision": [
      {{
        "vision": "长期愿景",
        "milestones": ["里程碑1", "里程碑2"],
        "success_criteria": "成功标准"
      }}
    ]
  }},
  "improved_code": {{
    "refactored_code": "重构后的代码",
    "architectural_changes": [
      {{
        "component": "组件名称",
        "old_design": "原设计",
        "new_design": "新设计",
        "benefits": "改进收益"
      }}
    ],
    "new_conventions": [
      "新的编码约定1",
      "新的编码约定2"
    ]
  }},
  "maintenance_guidelines": {{
    "coding_standards": "编码标准文档",
    "review_checklist": ["审查检查项1", "审查检查项2"],
    "testing_guidelines": "测试指南",
    "documentation_standards": "文档标准"
  }},
  "training_recommendations": [
    "培训建议1",
    "培训建议2"
  ]
}}
```

现在请开始维护性改进分析:"""
    
    # 辅助方法
    @staticmethod
    def _format_refactoring_goals(goals: List[str]) -> str:
        """格式化重构目标"""
        goals_text = '\n'.join([f"- {goal}" for goal in goals])
        return f"""
{goals_text}
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
## 重构约束
{chr(10).join(constraints_info)}
"""
    
    @staticmethod
    def _format_quality_targets(targets: Dict[str, float]) -> str:
        """格式化质量目标"""
        if not targets:
            return ""
        
        targets_info = []
        for key, value in targets.items():
            targets_info.append(f"**{key}**: {value}")
        
        return f"""
## 质量目标
{chr(10).join(targets_info)}
"""
    
    @staticmethod
    def _format_performance_requirements(requirements: Dict[str, Union[int, float]]) -> str:
        """格式化性能要求"""
        requirements_info = []
        for key, value in requirements.items():
            requirements_info.append(f"**{key}**: {value}")
        
        return '\n'.join(requirements_info)
    
    @staticmethod
    def _format_profiling_data(data: Dict[str, Any]) -> str:
        """格式化性能分析数据"""
        if not data:
            return ""
        
        profiling_info = []
        for key, value in data.items():
            profiling_info.append(f"**{key}**: {value}")
        
        return f"""
## 性能分析数据
{chr(10).join(profiling_info)}
"""
    
    @staticmethod
    def _format_optimization_constraints(constraints: List[str]) -> str:
        """格式化优化约束"""
        if not constraints:
            return ""
        
        constraints_text = '\n'.join([f"- {constraint}" for constraint in constraints])
        return f"""
## 优化约束
{constraints_text}
"""
    
    @staticmethod
    def _format_maintenance_pain_points(pain_points: List[str]) -> str:
        """格式化维护痛点"""
        pain_points_text = '\n'.join([f"- {point}" for point in pain_points])
        return f"""
{pain_points_text}
"""
    
    @staticmethod
    def _format_team_standards(standards: Dict[str, Any]) -> str:
        """格式化团队标准"""
        if not standards:
            return ""
        
        standards_info = []
        for key, value in standards.items():
            standards_info.append(f"**{key}**: {value}")
        
        return f"""
## 团队标准
{chr(10).join(standards_info)}
"""
    
    @staticmethod
    def _format_future_requirements(requirements: List[str]) -> str:
        """格式化未来需求"""
        if not requirements:
            return ""
        
        requirements_text = '\n'.join([f"- {req}" for req in requirements])
        return f"""
## 未来需求
{requirements_text}
"""