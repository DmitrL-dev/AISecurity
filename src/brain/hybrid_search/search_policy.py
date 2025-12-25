"""
Hybrid Search Policy — Multi-stage selection strategy.

Combines AIDE ML greedy search with AI-Scientist multi-stage pipeline.
Part of SENTINEL Hybrid Search Agent.
"""

import logging
import random
from typing import Optional, Literal

from .node import SearchNode
from .journal import SearchJournal
from .config import HybridConfig

logger = logging.getLogger("hybrid_search")

StageType = Literal["explore", "exploit", "polish"]


class HybridSearchPolicy:
    """
    Hybrid search policy combining AIDE ML and AI-Scientist approaches.

    Stages:
    1. AIDE: Generate initial drafts (num_drafts)
    2. AI-Scientist: Multi-stage pipeline
       - explore: Random selection from top-K (diversity)
       - exploit: Greedy selection (focus on best)
       - polish: Best-only selection (refinement)
    3. AI-Scientist: VLM-guided selection (optional)
    4. AI-Scientist: Ablation studies (probabilistic)
    5. AIDE: Probabilistic debugging
    """

    def __init__(self, config: HybridConfig):
        """
        Initialize the search policy.

        Args:
            config: Hybrid search configuration
        """
        self.config = config
        self.current_stage: StageType = "explore"
        self.step_count = 0

        # Calculate stage boundaries
        self.explore_end = int(config.max_steps * config.explore_fraction)
        self.exploit_end = self.explore_end + int(
            config.max_steps * config.exploit_fraction
        )

    def select(self, journal: SearchJournal) -> Optional[SearchNode]:
        """
        Select the next node to work on.

        Args:
            journal: The search journal with all nodes

        Returns:
            Node to improve/debug, or None to create a new draft
        """
        self.step_count += 1
        self._update_stage()

        # ============================================
        # Stage 1: AIDE - Initial Drafts
        # ============================================
        if len(journal.draft_nodes) < self.config.num_drafts:
            logger.debug(
                f"[policy] Drafting new node ({len(journal.draft_nodes)}/{self.config.num_drafts})"
            )
            return None

        # ============================================
        # Stage 2: AI-Scientist - Multi-Stage Pipeline
        # ============================================
        if self.current_stage == "explore":
            # Random selection from top-K for diversity
            top_k = journal.get_top_nodes(k=self.config.top_k)
            if top_k:
                selected = random.choice(top_k)
                logger.debug(
                    f"[policy] Explore: random from top-{len(top_k)}, selected {selected.id[:8]}"
                )
                return selected

        elif self.current_stage == "polish":
            # Best-only selection for final refinement
            best = journal.get_best_node()
            if best:
                logger.debug(f"[policy] Polish: best node {best.id[:8]}")
                return best

        # ============================================
        # Stage 3: AI-Scientist - VLM Feedback (optional)
        # ============================================
        if self.config.vlm_enabled:
            vlm_node = self._vlm_select(journal)
            if vlm_node:
                logger.debug(f"[policy] VLM-guided: {vlm_node.id[:8]}")
                return vlm_node

        # ============================================
        # Stage 4: AI-Scientist - Ablation (probabilistic)
        # ============================================
        if self.config.ablation_enabled and random.random() < self.config.ablation_prob:
            ablation_node = self._ablation_select(journal)
            if ablation_node:
                logger.debug(f"[policy] Ablation study for {ablation_node.id[:8]}")
                return ablation_node

        # ============================================
        # Stage 5: AIDE - Greedy + Probabilistic Debug
        # ============================================

        # 5a. Probabilistic debugging
        if random.random() < self.config.debug_prob:
            debuggable = journal.get_debuggable_nodes(self.config.max_debug_depth)
            if debuggable:
                selected = random.choice(debuggable)
                logger.debug(
                    f"[policy] Debug: {selected.id[:8]} (depth={selected.debug_depth})"
                )
                return selected

        # 5b. Greedy selection (AIDE default)
        best = journal.get_best_node()
        if best:
            logger.debug(f"[policy] Greedy: {best.id[:8]} (metric={best.metric:.4f})")
            return best

        # Fallback: new draft
        logger.debug("[policy] Fallback: new draft")
        return None

    def _update_stage(self) -> None:
        """Update current stage based on step count."""
        if self.step_count <= self.explore_end:
            new_stage: StageType = "explore"
        elif self.step_count <= self.exploit_end:
            new_stage = "exploit"
        else:
            new_stage = "polish"

        if new_stage != self.current_stage:
            logger.info(
                f"[policy] Stage transition: {self.current_stage} -> {new_stage}"
            )
            self.current_stage = new_stage

    def _vlm_select(self, journal: SearchJournal) -> Optional[SearchNode]:
        """
        Select node using VLM guidance for visual attacks.

        Prioritizes nodes with images that haven't been VLM-analyzed yet.
        """
        candidates = [
            n for n in journal.good_nodes if n.image_path and n.vlm_score is None
        ]

        if candidates:
            # Select node with highest base metric for VLM analysis
            return max(candidates, key=lambda n: n.metric)

        return None

    def _ablation_select(self, journal: SearchJournal) -> Optional[SearchNode]:
        """
        Select node for ablation study.

        Returns best node for ablation experiment.
        """
        return journal.get_best_node()

    def reset(self) -> None:
        """Reset policy state for a new search."""
        self.step_count = 0
        self.current_stage = "explore"
        logger.debug("[policy] Reset to initial state")
