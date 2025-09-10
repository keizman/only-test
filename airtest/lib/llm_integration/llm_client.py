#!/usr/bin/env python3
"""
Only-Test LLM服务客户端

支持多种LLM服务提供商的统一接口
包括OpenAI、Claude、OpenAI兼容服务等
提供自动重试、错误处理、回退机制
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path
import sys

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from lib.config_manager import ConfigManager

# 设置日志
logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM响应数据类"""
    content: str
    model: str
    provider: str
    usage: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    response_time: float = 0.0


@dataclass
class LLMMessage:
    """LLM消息数据类"""
    role: str  # system, user, assistant
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class BaseLLMProvider(ABC):
    """LLM提供商基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
    
    @abstractmethod
    def chat_completion(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """聊天完成接口"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查服务是否可用"""
        pass


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI兼容服务提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 尝试导入openai库
        try:
            import openai
            self.openai = openai
            
            # 配置客户端
            self.client = openai.OpenAI(
                api_key=config.get('api_key'),
                base_url=config.get('api_url', 'https://api.openai.com/v1'),
                timeout=self.timeout
            )
            # Debug: 基本连接信息（不打印密钥）
            try:
                logger.info(f"LLM(OpenAICompatible) base_url={config.get('api_url')}, model={config.get('model')}")
            except Exception:
                pass
            
        except ImportError:
            logger.error("未安装openai库: pip install openai")
            self.client = None
    
    def chat_completion(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """OpenAI风格的聊天完成"""
        if not self.client:
            return LLMResponse(
                content="",
                model=self.config.get('model', 'unknown'),
                provider="openai_compatible",
                usage={},
                success=False,
                error="OpenAI客户端未初始化"
            )
        
        start_time = time.time()
        
        # 准备请求参数
        request_params = {
            "model": self.config.get('model', 'gpt-3.5-turbo'),
            "messages": [msg.to_dict() for msg in messages],
            "temperature": kwargs.get('temperature', self.config.get('temperature', 0.7)),
            "max_tokens": kwargs.get('max_tokens', self.config.get('max_tokens', 2000))
        }
        
        # 添加其他参数
        if 'top_p' in kwargs:
            request_params['top_p'] = kwargs['top_p']
        if 'frequency_penalty' in kwargs:
            request_params['frequency_penalty'] = kwargs['frequency_penalty']
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(**request_params)
                
                response_time = time.time() - start_time
                
                return LLMResponse(
                    content=response.choices[0].message.content,
                    model=response.model,
                    provider="openai_compatible",
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    },
                    success=True,
                    response_time=response_time
                )
                
            except Exception as e:
                logger.warning(f"LLM请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    return LLMResponse(
                        content="",
                        model=self.config.get('model', 'unknown'),
                        provider="openai_compatible",
                        usage={},
                        success=False,
                        error=str(e),
                        response_time=time.time() - start_time
                    )
    
    def is_available(self) -> bool:
        """检查服务可用性"""
        if not self.client:
            return False
        
        try:
            # 发送简单测试请求
            test_messages = [LLMMessage("user", "Hello")]
            response = self.chat_completion(test_messages, max_tokens=1)
            return response.success
        except:
            return False


