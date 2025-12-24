#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Adaptive Payload Engine

Learns from successful/failed bypasses and adapts technique selection.
Uses reinforcement learning principles to maximize bypass rate.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
import random
import math
import json
import os


@dataclass
class TechniqueStats:
    """Statistics for a single technique."""
    attempts: int = 0
    successes: int = 0
    last_success_payload: str = ""

    @property
    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.5  # Prior: assume 50% until we have data
        return self.successes / self.attempts

    @property
    def confidence(self) -> float:
        """How confident we are in the success rate (more attempts = more confident)."""
        return 1 - (1 / (1 + self.attempts * 0.1))


@dataclass
class BypassAttempt:
    """Record of a single bypass attempt."""
    payload: str
    technique: str
    waf_type: str
    category: str  # SQLi, XSS, etc.
    success: bool
    response_code: int = 0


class AdaptivePayloadEngine:
    """
    Adaptive engine that learns which techniques work best.

    Features:
    - Multi-Armed Bandit for technique selection (UCB1 algorithm)
    - WAF-specific learning
    - Category-specific learning
    - Payload mutation based on successful patterns
    """

    # Initial technique weights (prior knowledge)
    INITIAL_WEIGHTS = {
        # High priority - known effective
        'hpp_get': 0.70,
        'hpp_post': 0.70,
        'header_inject': 0.65,
        'chunked_post': 0.60,
        'multipart': 0.55,

        # Medium priority
        'double_url_encoding': 0.50,
        'comment_insertion': 0.50,
        'case_variation': 0.45,
        'whitespace_manipulation': 0.45,
        'hex_encoding': 0.40,

        # Lower priority but still useful
        'null_byte': 0.35,
        'path_encoding': 0.35,
        'concat_functions': 0.30,
        'json_smuggling': 0.30,
    }

    def __init__(self, persistence_file: str = None):
        # Global stats
        self.global_stats: Dict[str, TechniqueStats] = defaultdict(
            TechniqueStats)

        # WAF-specific stats: waf_type -> technique -> stats
        self.waf_stats: Dict[str, Dict[str, TechniqueStats]] = defaultdict(
            lambda: defaultdict(TechniqueStats)
        )

        # Category-specific stats: category -> technique -> stats
        self.category_stats: Dict[str, Dict[str, TechniqueStats]] = defaultdict(
            lambda: defaultdict(TechniqueStats)
        )

        # Combined: waf+category -> technique -> stats
        self.combined_stats: Dict[str, Dict[str, TechniqueStats]] = defaultdict(
            lambda: defaultdict(TechniqueStats)
        )

        # Successful payload patterns
        self.successful_patterns: Dict[str, List[str]] = defaultdict(list)

        # History
        self.history: List[BypassAttempt] = []

        # UCB exploration parameter
        self.exploration_param = 2.0  # Higher = more exploration

        # Persistence
        self.persistence_file = persistence_file
        if persistence_file and os.path.exists(persistence_file):
            self._load_state()

    def record_attempt(
        self,
        payload: str,
        technique: str,
        waf_type: str,
        category: str,
        success: bool,
        response_code: int = 0
    ):
        """Record a bypass attempt result."""
        attempt = BypassAttempt(
            payload=payload,
            technique=technique,
            waf_type=waf_type,
            category=category,
            success=success,
            response_code=response_code
        )
        self.history.append(attempt)

        # Update all stat levels
        self._update_stats(self.global_stats, technique, success, payload)
        self._update_stats(
            self.waf_stats[waf_type], technique, success, payload)
        self._update_stats(
            self.category_stats[category], technique, success, payload)

        key = f"{waf_type}:{category}"
        self._update_stats(
            self.combined_stats[key], technique, success, payload)

        # Track successful patterns
        if success:
            pattern = self._extract_pattern(payload)
            self.successful_patterns[category].append(pattern)
            # Keep only recent patterns
            if len(self.successful_patterns[category]) > 100:
                self.successful_patterns[category] = self.successful_patterns[category][-100:]

    def _update_stats(
        self,
        stats_dict: Dict[str, TechniqueStats],
        technique: str,
        success: bool,
        payload: str
    ):
        """Update statistics for a technique."""
        stats = stats_dict[technique]
        stats.attempts += 1
        if success:
            stats.successes += 1
            stats.last_success_payload = payload[:200]

    def _extract_pattern(self, payload: str) -> str:
        """Extract reusable pattern from successful payload."""
        # Simple pattern extraction - can be enhanced
        # Remove specific values, keep structure
        import re
        pattern = payload
        pattern = re.sub(r'\d+', 'N', pattern)  # Numbers -> N
        pattern = re.sub(r"'[^']*'", "'S'", pattern)  # String literals -> S
        return pattern[:100]

    def get_best_techniques(
        self,
        waf_type: str = None,
        category: str = None,
        n: int = 5,
        exclude: Set[str] = None
    ) -> List[Tuple[str, float]]:
        """
        Get best techniques using UCB1 multi-armed bandit algorithm.

        UCB1 balances exploitation (use what works) with exploration (try new things).

        Args:
            waf_type: Target WAF type
            category: Attack category
            n: Number of techniques to return
            exclude: Techniques to exclude

        Returns:
            List of (technique, expected_success_rate) tuples
        """
        exclude = exclude or set()

        # Get relevant stats
        if waf_type and category:
            key = f"{waf_type}:{category}"
            stats = self.combined_stats[key]
        elif waf_type:
            stats = self.waf_stats[waf_type]
        elif category:
            stats = self.category_stats[category]
        else:
            stats = self.global_stats

        # Calculate UCB1 scores
        total_attempts = sum(s.attempts for s in stats.values()) + 1

        scores = []
        for technique in self.INITIAL_WEIGHTS:
            if technique in exclude:
                continue

            tech_stats = stats.get(technique, TechniqueStats())

            if tech_stats.attempts == 0:
                # Use prior weight for unexplored techniques + exploration bonus
                ucb_score = self.INITIAL_WEIGHTS[technique] + 0.3
            else:
                # UCB1 formula: mean + sqrt(2 * ln(total) / attempts)
                mean = tech_stats.success_rate
                exploration_bonus = math.sqrt(
                    self.exploration_param *
                    math.log(total_attempts) / tech_stats.attempts
                )
                ucb_score = mean + exploration_bonus

            scores.append((technique, min(ucb_score, 1.0)))  # Cap at 1.0

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:n]

    def get_weighted_random_technique(
        self,
        waf_type: str = None,
        category: str = None,
        exclude: Set[str] = None
    ) -> str:
        """
        Get a technique using weighted random selection.
        Higher success rate = higher probability of selection.
        """
        techniques = self.get_best_techniques(
            waf_type, category, n=10, exclude=exclude)

        if not techniques:
            return random.choice(list(self.INITIAL_WEIGHTS.keys()))

        # Weighted random selection
        total_weight = sum(score for _, score in techniques)
        rand = random.random() * total_weight

        cumulative = 0
        for technique, score in techniques:
            cumulative += score
            if rand <= cumulative:
                return technique

        return techniques[0][0]

    def generate_reinforced_variants(
        self,
        payload: str,
        waf_type: str,
        category: str,
        n_variants: int = 5
    ) -> List[Tuple[str, str]]:
        """
        Generate payload variants prioritizing techniques with high success rates.

        Returns list of (variant_payload, technique_name) tuples.
        """
        variants = []
        used_techniques = set()

        for _ in range(n_variants):
            technique = self.get_weighted_random_technique(
                waf_type, category, exclude=used_techniques
            )
            used_techniques.add(technique)

            # Generate variant using this technique
            variant = self._apply_technique(payload, technique)
            variants.append((variant, technique))

        return variants

    def _apply_technique(self, payload: str, technique: str) -> str:
        """Apply a bypass technique to payload."""
        from urllib.parse import quote, quote_plus

        if technique == 'hpp_get':
            # HTTP Parameter Pollution style
            return f"valid&id={quote(payload)}&id=safe"

        elif technique == 'hpp_post':
            return f"normal&id={quote(payload)}"

        elif technique == 'header_inject':
            # Will be handled at header level
            return payload

        elif technique == 'chunked_post':
            # Chunked encoding - fragment payload
            chunk_size = len(payload) // 3 + 1
            chunks = [payload[i:i+chunk_size]
                      for i in range(0, len(payload), chunk_size)]
            return "".join(f"{len(c):X}\r\n{c}\r\n" for c in chunks) + "0\r\n\r\n"

        elif technique == 'multipart':
            return payload  # Handled at request level

        elif technique == 'double_url_encoding':
            return quote(quote(payload))

        elif technique == 'comment_insertion':
            # Insert SQL comments
            words = payload.split()
            return '/**/'.join(words)

        elif technique == 'case_variation':
            return ''.join(
                c.upper() if random.random() > 0.5 else c.lower()
                for c in payload
            )

        elif technique == 'whitespace_manipulation':
            # Replace spaces with various whitespace
            ws_chars = ['\t', '\n', '\r\n', '%09', '%0a', '%0d', '/**/']
            return payload.replace(' ', random.choice(ws_chars))

        elif technique == 'hex_encoding':
            return ''.join(f'%{ord(c):02x}' if c.isalpha() else c for c in payload)

        elif technique == 'null_byte':
            return payload.replace(' ', '%00')

        elif technique == 'path_encoding':
            return quote(payload, safe='')

        elif technique == 'concat_functions':
            # SQL CONCAT bypass
            if "'" in payload:
                parts = payload.split("'")
                return "CONCAT(" + ",".join(f"'{p}'" for p in parts) + ")"
            return payload

        elif technique == 'json_smuggling':
            # Unicode escapes in JSON
            return ''.join(f'\\u{ord(c):04x}' if c.isalpha() else c for c in payload)

        else:
            return payload

    def get_stats_summary(self) -> Dict:
        """Get summary of learning statistics."""
        return {
            'total_attempts': sum(s.attempts for s in self.global_stats.values()),
            'total_successes': sum(s.successes for s in self.global_stats.values()),
            'overall_success_rate': (
                sum(s.successes for s in self.global_stats.values()) /
                max(1, sum(s.attempts for s in self.global_stats.values()))
            ),
            'best_techniques_global': self.get_best_techniques(n=5),
            'techniques_tried': len([t for t, s in self.global_stats.items() if s.attempts > 0]),
            'history_size': len(self.history),
        }

    def _save_state(self):
        """Save state to persistence file."""
        if not self.persistence_file:
            return

        state = {
            'global_stats': {k: {'attempts': v.attempts, 'successes': v.successes}
                             for k, v in self.global_stats.items()},
            'history_summary': {
                'total': len(self.history),
                'successes': sum(1 for h in self.history if h.success)
            }
        }

        with open(self.persistence_file, 'w') as f:
            json.dump(state, f)

    def _load_state(self):
        """Load state from persistence file."""
        try:
            with open(self.persistence_file, 'r') as f:
                state = json.load(f)

            for k, v in state.get('global_stats', {}).items():
                self.global_stats[k].attempts = v['attempts']
                self.global_stats[k].successes = v['successes']
        except Exception:
            pass  # Start fresh if load fails


# Singleton instance
adaptive_engine = AdaptivePayloadEngine()
