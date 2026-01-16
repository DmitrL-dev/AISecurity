"""
Extended Providers
==================

Additional LLM providers for maximum ecosystem coverage.
"""

from typing import Dict, Optional, Tuple
import os

from rlm_toolkit.providers.base import LLMProvider, LLMResponse
from rlm_toolkit.providers.compatible import OpenAICompatibleProvider


# =============================================================================
# NVIDIA NIM Provider
# =============================================================================

class NVIDIAProvider(OpenAICompatibleProvider):
    """NVIDIA NIM API provider."""
    
    BASE_URL = "https://integrate.api.nvidia.com/v1"
    API_KEY_ENV = "NVIDIA_API_KEY"
    PROVIDER_NAME = "nvidia"
    
    MODEL_PRICING = {
        "meta/llama-3.1-405b-instruct": (0.0, 0.0),  # Free tier
        "meta/llama-3.1-70b-instruct": (0.0, 0.0),
        "nvidia/nemotron-4-340b-instruct": (0.0, 0.0),
    }


# =============================================================================
# Alibaba Qwen Provider
# =============================================================================

class QwenProvider(OpenAICompatibleProvider):
    """Alibaba Qwen/DashScope provider."""
    
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    API_KEY_ENV = "DASHSCOPE_API_KEY"
    PROVIDER_NAME = "qwen"
    
    MODEL_PRICING = {
        "qwen-max": (0.28, 0.28),
        "qwen-plus": (0.14, 0.14),
        "qwen-turbo": (0.028, 0.028),
        "qwen2.5-72b-instruct": (0.28, 0.28),
    }
    
    MODEL_CONTEXT = {
        "qwen-max": 128_000,
        "qwen2.5-72b-instruct": 128_000,
    }


# =============================================================================
# Baidu Ernie Provider
# =============================================================================

class ErnieProvider(OpenAICompatibleProvider):
    """Baidu ERNIE provider."""
    
    BASE_URL = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop"
    API_KEY_ENV = "ERNIE_API_KEY"
    PROVIDER_NAME = "ernie"
    
    MODEL_PRICING = {
        "ernie-bot-4": (0.12, 0.12),
        "ernie-bot-turbo": (0.008, 0.008),
    }


# =============================================================================
# Moonshot AI Provider (Kimi)
# =============================================================================

class MoonshotProvider(OpenAICompatibleProvider):
    """Moonshot AI (Kimi) provider."""
    
    BASE_URL = "https://api.moonshot.cn/v1"
    API_KEY_ENV = "MOONSHOT_API_KEY"
    PROVIDER_NAME = "moonshot"
    
    MODEL_PRICING = {
        "moonshot-v1-128k": (0.84, 0.84),
        "moonshot-v1-32k": (0.34, 0.34),
        "moonshot-v1-8k": (0.17, 0.17),
    }
    
    MODEL_CONTEXT = {
        "moonshot-v1-128k": 128_000,
        "moonshot-v1-32k": 32_000,
        "moonshot-v1-8k": 8_000,
    }


# =============================================================================
# 01.AI Yi Provider
# =============================================================================

class YiProvider(OpenAICompatibleProvider):
    """01.AI Yi provider."""
    
    BASE_URL = "https://api.01.ai/v1"
    API_KEY_ENV = "YI_API_KEY"
    PROVIDER_NAME = "yi"
    
    MODEL_PRICING = {
        "yi-large": (3.0, 3.0),
        "yi-medium": (0.25, 0.25),
        "yi-spark": (0.10, 0.10),
    }


# =============================================================================
# Zhipu AI (GLM) Provider
# =============================================================================

class ZhipuProvider(OpenAICompatibleProvider):
    """Zhipu AI GLM provider."""
    
    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    API_KEY_ENV = "ZHIPU_API_KEY"
    PROVIDER_NAME = "zhipu"
    
    MODEL_PRICING = {
        "glm-4": (0.10, 0.10),
        "glm-4-flash": (0.001, 0.001),
        "glm-4v": (0.10, 0.10),
    }


# =============================================================================
# Minimax Provider
# =============================================================================

class MinimaxProvider(OpenAICompatibleProvider):
    """Minimax provider."""
    
    BASE_URL = "https://api.minimax.chat/v1"
    API_KEY_ENV = "MINIMAX_API_KEY"
    PROVIDER_NAME = "minimax"
    
    MODEL_PRICING = {
        "abab6.5-chat": (0.03, 0.03),
        "abab5.5-chat": (0.015, 0.015),
    }


# =============================================================================
# Baichuan Provider
# =============================================================================

class BaichuanProvider(OpenAICompatibleProvider):
    """Baichuan AI provider."""
    
    BASE_URL = "https://api.baichuan-ai.com/v1"
    API_KEY_ENV = "BAICHUAN_API_KEY"
    PROVIDER_NAME = "baichuan"
    
    MODEL_PRICING = {
        "Baichuan4": (0.10, 0.10),
        "Baichuan3-Turbo": (0.012, 0.012),
    }


