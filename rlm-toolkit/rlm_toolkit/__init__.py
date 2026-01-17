"""
RLM-Toolkit: Recursive Language Model Framework
================================================

A Python library for processing 10M+ token contexts with any LLM
using the Recursive Language Models paradigm (arxiv:2512.24601).

Features:
- 10M+ token processing without quality degradation
- InfiniRetri: Attention-based infinite context retrieval (100% NIH accuracy)
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

InfiniRetri (for 1M+ token contexts):
-------------------------------------
>>> from rlm_toolkit.retrieval import InfiniRetriever
>>> retriever = InfiniRetriever("Qwen/Qwen2.5-0.5B-Instruct")
>>> answer = retriever.retrieve(million_token_doc, "Find the key insight")

Advanced Usage:
--------------
>>> from rlm_toolkit import RLM, RLMConfig
>>> from rlm_toolkit.providers import OpenAIProvider, OllamaProvider
>>>
>>> config = RLMConfig(max_cost=5.0, sandbox=True, use_infiniretri=True)
>>> rlm = RLM(
...     root=OpenAIProvider("gpt-5.2"),
...     sub=OllamaProvider("qwen3:7b"),  # Free sub-calls
...     config=config,
... )
>>> result = rlm.run(codebase, "Find security vulnerabilities")

API Reference:
-------------
- RLM: Main engine class (auto-routes to InfiniRetri for large contexts)
- RLMConfig: Configuration options (includes infiniretri_threshold)
- RLMResult: Execution result with answer, cost, iterations
- InfiniRetriever: Attention-based infinite context retrieval

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

# InfiniRetri (optional, requires infini-retri package)
try:
    from rlm_toolkit.retrieval import InfiniRetriever, INFINIRETRI_AVAILABLE
except ImportError:
    InfiniRetriever = None
    INFINIRETRI_AVAILABLE = False

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
    # InfiniRetri
    "InfiniRetriever",
    "INFINIRETRI_AVAILABLE",
]

