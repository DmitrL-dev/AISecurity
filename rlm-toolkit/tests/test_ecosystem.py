"""Tests for loaders, vectorstores, embeddings, splitters."""

import pytest
from pathlib import Path
import tempfile
import json


class TestLoadersImport:
    """Test loaders can be imported."""
    
    def test_import_document(self):
        from rlm_toolkit.loaders import Document
        doc = Document("test content", {"source": "test"})
        assert doc.content == "test content"
    
    def test_import_text_loader(self):
        from rlm_toolkit.loaders import TextLoader
        assert TextLoader is not None
    
    def test_import_pdf_loader(self):
        from rlm_toolkit.loaders import PDFLoader
        assert PDFLoader is not None
    
    def test_import_csv_loader(self):
        from rlm_toolkit.loaders import CSVLoader
        assert CSVLoader is not None
    
    def test_import_json_loader(self):
        from rlm_toolkit.loaders import JSONLoader
        assert JSONLoader is not None
    
    def test_import_markdown_loader(self):
        from rlm_toolkit.loaders import MarkdownLoader
        assert MarkdownLoader is not None
    
    def test_import_html_loader(self):
        from rlm_toolkit.loaders import HTMLLoader
        assert HTMLLoader is not None
    
    def test_import_web_loader(self):
        from rlm_toolkit.loaders import WebPageLoader
        assert WebPageLoader is not None
    
    def test_import_s3_loader(self):
        from rlm_toolkit.loaders import S3Loader
        assert S3Loader is not None
    
    def test_import_github_loader(self):
        from rlm_toolkit.loaders import GitHubLoader
        assert GitHubLoader is not None
    
    def test_import_sql_loader(self):
        from rlm_toolkit.loaders import SQLLoader
        assert SQLLoader is not None
    
    def test_import_directory_loader(self):
        from rlm_toolkit.loaders import DirectoryLoader
        assert DirectoryLoader is not None


class TestLoadersFunction:
    """Test loaders function correctly."""
    
    def test_text_loader(self):
        from rlm_toolkit.loaders import TextLoader
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, World!")
            f.flush()
            
            loader = TextLoader(f.name)
            docs = loader.load()
            
            assert len(docs) == 1
            assert docs[0].content == "Hello, World!"
    
    def test_json_loader(self):
        from rlm_toolkit.loaders import JSONLoader
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([{"text": "item1"}, {"text": "item2"}], f)
            f.flush()
            
            loader = JSONLoader(f.name, content_key="text")
            docs = loader.load()
            
            assert len(docs) == 2
    
    def test_markdown_loader(self):
        from rlm_toolkit.loaders import MarkdownLoader
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Title\n\nContent here")
            f.flush()
            
            loader = MarkdownLoader(f.name)
            docs = loader.load()
            
            assert len(docs) == 1
            assert "Title" in docs[0].content


class TestVectorStoresImport:
    """Test vector stores can be imported."""
    
    def test_import_chroma(self):
        from rlm_toolkit.vectorstores import ChromaVectorStore
        assert ChromaVectorStore is not None
    
    def test_import_faiss(self):
        from rlm_toolkit.vectorstores import FAISSVectorStore
        assert FAISSVectorStore is not None
    
    def test_import_qdrant(self):
        from rlm_toolkit.vectorstores import QdrantVectorStore
        assert QdrantVectorStore is not None
    
    def test_import_pinecone(self):
        from rlm_toolkit.vectorstores import PineconeVectorStore
        assert PineconeVectorStore is not None
    
    def test_import_weaviate(self):
        from rlm_toolkit.vectorstores import WeaviateVectorStore
        assert WeaviateVectorStore is not None
    
    def test_import_milvus(self):
        from rlm_toolkit.vectorstores import MilvusVectorStore
        assert MilvusVectorStore is not None
    
    def test_import_pgvector(self):
        from rlm_toolkit.vectorstores import PGVectorStore
        assert PGVectorStore is not None
    
    def test_import_lancedb(self):
        from rlm_toolkit.vectorstores import LanceDBVectorStore
        assert LanceDBVectorStore is not None


