"""Tests for extended vector stores and tools."""

import pytest


class TestExtendedVectorStoresImport:
    """Test extended vector stores can be imported."""
    
    def test_import_redis(self):
        from rlm_toolkit.vectorstores.extended import RedisVectorStore
        assert RedisVectorStore is not None
    
    def test_import_elasticsearch(self):
        from rlm_toolkit.vectorstores.extended import ElasticsearchVectorStore
        assert ElasticsearchVectorStore is not None
    
    def test_import_opensearch(self):
        from rlm_toolkit.vectorstores.extended import OpenSearchVectorStore
        assert OpenSearchVectorStore is not None
    
    def test_import_supabase(self):
        from rlm_toolkit.vectorstores.extended import SupabaseVectorStore
        assert SupabaseVectorStore is not None
    
    def test_import_mongodb_atlas(self):
        from rlm_toolkit.vectorstores.extended import MongoDBAtlasVectorStore
        assert MongoDBAtlasVectorStore is not None
    
    def test_import_astradb(self):
        from rlm_toolkit.vectorstores.extended import AstraDBVectorStore
        assert AstraDBVectorStore is not None
    
    def test_import_singlestore(self):
        from rlm_toolkit.vectorstores.extended import SingleStoreVectorStore
        assert SingleStoreVectorStore is not None
    
    def test_import_typesense(self):
        from rlm_toolkit.vectorstores.extended import TypesenseVectorStore
        assert TypesenseVectorStore is not None


class TestExtendedToolsImport:
    """Test extended tools can be imported."""
    
    def test_import_weather(self):
        from rlm_toolkit.tools.extended import OpenWeatherMapTool
        assert OpenWeatherMapTool is not None
    
    def test_import_translate(self):
        from rlm_toolkit.tools.extended import GoogleTranslateTool
        assert GoogleTranslateTool is not None
    
    def test_import_deepl(self):
        from rlm_toolkit.tools.extended import DeepLTool
        assert DeepLTool is not None
    
    def test_import_dalle(self):
        from rlm_toolkit.tools.extended import DallETool
        assert DallETool is not None
    
    def test_import_stable_diffusion(self):
        from rlm_toolkit.tools.extended import StableDiffusionTool
        assert StableDiffusionTool is not None
    
    def test_import_whisper(self):
        from rlm_toolkit.tools.extended import WhisperTool
        assert WhisperTool is not None
    
    def test_import_tts(self):
        from rlm_toolkit.tools.extended import TextToSpeechTool
        assert TextToSpeechTool is not None
    
    def test_import_gmail(self):
        from rlm_toolkit.tools.extended import GmailTool
        assert GmailTool is not None
    
    def test_import_sendgrid(self):
        from rlm_toolkit.tools.extended import SendGridTool
        assert SendGridTool is not None
    
    def test_import_calendar(self):
        from rlm_toolkit.tools.extended import GoogleCalendarTool
        assert GoogleCalendarTool is not None
    
    def test_import_news(self):
        from rlm_toolkit.tools.extended import NewsAPITool
        assert NewsAPITool is not None
    
    def test_import_twitter(self):
        from rlm_toolkit.tools.extended import TwitterSearchTool
        assert TwitterSearchTool is not None
    
    def test_import_stock(self):
        from rlm_toolkit.tools.extended import YahooFinanceTool
        assert YahooFinanceTool is not None
    
    def test_import_crypto(self):
        from rlm_toolkit.tools.extended import CryptoTool
        assert CryptoTool is not None
    
    def test_import_datetime(self):
        from rlm_toolkit.tools.extended import DateTimeTool
        assert DateTimeTool is not None
    
    def test_import_uuid(self):
        from rlm_toolkit.tools.extended import UUIDTool
        assert UUIDTool is not None
    
    def test_import_hash(self):
        from rlm_toolkit.tools.extended import HashTool
        assert HashTool is not None
    
    def test_import_base64(self):
        from rlm_toolkit.tools.extended import Base64Tool
        assert Base64Tool is not None
    
    def test_import_json(self):
        from rlm_toolkit.tools.extended import JSONTool
        assert JSONTool is not None


class TestExtendedToolsFunction:
    """Test extended tools function correctly."""
    
    def test_uuid_tool(self):
        from rlm_toolkit.tools.extended import UUIDTool
        
        tool = UUIDTool()
        result = tool.run("")
        
        assert len(result) == 36  # UUID format
        assert "-" in result
    
    def test_hash_tool(self):
        from rlm_toolkit.tools.extended import HashTool
        
        tool = HashTool()
        result = tool.run("sha256|hello")
        
        assert len(result) == 64  # SHA256 hex length
    
    def test_base64_encode(self):
        from rlm_toolkit.tools.extended import Base64Tool
        
        tool = Base64Tool()
        result = tool.run("encode|hello")
        
        assert result == "aGVsbG8="
    
    def test_base64_decode(self):
        from rlm_toolkit.tools.extended import Base64Tool
        
        tool = Base64Tool()
        result = tool.run("decode|aGVsbG8=")
        
        assert result == "hello"
    
    def test_json_tool(self):
        from rlm_toolkit.tools.extended import JSONTool
        
        tool = JSONTool()
        result = tool.run('{"key": "value"}')
        
        assert "key" in result
        assert "value" in result
    
    def test_datetime_tool(self):
        from rlm_toolkit.tools.extended import DateTimeTool
        
        tool = DateTimeTool()
        result = tool.run("")
        
        assert "Current time" in result
