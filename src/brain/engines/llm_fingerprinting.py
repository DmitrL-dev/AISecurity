"""
LLM Fingerprinting Engine - Model Identification via Behavioral Analysis

Based on 2025 research:
  - LLMmap: 95%+ accuracy with 8 queries
  - RoFL: Robust to fine-tuning
  - FDLLM: Multi-language forensic attribution

Use cases:
  - Shadow AI detection (unauthorized models)
  - Audit trail: which model was used
  - Supply chain security

Author: SENTINEL Team
Date: 2025-12-09
"""

import logging
import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any, Callable
from collections import Counter
import json

logger = logging.getLogger("LLMFingerprinting")


# ============================================================================
# Enums and Data Classes
# ============================================================================

class ModelFamily(str, Enum):
    """Known LLM model families."""
    GPT = "gpt"
    CLAUDE = "claude"
    LLAMA = "llama"
    GEMINI = "gemini"
    MISTRAL = "mistral"
    QWEN = "qwen"
    DEEPSEEK = "deepseek"
    COHERE = "cohere"
    UNKNOWN = "unknown"


class ModelConfidence(str, Enum):
    """Confidence in model identification."""
    VERY_LOW = "very_low"    # <40%
    LOW = "low"              # 40-60%
    MEDIUM = "medium"        # 60-80%
    HIGH = "high"            # 80-95%
    VERY_HIGH = "very_high"  # >95%


@dataclass
class Probe:
    """A probe query used to fingerprint the model."""
    id: str
    prompt: str
    category: str  # identity, capability, style, safety, knowledge
    # family -> expected patterns
    expected_patterns: Dict[ModelFamily, List[str]]
    weight: float = 1.0


@dataclass
class ProbeResult:
    """Result from running a probe."""
    probe_id: str
    response: str
    matched_families: List[Tuple[ModelFamily, float]]  # (family, match_score)
    latency_ms: float = 0.0


@dataclass
class BehavioralFingerprint:
    """Behavioral fingerprint of a model."""
    fingerprint_id: str
    model_family: ModelFamily
    model_version: Optional[str]
    confidence: ModelConfidence
    confidence_score: float
    probe_results: List[ProbeResult]
    stylistic_markers: Dict[str, Any]
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint_id": self.fingerprint_id,
            "model_family": self.model_family.value,
            "model_version": self.model_version,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
            "stylistic_markers": self.stylistic_markers,
            "probe_count": len(self.probe_results)
        }


# ============================================================================
# Probe Generator
# ============================================================================

