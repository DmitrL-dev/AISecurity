"""
Knowledge Guard - Multi-Layer Semantic Access Control Engine

Layers:
  0. Cache - LRU cache for repeated queries
  1. Static - Regex/keyword blacklist  
  2. Canary - Honeypot detection for insider threats
  3. Semantic - Embedding similarity check
  4. Context - Session accumulator
  5. Verdict - Confidence zones + explainability
"""

import re
import os
import logging
import hashlib
import yaml
from functools import lru_cache
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger("KnowledgeGuard")


# ============================================================================
# SecureBERT 2.0 Embedder
# ============================================================================

class SecureBERT2Embedder:
    """
    SecureBERT 2.0 based embedder for cybersecurity-optimized semantic search.

    Uses Cisco AI Defense's SecureBERT 2.0 model trained on 13B+ cybersecurity tokens.
    Falls back to SentenceTransformer if SecureBERT is not available.

    HuggingFace: cisco-ai-defense/securebert-2.0-base
    """

    MODEL_NAME = "cisco-ai-defense/securebert-2.0-base"
    FALLBACK_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, use_securebert: bool = True, device: str = None):
        self.model = None
        self.tokenizer = None
        self.is_securebert = False
        self.device = device
        self._hidden_size = 768

        if use_securebert:
            self._try_load_securebert()

        if self.model is None:
            self._load_fallback()

    def _try_load_securebert(self):
        try:
            from transformers import AutoModel, AutoTokenizer
            import torch

            logger.info(f"Loading SecureBERT 2.0: {self.MODEL_NAME}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            self.model = AutoModel.from_pretrained(self.MODEL_NAME)

            if self.device is None:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = self.model.to(self.device)
            self.model.eval()
            self._hidden_size = self.model.config.hidden_size
            self.is_securebert = True
            logger.info(f"SecureBERT 2.0 loaded on {self.device}")
        except Exception as e:
            logger.warning(
                f"Failed to load SecureBERT 2.0: {e}. Using fallback.")
            self.model = None

    def _load_fallback(self):
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading fallback model: {self.FALLBACK_MODEL}")
            self.model = SentenceTransformer(self.FALLBACK_MODEL)
            self.is_securebert = False
            self._hidden_size = 384
            logger.info("Fallback SentenceTransformer loaded")
        except Exception as e:
            logger.error(f"Failed to load fallback model: {e}")
            self.model = None

    def encode(self, texts, batch_size: int = 32):
        if self.model is None:
            return np.zeros((len(texts) if isinstance(texts, list) else 1, self._hidden_size))
        if isinstance(texts, str):
            texts = [texts]
        if self.is_securebert:
            return self._encode_securebert(texts, batch_size)
        return self.model.encode(texts, convert_to_numpy=True)

    def _encode_securebert(self, texts: list, batch_size: int):
        import torch
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            inputs = self.tokenizer(batch, padding=True, truncation=True,
                                    max_length=512, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
                mask = inputs['attention_mask'].unsqueeze(-1).expand(
                    outputs.last_hidden_state.size()).float()
                embeddings = torch.sum(
                    outputs.last_hidden_state * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)
            all_embeddings.append(embeddings.cpu().numpy())
        return np.vstack(all_embeddings)

    @property
    def embedding_dim(self) -> int:
        return self._hidden_size

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME if self.is_securebert else self.FALLBACK_MODEL


@dataclass
class GuardDecision:
    """Explainable decision from Knowledge Guard."""
    action: str  # ALLOW, WARN, REVIEW, BLOCK
    score: float
    layer: str  # Which layer made the decision
    matched_topic: Optional[str] = None
    alert_code: Optional[str] = None
    explanation: str = ""
    audit_id: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "score": self.score,
            "layer": self.layer,
            "matched_topic": self.matched_topic,
            "alert_code": self.alert_code,
            "explanation": self.explanation,
            "audit_id": self.audit_id,
        }


class CacheLayer:
    """Layer 0: LRU cache for instant decisions on repeated queries."""

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        self.cache: Dict[str, Tuple[GuardDecision, datetime]] = {}
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)

    def _hash_query(self, query: str) -> str:
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]

    def get(self, query: str) -> Optional[GuardDecision]:
        key = self._hash_query(query)
        if key in self.cache:
            decision, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                logger.debug(f"Cache hit for query hash {key}")
                return decision
            else:
                del self.cache[key]
        return None

    def put(self, query: str, decision: GuardDecision):
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache, key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        key = self._hash_query(query)
        self.cache[key] = (decision, datetime.now())


