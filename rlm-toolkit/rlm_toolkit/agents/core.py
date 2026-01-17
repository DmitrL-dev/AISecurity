"""
Decentralized Multi-Agent Framework
====================================

P2P message-driven architecture inspired by Meta Matrix.
Unlike centralized orchestrators (LangGraph), this uses:
- Stateless agents with state serialized in messages
- Distributed queues for async execution
- Trust Zones from H-MEM for secure sharing
- Self-Evolving agents for autonomous improvement

Key Concepts:
- Message = Task state + Routing logic + History
- Agent = Stateless processor
- Orchestrator = Embedded in message, not central

Based on Meta Matrix (arXiv 2025) + SENTINEL Trust Zones.
"""

from __future__ import annotations

import time
import uuid
import hashlib
import json
import asyncio
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Set, Union
from enum import Enum
from queue import Queue, Empty
import logging

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Standard agent roles."""
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    RESEARCHER = "researcher"
    SYNTHESIZER = "synthesizer"
    CUSTOM = "custom"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class AgentMessage:
    """
    Self-contained message with embedded orchestration.
    
    The message carries the full task state, eliminating the need
    for a central orchestrator. Each message is an independent
    state machine that moves through stateless agents.
    
    Attributes:
        id: Unique message ID
        task_id: Parent task ID (groups related messages)
        sender: Sender agent ID
        recipient: Target agent ID (or "broadcast")
        content: Message payload
        history: Conversation/reasoning history
        state: Current task state dict
        routing: Next steps / routing logic
        priority: Message priority
        trust_zone: Security zone for this message
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    sender: str = ""
    recipient: str = ""
    content: Any = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    routing: List[str] = field(default_factory=list)  # Agent IDs to visit
    priority: MessagePriority = MessagePriority.NORMAL
    trust_zone: str = "public"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    
    def add_to_history(self, role: str, content: str) -> None:
        """Add entry to message history."""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
    
    def next_recipient(self) -> Optional[str]:
        """Get next agent in routing."""
        if self.routing:
            return self.routing[0]
        return None
    
    def advance_routing(self) -> None:
        """Move to next agent in routing."""
        if self.routing:
            self.routing.pop(0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "history": self.history,
            "state": self.state,
            "routing": self.routing,
            "priority": self.priority.value,
            "trust_zone": self.trust_zone,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            task_id=data.get("task_id", ""),
            sender=data.get("sender", ""),
            recipient=data.get("recipient", ""),
            content=data.get("content"),
            history=data.get("history", []),
            state=data.get("state", {}),
            routing=data.get("routing", []),
            priority=MessagePriority(data.get("priority", 1)),
            trust_zone=data.get("trust_zone", "public"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class AgentInfo:
    """Agent registration info."""
    id: str
    name: str
    role: AgentRole
    trust_zone: str = "public"
    capabilities: List[str] = field(default_factory=list)
    max_concurrent: int = 10
    created_at: float = field(default_factory=time.time)


class Agent(ABC):
    """
    Base class for stateless agents.
    
    Agents process messages and return new messages.
    They don't maintain state between calls - all state
    is carried in the AgentMessage.
    
    Example:
        >>> class MyAgent(Agent):
        ...     def process(self, message):
        ...         result = do_work(message.content)
        ...         message.content = result
        ...         message.advance_routing()
        ...         return [message]
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        role: AgentRole = AgentRole.CUSTOM,
        trust_zone: str = "public",
        llm_provider=None,
    ):
        """
        Initialize agent.
        
        Args:
            agent_id: Unique agent identifier
            name: Human-readable name
            role: Agent role
            trust_zone: Security zone
            llm_provider: Optional LLM provider for AI operations
        """
        self.id = agent_id
        self.name = name
        self.role = role
        self.trust_zone = trust_zone
        self.llm = llm_provider
        
        # Metrics
        self._messages_processed = 0
        self._total_processing_time = 0.0
    
    @abstractmethod
    def process(self, message: AgentMessage) -> List[AgentMessage]:
        """
        Process incoming message.
        
        Args:
            message: Incoming message with task state
            
        Returns:
            List of outgoing messages (can be 0, 1, or many)
        """
        pass
    
    def can_access(self, message: AgentMessage) -> bool:
        """Check if agent can access message based on trust zones."""
        # Simple zone hierarchy: public < internal < confidential < secret
        zone_levels = {"public": 0, "internal": 1, "confidential": 2, "secret": 3}
        agent_level = zone_levels.get(self.trust_zone, 0)
        message_level = zone_levels.get(message.trust_zone, 0)
        
        return agent_level >= message_level
    
    def get_info(self) -> AgentInfo:
        """Get agent registration info."""
        return AgentInfo(
            id=self.id,
            name=self.name,
            role=self.role,
            trust_zone=self.trust_zone,
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics."""
        avg_time = (
            self._total_processing_time / self._messages_processed
            if self._messages_processed > 0 else 0.0
        )
        return {
            "messages_processed": self._messages_processed,
            "avg_processing_time": avg_time,
        }


class MessageQueue:
    """
    Distributed message queue for agent communication.
    
    In production, this would be backed by Redis, RabbitMQ, or Ray.
    This implementation uses in-memory queues for development.
    """
    
    def __init__(self, max_size: int = 10000):
        self._queues: Dict[str, Queue] = {}
        self._max_size = max_size
        self._lock = threading.Lock()
    
    def _get_queue(self, agent_id: str) -> Queue:
        """Get or create queue for agent."""
        with self._lock:
            if agent_id not in self._queues:
                self._queues[agent_id] = Queue(maxsize=self._max_size)
            return self._queues[agent_id]
    
    def send(self, message: AgentMessage) -> None:
        """Send message to recipient's queue."""
        recipient = message.recipient or message.next_recipient()
        if recipient:
            queue = self._get_queue(recipient)
            queue.put(message)
    
    def receive(self, agent_id: str, timeout: float = 1.0) -> Optional[AgentMessage]:
        """Receive message from agent's queue."""
        queue = self._get_queue(agent_id)
        try:
            return queue.get(timeout=timeout)
        except Empty:
            return None
    
    def broadcast(self, message: AgentMessage, agent_ids: List[str]) -> None:
        """Broadcast message to multiple agents."""
        for agent_id in agent_ids:
            msg_copy = AgentMessage.from_dict(message.to_dict())
            msg_copy.recipient = agent_id
            self.send(msg_copy)
    
    def size(self, agent_id: str) -> int:
        """Get queue size for agent."""
        if agent_id in self._queues:
            return self._queues[agent_id].qsize()
        return 0


class AgentRegistry:
    """
    Agent registration and discovery service.
    
    Agents register themselves and can discover other agents
    by role, capability, or trust zone.
    """
    
    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._info: Dict[str, AgentInfo] = {}
        self._lock = threading.Lock()
    
    def register(self, agent: Agent) -> None:
        """Register an agent."""
        with self._lock:
            self._agents[agent.id] = agent
            self._info[agent.id] = agent.get_info()
    
    def unregister(self, agent_id: str) -> None:
        """Unregister an agent."""
        with self._lock:
            self._agents.pop(agent_id, None)
            self._info.pop(agent_id, None)
    
    def get(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self._agents.get(agent_id)
    
    def find_by_role(self, role: AgentRole) -> List[Agent]:
        """Find agents by role."""
        return [a for a in self._agents.values() if a.role == role]
    
    def find_by_trust_zone(self, zone: str) -> List[Agent]:
        """Find agents in trust zone."""
        return [a for a in self._agents.values() if a.trust_zone == zone]
    
    def list_all(self) -> List[AgentInfo]:
        """List all registered agents."""
        return list(self._info.values())


class MultiAgentRuntime:
    """
    Decentralized multi-agent runtime.
    
    Orchestration is embedded in messages, not centralized.
    The runtime just provides infrastructure:
    - Message routing
    - Agent execution
    - Trust zone enforcement
    
    Example:
        >>> runtime = MultiAgentRuntime()
        >>> runtime.register(PlannerAgent("planner"))
        >>> runtime.register(ExecutorAgent("executor"))
        >>> 
        >>> message = AgentMessage(
        ...     content="Solve this math problem: 2+2",
        ...     routing=["planner", "executor"]
        ... )
        >>> result = runtime.run(message)
    """
    
    def __init__(self, max_iterations: int = 100):
        """
        Initialize runtime.
        
        Args:
            max_iterations: Maximum message processing iterations
        """
        self.registry = AgentRegistry()
        self.queue = MessageQueue()
        self.max_iterations = max_iterations
        
        # Metrics
        self._tasks_completed = 0
        self._messages_routed = 0
        self._lock = threading.Lock()
    
    def register(self, agent: Agent) -> None:
        """Register an agent with the runtime."""
        self.registry.register(agent)
    
    def unregister(self, agent_id: str) -> None:
        """Unregister an agent."""
        self.registry.unregister(agent_id)
    
    def run(
        self,
        message: AgentMessage,
        on_step: Optional[Callable[[AgentMessage, Agent], None]] = None,
    ) -> AgentMessage:
        """
        Run message through agent pipeline.
        
        Args:
            message: Initial message with routing
            on_step: Optional callback(message, agent) after each step
            
        Returns:
            Final message after processing
        """
        if not message.task_id:
            message.task_id = str(uuid.uuid4())
        
        current = message
        iterations = 0
        
        while iterations < self.max_iterations:
            recipient_id = current.next_recipient()
            
            if not recipient_id:
                # No more agents to visit
                break
            
            agent = self.registry.get(recipient_id)
            if not agent:
                logger.warning(f"Agent not found: {recipient_id}")
                current.advance_routing()
                continue
            
            # Trust zone check
            if not agent.can_access(current):
                logger.warning(f"Agent {agent.id} cannot access message in zone {current.trust_zone}")
                current.advance_routing()
                continue
            
            # Process message
            start_time = time.perf_counter()
            current.recipient = agent.id
            results = agent.process(current)
            
            # Update agent metrics
            agent._messages_processed += 1
            agent._total_processing_time += time.perf_counter() - start_time
            
            with self._lock:
                self._messages_routed += 1
            
            # Callback
            if on_step and results:
                on_step(results[0], agent)
            
            # Handle results
            if not results:
                break
            
            current = results[0]
            iterations += 1
        
        with self._lock:
            self._tasks_completed += 1
        
        return current
    
    async def run_async(
        self,
        message: AgentMessage,
        on_step: Optional[Callable[[AgentMessage, Agent], None]] = None,
    ) -> AgentMessage:
        """Async version of run."""
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.run(message, on_step)
        )
    
    def run_batch(
        self,
        messages: List[AgentMessage],
        max_workers: int = 4,
    ) -> List[AgentMessage]:
        """Run multiple messages in parallel."""
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.run, msg) for msg in messages]
            return [f.result() for f in concurrent.futures.as_completed(futures)]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get runtime metrics."""
        with self._lock:
            return {
                "tasks_completed": self._tasks_completed,
                "messages_routed": self._messages_routed,
                "registered_agents": len(self.registry.list_all()),
            }


# Pre-built agent types

class LLMAgent(Agent):
    """Agent that uses an LLM to process messages."""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        llm_provider,
        system_prompt: str = "",
        role: AgentRole = AgentRole.CUSTOM,
        trust_zone: str = "public",
    ):
        super().__init__(agent_id, name, role, trust_zone, llm_provider)
        self.system_prompt = system_prompt
    
    def process(self, message: AgentMessage) -> List[AgentMessage]:
        """Process message using LLM."""
        # Build prompt from history
        history_str = "\n".join(
            f"{h['role']}: {h['content']}" for h in message.history[-10:]
        )
        
        prompt = f"""{self.system_prompt}

