"""Tests for extended3 loaders, extended2 providers, and callbacks."""

import pytest


class TestExtenders3LoadersImport:
    """Test extended3 loaders can be imported."""
    
    # CRM
    def test_pipedrive(self):
        from rlm_toolkit.loaders.extended3 import PipedriveLoader
        assert PipedriveLoader is not None
    
    def test_zoho(self):
        from rlm_toolkit.loaders.extended3 import ZohoLoader
        assert ZohoLoader is not None
    
    def test_dynamics(self):
        from rlm_toolkit.loaders.extended3 import DynamicsCRMLoader
        assert DynamicsCRMLoader is not None
    
    # PM
    def test_clickup(self):
        from rlm_toolkit.loaders.extended3 import ClickUpLoader
        assert ClickUpLoader is not None
    
    def test_monday(self):
        from rlm_toolkit.loaders.extended3 import MondayLoader
        assert MondayLoader is not None
    
    def test_wrike(self):
        from rlm_toolkit.loaders.extended3 import WrikeLoader
        assert WrikeLoader is not None
    
    # Wiki
    def test_mediawiki(self):
        from rlm_toolkit.loaders.extended3 import MediaWikiLoader
        assert MediaWikiLoader is not None
    
    def test_gitbook(self):
        from rlm_toolkit.loaders.extended3 import GitBookLoader
        assert GitBookLoader is not None
    
    # E-commerce
    def test_shopify(self):
        from rlm_toolkit.loaders.extended3 import ShopifyLoader
        assert ShopifyLoader is not None
    
    def test_stripe(self):
        from rlm_toolkit.loaders.extended3 import StripeLoader
        assert StripeLoader is not None
    
    # Analytics
    def test_google_analytics(self):
        from rlm_toolkit.loaders.extended3 import GoogleAnalyticsLoader
        assert GoogleAnalyticsLoader is not None
    
    def test_mixpanel(self):
        from rlm_toolkit.loaders.extended3 import MixpanelLoader
        assert MixpanelLoader is not None
    
    def test_tableau(self):
        from rlm_toolkit.loaders.extended3 import TableauLoader
        assert TableauLoader is not None
    
    # HR
    def test_greenhouse(self):
        from rlm_toolkit.loaders.extended3 import GreenhouseLoader
        assert GreenhouseLoader is not None
    
    # File formats
    def test_epub(self):
        from rlm_toolkit.loaders.extended3 import EPUBLoader
        assert EPUBLoader is not None
    
    def test_yaml(self):
        from rlm_toolkit.loaders.extended3 import YamlLoader
        assert YamlLoader is not None


class TestExtended2ProvidersImport:
    """Test extended2 providers can be imported."""
    
    def test_yandexgpt(self):
        from rlm_toolkit.providers.extended2 import YandexGPTProvider
        assert YandexGPTProvider is not None
    
    def test_gigachat(self):
        from rlm_toolkit.providers.extended2 import SberGigaChatProvider
        assert SberGigaChatProvider is not None
    
    def test_sensetime(self):
        from rlm_toolkit.providers.extended2 import SenseTimeProvider
        assert SenseTimeProvider is not None
    
    def test_bytedance(self):
        from rlm_toolkit.providers.extended2 import ByteDanceProvider
        assert ByteDanceProvider is not None
    
    def test_hunyuan(self):
        from rlm_toolkit.providers.extended2 import TencentHunyuanProvider
        assert TencentHunyuanProvider is not None
    
    def test_deepinfra(self):
        from rlm_toolkit.providers.extended2 import DeepInfraProvider
        assert DeepInfraProvider is not None
    
    def test_llamacpp(self):
        from rlm_toolkit.providers.extended2 import LlamaCPPProvider
        assert LlamaCPPProvider is not None


class TestCallbacksImport:
    """Test callbacks can be imported."""
    
    def test_base_callback(self):
        from rlm_toolkit.callbacks import BaseCallback
        assert BaseCallback is not None
    
    def test_logging_callback(self):
        from rlm_toolkit.callbacks import LoggingCallback
        assert LoggingCallback is not None
    
    def test_file_callback(self):
        from rlm_toolkit.callbacks import FileCallback
        assert FileCallback is not None
    
    def test_langsmith(self):
        from rlm_toolkit.callbacks import LangSmithCallback
        assert LangSmithCallback is not None
    
    def test_langfuse(self):
        from rlm_toolkit.callbacks import LangfuseCallback
        assert LangfuseCallback is not None
    
    def test_wandb(self):
        from rlm_toolkit.callbacks import WeightsAndBiasesCallback
        assert WeightsAndBiasesCallback is not None
    
    def test_mlflow(self):
        from rlm_toolkit.callbacks import MLflowCallback
        assert MLflowCallback is not None
    
    def test_prometheus(self):
        from rlm_toolkit.callbacks import PrometheusCallback
        assert PrometheusCallback is not None
    
    def test_otel(self):
        from rlm_toolkit.callbacks import OpenTelemetryCallback
        assert OpenTelemetryCallback is not None
    
    def test_callback_manager(self):
        from rlm_toolkit.callbacks import CallbackManager
        assert CallbackManager is not None


class TestCallbacksFunctionality:
    """Test callbacks work correctly."""
    
    def test_logging_callback(self):
        from rlm_toolkit.callbacks import LoggingCallback
        
        callback = LoggingCallback()
        callback.on_llm_start("test prompt")
        callback.on_llm_end("test response")
    
    def test_callback_manager(self):
        from rlm_toolkit.callbacks import CallbackManager, LoggingCallback
        
        manager = CallbackManager([LoggingCallback()])
        manager.on_llm_start("test")
        manager.on_llm_end("response")
    
    def test_llm_event(self):
        from rlm_toolkit.callbacks import LLMEvent
        
        event = LLMEvent(
            event_type="llm_call",
            model="gpt-4",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
        )
        assert event.model == "gpt-4"
        assert event.input_tokens == 100
