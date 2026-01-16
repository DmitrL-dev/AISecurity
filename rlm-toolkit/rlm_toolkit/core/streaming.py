"""
Streaming Events
================

Stream event types for real-time RLM progress (Gap G1).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional


@dataclass
class RLMStreamEvent:
    """Base streaming event.
    
    Emitted during RLM.stream() execution for real-time progress.
    
    Attributes:
        type: Event type
        iteration: Current iteration number
        timestamp: Unix timestamp
        data: Optional event-specific data
    """
    type: Literal[
        'run_start', 'run_end',
        'iteration_start', 'iteration_end',
        'llm_token', 'llm_complete',
        'code_extracted', 'code_executed',
        'subcall_start', 'subcall_end',
        'final', 'error',
    ]
    iteration: int
    timestamp: float
    data: Optional[Dict[str, Any]] = None
    
    def __repr__(self) -> str:
        return f"RLMStreamEvent(type={self.type!r}, iteration={self.iteration})"


@dataclass
class TokenEvent(RLMStreamEvent):
    """LLM token streaming event.
    
    Emitted for each token during streaming generation.
    """
    token: str = ""
    is_subcall: bool = False
    
    def __post_init__(self):
        self.type = 'llm_token'


@dataclass
class ExecutionEvent(RLMStreamEvent):
    """Code execution event.
    
    Emitted after code block execution.
    """
    code: str = ""
    output: str = ""
    
    def __post_init__(self):
        self.type = 'code_executed'


@dataclass
class FinalEvent(RLMStreamEvent):
    """Final result event.
    
    Emitted when FINAL() is reached.
    """
    answer: str = ""
    status: str = "success"
    
    def __post_init__(self):
        self.type = 'final'


@dataclass
class ErrorEvent(RLMStreamEvent):
    """Error event.
    
    Emitted on execution error.
    """
    error_type: str = ""
    error_message: str = ""
    
    def __post_init__(self):
        self.type = 'error'
