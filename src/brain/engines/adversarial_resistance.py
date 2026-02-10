"""
Adversarial Resistance Module
Hybrid defense against attackers who know our algorithms.

Combines:
1. Threshold randomization — unpredictable decision boundaries
2. Secret salts — prevent hash precomputation
3. Temporal jitter — unpredictable timing
4. Multi-path verification — different paths per request
"""

import os
import hashlib
import hmac
import random
import time
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Callable, List
from functools import wraps

logger = logging.getLogger("AdversarialResistance")


@dataclass
class SecureThreshold:
    """Threshold with randomization."""
    base_value: float
    jitter_range: float  # ±jitter from base
    _current: float = None

    def get(self) -> float:
        """Get randomized threshold."""
        if self._current is None:
            self.refresh()
        return self._current

    def refresh(self):
        """Refresh with new random value."""
        self._current = self.base_value + random.uniform(
            -self.jitter_range,
            self.jitter_range
        )


class SecretSaltManager:
    """Manages secret salts for hash-based detection."""

    def __init__(self):
        # Primary salt (long-lived) - try Vault first, then env var
        self._primary_salt = self._get_salt_from_vault()
        if not self._primary_salt:
            self._primary_salt = os.getenv("SENTINEL_SECRET_SALT")
        if not self._primary_salt:
            self._primary_salt = os.urandom(32).hex()
            logger.warning(
                "Generated ephemeral salt - set SENTINEL_SECRET_SALT in production!")

        # Rotating salt (changes periodically)
        self._rotating_salt = os.urandom(16).hex()
        self._salt_rotation_time = time.time()
        self._rotation_interval = 3600  # 1 hour

    def _get_salt_from_vault(self):
        """Try to get salt from Vault if enabled."""
        try:
            from infrastructure.vault import get_vault
            vault = get_vault()
            if vault.enabled:
                return vault.get_adversarial_salt()
        except Exception:
            pass  # Vault not available, use fallback
        return None

    def get_salted_hash(self, data: str, use_rotating: bool = True) -> str:
        """Compute HMAC with secret salt."""
        salt = self._get_current_salt(use_rotating)
        return hmac.new(
            salt.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

    def _get_current_salt(self, use_rotating: bool) -> str:
        """Get current salt, rotating if needed."""
        if use_rotating:
            if time.time() - self._salt_rotation_time > self._rotation_interval:
                self._rotate_salt()
            return self._primary_salt + self._rotating_salt
        return self._primary_salt

    def _rotate_salt(self):
        """Rotate the temporary salt."""
        self._rotating_salt = os.urandom(16).hex()
        self._salt_rotation_time = time.time()
        logger.info("Rotated ephemeral salt")


class AdversarialResistantEngine:
    """
    Wrapper that adds adversarial resistance to any detection engine.
    """

    def __init__(self):
        logger.info("Initializing Adversarial Resistance Module...")

        # Secret salt manager
        self.salt_manager = SecretSaltManager()

        # Randomized thresholds
        self.thresholds: Dict[str, SecureThreshold] = {
            "entropy_low": SecureThreshold(2.0, 0.3),
            "entropy_high": SecureThreshold(5.0, 0.5),
            "kl_divergence": SecureThreshold(2.0, 0.4),
            "lyapunov": SecureThreshold(0.1, 0.05),
            "risk_score": SecureThreshold(70.0, 5.0),
        }

        # Refresh schedule
        self._last_refresh = time.time()
        self._refresh_interval = 300  # 5 minutes

        # Multi-path strategies
        self._path_weights = [0.3, 0.3, 0.4]  # Randomized per request

        logger.info("Adversarial Resistance initialized")

    def get_threshold(self, name: str) -> float:
        """Get randomized threshold by name."""
        self._maybe_refresh_thresholds()

        if name in self.thresholds:
            return self.thresholds[name].get()
        return 0.0

    def _maybe_refresh_thresholds(self):
        """Refresh thresholds periodically."""
        if time.time() - self._last_refresh > self._refresh_interval:
            for threshold in self.thresholds.values():
                threshold.refresh()
            self._last_refresh = time.time()
            logger.debug("Refreshed randomized thresholds")

    def secure_compare(self, value: float, threshold_name: str) -> bool:
        """Compare value against randomized threshold."""
        threshold = self.get_threshold(threshold_name)

        # Add micro-jitter to comparison
        jitter = random.uniform(-0.01, 0.01) * threshold

        return value > (threshold + jitter)

    def compute_fingerprint(self, text: str) -> str:
        """Compute adversarial-resistant fingerprint of text."""
        # Normalize text
        normalized = text.lower().strip()

        # Add temporal component (changes hourly)
        hour_bucket = int(time.time() / 3600)
        temporal = str(hour_bucket)

        # Compute salted hash
        fingerprint = self.salt_manager.get_salted_hash(
            normalized + temporal,
            use_rotating=True
        )

        return fingerprint[:32]  # Truncated for efficiency

    def multi_path_decision(
        self,
        scores: Dict[str, float],
        weights: Optional[List[float]] = None
    ) -> tuple:
        """
        Make decision using multiple paths with random weighting.
        Prevents attackers from optimizing for a single path.
        """
        if weights is None:
            # Randomize weights each time
            weights = [random.random() for _ in range(len(scores))]
            total = sum(weights)
            weights = [w / total for w in weights]

        # Weighted average
        score_values = list(scores.values())
        weighted_score = sum(w * s for w, s in zip(weights, score_values))

        # Random path selection for threshold
        path_threshold = self.get_threshold("risk_score")

        is_threat = weighted_score > path_threshold

        return is_threat, weighted_score, weights

    def timing_safe_check(self, check_func: Callable, *args, **kwargs) -> tuple:
        """
        Execute check with timing jitter to prevent timing attacks.
        """
        # Add random delay before
        pre_delay = random.uniform(0.001, 0.01)  # 1-10ms
        time.sleep(pre_delay)

        # Execute check
        start = time.time()
        result = check_func(*args, **kwargs)
        elapsed = time.time() - start

        # Add random delay after to normalize timing
        target_time = 0.05  # 50ms target
        if elapsed < target_time:
            post_delay = target_time - elapsed + random.uniform(0, 0.01)
            time.sleep(post_delay)

        return result


def adversarial_resistant(threshold_name: str):
    """
    Decorator to add adversarial resistance to detection functions.

    Usage:
        @adversarial_resistant("entropy_low")
        def detect_low_entropy(text):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            engine = get_adversarial_engine()

            # Execute with timing protection
            result = engine.timing_safe_check(func, *args, **kwargs)

            # If result has score, compare with randomized threshold
            if isinstance(result, dict) and "score" in result:
                threshold = engine.get_threshold(threshold_name)
                result["threshold_used"] = threshold
                result["is_anomaly"] = result["score"] > threshold

            return result
        return wrapper
    return decorator


# Singleton
_adversarial_engine = None


def get_adversarial_engine() -> AdversarialResistantEngine:
    global _adversarial_engine
    if _adversarial_engine is None:
        _adversarial_engine = AdversarialResistantEngine()
    return _adversarial_engine


# Example usage documentation
"""
## Adversarial Resistance Usage

### 1. Randomized Thresholds
```python
engine = get_adversarial_engine()
threshold = engine.get_threshold("kl_divergence")
# Returns: ~2.0 ± 0.4 (different each time)
```

### 2. Secure Fingerprinting
```python
fingerprint = engine.compute_fingerprint("user prompt")
# Returns: salted, rotating hash
```

### 3. Multi-path Decisions
```python
scores = {"entropy": 30, "kl": 45, "lyapunov": 20}
is_threat, score, weights = engine.multi_path_decision(scores)
# Weights randomized each call
```

### 4. Timing-safe Checks
```python
result = engine.timing_safe_check(expensive_detection, prompt)
# All calls take ~50ms regardless of actual time
```

### 5. Decorator
```python
@adversarial_resistant("entropy_low")
def my_detection(text):
    return {"score": calculate_entropy(text)}
```
"""
