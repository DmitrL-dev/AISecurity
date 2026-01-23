"""
Hierarchical Memory Store for Memory Bridge v2.0

Provides L0-L3 memory hierarchy for enterprise-scale context persistence:
- L0: Project Meta (always loaded, 10-20 facts)
- L1: Domain/Service Clusters (loaded by task context)
- L2: Module Context (loaded on-demand)
- L3: Code-Level Integration (C³ Crystal)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import sqlite3
import uuid
import logging

logger = logging.getLogger(__name__)


class MemoryLevel(Enum):
    """Hierarchy levels for memory organization."""

    L0_PROJECT = 0  # Always loaded (10-20 facts)
    L1_DOMAIN = 1  # Loaded by task context (per service/domain)
    L2_MODULE = 2  # Loaded on-demand (specific modules)
    L3_CODE = 3  # C³ Crystal integration (functions/classes)


class TTLAction(Enum):
    """Actions to take when TTL expires."""

    MARK_STALE = "mark_stale"  # Mark as stale, keep visible with warning
    ARCHIVE = "archive"  # Move to archive, not visible by default
    DELETE = "delete"  # Permanently delete


@dataclass
class TTLConfig:
    """TTL configuration for a fact."""

    ttl_seconds: int
    refresh_trigger: Optional[str] = None  # Glob pattern: "src/auth/**/*.py"
    on_expire: TTLAction = TTLAction.MARK_STALE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ttl_seconds": self.ttl_seconds,
            "refresh_trigger": self.refresh_trigger,
            "on_expire": self.on_expire.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TTLConfig":
        return cls(
            ttl_seconds=data["ttl_seconds"],
            refresh_trigger=data.get("refresh_trigger"),
            on_expire=TTLAction(data.get("on_expire", "mark_stale")),
        )


@dataclass
class HierarchicalFact:
    """A fact with hierarchical organization and temporal metadata."""

    id: str
    content: str
    level: MemoryLevel
    domain: Optional[str] = None  # L1: "auth-service", "payment-service"
    module: Optional[str] = None  # L2: "fraud-detection", "api-contracts"
    code_ref: Optional[str] = None  # L3: "file:///path/to/file.py#L10-50"
    parent_id: Optional[str] = None  # Hierarchical link
    children_ids: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None  # For semantic search
    ttl_config: Optional[TTLConfig] = None
    created_at: datetime = field(default_factory=datetime.now)  # T (system time)
    valid_from: datetime = field(default_factory=datetime.now)  # T' (business time)
    valid_until: Optional[datetime] = None
    is_stale: bool = False
    is_archived: bool = False
    confidence: float = 1.0
    source: str = "manual"  # manual, git_diff, ast_analysis, template

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "level": self.level.value,
            "domain": self.domain,
            "module": self.module,
            "code_ref": self.code_ref,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "embedding": self.embedding,
            "ttl_config": self.ttl_config.to_dict() if self.ttl_config else None,
            "created_at": self.created_at.isoformat(),
            "valid_from": self.valid_from.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "is_stale": self.is_stale,
            "is_archived": self.is_archived,
            "confidence": self.confidence,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HierarchicalFact":
        return cls(
            id=data["id"],
            content=data["content"],
            level=MemoryLevel(data["level"]),
            domain=data.get("domain"),
            module=data.get("module"),
            code_ref=data.get("code_ref"),
            parent_id=data.get("parent_id"),
            children_ids=data.get("children_ids", []),
            embedding=data.get("embedding"),
            ttl_config=(
                TTLConfig.from_dict(data["ttl_config"])
                if data.get("ttl_config")
                else None
            ),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now()
            ),
            valid_from=(
                datetime.fromisoformat(data["valid_from"])
                if data.get("valid_from")
                else datetime.now()
            ),
            valid_until=(
                datetime.fromisoformat(data["valid_until"])
                if data.get("valid_until")
                else None
            ),
            is_stale=data.get("is_stale", False),
            is_archived=data.get("is_archived", False),
            confidence=data.get("confidence", 1.0),
            source=data.get("source", "manual"),
        )

    def token_estimate(self) -> int:
        """Estimate token count for this fact."""
        # Rough estimate: ~4 chars per token
        base_tokens = len(self.content) // 4
        metadata_tokens = 20  # level, domain, module overhead
        return base_tokens + metadata_tokens

    def is_expired(self) -> bool:
        """Check if TTL has expired."""
        if not self.ttl_config:
            return False
        expiry_time = self.created_at + timedelta(seconds=self.ttl_config.ttl_seconds)
        return datetime.now() > expiry_time


class HierarchicalMemoryStore:
    """
    Hierarchical memory storage with L0-L3 levels.

    Extends the base StateStorage with hierarchy, embeddings, and TTL support.
    """

    SCHEMA_VERSION = "2.0.0"

    def __init__(self, db_path: Optional[Path] = None):
        # Handle :memory: and string paths
        if db_path == ":memory:" or str(db_path) == ":memory:":
            self.db_path = ":memory:"
        elif db_path is None:
            self.db_path = Path.home() / ".rlm" / "memory_bridge_v2.db"
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                -- Main facts table with hierarchy
                CREATE TABLE IF NOT EXISTS hierarchical_facts (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 0,
                    domain TEXT,
                    module TEXT,
                    code_ref TEXT,
                    parent_id TEXT,
                    embedding BLOB,
                    ttl_config TEXT,
                    created_at TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_until TEXT,
                    is_stale INTEGER DEFAULT 0,
                    is_archived INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 1.0,
                    source TEXT DEFAULT 'manual',
                    session_id TEXT,
                    FOREIGN KEY (parent_id) REFERENCES hierarchical_facts(id)
                );
                
                -- Hierarchy relationships (for complex hierarchies)
                CREATE TABLE IF NOT EXISTS fact_hierarchy (
                    parent_id TEXT NOT NULL,
                    child_id TEXT NOT NULL,
                    relationship TEXT DEFAULT 'contains',
                    PRIMARY KEY (parent_id, child_id),
                    FOREIGN KEY (parent_id) REFERENCES hierarchical_facts(id),
                    FOREIGN KEY (child_id) REFERENCES hierarchical_facts(id)
                );
                
                -- Embeddings index for fast similarity search
                CREATE TABLE IF NOT EXISTS embeddings_index (
                    fact_id TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    model_name TEXT DEFAULT 'all-MiniLM-L6-v2',
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (fact_id) REFERENCES hierarchical_facts(id)
                );
                
                -- Domain centroids for fast routing
                CREATE TABLE IF NOT EXISTS domain_centroids (
                    domain TEXT PRIMARY KEY,
                    centroid BLOB NOT NULL,
                    fact_count INTEGER DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_facts_level ON hierarchical_facts(level);
                CREATE INDEX IF NOT EXISTS idx_facts_domain ON hierarchical_facts(domain);
                CREATE INDEX IF NOT EXISTS idx_facts_module ON hierarchical_facts(module);
                CREATE INDEX IF NOT EXISTS idx_facts_stale ON hierarchical_facts(is_stale);
                CREATE INDEX IF NOT EXISTS idx_facts_session ON hierarchical_facts(session_id);
                
                -- Schema version
                CREATE TABLE IF NOT EXISTS schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                INSERT OR REPLACE INTO schema_info (key, value) VALUES ('version', '2.0.0');
            """
            )

    def add_fact(
        self,
        content: str,
        level: MemoryLevel = MemoryLevel.L0_PROJECT,
        domain: Optional[str] = None,
        module: Optional[str] = None,
        code_ref: Optional[str] = None,
        parent_id: Optional[str] = None,
        ttl_config: Optional[TTLConfig] = None,
        embedding: Optional[List[float]] = None,
        confidence: float = 1.0,
        source: str = "manual",
        session_id: Optional[str] = None,
    ) -> str:
        """
        Add a fact with hierarchical organization.

        Args:
            content: The fact content
            level: Memory level (L0-L3)
            domain: Domain name for L1+ facts
            module: Module name for L2+ facts
            code_ref: Code reference for L3 facts
            parent_id: Parent fact ID for hierarchy
            ttl_config: TTL configuration
            embedding: Pre-computed embedding vector
            confidence: Confidence score (0.0-1.0)
            source: Source of the fact
            session_id: Session ID for scoping

        Returns:
            The fact ID
        """
        fact_id = str(uuid.uuid4())
        now = datetime.now()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO hierarchical_facts (
                    id, content, level, domain, module, code_ref, parent_id,
                    embedding, ttl_config, created_at, valid_from, confidence,
                    source, session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact_id,
                    content,
                    level.value,
                    domain,
                    module,
                    code_ref,
                    parent_id,
                    json.dumps(embedding) if embedding else None,
                    json.dumps(ttl_config.to_dict()) if ttl_config else None,
                    now.isoformat(),
                    now.isoformat(),
                    confidence,
                    source,
                    session_id,
                ),
            )

            # Add hierarchy relationship if parent exists
            if parent_id:
                conn.execute(
                    "INSERT OR IGNORE INTO fact_hierarchy (parent_id, child_id) VALUES (?, ?)",
                    (parent_id, fact_id),
                )

            # Store embedding in index if provided
            if embedding:
                conn.execute(
                    "INSERT OR REPLACE INTO embeddings_index (fact_id, embedding) VALUES (?, ?)",
                    (fact_id, json.dumps(embedding)),
                )

        logger.debug(f"Added fact {fact_id} at level {level.name}")
        return fact_id

    def get_fact(self, fact_id: str) -> Optional[HierarchicalFact]:
        """Get a fact by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM hierarchical_facts WHERE id = ?", (fact_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_fact(row)

    def get_facts_by_level(
        self,
        level: MemoryLevel,
        domain: Optional[str] = None,
        include_stale: bool = False,
        include_archived: bool = False,
        session_id: Optional[str] = None,
    ) -> List[HierarchicalFact]:
        """
        Get facts by level with optional filtering.

        Args:
            level: Memory level to query
            domain: Optional domain filter
            include_stale: Include stale facts
            include_archived: Include archived facts
            session_id: Optional session filter

        Returns:
            List of matching facts
        """
        query = "SELECT * FROM hierarchical_facts WHERE level = ?"
        params: List[Any] = [level.value]

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if not include_stale:
            query += " AND is_stale = 0"

        if not include_archived:
            query += " AND is_archived = 0"

        if session_id:
            query += " AND (session_id = ? OR session_id IS NULL)"
            params.append(session_id)

        query += " ORDER BY created_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_fact(row) for row in rows]

    def get_all_facts(
        self,
        include_stale: bool = False,
        include_archived: bool = False,
        session_id: Optional[str] = None,
    ) -> List[HierarchicalFact]:
        """Get all facts with optional filtering."""
        query = "SELECT * FROM hierarchical_facts WHERE 1=1"
        params: List[Any] = []

        if not include_stale:
            query += " AND is_stale = 0"

        if not include_archived:
            query += " AND is_archived = 0"

        if session_id:
            query += " AND (session_id = ? OR session_id IS NULL)"
            params.append(session_id)

        query += " ORDER BY level ASC, created_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_fact(row) for row in rows]

    def get_domain_facts(self, domain: str) -> List[HierarchicalFact]:
        """Get all facts for a specific domain."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM hierarchical_facts 
                WHERE domain = ? AND is_stale = 0 AND is_archived = 0
                ORDER BY level ASC, created_at DESC
                """,
                (domain,),
            ).fetchall()
            return [self._row_to_fact(row) for row in rows]

    def get_subtree(self, fact_id: str) -> List[HierarchicalFact]:
        """Get all facts in the subtree rooted at fact_id."""
        facts = []

        root = self.get_fact(fact_id)
        if root:
            facts.append(root)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Get all children recursively using CTE
            rows = conn.execute(
                """
                WITH RECURSIVE subtree AS (
                    SELECT id FROM hierarchical_facts WHERE parent_id = ?
                    UNION ALL
                    SELECT hf.id FROM hierarchical_facts hf
                    JOIN subtree s ON hf.parent_id = s.id
                )
                SELECT hf.* FROM hierarchical_facts hf
                JOIN subtree s ON hf.id = s.id
                ORDER BY hf.level ASC
                """,
                (fact_id,),
            ).fetchall()

            facts.extend(self._row_to_fact(row) for row in rows)

        return facts

    def get_domains(self) -> List[str]:
        """Get list of all domains."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT domain FROM hierarchical_facts WHERE domain IS NOT NULL"
            ).fetchall()
            return [row[0] for row in rows]

    def promote_fact(self, fact_id: str, new_level: MemoryLevel) -> bool:
        """
        Promote a fact to a higher level.

        Args:
            fact_id: The fact to promote
            new_level: The new level (must be lower number = higher priority)

        Returns:
            True if promoted successfully
        """
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE hierarchical_facts SET level = ? WHERE id = ?",
                (new_level.value, fact_id),
            )
            return result.rowcount > 0

    def mark_stale(self, fact_id: str) -> bool:
        """Mark a fact as stale."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE hierarchical_facts SET is_stale = 1 WHERE id = ?", (fact_id,)
            )
            return result.rowcount > 0

    def archive_fact(self, fact_id: str) -> bool:
        """Archive a fact."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE hierarchical_facts SET is_archived = 1 WHERE id = ?", (fact_id,)
            )
            return result.rowcount > 0

    def delete_fact(self, fact_id: str) -> bool:
        """Permanently delete a fact."""
        with sqlite3.connect(self.db_path) as conn:
            # Delete hierarchy relationships
            conn.execute(
                "DELETE FROM fact_hierarchy WHERE parent_id = ? OR child_id = ?",
                (fact_id, fact_id),
            )
            conn.execute("DELETE FROM embeddings_index WHERE fact_id = ?", (fact_id,))
            result = conn.execute(
                "DELETE FROM hierarchical_facts WHERE id = ?", (fact_id,)
            )
            return result.rowcount > 0

    def update_embedding(
        self, fact_id: str, embedding: List[float], model_name: str = "all-MiniLM-L6-v2"
    ) -> bool:
        """Update the embedding for a fact."""
        with sqlite3.connect(self.db_path) as conn:
            # Update in facts table
            conn.execute(
                "UPDATE hierarchical_facts SET embedding = ? WHERE id = ?",
                (json.dumps(embedding), fact_id),
            )
            # Update in index
            conn.execute(
                """
                INSERT OR REPLACE INTO embeddings_index (fact_id, embedding, model_name, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    fact_id,
                    json.dumps(embedding),
                    model_name,
                    datetime.now().isoformat(),
                ),
            )
            return True

    def get_facts_with_embeddings(self) -> List[Tuple[HierarchicalFact, List[float]]]:
        """Get all facts that have embeddings."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT hf.*, ei.embedding as stored_embedding
                FROM hierarchical_facts hf
                JOIN embeddings_index ei ON hf.id = ei.fact_id
                WHERE hf.is_archived = 0
                """
            ).fetchall()

            results = []
            for row in rows:
                fact = self._row_to_fact(row)
                embedding = (
                    json.loads(row["stored_embedding"])
                    if row["stored_embedding"]
                    else []
                )
                results.append((fact, embedding))

            return results

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM hierarchical_facts").fetchone()[
                0
            ]
            by_level = {}
            for level in MemoryLevel:
                count = conn.execute(
                    "SELECT COUNT(*) FROM hierarchical_facts WHERE level = ?",
                    (level.value,),
                ).fetchone()[0]
                by_level[level.name] = count

            stale = conn.execute(
                "SELECT COUNT(*) FROM hierarchical_facts WHERE is_stale = 1"
            ).fetchone()[0]
            archived = conn.execute(
                "SELECT COUNT(*) FROM hierarchical_facts WHERE is_archived = 1"
            ).fetchone()[0]
            with_embeddings = conn.execute(
                "SELECT COUNT(*) FROM embeddings_index"
            ).fetchone()[0]
            domains = conn.execute(
                "SELECT COUNT(DISTINCT domain) FROM hierarchical_facts WHERE domain IS NOT NULL"
            ).fetchone()[0]

            return {
                "total_facts": total,
                "by_level": by_level,
                "stale_facts": stale,
                "archived_facts": archived,
                "with_embeddings": with_embeddings,
                "domains": domains,
                "db_path": str(self.db_path),
                "schema_version": self.SCHEMA_VERSION,
            }

    def _row_to_fact(self, row: sqlite3.Row) -> HierarchicalFact:
        """Convert a database row to a HierarchicalFact."""
        ttl_config = None
        if row["ttl_config"]:
            ttl_config = TTLConfig.from_dict(json.loads(row["ttl_config"]))

        embedding = None
        if row["embedding"]:
            embedding = json.loads(row["embedding"])

        # Get children IDs
        children_ids = []
        with sqlite3.connect(self.db_path) as conn:
            children = conn.execute(
                "SELECT child_id FROM fact_hierarchy WHERE parent_id = ?", (row["id"],)
            ).fetchall()
            children_ids = [c[0] for c in children]

        return HierarchicalFact(
            id=row["id"],
            content=row["content"],
            level=MemoryLevel(row["level"]),
            domain=row["domain"],
            module=row["module"],
            code_ref=row["code_ref"],
            parent_id=row["parent_id"],
            children_ids=children_ids,
            embedding=embedding,
            ttl_config=ttl_config,
            created_at=datetime.fromisoformat(row["created_at"]),
            valid_from=datetime.fromisoformat(row["valid_from"]),
            valid_until=(
                datetime.fromisoformat(row["valid_until"])
                if row["valid_until"]
                else None
            ),
            is_stale=bool(row["is_stale"]),
            is_archived=bool(row["is_archived"]),
            confidence=row["confidence"],
            source=row["source"],
        )
