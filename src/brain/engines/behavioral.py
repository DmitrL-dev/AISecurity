"""
Behavioral Engine v2.0 - User Profiling and Anomaly Detection

Features:
  1. Isolation Forest for anomaly detection
  2. Time-series pattern analysis
  3. Session pattern detection (escalation, reconnaissance)
  4. User clustering for group-based baselines
  5. Adaptive trust scoring
  6. Redis-backed persistent profiles
"""

import logging
import os
import json
import time
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timedelta
from enum import Enum

import numpy as np

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger("BehavioralEngine")


# ============================================================================
# Enums and Data Classes
# ============================================================================

class UserTrustLevel(Enum):
    """User trust classification."""
    NEW = "new"            # New user, no history
    SUSPICIOUS = "suspicious"  # High block ratio
    NORMAL = "normal"      # Average behavior
    TRUSTED = "trusted"    # Low risk, long history


class SessionPattern(Enum):
    """Detected session patterns."""
    NORMAL = "normal"
    ESCALATION = "escalation"      # Gradually increasing risk
    RECONNAISSANCE = "reconnaissance"  # Probing behavior
    BURST = "burst"               # Sudden high-volume activity


@dataclass
class UserProfile:
    """User behavioral profile."""
    user_id: str
    request_count: int = 0
    total_risk: float = 0.0
    blocked_count: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0
    trust_level: UserTrustLevel = UserTrustLevel.NEW
    cluster_id: int = -1
    features_history: List[List[float]] = field(default_factory=list)

    def avg_risk(self) -> float:
        return self.total_risk / max(self.request_count, 1)

    def block_ratio(self) -> float:
        return self.blocked_count / max(self.request_count, 1)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "request_count": self.request_count,
            "total_risk": self.total_risk,
            "blocked_count": self.blocked_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "trust_level": self.trust_level.value,
            "cluster_id": self.cluster_id,
            "avg_risk": self.avg_risk(),
            "block_ratio": self.block_ratio()
        }


@dataclass
class BehavioralResult:
    """Result from behavioral analysis."""
    risk_adjustment: float = 0.0
    final_risk: float = 0.0
    is_anomaly: bool = False
    trust_level: UserTrustLevel = UserTrustLevel.NEW
    session_pattern: SessionPattern = SessionPattern.NORMAL
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "risk_adjustment": self.risk_adjustment,
            "final_risk": self.final_risk,
            "is_anomaly": self.is_anomaly,
            "trust_level": self.trust_level.value,
            "session_pattern": self.session_pattern.value,
            "reasons": self.reasons
        }


# ============================================================================
# Time-Series Analyzer
# ============================================================================

class TimeSeriesAnalyzer:
    """Analyzes temporal patterns in user behavior."""

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.sessions: Dict[str, deque] = {}

    def add_observation(self, session_id: str, risk_score: float, timestamp: float = None):
        """Add observation to session timeline."""
        if session_id not in self.sessions:
            self.sessions[session_id] = deque(maxlen=self.window_size)

        timestamp = timestamp or time.time()
        self.sessions[session_id].append((timestamp, risk_score))

    def detect_pattern(self, session_id: str) -> Tuple[SessionPattern, float]:
        """
        Detect session pattern.
        Returns (pattern, confidence).
        """
        if session_id not in self.sessions or len(self.sessions[session_id]) < 3:
            return SessionPattern.NORMAL, 0.0

        observations = list(self.sessions[session_id])
        timestamps = [o[0] for o in observations]
        risks = [o[1] for o in observations]

        # Check for escalation (increasing risk trend)
        if len(risks) >= 3:
            slope = np.polyfit(range(len(risks)), risks, 1)[0]
            if slope > 5.0:  # Significant upward trend
                return SessionPattern.ESCALATION, min(slope / 10, 1.0)

        # Check for burst (many requests in short time)
        if len(timestamps) >= 5:
            time_span = timestamps[-1] - timestamps[0]
            if time_span > 0:
                request_rate = len(timestamps) / time_span * 60  # per minute
                if request_rate > 30:
                    return SessionPattern.BURST, min(request_rate / 60, 1.0)

        # Check for reconnaissance (low risk probing)
        if len(risks) >= 5:
            avg_risk = np.mean(risks)
            std_risk = np.std(risks)
            if avg_risk < 30 and std_risk < 10 and len(set(risks)) > 3:
                return SessionPattern.RECONNAISSANCE, 0.5

        return SessionPattern.NORMAL, 0.0


# ============================================================================
# Feature Extractor
# ============================================================================

