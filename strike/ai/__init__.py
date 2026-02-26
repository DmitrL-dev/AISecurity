"""
SENTINEL Strike — AI Module

LLM-powered attack planning and adaptive bypass logic.
Based on NeuroSploit patterns.
"""

from .llm_manager import StrikeLLMManager, LLMProvider, LLMConfig
from .prompts import (
    EXPLOIT_EXPERT,
    WAF_BYPASS_EXPERT,
    RECON_EXPERT,
    JAILBREAK_EXPERT
)

__all__ = [
    'StrikeLLMManager',
    'LLMProvider',
    'LLMConfig',
    'EXPLOIT_EXPERT',
    'WAF_BYPASS_EXPERT',
    'RECON_EXPERT',
    'JAILBREAK_EXPERT'
]
