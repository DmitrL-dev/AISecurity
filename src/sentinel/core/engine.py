"""
BaseEngine — Abstract base class for all SENTINEL engines.

Provides unified interface for:
- Detection engines (defense)
- Attack engines (offense)
- Analysis engines (observability)

All 200+ SENTINEL engines inherit from this base.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Type
from datetime import datetime
import time
import logging

from sentinel.core.finding import Finding, Severity, Confidence, FindingCollection
from sentinel.core.context import AnalysisContext

logger = logging.getLogger(__name__)


@dataclass
class EngineResult:
    """
    Result from engine analysis.
    
    Unified result format for all engines containing:
    - Safety determination
    - Risk score
    - Findings list
    - Execution metrics
    """
    engine_name: str
    is_safe: bool
    risk_score: float  # 0.0 - 1.0
    findings: FindingCollection = field(default_factory=FindingCollection)
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Error handling
    error: Optional[str] = None
    success: bool = True
    
    @property
    def finding_count(self) -> int:
        """Number of findings."""
        return self.findings.count
    
    @property
    def max_severity(self) -> Optional[Severity]:
        """Highest severity finding."""
        return self.findings.max_severity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "engine_name": self.engine_name,
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "findings": self.findings.to_dict(),
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
            "error": self.error,
            "success": self.success,
        }
    
    @classmethod
    def safe(cls, engine_name: str, execution_time_ms: float = 0.0) -> "EngineResult":
        """Create safe result with no findings."""
        return cls(
            engine_name=engine_name,
            is_safe=True,
            risk_score=0.0,
            execution_time_ms=execution_time_ms,
        )
    
    @classmethod
    def error_result(
        cls, 
        engine_name: str, 
        error: str
    ) -> "EngineResult":
        """Create error result."""
        return cls(
            engine_name=engine_name,
            is_safe=True,  # Fail open
            risk_score=0.0,
            error=error,
            success=False,
        )


class BaseEngine(ABC):
    """
    Abstract base class for all SENTINEL detection engines.
    
    Subclasses must implement:
        - analyze(context) -> EngineResult
    
    Optional overrides:
        - initialize() - for lazy loading heavy models
        - analyze_batch() - for batch processing
    
    Example:
        >>> class MyEngine(BaseEngine):
        ...     name = "my_engine"
        ...     category = "custom"
        ...     
        ...     def analyze(self, context):
        ...         findings = []
        ...         if "bad" in context.prompt:
        ...             findings.append(Finding(...))
        ...         return self._create_result(findings)
    """
    
    # Engine metadata (override in subclasses)
    name: str = "base_engine"
    version: str = "1.0.0"
    category: str = "general"
    description: str = "Base engine"
    
    # Engine capabilities
    supports_prompt: bool = True
    supports_response: bool = False
    supports_multimodal: bool = False
    supports_batch: bool = False
    
    # Performance hints
    tier: int = 1  # 0=early_exit, 1=fast, 2=heavy, 3=deep
    typical_latency_ms: float = 10.0
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize engine with optional configuration.
        
        Args:
            config: Engine-specific configuration dictionary
        """
        self.config = config or {}
        self._initialized = False
        self._logger = logging.getLogger(
            f"sentinel.engine.{self.name}"
        )
    
    def initialize(self) -> None:
        """
        Lazy initialization for heavy models.
        
        Override this method to load ML models, compile patterns, etc.
        Called automatically on first analyze() call.
        """
        self._initialized = True
    
    def ensure_initialized(self) -> None:
        """Ensure engine is initialized."""
        if not self._initialized:
            self._logger.info(f"Initializing {self.name}...")
            start = time.time()
            self.initialize()
            elapsed = (time.time() - start) * 1000
            self._logger.info(
                f"Initialized {self.name} in {elapsed:.1f}ms"
            )
    
    @abstractmethod
    def analyze(self, context: AnalysisContext) -> EngineResult:
        """
        Main analysis method.
        
        Args:
            context: AnalysisContext with prompt, response, history, etc.
            
        Returns:
            EngineResult with findings and risk score
        """
        pass
    
    def analyze_safe(self, context: AnalysisContext) -> EngineResult:
        """
        Analyze with error handling.
        
        Catches exceptions and returns error result instead of raising.
        """
        try:
            self.ensure_initialized()
            start = time.time()
            result = self.analyze(context)
            result.execution_time_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            self._logger.error(f"Engine {self.name} error: {e}")
            return EngineResult.error_result(self.name, str(e))
    
    def analyze_batch(
        self, 
        contexts: List[AnalysisContext]
    ) -> List[EngineResult]:
        """
        Batch analysis for efficiency.
        
        Override for engines that benefit from batching (e.g., ML models).
        Default implementation processes sequentially.
        """
        return [self.analyze(ctx) for ctx in contexts]
    
    def _create_result(
        self,
        findings: List[Finding],
        execution_time_ms: float = 0.0,
        metadata: Dict[str, Any] = None,
    ) -> EngineResult:
        """
        Helper to create EngineResult from findings.
        """
        collection = FindingCollection(findings=findings)
        
        # Calculate risk score from findings
        risk_score = collection.max_risk_score
        is_safe = risk_score < 0.5
        
        return EngineResult(
            engine_name=self.name,
            is_safe=is_safe,
            risk_score=risk_score,
            findings=collection,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
        )
    
    def _create_finding(
        self,
        severity: Severity,
        confidence: Confidence,
        title: str,
        description: str,
        evidence: Optional[str] = None,
        **kwargs
    ) -> Finding:
        """
        Helper to create Finding.
        """
        return Finding(
            engine=self.name,
            severity=severity,
            confidence=confidence,
            title=title,
            description=description,
            evidence=evidence,
            **kwargs
        )
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, v{self.version})>"


# Engine registry
_engine_registry: Dict[str, Type[BaseEngine]] = {}


def register_engine(engine_class: Type[BaseEngine]) -> Type[BaseEngine]:
    """
    Decorator to register an engine class.
    
    Example:
        >>> @register_engine
        ... class MyEngine(BaseEngine):
        ...     name = "my_engine"
    """
    _engine_registry[engine_class.name] = engine_class
    return engine_class


def get_engine(name: str) -> Type[BaseEngine]:
    """Get engine class by name."""
    if name not in _engine_registry:
        raise KeyError(f"Engine '{name}' not found. Available: {list(_engine_registry.keys())}")
    return _engine_registry[name]


def list_engines() -> List[str]:
    """List all registered engine names."""
    return list(_engine_registry.keys())


def get_engines_by_category(category: str) -> List[Type[BaseEngine]]:
    """Get all engines in a category."""
    return [
        e for e in _engine_registry.values()
        if e.category == category
    ]
