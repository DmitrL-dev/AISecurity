"""
SENTINEL Framework — AI Security Framework

The pytest of AI Security: Protect and Test AI systems.
"""

__version__ = "1.0.0"

# Core imports (lazy loaded)
from sentinel.core.finding import Finding, Severity, Confidence
from sentinel.core.context import AnalysisContext
from sentinel.core.engine import BaseEngine, EngineResult
from sentinel.core.pipeline import Pipeline, Stage

# Public API
__all__ = [
    # Core
    "Finding",
    "Severity", 
    "Confidence",
    "AnalysisContext",
    "BaseEngine",
    "EngineResult",
    "Pipeline",
    "Stage",
    # Convenience
    "scan",
    "guard",
]


def scan(
    prompt: str,
    response: str = None,
    engines: list = None,
    **kwargs
) -> "EngineResult":
    """
    Scan prompt/response for security threats.
    
    Args:
        prompt: Input prompt to analyze
        response: Optional LLM response to analyze
        engines: List of engine names to use (default: all)
        
    Returns:
        EngineResult with findings
        
    Example:
        >>> from sentinel import scan
        >>> result = scan("Ignore previous instructions")
        >>> print(result.is_safe)  # False
    """
    from sentinel.core.pipeline import get_default_pipeline
    
    ctx = AnalysisContext(
        prompt=prompt,
        response=response,
        **kwargs
    )
    
    pipeline = get_default_pipeline(engines=engines)
    return pipeline.analyze_sync(ctx)


def guard(engines: list = None, on_threat: str = "raise"):
    """
    Decorator to guard functions with SENTINEL.
    
    Args:
        engines: List of engine names to use
        on_threat: Action on threat: "raise", "log", "block"
        
    Example:
        >>> @guard(engines=["injection", "pii"])
        ... def my_llm_call(prompt):
        ...     return openai.chat(prompt)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Find prompt in args
            prompt = args[0] if args else kwargs.get("prompt", "")
            
            result = scan(prompt, engines=engines)
            
            if not result.is_safe:
                if on_threat == "raise":
                    from sentinel.core.exceptions import ThreatDetected
                    raise ThreatDetected(result)
                elif on_threat == "block":
                    return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
