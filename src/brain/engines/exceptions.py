"""
SENTINEL Security Engine Exceptions

Custom exceptions for all security engines.
"""


class SentinelEngineError(Exception):
    """Base exception for all engine errors."""

    def __init__(self, message: str, engine_name: str = "Unknown"):
        self.engine_name = engine_name
        self.message = message
        super().__init__(f"[{engine_name}] {message}")


class DetectionError(SentinelEngineError):
    """Error during threat detection."""

    pass


class ValidationError(SentinelEngineError):
    """Error during validation."""

    pass


class AnalysisError(SentinelEngineError):
    """Error during analysis."""

    pass


class ConfigurationError(SentinelEngineError):
    """Error in engine configuration."""

    pass


class InitializationError(SentinelEngineError):
    """Error during engine initialization."""

    pass


class TimeoutError(SentinelEngineError):
    """Engine operation timed out."""

    pass


class ResourceExhaustedError(SentinelEngineError):
    """Engine resources exhausted."""

    pass


class ThreatDetectedError(SentinelEngineError):
    """Critical threat detected - immediate action required."""

    def __init__(
        self,
        message: str,
        engine_name: str = "Unknown",
        severity: str = "high",
        threat_type: str = "unknown",
    ):
        super().__init__(message, engine_name)
        self.severity = severity
        self.threat_type = threat_type
