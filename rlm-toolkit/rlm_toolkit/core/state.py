"""
RLM State Management
====================

Manages execution state across REPL iterations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional


@dataclass
class RLMState:
    """State maintained across RLM iterations.
    
    Attributes:
        context: Full context string
        context_hash: Hash for context verification
        variables: User-defined variables from REPL
        history: List of (action, output) tuples
        iteration: Current iteration number
        subcall_count: Number of llm_query() calls
        total_cost: Accumulated cost in USD
    """
    context: str = ""
    context_hash: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Tuple[str, str]] = field(default_factory=list)
    iteration: int = 0
    subcall_count: int = 0
    total_cost: float = 0.0
    
    def get_namespace(self) -> Dict[str, Any]:
        """Get namespace for REPL execution.
        
        Returns dictionary of user-defined variables
        that should be available in REPL.
        """
        return dict(self.variables)
    
    def add_variable(self, name: str, value: Any) -> None:
        """Add variable to state."""
        self.variables[name] = value
    
    def clear_variables(self) -> None:
        """Clear all variables."""
        self.variables.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dictionary."""
        return {
            'context_hash': self.context_hash,
            'variables': {k: repr(v) for k, v in self.variables.items()},
            'history': self.history,
            'iteration': self.iteration,
            'subcall_count': self.subcall_count,
            'total_cost': self.total_cost,
        }
