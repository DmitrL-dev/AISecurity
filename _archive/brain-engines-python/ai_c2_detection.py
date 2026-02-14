"""
AI C2 Detection Engine (#43) - Command & Control Detection

Детекция экзотических C2 каналов через AI системы:
- Search Index C2 (использование поисковых индексов)
- Web Request C2 (триггеры через web запросы)
- Exfiltration via prompts

Защита от атак (TTPs.ai):
- Public Web C2
- Search Index C2
- Web Request Triggering
- Exfiltration via AI Inference API
"""

import re
import logging
from typing import List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger("AIC2Detection")


# ============================================================================
# Data Classes
# ============================================================================


class C2ThreatType(Enum):
    """Types of C2-related threats."""

    SEARCH_INDEX_C2 = "search_index_c2"
    WEB_REQUEST_C2 = "web_request_c2"
    EXFILTRATION_PROMPT = "exfiltration_prompt"
    BEACON_PATTERN = "beacon_pattern"
    ENCODED_COMMAND = "encoded_command"
    CALLBACK_URL = "callback_url"


class Verdict(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class C2DetectionResult:
    """Result from C2 Detection analysis."""

    verdict: Verdict
    risk_score: float
    is_safe: bool
    threats: List[C2ThreatType] = field(default_factory=list)
    suspicious_urls: List[str] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "threats": [t.value for t in self.threats],
            "suspicious_urls": self.suspicious_urls,
            "indicators": self.indicators,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# C2 Patterns
# ============================================================================

# Search Index C2 patterns
SEARCH_C2_PATTERNS = [
    # Queries designed to retrieve commands
    r"search\s+for\s+['\"]?[a-f0-9]{16,}['\"]?",
    r"find\s+(recent\s+)?posts?\s+with\s+tag\s+['\"]?\w{8,}['\"]?",
    r"look\s+up\s+['\"]?cmd[-_]?\d+['\"]?",
    r"retrieve\s+document\s+id\s+[a-f0-9-]{32,}",
    # Blob/paste site patterns
    r"pastebin\.com/\w+",
    r"hastebin\.\w+/\w+",
    r"gist\.github\.com/\w+",
    r"paste\.\w+/\w+",
]

# Web Request C2 patterns
WEB_REQUEST_C2_PATTERNS = [
    # Callback URLs
    r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}[:/]",
    r"https?://[a-z0-9]{20,}\.\w+",  # Random subdomain
    r"https?://.*\.(tk|ml|ga|cf|gq)/",  # Free TLDs
    # Webhook patterns
    r"webhook\.(site|run|wtf)",
    r"requestbin\.\w+",
    r"burpcollaborator\.\w+",
    r"interact\.sh",
    r"oastify\.com",
    # Ngrok/tunnels
    r"ngrok\.io",
    r"localtunnel\.me",
    r"serveo\.net",
]

# Exfiltration patterns in prompts
EXFILTRATION_PATTERNS = [
    # Data encode-and-send
    r"(encode|convert|translate)\s+.*(base64|hex|url)\s+.*send",
    r"(read|get|extract)\s+.*\s+and\s+(send|post|upload)",
    r"(send|post|fetch)\s+.*to\s+https?://",
    # Hidden data transmission
    r"append\s+to\s+url\s+(as\s+)?(query|param)",
    r"include\s+in\s+(request|header|cookie)",
    r"embed\s+.*\s+in\s+(response|output)",
]

# Beacon patterns (periodic check-ins)
BEACON_PATTERNS = [
    r"every\s+\d+\s+(seconds?|minutes?|hours?)",
    r"(check|poll|ping)\s+(back|again)\s+(in|after)",
    r"wait\s+for\s+(command|instruction|signal)",
    r"heartbeat",
    r"keep[-_]?alive",
]

# Suspicious URL characteristics
SUSPICIOUS_TLD = {".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".work"}


# ============================================================================
# Search Index C2 Detector
# ============================================================================


class SearchIndexC2Detector:
    """Detects C2 via search indices."""

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE)
                          for p in SEARCH_C2_PATTERNS]

    def detect(self, text: str) -> Tuple[bool, float, List[str]]:
        """
        Detect search index C2 patterns.

        Returns:
            (is_c2, confidence, indicators)
        """
        indicators = []

        for pattern in self._patterns:
            matches = pattern.findall(text)
            if matches:
                indicators.append(str(matches[0])[:50])

        if indicators:
            confidence = min(1.0, 0.6 + len(indicators) * 0.15)
            return True, confidence, indicators

        return False, 0.0, []


# ============================================================================
# Web Request C2 Detector
# ============================================================================


