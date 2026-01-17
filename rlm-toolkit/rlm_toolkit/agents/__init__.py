"""
Multi-Agent module for RLM-Toolkit.

Decentralized P2P architecture inspired by Meta Matrix.
Unlike centralized orchestrators, state is embedded in messages.

Features:
- P2P message-driven (no central bottleneck)
- Trust Zones for agent isolation
- Stateless agents for scalability
- 2-15x throughput improvement
"""

from rlm_toolkit.agents.core import (
    # Core classes
    Agent,
    AgentMessage,
    AgentRole,
    AgentInfo,
    MessagePriority,
    MessageQueue,
    AgentRegistry,
    MultiAgentRuntime,
    # Pre-built agents
    LLMAgent,
    RouterAgent,
    AggregatorAgent,
    # Factory
    create_multi_agent_runtime,
)

from rlm_toolkit.agents.advanced import (
    SecureAgent,
    EvolvingAgent,
    SecureEvolvingAgent,
)

__all__ = [
    # Core
    "Agent",
    "AgentMessage",
    "AgentRole",
    "AgentInfo",
    "MessagePriority",
    "MessageQueue",
    "AgentRegistry",
    "MultiAgentRuntime",
    # Pre-built
    "LLMAgent",
    "RouterAgent",
    "AggregatorAgent",
    # Advanced (SENTINEL integration)
    "SecureAgent",
    "EvolvingAgent",
    "SecureEvolvingAgent",
    # Factory
    "create_multi_agent_runtime",
]
