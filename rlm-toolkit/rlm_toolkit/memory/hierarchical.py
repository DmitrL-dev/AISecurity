"""
Hierarchical Memory (H-MEM) for LLM Agents
==========================================

Multi-level memory storage with positional index encoding for efficient
layer-by-layer retrieval across long-term dialogue and reasoning tasks.

Based on arXiv H-MEM paper (July 2025).

Architecture:
    Level 0: Episode Layer     - Raw memories, recent interactions
    Level 1: Memory Trace Layer - Contextualized memories with metadata
    Level 2: Category Layer     - Grouped by semantic category
    Level 3: Domain Layer       - High-level domain knowledge

Each memory vector has positional index encoding pointing to related
sub-memories in the next layer, enabling efficient hierarchical retrieval.
"""

from __future__ import annotations

import time
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import IntEnum
import threading


class MemoryLevel(IntEnum):
    """Memory hierarchy levels (higher = more abstract)."""
    EPISODE = 0      # Raw interactions
    TRACE = 1        # Contextualized memories
    CATEGORY = 2     # Semantic categories
    DOMAIN = 3       # Domain knowledge


@dataclass
class MemoryEntry:
    """
    Single memory entry with hierarchical indexing.
    
    Attributes:
        id: Unique memory identifier
        content: The actual memory content (text)
        level: Hierarchy level (0-3)
        timestamp: Creation time
        parent_id: Link to parent memory in higher level
        child_ids: Links to child memories in lower level
        embedding: Optional vector embedding
        metadata: Additional key-value metadata
    """
    id: str
    content: str
    level: MemoryLevel
    timestamp: float = field(default_factory=time.time)
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0
    last_accessed: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "level": int(self.level),
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "metadata": self.metadata,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            level=MemoryLevel(data["level"]),
            timestamp=data.get("timestamp", time.time()),
            parent_id=data.get("parent_id"),
            child_ids=data.get("child_ids", []),
            metadata=data.get("metadata", {}),
            access_count=data.get("access_count", 0),
            last_accessed=data.get("last_accessed"),
        )


@dataclass
class HMEMConfig:
    """Configuration for H-MEM."""
    # Capacity per level
    max_episodes: int = 1000       # Level 0
    max_traces: int = 500          # Level 1
    max_categories: int = 100      # Level 2
    max_domains: int = 20          # Level 3
    
    # Consolidation thresholds
    episode_consolidation_threshold: int = 50   # Consolidate after N episodes
    trace_consolidation_threshold: int = 20     # Consolidate after N traces
    
    # Retrieval settings
    top_k_per_level: int = 5       # Top-K results per level
    similarity_threshold: float = 0.7
    
    # Persistence
    persistence_path: Optional[str] = None
    auto_persist: bool = True


