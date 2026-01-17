"""
Advanced Agent Types with SENTINEL Integration
==============================================

Agents integrated with:
- H-MEM Trust Zones for secure memory sharing
- Self-Evolving capabilities for autonomous improvement
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from rlm_toolkit.agents.core import (
    Agent,
    AgentMessage,
    AgentRole,
)

# Try to import H-MEM and evolve modules
try:
    from rlm_toolkit.memory.secure import SecureHierarchicalMemory, TrustLevel
    HMEM_AVAILABLE = True
except ImportError:
    HMEM_AVAILABLE = False

try:
    from rlm_toolkit.evolve import SelfEvolvingRLM, EvolutionStrategy
    EVOLVE_AVAILABLE = True
except ImportError:
    EVOLVE_AVAILABLE = False


class SecureAgent(Agent):
    """
    Agent with integrated H-MEM Trust Zone memory.
    
    Each agent maintains its own secure memory that respects
    trust zone boundaries when sharing with other agents.
    
    Example:
        >>> agent = SecureAgent(
        ...     agent_id="secure-001",
        ...     name="Secure Processor",
        ...     trust_zone="confidential",
        ...     llm_provider=provider
        ... )
        >>> agent.remember("Important finding")
        >>> memories = agent.recall("finding")
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        role: AgentRole = AgentRole.EXECUTOR,
        trust_zone: str = "internal",
        llm_provider=None,
        memory_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id, name, role, trust_zone, llm_provider)
        
        # Initialize secure memory
        if HMEM_AVAILABLE:
            self.memory = SecureHierarchicalMemory(
                agent_id=agent_id,
                trust_zone=trust_zone,
                **(memory_config or {})
            )
        else:
            self.memory = None
    
    def remember(self, content: str, metadata: Optional[Dict] = None) -> Optional[str]:
        """Store memory in secure H-MEM."""
        if self.memory:
            return self.memory.add_episode(content, metadata=metadata)
        return None
    
    def recall(self, query: str, top_k: int = 5) -> List[Any]:
        """Retrieve relevant memories."""
        if self.memory:
            return self.memory.retrieve(query, top_k=top_k)
        return []
    
    def share_memory_with(self, other_agent_id: str) -> None:
        """Grant another agent access to this agent's memory zone."""
        if self.memory:
            self.memory.grant_access(other_agent_id, self.trust_zone)
    
    def process(self, message: AgentMessage) -> List[AgentMessage]:
        """Process with memory augmentation."""
        # Retrieve relevant memories
        relevant = self.recall(str(message.content), top_k=3)
        
        # Augment message with memories
        if relevant:
            memory_context = "\n".join(m.content for m in relevant)
            message.state["memory_context"] = memory_context
        
        # Store interaction as memory
        self.remember(f"Processed: {message.content[:200]}")
        
        # Base processing
        if self.llm:
            prompt = f"""You are a secure agent with memory context.

Memory Context:
{message.state.get('memory_context', 'No relevant memories')}

Current Task: {message.content}

Your response:"""
            response = self.llm.generate(prompt)
            message.content = response.content
            message.add_to_history(self.name, response.content)
        
        message.advance_routing()
        return [message]


class EvolvingAgent(Agent):
    """
    Self-Evolving Agent that improves through usage.
    
    Uses R-Zero Challenger-Solver dynamics internally
    to continuously improve reasoning capabilities.
    
    Example:
        >>> agent = EvolvingAgent(
        ...     agent_id="evolve-001",
        ...     name="Evolving Solver",
        ...     llm_provider=provider,
        ...     strategy=EvolutionStrategy.SELF_REFINE
        ... )
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        llm_provider,
        role: AgentRole = AgentRole.EXECUTOR,
        trust_zone: str = "public",
        strategy: str = "self_refine",
        max_refinements: int = 3,
    ):
        super().__init__(agent_id, name, role, trust_zone, llm_provider)
        
        # Initialize self-evolving capabilities
        if EVOLVE_AVAILABLE:
            strategy_enum = {
                "self_refine": EvolutionStrategy.SELF_REFINE,
                "challenger_solver": EvolutionStrategy.CHALLENGER_SOLVER,
                "experience_replay": EvolutionStrategy.EXPERIENCE_REPLAY,
            }.get(strategy, EvolutionStrategy.SELF_REFINE)
            
            self.evolve = SelfEvolvingRLM(
                provider=llm_provider,
                strategy=strategy_enum,
                max_refinements=max_refinements,
            )
        else:
            self.evolve = None
    
    def process(self, message: AgentMessage) -> List[AgentMessage]:
        """Process with self-evolution."""
        if self.evolve:
            # Use self-evolving solve
            solution = self.evolve.solve(
                str(message.content),
                domain=message.state.get("domain", "general"),
            )
            
            message.content = solution.answer
            message.state["reasoning"] = solution.reasoning
            message.state["confidence"] = solution.confidence
            message.add_to_history(self.name, f"[Confidence: {solution.confidence:.2f}] {solution.answer}")
        elif self.llm:
            # Fallback to simple LLM
            response = self.llm.generate(str(message.content))
            message.content = response.content
            message.add_to_history(self.name, response.content)
        
        message.advance_routing()
        return [message]
    
    def get_evolution_metrics(self) -> Dict[str, Any]:
        """Get self-evolution metrics."""
        if self.evolve:
            return self.evolve.get_metrics().to_dict()
        return {}


class SecureEvolvingAgent(SecureAgent, EvolvingAgent):
    """
    Agent with both secure memory and self-evolving capabilities.
    
    The ultimate agent type combining:
    - H-MEM Trust Zones for secure memory
    - Self-Evolving for continuous improvement
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        llm_provider,
        role: AgentRole = AgentRole.EXECUTOR,
        trust_zone: str = "internal",
        strategy: str = "self_refine",
        max_refinements: int = 3,
        memory_config: Optional[Dict[str, Any]] = None,
    ):
        SecureAgent.__init__(
            self, agent_id, name, role, trust_zone, llm_provider, memory_config
        )
        # Manually initialize evolving part
        if EVOLVE_AVAILABLE:
            strategy_enum = {
                "self_refine": EvolutionStrategy.SELF_REFINE,
                "challenger_solver": EvolutionStrategy.CHALLENGER_SOLVER,
                "experience_replay": EvolutionStrategy.EXPERIENCE_REPLAY,
            }.get(strategy, EvolutionStrategy.SELF_REFINE)
            
            self.evolve = SelfEvolvingRLM(
                provider=llm_provider,
                strategy=strategy_enum,
                max_refinements=max_refinements,
            )
        else:
            self.evolve = None
    
    def process(self, message: AgentMessage) -> List[AgentMessage]:
        """Process with both memory and evolution."""
        # First, retrieve relevant memories
        relevant = self.recall(str(message.content), top_k=3)
        if relevant:
            memory_context = "\n".join(m.content for m in relevant)
            message.state["memory_context"] = memory_context
        
        # Then use self-evolving solve if available
        if self.evolve:
            augmented_content = str(message.content)
            if message.state.get("memory_context"):
                augmented_content = f"Memory: {message.state['memory_context']}\n\nTask: {message.content}"
            
            solution = self.evolve.solve(augmented_content)
            message.content = solution.answer
            message.state["confidence"] = solution.confidence
            
            # Store as memory for future
            self.remember(f"Solved: {message.content[:100]} -> {solution.answer[:100]}")
        elif self.llm:
            response = self.llm.generate(str(message.content))
            message.content = response.content
            self.remember(f"Processed: {message.content[:100]}")
        
        message.add_to_history(self.name, str(message.content)[:500])
        message.advance_routing()
        return [message]
