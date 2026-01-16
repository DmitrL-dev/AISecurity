"""
Callbacks System
================

LangChain-compatible callback system for RLM (FR-7).
"""

from __future__ import annotations

from abc import ABC
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rlm_toolkit.core.engine import RLMConfig, RLMResult
    from rlm_toolkit.providers.base import LLMResponse


class RLMCallback(ABC):
    """Base class for RLM callbacks.
    
    Implement this to receive events during RLM execution.
    All methods are optional - only implement what you need.
    
    Example:
        >>> class MyCallback(RLMCallback):
        ...     def on_iteration_start(self, iteration, history):
        ...         print(f"Starting iteration {iteration}")
        ...
        >>> rlm = RLM.from_ollama("llama4", callbacks=[MyCallback()])
    """
    
    def on_run_start(
        self,
        context: str,
        query: str,
        config: "RLMConfig",
    ) -> None:
        """Called when run() starts."""
        pass
    
    def on_iteration_start(
        self,
        iteration: int,
        history: List[tuple],
    ) -> None:
        """Called at start of each REPL iteration."""
        pass
    
    def on_iteration_end(
        self,
        iteration: int,
        output: str,
    ) -> None:
        """Called at end of each REPL iteration."""
        pass
    
    def on_llm_response(
        self,
        response: "LLMResponse",
        is_subcall: bool,
    ) -> None:
        """Called after each LLM response."""
        pass
    
    def on_code_extracted(
        self,
        code: str,
    ) -> None:
        """Called when code is extracted from response."""
        pass
    
    def on_code_executed(
        self,
        code: str,
        output: str,
    ) -> None:
        """Called after code execution."""
        pass
    
    def on_subcall_start(
        self,
        prompt: str,
        depth: int,
    ) -> None:
        """Called before llm_query() sub-call."""
        pass
    
    def on_subcall_end(
        self,
        response: str,
        depth: int,
        cost: float,
    ) -> None:
        """Called after llm_query() sub-call."""
        pass
    
    def on_final(
        self,
        result: str,
    ) -> None:
        """Called when FINAL() is reached."""
        pass
    
    def on_error(
        self,
        error: Exception,
        context: Dict[str, Any],
    ) -> None:
        """Called on any error."""
        pass
    
    def on_security_violation(
        self,
        violation: str,
        code: str,
    ) -> None:
        """Called on security violation."""
        pass


class CallbackManager:
    """Manages multiple callbacks.
    
    Provides centralized callback dispatch and management.
    
    Example:
        >>> manager = CallbackManager()
        >>> manager.add(LoggingCallback())
        >>> manager.add(CostTrackingCallback())
        >>> manager.fire("on_iteration_start", iteration=1, history=[])
    """
    
    def __init__(self, callbacks: Optional[List[RLMCallback]] = None):
        """Initialize with optional callbacks list."""
        self.callbacks: List[RLMCallback] = callbacks or []
    
    def add(self, callback: RLMCallback) -> None:
        """Add a callback handler."""
        self.callbacks.append(callback)
    
    def remove(self, callback: RLMCallback) -> None:
        """Remove a callback handler."""
        self.callbacks.remove(callback)
    
    def clear(self) -> None:
        """Remove all callbacks."""
        self.callbacks.clear()
    
    def fire(self, event: str, **kwargs) -> None:
        """Fire event to all callbacks.
        
        Args:
            event: Event method name (e.g., "on_iteration_start")
            **kwargs: Event arguments
        """
        for callback in self.callbacks:
            method = getattr(callback, event, None)
            if method and callable(method):
                try:
                    method(**kwargs)
                except Exception:
                    # Don't let callbacks break execution
                    pass


# Built-in callbacks

class LoggingCallback(RLMCallback):
    """Logs all events to structured logger."""
    
    def __init__(self, logger=None):
        import logging
        self.logger = logger or logging.getLogger("rlm_toolkit")
    
    def on_run_start(self, context, query, config):
        self.logger.info(f"RLM run started: query='{query[:50]}...', context_len={len(context)}")
    
    def on_iteration_start(self, iteration, history):
        self.logger.debug(f"Iteration {iteration} started")
    
    def on_code_executed(self, code, output):
        self.logger.debug(f"Code executed: {len(code)} chars -> {len(output)} chars output")
    
    def on_final(self, result):
        self.logger.info(f"FINAL reached: {result[:100]}...")
    
    def on_error(self, error, context):
        self.logger.error(f"Error: {type(error).__name__}: {error}")


class CostTrackingCallback(RLMCallback):
    """Tracks costs across calls."""
    
    def __init__(self):
        self.total_cost = 0.0
        self.subcall_costs = []
    
    def on_subcall_end(self, response, depth, cost):
        self.subcall_costs.append(cost)
        self.total_cost += cost
    
    def get_total_cost(self) -> float:
        return self.total_cost
    
    def reset(self):
        self.total_cost = 0.0
        self.subcall_costs.clear()


class StreamingCallback(RLMCallback):
    """Enables real-time output streaming."""
    
    def __init__(self, output_func=None):
        self.output_func = output_func or print
    
    def on_iteration_start(self, iteration, history):
        self.output_func(f"\n[Iteration {iteration}]")
    
    def on_code_executed(self, code, output):
        if output.strip():
            self.output_func(f"Output: {output[:500]}")
    
    def on_final(self, result):
        self.output_func(f"\nFINAL: {result}")
