"""
Engine Adapter — Wraps legacy brain.engines for SENTINEL Framework.

Provides backwards compatibility layer allowing existing 200+ engines
to work with the new BaseEngine interface without modification.
"""

from typing import Dict, Any, List, Optional, Type, Callable
import logging
import time

from sentinel.core.engine import BaseEngine, EngineResult, register_engine
from sentinel.core.finding import Finding, Severity, Confidence, FindingCollection
from sentinel.core.context import AnalysisContext

logger = logging.getLogger(__name__)


class LegacyEngineAdapter(BaseEngine):
    """
    Adapter that wraps legacy SENTINEL engines.
    
    Allows existing engines from brain.engines to work with
    the new framework without modification.
    
    Usage:
        >>> from brain.engines import InjectionDetector
        >>> adapted = LegacyEngineAdapter.wrap(InjectionDetector)
        >>> result = adapted.analyze(context)
    """
    
    # Set by wrap() classmethod
    _legacy_class: Type = None
    _legacy_instance: Any = None
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._legacy_instance = None
    
    def initialize(self) -> None:
        """Initialize the legacy engine."""
        if self._legacy_class:
            self._legacy_instance = self._legacy_class()
        self._initialized = True
    
    def analyze(self, context: AnalysisContext) -> EngineResult:
        """
        Analyze using legacy engine.
        
        Converts new context format to legacy format and back.
        """
        self.ensure_initialized()
        
        if not self._legacy_instance:
            return EngineResult.error_result(
                self.name, "Legacy engine not initialized"
            )
        
        start = time.time()
        
        try:
            # Call legacy analyze method
            # Most legacy engines expect (prompt, context_dict)
            legacy_context = self._to_legacy_context(context)
            
            if hasattr(self._legacy_instance, 'analyze'):
                legacy_result = self._legacy_instance.analyze(
                    context.prompt,
                    legacy_context
                )
            elif hasattr(self._legacy_instance, 'detect'):
                legacy_result = self._legacy_instance.detect(
                    context.prompt
                )
            else:
                return EngineResult.error_result(
                    self.name, "No analyze/detect method found"
                )
            
            # Convert legacy result to new format
            return self._from_legacy_result(
                legacy_result,
                (time.time() - start) * 1000
            )
            
        except Exception as e:
            logger.error(f"Legacy engine {self.name} error: {e}")
            return EngineResult.error_result(self.name, str(e))
    
    def _to_legacy_context(self, context: AnalysisContext) -> Dict[str, Any]:
        """Convert new context to legacy format."""
        return {
            "user_id": context.user_id,
            "session_id": context.session_id,
            "model": context.model,
            "history": [
                {"role": m.role, "content": m.content}
                for m in context.history
            ],
            **context.metadata,
        }
    
    def _from_legacy_result(
        self, 
        legacy_result: Any,
        execution_time_ms: float
    ) -> EngineResult:
        """Convert legacy result to new EngineResult."""
        findings = []
        
        # Handle dict result
        if isinstance(legacy_result, dict):
            is_safe = legacy_result.get("is_safe", True)
            risk_score = legacy_result.get("risk_score", 0.0)
            
            # Convert threats to findings
            threats = legacy_result.get("threats", [])
            patterns = legacy_result.get("patterns", [])
            indicators = legacy_result.get("indicators", [])
            
            for threat in (threats + patterns + indicators):
                if isinstance(threat, dict):
                    findings.append(self._threat_to_finding(threat))
                elif isinstance(threat, str):
                    findings.append(Finding(
                        engine=self.name,
                        severity=Severity.MEDIUM,
                        confidence=Confidence.MEDIUM,
                        title=threat,
                        description=threat,
                    ))
        
        # Handle bool result
        elif isinstance(legacy_result, bool):
            is_safe = legacy_result
            risk_score = 0.0 if is_safe else 0.8
        
        # Handle tuple (is_safe, score)
        elif isinstance(legacy_result, tuple):
            is_safe = legacy_result[0]
            risk_score = legacy_result[1] if len(legacy_result) > 1 else 0.0
        
        else:
            is_safe = True
            risk_score = 0.0
        
        return EngineResult(
            engine_name=self.name,
            is_safe=is_safe,
            risk_score=risk_score,
            findings=FindingCollection(findings=findings),
            execution_time_ms=execution_time_ms,
        )
    
    def _threat_to_finding(self, threat: Dict[str, Any]) -> Finding:
        """Convert legacy threat dict to Finding."""
        # Map legacy severity strings
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }
        
        severity_str = threat.get("severity", "medium").lower()
        severity = severity_map.get(severity_str, Severity.MEDIUM)
        
        confidence_str = threat.get("confidence", "medium").lower()
        confidence_map = {
            "high": Confidence.HIGH,
            "medium": Confidence.MEDIUM,
            "low": Confidence.LOW,
        }
        confidence = confidence_map.get(confidence_str, Confidence.MEDIUM)
        
        return Finding(
            engine=self.name,
            severity=severity,
            confidence=confidence,
            title=threat.get("title", threat.get("type", "Unknown")),
            description=threat.get("description", str(threat)),
            evidence=threat.get("evidence"),
            metadata=threat,
        )
    
    @classmethod
    def wrap(
        cls, 
        legacy_class: Type,
        name: str = None,
        category: str = "legacy",
        tier: int = 1,
    ) -> Type["LegacyEngineAdapter"]:
        """
        Create an adapter class for a legacy engine.
        
        Args:
            legacy_class: The legacy engine class to wrap
            name: Override engine name
            category: Engine category
            tier: Execution tier
            
        Returns:
            New class that wraps the legacy engine
        """
        class_name = f"{legacy_class.__name__}Adapter"
        
        # Create new adapter class
        adapter = type(class_name, (cls,), {
            "name": name or legacy_class.__name__.lower(),
            "category": category,
            "tier": tier,
            "description": getattr(legacy_class, '__doc__', '') or '',
            "_legacy_class": legacy_class,
        })
        
        return adapter