class TestEmbeddingsImport:
    """Test embeddings can be imported."""
    
    def test_import_openai(self):
        from rlm_toolkit.embeddings import OpenAIEmbeddings
        assert OpenAIEmbeddings is not None
    
    def test_import_cohere(self):
        from rlm_toolkit.embeddings import CohereEmbeddings
        assert CohereEmbeddings is not None
    
    def test_import_voyage(self):
        from rlm_toolkit.embeddings import VoyageEmbeddings
        assert VoyageEmbeddings is not None
    
    def test_import_huggingface(self):
        from rlm_toolkit.embeddings import HuggingFaceEmbeddings
        assert HuggingFaceEmbeddings is not None
    
    def test_import_ollama(self):
        from rlm_toolkit.embeddings import OllamaEmbeddings
        assert OllamaEmbeddings is not None
    
    def test_import_google(self):
        from rlm_toolkit.embeddings import GoogleEmbeddings
        assert GoogleEmbeddings is not None
    
    def test_import_azure(self):
        from rlm_toolkit.embeddings import AzureOpenAIEmbeddings
        assert AzureOpenAIEmbeddings is not None
    
    def test_import_bedrock(self):
        from rlm_toolkit.embeddings import BedrockEmbeddings
        assert BedrockEmbeddings is not None
    
    def test_import_fastembed(self):
        from rlm_toolkit.embeddings import FastEmbedEmbeddings
        assert FastEmbedEmbeddings is not None


class TestSplittersImport:
    """Test splitters can be imported."""
    
    def test_import_character(self):
        from rlm_toolkit.splitters import CharacterTextSplitter
        assert CharacterTextSplitter is not None
    
    def test_import_recursive(self):
        from rlm_toolkit.splitters import RecursiveCharacterTextSplitter
        assert RecursiveCharacterTextSplitter is not None
    
    def test_import_token(self):
        from rlm_toolkit.splitters import TokenTextSplitter
        assert TokenTextSplitter is not None
    
    def test_import_markdown(self):
        from rlm_toolkit.splitters import MarkdownTextSplitter
        assert MarkdownTextSplitter is not None
    
    def test_import_code(self):
        from rlm_toolkit.splitters import CodeTextSplitter
        assert CodeTextSplitter is not None
    
    def test_import_html(self):
        from rlm_toolkit.splitters import HTMLTextSplitter
        assert HTMLTextSplitter is not None
    
    def test_import_latex(self):
        from rlm_toolkit.splitters import LatexTextSplitter
        assert LatexTextSplitter is not None
    
    def test_import_sentence(self):
        from rlm_toolkit.splitters import SentenceTextSplitter
        assert SentenceTextSplitter is not None


class TestSplittersFunction:
    """Test splitters function correctly."""
    
    def test_character_splitter(self):
        from rlm_toolkit.splitters import CharacterTextSplitter
        
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        splitter = CharacterTextSplitter(chunk_size=30, chunk_overlap=5)
        chunks = splitter.split_text(text)
        
        assert len(chunks) > 0
    
    def test_recursive_splitter(self):
        from rlm_toolkit.splitters import RecursiveCharacterTextSplitter
        
        text = "First line.\nSecond line.\nThird line with more content here."
        splitter = RecursiveCharacterTextSplitter(chunk_size=30, chunk_overlap=5)
        chunks = splitter.split_text(text)
        
        assert len(chunks) > 0
    
    def test_sentence_splitter(self):
        from rlm_toolkit.splitters import SentenceTextSplitter
        
        text = "First sentence. Second sentence. Third sentence."
        splitter = SentenceTextSplitter(chunk_size=50, chunk_overlap=10)
        chunks = splitter.split_text(text)
        
        assert len(chunks) > 0
    
    def test_code_splitter(self):
        from rlm_toolkit.splitters import CodeTextSplitter
        
        code = """def foo():
    pass

def bar():
    pass

class Baz:
    pass
"""
        splitter = CodeTextSplitter(language="python", chunk_size=50, chunk_overlap=10)
        chunks = splitter.split_text(code)
        
        assert len(chunks) > 0


class TestEcosystemCount:
    """Verify total ecosystem integration count."""
    
    def test_provider_count(self):
        from rlm_toolkit.providers import __all__ as provider_all
        providers = [n for n in provider_all if n.endswith("Provider")]
        assert len(providers) >= 40, f"Expected 40+ providers, got {len(providers)}"
    
    def test_has_loaders_module(self):
        import rlm_toolkit.loaders
        assert hasattr(rlm_toolkit.loaders, "TextLoader")
        assert hasattr(rlm_toolkit.loaders, "PDFLoader")
    
    def test_has_vectorstores_module(self):
        import rlm_toolkit.vectorstores
        assert hasattr(rlm_toolkit.vectorstores, "ChromaVectorStore")
        assert hasattr(rlm_toolkit.vectorstores, "FAISSVectorStore")
    
    def test_has_embeddings_module(self):
        import rlm_toolkit.embeddings
        assert hasattr(rlm_toolkit.embeddings, "OpenAIEmbeddings")
        assert hasattr(rlm_toolkit.embeddings, "HuggingFaceEmbeddings")
    
    def test_has_splitters_module(self):
        import rlm_toolkit.splitters
        assert hasattr(rlm_toolkit.splitters, "CharacterTextSplitter")
        assert hasattr(rlm_toolkit.splitters, "RecursiveCharacterTextSplitter")
