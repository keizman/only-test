#!/usr/bin/env python3
"""
Only-Test LLM 驱动的测试用例生成器

核心功能:
1. 从自然语言描述生成测试用例
2. 基于现有用例模板生成相似用例  
3. 智能元素定位和路径生成
4. 支持多种 LLM 模型 (OpenAI GPT, Claude, 本地模型等)
"""

import sys
import os
import json
import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from airtest.lib.pure_uiautomator2_extractor import UIAutomationScheduler, UnifiedElement

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_generator")

@dataclass
class TestStep:
    """测试步骤数据结构"""
    page: str
    action: str
    comment: str
    target_element: Optional[str] = None
    element_uuid: Optional[str] = None
    input_text: Optional[str] = None
    wait_time: Optional[float] = None
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class TestCaseMetadata:
    """测试用例元数据"""
    testcase_id: str
    name: str
    description: str
    tags: List[str]
    path: List[str]  # 页面路径
    steps: List[TestStep]
    created_at: str
    device_type: str


class LLMClient:
    """LLM 客户端基类"""
    
    def __init__(self, model_name: str = "gpt-4"):
        self.model_name = model_name
    
    async def generate_completion(self, prompt: str, temperature: float = 0.7) -> str:
        """生成文本完成 - 子类需要实现"""
        raise NotImplementedError


class OpenAIClient(LLMClient):
    """OpenAI GPT 客户端"""
    
    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        super().__init__(model_name)
        self.api_key = api_key
        
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=api_key)
        except ImportError:
            logger.error("请安装 openai 包: pip install openai")
            raise
    
    async def generate_completion(self, prompt: str, temperature: float = 0.7) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API 调用失败: {e}")
            raise


class OllamaClient(LLMClient):
    """本地 Ollama 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "qwen2.5:32b"):
        super().__init__(model_name)
        self.base_url = base_url.rstrip('/')
        
        try:
            import requests
            self.session = requests.Session()
        except ImportError:
            logger.error("请安装 requests 包: pip install requests")
            raise
    
    async def generate_completion(self, prompt: str, temperature: float = 0.7) -> str:
        try:
            import asyncio
            import json
            
            # 使用 asyncio 运行同步请求
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "temperature": temperature,
                        "stream": False
                    },
                    timeout=120
                )
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                raise Exception(f"Ollama API 返回错误: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ollama API 调用失败: {e}")
            raise


class TestCaseGenerator:
    """测试用例生成器"""
    
    def __init__(self, device_id: str = None, llm_client: LLMClient = None):
        self.device_id = device_id
        self.llm_client = llm_client or self._create_default_llm_client()
        
        # 初始化UI自动化调度器
        self.ui_scheduler = UIAutomationScheduler(device_id)
        
        # 路径配置
        self.base_dir = Path(__file__).parent.parent.parent
        self.templates_dir = self.base_dir / "templates"
        self.testcases_dir = self.base_dir / "airtest" / "testcases"
        self.metadata_dir = self.testcases_dir / "metadata"
        self.python_dir = self.testcases_dir / "python"
        
        # 确保目录存在
        self.templates_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)
        self.python_dir.mkdir(exist_ok=True)
    
    def _create_default_llm_client(self) -> LLMClient:
        """创建默认LLM客户端"""
        # 优先使用环境变量中的OpenAI API Key
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            logger.info("使用 OpenAI GPT-4 模型")
            return OpenAIClient(api_key, "gpt-4")
        
        # 回退到本地 Ollama
        logger.info("使用本地 Ollama 模型")
        return OllamaClient()
    
    def load_template_examples(self) -> List[Dict[str, Any]]:
        """加载现有测试用例作为模板"""
        examples = []
        
        # 加载现有的Python测试用例
        for py_file in self.python_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 解析测试用例的元数据注释
                metadata = self._parse_testcase_metadata(content)
                if metadata:
                    examples.append({
                        "file": py_file.name,
                        "metadata": metadata,
                        "content": content[:2000]  # 只保留前2000字符作为示例
                    })
            except Exception as e:
                logger.warning(f"加载模板文件 {py_file} 失败: {e}")
        
        logger.info(f"加载了 {len(examples)} 个测试用例模板")
        return examples
    
    def _parse_testcase_metadata(self, content: str) -> Optional[Dict[str, Any]]:
        """从测试用例内容解析元数据"""
        lines = content.split('\n')
        metadata = {}
        
        for line in lines[:20]:  # 只检查前20行
            line = line.strip()
            if line.startswith('# [tag]'):
                metadata['tags'] = [tag.strip() for tag in line.replace('# [tag]', '').split(',')]
            elif line.startswith('# [path]'):
                metadata['path'] = [page.strip() for page in line.replace('# [path]', '').split('->')]
            elif line.startswith('## [page]') and '[comment]' in line:
                # 解析步骤注释
                if 'steps' not in metadata:
                    metadata['steps'] = []
                    
                # 提取页面、动作和注释
                parts = line.split(',')
                page_part = [p for p in parts if '[page]' in p]
                action_part = [p for p in parts if '[action]' in p]
                comment_part = [p for p in parts if '[comment]' in p]
                
                if page_part and comment_part:
                    page = page_part[0].replace('## [page]', '').strip()
                    action = action_part[0].replace('[action]', '').strip() if action_part else 'unknown'
                    comment = comment_part[0].replace('[comment]', '').strip()
                    
                    metadata['steps'].append({
                        'page': page,
                        'action': action, 
                        'comment': comment
                    })
        
        return metadata if metadata else None
    
    def _build_generation_prompt(self, description: str, examples: List[Dict[str, Any]]) -> str:
        """构建用例生成的Prompt"""
        
        # 准备示例模板
        example_templates = []
        for example in examples[:3]:  # 只使用前3个最相关的例子
            example_templates.append(f"""
