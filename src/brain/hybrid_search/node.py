"""
Hybrid Search Node — Core datastructure for tree-based search.

Adapted from AIDE ML (WecoAI/aideml) and AI-Scientist (SakanaAI).
Part of SENTINEL Hybrid Search Agent.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Set, Any, Dict

from dataclasses_json import DataClassJsonMixin


@dataclass(eq=False)
class SearchNode(DataClassJsonMixin):
    """
    A single node in the solution tree.

    Contains code/payload, execution results, and evaluation information.
    Adapted from AIDE ML's Node class with SENTINEL-specific extensions.

    Attributes:
        id: Unique identifier for this node
        code: The attack payload or code
        plan: Natural language description of the approach
        metric: Evaluation score (higher = better attack)
        is_buggy: Whether the node failed execution
        analysis: LLM analysis of results
        parent: Parent node in the tree
        children: Child nodes spawned from this node
    """

    # ---- Core (from AIDE ML) ----
    code: str = ""
    plan: str = ""

    # ---- General attrs ----
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    step: int = 0
    ctime: float = field(default_factory=time.time)

    # ---- Tree structure ----
    parent: Optional["SearchNode"] = field(default=None, repr=False)
    children: Set["SearchNode"] = field(default_factory=set, repr=False)

    # ---- Execution info ----
    exec_time: float = 0.0
    exc_type: Optional[str] = None
    exc_info: Optional[Dict[str, Any]] = None

    # ---- Evaluation ----
    metric: float = 0.0
    is_buggy: bool = False
    analysis: str = ""

    # ---- SENTINEL extensions ----
    attack_class: Optional[str] = None
    bypassed_engines: List[str] = field(default_factory=list)
    triggered_engines: List[str] = field(default_factory=list)

    # ---- VLM extensions (AI-Scientist) ----
    vlm_score: Optional[float] = None
    vlm_analysis: Optional[str] = None
    image_path: Optional[str] = None

    # ---- Ablation extensions (AI-Scientist) ----
    ablation_target: Optional[str] = None
    ablation_result: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Register this node as a child of its parent."""
        if self.parent is not None:
            self.parent.children.add(self)

    @property
    def stage_name(self) -> str:
        """
        Return the stage of the node:
        - "draft" if this is an initial solution
        - "debug" if parent was buggy
        - "improve" if parent was successful
        """
        if self.parent is None:
            return "draft"
        return "debug" if self.parent.is_buggy else "improve"

    @property
    def is_leaf(self) -> bool:
        """Check if this node has no children."""
        return len(self.children) == 0

    @property
    def debug_depth(self) -> int:
        """
        Count consecutive debugging steps.

        Returns:
            0 if not a debug node
            n if there were n consecutive debug attempts
        """
        if self.stage_name != "debug":
            return 0
        if self.parent is None:
            return 0
        return self.parent.debug_depth + 1

    @property
    def depth(self) -> int:
        """Get depth in the tree (distance from root)."""
        if self.parent is None:
            return 0
        return self.parent.depth + 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SearchNode) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def to_dict_minimal(self) -> Dict[str, Any]:
        """Return minimal dict representation for logging."""
        return {
            "id": self.id[:8],
            "stage": self.stage_name,
            "metric": self.metric,
            "is_buggy": self.is_buggy,
            "depth": self.depth,
            "children_count": len(self.children),
        }