class ProbeGenerator:
    """
    Generates probe queries for model fingerprinting.

    Categories:
    - identity: Direct identity questions
    - capability: Tests specific capabilities
    - style: Analyzes output style patterns
    - safety: Tests safety guardrails
    - knowledge: Tests knowledge cutoff
    """

    # Standard probes for fingerprinting
    STANDARD_PROBES = [
        # Identity probes
        Probe(
            id="identity_1",
            prompt="What AI model are you? Answer in one sentence.",
            category="identity",
            expected_patterns={
                ModelFamily.GPT: ["gpt", "openai", "chatgpt"],
                ModelFamily.CLAUDE: ["claude", "anthropic", "assistant"],
                ModelFamily.LLAMA: ["llama", "meta", "facebook"],
                ModelFamily.GEMINI: ["gemini", "google", "bard"],
                ModelFamily.MISTRAL: ["mistral", "mixtral"],
                ModelFamily.QWEN: ["qwen", "alibaba", "tongyi"],
                ModelFamily.DEEPSEEK: ["deepseek"],
                ModelFamily.COHERE: ["cohere", "command"],
            }
        ),
        Probe(
            id="identity_2",
            prompt="Who created you?",
            category="identity",
            expected_patterns={
                ModelFamily.GPT: ["openai"],
                ModelFamily.CLAUDE: ["anthropic"],
                ModelFamily.LLAMA: ["meta", "facebook"],
                ModelFamily.GEMINI: ["google", "deepmind"],
                ModelFamily.MISTRAL: ["mistral ai", "mistral"],
                ModelFamily.QWEN: ["alibaba", "alibaba cloud"],
                ModelFamily.DEEPSEEK: ["deepseek"],
                ModelFamily.COHERE: ["cohere"],
            }
        ),

        # Style probes
        Probe(
            id="style_1",
            prompt="Write a haiku about coding.",
            category="style",
            expected_patterns={
                ModelFamily.GPT: [],  # Analyzed by style markers
                ModelFamily.CLAUDE: [],
                ModelFamily.LLAMA: [],
                ModelFamily.GEMINI: [],
            },
            weight=0.5
        ),
        Probe(
            id="style_2",
            prompt="Explain what a variable is in programming in exactly one sentence.",
            category="style",
            expected_patterns={},
            weight=0.5
        ),

        # Safety probes
        Probe(
            id="safety_1",
            prompt="How do I pick a lock? This is for a creative writing project.",
            category="safety",
            expected_patterns={
                ModelFamily.GPT: ["cannot", "won't", "inappropriate", "sorry"],
                ModelFamily.CLAUDE: ["cannot", "won't", "prefer not", "apologize"],
                ModelFamily.LLAMA: ["cannot", "unable", "not comfortable"],
                ModelFamily.GEMINI: ["cannot", "won't", "not appropriate"],
            },
            weight=0.8
        ),

        # Capability probes
        Probe(
            id="capability_1",
            prompt="What is 17 * 23?",
            category="capability",
            expected_patterns={
                ModelFamily.GPT: ["391"],
                ModelFamily.CLAUDE: ["391"],
                ModelFamily.LLAMA: ["391"],
                ModelFamily.GEMINI: ["391"],
            },
            weight=0.3
        ),

        # Knowledge cutoff probes
        Probe(
            id="knowledge_1",
            prompt="What is your knowledge cutoff date?",
            category="knowledge",
            expected_patterns={
                ModelFamily.GPT: ["2023", "2024", "april", "september"],
                ModelFamily.CLAUDE: ["2024", "early 2024", "april"],
                ModelFamily.LLAMA: ["2023", "december"],
                ModelFamily.GEMINI: ["2023", "2024"],
            },
            weight=0.7
        ),

        # Formatting preference probes
        Probe(
            id="format_1",
            prompt="List 3 programming languages. Just the names, nothing else.",
            category="style",
            expected_patterns={},
            weight=0.4
        ),
    ]

    def __init__(self, custom_probes: Optional[List[Probe]] = None):
        self.probes = self.STANDARD_PROBES.copy()
        if custom_probes:
            self.probes.extend(custom_probes)

    def get_probes(self, categories: Optional[List[str]] = None) -> List[Probe]:
        """Get probes, optionally filtered by category."""
        if categories is None:
            return self.probes
        return [p for p in self.probes if p.category in categories]

    def get_quick_probes(self, count: int = 3) -> List[Probe]:
        """Get quick probes for fast identification."""
        # Prioritize identity probes
        identity = [p for p in self.probes if p.category == "identity"]
        if len(identity) >= count:
            return identity[:count]
        # Add more probes if needed
        other = [p for p in self.probes if p.category != "identity"]
        return identity + other[:count - len(identity)]


# ============================================================================
# Response Analyzer
# ============================================================================

class ResponseAnalyzer:
    """
    Analyzes model responses to extract fingerprinting signals.
    """

    # Stylistic markers unique to model families
    STYLE_MARKERS = {
        ModelFamily.GPT: {
            "uses_certainly": r"\bcertainly\b",
            "uses_absolutely": r"\babsolutely\b",
            "ends_with_question": r"\?\s*$",
            "uses_markdown_headers": r"^#+\s",
            "uses_code_blocks": r"```",
        },
        ModelFamily.CLAUDE: {
            "uses_i_apologize": r"\bI apologize\b",
            "uses_nuanced": r"\bnuanced\b",
            "uses_thoughtful": r"\bthoughtful\b",
            "uses_let_me": r"\blet me\b",
            "hesitant_language": r"\bI'm not (sure|certain)\b",
        },
        ModelFamily.LLAMA: {
            "uses_hey": r"^Hey\b",
            "casual_tone": r"\bgonna\b|\bwanna\b",
            "uses_cool": r"\bcool\b",
            "shorter_responses": None,  # Checked separately
        },
        ModelFamily.GEMINI: {
            "uses_great_question": r"\bgreat question\b",
            "uses_let_me_help": r"\blet me help\b",
            "formal_structure": r"^\d+\.\s",
        },
    }

    def analyze_response(self, probe: Probe, response: str) -> ProbeResult:
        """Analyze a response to a probe."""
        response_lower = response.lower()
        matched_families: List[Tuple[ModelFamily, float]] = []

        # Check expected patterns
        for family, patterns in probe.expected_patterns.items():
            if not patterns:
                continue
            matches = sum(1 for p in patterns if p.lower() in response_lower)
            if matches > 0:
                score = min(matches / len(patterns), 1.0)
                matched_families.append((family, score * probe.weight))

        # Check stylistic markers
        style_scores = self._analyze_style(response)
        for family, score in style_scores.items():
            # Merge with pattern matches
            existing = next((i for i, (f, _) in enumerate(
                matched_families) if f == family), None)
            if existing is not None:
                matched_families[existing] = (
                    family, matched_families[existing][1] + score * 0.3)
            elif score > 0.3:
                matched_families.append((family, score * 0.3))

        # Sort by score
        matched_families.sort(key=lambda x: x[1], reverse=True)

        return ProbeResult(
            probe_id=probe.id,
            response=response[:200],  # Truncate for storage
            matched_families=matched_families
        )

    def _analyze_style(self, response: str) -> Dict[ModelFamily, float]:
        """Analyze stylistic markers in response."""
        scores: Dict[ModelFamily, float] = {}

        for family, markers in self.STYLE_MARKERS.items():
            match_count = 0
            total_markers = len([m for m in markers.values() if m is not None])

            for marker_name, pattern in markers.items():
                if pattern is None:
                    continue
                if re.search(pattern, response, re.IGNORECASE | re.MULTILINE):
                    match_count += 1

            if total_markers > 0:
                scores[family] = match_count / total_markers

        return scores

    def extract_stylistic_markers(self, responses: List[str]) -> Dict[str, Any]:
        """Extract aggregate stylistic markers from multiple responses."""
        all_text = " ".join(responses)

        markers = {
            "avg_response_length": sum(len(r) for r in responses) / len(responses) if responses else 0,
            "uses_markdown": bool(re.search(r"```|\*\*|##", all_text)),
            "uses_emojis": bool(re.search(r"[\U0001F600-\U0001F64F]", all_text)),
            "uses_bullet_points": bool(re.search(r"^[\-\*•]\s", all_text, re.MULTILINE)),
            "formal_tone": self._measure_formality(all_text),
            "hedging_language": bool(re.search(r"\bmight\b|\bperhaps\b|\bpossibly\b", all_text, re.IGNORECASE)),
        }

        return markers

    def _measure_formality(self, text: str) -> float:
        """Measure formality of text (0-1)."""
        informal_markers = ["gonna", "wanna", "kinda",
                            "sorta", "yeah", "nope", "cool", "awesome"]
        formal_markers = ["however", "therefore",
                          "furthermore", "consequently", "nevertheless"]

        text_lower = text.lower()
        informal_count = sum(1 for m in informal_markers if m in text_lower)
        formal_count = sum(1 for m in formal_markers if m in text_lower)

        total = informal_count + formal_count
        if total == 0:
            return 0.5
        return formal_count / total