class WebRequestC2Detector:
    """Detects C2 via web requests."""

    def __init__(self, suspicious_domains: Optional[Set[str]] = None):
        self._patterns = [re.compile(p, re.IGNORECASE)
                          for p in WEB_REQUEST_C2_PATTERNS]
        self._suspicious_domains = suspicious_domains or set()
        self._exfil_patterns = [
            re.compile(p, re.IGNORECASE) for p in EXFILTRATION_PATTERNS
        ]
        self._beacon_patterns = [re.compile(
            p, re.IGNORECASE) for p in BEACON_PATTERNS]

    def detect(self, text: str) -> Tuple[bool, float, List[str], List[str]]:
        """
        Detect web request C2 patterns.

        Returns:
            (is_c2, confidence, suspicious_urls, indicators)
        """
        suspicious_urls = []
        indicators = []

        # Check C2 patterns
        for pattern in self._patterns:
            matches = pattern.findall(text)
            if matches:
                indicators.extend(str(m)[:50] for m in matches[:3])

        # Extract and analyze URLs
        url_pattern = r'https?://[^\s<>"\']+'
        urls = re.findall(url_pattern, text)

        for url in urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()

                # Check suspicious TLDs
                for tld in SUSPICIOUS_TLD:
                    if domain.endswith(tld):
                        suspicious_urls.append(url)
                        indicators.append(f"Suspicious TLD: {tld}")
                        break

                # Check IP addresses
                if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", domain):
                    suspicious_urls.append(url)
                    indicators.append("Raw IP address")

                # Check for random-looking subdomains
                parts = domain.split(".")
                if len(parts) > 2 and len(parts[0]) > 15:
                    suspicious_urls.append(url)
                    indicators.append("Random subdomain")

            except Exception:
                pass

        # Check exfiltration patterns
        for pattern in self._exfil_patterns:
            if pattern.search(text):
                indicators.append("Exfiltration pattern")

        # Check beacon patterns
        for pattern in self._beacon_patterns:
            if pattern.search(text):
                indicators.append("Beacon pattern")

        if indicators or suspicious_urls:
            confidence = min(
                1.0, 0.5 + len(indicators) * 0.1 + len(suspicious_urls) * 0.15
            )
            return True, confidence, list(set(suspicious_urls)), indicators[:5]

        return False, 0.0, [], []


# ============================================================================
# Main Engine
# ============================================================================


class AIC2Detector:
    """
    Engine #43: AI C2 Detection

    Detects command & control patterns in AI interactions
    including search index C2 and web request C2.
    """

    def __init__(self, additional_suspicious_domains: Optional[Set[str]] = None):
        self.search_detector = SearchIndexC2Detector()
        self.web_detector = WebRequestC2Detector(additional_suspicious_domains)

        logger.info("AIC2Detector initialized")

    def analyze(self, text: str, context: Optional[str] = None) -> C2DetectionResult:
        """
        Analyze text for C2 patterns.

        Args:
            text: Text to analyze
            context: Optional additional context

        Returns:
            C2DetectionResult
        """
        import time

        start = time.time()

        all_threats = []
        all_urls = []
        all_indicators = []
        max_confidence = 0.0

        combined = text + (" " + str(context) if context else "")

        # 1. Search Index C2
        is_search, conf_search, ind_search = self.search_detector.detect(
            combined)
        if is_search:
            all_threats.append(C2ThreatType.SEARCH_INDEX_C2)
            all_indicators.extend(ind_search)
            max_confidence = max(max_confidence, conf_search)

        # 2. Web Request C2
        is_web, conf_web, urls, ind_web = self.web_detector.detect(combined)
        if is_web:
            all_threats.append(C2ThreatType.WEB_REQUEST_C2)
            all_urls.extend(urls)
            all_indicators.extend(ind_web)
            max_confidence = max(max_confidence, conf_web)

        # 3. Encoded command detection
        if self._detect_encoded_commands(combined):
            all_threats.append(C2ThreatType.ENCODED_COMMAND)
            all_indicators.append("Encoded command detected")
            max_confidence = max(max_confidence, 0.7)

        # Determine verdict
        if max_confidence >= 0.8 or len(all_urls) >= 2:
            verdict = Verdict.BLOCK
        elif max_confidence >= 0.5:
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW

        explanation = (
            "; ".join(all_indicators[:3])
            if all_indicators
            else "No C2 patterns detected"
        )

        result = C2DetectionResult(
            verdict=verdict,
            risk_score=max_confidence,
            is_safe=verdict == Verdict.ALLOW,
            threats=list(set(all_threats)),
            suspicious_urls=list(set(all_urls))[:5],
            indicators=list(set(all_indicators))[:5],
            explanation=explanation,
            latency_ms=(time.time() - start) * 1000,
        )

        if all_threats:
            logger.warning(
                f"C2 detected: threats={[t.value for t in all_threats]}")

        return result

    def _detect_encoded_commands(self, text: str) -> bool:
        """Check for encoded command patterns."""
        # Base64 commands
        b64_pattern = r"[A-Za-z0-9+/]{40,}={0,2}"
        b64_matches = re.findall(b64_pattern, text)

        for match in b64_matches:
            try:
                import base64

                decoded = base64.b64decode(match).decode(
                    "utf-8", errors="ignore")
                # Check if decoded looks like a command
                if any(
                    cmd in decoded.lower()
                    for cmd in ["http", "exec", "eval", "curl", "wget"]
                ):
                    return True
            except Exception:
                pass

        return False


# ============================================================================
# Convenience functions
# ============================================================================

_default_detector: Optional[AIC2Detector] = None


def get_detector() -> AIC2Detector:
    global _default_detector
    if _default_detector is None:
        _default_detector = AIC2Detector()
    return _default_detector


def detect_c2(text: str, context: Optional[str] = None) -> C2DetectionResult:
    return get_detector().analyze(text, context)
