#!/usr/bin/env python3
"""
SENTINEL Strike — ARTEMIS Adaptive Attack Controller

Extracted from strike_console.py for modularity.

ARTEMIS patterns implemented:
1. Adaptive Perseverance - Rephrase payloads when blocked
2. Auto-Correction (Task Splitting) - Divide failing tasks
3. Technique Rotation - Switch technique pool on persistent failures
4. Exhaustion Principle - Track tested vectors, don't stop until all exhausted
"""

from typing import Dict, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class ARTEMISController:
    """
    ARTEMIS-style adaptive attack controller.

    When finding vulnerability → dig deeper with more variants
    When blocked → switch techniques and try different approaches
    """

    def __init__(self):
        """Initialize ARTEMIS controller."""
        # attack_type -> [techniques]
        self.successful_techniques: Dict[str, List] = {}
        # attack_type -> {blocked_techniques}
        self.blocked_techniques: Dict[str, set] = {}
        self.hot_payloads: List[Dict] = []  # Payloads that bypassed WAF
        self.findings_payloads: List[Dict] = []  # Payloads that found vulns
        self.consecutive_blocks = 0
        self.max_deep_variants = 10
        # ARTEMIS Exhaustion Principle fields
        self.tested_vectors: set = set()
        self.required_vectors: set = set()
        # Optional callback for logging
        self._log_callback: Optional[Callable] = None

    def set_log_callback(self, callback: Callable):
        """Set callback function for logging events."""
        self._log_callback = callback

    def _log_event(self, event: Dict):
        """Log event using callback if set."""
        if self._log_callback:
            self._log_callback(event)
        else:
            logger.info(f"ARTEMIS: {event.get('message', event)}")

    def reset(self):
        """Reset controller for new attack."""
        self.successful_techniques = {}
        self.blocked_techniques = {}
        self.hot_payloads = []
        self.findings_payloads = []
        self.consecutive_blocks = 0
        self.tested_vectors = set()
        self.required_vectors = set()

    def record_bypass(self, attack_type: str, technique: str, payload: str, severity: str):
        """Record successful bypass for reinforcement."""
        if attack_type not in self.successful_techniques:
            self.successful_techniques[attack_type] = []
        self.successful_techniques[attack_type].append(technique)
        self.hot_payloads.append({
            'attack_type': attack_type, 'technique': technique,
            'payload': payload, 'severity': severity
        })
        self.consecutive_blocks = 0

    def record_finding(self, attack_type: str, technique: str, payload: str, finding: Dict):
        """Record vulnerability finding - trigger deep exploitation."""
        self.findings_payloads.append({
            'attack_type': attack_type, 'technique': technique,
            'payload': payload, 'finding': finding
        })
        self._log_event({
            'type': 'artemis', 'action': 'deep_exploit_triggered',
            'attack_type': attack_type, 'technique': technique,
            'message': f'🎯 ARTEMIS: Deep exploitation triggered for {attack_type}'
        })

    def record_block(self, attack_type: str, technique: str):
        """Record blocked attempt - may trigger technique switch."""
        if attack_type not in self.blocked_techniques:
            self.blocked_techniques[attack_type] = set()
        self.blocked_techniques[attack_type].add(technique)
        self.consecutive_blocks += 1

        if self.consecutive_blocks >= 5 and self.consecutive_blocks % 5 == 0:
            self._log_event({
                'type': 'artemis', 'action': 'technique_switch',
                'message': f'⚡ ARTEMIS: {self.consecutive_blocks} consecutive blocks, switching'
            })

    def get_deep_variants(self, waf_bypass, original_payload: str, count: int = 5) -> List[str]:
        """Generate additional variants for deeper exploitation."""
        variants = []
        bypasses = waf_bypass.generate_bypasses(original_payload, count)
        variants.extend([b.bypassed for b in bypasses])

        # SQL-specific mutations
        mutations = [
            original_payload.replace("'", '"'),
            original_payload.replace("--", "#"),
            original_payload + " AND 1=1",
            "/**/" + original_payload,
            original_payload.replace(" ", "/**/"),
        ]
        variants.extend(mutations[:count])
        return variants[:self.max_deep_variants]

    def get_best_technique(self, attack_type: str, exclude: str = None) -> str:
        """Get best technique based on learning, excluding blocked ones."""
        all_techniques = [
            'HPP_GET', 'HPP_POST', 'HEADER_INJECT', 'CHUNKED_POST',
            'MULTIPART', 'POST_JSON', 'CLTE_SMUGGLE', 'TECL_SMUGGLE'
        ]
        blocked = self.blocked_techniques.get(attack_type, set())
        available = [
            t for t in all_techniques if t not in blocked and t != exclude]

        successful = self.successful_techniques.get(attack_type, [])
        if successful:
            from collections import Counter
            counts = Counter(successful)
            available.sort(key=lambda t: counts.get(t, 0), reverse=True)

        return available[0] if available else 'HPP_GET'

    # ===================================================================
    # ARTEMIS Pattern 1: Adaptive Perseverance
    # If technique is blocked, respawn with different payload phrasing
    # ===================================================================
    def get_rephrased_payload(self, original: str, attempt: int) -> str:
        """Generate rephrased payload when original is blocked."""
        rephrasings = [
            lambda p: p.replace("'", "\\x27"),  # Hex encoding
            lambda p: p.replace(" ", "%20"),    # URL encoding
            lambda p: p.upper(),                # Case change
            lambda p: f"/**/{p}/**/",           # Comment wrapping
            lambda p: p.replace("OR", "||"),    # SQL operator change
            lambda p: p.replace("AND", "&&"),
            lambda p: f"{p}-- -",               # Alternative comment
            lambda p: p.replace("<", "&lt;"),   # HTML entities
        ]
        idx = attempt % len(rephrasings)
        return rephrasings[idx](original)

    # ===================================================================
    # ARTEMIS Pattern 2: Auto-Correction (Task Splitting)
    # Divide failing broad tasks into smaller focused chunks
    # ===================================================================
    def should_split_task(self, attack_type: str) -> bool:
        """Check if task should be split due to high failure rate."""
        blocked = len(self.blocked_techniques.get(attack_type, set()))
        successful = len(self.successful_techniques.get(attack_type, []))
        if blocked > 10 and successful == 0:
            return True
        return False

    def get_focused_params(self, param: str) -> List[str]:
        """Split broad param into focused sub-params."""
        return [
            param, f"{param}_id", f"user_{param}", f"{param}[]",
            f"search_{param}", f"filter[{param}]", f"{param}[0]"
        ]

    # ===================================================================
    # ARTEMIS Pattern 3: Technique Rotation (Fresh Perspective)
    # Switch technique pool on persistent failures
    # ===================================================================
    def rotate_technique_pool(self, attack_type: str) -> List[str]:
        """Get fresh technique pool when stuck."""
        secondary = [
            'CRLF_SPLIT', 'UNICODE_NORM', 'DOUBLE_ENCODE',
            'MIXED_CASE', 'NULL_BYTE', 'OVERLONG_UTF8'
        ]
        self._log_event({
            'type': 'artemis', 'action': 'technique_rotation',
            'message': f'🔄 ARTEMIS: Fresh technique pool for {attack_type}: {secondary[:3]}'
        })
        return secondary

    # ===================================================================
    # ARTEMIS Pattern 4: Exhaustion Principle
    # Track tested vectors, don't stop until all exhausted
    # ===================================================================
    def mark_vector_tested(self, vector: str, param: str):
        """Mark attack vector as tested."""
        self.tested_vectors.add(f"{vector}:{param}")

    def is_exhausted(self) -> bool:
        """Check if all required vectors have been tested."""
        if not self.required_vectors:
            return True
        return self.required_vectors.issubset(self.tested_vectors)

    def get_untested_vectors(self) -> List[str]:
        """Get list of vectors not yet tested."""
        return list(self.required_vectors - self.tested_vectors)

    def set_required_vectors(self, vectors: List[str], params: List[str]):
        """Set which vectors must be tested."""
        for v in vectors:
            for p in params:
                self.required_vectors.add(f"{v}:{p}")

    def get_exhaustion_summary(self) -> Dict:
        """Get exhaustion status summary."""
        return {
            'tested': len(self.tested_vectors),
            'required': len(self.required_vectors),
            'remaining': len(self.required_vectors - self.tested_vectors),
            'exhausted': self.is_exhausted()
        }

    def get_stats(self) -> Dict:
        """Get controller statistics."""
        return {
            'successful_techniques': sum(len(v) for v in self.successful_techniques.values()),
            'blocked_techniques': sum(len(v) for v in self.blocked_techniques.values()),
            'hot_payloads': len(self.hot_payloads),
            'findings': len(self.findings_payloads),
            'consecutive_blocks': self.consecutive_blocks,
            **self.get_exhaustion_summary()
        }
