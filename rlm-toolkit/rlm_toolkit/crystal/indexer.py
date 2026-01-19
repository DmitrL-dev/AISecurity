"""
Crystal Indexer for fast search.

Provides indexing and search capabilities for crystals.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from .hierarchy import Primitive, FileCrystal, ModuleCrystal, ProjectCrystal

logger = logging.getLogger("rlm_crystal.indexer")

# Try to import embedding retriever
try:
    from ..retrieval.embeddings import EmbeddingRetriever

    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    EmbeddingRetriever = None


class CrystalIndexer:
    """
    Indexer for fast search across crystals.

    Creates inverted indexes for:
    - Primitive names
    - Primitive types
    - Keywords in values
    - Semantic embeddings (optional)
    """

    def __init__(self, use_embeddings: bool = True):
        """
        Initialize indexer.

        Args:
            use_embeddings: Enable semantic search with embeddings
        """
        self.name_index: Dict[str, List[Primitive]] = defaultdict(list)
        self.type_index: Dict[str, List[Primitive]] = defaultdict(list)
        self.keyword_index: Dict[str, List[Primitive]] = defaultdict(list)
        self.file_index: Dict[str, FileCrystal] = {}

        # Semantic search
        self.use_embeddings = use_embeddings and EMBEDDINGS_AVAILABLE
        self._embeddings: Optional[EmbeddingRetriever] = None
        self._primitive_list: List[Primitive] = []

        if self.use_embeddings:
            self._embeddings = EmbeddingRetriever()

    def index_file(self, crystal: FileCrystal):
        """Index a single file crystal."""
        self.file_index[crystal.path] = crystal

        for prim in crystal.primitives:
            # Index by name
            name_lower = prim.name.lower() if prim.name else ""
            self.name_index[name_lower].append(prim)

            # Index by type
            self.type_index[prim.ptype].append(prim)

            # Index by keywords in value
            for word in prim.value.lower().split():
                if len(word) > 2:  # Skip very short words
                    self.keyword_index[word].append(prim)

            # Add to embedding index
            if self.use_embeddings and self._embeddings:
                self._primitive_list.append(prim)
                self._embeddings.add(
                    f"{prim.ptype}: {prim.name} - {prim.value[:100]}",
                    metadata={"prim_idx": len(self._primitive_list) - 1},
                )

    def index_project(self, project: ProjectCrystal):
        """Index an entire project crystal."""
        for module in project.modules.values():
            for file_crystal in module.files.values():
                self.index_file(file_crystal)

        logger.info(
            f"Indexed {len(self.file_index)} files, "
            f"{len(self.name_index)} names, "
            f"{len(self.keyword_index)} keywords"
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        type_filter: Optional[str] = None,
        use_semantic: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search for primitives matching the query.

        Args:
            query: Search query
            limit: Maximum results
            type_filter: Optional type filter (CLASS, FUNCTION, etc.)
            use_semantic: Use semantic search if available

        Returns:
            List of matching primitives with scores
        """
        # Try semantic search first
        if use_semantic and self.use_embeddings and self._embeddings:
            return self._semantic_search(query, limit, type_filter)

        # Fall back to keyword search
        return self._keyword_search(query, limit, type_filter)

    def _semantic_search(
        self,
        query: str,
        limit: int,
        type_filter: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Semantic search using embeddings."""
        results = self._embeddings.search(query, top_k=limit * 2)

        output = []
        for r in results:
            if r.metadata and "prim_idx" in r.metadata:
                prim = self._primitive_list[r.metadata["prim_idx"]]

                # Apply type filter
                if type_filter and prim.ptype != type_filter:
                    continue

                output.append(
                    {
                        "primitive": prim,
                        "score": r.score * 3.0,  # Scale to match keyword scores
                        "file": prim.source_file,
                        "line": prim.source_line,
                        "semantic": True,
                    }
                )

                if len(output) >= limit:
                    break

        return output

    def _keyword_search(
        self,
        query: str,
        limit: int,
        type_filter: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Keyword-based search."""
        query_words = set(query.lower().split())
        scores: Dict[int, float] = defaultdict(float)
        primitives: Dict[int, Primitive] = {}

        for word in query_words:
            # Exact name match (highest score)
            for prim in self.name_index.get(word, []):
                pid = id(prim)
                scores[pid] += 3.0 * prim.confidence
                primitives[pid] = prim

            # Partial name match
            for name, prims in self.name_index.items():
                if word in name:
                    for prim in prims:
                        pid = id(prim)
                        scores[pid] += 1.5 * prim.confidence
                        primitives[pid] = prim

            # Keyword match
            for prim in self.keyword_index.get(word, []):
                pid = id(prim)
                scores[pid] += 1.0 * prim.confidence
                primitives[pid] = prim

        # Sort by score
        sorted_results = sorted(
            primitives.keys(), key=lambda pid: scores[pid], reverse=True
        )

        results = []
        for pid in sorted_results[:limit]:
            prim = primitives[pid]

            # Apply type filter
            if type_filter and prim.ptype != type_filter:
                continue

            results.append(
                {
                    "primitive": prim,
                    "score": scores[pid],
                    "file": prim.source_file,
                    "line": prim.source_line,
                }
            )

        return results

    def find_by_type(self, ptype: str, limit: int = 100) -> List[Primitive]:
        """Find all primitives of a given type."""
        return self.type_index.get(ptype, [])[:limit]

    def find_by_name(self, name: str) -> List[Primitive]:
        """Find primitives by exact name."""
        return self.name_index.get(name.lower(), [])

    def get_stats(self) -> Dict[str, Any]:
        """Get indexer statistics."""
        stats = {
            "files": len(self.file_index),
            "unique_names": len(self.name_index),
            "unique_keywords": len(self.keyword_index),
            "type_counts": {t: len(p) for t, p in self.type_index.items()},
            "embeddings_enabled": self.use_embeddings,
        }
        if self._embeddings:
            stats["embedding_stats"] = self._embeddings.get_stats()
        return stats

    def clear(self):
        """Clear all indexes."""
        self.name_index.clear()
        self.type_index.clear()
        self.keyword_index.clear()
        self.file_index.clear()
        self._primitive_list.clear()
        if self._embeddings:
            self._embeddings.clear()
