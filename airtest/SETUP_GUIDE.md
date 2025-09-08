# 🛠️ Only-Test 安装配置指南

## 📋 系统要求

### 软件要求
- **Python**: 3.8 或更高版本 (推荐 3.9+)
- **操作系统**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **Android设备**: Android 5.0 (API 21) 或更高版本
- **Java**: JDK 8 或更高版本

### 硬件要求
- **内存**: 最小 4GB RAM (推荐 8GB+)
- **存储**: 最小 2GB 可用空间
- **网络**: 稳定的网络连接 (用于LLM API调用)

## 🚀 快速安装

### 1. 克隆项目
```bash
git clone <repository-url>
cd airtest
```

### 2. 创建虚拟环境 (推荐)
```bash
# 使用 venv
python -m venv only_test_env
source only_test_env/bin/activate  # Linux/macOS
# 或
only_test_env\Scripts\activate     # Windows

# 使用 conda
conda create -n only_test python=3.9
conda activate only_test
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置环境变量
```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件，填入你的API密钥
nano .env  # 或使用其他编辑器
```

### 5. 验证安装
```bash
python tools/integration_check.py
```

## ⚙️ 详细配置

### 环境变量配置 (.env)

```bash
# === LLM服务配置 ===
LLM_PROVIDER=openai_compatible
LLM_API_URL=https://your-api-endpoint.com/v1/chat/completions
LLM_API_KEY=sk-your-api-key-here
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7

# === 备用LLM配置 ===
LLM_FALLBACK_PROVIDER=openai
LLM_FALLBACK_API_KEY=sk-your-fallback-key
LLM_FALLBACK_MODEL=gpt-3.5-turbo

# === 开发环境配置 ===
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

### 主配置文件 (testcases/main.yaml)

参考现有的 `main.yaml` 文件，根据你的设备和应用进行配置：

```yaml
devices:
  your_device_id:
    phone_type: "android_phone"
    custom_name: "Your Device Name"
    android_version: "13"
    screen_info:
      resolution: "1080x1920"
      density: 420

applications:
  your_app:
    package_name: "com.your.app"
    app_name: "Your App"
    category: "your_category"
```

## 📱 Android设备配置

### 1. 启用开发者选项
1. 设置 → 关于手机
2. 连续点击"版本号"7次
3. 返回设置，进入"开发者选项"

### 2. 启用USB调试
1. 开发者选项 → USB调试 (开启)
2. 开发者选项 → USB安装 (开启)
3. 开发者选项 → USB调试(安全设置) (开启)

### 3. 连接设备
```bash
# 检查设备连接
adb devices

# 如果没有设备，尝试重启ADB
adb kill-server
adb start-server
adb devices
```

### 4. 安装UIAutomator2
```bash
# 自动安装UIAutomator2服务
python -c "import uiautomator2 as u2; u2.connect().app_install('https://github.com/openatx/android-uiautomator-server/releases/download/1.3.6/app-uiautomator.apk')"
```

## 🧪 验证安装

### 基础功能测试
```bash
# 1. 配置系统检查
python tools/integration_check.py

# 2. 设备信息探测
python lib/device_adapter.py testcases/main.yaml --detect-only

# 3. LLM连接测试
python -c "from lib.llm_integration.llm_client import LLMClient; print('LLM可用:', LLMClient().is_available())"
```

### 生成测试用例
```bash
# 使用自然语言生成测试用例
python tools/case_generator.py \
  --description "在应用中搜索内容并验证结果" \
  --app com.example.app
```

### 运行完整工作流
```bash
# 运行完整演示
python examples/complete_workflow_demo.py
```

## 🐛 常见问题解决

### 问题1: 找不到Python模块
```bash
# 错误: ModuleNotFoundError: No module named 'yaml'
pip install pyyaml>=6.0

# 错误: No module named 'openai'
pip install openai>=1.0.0
```

### 问题2: ADB设备连接失败
```bash
# 检查ADB版本
adb version

# 重启ADB服务
adb kill-server && adb start-server

# 检查设备权限
adb shell pm list permissions | grep android.permission
```

### 问题3: UIAutomator2连接失败
```bash
# 重新安装UIAutomator2服务
python -m uiautomator2 init

# 检查服务状态
adb shell am instrument -e debug false -w com.github.uiautomator.test/androidx.test.runner.AndroidJUnitRunner
```

### 问题4: LLM API调用失败
```bash
# 检查网络连接
curl -I https://api.openai.com

# 验证API密钥
python -c "
from openai import OpenAI
client = OpenAI(api_key='your-key')
print('API Key 有效:', bool(client))
"
```

### 问题5: 权限问题
```bash
# Linux/macOS 权限修复
chmod +x tools/*.py
chmod +x lib/*.py

# Windows 权限问题
# 以管理员身份运行终端
```

## 🔧 高级配置

### 1. 多设备并行测试
```yaml
# main.yaml 中配置多个设备
devices:
  device1:
    custom_name: "Pixel 6 Pro"
    connection:
      adb_serial: "123456789"
  device2:
    custom_name: "Samsung Galaxy"
    connection:
      adb_serial: "987654321"
```

### 2. 自定义LLM提供商
```python
# 扩展 LLMClient 支持自定义API
from lib.llm_integration.llm_client import BaseLLMProvider

class CustomLLMProvider(BaseLLMProvider):
    def chat_completion(self, messages, **kwargs):
        # 实现你的自定义LLM接口
        pass
```

### 3. 持续集成配置
```yaml
# .github/workflows/test.yml
name: Only-Test CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - run: pip install -r requirements.txt
    - run: python tools/integration_check.py
```

## 📚 下一步

1. **阅读文档**: 查看 `README.md` 了解框架设计理念
2. **查看示例**: 运行 `examples/complete_workflow_demo.py`
3. **配置设备**: 根据你的测试设备更新 `main.yaml`
4. **生成测试**: 使用自然语言描述生成你的第一个测试用例
5. **加入社区**: 参与项目改进和功能建议

## 🆘 获取帮助

- **GitHub Issues**: 报告问题和功能建议
- **文档**: 查看项目 Wiki 和详细文档
- **示例代码**: `examples/` 目录包含完整的使用示例

---

**Happy Testing!** 🎯