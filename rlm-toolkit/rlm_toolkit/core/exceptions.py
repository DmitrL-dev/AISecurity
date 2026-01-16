"""
Exceptions
==========

Exception hierarchy for RLM-Toolkit.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class RLMError(Exception):
    """Base exception for all RLM errors.
    
    Attributes:
        message: Error message
        details: Additional error details
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message


class ProviderError(RLMError):
    """Error from LLM provider.
    
    Attributes:
        provider: Provider name
        status_code: HTTP status code if applicable
        response: Raw response if available
    """
    
    def __init__(
        self,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.provider = provider
        self.status_code = status_code
        self.response = response


class RateLimitError(ProviderError):
    """Rate limit exceeded."""
    
    def __init__(
        self,
        provider: str,
        retry_after: Optional[float] = None,
        **kwargs
    ):
        message = f"Rate limit exceeded for {provider}"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        super().__init__(message, provider, status_code=429, **kwargs)
        self.retry_after = retry_after


class AuthenticationError(ProviderError):
    """Authentication failed."""
    
    def __init__(self, provider: str, **kwargs):
        super().__init__(f"Authentication failed for {provider}", provider, status_code=401, **kwargs)


class QuotaExceededError(ProviderError):
    """API quota exceeded."""
    
    def __init__(self, provider: str, **kwargs):
        super().__init__(f"Quota exceeded for {provider}", provider, status_code=403, **kwargs)


class SecurityError(RLMError):
    """Security violation detected.
    
    Attributes:
        violation_type: Type of violation (import, builtin, pattern)
        code: The offending code
    """
    
    def __init__(
        self,
        message: str,
        violation_type: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.violation_type = violation_type
        self.code = code


class BlockedImportError(SecurityError):
    """Blocked import detected."""
    
    def __init__(self, module: str, code: Optional[str] = None):
        super().__init__(
            f"Blocked import: {module}",
            violation_type="import",
            code=code,
            details={"module": module},
        )


class BlockedBuiltinError(SecurityError):
    """Blocked builtin detected."""
    
    def __init__(self, builtin: str, code: Optional[str] = None):
        super().__init__(
            f"Blocked builtin: {builtin}",
            violation_type="builtin",
            code=code,
            details={"builtin": builtin},
        )


class ConfigurationError(RLMError):
    """Invalid configuration."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        super().__init__(message, details)
        self.field = field


class BudgetExceededError(RLMError):
    """Cost budget exceeded.
    
    Attributes:
        budget: Maximum budget
        spent: Amount spent
    """
    
    def __init__(self, budget: float, spent: float):
        super().__init__(
            f"Budget exceeded: ${spent:.4f} > ${budget:.4f}",
            details={"budget": budget, "spent": spent},
        )
        self.budget = budget
        self.spent = spent


class IterationLimitError(RLMError):
    """Maximum iterations exceeded."""
    
    def __init__(self, max_iterations: int, current: int):
        super().__init__(
            f"Max iterations exceeded: {current} > {max_iterations}",
            details={"max": max_iterations, "current": current},
        )


class ExecutionTimeoutError(RLMError):
    """Code execution timed out."""
    
    def __init__(self, timeout: float, code: Optional[str] = None):
        super().__init__(
            f"Execution timed out after {timeout}s",
            details={"timeout": timeout},
        )
        self.timeout = timeout
        self.code = code


class ContextTooLargeError(RLMError):
    """Context exceeds provider limits."""
    
    def __init__(self, size: int, max_size: int, provider: str):
        super().__init__(
            f"Context too large for {provider}: {size} > {max_size} tokens",
            details={"size": size, "max": max_size, "provider": provider},
        )
