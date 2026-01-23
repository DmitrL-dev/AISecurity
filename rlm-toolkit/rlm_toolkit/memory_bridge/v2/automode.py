"""
Auto-Mode Orchestrator for Memory Bridge v2.1

Provides zero-friction enterprise context:
- Auto-discovery for new projects
- Auto-routing for queries
- Suggestion system for git hooks
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging

from .hierarchical import (
    HierarchicalMemoryStore,
    HierarchicalFact,
    MemoryLevel,
)
from .router import SemanticRouter
from .coldstart import ColdStartOptimizer, DiscoveryResult
from .causal import CausalChainTracker

logger = logging.getLogger(__name__)


@dataclass
class ProjectFingerprint:
    """Fingerprint to detect project changes."""

    root_path: str
    project_type: str
    file_count: int
    created_at: datetime
    last_discovery: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_path": self.root_path,
            "project_type": self.project_type,
            "file_count": self.file_count,
            "created_at": self.created_at.isoformat(),
            "last_discovery": self.last_discovery.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectFingerprint":
        return cls(
            root_path=data["root_path"],
            project_type=data["project_type"],
            file_count=data["file_count"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_discovery=datetime.fromisoformat(data["last_discovery"]),
        )


@dataclass
class Suggestion:
    """Suggestion for user action."""

    type: str  # install_git_hook, reindex, etc.
    message: str
    command: str
    priority: str = "medium"  # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "message": self.message,
            "command": self.command,
            "priority": self.priority,
        }


@dataclass
class EnterpriseContext:
    """Complete enterprise context for injection."""

    facts: List[HierarchicalFact]
    causal_summary: str
    project_overview: str
    total_tokens: int
    discovery_performed: bool
    suggestions: List[Suggestion] = field(default_factory=list)

    def to_injection_string(self) -> str:
        """Format context for LLM injection."""
        parts = []

        # Project overview
        if self.project_overview:
            parts.append("## Project Overview")
            parts.append(self.project_overview)
            parts.append("")

        # Facts by level
        l0_facts = [f for f in self.facts if f.level == MemoryLevel.L0_PROJECT]
        l1_facts = [f for f in self.facts if f.level == MemoryLevel.L1_DOMAIN]
        l2_facts = [f for f in self.facts if f.level == MemoryLevel.L2_MODULE]

        if l0_facts:
            parts.append("## Architecture")
            for f in l0_facts:
                parts.append(f"- {f.content}")
            parts.append("")

        if l1_facts:
            parts.append("## Domains")
            for f in l1_facts:
                domain = f.domain or "general"
                parts.append(f"- [{domain}] {f.content}")
            parts.append("")

        if l2_facts:
            parts.append("## Modules")
            for f in l2_facts[:10]:  # Limit
                parts.append(f"- {f.content}")
            parts.append("")

        # Causal context
        if self.causal_summary:
            parts.append("## Past Decisions")
            parts.append(self.causal_summary)

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts_count": len(self.facts),
            "total_tokens": self.total_tokens,
            "discovery_performed": self.discovery_performed,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "context": self.to_injection_string(),
        }


class DiscoveryOrchestrator:
    """
    Orchestrates auto-discovery decisions.

    Determines when to:
    - Run full project discovery
    - Just restore existing state
    - Suggest re-indexing
    """

    # Re-discovery interval (days)
    REDISCOVERY_INTERVAL_DAYS = 30

    def __init__(
        self,
        store: HierarchicalMemoryStore,
        cold_start: ColdStartOptimizer,
        project_root: Optional[Path] = None,
    ):
        self.store = store
        self.cold_start = cold_start
        self.project_root = project_root or Path.cwd()
        self._last_discovery_performed = False
        self._fingerprint: Optional[ProjectFingerprint] = None

    @property
    def last_discovery_performed(self) -> bool:
        return self._last_discovery_performed

    def should_discover(self) -> tuple[bool, str]:
        """
        Check if project needs discovery.

        Returns:
            (should_discover, reason)
        """
        # 1. Check if any L0 facts exist
        l0_facts = self.store.get_facts_by_level(MemoryLevel.L0_PROJECT)
        if not l0_facts:
            return True, "no_l0_facts"

        # 2. Load fingerprint and check project root
        fingerprint = self._load_fingerprint()
        if fingerprint is None:
            return True, "no_fingerprint"

        current_root = str(self.project_root.resolve())
        if fingerprint.root_path != current_root:
            return True, "root_changed"

        # 3. Check if significant time passed
        days_since = (datetime.now() - fingerprint.last_discovery).days
        if days_since > self.REDISCOVERY_INTERVAL_DAYS:
            return True, "stale_discovery"

        return False, "up_to_date"

    def discover_or_restore(
        self,
        task_hint: Optional[str] = None,
    ) -> DiscoveryResult:
        """
        Auto-decide: discover new or restore existing.

        Returns:
            DiscoveryResult
        """
        should, reason = self.should_discover()

        if should:
            logger.info(f"Running discovery (reason: {reason})")
            result = self._run_discovery(task_hint)
            self._last_discovery_performed = True
            return result
        else:
            logger.info(f"Skipping discovery (reason: {reason})")
            self._last_discovery_performed = False
            # Return minimal result
            return DiscoveryResult(
                project_info=self._get_cached_project_info(),
                facts_created=0,
                discovery_tokens=0,
                suggested_domains=[],
            )

    def force_discovery(
        self,
        task_hint: Optional[str] = None,
    ) -> DiscoveryResult:
        """Force full discovery regardless of state."""
        logger.info("Forcing discovery")
        result = self._run_discovery(task_hint)
        self._last_discovery_performed = True
        return result

    def _run_discovery(
        self,
        task_hint: Optional[str] = None,
    ) -> DiscoveryResult:
        """Run cold start discovery."""
        result = self.cold_start.discover_project(
            root=self.project_root,
            task_hint=task_hint,
        )

        # Save fingerprint
        self._save_fingerprint(result)

        return result

    def _load_fingerprint(self) -> Optional[ProjectFingerprint]:
        """Load project fingerprint from store."""
        if self._fingerprint:
            return self._fingerprint

        try:
            # Store fingerprint in a special L0 fact
            facts = self.store.get_facts_by_level(MemoryLevel.L0_PROJECT)
            for fact in facts:
                if fact.content.startswith("__FINGERPRINT__:"):
                    fp_data = fact.content.replace("__FINGERPRINT__:", "")
                    data = json.loads(fp_data)
                    self._fingerprint = ProjectFingerprint.from_dict(data)
                    return self._fingerprint
        except Exception as e:
            logger.debug(f"Could not load fingerprint: {e}")

        return None

    def _save_fingerprint(self, result: DiscoveryResult) -> None:
        """Save project fingerprint."""
        fingerprint = ProjectFingerprint(
            root_path=str(self.project_root.resolve()),
            project_type=result.project_info.project_type.value,
            file_count=result.project_info.file_count,
            created_at=datetime.now(),
            last_discovery=datetime.now(),
        )

        # Store as special fact
        content = f"__FINGERPRINT__:{json.dumps(fingerprint.to_dict())}"

        # Remove old fingerprint
        facts = self.store.get_facts_by_level(MemoryLevel.L0_PROJECT)
        for fact in facts:
            if fact.content.startswith("__FINGERPRINT__:"):
                self.store.delete_fact(fact.id)

        # Add new
        self.store.add_fact(
            content=content,
            level=MemoryLevel.L0_PROJECT,
            source="fingerprint",
            confidence=1.0,
        )

        self._fingerprint = fingerprint

    def _get_cached_project_info(self):
        """Get cached project info from fingerprint."""
        from .coldstart import ProjectInfo, ProjectType

        fp = self._load_fingerprint()
        if fp:
            return ProjectInfo(
                project_type=ProjectType(fp.project_type),
                name=Path(fp.root_path).name,
                root_path=Path(fp.root_path),
                file_count=fp.file_count,
            )

        # Fallback
        return ProjectInfo(
            project_type=ProjectType.UNKNOWN,
            name=self.project_root.name,
            root_path=self.project_root,
        )


class EnterpriseContextBuilder:
    """
    Builds complete enterprise context for LLM injection.

    Combines:
    - Semantic routing
    - Causal chains
    - Project overview
    """

    def __init__(
        self,
        store: HierarchicalMemoryStore,
        router: SemanticRouter,
        causal_tracker: CausalChainTracker,
        orchestrator: DiscoveryOrchestrator,
    ):
        self.store = store
        self.router = router
        self.causal_tracker = causal_tracker
        self.orchestrator = orchestrator

    def build(
        self,
        query: str,
        max_tokens: int = 3000,
        include_causal: bool = True,
        task_hint: Optional[str] = None,
    ) -> EnterpriseContext:
        """
        Build full enterprise context.

        Steps:
        1. Check if discovery needed
        2. Route facts by query
        3. Get relevant causal chains
        4. Build suggestions
        5. Format for injection
        """
        # 1. Discovery check
        self.orchestrator.discover_or_restore(task_hint=task_hint)

        # 2. Route facts
        causal_budget = 500 if include_causal else 0
        routing_result = self.router.route(
            query=query,
            max_tokens=max_tokens - causal_budget,
        )

        # 3. Causal chains
        causal_summary = ""
        if include_causal:
            causal_summary = self._get_causal_summary(query)

        # 4. Project overview
        project_overview = self._get_project_overview()

        # 5. Suggestions
        suggestions = self._build_suggestions()

        # Calculate tokens
        total_tokens = routing_result.total_tokens
        total_tokens += len(causal_summary) // 4
        total_tokens += len(project_overview) // 4

        return EnterpriseContext(
            facts=routing_result.facts,
            causal_summary=causal_summary,
            project_overview=project_overview,
            total_tokens=total_tokens,
            discovery_performed=self.orchestrator.last_discovery_performed,
            suggestions=suggestions,
        )

    def _get_causal_summary(self, query: str) -> str:
        """Get relevant causal chain summary."""
        try:
            chain = self.causal_tracker.query_chain(query, max_depth=3)
            if chain:
                return self.causal_tracker.format_chain_summary(chain)
        except Exception as e:
            logger.debug(f"Could not get causal chain: {e}")

        return ""

    def _get_project_overview(self) -> str:
        """Get project overview from L0 facts."""
        l0_facts = self.store.get_facts_by_level(MemoryLevel.L0_PROJECT)

        # Filter out fingerprint
        l0_facts = [
            f for f in l0_facts
            if not f.content.startswith("__FINGERPRINT__:")
        ]

        if l0_facts:
            return l0_facts[0].content

        return ""

    def _build_suggestions(self) -> List[Suggestion]:
        """Build suggestions for user."""
        suggestions = []

        # Check if git hooks installed
        git_dir = self.orchestrator.project_root / ".git"
        if git_dir.exists():
            hook_path = git_dir / "hooks" / "post-commit"
            if not hook_path.exists():
                suggestions.append(
                    Suggestion(
                        type="install_git_hook",
                        message="Install git hook for auto-extract",
                        command="rlm_install_git_hooks()",
                        priority="medium",
                    )
                )

        # Check if embeddings need indexing
        stats = self.store.get_stats()
        if stats["total_facts"] > 0 and stats["with_embeddings"] == 0:
            suggestions.append(
                Suggestion(
                    type="index_embeddings",
                    message="Index facts with embeddings for better routing",
                    command="rlm_index_embeddings()",
                    priority="high",
                )
            )

        return suggestions
