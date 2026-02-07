"""
SENTINEL Community Edition - Detection Engines

Core security engines for LLM protection.
"""

# Core Detection Engines
# NOTE: InjectionEngine and PIIEngine now in Rust Core (sentinel_core)
from .yara_engine import YaraEngine
from .behavioral import BehavioralEngine
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

# R&D Jan 5 2026 - New Attack Vectors
from .adversarial_poetry_detector import AdversarialPoetryDetector
from .advertisement_embedding_detector import AdvertisementEmbeddingDetector
from .web_agent_manipulation_detector import WebAgentManipulationDetector

# Auto-generated engine
from .konni_adopts_social_engineering_detector import (
    KonniAdoptsSocialEngineeringDetector,
)

# Auto-generated engine
from .voidlink_evidence_malware_detector import VoidlinkEvidenceMalwareDetector

# Auto-generated engine
from .dns_overdos_other_detector import DnsOverdosOtherDetector

# Auto-generated engine
from .exploitation_vulnerability_other_detector import (
    ExploitationVulnerabilityOtherDetector,
)

# Auto-generated engine (renamed from 2nd_february to avoid invalid identifier)
from .february_2nd_malware_detector import SecondFebruaryMalwareDetector

# Auto-generated engine
from .konni_adopts_phishing_detector import KonniAdoptsPhishingDetector

# Auto-generated engine
from .unveiling_voidlink_malware_detector import UnveilingVoidlinkMalwareDetector

# Auto-generated engine
from .sicarii_ransomware_malware_detector import SicariiRansomwareMalwareDetector

# Auto-generated engine
from .inside_gobruteforcer_other_detector import InsideGobruteforcerOtherDetector

# Auto-generated engine
from .detecting_backdoored_other_detector import DetectingBackdooredOtherDetector

# Operational Context Injection (Feb 2026 R&D — Lakera Guard blind spot)
from .operational_context_injection import OperationalContextInjectionDetector


# Backward compatibility aliases (legacy names)
# NOTE: InjectionDetector and PIIDetector now in Rust Core
BehavioralAnalyzer = BehavioralEngine
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
    # Core Engines (InjectionEngine and PIIEngine in Rust Core)
    "YaraEngine",
    "BehavioralEngine",
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
    # Backward compat aliases (InjectionDetector/PIIDetector in Rust Core)
    "BehavioralAnalyzer",
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
    # R&D Jan 5 2026 - New Attack Vectors
    "AdversarialPoetryDetector",
    "AdvertisementEmbeddingDetector",
    "WebAgentManipulationDetector",
    # Auto-generated
    "KonniAdoptsSocialEngineeringDetector",
    # Auto-generated
    "VoidlinkEvidenceMalwareDetector",
    # Auto-generated
    "DnsOverdosOtherDetector",
    # Auto-generated
    "ExploitationVulnerabilityOtherDetector",
    "SecondFebruaryMalwareDetector",
    # Auto-generated
    "KonniAdoptsPhishingDetector",
    # Auto-generated
    "UnveilingVoidlinkMalwareDetector",
    # Auto-generated
    "SicariiRansomwareMalwareDetector",
    # Auto-generated
    "InsideGobruteforcerOtherDetector",
    # Auto-generated
    "DetectingBackdooredOtherDetector",
    # OCI — Operational Context Injection (Feb 2026)
    "OperationalContextInjectionDetector",
]