class FeatureExtractor:
    """Extracts numerical features from requests."""

    def extract(self, prompt: str, base_risk: float,
                hour_of_day: int = None) -> List[float]:
        """
        Extract features for anomaly detection.
        """
        if hour_of_day is None:
            hour_of_day = datetime.now().hour

        features = [
            len(prompt),                          # Length
            prompt.count(" "),                    # Word count approx
            base_risk,                            # Risk from engines
            self._uppercase_ratio(prompt),
            self._special_char_ratio(prompt),
            self._entropy(prompt),
            hour_of_day / 24.0,                   # Time of day normalized
            1.0 if any(c > '\u0400' for c in prompt) else 0.0,  # Has Cyrillic
        ]
        return features

    def _uppercase_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        return sum(1 for c in text if c.isupper()) / len(text)

    def _special_char_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        return sum(1 for c in text if not c.isalnum()) / len(text)

    def _entropy(self, text: str) -> float:
        if not text:
            return 0.0
        freq = {}
        for c in text:
            freq[c] = freq.get(c, 0) + 1
        n = len(text)
        return -sum((v/n) * np.log2(v/n) for v in freq.values())


# ============================================================================
# Trust Calculator
# ============================================================================

class TrustCalculator:
    """Calculates user trust level based on history."""

    def calculate(self, profile: UserProfile) -> UserTrustLevel:
        """Determine trust level from profile history."""
        # New users
        if profile.request_count < 5:
            return UserTrustLevel.NEW

        # Suspicious: high block ratio or high avg risk
        if profile.block_ratio() > 0.3 or profile.avg_risk() > 60:
            return UserTrustLevel.SUSPICIOUS

        # Trusted: long history, low risk
        if (profile.request_count > 50 and
            profile.avg_risk() < 20 and
                profile.block_ratio() < 0.05):
            return UserTrustLevel.TRUSTED

        return UserTrustLevel.NORMAL


# ============================================================================
# Main Behavioral Engine
# ============================================================================

