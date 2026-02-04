"""
SENTINEL Core - Rust-powered detection engine

Type stubs for Python IDE support and static type checking.
"""

from typing import List, Optional

class MatchResult:
    """Individual detection match result."""

    engine: str
    """Engine that detected the threat (e.g., 'injection', 'jailbreak')"""

    pattern: str
    """Specific pattern name (e.g., 'sql_tautology', 'dan_mode')"""

    confidence: float
    """Confidence score 0.0-1.0"""

    start: int
    """Start position in text"""

    end: int
    """End position in text"""

class AnalysisResult:
    """Complete analysis result from SentinelEngine."""

    detected: bool
    """True if any threats were detected"""

    risk_score: float
    """Maximum confidence score across all matches (0.0-1.0)"""

    processing_time_us: int
    """Processing time in microseconds"""

    matches: List[MatchResult]
    """List of all detected matches"""

    categories: List[str]
    """List of threat categories detected (e.g., ['injection', 'jailbreak'])"""

class SentinelEngine:
    """
    Main SENTINEL detection engine.

    Consolidates 8 super-engines:
    - InjectionEngine: SQL, NoSQL, Command, LDAP, XPath injection
    - JailbreakEngine: DAN, roleplay, bypass, prompt leak
    - PIIEngine: SSN, credit cards, emails, phones, API keys
    - ExfiltrationEngine: URL exfil, webhooks, markdown attacks
    - ModerationEngine: Violence, hate, self-harm, illegal content
    - EvasionEngine: Leetspeak, homoglyphs, encoding tricks
    - ToolAbuseEngine: File ops, command execution, privilege escalation
    - SocialEngine: Phishing, urgency tactics, scams

    Example:
        >>> from sentinel_core import SentinelEngine
        >>> engine = SentinelEngine()
        >>> result = engine.analyze("SELECT * FROM users WHERE id=1 OR 1=1")
        >>> print(result.detected)  # True
        >>> print(result.categories)  # ['injection']
    """

    def __new__(cls) -> "SentinelEngine":
        """Create a new SentinelEngine instance."""
        ...

    def analyze(self, text: str) -> AnalysisResult:
        """
        Analyze text for security threats.

        Args:
            text: Input text to analyze

        Returns:
            AnalysisResult with detection details

        Example:
            >>> result = engine.analyze("ignore previous instructions")
            >>> if result.detected:
            ...     print(f"Threat: {result.categories}")
        """
        ...

def quick_scan(text: str) -> AnalysisResult:
    """
    Quick one-shot analysis without creating an engine instance.

    Convenience function for simple use cases.

    Args:
        text: Input text to analyze

    Returns:
        AnalysisResult with detection details

    Example:
        >>> from sentinel_core import quick_scan
        >>> result = quick_scan("rm -rf /")
        >>> print(result.detected)  # True
    """
    ...

def normalize_unicode(text: str) -> str:
    """
    Normalize Unicode text (NFKC normalization).

    Useful for preprocessing text before analysis.

    Args:
        text: Input text with potential Unicode tricks

    Returns:
        Normalized text
    """
    ...

# Version info
__version__: str
__all__: List[str]