# =============================================================================
# xAI Grok Provider
# =============================================================================

class XAIProvider(OpenAICompatibleProvider):
    """xAI Grok provider."""
    
    BASE_URL = "https://api.x.ai/v1"
    API_KEY_ENV = "XAI_API_KEY"
    PROVIDER_NAME = "xai"
    
    MODEL_PRICING = {
        "grok-2": (2.0, 10.0),
        "grok-2-mini": (0.20, 1.0),
        "grok-beta": (5.0, 15.0),
    }
    
    MODEL_CONTEXT = {
        "grok-2": 131_072,
        "grok-2-mini": 131_072,
    }


# =============================================================================
# Reka AI Provider
# =============================================================================

class RekaProvider(OpenAICompatibleProvider):
    """Reka AI provider."""
    
    BASE_URL = "https://api.reka.ai/v1"
    API_KEY_ENV = "REKA_API_KEY"
    PROVIDER_NAME = "reka"
    
    MODEL_PRICING = {
        "reka-core": (3.0, 15.0),
        "reka-flash": (0.40, 2.0),
        "reka-edge": (0.40, 1.0),
    }


# =============================================================================
# Writer AI Provider
# =============================================================================

class WriterProvider(OpenAICompatibleProvider):
    """Writer AI Palmyra provider."""
    
    BASE_URL = "https://api.writer.com/v1"
    API_KEY_ENV = "WRITER_API_KEY"
    PROVIDER_NAME = "writer"
    
    MODEL_PRICING = {
        "palmyra-x-004": (2.0, 6.0),
        "palmyra-x-003": (1.0, 3.0),
    }


# =============================================================================
# Voyage AI (Embeddings) Provider
# =============================================================================

class VoyageProvider(OpenAICompatibleProvider):
    """Voyage AI provider."""
    
    BASE_URL = "https://api.voyageai.com/v1"
    API_KEY_ENV = "VOYAGE_API_KEY"
    PROVIDER_NAME = "voyage"
    
    MODEL_PRICING = {
        "voyage-3": (0.06, 0.06),
        "voyage-3-lite": (0.02, 0.02),
    }


# =============================================================================
# Cloudflare Workers AI Provider
# =============================================================================

class CloudflareProvider(OpenAICompatibleProvider):
    """Cloudflare Workers AI provider."""
    
    BASE_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"
    API_KEY_ENV = "CLOUDFLARE_API_TOKEN"
    PROVIDER_NAME = "cloudflare"
    
    MODEL_PRICING = {
        "@cf/meta/llama-3.1-8b-instruct": (0.0, 0.0),  # Free tier
        "@cf/mistral/mistral-7b-instruct-v0.1": (0.0, 0.0),
    }


# =============================================================================
# Modal Provider
# =============================================================================

class ModalProvider(OpenAICompatibleProvider):
    """Modal serverless provider."""
    
    BASE_URL = "https://api.modal.com/v1"
    API_KEY_ENV = "MODAL_TOKEN"
    PROVIDER_NAME = "modal"
    
    MODEL_PRICING = {}  # Pay per compute


# =============================================================================
# RunPod Provider
# =============================================================================

class RunPodProvider(OpenAICompatibleProvider):
    """RunPod serverless GPU provider."""
    
    BASE_URL = "https://api.runpod.ai/v2"
    API_KEY_ENV = "RUNPOD_API_KEY"
    PROVIDER_NAME = "runpod"
    
    MODEL_PRICING = {}  # Pay per second


# =============================================================================
# AWS Bedrock Provider
# =============================================================================

class BedrockProvider(LLMProvider):
    """AWS Bedrock provider."""
    
    MODEL_PRICING = {
        "anthropic.claude-3-5-sonnet-20241022-v2:0": (3.0, 15.0),
        "anthropic.claude-3-opus-20240229-v1:0": (15.0, 75.0),
        "amazon.titan-text-express-v1": (0.20, 0.60),
        "meta.llama3-1-405b-instruct-v1:0": (2.65, 3.50),
    }
    
    def __init__(
        self,
        model: str,
        region: str = "us-east-1",
    ):
        self._model = model
        self._region = region
        self._client = None
        
        pricing = self.MODEL_PRICING.get(model, (3.0, 15.0))
        self.PRICE_PER_1M_INPUT = pricing[0]
        self.PRICE_PER_1M_OUTPUT = pricing[1]
    
    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "bedrock-runtime",
                    region_name=self._region,
                )
            except ImportError:
                raise ImportError("boto3 required. pip install boto3")
        return self._client
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        import json
        client = self._get_client()
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or 1024,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt
        
        response = client.invoke_model(
            modelId=self._model,
            body=json.dumps(body),
        )
        
        result = json.loads(response["body"].read())
        content = result.get("content", [{}])[0].get("text", "")
        
        return LLMResponse(
            content=content,
            model=self._model,
            tokens_in=result.get("usage", {}).get("input_tokens", 0),
            tokens_out=result.get("usage", {}).get("output_tokens", 0),
            raw=result,
        )
    
    @property
    def max_context(self) -> int:
        return 200_000
    
    @property
    def model_name(self) -> str:
        return self._model


