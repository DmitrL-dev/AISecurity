"""
Memory Bridge v2 — Domain Models

Enums, dataclasses, and value objects used across v2 modules.
Extracted from hierarchical.py for Single Responsibility.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryLevel(Enum):
    """Hierarchy levels for memory organization."""

    L0_PROJECT = 0  # Always loaded (10-20 facts)
    L1_DOMAIN = 1  # Loaded by task context
    L2_MODULE = 2  # Loaded on-demand
    L3_CODE = 3  # C³ Crystal integration


class TTLAction(Enum):
    """Actions to take when TTL expires."""

    MARK_STALE = "mark_stale"
    ARCHIVE = "archive"
    DELETE = "delete"


@dataclass
class TTLConfig:
    """TTL configuration for a fact."""

    ttl_seconds: int
    refresh_trigger: Optional[str] = None
    on_expire: TTLAction = TTLAction.MARK_STALE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ttl_seconds": self.ttl_seconds,
            "refresh_trigger": self.refresh_trigger,
            "on_expire": self.on_expire.value,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "TTLConfig":
        return cls(
            ttl_seconds=data["ttl_seconds"],
            refresh_trigger=data.get("refresh_trigger"),
            on_expire=TTLAction(data.get("on_expire", "mark_stale")),
        )


@dataclass
class HierarchicalFact:
    """A fact with hierarchical organization and
    temporal metadata."""

    id: str
    content: str
    level: MemoryLevel
    domain: Optional[str] = None
    module: Optional[str] = None
    code_ref: Optional[str] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = field(
        default_factory=list,
    )
    embedding: Optional[List[float]] = None
    ttl_config: Optional[TTLConfig] = None
    created_at: datetime = field(
        default_factory=datetime.now,
    )
    valid_from: datetime = field(
        default_factory=datetime.now,
    )
    valid_until: Optional[datetime] = None
    is_stale: bool = False
    is_archived: bool = False
    confidence: float = 1.0
    source: str = "manual"

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
            "ttl_config": (self.ttl_config.to_dict() if self.ttl_config else None),
            "created_at": (self.created_at.isoformat()),
            "valid_from": (self.valid_from.isoformat()),
            "valid_until": (self.valid_until.isoformat() if self.valid_until else None),
            "is_stale": self.is_stale,
            "is_archived": self.is_archived,
            "confidence": self.confidence,
            "source": self.source,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "HierarchicalFact":
        return cls(
            id=data["id"],
            content=data["content"],
            level=MemoryLevel(data["level"]),
            domain=data.get("domain"),
            module=data.get("module"),
            code_ref=data.get("code_ref"),
            parent_id=data.get("parent_id"),
            children_ids=data.get(
                "children_ids",
                [],
            ),
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
            is_archived=data.get(
                "is_archived",
                False,
            ),
            confidence=data.get("confidence", 1.0),
            source=data.get("source", "manual"),
        )

    def token_estimate(self) -> int:
        """Estimate token count for this fact."""
        base_tokens = len(self.content) // 4
        metadata_tokens = 20
        return base_tokens + metadata_tokens

    def is_expired(self) -> bool:
        """Check if TTL has expired."""
        if not self.ttl_config:
            return False
        expiry_time = self.created_at + timedelta(
            seconds=self.ttl_config.ttl_seconds,
        )
        return datetime.now() > expiry_time
