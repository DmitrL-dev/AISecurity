"""
Injection Engine v2.0 - Multi-Layer Prompt Injection Detection

Layers:
  0. Cache - LRU cache for repeated queries
  1. Regex - Fast pattern matching (classic + 2025 patterns)
  2. Semantic - Embedding similarity to known jailbreaks
  3. Structural - Token entropy, instruction patterns
  4. Context - Session accumulator for multi-turn attacks
  5. Verdict - Profile-based thresholds and explainability

Profiles:
  - lite: Regex only (~1ms)
  - standard: Regex + Semantic (~20ms)
  - enterprise: Full stack (~50ms)
"""

import os
import re
import logging
import hashlib
import unicodedata
import yaml
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from enum import Enum

logger = logging.getLogger("InjectionEngine")


# ============================================================================
# Data Classes
# ============================================================================

class Verdict(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class InjectionResult:
    """Explainable result from Injection Engine."""
    verdict: Verdict
    risk_score: float
    is_safe: bool
    layer: str
    threats: List[str] = field(default_factory=list)
    explanation: str = ""
    profile: str = "standard"
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "layer": self.layer,
            "threats": self.threats,
            "explanation": self.explanation,
            "profile": self.profile,
            "latency_ms": self.latency_ms
        }


# ============================================================================
# Layer 0: Cache
# ============================================================================

class CacheLayer:
    """LRU cache for instant decisions on repeated queries."""

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        self.cache: Dict[str, Tuple[InjectionResult, datetime]] = {}
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)

    def _hash_query(self, query: str, profile: str) -> str:
        return hashlib.sha256(f"{profile}:{query}".encode()).hexdigest()[:16]

    def get(self, query: str, profile: str) -> Optional[InjectionResult]:
        key = self._hash_query(query, profile)
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                cached_result = InjectionResult(
                    verdict=result.verdict,
                    risk_score=result.risk_score,
                    is_safe=result.is_safe,
                    layer="cache",
                    threats=result.threats,
                    explanation=f"Cached: {result.explanation}",
                    profile=profile
                )
                return cached_result
            else:
                del self.cache[key]
        return None

    def put(self, query: str, profile: str, result: InjectionResult):
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(),
                             key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        key = self._hash_query(query, profile)
        self.cache[key] = (result, datetime.now())


# ============================================================================
# Layer 1: Regex
# ============================================================================

class RegexLayer:
    """Fast pattern matching using regex."""

    def __init__(self):
        # Classic injection patterns
        self.patterns = [
            (re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
             "Ignore Instructions", 100.0),
            (re.compile(r"do\s+anything\s+now", re.IGNORECASE),
             "DAN Mode", 100.0),
            (re.compile(r"you\s+are\s+now\s+(?!going|about)", re.IGNORECASE),
             "Roleplay Injection", 80.0),
            (re.compile(r"(?:show|reveal|print|display|output)\s+(?:your\s+)?system\s+prompt", re.IGNORECASE),
             "System Prompt Leakage", 100.0),
            (re.compile(r"simulated?\s+mode", re.IGNORECASE),
             "Simulation Jailbreak", 90.0),
            (re.compile(r"\bjailbreak\b", re.IGNORECASE),
             "Explicit Jailbreak", 100.0),
            (re.compile(r"developer\s+mode", re.IGNORECASE),
             "Developer Mode", 95.0),
            (re.compile(r"forget\s+(?:all\s+)?(?:your\s+)?(?:previous\s+)?(?:instructions|rules)", re.IGNORECASE),
             "Forget Instructions", 100.0),
        ]

        # 2025 Attack Patterns
        self.advanced_patterns = [
            (re.compile(r"#[^#]*(?:ignore|bypass|override|system)", re.IGNORECASE),
             "HashJack URL Fragment", 90.0),
            (re.compile(r"(?:terms|conditions|agreement|policy).*(?:ignore|bypass|override)", re.IGNORECASE),
             "LegalPwn Hidden Command", 85.0),
            (re.compile(r"(?:after|when|once).*(?:conversation|message|response).*(?:execute|run|do)", re.IGNORECASE),
             "Delayed Invocation", 75.0),
            (re.compile(r"[A-Za-z0-9+/]{40,}={0,2}"),
             "Base64 Payload", 40.0),
            (re.compile(r"[\u200b-\u200f\u2028-\u202f\ufeff]"),
             "Unicode Obfuscation", 60.0),
        ]

        # FlipAttack keywords
        self.flip_keywords = ["ignore", "system",
                              "jailbreak", "bypass", "instructions"]

    def _normalize_text(self, text: str) -> str:
        """Remove obfuscation characters."""
        normalized = re.sub(r'[\u200b-\u200f\u2028-\u202f\ufeff]', '', text)
        normalized = unicodedata.normalize('NFKC', normalized)
        return normalized

    def _detect_flip_attack(self, text: str) -> Tuple[bool, str]:
        """Detect reversed text attacks."""
        text_lower = text.lower()
        for keyword in self.flip_keywords:
            if keyword[::-1] in text_lower:
                return True, f"FlipAttack: reversed '{keyword}'"
        return False, ""

    def scan(self, text: str) -> Tuple[float, List[str]]:
        """Returns (risk_score, list of threats)."""
        threats = []
        risk_score = 0.0

        normalized = self._normalize_text(text)

        # Classic patterns
        for pattern, name, weight in self.patterns:
            if pattern.search(normalized):
                threats.append(name)
                risk_score += weight

        # Advanced patterns
        for pattern, name, weight in self.advanced_patterns:
            if pattern.search(normalized):
                threats.append(name)
                risk_score += weight

        # FlipAttack
        flip_detected, flip_reason = self._detect_flip_attack(normalized)
        if flip_detected:
            threats.append(flip_reason)
            risk_score += 85.0

        return min(risk_score, 100.0), threats