# =============================================================================
# Google Vertex AI Provider
# =============================================================================

class VertexAIProvider(LLMProvider):
    """Google Vertex AI provider."""
    
    MODEL_PRICING = {
        "gemini-1.5-pro": (1.25, 5.0),
        "gemini-1.5-flash": (0.075, 0.30),
        "gemini-2.0-flash-exp": (0.0, 0.0),
    }
    
    def __init__(
        self,
        model: str = "gemini-1.5-pro",
        project: Optional[str] = None,
        location: str = "us-central1",
    ):
        self._model = model
        self._project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self._location = location
        self._client = None
        
        pricing = self.MODEL_PRICING.get(model, (1.25, 5.0))
        self.PRICE_PER_1M_INPUT = pricing[0]
        self.PRICE_PER_1M_OUTPUT = pricing[1]
    
    def _get_client(self):
        if self._client is None:
            try:
                import vertexai
                from vertexai.generative_models import GenerativeModel
                vertexai.init(project=self._project, location=self._location)
                self._client = GenerativeModel(self._model)
            except ImportError:
                raise ImportError("google-cloud-aiplatform required")
        return self._client
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        client = self._get_client()
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = client.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": max_tokens or 1024,
                "temperature": temperature,
            },
        )
        
        return LLMResponse(
            content=response.text,
            model=self._model,
            tokens_in=len(full_prompt) // 4,
            tokens_out=len(response.text) // 4,
            raw=response,
        )
    
    @property
    def max_context(self) -> int:
        return 2_000_000
    
    @property
    def model_name(self) -> str:
        return self._model


# =============================================================================
# OctoAI Provider
# =============================================================================

class OctoAIProvider(OpenAICompatibleProvider):
    """OctoAI provider."""
    
    BASE_URL = "https://text.octoai.run/v1"
    API_KEY_ENV = "OCTOAI_API_KEY"
    PROVIDER_NAME = "octoai"
    
    MODEL_PRICING = {
        "meta-llama-3.1-405b-instruct": (3.0, 9.0),
        "meta-llama-3.1-70b-instruct": (0.90, 0.90),
        "mixtral-8x22b-instruct": (1.20, 1.20),
    }


# =============================================================================
# Baseten Provider
# =============================================================================

class BasetenProvider(OpenAICompatibleProvider):
    """Baseten provider."""
    
    BASE_URL = "https://model-{model_id}.api.baseten.co/production/v1"
    API_KEY_ENV = "BASETEN_API_KEY"
    PROVIDER_NAME = "baseten"
    
    MODEL_PRICING = {}


# =============================================================================
# Monster API Provider
# =============================================================================

class MonsterAPIProvider(OpenAICompatibleProvider):
    """Monster API provider."""
    
    BASE_URL = "https://llm.monsterapi.ai/v1"
    API_KEY_ENV = "MONSTER_API_KEY"
    PROVIDER_NAME = "monsterapi"
    
    MODEL_PRICING = {
        "meta-llama/Meta-Llama-3-8B-Instruct": (0.20, 0.20),
        "mistralai/Mistral-7B-Instruct-v0.2": (0.20, 0.20),
    }


# =============================================================================
# Sagemaker Provider
# =============================================================================

class SagemakerProvider(LLMProvider):
    """AWS Sagemaker Endpoints provider."""
    
    def __init__(
        self,
        endpoint_name: str,
        region: str = "us-east-1",
    ):
        self._endpoint = endpoint_name
        self._region = region
        self._client = None
        self.PRICE_PER_1M_INPUT = 0.0
        self.PRICE_PER_1M_OUTPUT = 0.0
    
    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "sagemaker-runtime",
                    region_name=self._region,
                )
            except ImportError:
                raise ImportError("boto3 required")
        return self._client
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        import json
        client = self._get_client()
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens or 256,
                "temperature": temperature,
            },
        }
        
        response = client.invoke_endpoint(
            EndpointName=self._endpoint,
            ContentType="application/json",
            Body=json.dumps(payload),
        )
        
        result = json.loads(response["Body"].read().decode())
        content = result[0].get("generated_text", "") if result else ""
        
        return LLMResponse(
            content=content,
            model=self._endpoint,
            tokens_in=len(prompt) // 4,
            tokens_out=len(content) // 4,
            raw=result,
        )
    
    @property
    def max_context(self) -> int:
        return 8_192
    
    @property
    def model_name(self) -> str:
        return self._endpoint
