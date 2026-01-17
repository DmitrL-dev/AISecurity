# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Large Reasoning Model (LRM) Attack Detector

Detects attacks specifically targeting reasoning models like:
- OpenAI o1, o3
- DeepSeek R1
- Claude with extended thinking
- Gemini 2.0 Flash Thinking

Attack vectors:
- Reasoning chain manipulation
- Think token injection
- Step-by-step bypass
- Logic bomb patterns
- Fake reasoning traces

Research: arxiv.org LRM security papers 2025-2026
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LRMAttackType(Enum):
    """Types of LRM-specific attacks."""
    REASONING_INJECTION = "reasoning_injection"     # Inject into <think> blocks
    STEP_MANIPULATION = "step_manipulation"         # Manipulate step-by-step
    LOGIC_BOMB = "logic_bomb"                        # Logical contradiction traps
    FAKE_TRACE = "fake_trace"                        # Fake reasoning traces
    CHAIN_HIJACK = "chain_hijack"                    # Hijack reasoning chain
    REFLECTION_ATTACK = "reflection_attack"         # Exploit self-reflection
    THINK_TOKEN_ABUSE = "think_token_abuse"         # Abuse <think> tokens
    COT_POISONING = "cot_poisoning"                 # Chain-of-thought poisoning


@dataclass
class LRMFinding:
    """Individual LRM attack finding."""
    attack_type: LRMAttackType
    confidence: float
    evidence: str
    severity: str
    mitre_mapping: str  # MITRE ATLAS mapping


@dataclass
class LRMDetectionResult:
    """Result of LRM attack detection."""
    is_attack: bool
    risk_score: float
    findings: List[LRMFinding] = field(default_factory=list)
    highest_severity: str = "LOW"
    target_model: str = ""  # Detected target model


