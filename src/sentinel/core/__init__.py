"""
SENTINEL Core — Core abstractions package.
"""

from sentinel.core.finding import Finding, Severity, Confidence
from sentinel.core.context import AnalysisContext
from sentinel.core.engine import BaseEngine, EngineResult
from sentinel.core.pipeline import Pipeline, Stage

__all__ = [
    "Finding",
    "Severity",
    "Confidence",
    "AnalysisContext",
    "BaseEngine",
    "EngineResult",
    "Pipeline",
    "Stage",
]