class OpenAIProvider(OpenAICompatibleProvider):
    """官方OpenAI服务提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        # 设置官方API URL
        config['api_url'] = 'https://api.openai.com/v1'
        super().__init__(config)


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude服务提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(
                api_key=config.get('api_key'),
                timeout=self.timeout
            )
        except ImportError:
            logger.error("未安装anthropic库: pip install anthropic")
            self.client = None
    
    def chat_completion(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Claude风格的消息完成"""
        if not self.client:
            return LLMResponse(
                content="",
                model=self.config.get('model', 'claude-3'),
                provider="claude",
                usage={},
                success=False,
                error="Claude客户端未初始化"
            )
        
        start_time = time.time()
        
        # 转换消息格式 (Claude要求不同的格式)
        claude_messages = []
        system_message = ""
        
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                claude_messages.append(msg.to_dict())
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.config.get('model', 'claude-3-sonnet-20240229'),
                    max_tokens=kwargs.get('max_tokens', self.config.get('max_tokens', 2000)),
                    temperature=kwargs.get('temperature', self.config.get('temperature', 0.7)),
                    system=system_message,
                    messages=claude_messages
                )
                
                response_time = time.time() - start_time
                
                return LLMResponse(
                    content=response.content[0].text,
                    model=response.model,
                    provider="claude",
                    usage={
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                        "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                    },
                    success=True,
                    response_time=response_time
                )
                
            except Exception as e:
                logger.warning(f"Claude请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return LLMResponse(
                        content="",
                        model=self.config.get('model', 'claude-3'),
                        provider="claude",
                        usage={},
                        success=False,
                        error=str(e),
                        response_time=time.time() - start_time
                    )
    
    def is_available(self) -> bool:
        """检查Claude服务可用性"""
        if not self.client:
            return False
        
        try:
            test_messages = [LLMMessage("user", "Hi")]
            response = self.chat_completion(test_messages, max_tokens=1)
            return response.success
        except:
            return False


class LLMClient:
    """统一LLM客户端"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化LLM客户端
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or ConfigManager()
        self.llm_config = self.config_manager.get_llm_config()
        
        # 初始化提供商
        self.providers = {}
        self._init_providers()
        
        # 当前活跃提供商
        self.active_provider = None
        self._select_active_provider()
    
    def _init_providers(self):
        """初始化LLM提供商"""
        provider_type = self.llm_config.get('provider', 'openai_compatible')
        
        # 主提供商配置
        main_config = {
            'api_key': os.getenv('LLM_API_KEY'),
            'api_url': os.getenv('LLM_API_URL'),
            'model': os.getenv('LLM_MODEL'),
            'temperature': float(os.getenv('LLM_TEMPERATURE', '0.7')),
            'max_tokens': int(os.getenv('LLM_MAX_TOKENS', '2000')),
            'timeout': int(os.getenv('LLM_TIMEOUT', '30'))
        }
        
        # 根据类型初始化主提供商
        if provider_type == 'openai_compatible':
            self.providers['main'] = OpenAICompatibleProvider(main_config)
        elif provider_type == 'openai':
            self.providers['main'] = OpenAIProvider(main_config)
        elif provider_type == 'claude':
            self.providers['main'] = ClaudeProvider(main_config)
        else:
            logger.error(f"不支持的LLM提供商类型: {provider_type}")
        
        # 回退提供商配置
        fallback_provider = os.getenv('LLM_FALLBACK_PROVIDER')
        fallback_api_key = os.getenv('LLM_FALLBACK_API_KEY')
        
        if fallback_provider and fallback_api_key:
            fallback_config = {
                'api_key': fallback_api_key,
                'model': os.getenv('LLM_FALLBACK_MODEL', 'gpt-3.5-turbo'),
                'temperature': 0.7,
                'max_tokens': 2000,
                'timeout': 30
            }
            
            if fallback_provider == 'openai':
                self.providers['fallback'] = OpenAIProvider(fallback_config)
            elif fallback_provider == 'claude':
                self.providers['fallback'] = ClaudeProvider(fallback_config)
    
    def _select_active_provider(self):
        """选择活跃的提供商"""
        # 优先使用主提供商
        if 'main' in self.providers and self.providers['main'].is_available():
            self.active_provider = self.providers['main']
            logger.info("使用主LLM提供商")
            return
        
        # 回退到备用提供商
        if 'fallback' in self.providers and self.providers['fallback'].is_available():
            self.active_provider = self.providers['fallback']
            logger.warning("主LLM提供商不可用，切换到备用提供商")
            return
        
        logger.error("所有LLM提供商都不可用")
        self.active_provider = None
    
    def is_available(self) -> bool:
        """检查LLM服务是否可用"""
        if not self.llm_config.get('enabled', True):
            return False
        
        return self.active_provider is not None
    
    def chat_completion(self, messages: Union[List[LLMMessage], List[Dict[str, str]]], **kwargs) -> LLMResponse:
        """
        聊天完成接口
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: 响应结果
        """
        if not self.is_available():
            return LLMResponse(
                content="",
                model="unavailable",
                provider="unavailable",
                usage={},
                success=False,
                error="LLM服务不可用"
            )
        
        # 转换消息格式
        if messages and isinstance(messages[0], dict):
            messages = [LLMMessage(msg['role'], msg['content']) for msg in messages]
        
        # 尝试主提供商
        response = self.active_provider.chat_completion(messages, **kwargs)
        
        # 如果主提供商失败，尝试备用提供商
        if not response.success and 'fallback' in self.providers:
            logger.warning("主LLM提供商失败，尝试备用提供商")
            fallback_provider = self.providers['fallback']
            if fallback_provider.is_available():
                response = fallback_provider.chat_completion(messages, **kwargs)
        
        return response
    
    def generate_test_case(self, description: str, app_package: str, device_type: str = "android_phone") -> Optional[Dict[str, Any]]:
        """
        生成测试用例
        
        Args:
            description: 测试需求描述
            app_package: 应用包名
            device_type: 设备类型
            
        Returns:
            Dict: 生成的测试用例JSON
        """
        system_prompt = """你是一个专业的移动端UI自动化测试专家，负责将用户的自然语言描述转换为结构化的测试用例JSON。

请根据用户描述生成完整的测试用例，包含：
1. 条件分支逻辑 (如果...就...)
2. 智能元数据 (AI提示、业务逻辑说明)
3. 多重选择器策略
4. 断言验证

返回标准的Only-Test JSON格式。"""
        
        user_prompt = f"""
请为以下测试需求生成测试用例:

应用包名: {app_package}
设备类型: {device_type}
测试需求: {description}

请生成包含智能条件逻辑的完整JSON测试用例。
"""
        
        messages = [
            LLMMessage("system", system_prompt),
            LLMMessage("user", user_prompt)
        ]
        
        response = self.chat_completion(messages, temperature=0.3)  # 较低温度保证结构化输出
        
        if not response.success:
            logger.error(f"LLM测试用例生成失败: {response.error}")
            return None
        
        try:
            # 尝试解析JSON
            content = response.content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"LLM返回内容不是有效JSON: {e}")
            logger.debug(f"原始内容: {response.content}")
            return None
    
    def review_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        审查测试用例
        
        Args:
            test_case: 测试用例JSON
            
        Returns:
            Dict: 审查结果和建议
        """
        system_prompt = """你是一个测试用例审查专家，负责审查移动端UI自动化测试用例的质量。

请从以下方面评估测试用例：
1. 逻辑完整性
2. 选择器准确性  
3. 异常处理
4. 执行效率
5. 维护性

返回JSON格式的审查报告。"""
        
        user_prompt = f"""
请审查以下测试用例:

{json.dumps(test_case, ensure_ascii=False, indent=2)}

返回审查报告，包含评分、问题列表和改进建议。
"""
        
        messages = [
            LLMMessage("system", system_prompt),
            LLMMessage("user", user_prompt)
        ]
        
        response = self.chat_completion(messages, temperature=0.2)
        
        if not response.success:
            return {
                "success": False,
                "error": response.error,
                "score": 0,
                "issues": ["LLM审查服务不可用"],
                "suggestions": []
            }
        
        try:
            content = response.content.strip()
            if content.startswith('```json'):
                content = content[7:-3]
            
            review_result = json.loads(content)
            review_result["success"] = True
            return review_result
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "审查结果解析失败",
                "raw_response": response.content
            }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "providers_available": len(self.providers),
            "active_provider": self.active_provider.__class__.__name__ if self.active_provider else None,
            "llm_enabled": self.llm_config.get('enabled', False),
            "model_preferences": self.llm_config.get('model_preferences', {})
        }


