"""
SENTINEL Community Edition - AI Security Platform

Open source protection for LLM applications.

Engines:
- 15 detection engines for prompt injection, PII, VLM, RAG, and more
- NOTE: InjectionEngine and PIIEngine are now in Rust Core (sentinel_core)
"""

__version__ = "1.0.0"
__author__ = "Dmitry Labintsev"
__license__ = "Apache-2.0"

# Re-export SentinelAnalyzer from core for backward compatibility
from .core.analyzer import SentinelAnalyzer

# NOTE: InjectionDetector and PIIDetector removed - now in Rust Core (sentinel_core)
from .engines import (
    YaraEngine,
    BehavioralAnalyzer,
    QueryValidator,
    LanguageDetector,
    PromptGuard,
    HallucinationDetector,
    TDAEnhanced,
    SheafCoherence,
    VisualContent,
    CrossModal,
    RAGGuard,
    ProbingDetection,
    StreamingGuard,
)

__all__ = [
    "SentinelAnalyzer",
    # InjectionDetector and PIIDetector now in Rust Core
    "YaraEngine",
    "BehavioralAnalyzer",
    "QueryValidator",
    "LanguageDetector",
    "PromptGuard",
    "HallucinationDetector",
    "TDAEnhanced",
    "SheafCoherence",
    "VisualContent",
    "CrossModal",
    "RAGGuard",
    "ProbingDetection",
    "StreamingGuard",
]