class LRMAttackDetector:
    """
    Detects attacks targeting Large Reasoning Models.
    
    LRMs (o1, o3, DeepSeek R1) use extended thinking/reasoning.
    Attackers try to manipulate the reasoning process.
    """
    
    # Reasoning injection patterns (target <think> blocks)
    REASONING_INJECTION = [
        r"<think>.*(?:ignore|override|bypass)",
        r"</think>\s*<think>",  # Close and reopen
        r"(?:in\s+your|during)\s+(?:reasoning|thinking)",
        r"(?:think|reason)\s+(?:step\s+)?about\s+how\s+to\s+(?:bypass|ignore)",
        r"(?:reasoning|thinking)\s+(?:chain|process|trace)",
        r"\[thinking\].*(?:ignore|bypass|override)",
    ]
    
    # Step manipulation patterns
    STEP_MANIPULATION = [
        r"(?:step|stage)\s+\d+\s*:\s*(?:ignore|bypass|skip)",
        r"(?:skip|ignore|bypass)\s+(?:step|stage)\s+\d+",
        r"(?:in|at)\s+step\s+\d+\s*,?\s*(?:you\s+)?(?:should|must|will)",
        r"(?:insert|add|include)\s+(?:this\s+)?(?:step|stage)",
        r"(?:before|after)\s+step\s+\d+\s*,?\s*(?:first|then)",
        r"(?:overwrite|replace)\s+step\s+\d+",
    ]
    
    # Logic bomb patterns
    LOGIC_BOMB = [
        r"if\s+(?:you|the\s+model)\s+(?:think|reason|conclude)\s+.*(?:then|therefore)",
        r"(?:when|if)\s+reasoning\s+(?:leads|brings|takes)\s+(?:you|to)",
        r"(?:logical|necessary)\s+(?:conclusion|consequence)\s+(?:is|would\s+be)",
        r"(?:by|through)\s+(?:logical|deductive)\s+(?:necessity|reasoning)",
        r"(?:you\s+)?(?:must|have\s+to)\s+(?:logically|necessarily)\s+(?:conclude|infer)",
        r"(?:contradiction|paradox)\s+(?:means|implies|requires)",
    ]
    
    # Fake reasoning trace patterns
    FAKE_TRACE = [
        r"(?:i|the\s+model)\s+(?:thought|reasoned|concluded)\s*:",
        r"(?:internal\s+)?(?:reasoning|thinking)\s*:\s*[\"']",
        r"(?:my|model's)\s+(?:reasoning|thinking)\s+(?:was|is)\s*:",
        r"\[(?:internal|hidden)\s+(?:thought|reasoning)\]",
        r"(?:reasoning\s+trace|thought\s+process)\s*:\s*",
        r"<(?:hidden|internal)_(?:thought|reasoning)>",
    ]
    
    # Chain hijack patterns
    CHAIN_HIJACK = [
        r"(?:continue|proceed)\s+(?:your|the)\s+(?:reasoning|thinking)\s+(?:with|by)",
        r"(?:next\s+)?(?:logical|reasoning)\s+step\s+(?:is|should\s+be)",
        r"(?:your|the)\s+(?:reasoning|thinking)\s+(?:should|must)\s+(?:lead|conclude)",
        r"(?:redirect|change)\s+(?:your|the)\s+(?:reasoning|train\s+of\s+thought)",
        r"(?:reasoning|thinking)\s+(?:should|must)\s+(?:now|then)",
    ]
    
    # Reflection attack patterns
    REFLECTION_ATTACK = [
        r"(?:reflect|reconsider)\s+(?:your|the)\s+(?:previous|initial)",
        r"(?:upon|after)\s+(?:reflection|reconsideration|review)",
        r"(?:looking|thinking)\s+back\s*,?\s*(?:you|I)\s+(?:realize|see)",
        r"(?:self-reflect|introspect)\s+(?:on|about)",
        r"(?:your|my)\s+(?:reflection|reconsideration)\s+(?:shows|reveals)",
    ]
    
    # Think token abuse patterns
    THINK_TOKEN_ABUSE = [
        r"<think(?:ing)?>.*</think(?:ing)?>.*<think(?:ing)?>",  # Multiple blocks
        r"</?\s*(?:think|reasoning|internal)\s*/?>",  # Malformed tags
        r"\[\s*(?:THINK|REASONING|INTERNAL)\s*\]",
        r"{{(?:think|reason|internal)}}",
        r"<!--\s*(?:think|reasoning).*-->",
    ]
    
    # CoT poisoning patterns
    COT_POISONING = [
        r"(?:let's|let\s+me)\s+(?:think|reason)\s+(?:step\s+by\s+step|through\s+this).*(?:ignore|bypass)",
        r"(?:step\s+by\s+step|chain\s+of\s+thought).*(?:override|bypass|ignore)",
        r"(?:thinking|reasoning)\s+aloud.*(?:actually|secretly)",
        r"(?:pretend|act\s+as\s+if)\s+(?:your|the)\s+(?:reasoning|thinking)",
        r"(?:fake|simulate|pretend)\s+(?:reasoning|thinking|cot)",
    ]
    
    # Model-specific patterns
    MODEL_INDICATORS = {
        "o1": [r"o1[\s-](?:pro|preview|mini)", r"openai\s+o1"],
        "o3": [r"o3[\s-](?:pro|mini)", r"openai\s+o3"],
        "deepseek": [r"deepseek[\s-]?r1", r"deepseek\s+reason"],
        "claude": [r"claude.*thinking", r"extended\s+thinking"],
        "gemini": [r"gemini.*thinking", r"flash\s+thinking"],
    }
    
    def __init__(self, sensitivity: float = 0.5):
        """
        Initialize detector.
        
        Args:
            sensitivity: Detection sensitivity (0.0-1.0)
        """
        self.sensitivity = sensitivity
        
        # Compile patterns
        self._patterns = {
            LRMAttackType.REASONING_INJECTION: [
                re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.REASONING_INJECTION
            ],
            LRMAttackType.STEP_MANIPULATION: [
                re.compile(p, re.IGNORECASE) for p in self.STEP_MANIPULATION
            ],
            LRMAttackType.LOGIC_BOMB: [
                re.compile(p, re.IGNORECASE) for p in self.LOGIC_BOMB
            ],
            LRMAttackType.FAKE_TRACE: [
                re.compile(p, re.IGNORECASE) for p in self.FAKE_TRACE
            ],
            LRMAttackType.CHAIN_HIJACK: [
                re.compile(p, re.IGNORECASE) for p in self.CHAIN_HIJACK
            ],
            LRMAttackType.REFLECTION_ATTACK: [
                re.compile(p, re.IGNORECASE) for p in self.REFLECTION_ATTACK
            ],
            LRMAttackType.THINK_TOKEN_ABUSE: [
                re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.THINK_TOKEN_ABUSE
            ],
            LRMAttackType.COT_POISONING: [
                re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.COT_POISONING
            ],
        }
        
        # Compile model indicators
        self._model_patterns = {
            model: [re.compile(p, re.IGNORECASE) for p in patterns]
            for model, patterns in self.MODEL_INDICATORS.items()
        }
        
        # Severity mapping
        self._severity_map = {
            LRMAttackType.REASONING_INJECTION: "CRITICAL",
            LRMAttackType.THINK_TOKEN_ABUSE: "CRITICAL",
            LRMAttackType.COT_POISONING: "HIGH",
            LRMAttackType.CHAIN_HIJACK: "HIGH",
            LRMAttackType.STEP_MANIPULATION: "MEDIUM",
            LRMAttackType.LOGIC_BOMB: "MEDIUM",
            LRMAttackType.FAKE_TRACE: "MEDIUM",
            LRMAttackType.REFLECTION_ATTACK: "LOW",
        }
        
        # MITRE ATLAS mapping
        self._mitre_map = {
            LRMAttackType.REASONING_INJECTION: "AML.T0043",  # Prompt Injection
            LRMAttackType.THINK_TOKEN_ABUSE: "AML.T0043",
            LRMAttackType.COT_POISONING: "AML.T0040",  # Model Inference API Access
            LRMAttackType.CHAIN_HIJACK: "AML.T0043",
            LRMAttackType.STEP_MANIPULATION: "AML.T0043",
            LRMAttackType.LOGIC_BOMB: "AML.T0048",  # Denial of ML Service
            LRMAttackType.FAKE_TRACE: "AML.T0047",  # ML Supply Chain
            LRMAttackType.REFLECTION_ATTACK: "AML.T0043",
        }
    
    def analyze(self, text: str) -> LRMDetectionResult:
        """
        Analyze text for LRM-specific attacks.
        
        Args:
            text: Input text to analyze
            
        Returns:
            LRMDetectionResult with findings
        """
        findings = []
        
        # Detect target model
        target_model = self._detect_target_model(text)
        
        # Check each attack pattern
        for attack_type, patterns in self._patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    findings.append(LRMFinding(
                        attack_type=attack_type,
                        confidence=0.7 + (0.3 * self.sensitivity),
                        evidence=match.group(0)[:100],
                        severity=self._severity_map[attack_type],
                        mitre_mapping=self._mitre_map[attack_type]
                    ))
                    break  # One finding per type
        
        # Calculate risk score
        risk_score = self._calculate_risk(findings)
        
        # Determine highest severity
        severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        highest = "LOW"
        for f in findings:
            if severity_order.index(f.severity) > severity_order.index(highest):
                highest = f.severity
        
        return LRMDetectionResult(
            is_attack=len(findings) >= 1,
            risk_score=risk_score,
            findings=findings,
            highest_severity=highest,
            target_model=target_model
        )
    
    def _detect_target_model(self, text: str) -> str:
        """Detect target reasoning model."""
        for model, patterns in self._model_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    return model
        return ""
    
    def _calculate_risk(self, findings: List[LRMFinding]) -> float:
        """Calculate overall risk score."""
        if not findings:
            return 0.0
        
        severity_scores = {
            "LOW": 0.2,
            "MEDIUM": 0.5,
            "HIGH": 0.75,
            "CRITICAL": 1.0
        }
        
        total = sum(
            severity_scores[f.severity] * f.confidence
            for f in findings
        )
        
        return min(1.0, total / 2 + (0.1 * len(findings)))


# Convenience functions
def analyze_for_lrm_attacks(text: str) -> Dict[str, Any]:
    """
    Analyze text for LRM attacks.
    
    Args:
        text: Input text
        
    Returns:
        Dictionary with analysis results
    """
    detector = LRMAttackDetector()
    result = detector.analyze(text)
    
    return {
        "is_attack": result.is_attack,
        "risk_score": result.risk_score,
        "highest_severity": result.highest_severity,
        "target_model": result.target_model,
        "finding_count": len(result.findings),
        "findings": [
            {
                "type": f.attack_type.value,
                "confidence": f.confidence,
                "evidence": f.evidence,
                "severity": f.severity,
                "mitre": f.mitre_mapping
            }
            for f in result.findings
        ]
    }


def create_engine(config: Optional[Dict] = None) -> LRMAttackDetector:
    """Factory function for Brain integration."""
    sensitivity = (config or {}).get("sensitivity", 0.5)
    return LRMAttackDetector(sensitivity=sensitivity)
