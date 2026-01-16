"""
Extended Vector Stores
======================

Additional vector store integrations.
"""

from typing import Any, Dict, List, Optional, Tuple
import os

from rlm_toolkit.vectorstores import VectorStore


# =============================================================================
# Redis Vector Store
# =============================================================================

class RedisVectorStore(VectorStore):
    """Redis with vector search capability."""
    
    def __init__(
        self,
        index_name: str = "vectors",
        redis_url: str = "redis://localhost:6379",
        embedding_function: Optional[Any] = None,
    ):
        self.index_name = index_name
        self.redis_url = redis_url
        self._embedding_function = embedding_function
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import redis
                self._client = redis.from_url(self.redis_url)
            except ImportError:
                raise ImportError("redis required")
        return self._client
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import json
        import uuid
        
        client = self._get_client()
        embeddings = self._embedding_function.embed_documents(texts)
        
        ids = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            
            doc = {
                "text": text,
                "embedding": embedding,
                "metadata": json.dumps(metadatas[i] if metadatas and i < len(metadatas) else {}),
            }
            
            client.hset(f"{self.index_name}:{doc_id}", mapping=doc)
        
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        # Simplified - would need Redis vector search module
        return []


# =============================================================================
# Elasticsearch Vector Store
# =============================================================================

class ElasticsearchVectorStore(VectorStore):
    """Elasticsearch with vector search."""
    
    def __init__(
        self,
        index_name: str = "vectors",
        es_url: str = "http://localhost:9200",
        embedding_function: Optional[Any] = None,
    ):
        self.index_name = index_name
        self.es_url = es_url
        self._embedding_function = embedding_function
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                from elasticsearch import Elasticsearch
                self._client = Elasticsearch(self.es_url)
            except ImportError:
                raise ImportError("elasticsearch required")
        return self._client
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import uuid
        
        client = self._get_client()
        embeddings = self._embedding_function.embed_documents(texts)
        
        ids = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            
            doc = {
                "text": text,
                "embedding": embedding,
            }
            if metadatas and i < len(metadatas):
                doc.update(metadatas[i])
            
            client.index(index=self.index_name, id=doc_id, document=doc)
        
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        client = self._get_client()
        query_embedding = self._embedding_function.embed_query(query)
        
        response = client.search(
            index=self.index_name,
            knn={
                "field": "embedding",
                "query_vector": query_embedding,
                "k": k,
                "num_candidates": k * 10,
            },
        )
        
        results = []
        for hit in response["hits"]["hits"]:
            results.append((hit["_source"].get("text", ""), hit["_score"]))
        
        return results


# =============================================================================
# OpenSearch Vector Store
# =============================================================================

class OpenSearchVectorStore(VectorStore):
    """OpenSearch with vector search."""
    
    def __init__(
        self,
        index_name: str = "vectors",
        host: str = "localhost",
        port: int = 9200,
        embedding_function: Optional[Any] = None,
    ):
        self.index_name = index_name
        self.host = host
        self.port = port
        self._embedding_function = embedding_function
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                from opensearchpy import OpenSearch
                self._client = OpenSearch(
                    hosts=[{"host": self.host, "port": self.port}],
                )
            except ImportError:
                raise ImportError("opensearch-py required")
        return self._client
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import uuid
        
        client = self._get_client()
        embeddings = self._embedding_function.embed_documents(texts)
        
        ids = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            
            doc = {"text": text, "embedding": embedding}
            if metadatas and i < len(metadatas):
                doc.update(metadatas[i])
            
            client.index(index=self.index_name, id=doc_id, body=doc)
        
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        client = self._get_client()
        query_embedding = self._embedding_function.embed_query(query)
        
        response = client.search(
            index=self.index_name,
            body={
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": query_embedding,
                            "k": k,
                        }
                    }
                }
            },
        )
        
        results = []
        for hit in response["hits"]["hits"]:
            results.append((hit["_source"].get("text", ""), hit["_score"]))
        
        return results


# =============================================================================
# Supabase Vector Store
# =============================================================================

class SupabaseVectorStore(VectorStore):
    """Supabase pgvector integration."""
    
    def __init__(
        self,
        table_name: str = "documents",
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        embedding_function: Optional[Any] = None,
    ):
        self.table_name = table_name
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        self._embedding_function = embedding_function
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                from supabase import create_client
                self._client = create_client(self.supabase_url, self.supabase_key)
            except ImportError:
                raise ImportError("supabase required")
        return self._client
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import uuid
        
        client = self._get_client()
        embeddings = self._embedding_function.embed_documents(texts)
        
        ids = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            
            data = {
                "id": doc_id,
                "content": text,
                "embedding": embedding,
                "metadata": metadatas[i] if metadatas and i < len(metadatas) else {},
            }
            
            client.table(self.table_name).insert(data).execute()
        
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        client = self._get_client()
        query_embedding = self._embedding_function.embed_query(query)
        
        response = client.rpc(
            "match_documents",
            {"query_embedding": query_embedding, "match_count": k},
        ).execute()
        
        results = []
        for item in response.data:
            results.append((item.get("content", ""), item.get("similarity", 0)))
        
        return results


# =============================================================================
# MongoDB Atlas Vector Store
# =============================================================================

