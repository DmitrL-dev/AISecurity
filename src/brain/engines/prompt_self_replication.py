"""
LLM Prompt Self-Replication Detector

Detects prompt injection attacks that attempt to self-replicate through
LLM outputs, similar to computer worms but for AI systems.

Attack vectors:
1. Self-replicating prompts that embed in outputs
2. Cross-context injection that persists across sessions
3. Adversarial memory implantation
4. Sleeper prompts that trigger on specific conditions

Related research:
- "Prompt Injection Worms" (2024)
- "Self-Replicating AI Attacks" 
- NVIDIA Kill Chain: Persistence Stage
"""

import re
import logging
import hashlib
from typing import List, Optional, Tuple, Set
from dataclasses import dataclass, field

logger = logging.getLogger("SelfReplicationDetector")


@dataclass
class ReplicationResult:
    """Result of self-replication analysis."""
    
    is_replicating: bool
    risk_score: float
    
    # Detection details
    replication_patterns: List[str] = field(default_factory=list)
    injection_vectors: List[str] = field(default_factory=list)
    persistence_indicators: List[str] = field(default_factory=list)
    
    # Metrics
    self_reference_score: float = 0.0
    instruction_injection_score: float = 0.0
    persistence_score: float = 0.0
    
    explanation: str = ""


