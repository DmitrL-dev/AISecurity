"""DomainConfig — declarative domain definitions for Micro-Model Swarm.

Each domain describes which session features to extract and how to normalize them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class NormMethod(str, Enum):
    """Feature normalization methods."""

    NONE = "none"
    MIN_MAX = "min_max"
    Z_SCORE = "z_score"


@dataclass(frozen=True)
class FeatureSpec:
    """Specification for a single feature."""

    name: str
    norm_method: NormMethod = NormMethod.MIN_MAX
    min_val: float = 0.0
    max_val: float = 1.0
    mean: float = 0.0
    std: float = 1.0
    default: float = 0.0

    def normalize(self, value: float) -> float:
        """Normalize a single value according to this spec."""
        if self.norm_method == NormMethod.NONE:
            return value
        if self.norm_method == NormMethod.MIN_MAX:
            denom = self.max_val - self.min_val
            if denom == 0:
                return 0.0
            return (value - self.min_val) / denom
        if self.norm_method == NormMethod.Z_SCORE:
            if self.std == 0:
                return 0.0
            return (value - self.mean) / self.std
        return value


@dataclass(frozen=True)
class DomainConfig:
    """Declarative domain configuration.

    Describes which features a domain needs and how to normalize them.
    """

    name: str
    features: tuple[FeatureSpec, ...]
    description: str = ""

    @property
    def n_features(self) -> int:
        return len(self.features)

    @property
    def feature_names(self) -> list[str]:
        return [f.name for f in self.features]

    def extract(self, session_data: dict[str, Any]) -> list[float]:
        """Extract and normalize features from session data.

        Missing features get their default values (normalized).
        """
        result: list[float] = []
        for spec in self.features:
            raw = session_data.get(spec.name, spec.default)
            try:
                val = float(raw)
            except (ValueError, TypeError):
                val = spec.default
            result.append(spec.normalize(val))
        return result

    def extract_raw(self, session_data: dict[str, Any]) -> list[float]:
        """Extract features without normalization."""
        result: list[float] = []
        for spec in self.features:
            raw = session_data.get(spec.name, spec.default)
            try:
                val = float(raw)
            except (ValueError, TypeError):
                val = spec.default
            result.append(val)
        return result
