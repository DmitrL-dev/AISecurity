"""Core module - RLM engine, REPL, state, callbacks, streaming."""

from rlm_toolkit.core.engine import RLM, RLMResult
from rlm_toolkit.core.config import RLMConfig, SecurityConfig, ProviderConfig, MemoryConfig
from rlm_toolkit.core.state import RLMState
from rlm_toolkit.core.repl import SecureREPL, SecurityViolation
from rlm_toolkit.core.callbacks import RLMCallback, CallbackManager
from rlm_toolkit.core.streaming import RLMStreamEvent
from rlm_toolkit.core.recovery import RecoveryConfig, RecoveryStrategy
from rlm_toolkit.core.context import LazyContext
from rlm_toolkit.core.exceptions import (
    RLMError,
    ProviderError,
    SecurityError,
    ConfigurationError,
    BudgetExceededError,
    IterationLimitError,
    ExecutionTimeoutError,
)

__all__ = [
    "RLM",
    "RLMConfig",
    "RLMResult",
    "RLMState",
    "SecureREPL",
    "SecurityViolation",
    "RLMCallback",
    "CallbackManager",
    "RLMStreamEvent",
    "RecoveryConfig",
    "RecoveryStrategy",
    "LazyContext",
    "SecurityConfig",
    "ProviderConfig",
    "MemoryConfig",
    "RLMError",
    "ProviderError",
    "SecurityError",
    "ConfigurationError",
    "BudgetExceededError",
    "IterationLimitError",
    "ExecutionTimeoutError",
]