class HierarchicalMemory:
    """
    Hierarchical Memory (H-MEM) for LLM Agents.
    
    Provides multi-level memory storage with efficient hierarchical retrieval.
    Memory is organized from specific (episodes) to abstract (domains).
    
    Example:
        >>> hmem = HierarchicalMemory()
        >>> hmem.add_episode("User asked about weather in Moscow")
        >>> hmem.add_episode("AI responded with forecast")
        >>> hmem.consolidate()  # Creates traces, categories, domains
        >>> results = hmem.retrieve("weather forecast")
    """
    
    def __init__(self, config: Optional[HMEMConfig] = None):
        """
        Initialize H-MEM.
        
        Args:
            config: Configuration options
        """
        self.config = config or HMEMConfig()
        
        # Memory storage by level
        self._memories: Dict[MemoryLevel, Dict[str, MemoryEntry]] = {
            level: {} for level in MemoryLevel
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._total_added = 0
        self._total_retrieved = 0
        self._consolidation_count = 0
        
        # Load persisted state if available
        if self.config.persistence_path:
            self._load_from_disk()
    
    def _generate_id(self, content: str, level: MemoryLevel) -> str:
        """Generate unique ID for memory entry."""
        hash_input = f"{level}:{content}:{time.time()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def add_episode(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """
        Add raw episode memory (Level 0).
        
        Args:
            content: Memory content
            metadata: Optional metadata
            embedding: Optional vector embedding
            
        Returns:
            Memory ID
        """
        with self._lock:
            entry_id = self._generate_id(content, MemoryLevel.EPISODE)
            
            entry = MemoryEntry(
                id=entry_id,
                content=content,
                level=MemoryLevel.EPISODE,
                metadata=metadata or {},
                embedding=embedding,
            )
            
            self._memories[MemoryLevel.EPISODE][entry_id] = entry
            self._total_added += 1
            
            # Evict oldest if over capacity
            self._evict_if_needed(MemoryLevel.EPISODE, self.config.max_episodes)
            
            # Auto-consolidate if threshold reached
            if len(self._memories[MemoryLevel.EPISODE]) >= self.config.episode_consolidation_threshold:
                self._consolidate_episodes()
            
            # Auto-persist
            if self.config.auto_persist and self.config.persistence_path:
                self._save_to_disk()
            
            return entry_id
    
    def add_trace(
        self,
        content: str,
        episode_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add memory trace (Level 1) - consolidation of episodes.
        
        Args:
            content: Summarized content
            episode_ids: IDs of source episodes
            metadata: Optional metadata
            
        Returns:
            Memory ID
        """
        with self._lock:
            entry_id = self._generate_id(content, MemoryLevel.TRACE)
            
            entry = MemoryEntry(
                id=entry_id,
                content=content,
                level=MemoryLevel.TRACE,
                child_ids=episode_ids,
                metadata=metadata or {},
            )
            
            # Link episodes to this trace
            for ep_id in episode_ids:
                if ep_id in self._memories[MemoryLevel.EPISODE]:
                    self._memories[MemoryLevel.EPISODE][ep_id].parent_id = entry_id
            
            self._memories[MemoryLevel.TRACE][entry_id] = entry
            self._evict_if_needed(MemoryLevel.TRACE, self.config.max_traces)
            
            return entry_id
    
    def add_category(
        self,
        content: str,
        trace_ids: List[str],
        category_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add category memory (Level 2) - semantic grouping of traces.
        
        Args:
            content: Category description
            trace_ids: IDs of related traces
            category_name: Human-readable category name
            metadata: Optional metadata
            
        Returns:
            Memory ID
        """
        with self._lock:
            entry_id = self._generate_id(content, MemoryLevel.CATEGORY)
            
            meta = metadata or {}
            meta["category_name"] = category_name
            
            entry = MemoryEntry(
                id=entry_id,
                content=content,
                level=MemoryLevel.CATEGORY,
                child_ids=trace_ids,
                metadata=meta,
            )
            
            # Link traces to this category
            for tr_id in trace_ids:
                if tr_id in self._memories[MemoryLevel.TRACE]:
                    self._memories[MemoryLevel.TRACE][tr_id].parent_id = entry_id
            
            self._memories[MemoryLevel.CATEGORY][entry_id] = entry
            self._evict_if_needed(MemoryLevel.CATEGORY, self.config.max_categories)
            
            return entry_id
    
    def add_domain(
        self,
        content: str,
        category_ids: List[str],
        domain_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add domain knowledge (Level 3) - highest abstraction.
        
        Args:
            content: Domain knowledge description
            category_ids: IDs of related categories
            domain_name: Human-readable domain name
            metadata: Optional metadata
            
        Returns:
            Memory ID
        """
        with self._lock:
            entry_id = self._generate_id(content, MemoryLevel.DOMAIN)
            
            meta = metadata or {}
            meta["domain_name"] = domain_name
            
            entry = MemoryEntry(
                id=entry_id,
                content=content,
                level=MemoryLevel.DOMAIN,
                child_ids=category_ids,
                metadata=meta,
            )
            
            self._memories[MemoryLevel.DOMAIN][entry_id] = entry
            self._evict_if_needed(MemoryLevel.DOMAIN, self.config.max_domains)
            
            return entry_id
    
    def retrieve(
        self,
        query: str,
        levels: Optional[List[MemoryLevel]] = None,
        top_k: Optional[int] = None,
        include_children: bool = True,
    ) -> List[MemoryEntry]:
        """
        Hierarchical retrieval across memory levels.
        
        Args:
            query: Search query
            levels: Levels to search (default: all)
            top_k: Maximum results per level
            include_children: Include child memories in results
            
        Returns:
            List of matching MemoryEntry objects
        """
        with self._lock:
            self._total_retrieved += 1
            
            if levels is None:
                levels = list(MemoryLevel)
            
            k = top_k or self.config.top_k_per_level
            results = []
            
            # Search from high (abstract) to low (specific)
            for level in sorted(levels, reverse=True):
                level_memories = list(self._memories[level].values())
                
                # Simple text matching (replace with embedding similarity for production)
                query_lower = query.lower()
                scored = []
                for mem in level_memories:
                    score = self._simple_match_score(query_lower, mem.content.lower())
                    if score > 0:
                        scored.append((score, mem))
                
                # Sort by score, take top-K
                scored.sort(key=lambda x: x[0], reverse=True)
                for score, mem in scored[:k]:
                    mem.access_count += 1
                    mem.last_accessed = time.time()
                    results.append(mem)
                    
                    # Include children if requested
                    if include_children:
                        results.extend(self._get_children(mem))
            
            return results
    
    def _simple_match_score(self, query: str, content: str) -> float:
        """Simple word overlap score (replace with embeddings for production)."""
        query_words = set(query.split())
        content_words = set(content.split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words & content_words)
        return overlap / len(query_words)
    
    def _get_children(self, memory: MemoryEntry, max_depth: int = 2) -> List[MemoryEntry]:
        """Recursively get child memories."""
        if max_depth <= 0 or not memory.child_ids:
            return []
        
        children = []
        child_level = MemoryLevel(memory.level - 1) if memory.level > 0 else None
        
        if child_level is not None:
            for child_id in memory.child_ids:
                if child_id in self._memories[child_level]:
                    child = self._memories[child_level][child_id]
                    children.append(child)
                    children.extend(self._get_children(child, max_depth - 1))
        
        return children
    
    def _evict_if_needed(self, level: MemoryLevel, max_count: int) -> None:
        """Evict oldest memories if over capacity."""
        level_memories = self._memories[level]
        
        while len(level_memories) > max_count:
            # Find least recently accessed
            oldest_id = min(
                level_memories.keys(),
                key=lambda k: level_memories[k].last_accessed or level_memories[k].timestamp
            )
            del level_memories[oldest_id]
    
    def _consolidate_episodes(self) -> None:
        """Consolidate episodes into traces."""
        episodes = list(self._memories[MemoryLevel.EPISODE].values())
        if len(episodes) < 5:  # Need minimum episodes
            return
        
        # Group recent episodes into a trace (simple implementation)
        recent = sorted(episodes, key=lambda e: e.timestamp, reverse=True)[:10]
        
        # Create summary (in production, use LLM for this)
        summary = f"Conversation trace with {len(recent)} episodes"
        episode_ids = [e.id for e in recent]
        
        self.add_trace(
            content=summary,
            episode_ids=episode_ids,
            metadata={"auto_consolidated": True},
        )
        
        self._consolidation_count += 1
    
    def consolidate(self, summarizer=None) -> int:
        """
        Trigger manual consolidation across all levels.
        
        Args:
            summarizer: Optional callable(texts: List[str]) -> str for LLM summarization
            
        Returns:
            Number of consolidations performed
        """
        with self._lock:
            count = 0
            
            # Consolidate episodes → traces
            if len(self._memories[MemoryLevel.EPISODE]) >= 5:
                count += self._consolidate_episodes_to_traces(summarizer)
            
            # Consolidate traces → categories
            if len(self._memories[MemoryLevel.TRACE]) >= self.config.trace_consolidation_threshold:
                count += self._consolidate_traces_to_categories(summarizer)
            
            # Consolidate categories → domains
            if len(self._memories[MemoryLevel.CATEGORY]) >= 5:
                count += self._consolidate_categories_to_domains(summarizer)
            
            self._consolidation_count += count
            return count
    
    def _consolidate_episodes_to_traces(self, summarizer=None) -> int:
        """Consolidate episodes into traces using LLM summarization."""
        episodes = list(self._memories[MemoryLevel.EPISODE].values())
        if len(episodes) < 5:
            return 0
        
        # Group recent episodes into a trace
        recent = sorted(episodes, key=lambda e: e.timestamp, reverse=True)[:10]
        episode_ids = [e.id for e in recent]
        episode_texts = [e.content for e in recent]
        
        # Use LLM summarizer if available, else simple concatenation
        if summarizer:
            summary = summarizer(episode_texts)
        else:
            summary = f"Conversation trace ({len(recent)} episodes): " + "; ".join(
                t[:50] for t in episode_texts[:3]
            ) + "..."
        
        self.add_trace(
            content=summary,
            episode_ids=episode_ids,
            metadata={"auto_consolidated": True, "source_count": len(recent)},
        )
        
        return 1
    
    def _consolidate_traces_to_categories(self, summarizer=None) -> int:
        """Consolidate traces into categories using semantic clustering."""
        traces = list(self._memories[MemoryLevel.TRACE].values())
        if len(traces) < 3:
            return 0
        
        # Simple keyword-based clustering (replace with embeddings for production)
        clusters = self._cluster_by_keywords(traces)
        count = 0
        
        for category_name, cluster_traces in clusters.items():
            if len(cluster_traces) < 2:
                continue
            
            trace_ids = [t.id for t in cluster_traces]
            trace_texts = [t.content for t in cluster_traces]
            
            # Use LLM summarizer if available
            if summarizer:
                content = summarizer(trace_texts)
            else:
                content = f"Category '{category_name}' with {len(cluster_traces)} related memories"
            
            self.add_category(
                content=content,
                trace_ids=trace_ids,
                category_name=category_name,
                metadata={"auto_consolidated": True, "source_count": len(cluster_traces)},
            )
            count += 1
        
        return count
    
    def _consolidate_categories_to_domains(self, summarizer=None) -> int:
        """Consolidate categories into high-level domain knowledge."""
        categories = list(self._memories[MemoryLevel.CATEGORY].values())
        if len(categories) < 2:
            return 0
        
        # Group all categories into a domain (simplified)
        category_ids = [c.id for c in categories[:10]]
        category_texts = [c.content for c in categories[:10]]
        
        # Extract domain name from category names
        domain_names = [c.metadata.get("category_name", "unknown") for c in categories[:10]]
        domain_name = f"Knowledge Domain: {', '.join(set(domain_names)[:3])}"
        
        if summarizer:
            content = summarizer(category_texts)
        else:
            content = f"Domain knowledge consolidating {len(categories)} categories"
        
        self.add_domain(
            content=content,
            category_ids=category_ids,
            domain_name=domain_name,
            metadata={"auto_consolidated": True, "source_count": len(categories)},
        )
        
        return 1
    
    def _cluster_by_keywords(self, memories: List[MemoryEntry]) -> Dict[str, List[MemoryEntry]]:
        """Simple keyword-based clustering for memories."""
        # Common topic keywords
        topic_keywords = {
            "weather": ["weather", "temperature", "rain", "sunny", "forecast", "climate"],
            "technology": ["code", "programming", "software", "computer", "ai", "llm"],
            "business": ["meeting", "project", "deadline", "report", "client"],
            "personal": ["feel", "think", "want", "like", "prefer"],
            "general": [],  # catch-all
        }
        
        clusters: Dict[str, List[MemoryEntry]] = {k: [] for k in topic_keywords}
        
        for mem in memories:
            content_lower = mem.content.lower()
            assigned = False
            
            for topic, keywords in topic_keywords.items():
                if topic == "general":
                    continue
                if any(kw in content_lower for kw in keywords):
                    clusters[topic].append(mem)
                    assigned = True
                    break
            
            if not assigned:
                clusters["general"].append(mem)
        
        # Filter out empty clusters
        return {k: v for k, v in clusters.items() if v}
    
    def consolidate_with_llm(self, llm_provider) -> int:
        """
        Convenience method for consolidation using RLM LLM provider.
        
        Args:
            llm_provider: LLMProvider instance (e.g., from rlm_toolkit.providers)
            
        Returns:
            Number of consolidations performed
        """
        def summarizer(texts: List[str]) -> str:
            prompt = f"""Summarize the following {len(texts)} memory entries into a concise, coherent summary:

{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(texts))}

Summary (1-2 sentences):"""
            response = llm_provider.generate(prompt)
            return response.content.strip()
        
        return self.consolidate(summarizer=summarizer)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with self._lock:
            return {
                "total_added": self._total_added,
                "total_retrieved": self._total_retrieved,
                "consolidation_count": self._consolidation_count,
                "level_counts": {
                    level.name: len(memories)
                    for level, memories in self._memories.items()
                },
            }
    
    def clear(self, levels: Optional[List[MemoryLevel]] = None) -> None:
        """Clear memories at specified levels (default: all)."""
        with self._lock:
            if levels is None:
                levels = list(MemoryLevel)
            
            for level in levels:
                self._memories[level].clear()
    
    def _save_to_disk(self) -> None:
        """Persist memory to disk."""
        if not self.config.persistence_path:
            return
        
        data = {
            level.name: {
                mid: mem.to_dict()
                for mid, mem in memories.items()
            }
            for level, memories in self._memories.items()
        }
        
        with open(self.config.persistence_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_from_disk(self) -> None:
        """Load memory from disk."""
        if not self.config.persistence_path:
            return
        
        try:
            with open(self.config.persistence_path) as f:
                data = json.load(f)
            
            for level_name, memories in data.items():
                level = MemoryLevel[level_name]
                for mid, mem_data in memories.items():
                    self._memories[level][mid] = MemoryEntry.from_dict(mem_data)
        except FileNotFoundError:
            pass  # No persisted state yet


# Convenience factory
def create_hierarchical_memory(
    persistence_path: Optional[str] = None,
    **config_kwargs
) -> HierarchicalMemory:
    """
    Create H-MEM with default configuration.
    
    Args:
        persistence_path: Optional path to persist memory
        **config_kwargs: Additional HMEMConfig options
        
    Returns:
        Configured HierarchicalMemory instance
    """
    config = HMEMConfig(
        persistence_path=persistence_path,
        **config_kwargs
    )
    return HierarchicalMemory(config)
