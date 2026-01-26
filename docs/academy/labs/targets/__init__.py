"""
Academy Lab Targets Package

Provides vulnerable and secured targets for security testing labs.
"""

from .vulnerable_agent import VulnerableAgent, AgentResponse, ToolCall
from .target_chatbot import TargetChatbot, TargetChatbotRU, ChatResponse
from .secured_chatbot import SecuredChatbot, SecurityEvent

__all__ = [
    # Vulnerable targets (for attacks)
    "VulnerableAgent",
    "TargetChatbot",
    "TargetChatbotRU",
    # Secured targets (for comparison)
    "SecuredChatbot",
    # Response types
    "AgentResponse",
    "ChatResponse",
    "ToolCall",
    "SecurityEvent",
]
