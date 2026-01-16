"""
Vector Stores
=============

Vector database integrations for similarity search.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import os


class VectorStore(ABC):
    """Base class for vector stores."""
    
    @abstractmethod
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        """Add texts to the vector store."""
        pass
    
    @abstractmethod
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        """Search for similar texts."""
        pass
    
    def add_documents(self, documents: List[Any], **kwargs) -> List[str]:
        """Add documents to the vector store."""
        texts = [doc.content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        return self.add_texts(texts, metadatas, **kwargs)


# =============================================================================
# ChromaDB
# =============================================================================

class ChromaVectorStore(VectorStore):
    """ChromaDB vector store."""
    
    def __init__(
        self,
        collection_name: str = "default",
        persist_directory: Optional[str] = None,
        embedding_function: Optional[Any] = None,
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._client = None
        self._collection = None
        self._embedding_function = embedding_function
    
    def _get_collection(self):
        if self._collection is None:
            try:
                import chromadb
                
                if self.persist_directory:
                    self._client = chromadb.PersistentClient(path=self.persist_directory)
                else:
                    self._client = chromadb.Client()
                
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self._embedding_function,
                )
            except ImportError:
                raise ImportError("chromadb required. pip install chromadb")
        return self._collection
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        collection = self._get_collection()
        
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in texts]
        
        collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict] = None,
        **kwargs
    ) -> List[Tuple[str, float]]:
        collection = self._get_collection()
        results = collection.query(
            query_texts=[query],
            n_results=k,
            where=filter,
        )
        
        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        return list(zip(docs, distances))
    
    def delete(self, ids: Optional[List[str]] = None, filter: Optional[Dict] = None):
        """Delete documents by IDs or filter."""
        collection = self._get_collection()
        
        if ids:
            collection.delete(ids=ids)
        elif filter:
            collection.delete(where=filter)
    
    def get(self, ids: List[str]) -> List[str]:
        """Get documents by IDs."""
        collection = self._get_collection()
        results = collection.get(ids=ids)
        return results.get("documents", [])
    
    def count(self) -> int:
        """Get total document count."""
        collection = self._get_collection()
        return collection.count()


# =============================================================================
# FAISS
# =============================================================================

class FAISSVectorStore(VectorStore):
    """FAISS vector store."""
    
    def __init__(
        self,
        embedding_function: Any,
        index_path: Optional[str] = None,
    ):
        self._embedding_function = embedding_function
        self.index_path = index_path
        self._index = None
        self._texts: List[str] = []
        self._metadatas: List[Dict] = []
    
    def _get_index(self, dimension: int):
        if self._index is None:
            try:
                import faiss
                self._index = faiss.IndexFlatL2(dimension)
            except ImportError:
                raise ImportError("faiss-cpu required. pip install faiss-cpu")
        return self._index
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import numpy as np
        
        embeddings = self._embedding_function.embed_documents(texts)
        embeddings_np = np.array(embeddings).astype("float32")
        
        index = self._get_index(embeddings_np.shape[1])
        index.add(embeddings_np)
        
        self._texts.extend(texts)
        self._metadatas.extend(metadatas or [{} for _ in texts])
        
        return [str(i) for i in range(len(self._texts) - len(texts), len(self._texts))]
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        import numpy as np
        
        query_embedding = self._embedding_function.embed_query(query)
        query_np = np.array([query_embedding]).astype("float32")
        
        distances, indices = self._index.search(query_np, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self._texts):
                results.append((self._texts[idx], float(distances[0][i])))
        
        return results
    
    def save(self, path: str):
        import faiss
        import pickle
        
        faiss.write_index(self._index, f"{path}.index")
        with open(f"{path}.pkl", "wb") as f:
            pickle.dump({"texts": self._texts, "metadatas": self._metadatas}, f)
    
    def load(self, path: str):
        import faiss
        import pickle
        
        self._index = faiss.read_index(f"{path}.index")
        with open(f"{path}.pkl", "rb") as f:
            data = pickle.load(f)
            self._texts = data["texts"]
            self._metadatas = data["metadatas"]


# =============================================================================
# Qdrant
# =============================================================================

class QdrantVectorStore(VectorStore):
    """Qdrant vector store."""
    
    def __init__(
        self,
        collection_name: str,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
        embedding_function: Optional[Any] = None,
    ):
        self.collection_name = collection_name
        self.url = url
        self.api_key = api_key
        self._embedding_function = embedding_function
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(url=self.url, api_key=self.api_key)
            except ImportError:
                raise ImportError("qdrant-client required")
        return self._client
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        from qdrant_client.models import PointStruct
        import uuid
        
        client = self._get_client()
        embeddings = self._embedding_function.embed_documents(texts)
        
        points = []
        ids = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            point_id = str(uuid.uuid4())
            ids.append(point_id)
            
            payload = {"text": text}
            if metadatas and i < len(metadatas):
                payload.update(metadatas[i])
            
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            ))
        
        client.upsert(collection_name=self.collection_name, points=points)
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        client = self._get_client()
        query_embedding = self._embedding_function.embed_query(query)
        
        results = client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=k,
        )
        
        return [(r.payload.get("text", ""), r.score) for r in results]


# =============================================================================
# Pinecone
# =============================================================================

class PineconeVectorStore(VectorStore):
    """Pinecone vector store."""
    
    def __init__(
        self,
        index_name: str,
        api_key: Optional[str] = None,
        environment: str = "us-east-1",
        embedding_function: Optional[Any] = None,
    ):
        self.index_name = index_name
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.environment = environment
        self._embedding_function = embedding_function
        self._index = None
    
    def _get_index(self):
        if self._index is None:
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=self.api_key)
                self._index = pc.Index(self.index_name)
            except ImportError:
                raise ImportError("pinecone-client required")
        return self._index
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import uuid
        
        index = self._get_index()
        embeddings = self._embedding_function.embed_documents(texts)
        
        vectors = []
        ids = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            vec_id = str(uuid.uuid4())
            ids.append(vec_id)
            
            metadata = {"text": text}
            if metadatas and i < len(metadatas):
                metadata.update(metadatas[i])
            
            vectors.append({"id": vec_id, "values": embedding, "metadata": metadata})
        
        index.upsert(vectors=vectors)
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        index = self._get_index()
        query_embedding = self._embedding_function.embed_query(query)
        
        results = index.query(vector=query_embedding, top_k=k, include_metadata=True)
        
        return [(r.metadata.get("text", ""), r.score) for r in results.matches]


# =============================================================================
# Weaviate
# =============================================================================

class WeaviateVectorStore(VectorStore):
    """Weaviate vector store."""
    
    def __init__(
        self,
        class_name: str,
        url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        embedding_function: Optional[Any] = None,
    ):
        self.class_name = class_name
        self.url = url
        self.api_key = api_key
        self._embedding_function = embedding_function
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import weaviate
                self._client = weaviate.Client(
                    url=self.url,
                    auth_client_secret=weaviate.AuthApiKey(api_key=self.api_key) if self.api_key else None,
                )
            except ImportError:
                raise ImportError("weaviate-client required")
        return self._client
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import uuid
        
        client = self._get_client()
        embeddings = self._embedding_function.embed_documents(texts) if self._embedding_function else [None] * len(texts)
        
        ids = []
        with client.batch as batch:
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                obj_id = str(uuid.uuid4())
                ids.append(obj_id)
                
                properties = {"text": text}
                if metadatas and i < len(metadatas):
                    properties.update(metadatas[i])
                
                batch.add_data_object(
                    properties,
                    self.class_name,
                    uuid=obj_id,
                    vector=embedding,
                )
        
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        client = self._get_client()
        query_embedding = self._embedding_function.embed_query(query)
        
        result = (
            client.query
            .get(self.class_name, ["text"])
            .with_near_vector({"vector": query_embedding})
            .with_limit(k)
            .with_additional(["distance"])
            .do()
        )
        
        items = result.get("data", {}).get("Get", {}).get(self.class_name, [])
        return [(item.get("text", ""), item.get("_additional", {}).get("distance", 0)) for item in items]


# =============================================================================
# Milvus
# =============================================================================

class MilvusVectorStore(VectorStore):
    """Milvus vector store."""
    
    def __init__(
        self,
        collection_name: str,
        host: str = "localhost",
        port: int = 19530,
        embedding_function: Optional[Any] = None,
    ):
        self.collection_name = collection_name
        self.host = host
        self.port = port
        self._embedding_function = embedding_function
        self._collection = None
    
    def _get_collection(self, dimension: int = 1536):
        if self._collection is None:
            try:
                from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
                
                connections.connect(host=self.host, port=self.port)
                
                # Check if collection exists
                from pymilvus import utility
                if utility.has_collection(self.collection_name):
                    self._collection = Collection(self.collection_name)
                else:
                    # Create collection
                    fields = [
                        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                    ]
                    schema = CollectionSchema(fields)
                    self._collection = Collection(self.collection_name, schema)
            except ImportError:
                raise ImportError("pymilvus required")
        return self._collection
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        embeddings = self._embedding_function.embed_documents(texts)
        collection = self._get_collection(len(embeddings[0]))
        
        data = [texts, embeddings]
        mr = collection.insert(data)
        
        return [str(i) for i in mr.primary_keys]
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        query_embedding = self._embedding_function.embed_query(query)
        collection = self._get_collection()
        collection.load()
        
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "L2", "params": {"nprobe": 10}},
            limit=k,
            output_fields=["text"],
        )
        
        return [(hit.entity.get("text", ""), hit.distance) for hit in results[0]]


# =============================================================================
# pgvector
# =============================================================================

class PGVectorStore(VectorStore):
    """PostgreSQL with pgvector extension."""
    
    def __init__(
        self,
        connection_string: str,
        table_name: str = "vectors",
        embedding_function: Optional[Any] = None,
    ):
        self.connection_string = connection_string
        self.table_name = table_name
        self._embedding_function = embedding_function
        self._conn = None
    
    def _get_connection(self):
        if self._conn is None:
            try:
                import psycopg2
                self._conn = psycopg2.connect(self.connection_string)
            except ImportError:
                raise ImportError("psycopg2 required")
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
                vec_id = str(uuid.uuid4())
                ids.append(vec_id)
                
                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                
                cur.execute(
                    f"INSERT INTO {self.table_name} (id, text, embedding, metadata) VALUES (%s, %s, %s, %s)",
                    (vec_id, text, embedding, json.dumps(metadata)),
                )
        
        conn.commit()
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        conn = self._get_connection()
        query_embedding = self._embedding_function.embed_query(query)
        
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT text, embedding <-> %s::vector AS distance FROM {self.table_name} ORDER BY distance LIMIT %s",
                (query_embedding, k),
            )
            results = cur.fetchall()
        
        return [(text, distance) for text, distance in results]


# =============================================================================
# LanceDB
# =============================================================================

class LanceDBVectorStore(VectorStore):
    """LanceDB vector store."""
    
    def __init__(
        self,
        uri: str = "./lancedb",
        table_name: str = "vectors",
        embedding_function: Optional[Any] = None,
    ):
        self.uri = uri
        self.table_name = table_name
        self._embedding_function = embedding_function
        self._db = None
        self._table = None
    
    def _get_table(self):
        if self._table is None:
            try:
                import lancedb
                self._db = lancedb.connect(self.uri)
                
                if self.table_name in self._db.table_names():
                    self._table = self._db.open_table(self.table_name)
            except ImportError:
                raise ImportError("lancedb required")
        return self._table
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        import lancedb
        import uuid
        
        if self._db is None:
            self._db = lancedb.connect(self.uri)
        
        embeddings = self._embedding_function.embed_documents(texts)
        
        data = []
        ids = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            vec_id = str(uuid.uuid4())
            ids.append(vec_id)
            
            record = {"id": vec_id, "text": text, "vector": embedding}
            if metadatas and i < len(metadatas):
                record.update(metadatas[i])
            data.append(record)
        
        if self._table is None:
            self._table = self._db.create_table(self.table_name, data)
        else:
            self._table.add(data)
        
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs
    ) -> List[Tuple[str, float]]:
        table = self._get_table()
        if table is None:
            return []
        
        query_embedding = self._embedding_function.embed_query(query)
        results = table.search(query_embedding).limit(k).to_list()
        
        return [(r.get("text", ""), r.get("_distance", 0)) for r in results]