示例用例: {example['file']}
标签: {example['metadata'].get('tags', [])}
路径: {' -> '.join(example['metadata'].get('path', []))}
部分代码:
```python
{example['content'][:800]}...
```
""")
        
        prompt = f"""你是Only-Test框架的测试用例生成专家。请根据用户描述生成高质量的自动化测试用例。

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

### 3. 页面类型
- home: 首页
- search: 搜索页面  
- search_result: 搜索结果页面
- vod: 点播内容页面
- vod_playing_detail: 点播详情页面
- playing: 播放页面
- live: 直播页面
- login: 登录页面
- signup: 注册页面
- settings: 设置页面
- user_center: 用户中心

### 4. 动作类型
- launch: 启动应用
- click: 点击操作
- input: 文本输入
- swipe: 滑动操作
- wait: 等待操作
- assert: 断言验证

### 5. 智能条件判断
当存在多种可能的操作路径时，请在comment中描述判断逻辑，例如：
"根据搜索框内容状态智能选择点击搜索或取消搜索按钮"

## 现有测试用例示例
{"".join(example_templates)}

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

        return prompt
    
    async def generate_from_description(self, description: str) -> str:
        """从自然语言描述生成测试用例"""
        try:
            logger.info(f"开始生成测试用例: {description}")
            
            # 加载现有模板例子
            examples = self.load_template_examples()
            
            # 构建生成提示
            prompt = self._build_generation_prompt(description, examples)
            
            # 调用LLM生成
            logger.info("正在调用LLM生成测试用例...")
            generated_content = await self.llm_client.generate_completion(prompt, temperature=0.3)
            
            # 提取Python代码块
            python_code = self._extract_python_code(generated_content)
            
            if not python_code:
                raise Exception("LLM未能生成有效的Python代码")
            
            # 生成测试用例文件名
            testcase_name = self._generate_testcase_name(description)
            
            # 保存生成的测试用例
            testcase_file = self.python_dir / f"{testcase_name}.py"
            with open(testcase_file, 'w', encoding='utf-8') as f:
                f.write(python_code)
            
            logger.info(f"✅ 测试用例生成成功: {testcase_file}")
            
            # 解析并保存元数据
            metadata = self._parse_testcase_metadata(python_code)
            if metadata:
                metadata_file = self.metadata_dir / f"{testcase_name}.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "testcase_id": testcase_name,
                        "description": description,
                        "generated_at": datetime.now().isoformat(),
                        "metadata": metadata
                    }, f, indent=2, ensure_ascii=False)
            
            return testcase_name
            
        except Exception as e:
            logger.error(f"生成测试用例失败: {e}")
            raise
    
    def _extract_python_code(self, content: str) -> Optional[str]:
        """从LLM输出中提取Python代码"""
        # 查找代码块标记
        if '```python' in content:
            start = content.find('```python') + len('```python')
            end = content.find('```', start)
            if end != -1:
                return content[start:end].strip()
        
        # 如果没有找到代码块标记，尝试提取整个内容
        lines = content.split('\n')
        python_lines = []
        in_code = False
        
        for line in lines:
            # 检查是否是Python代码行
            if (line.strip().startswith('#') or 
                line.strip().startswith('from ') or
                line.strip().startswith('import ') or
                'connect_device' in line or
                'poco(' in line or
                'start_app' in line):
                in_code = True
            
            if in_code:
                python_lines.append(line)
        
        if python_lines:
            return '\n'.join(python_lines)
        
        return None
    
    def _generate_testcase_name(self, description: str) -> str:
        """生成测试用例文件名"""
        # 生成基于时间戳的唯一名称
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 从描述中提取关键词
        keywords = []
        for word in description.lower().split():
            if word in ['搜索', 'search', '播放', 'play', '登录', 'login', '视频', 'video', 'vod']:
                keywords.append(word)
        
        if keywords:
            name = f"generated_{'_'.join(keywords[:2])}_{timestamp}"
        else:
            name = f"generated_testcase_{timestamp}"
        
        return name
    
    async def generate_interactive_testcase(self, description: str) -> str:
        """交互式生成测试用例 - 获取当前屏幕元素辅助生成"""
        try:
            logger.info("开始交互式测试用例生成...")
            
            # 初始化UI调度器
            if not await self.ui_scheduler.initialize():
                raise Exception("UI调度器初始化失败")
            
            # 获取当前屏幕元素
            logger.info("获取当前屏幕元素...")
            screen_elements = await self.ui_scheduler.get_screen_elements()
            
            # 过滤出可操作的元素
            clickable_elements = [
                elem for elem in screen_elements.get('elements', [])
                if elem.get('clickable', False) and (elem.get('text', '').strip() or elem.get('resource_id', ''))
            ]
            
            logger.info(f"找到 {len(clickable_elements)} 个可操作元素")
            
            # 构建包含当前屏幕信息的提示
            enhanced_prompt = f"""
{description}

## 当前屏幕信息
设备分辨率: {screen_elements.get('screen_size', 'unknown')}
提取模式: {screen_elements.get('extraction_mode', 'unknown')} 
元素总数: {screen_elements.get('total_count', 0)}

## 可操作元素列表
"""
            
            for i, elem in enumerate(clickable_elements[:15], 1):  # 只显示前15个
                enhanced_prompt += f"""
{i}. resource_id: {elem.get('resource_id', 'N/A')}
   text: "{elem.get('text', '')}"
   class: {elem.get('class_name', 'N/A')}
   center: ({elem.get('center_x', 0):.3f}, {elem.get('center_y', 0):.3f})
"""
            
            enhanced_prompt += f"""
请基于以上当前屏幕的真实元素信息生成测试用例，确保：
1. 使用真实存在的resource_id和元素
2. 点击操作使用实际可点击的元素
3. 生成的代码能够在当前屏幕状态下正确执行

{self._build_generation_prompt(description, self.load_template_examples())}
"""
            
            # 生成测试用例
            generated_content = await self.llm_client.generate_completion(enhanced_prompt, temperature=0.2)
            
            # 后续处理与普通生成相同
            python_code = self._extract_python_code(generated_content)
            
            if not python_code:
                raise Exception("未能生成有效的Python代码")
            
            testcase_name = self._generate_testcase_name(f"interactive_{description}")
            
            # 保存测试用例
            testcase_file = self.python_dir / f"{testcase_name}.py"
            with open(testcase_file, 'w', encoding='utf-8') as f:
                f.write(python_code)
            
            # 同时保存屏幕元素快照
            snapshot_file = self.metadata_dir / f"{testcase_name}_screen_snapshot.json"
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(screen_elements, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 交互式测试用例生成成功: {testcase_file}")
            return testcase_name
            
        except Exception as e:
            logger.error(f"交互式测试用例生成失败: {e}")
            raise


# CLI接口
async def main():
    """主函数 - CLI接口"""
    if len(sys.argv) < 2:
        print("用法: python test_generator.py <测试描述>")
        print("示例: python test_generator.py '搜索并播放视频'")
        return
    
    description = ' '.join(sys.argv[1:])
    
    try:
        # 创建生成器
        generator = TestCaseGenerator()
        
        # 生成测试用例
        testcase_name = await generator.generate_from_description(description)
        print(f"✅ 成功生成测试用例: {testcase_name}")
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())