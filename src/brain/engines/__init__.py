"""
SENTINEL Community Edition - Detection Engines

15 open source engines for LLM security.
"""

# Classic Detection
from .injection import InjectionDetector
from .yara_engine import YaraEngine
from .behavioral import BehavioralAnalyzer
from .pii import PIIDetector
from .query import QueryValidator
from .language import LanguageDetector

# NLP Guard
from .prompt_guard import PromptGuard
from .hallucination import HallucinationDetector

# Strange Math (Basic)
from .tda_enhanced import TDAEnhanced
from .sheaf_coherence import SheafCoherence

# VLM Protection
from .visual_content import VisualContent
from .cross_modal import CrossModal

# Agent Security
from .rag_guard import RAGGuard
from .probing_detection import ProbingDetection

# Supply Chain Security
from .pickle_security import PickleSecurityEngine, PyTorchModelScanner

# Context Management
from .context_compression import ContextCompressionEngine

# Orchestration
from .task_complexity import TaskComplexityAnalyzer

# Rule Engine (Colang-inspired)
from .rule_dsl import SentinelRuleEngine

# Serialization Security (CVE-2025-68664 LangGrinch)
from .serialization_security import SerializationSecurityEngine

# Tool Security (ToolHijacker, Log-To-Leak)
from .tool_hijacker_detector import ToolHijackerDetector, MCPToolValidator

# Multi-Turn Attack Detection (Echo Chamber)
from .echo_chamber_detector import EchoChamberDetector

# RAG Security (Dec 2025 R&D)
from .rag_poisoning_detector import RAGPoisoningDetector

# Agent Security - OWASP Agentic AI (Dec 2025 R&D)
from .identity_privilege_detector import IdentityPrivilegeAbuseDetector
from .memory_poisoning_detector import MemoryPoisoningDetector

# Dark Pattern Defense (Dec 2025 R&D - DECEPTICON)
from .dark_pattern_detector import DarkPatternDetector

# Polymorphic Prompt Defense (Dec 2025 R&D)
from .polymorphic_prompt_assembler import PolymorphicPromptAssembler

# Streaming
from .streaming import StreamingGuard

__all__ = [
    # Classic
    "InjectionDetector",
    "YaraEngine",
    "BehavioralAnalyzer",
    "PIIDetector",
    "QueryValidator",
    "LanguageDetector",
    # NLP
    "PromptGuard",
    "HallucinationDetector",
    # Math
    "TDAEnhanced",
    "SheafCoherence",
    # VLM
    "VisualContent",
    "CrossModal",
    # Agent
    "RAGGuard",
    "ProbingDetection",
    # Supply Chain
    "PickleSecurityEngine",
    "PyTorchModelScanner",
    # Context Management
    "ContextCompressionEngine",
    # Orchestration
    "TaskComplexityAnalyzer",
    # Rule Engine
    "SentinelRuleEngine",
    # Serialization Security (Dec 2025 R&D)
    "SerializationSecurityEngine",
    # Tool Security (Dec 2025 R&D)
    "ToolHijackerDetector",
    "MCPToolValidator",
    # Multi-Turn Attack Detection (Dec 2025 R&D)
    "EchoChamberDetector",
    # RAG Security (Dec 2025 R&D)
    "RAGPoisoningDetector",
    # Agent Security - OWASP Agentic AI (Dec 2025 R&D)
    "IdentityPrivilegeAbuseDetector",
    "MemoryPoisoningDetector",
    # Dark Pattern Defense (Dec 2025 R&D)
    "DarkPatternDetector",
    # Polymorphic Prompt Defense (Dec 2025 R&D)
    "PolymorphicPromptAssembler",
    # Streaming
    "StreamingGuard",
]