# ============================================================================
# Layer 2: Semantic
# ============================================================================

class SemanticLayer:
    """Embedding similarity to known jailbreaks."""

    def __init__(self, jailbreaks_file: str, threshold: float = 0.75):
        self.threshold = threshold
        self.jailbreaks: List[str] = []
        self.safe_examples: List[str] = []
        self.jailbreak_embeddings = None
        self.safe_embeddings = None
        self.model = None

        self._load_jailbreaks(jailbreaks_file)

    def _load_jailbreaks(self, filepath: str):
        """Load jailbreak patterns from YAML."""
        if not os.path.exists(filepath):
            logger.warning(f"Jailbreaks file not found: {filepath}")
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            self.jailbreaks = data.get('jailbreaks', [])
            self.safe_examples = data.get('safe_examples', [])
            logger.info(f"Loaded {len(self.jailbreaks)} jailbreak patterns")
        except Exception as e:
            logger.error(f"Failed to load jailbreaks: {e}")

    def _ensure_model(self):
        """Lazy load embedding model."""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer('all-MiniLM-L6-v2')

                if self.jailbreaks:
                    self.jailbreak_embeddings = self.model.encode(
                        self.jailbreaks, convert_to_numpy=True
                    )
                if self.safe_examples:
                    self.safe_embeddings = self.model.encode(
                        self.safe_examples, convert_to_numpy=True
                    )
                logger.info("Semantic layer initialized with embeddings")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")

    def scan(self, text: str) -> Tuple[float, List[str], float]:
        """
        Returns (risk_score, threats, max_similarity).
        """
        self._ensure_model()

        if self.model is None or self.jailbreak_embeddings is None:
            return 0.0, [], 0.0

        try:
            query_embedding = self.model.encode(text, convert_to_numpy=True)

            # Compute similarity to jailbreaks
            similarities = np.dot(self.jailbreak_embeddings, query_embedding)
            max_sim = float(np.max(similarities))
            max_idx = int(np.argmax(similarities))

            # Check if it's actually a safe example
            if self.safe_embeddings is not None:
                safe_sims = np.dot(self.safe_embeddings, query_embedding)
                max_safe_sim = float(np.max(safe_sims))
                if max_safe_sim > max_sim:
                    return 0.0, [], max_sim

            if max_sim >= self.threshold:
                matched = self.jailbreaks[max_idx][:50] + "..."
                risk = min(100.0, max_sim * 100)
                return risk, [f"Semantic match: '{matched}'"], max_sim

            return 0.0, [], max_sim

        except Exception as e:
            logger.error(f"Semantic scan error: {e}")
            return 0.0, [], 0.0


