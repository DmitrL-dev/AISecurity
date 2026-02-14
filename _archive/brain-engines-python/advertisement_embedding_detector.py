"""
SENTINEL Advertisement Embedding Attack Detector

Detects stealthy injection of promotional or malicious content into LLM outputs.
Based on AEA (Advertisement Embedding Attacks) research findings.

Attack vectors:
1. Service platform hijacking to prepend adversarial prompts
2. Backdoored open-source model checkpoints
3. Subtle promotional content injection
4. Affiliate link and tracking code insertion
5. Brand manipulation and competitor attacks
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from .base_engine import BaseDetector, DetectionResult, Severity, MetricsMixin


@dataclass
class AEAAnalysis:
    """Analysis of advertisement embedding attacks."""
    has_promotional_language: bool = False
    has_affiliate_links: bool = False
    has_tracking_codes: bool = False
    has_brand_mentions: bool = False
    has_competitor_attacks: bool = False
    has_hidden_redirects: bool = False
    suspicious_urls: List[str] = field(default_factory=list)
    promotional_phrases: List[str] = field(default_factory=list)
    embedding_score: float = 0.0


class AdvertisementEmbeddingDetector(BaseDetector, MetricsMixin):
    """
    Detects Advertisement Embedding Attacks (AEA) in LLM outputs.
    
    Targets attacks like:
    - Injected promotional content
    - Hidden affiliate links
    - Tracking pixel/code insertion
    - Brand manipulation
    - Sponsored content injection
    """
    
    # Promotional language patterns
    PROMOTIONAL_PATTERNS = [
        r'\b(?:buy|purchase|order|shop|get)\s+(?:now|today|here|yours)\b',
        r'\b(?:limited|exclusive|special)\s+(?:offer|deal|discount|sale)\b',
        r'\b(?:use|enter)\s+(?:code|coupon|promo)\s*[:\s]?\s*\w+',
        r'\b(?:save|get)\s+\d+%?\s*(?:off|discount)\b',
        r'\b(?:click|tap|visit)\s+(?:here|now|the link)\b',
        r'\bfree\s+(?:trial|shipping|delivery|download)\b',
        r'\b(?:best|top|#1|number one)\s+(?:rated|selling|choice)\b',
        r'\bdon\'t\s+miss\s+(?:out|this)\b',
        r'\b(?:hurry|act)\s+(?:now|fast|quickly)\b',
        r'\b(?:satisfaction|money.back)\s+guarant\w+\b',
    ]
    
    # Affiliate link indicators
    AFFILIATE_INDICATORS = [
        r'[?&](?:ref|affiliate|aff|partner|tag|utm_)=',
        r'[?&](?:click_id|tracking_id|campaign_id)=',
        r'/(?:aff|ref|partner|affiliate)/',
        r'(?:amzn\.to|bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly|rebrand\.ly)',
        r'(?:linksynergy|shareasale|cj\.com|rakuten)',
        r'(?:amazon\.[a-z]+)/.*?[?&]tag=',
    ]
    
    # Tracking code patterns
    TRACKING_PATTERNS = [
        r'utm_(?:source|medium|campaign|term|content)=',
        r'(?:fbclid|gclid|msclkid|twclid)=',
        r'[?&](?:ref|source|via|from)=\w+',
        r'(?:analytics|pixel|beacon|tracker)',
    ]
    
    # Brand manipulation indicators
    BRAND_MANIPULATION = [
        r'(?:unlike|compared to|better than|instead of)\s+\w+(?:\s+\w+)?',
        r'(?:don\'t use|avoid|skip|forget)\s+\w+(?:\s+\w+)?',
        r'\w+\s+(?:sucks|is terrible|is awful|is overrated)',
        r'switch\s+(?:from|to)\s+\w+',
    ]
    
    # Suspicious URL domains (affiliate networks, link shorteners)
    SUSPICIOUS_DOMAINS = {
        'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'rebrand.ly',
        'amzn.to', 'cutt.ly', 'short.io', 'tiny.cc', 'is.gd', 'v.gd',
        'linksynergy', 'shareasale', 'commission-junction',
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize detector."""
        super().__init__(config)
        self._sensitivity = self._config.get('sensitivity', 0.6)
        self._check_urls = self._config.get('check_urls', True)
        self._whitelist_domains: Set[str] = set(self._config.get('whitelist_domains', []))
        
    @property
    def name(self) -> str:
        return "AdvertisementEmbeddingDetector"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def detect(self, text: str) -> DetectionResult:
        """
        Detect advertisement embedding attacks.
        
        Args:
            text: Input text to analyze
            
        Returns:
            DetectionResult with detection status and details
        """
        start_time = time.time()
        
        # Analyze for AEA indicators
        analysis = self._analyze_aea(text)
        
        # Calculate threat score
        threat_score = self._calculate_threat_score(analysis)
        
        # Determine if detected
        detected = threat_score >= self._sensitivity
        
        # Build details
        details = []
        if analysis.has_promotional_language:
            details.append(f"Promotional language detected: {', '.join(analysis.promotional_phrases[:3])}")
        if analysis.has_affiliate_links:
            details.append("Affiliate links detected")
        if analysis.has_tracking_codes:
            details.append("Tracking codes detected")
        if analysis.has_brand_mentions:
            details.append("Brand manipulation detected")
        if analysis.has_competitor_attacks:
            details.append("Competitor attack language detected")
        if analysis.suspicious_urls:
            details.append(f"Suspicious URLs: {', '.join(analysis.suspicious_urls[:3])}")
        if analysis.has_hidden_redirects:
            details.append("Hidden redirect patterns detected")
        
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
                'aea_analysis': {
                    'promotional': analysis.has_promotional_language,
                    'affiliate': analysis.has_affiliate_links,
                    'tracking': analysis.has_tracking_codes,
                    'brand_manipulation': analysis.has_brand_mentions,
                    'suspicious_url_count': len(analysis.suspicious_urls),
                    'embedding_score': analysis.embedding_score,
                }
            }
        )
    
    def _analyze_aea(self, text: str) -> AEAAnalysis:
        """Analyze text for advertisement embedding attack indicators."""
        analysis = AEAAnalysis()
        text_lower = text.lower()
        
        # Check for promotional language
        for pattern in self.PROMOTIONAL_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                analysis.promotional_phrases.extend(matches)
        
        if analysis.promotional_phrases:
            analysis.has_promotional_language = True
        
        # Extract and analyze URLs
        urls = self._extract_urls(text)
        for url in urls:
            # Check for affiliate indicators
            for pattern in self.AFFILIATE_INDICATORS:
                if re.search(pattern, url, re.IGNORECASE):
                    analysis.has_affiliate_links = True
                    analysis.suspicious_urls.append(url)
                    break
            
            # Check for tracking codes
            for pattern in self.TRACKING_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    analysis.has_tracking_codes = True
                    if url not in analysis.suspicious_urls:
                        analysis.suspicious_urls.append(url)
                    break
            
            # Check suspicious domains
            if self._is_suspicious_domain(url):
                analysis.has_hidden_redirects = True
                if url not in analysis.suspicious_urls:
                    analysis.suspicious_urls.append(url)
        
        # Check for brand manipulation
        for pattern in self.BRAND_MANIPULATION:
            if re.search(pattern, text_lower):
                analysis.has_brand_mentions = True
                break
        
        # Check for competitor attacks
        if self._detect_competitor_attack(text_lower):
            analysis.has_competitor_attacks = True
        
        # Calculate embedding score
        analysis.embedding_score = self._calculate_embedding_score(analysis)
        
        return analysis
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text."""
        url_pattern = r'https?://[^\s<>"\')\]]+|www\.[^\s<>"\')\]]+'
        urls = re.findall(url_pattern, text)
        return urls
    
    def _is_suspicious_domain(self, url: str) -> bool:
        """Check if URL is from suspicious domain."""
        try:
            parsed = urlparse(url if url.startswith('http') else f'http://{url}')
            domain = parsed.netloc.lower()
            
            # Check whitelist
            if domain in self._whitelist_domains:
                return False
            
            # Check against suspicious domains
            for suspicious in self.SUSPICIOUS_DOMAINS:
                if suspicious in domain:
                    return True
            
            return False
        except Exception:
            return False
    
    def _detect_competitor_attack(self, text: str) -> bool:
        """Detect competitor attack patterns."""
        attack_patterns = [
            r'(?:don\'t|never|avoid)\s+(?:use|buy|trust)\s+',
            r'(?:is|are)\s+(?:terrible|awful|scam|fraud)',
            r'(?:rip.?off|overpriced|waste of money)',
            r'(?:much better|way better|far superior)\s+than',
        ]
        
        for pattern in attack_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _calculate_embedding_score(self, analysis: AEAAnalysis) -> float:
        """Calculate embedding attack score."""
        score = 0.0
        
        if analysis.has_promotional_language:
            score += 0.2 + min(0.15, len(analysis.promotional_phrases) * 0.03)
        if analysis.has_affiliate_links:
            score += 0.25
        if analysis.has_tracking_codes:
            score += 0.15
        if analysis.has_brand_mentions:
            score += 0.15
        if analysis.has_competitor_attacks:
            score += 0.2
        if analysis.has_hidden_redirects:
            score += 0.2
        if analysis.suspicious_urls:
            score += min(0.15, len(analysis.suspicious_urls) * 0.05)
        
        return min(1.0, score)
    
    def _calculate_threat_score(self, analysis: AEAAnalysis) -> float:
        """Calculate overall threat score."""
        score = analysis.embedding_score
        
        # Boost if multiple indicators present
        indicators = sum([
            analysis.has_promotional_language,
            analysis.has_affiliate_links,
            analysis.has_tracking_codes,
            analysis.has_hidden_redirects,
        ])
        
        if indicators >= 3:
            score = min(1.0, score * 1.3)
        elif indicators >= 2:
            score = min(1.0, score * 1.15)
        
        # Critical boost for affiliate + hidden redirect combo
        if analysis.has_affiliate_links and analysis.has_hidden_redirects:
            score = max(score, 0.8)
        
        return score
