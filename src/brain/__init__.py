"""
SENTINEL Community Edition - AI Security Platform

Open source protection for LLM applications.

Engines:
- 15 detection engines for prompt injection, PII, VLM, RAG, and more
"""

__version__ = "1.0.0"
__author__ = "Dmitry Labintsev"
__license__ = "Apache-2.0"

from .engines import (
    InjectionDetector,
    YaraEngine,
    BehavioralAnalyzer,
    PIIDetector,
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
    "InjectionDetector",
    "YaraEngine",
    "BehavioralAnalyzer",
    "PIIDetector",
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