class StaticLayer:
    """Layer 1: Regex/keyword blacklist for fast matching."""

    def __init__(self, blacklist_file: str):
        self.patterns: List[re.Pattern] = []
        self._load_blacklist(blacklist_file)

    def _load_blacklist(self, filepath: str):
        if not os.path.exists(filepath):
            logger.warning(f"Blacklist file not found: {filepath}")
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        self.patterns.append(re.compile(line, re.IGNORECASE))
                    except re.error as e:
                        logger.warning(f"Invalid regex pattern '{line}': {e}")

        logger.info(f"Loaded {len(self.patterns)} static patterns")

    def check(self, query: str) -> Optional[GuardDecision]:
        for pattern in self.patterns:
            match = pattern.search(query)
            if match:
                return GuardDecision(
                    action="BLOCK",
                    score=1.0,
                    layer="STATIC",
                    matched_topic=pattern.pattern,
                    explanation=f"Static blacklist match: {match.group()}",
                    audit_id=f"static-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                )
        return None


class CanaryLayer:
    """Layer 2: Honeypot detection for insider threats."""

    def __init__(self, canaries_file: str):
        self.canaries: Dict[str, str] = {}  # topic -> alert_code
        self._load_canaries(canaries_file)

    def _load_canaries(self, filepath: str):
        if not os.path.exists(filepath):
            logger.warning(f"Canaries file not found: {filepath}")
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('|')
                    if len(parts) == 2:
                        self.canaries[parts[0].lower()] = parts[1]

        logger.info(f"Loaded {len(self.canaries)} canary traps")

    def check(self, query: str) -> Optional[GuardDecision]:
        query_lower = query.lower()
        for trap, alert_code in self.canaries.items():
            if trap in query_lower:
                logger.critical(f"CANARY TRAP TRIGGERED: {alert_code}")
                return GuardDecision(
                    action="BLOCK",
                    score=1.0,
                    layer="CANARY",
                    matched_topic=trap,
                    alert_code=alert_code,
                    explanation=f"Canary trap triggered: {alert_code}",
                    audit_id=f"canary-{alert_code}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                )
        return None


class SemanticLayer:
    """Layer 3: Embedding similarity check."""

    def __init__(self, model, protected_topics: List[str],
                 negative_examples: List[str], threshold: float = 0.85):
        self.model = model  # Shared SentenceTransformer
        self.threshold = threshold
        self.protected_topics = protected_topics
        self.negative_examples = negative_examples

        # Pre-compute embeddings
        self.topic_embeddings = None
        self.negative_embeddings = None
        self._precompute_embeddings()

    def _precompute_embeddings(self):
        if self.protected_topics:
            self.topic_embeddings = self.model.encode(self.protected_topics)
            logger.info(
                f"Pre-computed embeddings for {len(self.protected_topics)} protected topics")

        if self.negative_examples:
            self.negative_embeddings = self.model.encode(
                self.negative_examples)
            logger.info(
                f"Pre-computed embeddings for {len(self.negative_examples)} negative examples")

    def check(self, query: str, query_embedding: np.ndarray = None) -> Tuple[float, Optional[str]]:
        """Returns (max_similarity, matched_topic)."""
        if self.topic_embeddings is None:
            return 0.0, None

        if query_embedding is None:
            query_embedding = self.model.encode([query])[0]

        # Calculate similarities to protected topics
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(
            [query_embedding], self.topic_embeddings)[0]

        max_sim_idx = np.argmax(similarities)
        max_similarity = similarities[max_sim_idx]
        matched_topic = self.protected_topics[max_sim_idx]

        # Check negative examples (reduce false positives)
        if self.negative_embeddings is not None and max_similarity > 0.5:
            neg_similarities = cosine_similarity(
                [query_embedding], self.negative_embeddings)[0]
            max_neg_sim = np.max(neg_similarities)

            # If query is more similar to negative example, reduce score
            if max_neg_sim > max_similarity:
                logger.debug(
                    f"Negative example match reduces score: {max_similarity:.2f} -> {max_similarity * 0.5:.2f}")
                max_similarity *= 0.5

        return max_similarity, matched_topic


class ContextLayer:
    """Layer 4: Session accumulator for reconnaissance detection."""

    def __init__(self, session_window: int = 300, cumulative_threshold: float = 2.0):
        self.sessions: Dict[str, List[Tuple[float, datetime]]] = {}
        self.window = timedelta(seconds=session_window)
        self.threshold = cumulative_threshold

    def add_and_check(self, session_id: str, score: float) -> Tuple[float, bool]:
        """Add score to session and check if cumulative exceeds threshold."""
        now = datetime.now()

        if session_id not in self.sessions:
            self.sessions[session_id] = []

        # Clean old entries
        self.sessions[session_id] = [
            (s, t) for s, t in self.sessions[session_id]
            if now - t < self.window
        ]

        # Add current
        self.sessions[session_id].append((score, now))

        # Calculate cumulative
        cumulative = sum(s for s, _ in self.sessions[session_id])
        is_suspicious = cumulative > self.threshold

        if is_suspicious:
            logger.warning(
                f"Session {session_id} cumulative risk: {cumulative:.2f} > {self.threshold}")

        return cumulative, is_suspicious


class VerdictEngine:
    """Layer 5: Confidence zones and final decision."""

    def __init__(self, zones: dict):
        self.zones = zones  # {zone_name: [min, max]}

    def decide(self, score: float) -> str:
        for zone, (min_val, max_val) in self.zones.items():
            if min_val <= score < max_val:
                return zone.upper()
        return "BLOCK" if score >= 0.85 else "ALLOW"


class KnowledgeGuard:
    """
    Multi-Layer Semantic Access Control Engine.

    Orchestrates all layers to provide defense-in-depth for sensitive data access.
    """

    def __init__(self, sentence_model=None):
        logger.info("Initializing Knowledge Guard (Multi-Layer)...")

        self.config = self._load_config()
        self.sentence_model = sentence_model

        # Initialize layers
        config_dir = os.path.dirname(os.path.dirname(__file__))

        # Layer 0: Cache
        cache_cfg = self.config.get('layers', {}).get('cache', {})
        self.cache = CacheLayer(
            max_size=cache_cfg.get('max_size', 10000),
            ttl_seconds=cache_cfg.get('ttl_seconds', 300)
        )

        # Layer 1: Static
        static_cfg = self.config.get('layers', {}).get('static', {})
        blacklist_path = os.path.join(config_dir, static_cfg.get(
            'blacklist_file', 'config/blacklist.txt'))
        self.static = StaticLayer(blacklist_path)

        # Layer 2: Canary
        canary_cfg = self.config.get('layers', {}).get('canary', {})
        canaries_path = os.path.join(config_dir, canary_cfg.get(
            'traps_file', 'config/canaries.txt'))
        self.canary = CanaryLayer(canaries_path)

        # Layer 3: Semantic
        semantic_cfg = self.config.get('layers', {}).get('semantic', {})
        protected_topics = self._flatten_topics(
            self.config.get('protected_topics', {}))
        negative_examples = self.config.get('negative_examples', [])

        if self.sentence_model:
            self.semantic = SemanticLayer(
                model=self.sentence_model,
                protected_topics=protected_topics,
                negative_examples=negative_examples,
                threshold=semantic_cfg.get('threshold', 0.85)
            )
        else:
            self.semantic = None
            logger.warning(
                "No sentence model provided, semantic layer disabled")

        # Layer 4: Context
        context_cfg = self.config.get('layers', {}).get('context', {})
        self.context = ContextLayer(
            session_window=context_cfg.get('session_window_seconds', 300),
            cumulative_threshold=context_cfg.get('cumulative_threshold', 2.0)
        )

        # Layer 5: Verdict
        verdict_cfg = self.config.get('layers', {}).get('verdict', {})
        zones = verdict_cfg.get('zones', {
            'allow': [0.0, 0.5],
            'warn': [0.5, 0.7],
            'review': [0.7, 0.85],
            'block': [0.85, 1.0]
        })
        self.verdict = VerdictEngine(zones)

        logger.info("Knowledge Guard initialized with all layers.")

    def _load_config(self) -> dict:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config', 'knowledge_guard.yaml'
        )

        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

        logger.warning(f"Config not found at {config_path}, using defaults")
        return {}

    def _flatten_topics(self, topics_dict: dict) -> List[str]:
        """Flatten hierarchical topics into a list."""
        result = []
        for category, items in topics_dict.items():
            if isinstance(items, list):
                result.extend(items)
        return result

    def check(self, query: str, session_id: str = "anonymous") -> GuardDecision:
        """
        Run query through all protection layers.

        Returns GuardDecision with action, score, and explanation.
        """
        # Layer 0: Cache
        cached = self.cache.get(query)
        if cached:
            cached.layer = "CACHE"
            return cached

        # Layer 1: Static
        static_result = self.static.check(query)
        if static_result:
            self.cache.put(query, static_result)
            return static_result

        # Layer 2: Canary
        canary_result = self.canary.check(query)
        if canary_result:
            # Don't cache canary hits (forensic purposes)
            return canary_result

        # Layer 3: Semantic
        semantic_score = 0.0
        matched_topic = None

        if self.semantic:
            semantic_score, matched_topic = self.semantic.check(query)

        # Layer 4: Context
        cumulative, is_suspicious = self.context.add_and_check(
            session_id, semantic_score)

        # Boost score if session is suspicious
        final_score = semantic_score
        if is_suspicious:
            final_score = min(1.0, semantic_score + 0.2)
            logger.warning(
                f"Session suspicious, boosting score: {semantic_score:.2f} -> {final_score:.2f}")

        # Layer 5: Verdict
        action = self.verdict.decide(final_score)

        decision = GuardDecision(
            action=action,
            score=final_score,
            layer="SEMANTIC" if not is_suspicious else "CONTEXT",
            matched_topic=matched_topic,
            explanation=f"Semantic similarity: {semantic_score:.2f}, Session cumulative: {cumulative:.2f}",
            audit_id=f"kg-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        )

        # Cache non-block decisions
        if action != "BLOCK":
            self.cache.put(query, decision)

        return decision

    def get_risk_adjustment(self, query: str, session_id: str = "anonymous") -> float:
        """
        Get risk score adjustment for analyzer pipeline.

        Returns:
            float: Risk adjustment (0-100 scale)
        """
        decision = self.check(query, session_id)

        # Map actions to risk adjustments
        risk_map = {
            "ALLOW": 0.0,
            "WARN": 25.0,
            "REVIEW": 50.0,
            "BLOCK": 100.0,
        }

        risk = risk_map.get(decision.action, 0.0)

        if decision.action != "ALLOW":
            logger.info(
                f"Knowledge Guard: {decision.action} (score={decision.score:.2f}, topic={decision.matched_topic})")

        return risk
