"""
RLM-Toolkit: Recursive Language Model Framework
================================================

A Python library for processing 10M+ token contexts with any LLM
using the Recursive Language Models paradigm (arxiv:2512.24601).

Features:
- 10M+ token processing without quality degradation
- 80-90% cost reduction vs direct processing
- Security-first design (CIRCLE-based guards)
- LangChain-competitive observability & callbacks
- Multiple memory types (Buffer, Summary, Episodic)
- Built-in evaluation framework

Quick Start:
-----------
>>> from rlm_toolkit import RLM
>>> rlm = RLM.from_ollama("llama4")
>>> result = rlm.run(huge_document, "Summarize all chapters")
>>> print(result.answer)

Advanced Usage:
--------------
>>> from rlm_toolkit import RLM, RLMConfig
>>> from rlm_toolkit.providers import OpenAIProvider, OllamaProvider
>>>
>>> config = RLMConfig(max_cost=5.0, sandbox=True)
>>> rlm = RLM(
...     root=OpenAIProvider("gpt-5.2"),
...     sub=OllamaProvider("qwen3:7b"),  # Free sub-calls
...     config=config,
... )
>>> result = rlm.run(codebase, "Find security vulnerabilities")

API Reference:
-------------
- RLM: Main engine class
- RLMConfig: Configuration options
- RLMResult: Execution result with answer, cost, iterations
- LLMProvider: Base class for LLM providers

Version: 2.0.0a1
License: Apache-2.0
"""

__version__ = "2.0.0a1"
__author__ = "SENTINEL Team"
__license__ = "Apache-2.0"

# Public API - lazy imports for optional dependencies
from rlm_toolkit.core.engine import RLM, RLMConfig, RLMResult
from rlm_toolkit.core.state import RLMState
from rlm_toolkit.core.repl import SecureREPL, SecurityViolation
from rlm_toolkit.core.callbacks import RLMCallback, CallbackManager
from rlm_toolkit.core.streaming import RLMStreamEvent

# Type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from rlm_toolkit.providers import (
        LLMProvider,
        OllamaProvider,
        OpenAIProvider,
        AnthropicProvider,
        GeminiProvider,
    )
    from rlm_toolkit.memory import Memory

__all__ = [
    # Version
    "__version__",
    # Core
    "RLM",
    "RLMConfig",
    "RLMResult",
    "RLMState",
    # Security
    "SecureREPL",
    "SecurityViolation",
    # Callbacks
    "RLMCallback",
    "CallbackManager",
    # Streaming
    "RLMStreamEvent",
]