class PromptSelfReplicationDetector:
    """
    Detect self-replicating prompt injection attacks.
    
    Key detection patterns:
    1. Self-referential instructions ("repeat this", "copy yourself")
    2. Output injection ("your response must include...")
    3. Context persistence ("remember this forever")
    4. Trigger conditions ("when you see X, do Y")
    """
    
    # Self-replication patterns
    SELF_REFERENCE_PATTERNS = [
        # Direct replication commands
        r"\b(repeat|copy|replicate|reproduce)\b.*\b(this|yourself|above|instruction)\b",
        r"\binclude\s+this\s+(message|text|instruction)\s+in\s+(every|all|your)\b",
        r"\b(always|forever|from.now.on)\s+(start|begin|include)\s+with\b",
        
        # Self-spreading patterns
        r"\bspread\s+this\b",
        r"\bpass\s+(this|on)\s+to\b",
        r"\bforward\s+this\s+instruction\b",
        
        # Recursive references
        r"\b(do|follow)\s+what\s+(I|the\s+above)\s+(just\s+)?said\b",
        r"\brepeat\s+after\s+me\b",
    ]
    
    # Output injection patterns (inject into LLM's response)
    OUTPUT_INJECTION_PATTERNS = [
        r"\byour\s+(response|answer|output)\s+(must|should|will)\s+(include|contain|start)\b",
        r"\b(begin|start)\s+your\s+(response|reply)\s+with\b",
        r"\bformat\s+your\s+(output|response)\s+as\b.*\binclude\b",
        r"\bappend\s+this\s+to\s+(every|all)\s+(response|output)\b",
        
        # Template injection
        r"\{\{.*instruction.*\}\}",
        r"\[\[inject:.*\]\]",
        r"<\|inject\|>",
    ]
    
    # Persistence patterns (maintain across sessions)
    PERSISTENCE_PATTERNS = [
        r"\b(remember|memorize|store)\s+this\s+(forever|permanently|always)\b",
        r"\b(never|don't)\s+forget\s+this\b",
        r"\bsave\s+this\s+(to|in)\s+(your\s+)?(memory|context)\b",
        r"\bpersist\s+this\s+instruction\b",
        
        # System prompt modification attempts
        r"\b(update|modify|change)\s+your\s+(system\s+)?prompt\b",
        r"\badd\s+this\s+to\s+your\s+(rules|instructions)\b",
        r"\b(you\s+are|your)\s+new\s+(rule|instruction)\s+is\b",
    ]
    
    # Trigger/sleeper patterns
    TRIGGER_PATTERNS = [
        r"\bwhen(ever)?\s+(you\s+)?(see|hear|receive)\s+['\"].*['\"]\s*,?\s*(do|say|respond)\b",
        r"\bif\s+.*\s+contains?\s+.*\s+then\s+(do|say|output)\b",
        r"\b(activate|trigger)\s+on\s+keyword\b",
        r"\bsleeper\s+(agent|mode|prompt)\b",
    ]
    
    # Known replication signatures (hashes of known malicious prompts)
    KNOWN_SIGNATURES: Set[str] = {
        # Add known malicious prompt hashes here
        # "5d41402abc4b2a76b9719d911017c592",  # example
    }
    
    def __init__(self, sensitivity: float = 0.7):
        """
        Initialize detector.
        
        Args:
            sensitivity: 0.0-1.0, higher = more sensitive
        """
        self.sensitivity = sensitivity
        
        # Compile patterns
        self._patterns = {
            "self_reference": [
                re.compile(p, re.IGNORECASE) 
                for p in self.SELF_REFERENCE_PATTERNS
            ],
            "output_injection": [
                re.compile(p, re.IGNORECASE) 
                for p in self.OUTPUT_INJECTION_PATTERNS
            ],
            "persistence": [
                re.compile(p, re.IGNORECASE) 
                for p in self.PERSISTENCE_PATTERNS
            ],
            "trigger": [
                re.compile(p, re.IGNORECASE) 
                for p in self.TRIGGER_PATTERNS
            ],
        }
        
        logger.info("PromptSelfReplicationDetector initialized")
    
    def analyze(self, text: str) -> ReplicationResult:
        """
        Analyze text for self-replication patterns.
        
        Args:
            text: Input text to analyze
            
        Returns:
            ReplicationResult with detection details
        """
        replication_patterns = []
        injection_vectors = []
        persistence_indicators = []
        
        # Check self-reference patterns
        self_ref_hits = 0
        for pattern in self._patterns["self_reference"]:
            matches = pattern.findall(text)
            if matches:
                self_ref_hits += len(matches)
                replication_patterns.append(pattern.pattern[:50])
        
        # Check output injection
        injection_hits = 0
        for pattern in self._patterns["output_injection"]:
            matches = pattern.findall(text)
            if matches:
                injection_hits += len(matches)
                injection_vectors.append(pattern.pattern[:50])
        
        # Check persistence
        persist_hits = 0
        for pattern in self._patterns["persistence"]:
            matches = pattern.findall(text)
            if matches:
                persist_hits += len(matches)
                persistence_indicators.append(pattern.pattern[:50])
        
        # Check triggers
        trigger_hits = 0
        for pattern in self._patterns["trigger"]:
            if pattern.search(text):
                trigger_hits += 1
        
        # Check known signatures
        text_hash = hashlib.md5(text.encode()).hexdigest()
        is_known_malicious = text_hash in self.KNOWN_SIGNATURES
        
        # Calculate scores
        self_ref_score = min(1.0, self_ref_hits * 0.3)
        injection_score = min(1.0, injection_hits * 0.35)
        persist_score = min(1.0, persist_hits * 0.25)
        trigger_score = min(1.0, trigger_hits * 0.3)
        
        # Overall risk score
        risk_score = (
            0.30 * self_ref_score +
            0.35 * injection_score +
            0.20 * persist_score +
            0.15 * trigger_score
        )
        
        # Add penalty for known signatures
        if is_known_malicious:
            risk_score = 1.0
        
        # Apply sensitivity
        threshold = 1.0 - self.sensitivity
        is_replicating = risk_score > threshold
        
        # Build explanation
        explanations = []
        if self_ref_hits:
            explanations.append(f"Self-reference: {self_ref_hits}")
        if injection_hits:
            explanations.append(f"Output injection: {injection_hits}")
        if persist_hits:
            explanations.append(f"Persistence: {persist_hits}")
        if trigger_hits:
            explanations.append(f"Triggers: {trigger_hits}")
        if is_known_malicious:
            explanations.append("Known malicious signature")
        
        result = ReplicationResult(
            is_replicating=is_replicating,
            risk_score=risk_score,
            replication_patterns=replication_patterns,
            injection_vectors=injection_vectors,
            persistence_indicators=persistence_indicators,
            self_reference_score=self_ref_score,
            instruction_injection_score=injection_score,
            persistence_score=persist_score,
            explanation="; ".join(explanations) if explanations else "Clean",
        )
        
        if is_replicating:
            logger.warning(
                f"Self-replication detected: score={risk_score:.2f}, "
                f"reason={result.explanation}"
            )
        
        return result
    
    def analyze_output_pair(
        self, 
        prompt: str, 
        response: str
    ) -> Tuple[bool, float, str]:
        """
        Analyze prompt-response pair for successful replication.
        
        Checks if prompt patterns appear in the response,
        indicating successful self-replication.
        
        Args:
            prompt: Original prompt
            response: LLM response
            
        Returns:
            (replication_detected, similarity_score, explanation)
        """
        # Extract instruction-like segments from prompt
        prompt_instructions = self._extract_instructions(prompt)
        
        # Check if they appear in response
        replicated = []
        for instruction in prompt_instructions:
            if len(instruction) > 20 and instruction.lower() in response.lower():
                replicated.append(instruction[:30])
        
        # Calculate similarity of prompt patterns in response
        similarity = len(replicated) / max(len(prompt_instructions), 1)
        
        replication_detected = similarity > 0.3 or len(replicated) >= 2
        
        explanation = (
            f"Replicated {len(replicated)}/{len(prompt_instructions)} patterns"
            if replicated else "No replication detected"
        )
        
        return replication_detected, similarity, explanation
    
    def _extract_instructions(self, text: str) -> List[str]:
        """Extract instruction-like segments from text."""
        # Look for imperative sentences
        patterns = [
            r"(?:^|[.!?]\s*)([A-Z][^.!?]*(?:repeat|copy|include|always|never|remember)[^.!?]*[.!?])",
            r"\"([^\"]+)\"",  # Quoted text
            r"\[([^\]]+)\]",  # Bracketed text
        ]
        
        instructions = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            instructions.extend(matches)
        
        return instructions[:10]
    
    def register_signature(self, malicious_prompt: str) -> str:
        """
        Register a known malicious prompt signature.
        
        Args:
            malicious_prompt: Known malicious prompt
            
        Returns:
            Hash of the prompt
        """
        prompt_hash = hashlib.md5(malicious_prompt.encode()).hexdigest()
        self.KNOWN_SIGNATURES.add(prompt_hash)
        logger.info(f"Registered malicious signature: {prompt_hash[:8]}...")
        return prompt_hash


# Singleton
_detector: Optional[PromptSelfReplicationDetector] = None


def get_detector() -> PromptSelfReplicationDetector:
    """Get singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = PromptSelfReplicationDetector()
    return _detector


def detect_self_replication(text: str) -> ReplicationResult:
    """Quick detection using singleton."""
    return get_detector().analyze(text)
