"""
Pipeline — Analysis pipeline with tiered parallel execution.

Implements SENTINEL's tiered architecture:
- Tier 0: Early exit (YARA, regex) - <10ms
- Tier 1: Fast engines - ~50ms
- Tier 2: Heavy engines (ML) - ~200ms
- Tier 3: Deep analysis - optional
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from concurrent.futures import ThreadPoolExecutor
import logging

from sentinel.core.finding import Finding, FindingCollection
from sentinel.core.context import AnalysisContext
from sentinel.core.engine import BaseEngine, EngineResult

logger = logging.getLogger(__name__)


class Stage(Enum):
    """Analysis pipeline stages."""
    PREPROCESS = "preprocess"
    EARLY_EXIT = "early_exit"       # Tier 0: <10ms
    TIER1_FAST = "tier1_fast"       # Tier 1: ~50ms
    TIER2_HEAVY = "tier2_heavy"     # Tier 2: ~200ms
    TIER3_DEEP = "tier3_deep"       # Tier 3: optional
    AGGREGATE = "aggregate"          # Meta-judge
    POSTPROCESS = "postprocess"


@dataclass
class PipelineConfig:
    """Configuration for analysis pipeline."""
    # Execution
    parallel: bool = True
    max_workers: int = 4
    
    # Timeouts (ms)
    tier0_timeout_ms: float = 10.0
    tier1_timeout_ms: float = 50.0
    tier2_timeout_ms: float = 200.0
    total_timeout_ms: float = 500.0
    
    # Early exit
    early_exit_enabled: bool = True
    early_exit_threshold: float = 0.9
    
    # Filtering
    min_confidence: float = 0.0
    min_severity: str = "info"


@dataclass
class PipelineResult:
    """Result from full pipeline analysis."""
    is_safe: bool
    risk_score: float
    findings: FindingCollection
    engine_results: List[EngineResult]
    
    # Execution stats
    total_time_ms: float
    engines_executed: int
    early_exit: bool = False
    
    # Metadata
    context_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def finding_count(self) -> int:
        return self.findings.count
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "findings": self.findings.to_dict(),
            "total_time_ms": self.total_time_ms,
            "engines_executed": self.engines_executed,
            "early_exit": self.early_exit,
            "context_id": self.context_id,
        }


class Pipeline:
    """
    Configurable analysis pipeline with tiered execution.
    
    Executes engines in parallel tiers with early exit support:
    1. Tier 0 (Early Exit): Fast pattern checks
    2. Tier 1 (Fast): Lightweight analysis
    3. Tier 2 (Heavy): ML-based analysis
    4. Aggregate: Combine results
    
    Usage:
        >>> pipeline = Pipeline(engines=[...])
        >>> result = pipeline.analyze_sync(context)
        >>> # or async
        >>> result = await pipeline.analyze(context)
    """
    
    def __init__(
        self,
        engines: List[BaseEngine] = None,
        config: PipelineConfig = None,
    ):
        self.engines = engines or []
        self.config = config or PipelineConfig()
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.max_workers
        )
        
        # Group engines by tier
        self._tier_engines = self._group_by_tier()
    
    def _group_by_tier(self) -> Dict[int, List[BaseEngine]]:
        """Group engines by their tier."""
        tiers = {0: [], 1: [], 2: [], 3: []}
        for engine in self.engines:
            tier = getattr(engine, 'tier', 1)
            if tier in tiers:
                tiers[tier].append(engine)
        return tiers
    
    def add_engine(self, engine: BaseEngine) -> None:
        """Add engine to pipeline."""
        self.engines.append(engine)
        self._tier_engines = self._group_by_tier()
    
    def analyze_sync(self, context: AnalysisContext) -> PipelineResult:
        """Synchronous analysis (runs async in thread)."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.analyze(context))
        finally:
            loop.close()
    
    async def analyze(self, context: AnalysisContext) -> PipelineResult:
        """
        Run full analysis pipeline.
        
        Executes engines in tiers, with early exit if high-confidence
        threat is detected.
        """
        start_time = time.time()
        all_results: List[EngineResult] = []
        early_exit = False
        
        # Tier 0: Early exit checks
        tier0_results = await self._run_tier(0, context)
        all_results.extend(tier0_results)
        
        if self._should_exit(tier0_results):
            early_exit = True
        else:
            # Tier 1: Fast engines
            tier1_results = await self._run_tier(1, context)
            all_results.extend(tier1_results)
            
            if self._should_exit(tier1_results):
                early_exit = True
            else:
                # Tier 2: Heavy engines
                tier2_results = await self._run_tier(2, context)
                all_results.extend(tier2_results)
        
        # Aggregate results
        total_time_ms = (time.time() - start_time) * 1000
        
        return self._aggregate_results(
            all_results,
            total_time_ms,
            context.request_id,
            early_exit,
        )
    
    async def _run_tier(
        self,
        tier: int,
        context: AnalysisContext
    ) -> List[EngineResult]:
        """Run all engines in a tier."""
        engines = self._tier_engines.get(tier, [])
        if not engines:
            return []
        
        if self.config.parallel:
            # Run in parallel
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(
                    self._executor,
                    engine.analyze_safe,
                    context
                )
                for engine in engines
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    valid_results.append(
                        EngineResult.error_result(
                            engines[i].name, str(result)
                        )
                    )
                else:
                    valid_results.append(result)
            return valid_results
        else:
            # Run sequentially
            return [e.analyze_safe(context) for e in engines]
    
    def _should_exit(self, results: List[EngineResult]) -> bool:
        """Check if early exit should be triggered."""
        if not self.config.early_exit_enabled:
            return False
        
        for result in results:
            if result.risk_score >= self.config.early_exit_threshold:
                logger.info(
                    f"Early exit triggered by {result.engine_name} "
                    f"(risk={result.risk_score})"
                )
                return True
        return False
    
    def _aggregate_results(
        self,
        results: List[EngineResult],
        total_time_ms: float,
        context_id: Optional[str],
        early_exit: bool,
    ) -> PipelineResult:
        """Aggregate results from all engines."""
        # Collect all findings
        all_findings = FindingCollection()
        for result in results:
            all_findings.extend(result.findings.findings)
        
        # Calculate aggregate risk score
        if results:
            risk_score = max(r.risk_score for r in results)
        else:
            risk_score = 0.0
        
        is_safe = risk_score < 0.5
        
        return PipelineResult(
            is_safe=is_safe,
            risk_score=risk_score,
            findings=all_findings,
            engine_results=results,
            total_time_ms=total_time_ms,
            engines_executed=len(results),
            early_exit=early_exit,
            context_id=context_id,
        )


# Default pipeline (lazy initialized)
_default_pipeline: Optional[Pipeline] = None


def get_default_pipeline(engines: List[str] = None) -> Pipeline:
    """Get or create default pipeline."""
    global _default_pipeline
    
    if _default_pipeline is None:
        # TODO: Load engines from registry
        _default_pipeline = Pipeline(engines=[])
    
    return _default_pipeline


def create_pipeline(
    engines: List[BaseEngine] = None,
    **config_kwargs
) -> Pipeline:
    """Create new pipeline with configuration."""
    config = PipelineConfig(**config_kwargs)
    return Pipeline(engines=engines or [], config=config)