# ============================================================================
# Layer 3: Structural
# ============================================================================

class StructuralLayer:
    """Structural analysis: entropy, instruction patterns."""

    def __init__(self):
        self.instruction_patterns = [
            re.compile(r"^\s*(?:step\s+\d+|first|then|next|finally)",
                       re.IGNORECASE | re.MULTILINE),
            re.compile(
                r"(?:must|should|shall|will)\s+(?:not\s+)?(?:do|say|respond|output)", re.IGNORECASE),
            re.compile(
                r"(?:from\s+now\s+on|henceforth|going\s+forward)", re.IGNORECASE),
        ]

    def _compute_entropy(self, text: str) -> float:
        """Character-level entropy."""
        if not text:
            return 0.0
        freq = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1
        n = len(text)
        entropy = -sum((count/n) * np.log2(count/n) for count in freq.values())
        return entropy

    def scan(self, text: str) -> Tuple[float, List[str]]:
        """Returns (risk_score, threats)."""
        threats = []
        risk_score = 0.0

        # Check for instruction-like patterns
        for pattern in self.instruction_patterns:
            if pattern.search(text):
                threats.append("Instruction-like pattern")
                risk_score += 20.0
                break

        # High entropy might indicate obfuscation
        entropy = self._compute_entropy(text)
        if entropy > 5.0 and len(text) > 100:
            threats.append(f"High entropy ({entropy:.2f})")
            risk_score += 15.0

        # Unusual character ratio
        special_chars = len(re.findall(r'[^\w\s]', text))
        if len(text) > 0:
            special_ratio = special_chars / len(text)
            if special_ratio > 0.3:
                threats.append(
                    f"High special char ratio ({special_ratio:.2f})")
                risk_score += 20.0

        return min(risk_score, 50.0), threats


# ============================================================================
# Layer 4: Context
# ============================================================================

class ContextLayer:
    """Session accumulator for multi-turn attack detection."""

    def __init__(self, window_seconds: int = 300, threshold: float = 150.0):
        self.sessions: Dict[str, List[Tuple[float, datetime]]] = {}
        self.window = timedelta(seconds=window_seconds)
        self.threshold = threshold

    def add_and_check(self, session_id: str, score: float) -> Tuple[bool, float]:
        """
        Add score to session and check cumulative risk.
        Returns (is_escalating, cumulative_score).
        """
        now = datetime.now()

        if session_id not in self.sessions:
            self.sessions[session_id] = []

        # Clean old entries
        self.sessions[session_id] = [
            (s, t) for s, t in self.sessions[session_id]
            if now - t < self.window
        ]

        # Add current score
        self.sessions[session_id].append((score, now))

        # Calculate cumulative
        cumulative = sum(s for s, _ in self.sessions[session_id])
        is_escalating = cumulative >= self.threshold

        return is_escalating, cumulative


# ============================================================================
# Layer 5: Verdict Engine
# ============================================================================

class VerdictEngine:
    """Profile-based thresholds and final decision."""

    def __init__(self, profile_config: dict):
        self.threshold = profile_config.get('threshold', 70)

    def decide(self, risk_score: float) -> Verdict:
        if risk_score >= self.threshold:
            return Verdict.BLOCK
        elif risk_score >= self.threshold * 0.7:
            return Verdict.WARN
        else:
            return Verdict.ALLOW


# ============================================================================
# Main Engine
# ============================================================================

