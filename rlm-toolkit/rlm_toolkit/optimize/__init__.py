"""
Prompt Optimization module for RLM-Toolkit.

DSPy-style automatic prompt optimization.
"""

from rlm_toolkit.optimize.dspy import (
    # Core types
    Signature,
    Example,
    Module,
    # Modules
    Predict,
    ChainOfThought,
    SelfRefine,
    # Optimizers
    BootstrapFewShot,
    PromptOptimizer,
    # Factories
    create_qa_signature,
    create_summarize_signature,
    create_classify_signature,
)

__all__ = [
    # Types
    "Signature",
    "Example",
    "Module",
    # Modules
    "Predict",
    "ChainOfThought",
    "SelfRefine",
    # Optimizers
    "BootstrapFewShot",
    "PromptOptimizer",
    # Factories
    "create_qa_signature",
    "create_summarize_signature",
    "create_classify_signature",
]