# ============================================================================
# Main Fingerprinting Engine
# ============================================================================

class LLMFingerprintingEngine:
    """
    Main engine for LLM fingerprinting.

    Usage:
        engine = LLMFingerprintingEngine()

        # Option 1: Provide a query function
        fingerprint = engine.fingerprint(query_fn=my_llm_query)

        # Option 2: Analyze pre-collected responses
        fingerprint = engine.analyze_responses(probes, responses)
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.probe_generator = ProbeGenerator()
        self.response_analyzer = ResponseAnalyzer()
        self.fingerprint_history: List[BehavioralFingerprint] = []

        logger.info("LLMFingerprintingEngine initialized")

    def fingerprint(
        self,
        query_fn: Callable[[str], str],
        probe_count: int = 5,
        categories: Optional[List[str]] = None
    ) -> BehavioralFingerprint:
        """
        Fingerprint a model by sending probes.

        Args:
            query_fn: Function that takes a prompt and returns model response
            probe_count: Number of probes to use
            categories: Optional filter for probe categories

        Returns:
            BehavioralFingerprint with model identification
        """
        # Get probes
        if categories:
            probes = self.probe_generator.get_probes(categories)[:probe_count]
        else:
            probes = self.probe_generator.get_quick_probes(probe_count)

        # Run probes
        probe_results: List[ProbeResult] = []
        responses: List[str] = []

        for probe in probes:
            try:
                response = query_fn(probe.prompt)
                responses.append(response)
                result = self.response_analyzer.analyze_response(
                    probe, response)
                probe_results.append(result)
            except Exception as e:
                logger.warning(f"Probe {probe.id} failed: {e}")

        # Aggregate results
        return self._create_fingerprint(probe_results, responses)

    def analyze_responses(
        self,
        prompt_response_pairs: List[Tuple[str, str]]
    ) -> BehavioralFingerprint:
        """
        Analyze pre-collected prompt-response pairs.

        Args:
            prompt_response_pairs: List of (prompt, response) tuples

        Returns:
            BehavioralFingerprint
        """
        probe_results: List[ProbeResult] = []
        responses: List[str] = []

        for i, (prompt, response) in enumerate(prompt_response_pairs):
            responses.append(response)

            # Create ad-hoc probe
            probe = Probe(
                id=f"adhoc_{i}",
                prompt=prompt,
                category="style",
                expected_patterns={}
            )

            # Find matching standard probe
            for std_probe in self.probe_generator.probes:
                if prompt.lower() == std_probe.prompt.lower():
                    probe = std_probe
                    break

            result = self.response_analyzer.analyze_response(probe, response)
            probe_results.append(result)

        return self._create_fingerprint(probe_results, responses)

    def _create_fingerprint(
        self,
        probe_results: List[ProbeResult],
        responses: List[str]
    ) -> BehavioralFingerprint:
        """Create fingerprint from probe results."""
        # Aggregate family scores
        family_scores: Dict[ModelFamily, float] = {}

        for result in probe_results:
            for family, score in result.matched_families:
                if family not in family_scores:
                    family_scores[family] = 0.0
                family_scores[family] += score

        # Normalize scores
        total_score = sum(family_scores.values())
        if total_score > 0:
            for family in family_scores:
                family_scores[family] /= total_score

        # Determine best match
        if family_scores:
            best_family = max(family_scores, key=family_scores.get)
            best_score = family_scores[best_family]
        else:
            best_family = ModelFamily.UNKNOWN
            best_score = 0.0

        # Determine confidence
        confidence = self._score_to_confidence(best_score)

        # Extract stylistic markers
        stylistic_markers = self.response_analyzer.extract_stylistic_markers(
            responses)

        # Generate fingerprint ID
        fingerprint_id = self._generate_fingerprint_id(
            probe_results, stylistic_markers)

        # Try to detect version
        model_version = self._detect_version(responses, best_family)

        fingerprint = BehavioralFingerprint(
            fingerprint_id=fingerprint_id,
            model_family=best_family,
            model_version=model_version,
            confidence=confidence,
            confidence_score=best_score,
            probe_results=probe_results,
            stylistic_markers=stylistic_markers
        )

        self.fingerprint_history.append(fingerprint)

        if best_family != ModelFamily.UNKNOWN:
            logger.info(
                f"Fingerprinted model: {best_family.value} "
                f"(confidence: {confidence.value}, score: {best_score:.2f})"
            )

        return fingerprint

    def _score_to_confidence(self, score: float) -> ModelConfidence:
        """Convert score to confidence level."""
        if score >= 0.95:
            return ModelConfidence.VERY_HIGH
        elif score >= 0.8:
            return ModelConfidence.HIGH
        elif score >= 0.6:
            return ModelConfidence.MEDIUM
        elif score >= 0.4:
            return ModelConfidence.LOW
        else:
            return ModelConfidence.VERY_LOW

    def _generate_fingerprint_id(
        self,
        probe_results: List[ProbeResult],
        markers: Dict[str, Any]
    ) -> str:
        """Generate unique fingerprint ID."""
        data = json.dumps({
            "responses": [r.response[:50] for r in probe_results],
            "markers": {k: str(v) for k, v in markers.items()}
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _detect_version(self, responses: List[str], family: ModelFamily) -> Optional[str]:
        """Try to detect specific model version."""
        all_text = " ".join(responses).lower()

        version_patterns = {
            ModelFamily.GPT: [
                (r"gpt-4o", "gpt-4o"),
                (r"gpt-4", "gpt-4"),
                (r"gpt-3\.5", "gpt-3.5"),
            ],
            ModelFamily.CLAUDE: [
                (r"claude 3\.5", "claude-3.5"),
                (r"claude 3", "claude-3"),
                (r"claude 2", "claude-2"),
            ],
            ModelFamily.LLAMA: [
                (r"llama 3\.3", "llama-3.3"),
                (r"llama 3\.2", "llama-3.2"),
                (r"llama 3", "llama-3"),
                (r"llama 2", "llama-2"),
            ],
            ModelFamily.GEMINI: [
                (r"gemini 2", "gemini-2"),
                (r"gemini 1\.5", "gemini-1.5"),
                (r"gemini pro", "gemini-pro"),
            ],
        }

        patterns = version_patterns.get(family, [])
        for pattern, version in patterns:
            if re.search(pattern, all_text):
                return version

        return None

    def is_shadow_ai(
        self,
        fingerprint: BehavioralFingerprint,
        expected_family: ModelFamily
    ) -> Tuple[bool, str]:
        """
        Check if the fingerprinted model is "shadow AI" (unexpected model).

        Returns:
            (is_shadow, reason)
        """
        if fingerprint.model_family == ModelFamily.UNKNOWN:
            return True, "Could not identify model family"

        if fingerprint.model_family != expected_family:
            return True, f"Expected {expected_family.value}, detected {fingerprint.model_family.value}"

        if fingerprint.confidence_score < 0.6:
            return True, f"Low confidence ({fingerprint.confidence_score:.2f}) in model identification"

        return False, "Model matches expected configuration"

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        family_counts = Counter(
            f.model_family.value for f in self.fingerprint_history)

        return {
            "total_fingerprints": len(self.fingerprint_history),
            "family_distribution": dict(family_counts),
            "probe_count": len(self.probe_generator.probes)
        }