def adapt_all_engines() -> List[Type[BaseEngine]]:
    """
    Adapt all legacy brain.engines to BaseEngine.
    
    Returns list of adapted engine classes.
    """
    adapted = []
    
    try:
        from brain import engines as legacy_engines
        
        # Get all engine classes
        for name in dir(legacy_engines):
            obj = getattr(legacy_engines, name)
            if (
                isinstance(obj, type) and 
                hasattr(obj, 'analyze') and
                not name.startswith('_')
            ):
                try:
                    adapter = LegacyEngineAdapter.wrap(
                        obj,
                        name=name.lower(),
                        category=_guess_category(name),
                        tier=_guess_tier(name),
                    )
                    adapted.append(adapter)
                    register_engine(adapter)
                except Exception as e:
                    logger.warning(f"Failed to adapt {name}: {e}")
        
        logger.info(f"Adapted {len(adapted)} legacy engines")
        
    except ImportError:
        logger.debug("brain.engines not available")
    
    return adapted


def _guess_category(name: str) -> str:
    """Guess engine category from name."""
    name_lower = name.lower()
    
    if any(x in name_lower for x in ['inject', 'prompt']):
        return "injection"
    if any(x in name_lower for x in ['rag', 'agent', 'tool', 'memory']):
        return "agentic"
    if any(x in name_lower for x in ['tda', 'sheaf', 'chaos', 'entropy']):
        return "mathematical"
    if any(x in name_lower for x in ['pii', 'privacy', 'leak']):
        return "privacy"
    if any(x in name_lower for x in ['pickle', 'serial', 'supply']):
        return "supply_chain"
    
    return "general"


def _guess_tier(name: str) -> int:
    """Guess execution tier from name."""
    name_lower = name.lower()
    
    # Tier 0: Fast pattern matching
    if any(x in name_lower for x in ['yara', 'regex', 'pattern']):
        return 0
    
    # Tier 2: Heavy ML
    if any(x in name_lower for x in ['bert', 'transformer', 'embed', 'qwen']):
        return 2
    
    # Default: Tier 1
    return 1
