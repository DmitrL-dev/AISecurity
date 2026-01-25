"""
RLM Extractors Package

Provides extractors for automatic fact population from various sources:
- CodeExtractor: README, docstrings, comments
- ConfigExtractor: package.json, pyproject.toml
- ConversationExtractor: Agent decision patterns
- GitExtractor: Conventional commits
"""

from .base import BaseExtractor, FactCandidate, ExtractionResult
from .code_extractor import CodeExtractor
from .config_extractor import ConfigExtractor
from .conversation_extractor import ConversationExtractor
from .git_extractor import GitExtractor
from .orchestrator import ExtractionOrchestrator

__all__ = [
    "BaseExtractor",
    "FactCandidate",
    "ExtractionResult",
    "CodeExtractor",
    "ConfigExtractor",
    "ConversationExtractor",
    "GitExtractor",
    "ExtractionOrchestrator",
]