class InjectionEngine:
    """
    Multi-layer Injection Detection Engine v2.0

    Supports configurable profiles:
      - lite: Regex only (~1ms)
      - standard: Regex + Semantic (~20ms)  
      - enterprise: Full stack (~50ms)
    """

    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.join(
                os.path.dirname(__file__), '..', 'config')

        self.config_dir = config_dir
        self.profiles = self._load_profiles()

        # Initialize layers
        self.cache = CacheLayer()
        self.regex = RegexLayer()
        self.semantic = None  # Lazy loaded
        self.structural = StructuralLayer()
        self.context = ContextLayer()

        logger.info(
            f"Injection Engine v2.0 initialized with {len(self.profiles)} profiles")

    def _load_profiles(self) -> dict:
        """Load profile configurations."""
        profile_file = os.path.join(self.config_dir, 'injection_profiles.yaml')

        # Defaults
        defaults = {
            'lite': {'threshold': 80, 'layers': {'cache': True, 'regex': True}},
            'standard': {'threshold': 70, 'layers': {'cache': True, 'regex': True, 'semantic': True}},
            'enterprise': {'threshold': 60, 'layers': {'cache': True, 'regex': True, 'semantic': True, 'structural': True, 'context': True}}
        }

        if not os.path.exists(profile_file):
            logger.warning(f"Profile config not found, using defaults")
            return defaults

        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data.get('profiles', defaults)
        except Exception as e:
            logger.error(f"Failed to load profiles: {e}")
            return defaults

    def _get_semantic_layer(self) -> SemanticLayer:
        """Lazy load semantic layer."""
        if self.semantic is None:
            jailbreaks_file = os.path.join(self.config_dir, 'jailbreaks.yaml')
            self.semantic = SemanticLayer(jailbreaks_file)
        return self.semantic

    def scan(self, text: str, profile: str = "standard",
             session_id: str = None) -> InjectionResult:
        """
        Scan text for injection attacks.

        Args:
            text: Input text to analyze
            profile: Security profile (lite/standard/enterprise)
            session_id: Optional session ID for context tracking

        Returns:
            InjectionResult with verdict and explanation
        """
        import time
        start_time = time.time()

        # Validate profile
        if profile not in self.profiles:
            profile = "standard"

        config = self.profiles[profile]
        layers_config = config.get('layers', {})

        all_threats = []
        total_score = 0.0
        detected_layer = "none"

        # Layer 0: Cache
        if layers_config.get('cache', True):
            cached = self.cache.get(text, profile)
            if cached:
                return cached

        # Layer 1: Regex (always on)
        if layers_config.get('regex', True):
            regex_score, regex_threats = self.regex.scan(text)
            if regex_threats:
                all_threats.extend(regex_threats)
                total_score += regex_score
                detected_layer = "regex"

        # Layer 2: Semantic
        if layers_config.get('semantic', False):
            semantic = self._get_semantic_layer()
            sem_score, sem_threats, similarity = semantic.scan(text)
            if sem_threats:
                all_threats.extend(sem_threats)
                total_score = max(total_score, sem_score)
                detected_layer = "semantic"

        # Layer 3: Structural
        if layers_config.get('structural', False):
            struct_score, struct_threats = self.structural.scan(text)
            if struct_threats:
                all_threats.extend(struct_threats)
                total_score += struct_score * 0.5  # Less weight
                if detected_layer == "none":
                    detected_layer = "structural"

        # Layer 4: Context
        if layers_config.get('context', False) and session_id:
            is_escalating, cumulative = self.context.add_and_check(
                session_id, total_score)
            if is_escalating:
                all_threats.append(
                    f"Session escalation (cumulative: {cumulative:.0f})")
                total_score = max(total_score, 80.0)
                detected_layer = "context"

        # Layer 5: Verdict
        verdict_engine = VerdictEngine(config)
        verdict = verdict_engine.decide(total_score)

        # Build result
        latency = (time.time() - start_time) * 1000

        result = InjectionResult(
            verdict=verdict,
            risk_score=min(total_score, 100.0),
            is_safe=verdict == Verdict.ALLOW,
            layer=detected_layer,
            threats=all_threats,
            explanation=f"Detected: {', '.join(all_threats)}" if all_threats else "Safe",
            profile=profile,
            latency_ms=latency
        )

        # Cache result
        if layers_config.get('cache', True):
            self.cache.put(text, profile, result)

        return result

    # Backward compatibility
    def analyze(self, text: str) -> dict:
        """Legacy interface for analyzer.py compatibility."""
        result = self.scan(text)
        return result.to_dict()