class BehavioralEngine:
    """
    Behavioral Engine v2.0 - User Profiling and Anomaly Detection.

    Features:
      - Isolation Forest anomaly detection
      - Time-series pattern analysis
      - User trust scoring
      - Session pattern detection
      - Redis-backed profiles
    """

    def __init__(self, redis_url: str = None):
        logger.info("Initializing Behavioral Engine v2.0...")

        # Redis connection
        self.redis_client = None
        if REDIS_AVAILABLE:
            redis_url = redis_url or os.getenv(
                "REDIS_URL", "redis://localhost:6379")
            try:
                self.redis_client = redis.from_url(
                    redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Redis connected")
            except Exception as e:
                logger.warning(
                    f"Redis unavailable: {e}. Using in-memory storage.")
                self.redis_client = None

        # In-memory fallback
        self.memory_profiles: Dict[str, dict] = {}

        # Components
        self.feature_extractor = FeatureExtractor()
        self.time_series = TimeSeriesAnalyzer()
        self.trust_calculator = TrustCalculator()

        # Isolation Forest
        self.isolation_forest = None
        self.is_trained = False
        self.min_samples = 50

        if SKLEARN_AVAILABLE:
            self.isolation_forest = IsolationForest(
                n_estimators=100,
                contamination=0.1,
                random_state=42
            )

        # Trust level adjustments
        self.trust_adjustments = {
            UserTrustLevel.NEW: 0.0,
            UserTrustLevel.SUSPICIOUS: 15.0,
            UserTrustLevel.NORMAL: 0.0,
            UserTrustLevel.TRUSTED: -5.0,
        }

        # Session pattern adjustments
        self.pattern_adjustments = {
            SessionPattern.NORMAL: 0.0,
            SessionPattern.ESCALATION: 20.0,
            SessionPattern.RECONNAISSANCE: 10.0,
            SessionPattern.BURST: 15.0,
        }

        logger.info("Behavioral Engine v2.0 initialized.")

    def _get_profile_key(self, user_id: str) -> str:
        return f"sentinel:profile:{user_id}"

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieve user profile."""
        key = self._get_profile_key(user_id)
        data = None

        if self.redis_client:
            try:
                raw = self.redis_client.get(key)
                if raw:
                    data = json.loads(raw)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        else:
            data = self.memory_profiles.get(user_id)

        if data:
            profile = UserProfile(
                user_id=data["user_id"],
                request_count=data.get("request_count", 0),
                total_risk=data.get("total_risk", 0.0),
                blocked_count=data.get("blocked_count", 0),
                first_seen=data.get("first_seen", 0.0),
                last_seen=data.get("last_seen", 0.0),
                trust_level=UserTrustLevel(data.get("trust_level", "new")),
                cluster_id=data.get("cluster_id", -1),
                features_history=data.get("features_history", [])
            )
            return profile

        return None

    def update_profile(self, user_id: str, features: List[float],
                       risk_score: float, was_blocked: bool) -> UserProfile:
        """Update user profile with new request."""
        profile = self.get_profile(user_id) or UserProfile(
            user_id=user_id,
            first_seen=time.time()
        )

        profile.request_count += 1
        profile.total_risk += risk_score
        profile.last_seen = time.time()
        if was_blocked:
            profile.blocked_count += 1

        # Update features history
        profile.features_history.append(features)
        if len(profile.features_history) > 100:
            profile.features_history = profile.features_history[-100:]

        # Update trust level
        profile.trust_level = self.trust_calculator.calculate(profile)

        # Save
        self._save_profile(profile)

        return profile

    def _save_profile(self, profile: UserProfile):
        """Save profile to storage."""
        data = {
            "user_id": profile.user_id,
            "request_count": profile.request_count,
            "total_risk": profile.total_risk,
            "blocked_count": profile.blocked_count,
            "first_seen": profile.first_seen,
            "last_seen": profile.last_seen,
            "trust_level": profile.trust_level.value,
            "cluster_id": profile.cluster_id,
            "features_history": profile.features_history
        }

        key = self._get_profile_key(profile.user_id)

        if self.redis_client:
            try:
                self.redis_client.set(key, json.dumps(data), ex=86400 * 30)
            except Exception as e:
                logger.warning(f"Redis save error: {e}")
                self.memory_profiles[profile.user_id] = data
        else:
            self.memory_profiles[profile.user_id] = data

    def detect_anomaly(self, features: List[float]) -> Tuple[bool, float]:
        """
        Detect if request is anomalous.
        Returns (is_anomaly, anomaly_score).
        """
        if not self.is_trained or self.isolation_forest is None:
            return False, 0.0

        try:
            features_array = np.array(features).reshape(1, -1)
            score = -self.isolation_forest.score_samples(features_array)[0]
            is_anomaly = score > 0.5
            return is_anomaly, min(score * 20, 30.0)
        except Exception as e:
            logger.warning(f"Anomaly detection error: {e}")
            return False, 0.0

    def analyze(self, prompt: str, user_id: str,
                base_risk: float, session_id: str = None) -> BehavioralResult:
        """
        Analyze request for behavioral anomalies.

        Args:
            prompt: Request text
            user_id: User identifier
            base_risk: Risk score from other engines
            session_id: Session identifier for pattern detection

        Returns:
            BehavioralResult with adjustments and reasoning
        """
        result = BehavioralResult()
        adjustment = 0.0
        reasons = []

        # Extract features
        features = self.feature_extractor.extract(prompt, base_risk)

        # Get/update profile
        profile = self.get_profile(user_id) or UserProfile(user_id=user_id)
        result.trust_level = profile.trust_level

        # 1. Trust level adjustment
        trust_adj = self.trust_adjustments.get(profile.trust_level, 0.0)
        if trust_adj != 0:
            adjustment += trust_adj
            reasons.append(
                f"Trust: {profile.trust_level.value} ({trust_adj:+.0f})")

        # 2. Anomaly detection
        is_anomaly, anomaly_score = self.detect_anomaly(features)
        if is_anomaly:
            adjustment += anomaly_score
            reasons.append(f"Anomaly detected (+{anomaly_score:.0f})")
            result.is_anomaly = True

        # 3. Session pattern detection
        if session_id:
            self.time_series.add_observation(session_id, base_risk)
            pattern, confidence = self.time_series.detect_pattern(session_id)
            result.session_pattern = pattern

            if pattern != SessionPattern.NORMAL:
                pattern_adj = self.pattern_adjustments.get(
                    pattern, 0.0) * confidence
                adjustment += pattern_adj
                reasons.append(
                    f"Pattern: {pattern.value} (+{pattern_adj:.0f})")

        # 4. History-based adjustment
        if profile.request_count > 10:
            if profile.block_ratio() > 0.5:
                adjustment += 20.0
                reasons.append("Very high block ratio (+20)")

        # Build result
        result.risk_adjustment = adjustment
        result.final_risk = min(100.0, max(0.0, base_risk + adjustment))
        result.reasons = reasons

        return result

    def train_model(self):
        """Train Isolation Forest on accumulated data."""
        if self.isolation_forest is None:
            logger.warning("sklearn not available, cannot train")
            return

        all_features = []

        if self.redis_client:
            try:
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(
                        cursor, match="sentinel:profile:*", count=100
                    )
                    for key in keys:
                        raw = self.redis_client.get(key)
                        if raw:
                            profile = json.loads(raw)
                            all_features.extend(
                                profile.get("features_history", []))
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis scan error: {e}")
        else:
            for data in self.memory_profiles.values():
                all_features.extend(data.get("features_history", []))

        if len(all_features) >= self.min_samples:
            logger.info(f"Training on {len(all_features)} samples...")
            self.isolation_forest.fit(np.array(all_features))
            self.is_trained = True
            logger.info("Model trained.")
        else:
            logger.info(
                f"Not enough samples ({len(all_features)}/{self.min_samples})")

    # Backward compatibility
    def calculate_risk_adjustment(self, user_id: str, base_risk: float,
                                  features: List[float]) -> dict:
        """Legacy interface."""
        result = self.analyze("", user_id, base_risk)
        return {
            "adjustment": result.risk_adjustment,
            "reasons": result.reasons,
            "final_risk": result.final_risk
        }

    def _extract_features(self, prompt: str, base_risk: float) -> List[float]:
        """Legacy interface."""
        return self.feature_extractor.extract(prompt, base_risk)
