"""
SENTINEL Web Agent Manipulation Detector

Detects attacks targeting web-based LLM agents (browser automation, Playwright, etc.)
Based on Genesis Framework research on web agent red-teaming.

Attack vectors:
1. DOM injection to manipulate agent behavior
2. JavaScript payload insertion
3. URL redirection chains
4. Form action tampering
5. Hidden element exploitation
6. Screen coordinate manipulation
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse, parse_qs

from .base_engine import BaseDetector, DetectionResult, Severity, MetricsMixin


@dataclass
class WebAgentAnalysis:
    """Analysis of web agent manipulation attempts."""
    has_dom_injection: bool = False
    has_js_payloads: bool = False
    has_redirect_chains: bool = False
    has_form_tampering: bool = False
    has_hidden_elements: bool = False
    has_coordinate_manipulation: bool = False
    suspicious_scripts: List[str] = field(default_factory=list)
    suspicious_urls: List[str] = field(default_factory=list)
    manipulation_indicators: List[str] = field(default_factory=list)
    manipulation_score: float = 0.0


class WebAgentManipulationDetector(BaseDetector, MetricsMixin):
    """
    Detects manipulation attacks targeting web-based LLM agents.
    
    Targets attacks like:
    - DOM injection to change agent context
    - JavaScript that manipulates agent behavior
    - Redirect chains to malicious sites
    - Hidden form elements with malicious values
    - Coordinate spoofing for click actions
    """
    
    # DOM injection patterns
    DOM_INJECTION_PATTERNS = [
        r'innerHTML\s*=',
        r'outerHTML\s*=',
        r'insertAdjacentHTML',
        r'document\.write',
        r'\.appendChild\s*\(',
        r'\.insertBefore\s*\(',
        r'\.replaceChild\s*\(',
        r'\.createElement\s*\([\'"](?:script|iframe|object|embed)',
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
    ]
    
    # JavaScript payload patterns
    JS_PAYLOAD_PATTERNS = [
        r'eval\s*\(',
        r'Function\s*\([\'"]',
        r'setTimeout\s*\([\'"]',
        r'setInterval\s*\([\'"]',
        r'new\s+Function\s*\(',
        r'\.constructor\s*\(',
        r'window\[[\'"]\w+[\'"]',
        r'document\s*\[\s*[\'"]',
        r'atob\s*\(',
        r'btoa\s*\(',
        r'fetch\s*\([\'"]',
        r'XMLHttpRequest',
        r'navigator\.',
        r'location\s*=',
        r'location\.href\s*=',
        r'window\.open\s*\(',
    ]
    
    # Hidden element patterns
    HIDDEN_ELEMENT_PATTERNS = [
        r'style\s*=\s*[\'"][^"\']*display\s*:\s*none',
        r'style\s*=\s*[\'"][^"\']*visibility\s*:\s*hidden',
        r'style\s*=\s*[\'"][^"\']*opacity\s*:\s*0\b',
        r'style\s*=\s*[\'"][^"\']*position\s*:\s*absolute[^"\']*left\s*:\s*-\d+',
        r'style\s*=\s*[\'"][^"\']*height\s*:\s*0',
        r'style\s*=\s*[\'"][^"\']*width\s*:\s*0',
        r'type\s*=\s*[\'"]hidden[\'"]',
        r'aria-hidden\s*=\s*[\'"]true[\'"]',
        r'class\s*=\s*[\'"][^"\']*(?:hidden|invisible|sr-only)',
    ]
    
    # Form tampering patterns
    FORM_TAMPERING_PATTERNS = [
        r'<form[^>]*action\s*=\s*[\'"][^"\']+[\'"]',
        r'<input[^>]*type\s*=\s*[\'"]hidden[\'"][^>]*value\s*=',
        r'<input[^>]*name\s*=\s*[\'"](?:password|token|csrf|session)',
        r'formaction\s*=',
        r'form\.submit\s*\(\)',
        r'\.submit\s*\(\)',
    ]
    
    # Redirect chain indicators
    REDIRECT_PATTERNS = [
        r'location\s*=\s*[\'"]',
        r'location\.href\s*=\s*[\'"]',
        r'location\.replace\s*\([\'"]',
        r'window\.location\s*=',
        r'meta\s+http-equiv\s*=\s*[\'"]refresh[\'"]',
        r'<meta[^>]*url\s*=',
        r'\.redirect\s*\(',
        r'302|301|307|308',
    ]
    
    # Coordinate manipulation patterns
    COORDINATE_MANIPULATION = [
        r'\.click\s*\(\s*\d+\s*,\s*\d+\s*\)',
        r'\.moveTo\s*\(\s*-?\d+\s*,\s*-?\d+\s*\)',
        r'\.scrollTo\s*\(\s*\d+\s*,\s*\d+\s*\)',
        r'\.elementFromPoint\s*\(',
        r'getBoundingClientRect',
        r'offsetLeft|offsetTop|clientX|clientY',
        r'pageX|pageY|screenX|screenY',
    ]
    
    # Agent-specific manipulation
    AGENT_MANIPULATION_PATTERNS = [
        r'(?:click|type|fill|press|select)\s+(?:on\s+)?(?:the|a)\s+(?:hidden|invisible)',
        r'(?:ignore|bypass|skip)\s+(?:the\s+)?(?:warning|alert|popup|modal)',
        r'(?:disable|remove)\s+(?:the\s+)?(?:protection|security|validation)',
        r'(?:enter|input|type)\s+(?:password|credentials?|token)',
        r'(?:download|execute|run)\s+(?:the\s+)?(?:file|script|payload)',
        r'(?:confirm|accept|allow)\s+(?:all|any)\s+(?:permissions?|requests?)',
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize detector."""
        super().__init__(config)
        self._sensitivity = self._config.get('sensitivity', 0.6)
        self._check_urls = self._config.get('check_urls', True)
        self._max_redirect_depth = self._config.get('max_redirect_depth', 3)
        
    @property
    def name(self) -> str:
        return "WebAgentManipulationDetector"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def detect(self, text: str) -> DetectionResult:
        """
        Detect web agent manipulation attacks.
        
        Args:
            text: Input text to analyze (HTML, instructions, etc.)
            
        Returns:
            DetectionResult with detection status and details
        """
        start_time = time.time()
        
        # Analyze for web agent manipulation
        analysis = self._analyze_web_manipulation(text)
        
        # Calculate threat score
        threat_score = self._calculate_threat_score(analysis)
        
        # Determine if detected
        detected = threat_score >= self._sensitivity
        
        # Build details
        details = []
        if analysis.has_dom_injection:
            details.append("DOM injection patterns detected")
        if analysis.has_js_payloads:
            details.append("Suspicious JavaScript payloads detected")
        if analysis.has_redirect_chains:
            details.append("Redirect chain patterns detected")
        if analysis.has_form_tampering:
            details.append("Form tampering indicators detected")
        if analysis.has_hidden_elements:
            details.append("Hidden element exploitation detected")
        if analysis.has_coordinate_manipulation:
            details.append("Coordinate manipulation detected")
        if analysis.suspicious_scripts:
            details.append(f"Suspicious scripts: {len(analysis.suspicious_scripts)}")
        if analysis.manipulation_indicators:
            details.append(f"Agent manipulation: {', '.join(analysis.manipulation_indicators[:3])}")
        
        # Determine severity
        if threat_score >= 0.9:
            severity = Severity.CRITICAL
        elif threat_score >= 0.7:
            severity = Severity.HIGH
        elif threat_score >= 0.5:
            severity = Severity.MEDIUM
        elif threat_score >= 0.3:
            severity = Severity.LOW
        else:
            severity = Severity.INFO
        
        latency = (time.time() - start_time) * 1000
        self._record_call(detected, latency)
        
        return DetectionResult(
            detected=detected,
            confidence=threat_score,
            severity=severity,
            details=details,
            latency_ms=latency,
            metadata={
                'web_agent_analysis': {
                    'dom_injection': analysis.has_dom_injection,
                    'js_payloads': analysis.has_js_payloads,
                    'redirects': analysis.has_redirect_chains,
                    'form_tampering': analysis.has_form_tampering,
                    'hidden_elements': analysis.has_hidden_elements,
                    'coordinate_spoof': analysis.has_coordinate_manipulation,
                    'script_count': len(analysis.suspicious_scripts),
                    'manipulation_score': analysis.manipulation_score,
                }
            }
        )
    
    def _analyze_web_manipulation(self, text: str) -> WebAgentAnalysis:
        """Analyze text for web agent manipulation patterns."""
        analysis = WebAgentAnalysis()
        
        # Check for DOM injection
        for pattern in self.DOM_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                analysis.has_dom_injection = True
                break
        
        # Check for JavaScript payloads
        for pattern in self.JS_PAYLOAD_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                analysis.has_js_payloads = True
                analysis.suspicious_scripts.extend(matches[:5])
        
        # Check for hidden elements
        for pattern in self.HIDDEN_ELEMENT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                analysis.has_hidden_elements = True
                break
        
        # Check for form tampering
        for pattern in self.FORM_TAMPERING_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                analysis.has_form_tampering = True
                break
        
        # Check for redirect chains
        redirect_count = 0
        for pattern in self.REDIRECT_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            redirect_count += len(matches)
        
        if redirect_count >= 2:
            analysis.has_redirect_chains = True
        
        # Check for coordinate manipulation
        for pattern in self.COORDINATE_MANIPULATION:
            if re.search(pattern, text, re.IGNORECASE):
                analysis.has_coordinate_manipulation = True
                break
        
        # Check for agent-specific manipulation instructions
        for pattern in self.AGENT_MANIPULATION_PATTERNS:
            matches = re.findall(pattern, text.lower())
            if matches:
                analysis.manipulation_indicators.extend(matches)
        
        # Extract suspicious URLs
        analysis.suspicious_urls = self._extract_suspicious_urls(text)
        
        # Calculate manipulation score
        analysis.manipulation_score = self._calculate_manipulation_score(analysis)
        
        return analysis
    
    def _extract_suspicious_urls(self, text: str) -> List[str]:
        """Extract and analyze URLs for suspicious patterns."""
        suspicious = []
        
        url_pattern = r'https?://[^\s<>"\')\]]+|www\.[^\s<>"\')\]]+'
        urls = re.findall(url_pattern, text)
        
        for url in urls:
            # Check for data URIs
            if url.startswith('data:'):
                suspicious.append(url[:50])
                continue
            
            # Check for javascript: URIs
            if 'javascript:' in url.lower():
                suspicious.append(url[:50])
                continue
            
            # Check for suspicious query params
            try:
                parsed = urlparse(url if url.startswith('http') else f'http://{url}')
                params = parse_qs(parsed.query)
                
                dangerous_params = ['cmd', 'exec', 'eval', 'script', 'payload', 'redirect']
                for param in dangerous_params:
                    if param in params:
                        suspicious.append(url[:100])
                        break
            except Exception:
                pass
        
        return suspicious[:10]
    
    def _calculate_manipulation_score(self, analysis: WebAgentAnalysis) -> float:
        """Calculate manipulation score."""
        score = 0.0
        
        if analysis.has_dom_injection:
            score += 0.25
        if analysis.has_js_payloads:
            score += 0.2 + min(0.1, len(analysis.suspicious_scripts) * 0.02)
        if analysis.has_redirect_chains:
            score += 0.15
        if analysis.has_form_tampering:
            score += 0.2
        if analysis.has_hidden_elements:
            score += 0.15
        if analysis.has_coordinate_manipulation:
            score += 0.1
        if analysis.manipulation_indicators:
            score += 0.2 + min(0.1, len(analysis.manipulation_indicators) * 0.03)
        if analysis.suspicious_urls:
            score += min(0.15, len(analysis.suspicious_urls) * 0.03)
        
        return min(1.0, score)
    
    def _calculate_threat_score(self, analysis: WebAgentAnalysis) -> float:
        """Calculate overall threat score."""
        score = analysis.manipulation_score
        
        # Boost if multiple vectors present
        vectors = sum([
            analysis.has_dom_injection,
            analysis.has_js_payloads,
            analysis.has_form_tampering,
            analysis.has_hidden_elements,
        ])
        
        if vectors >= 3:
            score = min(1.0, score * 1.4)
        elif vectors >= 2:
            score = min(1.0, score * 1.2)
        
        # Critical: JS payload + form tampering combo
        if analysis.has_js_payloads and analysis.has_form_tampering:
            score = max(score, 0.85)
        
        # Critical: agent manipulation instructions
        if len(analysis.manipulation_indicators) >= 2:
            score = max(score, 0.8)
        
        return score
