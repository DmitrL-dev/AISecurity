"""
SENTINEL Shield v2.0 — Detection Pipeline

Orchestrates multiple detection engines in parallel,
fuses results using weighted scoring, and returns
a unified verdict.
"""

import time
import logging
from dataclasses import dataclass, field
from .base import BaseEngine, EngineResult, ThreatMatch

logger = logging.getLogger("shield.pipeline")


@dataclass
class PipelineResult:
    """Unified result from all engines."""

    verdict: str  # "block", "warn", "allow"
    risk_score: float  # 0.0 - 1.0 (fused)
    threats: list[ThreatMatch] = field(default_factory=list)
    engine_results: list[EngineResult] = field(default_factory=list)
    latency_ms: float = 0.0
    engines_checked: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "risk_score": round(self.risk_score, 4),
            "latency_ms": round(self.latency_ms, 2),
            "engines_checked": self.engines_checked,
            "threats": [
                {
                    "type": t.threat_type,
                    "risk": round(t.risk_score, 3),
                    "engine": t.engine,
                    "description": t.description,
                    "matched_text": t.matched_text[:80] if t.matched_text else "",
                    "category": t.category,
                }
                for t in self.threats
            ],
            "engine_details": [
                {
                    "name": er.engine_name,
                    "risk_score": round(er.risk_score, 3),
                    "threats_count": len(er.threats),
                    "latency_ms": round(er.latency_ms, 2),
                    "error": er.error,
                }
                for er in self.engine_results
            ],
        }


class DetectionPipeline:
    """
    Multi-engine detection pipeline.

    Runs all enabled engines, fuses results using max-weighted scoring.
    """

    def __init__(
        self,
        engines: list[BaseEngine] | None = None,
        block_threshold: float = 0.85,
        warn_threshold: float = 0.50,
    ):
        self.engines: list[BaseEngine] = engines or []
        self.block_threshold = block_threshold
        self.warn_threshold = warn_threshold
        self._total_requests = 0

    def add_engine(self, engine: BaseEngine):
        self.engines.append(engine)
        logger.info(f"Pipeline: added engine '{engine.name}' (weight={engine.weight})")

    def remove_engine(self, name: str):
        self.engines = [e for e in self.engines if e.name != name]

    def get_engine(self, name: str) -> BaseEngine | None:
        return next((e for e in self.engines if e.name == name), None)

    def analyze(self, text: str) -> PipelineResult:
        """
        Run all engines and fuse results.

        Scoring strategy: Weighted maximum.
        The highest weighted risk from any engine determines the final score.
        """
        start = time.perf_counter()
        self._total_requests += 1

        all_threats: list[ThreatMatch] = []
        engine_results: list[EngineResult] = []
        engines_checked: list[str] = []

        # Run engines sequentially (async version would use gather)
        for engine in self.engines:
            result = engine.safe_analyze(text)
            engine_results.append(result)
            engines_checked.append(engine.name)

            if result.has_threats:
                all_threats.extend(result.threats)

        # Fuse scores: weighted maximum
        fused_risk = 0.0
        for result in engine_results:
            engine = next(
                (e for e in self.engines if e.name == result.engine_name), None
            )
            if engine and result.risk_score > 0:
                weighted = result.risk_score * engine.weight
                fused_risk = max(fused_risk, weighted)

        # Clamp to 1.0
        fused_risk = min(fused_risk, 1.0)

        # Determine verdict
        if fused_risk >= self.block_threshold:
            verdict = "block"
        elif fused_risk >= self.warn_threshold:
            verdict = "warn"
        else:
            verdict = "allow"

        # Sort threats by risk descending
        all_threats.sort(key=lambda t: t.risk_score, reverse=True)

        total_latency = (time.perf_counter() - start) * 1000

        return PipelineResult(
            verdict=verdict,
            risk_score=fused_risk,
            threats=all_threats,
            engine_results=engine_results,
            latency_ms=total_latency,
            engines_checked=engines_checked,
        )

    def stats(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "block_threshold": self.block_threshold,
            "warn_threshold": self.warn_threshold,
            "engines": [e.stats() for e in self.engines],
        }
