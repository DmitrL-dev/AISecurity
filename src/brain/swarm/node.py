"""
SwarmNode — BRAIN Node Identity and Status

Represents a single BRAIN instance in the swarm.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
import hashlib
import json
import random


class NodeStatus(Enum):
    """Node health status."""

    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class SwarmNode:
    """
    Represents a single BRAIN node in the swarm.

    Attributes:
        node_id: Unique identifier (auto-generated if not provided)
        hostname: DNS name or IP
        port: API port
        version: BRAIN version string
        status: Current health status
        capabilities: List of enabled features
        last_heartbeat: Last heartbeat timestamp
        registered_at: Registration timestamp
    """

    hostname: str
    port: int
    node_id: str = field(default_factory=lambda: "")
    version: str = "1.0.0"
    status: NodeStatus = NodeStatus.ONLINE
    capabilities: List[str] = field(default_factory=list)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    registered_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Generate node_id if not provided."""
        if not self.node_id:
            self.node_id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate a unique node ID."""
        unique = f"{self.hostname}:{self.port}:{random.random()}"
        return hashlib.sha256(unique.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "hostname": self.hostname,
            "port": self.port,
            "version": self.version,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "registered_at": self.registered_at.isoformat(),
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "SwarmNode":
        """Create from dictionary."""
        return cls(
            node_id=data.get("node_id", ""),
            hostname=data["hostname"],
            port=data["port"],
            version=data.get("version", "1.0.0"),
            status=NodeStatus(data.get("status", "online")),
            capabilities=data.get("capabilities", []),
            last_heartbeat=(
                datetime.fromisoformat(data["last_heartbeat"])
                if "last_heartbeat" in data
                else datetime.now()
            ),
            registered_at=(
                datetime.fromisoformat(data["registered_at"])
                if "registered_at" in data
                else datetime.now()
            ),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "SwarmNode":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.now()
