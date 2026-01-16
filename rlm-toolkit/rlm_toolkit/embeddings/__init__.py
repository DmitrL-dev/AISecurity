"""
Embeddings
==========

Embedding model integrations for text vectorization.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import os


class Embeddings(ABC):
    """Base class for embeddings."""
    
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        pass
    
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        pass


# =============================================================================
# OpenAI Embeddings
# =============================================================================

class OpenAIEmbeddings(Embeddings):
    """OpenAI embeddings with batch processing support."""
    
    # Model dimensions and max tokens
    MODEL_INFO = {
        "text-embedding-3-small": {"dimensions": 1536, "max_tokens": 8191},
        "text-embedding-3-large": {"dimensions": 3072, "max_tokens": 8191},
        "text-embedding-ada-002": {"dimensions": 1536, "max_tokens": 8191},
    }
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        batch_size: int = 100,
        dimensions: Optional[int] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.batch_size = batch_size
        self.dimensions = dimensions  # For text-embedding-3-* models
        self._client = None
        self._total_tokens = 0
    
    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai required. pip install openai")
        return self._client
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents with automatic batching for large lists."""
        client = self._get_client()
        
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            # Build request with optional dimensions
            kwargs = {"input": batch, "model": self.model}
            if self.dimensions and "text-embedding-3" in self.model:
                kwargs["dimensions"] = self.dimensions
            
            response = client.embeddings.create(**kwargs)
            
            # Track token usage
            if hasattr(response, "usage"):
                self._total_tokens += response.usage.total_tokens
            
            # Sort by index to ensure correct order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([item.embedding for item in sorted_data])
        
        return all_embeddings
    
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]
    
    @property
    def total_tokens_used(self) -> int:
        """Get total tokens used across all calls."""
        return self._total_tokens
    
    def reset_token_counter(self):
        """Reset the token counter."""
        self._total_tokens = 0


# =============================================================================
# Cohere Embeddings
# =============================================================================

class CohereEmbeddings(Embeddings):
    """Cohere embeddings."""
    
    def __init__(
        self,
        model: str = "embed-english-v3.0",
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import cohere
                self._client = cohere.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError("cohere required")
        return self._client
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        response = client.embed(texts=texts, model=self.model, input_type="search_document")
        return response.embeddings
    
    def embed_query(self, text: str) -> List[float]:
        client = self._get_client()
        response = client.embed(texts=[text], model=self.model, input_type="search_query")
        return response.embeddings[0]


# =============================================================================
# Voyage Embeddings
# =============================================================================

class VoyageEmbeddings(Embeddings):
    """Voyage AI embeddings."""
    
    def __init__(
        self,
        model: str = "voyage-3",
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY")
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import voyageai
                self._client = voyageai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError("voyageai required")
        return self._client
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        response = client.embed(texts, model=self.model, input_type="document")
        return response.embeddings
    
    def embed_query(self, text: str) -> List[float]:
        client = self._get_client()
        response = client.embed([text], model=self.model, input_type="query")
        return response.embeddings[0]


# =============================================================================
# HuggingFace Embeddings
# =============================================================================

class HuggingFaceEmbeddings(Embeddings):
    """HuggingFace sentence-transformers embeddings."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.device = device
        self._model = None
    
    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=self.device)
            except ImportError:
                raise ImportError("sentence-transformers required")
        return self._model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        model = self._get_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


# =============================================================================
# Ollama Embeddings
# =============================================================================

class OllamaEmbeddings(Embeddings):
    """Ollama local embeddings."""
    
    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        import requests
        
        embeddings = []
        for text in texts:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            response.raise_for_status()
            embeddings.append(response.json()["embedding"])
        
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


# =============================================================================
# Google Embeddings
# =============================================================================

class GoogleEmbeddings(Embeddings):
    """Google generative AI embeddings."""
    
    def __init__(
        self,
        model: str = "models/text-embedding-004",
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
            except ImportError:
                raise ImportError("google-generativeai required")
        return self._client
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        embeddings = []
        for text in texts:
            result = client.embed_content(model=self.model, content=text)
            embeddings.append(result["embedding"])
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


# =============================================================================
# Azure OpenAI Embeddings
# =============================================================================

class AzureOpenAIEmbeddings(Embeddings):
    """Azure OpenAI embeddings."""
    
    def __init__(
        self,
        deployment_name: str,
        azure_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: str = "2024-02-01",
    ):
        self.deployment_name = deployment_name
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = api_version
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                from openai import AzureOpenAI
                self._client = AzureOpenAI(
                    api_key=self.api_key,
                    azure_endpoint=self.azure_endpoint,
                    api_version=self.api_version,
                )
            except ImportError:
                raise ImportError("openai required")
        return self._client
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        response = client.embeddings.create(input=texts, model=self.deployment_name)
        return [item.embedding for item in response.data]
    
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


# =============================================================================
# Bedrock Embeddings
# =============================================================================

class BedrockEmbeddings(Embeddings):
    """AWS Bedrock embeddings."""
    
    def __init__(
        self,
        model: str = "amazon.titan-embed-text-v2:0",
        region: str = "us-east-1",
    ):
        self.model = model
        self.region = region
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("bedrock-runtime", region_name=self.region)
            except ImportError:
                raise ImportError("boto3 required")
        return self._client
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        import json
        
        client = self._get_client()
        embeddings = []
        
        for text in texts:
            response = client.invoke_model(
                modelId=self.model,
                body=json.dumps({"inputText": text}),
            )
            result = json.loads(response["body"].read())
            embeddings.append(result["embedding"])
        
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


# =============================================================================
# FastEmbed (Local, Fast)
# =============================================================================

class FastEmbedEmbeddings(Embeddings):
    """FastEmbed local embeddings (Qdrant)."""
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
    ):
        self.model_name = model_name
        self._model = None
    
    def _get_model(self):
        if self._model is None:
            try:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(model_name=self.model_name)
            except ImportError:
                raise ImportError("fastembed required")
        return self._model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        model = self._get_model()
        embeddings = list(model.embed(texts))
        return [e.tolist() for e in embeddings]
    
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]