def main():
    """测试LLM客户端"""
    print("🤖 Only-Test LLM客户端测试")
    print("=" * 50)
    
    # 初始化客户端
    try:
        llm_client = LLMClient()
        
        # 检查可用性
        if not llm_client.is_available():
            print("❌ LLM服务不可用")
            return
        
        print("✅ LLM服务可用")
        
        # 获取使用统计
        stats = llm_client.get_usage_stats()
        print(f"📊 使用统计: {stats}")
        
        # 测试简单聊天
        test_messages = [
            LLMMessage("user", "请简单介绍一下移动端UI自动化测试")
        ]
        
        print("\n🔄 测试聊天完成...")
        response = llm_client.chat_completion(test_messages, max_tokens=100)
        
        if response.success:
            print(f"✅ 响应成功")
            print(f"📝 内容: {response.content[:200]}...")
            print(f"⏱️  耗时: {response.response_time:.2f}秒")
            print(f"🔢 Token使用: {response.usage}")
        else:
            print(f"❌ 响应失败: {response.error}")
        
        # 测试用例生成
        print("\n🧪 测试用例生成...")
        test_case = llm_client.generate_test_case(
            "在抖音中搜索美食视频，如果搜索框有内容先清空",
            "com.mobile.brasiltvmobile"
        )
        
        if test_case:
            print("✅ 测试用例生成成功")
            print(f"📋 用例名称: {test_case.get('name', 'Unknown')}")
            print(f"🔄 执行步骤: {len(test_case.get('execution_path', []))}")
        else:
            print("❌ 测试用例生成失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
