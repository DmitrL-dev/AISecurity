"""
SENTINEL Shield SDK — Exception Hierarchy.

Clean Architecture: Exceptions belong to the domain layer.
"""


class ShieldError(Exception):
    """Base exception for all Shield SDK errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(ShieldError):
    """Raised when API key is invalid or missing (HTTP 401)."""

    def __init__(self, message: str = "Invalid or missing API key") -> None:
        super().__init__(message, status_code=401)


class RateLimitError(ShieldError):
    """Raised when rate limit is exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ConnectionError(ShieldError):
    """Raised when Shield API is unreachable."""

    def __init__(self, message: str = "Cannot connect to Shield API") -> None:
        super().__init__(message, status_code=None)


class TimeoutError(ShieldError):
    """Raised when request times out."""

    def __init__(self, message: str = "Request timed out") -> None:
        super().__init__(message, status_code=None)


class ServerError(ShieldError):
    """Raised on Shield API 5xx errors."""

    def __init__(self, message: str = "Shield API server error") -> None:
        super().__init__(message, status_code=500)


class ValidationError(ShieldError):
    """Raised when input validation fails (HTTP 422)."""

    def __init__(self, message: str = "Input validation failed") -> None:
        super().__init__(message, status_code=422)
