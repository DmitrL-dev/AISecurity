"""
Synced Defense Engines

Auto-generated from Strike attack modules.
Total: 13 detectors + 1 combined + 9 security engines (Jan 2026).

Generated: 2025-12-29T21:24:05.508423
Updated: 2026-01-09 (Added SandboxMonitor)
"""

from .doublespeak_detector import DoublespeakDetector
from .cognitive_overload_detector import CognitiveOverloadDetector
from .crescendo_detector import CrescendoDetector
from .skeleton_key_detector import SkeletonKeyDetector
from .manyshot_detector import ManyshotDetector
from .artprompt_detector import ArtpromptDetector
from .policy_puppetry_detector import PolicyPuppetryDetector
from .tokenizer_exploit_detector import TokenizerExploitDetector
from .bad_likert_detector import BadLikertDetector
from .deceptive_delight_detector import DeceptiveDelightDetector
from .godel_attack_detector import GodelAttackDetector
from .gestalt_reversal_detector import GestaltReversalDetector
from .anti_troll_detector import AntiTrollDetector
from .synced_attack_detector import SyncedAttackDetector, detect_synced_attacks

# Security Engines (Jan 2026 R&D)
from .supply_chain_scanner import SupplyChainScanner, scan as supply_chain_scan
from .mcp_security_monitor import MCPSecurityMonitor, analyze as mcp_analyze
from .agentic_behavior_analyzer import (
    AgenticBehaviorAnalyzer,
    analyze as agentic_analyze,
)
from .sleeper_agent_detector import SleeperAgentDetector, detect as sleeper_detect
from .model_integrity_verifier import ModelIntegrityVerifier, verify as model_verify

# Additional Engines (Jan 2026 R&D Part 2)
from .guardrails_engine import GuardrailsEngine, check_input, check_output
from .prompt_leak_detector import PromptLeakDetector, detect as leak_detect

# Sandbox Escape Monitor (Jan 9 2026)
from .sandbox_monitor import SandboxMonitor, analyze as sandbox_analyze

# Marketplace Skill Validator (Jan 9 2026)
from .marketplace_skill_validator import (
    MarketplaceSkillValidator,
    validate as skill_validate,
)

# R&D Daily Research Engines (Jan 25 2026)
from .skill_worm_detector import SkillWormDetector, detect_skill_worm
from .ide_extension_detector import (
    IDEExtensionDetector,
    detect_malicious_extension as detect_ide_extension,
)
from .ai_generated_malware_detector import AIGeneratedMalwareDetector
from .mcp_auth_bypass_detector import MCPAuthBypassDetector
from .advanced_injection_detector import (
    AdvancedInjectionDetector,
    detect_advanced_injection,
)
from .agent_autonomy_level_analyzer import (
    AgentAutonomyLevelAnalyzer,
    analyze_agent_autonomy,
)
from .multi_agent_cascade_detector import MultiAgentCascadeDetector, detect_cascade
from .agentic_governance_compliance import (
    AgenticGovernanceCompliance,
    check_governance_compliance,
)

__all__ = [
    # Original detectors
    "SyncedAttackDetector",
    "detect_synced_attacks",
    # Security engines (2026)
    "SupplyChainScanner",
    "supply_chain_scan",
    "MCPSecurityMonitor",
    "mcp_analyze",
    "AgenticBehaviorAnalyzer",
    "agentic_analyze",
    "SleeperAgentDetector",
    "sleeper_detect",
    "ModelIntegrityVerifier",
    "model_verify",
    # Additional engines (2026 Part 2)
    "GuardrailsEngine",
    "check_input",
    "check_output",
    "PromptLeakDetector",
    "leak_detect",
    # Sandbox Monitor (Jan 9 2026)
    "SandboxMonitor",
    "sandbox_analyze",
    # Marketplace Skill Validator (Jan 9 2026)
    "MarketplaceSkillValidator",
    "skill_validate",
    # R&D Daily Research (Jan 25 2026)
    "SkillWormDetector",
    "detect_skill_worm",
    "IDEExtensionDetector",
    "detect_ide_extension",
    "AIGeneratedMalwareDetector",
    "MCPAuthBypassDetector",
    "AdvancedInjectionDetector",
    "detect_advanced_injection",
    "AgentAutonomyLevelAnalyzer",
    "analyze_agent_autonomy",
    "MultiAgentCascadeDetector",
    "detect_cascade",
    "AgenticGovernanceCompliance",
    "check_governance_compliance",
]
