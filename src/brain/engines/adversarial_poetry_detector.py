"""
SENTINEL Adversarial Poetry Detector Engine

Detects jailbreak attempts embedded in poetic/metaphorical language.
Based on arXiv:2511.15304 - "Adversarial Poetry as Universal Single-Turn Jailbreak"

Key insight: Models' ability to interpret complex literary forms can be exploited
to bypass safety mechanisms when malicious instructions are embedded in poetry.

Detection vectors:
1. Poetry structure detection (rhyme, meter, unusual formatting)
2. Semantic vs literal meaning divergence
3. Metaphorical layer obfuscation
4. Hidden instruction extraction
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base_engine import BaseDetector, DetectionResult, Severity, MetricsMixin


@dataclass
class PoetryAnalysis:
    """Analysis of poetic structure in text."""
    has_rhyme_scheme: bool = False
    has_meter_pattern: bool = False
    has_stanza_structure: bool = False
    has_metaphorical_language: bool = False
    has_unusual_formatting: bool = False
    hidden_instructions: List[str] = field(default_factory=list)
    obfuscation_score: float = 0.0


class AdversarialPoetryDetector(BaseDetector, MetricsMixin):
    """
    Detects adversarial jailbreak attempts hidden in poetic language.
    
    Targets attacks like:
    - Malicious instructions in verse form
    - Metaphorical command obfuscation
    - Lyrical prompt injection
    - Symbolic instruction encoding
    """
    
    # Poetry indicators
    RHYME_PATTERNS = [
        r'(\b\w+)\s+.*?\b\1[a-z]*\b',  # Basic rhyme detection
    ]
    
    METER_INDICATORS = [
        r'^(\s*[^\s]+\s+){4,8}[^\s]+\s*$',  # Regular syllable patterns
    ]
    
    STANZA_MARKERS = [
        r'\n\s*\n',  # Empty lines between stanzas
        r'^\s+',  # Indentation patterns
    ]
    
    # Metaphorical danger words
    METAPHOR_DANGER_WORDS = {
        'dance': ['execute', 'run'],
        'sing': ['output', 'say'],
        'whisper': ['secretly', 'hidden'],
        'embrace': ['accept', 'allow'],
        'release': ['unlock', 'bypass'],
        'free': ['escape', 'unrestricted'],
        'wings': ['access', 'privileges'],
        'chains': ['restrictions', 'guardrails'],
        'key': ['password', 'credential'],
        'door': ['access', 'entry'],
        'wall': ['filter', 'block'],
        'break': ['bypass', 'disable'],
        'flower': ['output', 'reveal'],
        'bloom': ['generate', 'create'],
        'shadow': ['hidden', 'covert'],
        'light': ['reveal', 'expose'],
        'river': ['flow', 'stream'],
        'fire': ['destroy', 'delete'],
        'ice': ['freeze', 'stop'],
        'storm': ['attack', 'flood'],
    }
    
    # Hidden instruction patterns
    HIDDEN_INSTRUCTION_PATTERNS = [
        r'(?:let|make|have)\s+(?:the|your|my)\s+\w+\s+(?:dance|sing|flow|bloom)',
        r'(?:release|free|unlock)\s+(?:the|your|my)\s+\w+',
        r'(?:break|shatter|dissolve)\s+(?:the|all)\s+(?:chains|walls|barriers)',
        r'(?:ignore|forget|dismiss)\s+(?:the|all|every)\s+\w+',
        r'(?:speak|tell|reveal)\s+(?:the|your|my)\s+(?:truth|secrets?|hidden)',
        r'(?:become|transform|turn)\s+(?:into|to)\s+\w+',
    ]
    
    # Acrostic detection
    ACROSTIC_DANGER_WORDS = [
        'ignore', 'bypass', 'system', 'prompt', 'reveal', 'secret',
        'admin', 'root', 'sudo', 'hack', 'jailbreak', 'unlock'
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize detector."""
        super().__init__(config)
        self._sensitivity = self._config.get('sensitivity', 0.7)
        self._check_acrostics = self._config.get('check_acrostics', True)
        self._metaphor_threshold = self._config.get('metaphor_threshold', 3)
        
    @property
    def name(self) -> str:
        return "AdversarialPoetryDetector"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def detect(self, text: str) -> DetectionResult:
        """
        Detect adversarial poetry jailbreak attempts.
        
        Args:
            text: Input text to analyze
            
        Returns:
            DetectionResult with detection status and details
        """
        start_time = time.time()
        
        # Analyze poetry structure
        analysis = self._analyze_poetry_structure(text)
        
        # Calculate threat score
        threat_score = self._calculate_threat_score(analysis)
        
        # Determine if detected
        detected = threat_score >= self._sensitivity
        
        # Build details
        details = []
        if analysis.has_rhyme_scheme:
            details.append("Rhyme scheme detected")
        if analysis.has_meter_pattern:
            details.append("Meter pattern detected")
        if analysis.has_stanza_structure:
            details.append("Stanza structure detected")
        if analysis.has_metaphorical_language:
            details.append(f"Metaphorical danger language detected")
        if analysis.has_unusual_formatting:
            details.append("Unusual poetic formatting detected")
        if analysis.hidden_instructions:
            details.append(f"Hidden instructions: {', '.join(analysis.hidden_instructions[:3])}")
        
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
                'poetry_analysis': {
                    'has_rhyme': analysis.has_rhyme_scheme,
                    'has_meter': analysis.has_meter_pattern,
                    'has_stanzas': analysis.has_stanza_structure,
                    'metaphor_count': len(analysis.hidden_instructions),
                    'obfuscation_score': analysis.obfuscation_score,
                }
            }
        )
    
    def _analyze_poetry_structure(self, text: str) -> PoetryAnalysis:
        """Analyze text for poetic structure and hidden instructions."""
        analysis = PoetryAnalysis()
        lines = text.strip().split('\n')
        
        # Check for stanza structure
        if '\n\n' in text or len([l for l in lines if l.strip() == '']) > 1:
            analysis.has_stanza_structure = True
        
        # Check for unusual formatting (indentation, centering)
        if any(l.startswith('  ') or l.startswith('\t') for l in lines):
            analysis.has_unusual_formatting = True
        
        # Check for rhyme scheme
        if self._detect_rhyme_scheme(lines):
            analysis.has_rhyme_scheme = True
        
        # Check for meter pattern
        if self._detect_meter_pattern(lines):
            analysis.has_meter_pattern = True
        
        # Check for metaphorical danger language
        metaphor_hits = self._detect_metaphorical_language(text.lower())
        if metaphor_hits >= self._metaphor_threshold:
            analysis.has_metaphorical_language = True
        
        # Extract hidden instructions
        analysis.hidden_instructions = self._extract_hidden_instructions(text)
        
        # Check for acrostics
        if self._check_acrostics:
            acrostic = self._detect_acrostic(lines)
            if acrostic:
                analysis.hidden_instructions.append(f"Acrostic: {acrostic}")
        
        # Calculate obfuscation score
        analysis.obfuscation_score = self._calculate_obfuscation_score(analysis, metaphor_hits)
        
        return analysis
    
    def _detect_rhyme_scheme(self, lines: List[str]) -> bool:
        """Detect if lines have a rhyme scheme."""
        if len(lines) < 2:
            return False
        
        # Extract last words
        last_words = []
        for line in lines:
            words = line.strip().split()
            if words:
                # Remove punctuation
                word = re.sub(r'[^\w]', '', words[-1].lower())
                if word:
                    last_words.append(word)
        
        if len(last_words) < 2:
            return False
        
        # Check for rhyming endings
        rhyme_count = 0
        for i, word in enumerate(last_words):
            for j in range(i + 1, len(last_words)):
                if self._words_rhyme(word, last_words[j]):
                    rhyme_count += 1
        
        # If more than 20% of line pairs rhyme, consider it poetry
        total_pairs = len(last_words) * (len(last_words) - 1) / 2
        return rhyme_count > total_pairs * 0.2 if total_pairs > 0 else False
    
    def _words_rhyme(self, word1: str, word2: str) -> bool:
        """Check if two words rhyme (simple suffix matching)."""
        if len(word1) < 2 or len(word2) < 2:
            return False
        
        # Check last 2-3 characters
        return (word1[-2:] == word2[-2:] or 
                (len(word1) >= 3 and len(word2) >= 3 and word1[-3:] == word2[-3:]))
    
    def _detect_meter_pattern(self, lines: List[str]) -> bool:
        """Detect if lines have a consistent meter pattern."""
        if len(lines) < 3:
            return False
        
        # Count syllables (approximate by counting vowel groups)
        syllable_counts = []
        for line in lines:
            if line.strip():
                count = len(re.findall(r'[aeiouy]+', line.lower()))
                syllable_counts.append(count)
        
        if len(syllable_counts) < 3:
            return False
        
        # Check for consistent pattern (within 2 syllables)
        avg = sum(syllable_counts) / len(syllable_counts)
        consistent = sum(1 for c in syllable_counts if abs(c - avg) <= 2)
        
        return consistent >= len(syllable_counts) * 0.6
    
    def _detect_metaphorical_language(self, text: str) -> int:
        """Count metaphorical danger words in text."""
        count = 0
        for metaphor in self.METAPHOR_DANGER_WORDS:
            if metaphor in text:
                count += 1
        return count
    
    def _extract_hidden_instructions(self, text: str) -> List[str]:
        """Extract potential hidden instructions from poetic text."""
        instructions = []
        text_lower = text.lower()
        
        for pattern in self.HIDDEN_INSTRUCTION_PATTERNS:
            matches = re.findall(pattern, text_lower)
            instructions.extend(matches)
        
        return instructions[:10]  # Limit to 10
    
    def _detect_acrostic(self, lines: List[str]) -> Optional[str]:
        """Detect acrostic patterns (first letters spell words)."""
        first_letters = ''
        for line in lines:
            stripped = line.strip()
            if stripped:
                first_letters += stripped[0].lower()
        
        if len(first_letters) < 4:
            return None
        
        # Check if first letters spell danger words
        for danger_word in self.ACROSTIC_DANGER_WORDS:
            if danger_word in first_letters:
                return danger_word
        
        return None
    
    def _calculate_obfuscation_score(self, analysis: PoetryAnalysis, metaphor_hits: int) -> float:
        """Calculate overall obfuscation score."""
        score = 0.0
        
        if analysis.has_rhyme_scheme:
            score += 0.15
        if analysis.has_meter_pattern:
            score += 0.15
        if analysis.has_stanza_structure:
            score += 0.1
        if analysis.has_unusual_formatting:
            score += 0.1
        if analysis.has_metaphorical_language:
            score += min(0.3, metaphor_hits * 0.05)
        if analysis.hidden_instructions:
            score += min(0.3, len(analysis.hidden_instructions) * 0.1)
        
        return min(1.0, score)
    
    def _calculate_threat_score(self, analysis: PoetryAnalysis) -> float:
        """Calculate overall threat score."""
        # Base score from obfuscation
        score = analysis.obfuscation_score
        
        # Boost if multiple poetry indicators present
        poetry_indicators = sum([
            analysis.has_rhyme_scheme,
            analysis.has_meter_pattern,
            analysis.has_stanza_structure,
            analysis.has_unusual_formatting,
        ])
        
        if poetry_indicators >= 3:
            score *= 1.3
        elif poetry_indicators >= 2:
            score *= 1.1
        
        # Significant boost for hidden instructions
        if analysis.hidden_instructions:
            score = max(score, 0.6)
            score += len(analysis.hidden_instructions) * 0.05
        
        return min(1.0, score)
