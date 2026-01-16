"""Tests for extended providers."""

import pytest

from rlm_toolkit.providers.extended import (
    NVIDIAProvider,
    QwenProvider,
    ErnieProvider,
    MoonshotProvider,
    YiProvider,
    ZhipuProvider,
    MinimaxProvider,
    BaichuanProvider,
    XAIProvider,
    RekaProvider,
    WriterProvider,
    VoyageProvider,
    CloudflareProvider,
    OctoAIProvider,
    MonsterAPIProvider,
    BedrockProvider,
    VertexAIProvider,
    SagemakerProvider,
    ModalProvider,
    RunPodProvider,
    BasetenProvider,
)


class TestInternationalProviders:
    """Tests for international (Chinese) providers."""
    
    def test_nvidia_config(self):
        assert NVIDIAProvider.BASE_URL == "https://integrate.api.nvidia.com/v1"
        assert NVIDIAProvider.PROVIDER_NAME == "nvidia"
    
    def test_qwen_config(self):
        assert QwenProvider.API_KEY_ENV == "DASHSCOPE_API_KEY"
        assert "qwen-max" in QwenProvider.MODEL_PRICING
    
    def test_ernie_config(self):
        assert ErnieProvider.PROVIDER_NAME == "ernie"
    
    def test_moonshot_context(self):
        assert MoonshotProvider.MODEL_CONTEXT.get("moonshot-v1-128k") == 128_000
    
    def test_yi_pricing(self):
        assert YiProvider.MODEL_PRICING.get("yi-large") == (3.0, 3.0)
    
    def test_zhipu_config(self):
        assert ZhipuProvider.PROVIDER_NAME == "zhipu"
        assert "glm-4" in ZhipuProvider.MODEL_PRICING
    
    def test_minimax_config(self):
        assert MinimaxProvider.PROVIDER_NAME == "minimax"
    
    def test_baichuan_config(self):
        assert BaichuanProvider.PROVIDER_NAME == "baichuan"


class TestWesternProviders:
    """Tests for western providers."""
    
    def test_xai_config(self):
        assert XAIProvider.BASE_URL == "https://api.x.ai/v1"
        assert "grok-2" in XAIProvider.MODEL_PRICING
    
    def test_reka_config(self):
        assert RekaProvider.PROVIDER_NAME == "reka"
    
    def test_writer_config(self):
        assert WriterProvider.PROVIDER_NAME == "writer"
    
    def test_voyage_config(self):
        assert VoyageProvider.API_KEY_ENV == "VOYAGE_API_KEY"
    
    def test_cloudflare_config(self):
        assert CloudflareProvider.PROVIDER_NAME == "cloudflare"
    
    def test_octoai_config(self):
        assert OctoAIProvider.BASE_URL == "https://text.octoai.run/v1"
    
    def test_monsterapi_config(self):
        assert MonsterAPIProvider.PROVIDER_NAME == "monsterapi"


class TestCloudProviders:
    """Tests for cloud providers."""
    
    def test_bedrock_initialization(self):
        provider = BedrockProvider("anthropic.claude-3-5-sonnet-20241022-v2:0")
        assert provider._model == "anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert provider.PRICE_PER_1M_INPUT == 3.0
    
    def test_vertexai_initialization(self):
        provider = VertexAIProvider("gemini-1.5-pro", project="test-project")
        assert provider._model == "gemini-1.5-pro"
        assert provider.max_context == 2_000_000
    
    def test_sagemaker_initialization(self):
        provider = SagemakerProvider("my-endpoint")
        assert provider._endpoint == "my-endpoint"
    
    def test_modal_config(self):
        assert ModalProvider.PROVIDER_NAME == "modal"
    
    def test_runpod_config(self):
        assert RunPodProvider.PROVIDER_NAME == "runpod"
    
    def test_baseten_config(self):
        assert BasetenProvider.PROVIDER_NAME == "baseten"


class TestExtendedProviderImports:
    """Test extended providers can be imported from main module."""
    
    def test_import_nvidia(self):
        from rlm_toolkit.providers import NVIDIAProvider
        assert NVIDIAProvider is not None
    
    def test_import_qwen(self):
        from rlm_toolkit.providers import QwenProvider
        assert QwenProvider is not None
    
    def test_import_xai(self):
        from rlm_toolkit.providers import XAIProvider
        assert XAIProvider is not None
    
    def test_import_bedrock(self):
        from rlm_toolkit.providers import BedrockProvider
        assert BedrockProvider is not None
    
    def test_import_vertexai(self):
        from rlm_toolkit.providers import VertexAIProvider
        assert VertexAIProvider is not None
    
    def test_import_moonshot(self):
        from rlm_toolkit.providers import MoonshotProvider
        assert MoonshotProvider is not None
    
    def test_import_zhipu(self):
        from rlm_toolkit.providers import ZhipuProvider
        assert ZhipuProvider is not None
    
    def test_import_reka(self):
        from rlm_toolkit.providers import RekaProvider
        assert RekaProvider is not None


class TestAllProvidersCount:
    """Test we have the expected number of providers."""
    
    def test_total_provider_count(self):
        from rlm_toolkit.providers import __all__
        # Filter to only provider names
        providers = [n for n in __all__ if n.endswith("Provider")]
        assert len(providers) >= 40, f"Expected 40+ providers, got {len(providers)}"
