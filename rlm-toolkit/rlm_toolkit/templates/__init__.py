"""Templates module - prompt templates and system prompts."""

from rlm_toolkit.templates.base import PromptTemplate, TemplateRegistry
from rlm_toolkit.templates.builtin import (
    DEFAULT_SYSTEM_PROMPT,
    ANALYSIS_TEMPLATE,
    SUMMARY_TEMPLATE,
    QA_TEMPLATE,
)

__all__ = [
    "PromptTemplate",
    "TemplateRegistry",
    "DEFAULT_SYSTEM_PROMPT",
    "ANALYSIS_TEMPLATE",
    "SUMMARY_TEMPLATE",
    "QA_TEMPLATE",
]
