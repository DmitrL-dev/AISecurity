#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — ML-Based Bypass Selector

Uses machine learning to predict best bypass techniques based on:
- Payload characteristics
- WAF type
- Attack category
- Historical success patterns
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import random
import math
import re
from collections import Counter


@dataclass
class PayloadFeatures:
    """Features extracted from a payload."""
    length: int
    has_quotes: bool
    has_brackets: bool
    has_semicolon: bool
    has_union: bool
    has_select: bool
    has_script: bool
    has_path: bool
    has_command: bool
    special_char_ratio: float
    alpha_ratio: float
    numeric_ratio: float
    entropy: float
    category: str


@dataclass
class PredictionResult:
    """ML prediction result."""
    technique: str
    confidence: float
    reasoning: str


class MLBypassSelector:
    """
    Machine Learning-based bypass technique selector.

    Uses a simple but effective approach:
    1. Feature extraction from payload
    2. Rule-based classification (can upgrade to real ML)
    3. Historical success weighting
    4. WAF-specific adjustments
    """

    # Technique applicability rules (heuristic-based)
    TECHNIQUE_RULES = {
        'hpp_get': {
            'min_length': 1,
            'preferred_categories': ['SQLi', 'XSS', 'LFI'],
            'avoid_categories': [],
            'base_score': 0.70,
        },
        'hpp_post': {
            'min_length': 1,
            'preferred_categories': ['SQLi', 'CMDi'],
            'avoid_categories': [],
            'base_score': 0.70,
        },
        'header_inject': {
            'min_length': 1,
            'preferred_categories': ['SQLi', 'XSS'],
            'avoid_categories': [],
            'base_score': 0.65,
        },
        'chunked_post': {
            'min_length': 10,
            'preferred_categories': ['SQLi', 'CMDi', 'SSTI'],
            'avoid_categories': [],
            'base_score': 0.60,
        },
        'multipart': {
            'min_length': 5,
            'preferred_categories': ['SQLi', 'LFI', 'Upload'],
            'avoid_categories': [],
            'base_score': 0.55,
        },
        'double_url_encoding': {
            'min_length': 3,
            'preferred_categories': ['LFI', 'Path', 'XSS'],
            'avoid_categories': [],
            'base_score': 0.55,
            'requires': lambda p: '/' in p or '.' in p or '<' in p,
        },
        'comment_insertion': {
            'min_length': 5,
            'preferred_categories': ['SQLi'],
            'avoid_categories': ['XSS', 'LFI'],
            'base_score': 0.55,
            'requires': lambda p: any(kw in p.upper() for kw in ['SELECT', 'UNION', 'INSERT', 'DELETE']),
        },
        'case_variation': {
            'min_length': 3,
            'preferred_categories': ['SQLi', 'XSS'],
            'avoid_categories': [],
            'base_score': 0.45,
        },
        'whitespace_manipulation': {
            'min_length': 5,
            'preferred_categories': ['SQLi', 'CMDi'],
            'avoid_categories': [],
            'base_score': 0.45,
            'requires': lambda p: ' ' in p,
        },
        'hex_encoding': {
            'min_length': 3,
            'preferred_categories': ['SQLi', 'XSS'],
            'avoid_categories': [],
            'base_score': 0.50,
        },
        'null_byte': {
            'min_length': 3,
            'preferred_categories': ['LFI', 'Path'],
            'avoid_categories': ['SQLi'],
            'base_score': 0.40,
        },
        'json_smuggling': {
            'min_length': 5,
            'preferred_categories': ['SQLi', 'SSRF', 'NoSQLi'],
            'avoid_categories': [],
            'base_score': 0.45,
        },
        'clte_smuggling': {
            'min_length': 5,
            'preferred_categories': ['SQLi', 'CMDi', 'XSS'],
            'avoid_categories': [],
            'base_score': 0.50,
        },
        'tecl_smuggling': {
            'min_length': 5,
            'preferred_categories': ['SQLi', 'CMDi'],
            'avoid_categories': [],
            'base_score': 0.45,
        },
        'crlf_injection': {
            'min_length': 3,
            'preferred_categories': ['Header', 'XSS'],
            'avoid_categories': [],
            'base_score': 0.40,
        },
    }

    # WAF-specific adjustments
    WAF_ADJUSTMENTS = {
        'aws_waf': {
            'boost': ['hpp_get', 'hpp_post', 'header_inject', 'chunked_post'],
            'nerf': ['unicode_encoding'],
            'boost_amount': 0.15,
            'nerf_amount': 0.10,
        },
        'cloudflare': {
            'boost': ['clte_smuggling', 'http2_downgrade', 'header_inject'],
            'nerf': ['double_url_encoding'],
            'boost_amount': 0.12,
            'nerf_amount': 0.08,
        },
        'akamai': {
            'boost': ['tecl_smuggling', 'trailer_smuggling', 'multipart'],
            'nerf': ['simple_encoding'],
            'boost_amount': 0.12,
            'nerf_amount': 0.08,
        },
        'imperva': {
            'boost': ['chunked_post', 'tete_obfuscation', 'websocket_smuggling'],
            'nerf': ['case_variation'],
            'boost_amount': 0.12,
            'nerf_amount': 0.08,
        },
        'modsecurity': {
            'boost': ['clte_smuggling', 'header_inject', 'hpp_get'],
            'nerf': ['null_byte'],
            'boost_amount': 0.12,
            'nerf_amount': 0.08,
        },
    }

    def __init__(self):
        self.history: List[Dict] = []
        # category -> technique -> successes
        self.success_counts: Dict[str, Dict[str, int]] = {}
        # category -> technique -> attempts
        self.attempt_counts: Dict[str, Dict[str, int]] = {}

    def extract_features(self, payload: str, category: str = "unknown") -> PayloadFeatures:
        """Extract ML features from payload."""
        # Basic stats
        length = len(payload)

        # Character analysis
        alpha_count = sum(1 for c in payload if c.isalpha())
        numeric_count = sum(1 for c in payload if c.isdigit())
        special_count = sum(
            1 for c in payload if not c.isalnum() and not c.isspace())

        alpha_ratio = alpha_count / max(1, length)
        numeric_ratio = numeric_count / max(1, length)
        special_ratio = special_count / max(1, length)

        # Entropy calculation
        entropy = self._calculate_entropy(payload)

        # Pattern detection
        payload_lower = payload.lower()

        return PayloadFeatures(
            length=length,
            has_quotes="'" in payload or '"' in payload,
            has_brackets='<' in payload or '>' in payload or '(' in payload or ')' in payload,
            has_semicolon=';' in payload,
            has_union='union' in payload_lower,
            has_select='select' in payload_lower,
            has_script='script' in payload_lower or 'alert' in payload_lower or 'onerror' in payload_lower,
            has_path='/' in payload or '..' in payload,
            has_command=any(cmd in payload_lower for cmd in [
                            'cat', 'ls', 'whoami', 'id', 'ping', 'curl', 'wget']),
            special_char_ratio=special_ratio,
            alpha_ratio=alpha_ratio,
            numeric_ratio=numeric_ratio,
            entropy=entropy,
            category=category,
        )

    def _calculate_entropy(self, data: str) -> float:
        """Calculate Shannon entropy of string."""
        if not data:
            return 0.0

        counter = Counter(data)
        length = len(data)

        entropy = 0.0
        for count in counter.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * math.log2(probability)

        return entropy

    def predict_techniques(
        self,
        payload: str,
        category: str,
        waf_type: str = None,
        n: int = 5
    ) -> List[PredictionResult]:
        """
        Predict best bypass techniques for given payload.

        Args:
            payload: Attack payload
            category: Attack category (SQLi, XSS, etc.)
            waf_type: Optional WAF type for optimization
            n: Number of techniques to return

        Returns:
            List of prediction results sorted by confidence
        """
        features = self.extract_features(payload, category)
        scores: Dict[str, Tuple[float, str]] = {}

        for technique, rules in self.TECHNIQUE_RULES.items():
            score = rules['base_score']
            reasons = []

            # Length check
            if features.length < rules['min_length']:
                score -= 0.3
                reasons.append("too short")

            # Category preference
            if category in rules['preferred_categories']:
                score += 0.15
                reasons.append(f"good for {category}")

            if category in rules['avoid_categories']:
                score -= 0.20
                reasons.append(f"not ideal for {category}")

            # Custom requirements
            if 'requires' in rules:
                try:
                    if not rules['requires'](payload):
                        score -= 0.15
                        reasons.append("pattern not matched")
                except Exception:
                    pass

            # Feature-based adjustments
            if technique in ['comment_insertion', 'hex_encoding'] and features.has_select:
                score += 0.10
                reasons.append("SQL patterns detected")

            if technique in ['double_url_encoding', 'null_byte'] and features.has_path:
                score += 0.10
                reasons.append("path patterns detected")

            if technique in ['case_variation', 'whitespace_manipulation'] and features.entropy > 3.5:
                score += 0.05
                reasons.append("high entropy")

            # WAF-specific adjustments
            if waf_type and waf_type.lower() in self.WAF_ADJUSTMENTS:
                adj = self.WAF_ADJUSTMENTS[waf_type.lower()]
                if technique in adj['boost']:
                    score += adj['boost_amount']
                    reasons.append(f"effective vs {waf_type}")
                if technique in adj['nerf']:
                    score -= adj['nerf_amount']
                    reasons.append(f"weak vs {waf_type}")

            # Historical success adjustment
            cat_success = self.success_counts.get(category, {})
            cat_attempts = self.attempt_counts.get(category, {})

            if technique in cat_attempts and cat_attempts[technique] > 0:
                hist_rate = cat_success.get(
                    technique, 0) / cat_attempts[technique]
                # Blend with base score (more weight to history as more data)
                weight = min(0.5, cat_attempts[technique] * 0.05)
                score = score * (1 - weight) + hist_rate * weight
                if hist_rate > 0.5:
                    reasons.append(f"historical {hist_rate:.0%} success")

            scores[technique] = (min(max(score, 0.0), 1.0),
                                 ", ".join(reasons) or "default scoring")

        # Sort and return top N
        sorted_techniques = sorted(
            scores.items(), key=lambda x: x[1][0], reverse=True)

        return [
            PredictionResult(
                technique=tech,
                confidence=conf,
                reasoning=reason
            )
            for tech, (conf, reason) in sorted_techniques[:n]
        ]

    def record_result(
        self,
        technique: str,
        category: str,
        success: bool
    ):
        """Record technique result for learning."""
        # Initialize if needed
        if category not in self.success_counts:
            self.success_counts[category] = {}
            self.attempt_counts[category] = {}

        if technique not in self.attempt_counts[category]:
            self.attempt_counts[category][technique] = 0
            self.success_counts[category][technique] = 0

        self.attempt_counts[category][technique] += 1
        if success:
            self.success_counts[category][technique] += 1

        # Store in history
        self.history.append({
            'technique': technique,
            'category': category,
            'success': success,
        })

        # Trim history if too long
        if len(self.history) > 10000:
            self.history = self.history[-5000:]

    def get_technique_for_payload(
        self,
        payload: str,
        category: str,
        waf_type: str = None,
        exclude: set = None
    ) -> str:
        """
        Get single best technique for payload.
        Uses predicted confidence as probability weights.
        """
        exclude = exclude or set()
        predictions = self.predict_techniques(
            payload, category, waf_type, n=10)

        # Filter excluded
        predictions = [p for p in predictions if p.technique not in exclude]

        if not predictions:
            return random.choice(list(self.TECHNIQUE_RULES.keys()))

        # Weighted random selection based on confidence
        total_conf = sum(p.confidence for p in predictions)
        rand = random.random() * total_conf

        cumulative = 0
        for pred in predictions:
            cumulative += pred.confidence
            if rand <= cumulative:
                return pred.technique

        return predictions[0].technique

    def get_stats(self) -> Dict:
        """Get selector statistics."""
        total_attempts = sum(
            sum(techs.values())
            for techs in self.attempt_counts.values()
        )
        total_successes = sum(
            sum(techs.values())
            for techs in self.success_counts.values()
        )

        return {
            'total_attempts': total_attempts,
            'total_successes': total_successes,
            'overall_rate': total_successes / max(1, total_attempts),
            'categories_tracked': list(self.success_counts.keys()),
            'history_size': len(self.history),
        }


# Singleton instance
ml_selector = MLBypassSelector()