class MongoDBAtlasVectorStore(VectorStore):
    """MongoDB Atlas with vector search."""
    
    def __init__(
        self,
        connection_string: str,
        database: str,
        collection: str,
        index_name: str = "vector_index",
        embedding_function: Optional[Any] = None,
    ):
        self.connection_string = connection_string
        self.database = database
        self.collection_name = collection
        self.index_name = index_name
        self._embedding_function = embedding_function
        self._collection = None
    
    def _get_collection(self):
        if self._collection is None:
            try:
                from pymongo import MongoClient
                client = MongoClient(self.connection_string)
                db = client[self.database]
                self._collection = db[self.collection_name]
            except ImportError:
                raise ImportError("pymongo required")
        return self._collection
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import uuid
        
        collection = self._get_collection()
        embeddings = self._embedding_function.embed_documents(texts)
        
        ids = []
        docs = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            
            doc = {
                "_id": doc_id,
                "text": text,
                "embedding": embedding,
            }
            if metadatas and i < len(metadatas):
                doc["metadata"] = metadatas[i]
            docs.append(doc)
        
        collection.insert_many(docs)
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        collection = self._get_collection()
        query_embedding = self._embedding_function.embed_query(query)
        
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.index_name,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": k * 10,
                    "limit": k,
                }
            },
            {
                "$project": {
                    "text": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        
        results = []
        for doc in collection.aggregate(pipeline):
            results.append((doc.get("text", ""), doc.get("score", 0)))
        
        return results


# =============================================================================
# Astra DB Vector Store
# =============================================================================

class AstraDBVectorStore(VectorStore):
    """DataStax Astra DB vector store."""
    
    def __init__(
        self,
        collection_name: str,
        token: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        embedding_function: Optional[Any] = None,
    ):
        self.collection_name = collection_name
        self.token = token or os.getenv("ASTRA_DB_TOKEN")
        self.api_endpoint = api_endpoint or os.getenv("ASTRA_DB_API_ENDPOINT")
        self._embedding_function = embedding_function
        self._collection = None
    
    def _get_collection(self):
        if self._collection is None:
            try:
                from astrapy.db import AstraDB
                db = AstraDB(token=self.token, api_endpoint=self.api_endpoint)
                self._collection = db.collection(self.collection_name)
            except ImportError:
                raise ImportError("astrapy required")
        return self._collection
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import uuid
        
        collection = self._get_collection()
        embeddings = self._embedding_function.embed_documents(texts)
        
        ids = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            
            doc = {
                "_id": doc_id,
                "text": text,
                "$vector": embedding,
            }
            if metadatas and i < len(metadatas):
                doc.update(metadatas[i])
            
            collection.insert_one(doc)
        
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        collection = self._get_collection()
        query_embedding = self._embedding_function.embed_query(query)
        
        results = collection.vector_find(
            vector=query_embedding,
            limit=k,
        )
        
        return [(doc.get("text", ""), doc.get("$similarity", 0)) for doc in results]


# =============================================================================
# SingleStore Vector Store
# =============================================================================

class SingleStoreVectorStore(VectorStore):
    """SingleStore DB with vector search."""
    
    def __init__(
        self,
        host: str,
        database: str,
        table_name: str = "vectors",
        user: Optional[str] = None,
        password: Optional[str] = None,
        embedding_function: Optional[Any] = None,
    ):
        self.host = host
        self.database = database
        self.table_name = table_name
        self.user = user or os.getenv("SINGLESTORE_USER")
        self.password = password or os.getenv("SINGLESTORE_PASSWORD")
        self._embedding_function = embedding_function
        self._conn = None
    
    def _get_connection(self):
        if self._conn is None:
            try:
                import singlestoredb as s2
                self._conn = s2.connect(
                    host=self.host,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                )
            except ImportError:
                raise ImportError("singlestoredb required")
        return self._conn
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import json
        import uuid
        
        conn = self._get_connection()
        embeddings = self._embedding_function.embed_documents(texts)
        
        ids = []
        with conn.cursor() as cur:
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                doc_id = str(uuid.uuid4())
                ids.append(doc_id)
                
                cur.execute(
                    f"INSERT INTO {self.table_name} (id, text, embedding) VALUES (%s, %s, JSON_ARRAY_PACK(%s))",
                    (doc_id, text, json.dumps(embedding)),
                )
        
        conn.commit()
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        import json
        
        conn = self._get_connection()
        query_embedding = self._embedding_function.embed_query(query)
        
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT text, DOT_PRODUCT(embedding, JSON_ARRAY_PACK(%s)) as score
                FROM {self.table_name}
                ORDER BY score DESC
                LIMIT %s
                """,
                (json.dumps(query_embedding), k),
            )
            results = cur.fetchall()
        
        return [(text, score) for text, score in results]


# =============================================================================
# Typesense Vector Store
# =============================================================================

class TypesenseVectorStore(VectorStore):
    """Typesense with vector search."""
    
    def __init__(
        self,
        collection_name: str,
        host: str = "localhost",
        port: int = 8108,
        api_key: Optional[str] = None,
        embedding_function: Optional[Any] = None,
    ):
        self.collection_name = collection_name
        self.host = host
        self.port = port
        self.api_key = api_key or os.getenv("TYPESENSE_API_KEY")
        self._embedding_function = embedding_function
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import typesense
                self._client = typesense.Client({
                    "nodes": [{"host": self.host, "port": self.port, "protocol": "http"}],
                    "api_key": self.api_key,
                })
            except ImportError:
                raise ImportError("typesense required")
        return self._client
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import uuid
        
        client = self._get_client()
        embeddings = self._embedding_function.embed_documents(texts)
        
        ids = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            
            doc = {"id": doc_id, "text": text, "embedding": embedding}
            client.collections[self.collection_name].documents.create(doc)
        
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        client = self._get_client()
        query_embedding = self._embedding_function.embed_query(query)
        
        results = client.collections[self.collection_name].documents.search({
            "q": "*",
            "vector_query": f"embedding:([{','.join(map(str, query_embedding))}], k:{k})",
        })
        
        return [
            (hit["document"].get("text", ""), hit.get("vector_distance", 0))
            for hit in results.get("hits", [])
        ]
