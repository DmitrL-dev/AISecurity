"""
Error Recovery
==============

Recovery strategies for LLM/execution failures (ADR-007).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rlm_toolkit.providers.base import LLMProvider


class RecoveryStrategy(Enum):
    """Recovery strategy after error.
    
    SAME: Retry with same prompt
    FIX: Ask LLM to fix the error
    SKIP: Skip and continue
    """
    SAME = "same"
    FIX = "fix"
    SKIP = "skip"


@dataclass
class RecoveryConfig:
    """Error recovery configuration.
    
    Attributes:
        max_retries: Maximum retries per error (default: 3)
        retry_strategy: Strategy to use (default: FIX)
        fallback_provider: Alternative provider if main fails
    """
    max_retries: int = 3
    retry_strategy: RecoveryStrategy = RecoveryStrategy.FIX
    fallback_provider: Optional["LLMProvider"] = None
    
    # FIX strategy prompt template
    fix_prompt_template: str = """
The previous code execution failed with this error:
{error}

Original code:
```python
{code}
```

Please fix the code to avoid this error and try again.
"""


class RecoveryHandler:
    """Handles error recovery during RLM execution.
    
    Implements ADR-007 recovery strategies.
    """
    
    def __init__(self, config: RecoveryConfig):
        self.config = config
        self.retry_counts: dict = {}
    
    def should_retry(self, error_key: str) -> bool:
        """Check if retry is allowed for this error."""
        count = self.retry_counts.get(error_key, 0)
        return count < self.config.max_retries
    
    def record_retry(self, error_key: str) -> None:
        """Record a retry attempt."""
        self.retry_counts[error_key] = self.retry_counts.get(error_key, 0) + 1
    
    def get_recovery_prompt(self, code: str, error: str) -> str:
        """Get prompt for FIX strategy."""
        return self.config.fix_prompt_template.format(
            error=error,
            code=code,
        )
    
    def reset(self) -> None:
        """Reset retry counts."""
        self.retry_counts.clear()
