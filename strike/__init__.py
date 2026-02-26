"""
SENTINEL Strike — AI Red Team Platform

Advanced AI-powered penetration testing framework.

Modules:
    - ai: LLM integration for intelligent attack planning
    - hydra: Multi-head attack orchestration
    - evasion: WAF bypass and stealth techniques
    - recon: Network and web reconnaissance
    - bugbounty: Scope validation and reporting
    - payloads: Attack payload library
    - stealth: Advanced stealth and evasion
"""

__version__ = "3.0.0"
__author__ = "SENTINEL Security Team"

# Core components
from .executor import AttackExecutor
from .config import StrikeConfig
from .target import Target
from .universal_controller import UniversalController

# Sub-modules (lazy imports for optional components)


def get_llm_manager():
    """Get LLM Manager for AI-powered attacks."""
    from .ai import StrikeLLMManager
    return StrikeLLMManager


def get_hydra():
    """Get HYDRA controller for multi-head attacks."""
    from .hydra import HydraAttackController
    return HydraAttackController


def get_recon():
    """Get reconnaissance tools."""
    from .recon import NetworkScanner, TechFingerprinter
    return NetworkScanner, TechFingerprinter


def get_bugbounty():
    """Get bug bounty tools."""
    from .bugbounty import ScopeValidator, BugBountyReporter
    return ScopeValidator, BugBountyReporter


__all__ = [
    # Core
    "AttackExecutor",
    "StrikeConfig",
    "Target",
    "UniversalController",
    "__version__",
    # Lazy loaders
    "get_llm_manager",
    "get_hydra",
    "get_recon",
    "get_bugbounty",
]
