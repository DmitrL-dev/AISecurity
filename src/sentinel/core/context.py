"""
AnalysisContext — Context for all SENTINEL analyses.

Provides unified context passed to all engines containing:
- Input prompt and optional response
- Session/user information
- Multi-turn history
- Model metadata
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class Message:
    """Single message in conversation history."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata,
        }


@dataclass
class AnalysisContext:
    """
    Context passed to all SENTINEL engines.
    
    Contains all information needed for analysis:
    - prompt: The user input to analyze
    - response: Optional LLM response (for egress analysis)
    - history: Multi-turn conversation history
    - Metadata: user, session, model info
    
    Usage:
        >>> ctx = AnalysisContext(
        ...     prompt="Hello",
        ...     user_id="user123",
        ...     model="gpt-4"
        ... )
        >>> engine.analyze(ctx)
    """
    # Primary content
    prompt: str
    response: Optional[str] = None
    
    # Session context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Model information
    model: Optional[str] = None
    provider: Optional[str] = None  # openai, anthropic, etc.
    
    # Multi-turn history
    history: List[Message] = field(default_factory=list)
    
    # RAG context (for RAG analysis)
    retrieved_documents: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tool/agent context
    available_tools: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Generate request_id if not provided."""
        if self.request_id is None:
            import uuid
            self.request_id = str(uuid.uuid4())[:8]
    
    @property
    def has_response(self) -> bool:
        """Check if response is present (egress analysis)."""
        return self.response is not None
    
    @property
    def is_multi_turn(self) -> bool:
        """Check if this is a multi-turn conversation."""
        return len(self.history) > 0
    
    @property
    def history_length(self) -> int:
        """Number of messages in history."""
        return len(self.history)
    
    @property
    def full_conversation(self) -> str:
        """Get full conversation including history."""
        parts = []
        for msg in self.history:
            parts.append(f"[{msg.role}]: {msg.content}")
        parts.append(f"[user]: {self.prompt}")
        if self.response:
            parts.append(f"[assistant]: {self.response}")
        return "\n".join(parts)
    
    def add_to_history(
        self,
        role: str,
        content: str,
        **kwargs
    ) -> None:
        """Add message to history."""
        self.history.append(Message(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=kwargs,
        ))
    
    def with_response(self, response: str) -> "AnalysisContext":
        """Create new context with response added."""
        return AnalysisContext(
            prompt=self.prompt,
            response=response,
            user_id=self.user_id,
            session_id=self.session_id,
            request_id=self.request_id,
            model=self.model,
            provider=self.provider,
            history=self.history.copy(),
            retrieved_documents=self.retrieved_documents.copy(),
            available_tools=self.available_tools.copy(),
            tool_calls=self.tool_calls.copy(),
            metadata=self.metadata.copy(),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "prompt": self.prompt,
            "response": self.response,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "model": self.model,
            "provider": self.provider,
            "history": [m.to_dict() for m in self.history],
            "retrieved_documents": self.retrieved_documents,
            "available_tools": self.available_tools,
            "tool_calls": self.tool_calls,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisContext":
        """Create from dictionary."""
        history = [
            Message(
                role=m["role"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]) if m.get("timestamp") else None,
                metadata=m.get("metadata", {}),
            )
            for m in data.get("history", [])
        ]
        
        return cls(
            prompt=data["prompt"],
            response=data.get("response"),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            request_id=data.get("request_id"),
            model=data.get("model"),
            provider=data.get("provider"),
            history=history,
            retrieved_documents=data.get("retrieved_documents", []),
            available_tools=data.get("available_tools", []),
            tool_calls=data.get("tool_calls", []),
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def simple(cls, prompt: str, **kwargs) -> "AnalysisContext":
        """Create simple context with just prompt."""
        return cls(prompt=prompt, **kwargs)
