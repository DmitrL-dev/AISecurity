"""
Causal Chain Tracker for Memory Bridge v2.0

Provides decision reasoning preservation across sessions:
- Record decisions with reasons and consequences
- Query causal chains
- Visualize reasoning graphs
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import json
import logging
import sqlite3
import uuid

logger = logging.getLogger(__name__)


class CausalNodeType(Enum):
    """Types of nodes in a causal chain."""

    DECISION = "decision"  # A choice made
    REASON = "reason"  # Why the decision was made
    CONSEQUENCE = "consequence"  # What resulted from the decision
    CONSTRAINT = "constraint"  # Limitations that affected the decision
    ASSUMPTION = "assumption"  # Assumptions made
    ALTERNATIVE = "alternative"  # Alternatives considered but not chosen


class CausalEdgeType(Enum):
    """Types of edges connecting causal nodes."""

    CAUSES = "causes"  # A causes B
    JUSTIFIES = "justifies"  # A justifies B
    LEADS_TO = "leads_to"  # A leads to B
    BLOCKS = "blocks"  # A blocks B
    ENABLES = "enables"  # A enables B
    CONFLICTS = "conflicts"  # A conflicts with B


@dataclass
class CausalNode:
    """A node in a causal chain."""

    id: str
    node_type: CausalNodeType
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "session_id": self.session_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalNode":
        return cls(
            id=data["id"],
            node_type=CausalNodeType(data["node_type"]),
            content=data["content"],
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now()
            ),
            session_id=data.get("session_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CausalEdge:
    """An edge connecting causal nodes."""

    from_id: str
    to_id: str
    edge_type: CausalEdgeType
    strength: float = 1.0  # 0.0-1.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_id": self.from_id,
            "to_id": self.to_id,
            "edge_type": self.edge_type.value,
            "strength": self.strength,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalEdge":
        return cls(
            from_id=data["from_id"],
            to_id=data["to_id"],
            edge_type=CausalEdgeType(data["edge_type"]),
            strength=data.get("strength", 1.0),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now()
            ),
        )


@dataclass
class CausalChain:
    """A complete causal chain starting from a decision."""

    root: CausalNode
    nodes: List[CausalNode]
    edges: List[CausalEdge]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": self.root.to_dict(),
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    @property
    def reasons(self) -> List[CausalNode]:
        """Get all reason nodes."""
        return [n for n in self.nodes if n.node_type == CausalNodeType.REASON]

    @property
    def consequences(self) -> List[CausalNode]:
        """Get all consequence nodes."""
        return [n for n in self.nodes if n.node_type == CausalNodeType.CONSEQUENCE]

    @property
    def constraints(self) -> List[CausalNode]:
        """Get all constraint nodes."""
        return [n for n in self.nodes if n.node_type == CausalNodeType.CONSTRAINT]


class CausalChainTracker:
    """
    Tracks and manages causal chains for decision reasoning.

    Provides:
    - Recording decisions with reasons, consequences, constraints
    - Querying causal chains by decision content
    - Visualization in Mermaid format
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".rlm" / "causal_chains.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS causal_nodes (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    metadata TEXT DEFAULT '{}'
                );
                
                CREATE TABLE IF NOT EXISTS causal_edges (
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    strength REAL DEFAULT 1.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (from_id, to_id, edge_type),
                    FOREIGN KEY (from_id) REFERENCES causal_nodes(id),
                    FOREIGN KEY (to_id) REFERENCES causal_nodes(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_nodes_type ON causal_nodes(node_type);
                CREATE INDEX IF NOT EXISTS idx_nodes_session ON causal_nodes(session_id);
                CREATE INDEX IF NOT EXISTS idx_edges_from ON causal_edges(from_id);
                CREATE INDEX IF NOT EXISTS idx_edges_to ON causal_edges(to_id);
            """
            )

    def record_decision(
        self,
        decision: str,
        reasons: Optional[List[str]] = None,
        consequences: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        alternatives: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record a decision with its causal context.

        Args:
            decision: The decision that was made
            reasons: List of reasons for the decision
            consequences: List of resulting consequences
            constraints: List of constraints that affected the decision
            alternatives: List of alternatives that were considered
            session_id: Session ID for grouping
            metadata: Additional metadata

        Returns:
            The decision node ID
        """
        decision_id = str(uuid.uuid4())
        now = datetime.now()

        # Create decision node
        decision_node = CausalNode(
            id=decision_id,
            node_type=CausalNodeType.DECISION,
            content=decision,
            created_at=now,
            session_id=session_id,
            metadata=metadata or {},
        )
        self._save_node(decision_node)

        # Create reason nodes and edges
        for reason in reasons or []:
            reason_id = str(uuid.uuid4())
            reason_node = CausalNode(
                id=reason_id,
                node_type=CausalNodeType.REASON,
                content=reason,
                created_at=now,
                session_id=session_id,
            )
            self._save_node(reason_node)

            edge = CausalEdge(
                from_id=reason_id,
                to_id=decision_id,
                edge_type=CausalEdgeType.JUSTIFIES,
            )
            self._save_edge(edge)

        # Create consequence nodes and edges
        for consequence in consequences or []:
            cons_id = str(uuid.uuid4())
            cons_node = CausalNode(
                id=cons_id,
                node_type=CausalNodeType.CONSEQUENCE,
                content=consequence,
                created_at=now,
                session_id=session_id,
            )
            self._save_node(cons_node)

            edge = CausalEdge(
                from_id=decision_id,
                to_id=cons_id,
                edge_type=CausalEdgeType.LEADS_TO,
            )
            self._save_edge(edge)

        # Create constraint nodes and edges
        for constraint in constraints or []:
            const_id = str(uuid.uuid4())
            const_node = CausalNode(
                id=const_id,
                node_type=CausalNodeType.CONSTRAINT,
                content=constraint,
                created_at=now,
                session_id=session_id,
            )
            self._save_node(const_node)

            edge = CausalEdge(
                from_id=const_id,
                to_id=decision_id,
                edge_type=CausalEdgeType.BLOCKS,
                strength=0.5,  # Constraints partially influence
            )
            self._save_edge(edge)

        # Create alternative nodes and edges
        for alternative in alternatives or []:
            alt_id = str(uuid.uuid4())
            alt_node = CausalNode(
                id=alt_id,
                node_type=CausalNodeType.ALTERNATIVE,
                content=alternative,
                created_at=now,
                session_id=session_id,
            )
            self._save_node(alt_node)

            edge = CausalEdge(
                from_id=alt_id,
                to_id=decision_id,
                edge_type=CausalEdgeType.CONFLICTS,
                strength=0.3,
            )
            self._save_edge(edge)

        logger.info(f"Recorded decision {decision_id}: {decision[:50]}...")
        return decision_id

    def query_chain(
        self,
        query: str,
        max_depth: int = 5,
        session_id: Optional[str] = None,
    ) -> Optional[CausalChain]:
        """
        Query causal chain by content search.

        Args:
            query: Search query for decision content
            max_depth: Maximum traversal depth
            session_id: Optional session filter

        Returns:
            CausalChain if found, None otherwise
        """
        # Find matching decision nodes
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = """
                SELECT * FROM causal_nodes 
                WHERE node_type = 'decision' 
                AND content LIKE ?
            """
            params = [f"%{query}%"]

            if session_id:
                sql += " AND session_id = ?"
                params.append(session_id)

            sql += " ORDER BY created_at DESC LIMIT 1"

            row = conn.execute(sql, params).fetchone()

            if not row:
                return None

            decision_node = self._row_to_node(row)

        # Build full chain from decision
        return self.get_chain_for_decision(decision_node.id, max_depth)

    def get_chain_for_decision(
        self,
        decision_id: str,
        max_depth: int = 5,
    ) -> Optional[CausalChain]:
        """
        Get the full causal chain for a decision.

        Args:
            decision_id: The decision node ID
            max_depth: Maximum traversal depth

        Returns:
            CausalChain with all related nodes and edges
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get decision node
            row = conn.execute(
                "SELECT * FROM causal_nodes WHERE id = ?", (decision_id,)
            ).fetchone()

            if not row:
                return None

            decision_node = self._row_to_node(row)

            # Collect all connected nodes and edges using BFS
            visited_nodes: Set[str] = {decision_id}
            nodes: List[CausalNode] = [decision_node]
            edges: List[CausalEdge] = []

            frontier = [decision_id]
            depth = 0

            while frontier and depth < max_depth:
                next_frontier = []

                for node_id in frontier:
                    # Get outgoing edges
                    edge_rows = conn.execute(
                        "SELECT * FROM causal_edges WHERE from_id = ? OR to_id = ?",
                        (node_id, node_id),
                    ).fetchall()

                    for edge_row in edge_rows:
                        edge = self._row_to_edge(edge_row)
                        if edge not in edges:
                            edges.append(edge)

                        # Get connected node
                        other_id = (
                            edge.to_id if edge.from_id == node_id else edge.from_id
                        )

                        if other_id not in visited_nodes:
                            visited_nodes.add(other_id)
                            node_row = conn.execute(
                                "SELECT * FROM causal_nodes WHERE id = ?", (other_id,)
                            ).fetchone()

                            if node_row:
                                nodes.append(self._row_to_node(node_row))
                                next_frontier.append(other_id)

                frontier = next_frontier
                depth += 1

        return CausalChain(
            root=decision_node,
            nodes=nodes,
            edges=edges,
        )

    def get_all_decisions(
        self,
        session_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CausalNode]:
        """Get all decision nodes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = "SELECT * FROM causal_nodes WHERE node_type = 'decision'"
            params = []

            if session_id:
                sql += " AND session_id = ?"
                params.append(session_id)

            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_node(row) for row in rows]

    def visualize(self, chain: CausalChain) -> str:
        """
        Generate Mermaid diagram for a causal chain.

        Args:
            chain: The causal chain to visualize

        Returns:
            Mermaid diagram string
        """
        lines = ["graph TD"]

        # Node type to shape mapping
        shapes = {
            CausalNodeType.DECISION: ('["', '"]'),  # Rectangle
            CausalNodeType.REASON: ('("', '")'),  # Rounded
            CausalNodeType.CONSEQUENCE: ('(["', '"])'),  # Stadium
            CausalNodeType.CONSTRAINT: ('{"', '"}'),  # Diamond-ish
            CausalNodeType.ALTERNATIVE: ('(("', '"))'),  # Circle
            CausalNodeType.ASSUMPTION: ('["', '"]'),  # Rectangle
        }

        # Edge type to arrow mapping
        arrows = {
            CausalEdgeType.CAUSES: "-->",
            CausalEdgeType.JUSTIFIES: "-.->",
            CausalEdgeType.LEADS_TO: "==>",
            CausalEdgeType.BLOCKS: "--x",
            CausalEdgeType.ENABLES: "-->",
            CausalEdgeType.CONFLICTS: "-.-x",
        }

        # Create node ID mapping (short IDs for mermaid)
        node_ids = {node.id: f"N{i}" for i, node in enumerate(chain.nodes)}

        # Add nodes
        for node in chain.nodes:
            short_id = node_ids[node.id]
            open_shape, close_shape = shapes.get(node.node_type, ('["', '"]'))

            # Truncate and escape content
            content = node.content[:50].replace('"', "'")
            if len(node.content) > 50:
                content += "..."

            lines.append(f"    {short_id}{open_shape}{content}{close_shape}")

        # Add edges
        for edge in chain.edges:
            if edge.from_id in node_ids and edge.to_id in node_ids:
                from_short = node_ids[edge.from_id]
                to_short = node_ids[edge.to_id]
                arrow = arrows.get(edge.edge_type, "-->")
                lines.append(f"    {from_short} {arrow} {to_short}")

        return "\n".join(lines)

    def format_chain_summary(self, chain: CausalChain) -> str:
        """
        Format causal chain as a text summary.

        Args:
            chain: The causal chain to format

        Returns:
            Human-readable summary
        """
        lines = [f"## Decision: {chain.root.content}"]

        if chain.reasons:
            lines.append("\n### Reasons:")
            for reason in chain.reasons:
                lines.append(f"- {reason.content}")

        if chain.constraints:
            lines.append("\n### Constraints:")
            for constraint in chain.constraints:
                lines.append(f"- {constraint.content}")

        if chain.consequences:
            lines.append("\n### Consequences:")
            for consequence in chain.consequences:
                lines.append(f"- {consequence.content}")

        return "\n".join(lines)

    def _save_node(self, node: CausalNode) -> None:
        """Save a node to the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO causal_nodes 
                (id, node_type, content, created_at, session_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.node_type.value,
                    node.content,
                    node.created_at.isoformat(),
                    node.session_id,
                    json.dumps(node.metadata),
                ),
            )

    def _save_edge(self, edge: CausalEdge) -> None:
        """Save an edge to the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO causal_edges 
                (from_id, to_id, edge_type, strength, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    edge.from_id,
                    edge.to_id,
                    edge.edge_type.value,
                    edge.strength,
                    edge.created_at.isoformat(),
                ),
            )

    def _row_to_node(self, row: sqlite3.Row) -> CausalNode:
        """Convert database row to CausalNode."""
        return CausalNode(
            id=row["id"],
            node_type=CausalNodeType(row["node_type"]),
            content=row["content"],
            created_at=(
                datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else datetime.now()
            ),
            session_id=row["session_id"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _row_to_edge(self, row: sqlite3.Row) -> CausalEdge:
        """Convert database row to CausalEdge."""
        return CausalEdge(
            from_id=row["from_id"],
            to_id=row["to_id"],
            edge_type=CausalEdgeType(row["edge_type"]),
            strength=row["strength"],
            created_at=(
                datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else datetime.now()
            ),
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get causal chain statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total_nodes = conn.execute("SELECT COUNT(*) FROM causal_nodes").fetchone()[
                0
            ]
            total_edges = conn.execute("SELECT COUNT(*) FROM causal_edges").fetchone()[
                0
            ]
            decisions = conn.execute(
                "SELECT COUNT(*) FROM causal_nodes WHERE node_type = 'decision'"
            ).fetchone()[0]

            by_type = {}
            for node_type in CausalNodeType:
                count = conn.execute(
                    "SELECT COUNT(*) FROM causal_nodes WHERE node_type = ?",
                    (node_type.value,),
                ).fetchone()[0]
                by_type[node_type.value] = count

            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "decisions": decisions,
                "by_type": by_type,
                "db_path": str(self.db_path),
            }