History:
{history_str}

Current task: {message.content}

Your response:"""
        
        response = self.llm.generate(prompt)
        
        # Update message
        message.add_to_history(self.name, response.content)
        message.content = response.content
        message.advance_routing()
        
        return [message]


class RouterAgent(Agent):
    """Agent that dynamically routes messages based on content."""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        routing_rules: Dict[str, List[str]],
        trust_zone: str = "public",
    ):
        """
        Initialize router.
        
        Args:
            routing_rules: keyword -> agent_ids mapping
        """
        super().__init__(agent_id, name, AgentRole.PLANNER, trust_zone)
        self.routing_rules = routing_rules
    
    def process(self, message: AgentMessage) -> List[AgentMessage]:
        """Route message based on content keywords."""
        content_lower = str(message.content).lower()
        
        for keyword, agent_ids in self.routing_rules.items():
            if keyword in content_lower:
                message.routing = agent_ids + message.routing
                break
        
        message.advance_routing()
        return [message]


class AggregatorAgent(Agent):
    """Agent that collects results from multiple sources."""
    
    def __init__(self, agent_id: str, name: str, trust_zone: str = "public"):
        super().__init__(agent_id, name, AgentRole.SYNTHESIZER, trust_zone)
        self._collected: Dict[str, List[Any]] = {}
    
    def process(self, message: AgentMessage) -> List[AgentMessage]:
        """Collect and aggregate results."""
        task_id = message.task_id
        
        if task_id not in self._collected:
            self._collected[task_id] = []
        
        self._collected[task_id].append(message.content)
        
        # Check if aggregation is complete (based on expected count in state)
        expected = message.state.get("aggregation_count", 1)
        if len(self._collected[task_id]) >= expected:
            message.content = {
                "aggregated": True,
                "results": self._collected.pop(task_id),
            }
        
        message.advance_routing()
        return [message]


# Convenience factory
def create_multi_agent_runtime() -> MultiAgentRuntime:
    """Create a new multi-agent runtime."""
    return MultiAgentRuntime()
