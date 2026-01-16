"""Tests for extended vector stores and embeddings."""

import pytest


class TestExtendedVectorStores2Import:
    """Test extended vector stores 2 can be imported."""
    
    # Cloud
    def test_upstash(self):
        from rlm_toolkit.vectorstores.extended2 import UpstashVectorStore
        assert UpstashVectorStore is not None
    
    def test_tidb(self):
        from rlm_toolkit.vectorstores.extended2 import TiDBVectorStore
        assert TiDBVectorStore is not None
    
    def test_neon(self):
        from rlm_toolkit.vectorstores.extended2 import NeonVectorStore
        assert NeonVectorStore is not None
    
    def test_turso(self):
        from rlm_toolkit.vectorstores.extended2 import TursoVectorStore
        assert TursoVectorStore is not None
    
    # Enterprise
    def test_oracle(self):
        from rlm_toolkit.vectorstores.extended2 import OracleVectorStore
        assert OracleVectorStore is not None
    
    def test_snowflake(self):
        from rlm_toolkit.vectorstores.extended2 import SnowflakeCortexVectorStore
        assert SnowflakeCortexVectorStore is not None
    
    def test_databricks(self):
        from rlm_toolkit.vectorstores.extended2 import DatabricksVectorStore
        assert DatabricksVectorStore is not None
    
    # Specialized
    def test_vespa(self):
        from rlm_toolkit.vectorstores.extended2 import VespaVectorStore
        assert VespaVectorStore is not None
    
    def test_marqo(self):
        from rlm_toolkit.vectorstores.extended2 import MarqoVectorStore
        assert MarqoVectorStore is not None
    
    # Open source
    def test_hnswlib(self):
        from rlm_toolkit.vectorstores.extended2 import HNSWlibVectorStore
        assert HNSWlibVectorStore is not None
    
    def test_annoy(self):
        from rlm_toolkit.vectorstores.extended2 import AnnoyVectorStore
        assert AnnoyVectorStore is not None
    
    def test_scann(self):
        from rlm_toolkit.vectorstores.extended2 import ScaNNVectorStore
        assert ScaNNVectorStore is not None
    
    # Hybrid
    def test_solr(self):
        from rlm_toolkit.vectorstores.extended2 import SolrVectorStore
        assert SolrVectorStore is not None


class TestExtendedEmbeddingsImport:
    """Test extended embeddings can be imported."""
    
    # Cloud
    def test_jina(self):
        from rlm_toolkit.embeddings.extended import JinaEmbeddings
        assert JinaEmbeddings is not None
    
    def test_mixedbread(self):
        from rlm_toolkit.embeddings.extended import MixedbreadEmbeddings
        assert MixedbreadEmbeddings is not None
    
    def test_nomic(self):
        from rlm_toolkit.embeddings.extended import NomicEmbeddings
        assert NomicEmbeddings is not None
    
    def test_together(self):
        from rlm_toolkit.embeddings.extended import TogetherEmbeddings
        assert TogetherEmbeddings is not None
    
    def test_mistral(self):
        from rlm_toolkit.embeddings.extended import MistralEmbeddings
        assert MistralEmbeddings is not None
    
    # Enterprise
    def test_vertexai(self):
        from rlm_toolkit.embeddings.extended import VertexAIEmbeddings
        assert VertexAIEmbeddings is not None
    
    def test_watsonx(self):
        from rlm_toolkit.embeddings.extended import WatsonxEmbeddings
        assert WatsonxEmbeddings is not None
    
    # Local
    def test_bge(self):
        from rlm_toolkit.embeddings.extended import BGEEmbeddings
        assert BGEEmbeddings is not None
    
    def test_e5(self):
        from rlm_toolkit.embeddings.extended import E5Embeddings
        assert E5Embeddings is not None
    
    def test_gte(self):
        from rlm_toolkit.embeddings.extended import GTEEmbeddings
        assert GTEEmbeddings is not None
    
    def test_instructor(self):
        from rlm_toolkit.embeddings.extended import InstructorEmbeddings
        assert InstructorEmbeddings is not None
    
    # Multilingual
    def test_multilingual_e5(self):
        from rlm_toolkit.embeddings.extended import MultilingualE5Embeddings
        assert MultilingualE5Embeddings is not None
    
    def test_labse(self):
        from rlm_toolkit.embeddings.extended import LaBSEEmbeddings
        assert LaBSEEmbeddings is not None
    
    # Specialized
    def test_clip(self):
        from rlm_toolkit.embeddings.extended import CLIPEmbeddings
        assert CLIPEmbeddings is not None
    
    def test_colbert(self):
        from rlm_toolkit.embeddings.extended import ColBERTEmbeddings
        assert ColBERTEmbeddings is not None
    
    def test_splade(self):
        from rlm_toolkit.embeddings.extended import SPLADEEmbeddings
        assert SPLADEEmbeddings is not None


class TestExtendedEmbeddingsFunction:
    """Test extended embeddings work."""
    
    @pytest.mark.skip(reason="Requires JINA_API_KEY")
    def test_jina_embed(self):
        from rlm_toolkit.embeddings.extended import JinaEmbeddings
        
        emb = JinaEmbeddings()
        result = emb.embed_documents(["test"])
        
        assert len(result) == 1
        assert len(result[0]) == 768
    
    @pytest.mark.skip(reason="Downloads ~1.3GB model on first run")
    def test_bge_embed(self):
        from rlm_toolkit.embeddings.extended import BGEEmbeddings
        
        emb = BGEEmbeddings()
        result = emb.embed_query("test")
        
        assert len(result) == 1024
