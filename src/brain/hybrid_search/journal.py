"""
Hybrid Search Journal — Collection of nodes representing the solution tree.

Adapted from AIDE ML (WecoAI/aideml) and AI-Scientist (SakanaAI).
Part of SENTINEL Hybrid Search Agent.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

from dataclasses_json import DataClassJsonMixin

from .node import SearchNode

logger = logging.getLogger("hybrid_search")


@dataclass
class SearchJournal(DataClassJsonMixin):
    """
    A collection of nodes representing the solution tree.

    Tracks all search nodes, provides filtering (good/buggy),
    and implements selection strategies (best, top-k).

    Adapted from AIDE ML's Journal class.
    """

    nodes: List[SearchNode] = field(default_factory=list)

    def __getitem__(self, idx: int) -> SearchNode:
        return self.nodes[idx]

    def __len__(self) -> int:
        """Return total number of nodes."""
        return len(self.nodes)

    def append(self, node: SearchNode) -> None:
        """Add a new node to the journal."""
        node.step = len(self.nodes)
        self.nodes.append(node)
        logger.debug(
            f"[journal] Added node {node.id[:8]} (step={node.step}, stage={node.stage_name})"
        )

    # ---- Filtering ----

    @property
    def draft_nodes(self) -> List[SearchNode]:
        """Return initial solution drafts (no parent)."""
        return [n for n in self.nodes if n.parent is None]

    @property
    def buggy_nodes(self) -> List[SearchNode]:
        """Return nodes that failed or are marked buggy."""
        return [n for n in self.nodes if n.is_buggy]

    @property
    def good_nodes(self) -> List[SearchNode]:
        """Return nodes that are not buggy."""
        return [n for n in self.nodes if not n.is_buggy]

    @property
    def leaf_nodes(self) -> List[SearchNode]:
        """Return nodes with no children."""
        return [n for n in self.nodes if n.is_leaf]

    # ---- Selection ----

    def get_best_node(self, only_good: bool = True) -> Optional[SearchNode]:
        """
        Return the best solution found so far.

        Args:
            only_good: If True, only consider non-buggy nodes

        Returns:
            Node with highest metric, or None if no nodes
        """
        candidates = self.good_nodes if only_good else self.nodes
        if not candidates:
            return None
        return max(candidates, key=lambda n: n.metric)

    def get_top_nodes(self, k: int = 5, only_good: bool = True) -> List[SearchNode]:
        """
        Return top-K nodes by metric for exploration.

        Args:
            k: Number of top nodes to return
            only_good: If True, only consider non-buggy nodes

        Returns:
            List of top-K nodes sorted by metric descending
        """
        candidates = self.good_nodes if only_good else self.nodes
        return sorted(candidates, key=lambda n: n.metric, reverse=True)[:k]

    def get_debuggable_nodes(self, max_debug_depth: int = 3) -> List[SearchNode]:
        """
        Return buggy leaf nodes that can still be debugged.

        Args:
            max_debug_depth: Maximum consecutive debug attempts

        Returns:
            List of nodes eligible for debugging
        """
        return [
            n
            for n in self.buggy_nodes
            if n.is_leaf and n.debug_depth <= max_debug_depth
        ]

    # ---- Metrics ----

    def get_metric_history(self) -> List[float]:
        """Return list of all metrics in order."""
        return [n.metric for n in self.nodes]

    def get_best_metric_so_far(self) -> List[float]:
        """Return cumulative best metric at each step."""
        best_so_far = []
        current_best = float("-inf")
        for node in self.nodes:
            if not node.is_buggy and node.metric > current_best:
                current_best = node.metric
            best_so_far.append(current_best if current_best > float("-inf") else 0.0)
        return best_so_far

    # ---- Summary ----

    def generate_summary(self, include_code: bool = False) -> str:
        """
        Generate a summary of the journal for reporting.

        Args:
            include_code: Whether to include code in summary

        Returns:
            Formatted summary string
        """
        lines = [
            "=== Search Journal Summary ===",
            f"Total nodes: {len(self.nodes)}",
            f"Draft nodes: {len(self.draft_nodes)}",
            f"Good nodes: {len(self.good_nodes)}",
            f"Buggy nodes: {len(self.buggy_nodes)}",
            "",
        ]

        best = self.get_best_node()
        if best:
            lines.append(f"Best node: {best.id[:8]}")
            lines.append(f"  Metric: {best.metric:.4f}")
            lines.append(f"  Stage: {best.stage_name}")
            lines.append(f"  Depth: {best.depth}")
            if include_code:
                lines.append(f"  Code: {best.code[:200]}...")

        return "\n".join(lines)

    # ---- Persistence ----

    def save(self, path: Path) -> None:
        """Save journal to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format (exclude parent/children to avoid cycles)
        data = []
        for node in self.nodes:
            node_dict = {
                "id": node.id,
                "code": node.code,
                "plan": node.plan,
                "step": node.step,
                "ctime": node.ctime,
                "exec_time": node.exec_time,
                "exc_type": node.exc_type,
                "exc_info": node.exc_info,
                "metric": node.metric,
                "is_buggy": node.is_buggy,
                "analysis": node.analysis,
                "attack_class": node.attack_class,
                "bypassed_engines": node.bypassed_engines,
                "triggered_engines": node.triggered_engines,
                "vlm_score": node.vlm_score,
                "vlm_analysis": node.vlm_analysis,
                "image_path": node.image_path,
                "ablation_target": node.ablation_target,
                "ablation_result": node.ablation_result,
                "parent_id": node.parent.id if node.parent else None,
            }
            data.append(node_dict)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"[journal] Saved {len(self.nodes)} nodes to {path}")

    @classmethod
    def load(cls, path: Path) -> "SearchJournal":
        """Load journal from JSON file."""
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        journal = cls()
        id_to_node = {}

        # First pass: create all nodes
        for node_dict in data:
            parent_id = node_dict.pop("parent_id", None)
            node = SearchNode.from_dict(node_dict)
            node._pending_parent_id = parent_id  # type: ignore
            id_to_node[node.id] = node
            journal.nodes.append(node)

        # Second pass: restore parent/child relationships
        for node in journal.nodes:
            parent_id = getattr(node, "_pending_parent_id", None)
            if parent_id and parent_id in id_to_node:
                node.parent = id_to_node[parent_id]
                node.parent.children.add(node)
            (
                delattr(node, "_pending_parent_id")
                if hasattr(node, "_pending_parent_id")
                else None
            )

        logger.info(f"[journal] Loaded {len(journal.nodes)} nodes from {path}")
        return journal
