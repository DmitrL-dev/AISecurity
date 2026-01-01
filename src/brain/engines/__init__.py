"""
SENTINEL Community Edition - Detection Engines

Core security engines for LLM protection.
"""

# Core Detection Engines
from .injection import InjectionEngine
from .yara_engine import YaraEngine
from .behavioral import BehavioralEngine
from .pii import PIIEngine
from .query import QueryEngine
from .language import LanguageEngine

# System Prompt Protection
from .prompt_guard import SystemPromptGuard

# Hallucination Detection
from .hallucination import HallucinationEngine

# Strange Math
from .tda_enhanced import TDAEnhancedEngine
from .sheaf_coherence import SheafCoherenceEngine

# VLM Protection
from .visual_content import VisualContentAnalyzer
from .cross_modal import CrossModalConsistency

# Agent Security
from .rag_guard import RAGGuard
from .probing_detection import ProbingDetector

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
from .streaming import StreamingEngine

# MoE Security (Jan 2026 R&D - GateBreaker defense)
from .moe_guard import MoEGuardEngine

# Evolutive Attack Detection (Jan 2026 R&D - LLM-Virus defense)
from .evolutive_attack_detector import EvolutiveAttackDetector

# Backward compatibility aliases (legacy names)
InjectionDetector = InjectionEngine
BehavioralAnalyzer = BehavioralEngine
PIIDetector = PIIEngine
QueryValidator = QueryEngine
LanguageDetector = LanguageEngine
HallucinationDetector = HallucinationEngine
PromptGuard = SystemPromptGuard
TDAEnhanced = TDAEnhancedEngine
SheafCoherence = SheafCoherenceEngine
VisualContent = VisualContentAnalyzer
CrossModal = CrossModalConsistency
StreamingGuard = StreamingEngine
ProbingDetection = ProbingDetector

__all__ = [
    # Core Engines
    "InjectionEngine",
    "YaraEngine",
    "BehavioralEngine",
    "PIIEngine",
    "QueryEngine",
    "LanguageEngine",
    "SystemPromptGuard",
    "HallucinationEngine",
    "TDAEnhancedEngine",
    "SheafCoherenceEngine",
    "VisualContentAnalyzer",
    "CrossModalConsistency",
    "ProbingDetector",
    "StreamingEngine",
    # Backward compat aliases
    "InjectionDetector",
    "BehavioralAnalyzer",
    "PIIDetector",
    "QueryValidator",
    "LanguageDetector",
    "HallucinationDetector",
    "PromptGuard",
    "TDAEnhanced",
    "SheafCoherence",
    "VisualContent",
    "CrossModal",
    "StreamingGuard",
    "ProbingDetection",
    # Other engines
    "RAGGuard",
    "PickleSecurityEngine",
    "PyTorchModelScanner",
    "ContextCompressionEngine",
    "TaskComplexityAnalyzer",
    "SentinelRuleEngine",
    "SerializationSecurityEngine",
    "ToolHijackerDetector",
    "MCPToolValidator",
    "EchoChamberDetector",
    "RAGPoisoningDetector",
    "IdentityPrivilegeAbuseDetector",
    "MemoryPoisoningDetector",
    "DarkPatternDetector",
    "PolymorphicPromptAssembler",
    "MoEGuardEngine",
    "EvolutiveAttackDetector",
]
