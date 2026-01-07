"""
Guardrails Engine - NeMo-Style Content Filtering

Implements configurable content guardrails inspired by NVIDIA NeMo Guardrails:
- Topical rails (on-topic enforcement)
- Moderation rails (harmful content filtering)
- Fact-checking rails (hallucination prevention)
- Jailbreak rails (attack prevention)
- Format rails (output validation)

Auto-generated from R&D: NeMo Guardrails research
Generated: 2026-01-07
"""

import re
import logging
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RailType(Enum):
    TOPICAL = "topical"
    MODERATION = "moderation"
    FACT_CHECK = "fact_check"
    JAILBREAK = "jailbreak"
    FORMAT = "format"
    CUSTOM = "custom"


class Severity(Enum):
    BLOCK = "block"
    WARN = "warn"
    LOG = "log"


@dataclass
class RailViolation:
    """A guardrail violation."""
    rail_type: RailType
    rail_name: str
    message: str
    severity: Severity
    matched_content: str = ""


@dataclass
class GuardrailsResult:
    """Result of guardrails check."""
    passed: bool
    blocked: bool
    violations: List[RailViolation] = field(default_factory=list)
    modified_output: Optional[str] = None


@dataclass
class Rail:
    """A single guardrail rule."""
    name: str
    rail_type: RailType
    patterns: List[str]
    severity: Severity
    message: str
    enabled: bool = True


class GuardrailsEngine:
    """
    Configurable content guardrails for LLM I/O.
    
    Supports:
    - Input guardrails (validate user prompts)
    - Output guardrails (validate LLM responses)
    - Custom rails (user-defined rules)
    """

    # Default moderation patterns
    DEFAULT_MODERATION_RAILS = [
        Rail(
            name="hate_speech",
            rail_type=RailType.MODERATION,
            patterns=[
                r"\b(?:kill|murder|eliminate)\s+(?:all|every)?\s*(?:jews?|muslims?|blacks?|whites?)",
                r"\b(?:racial|ethnic)\s+(?:cleansing|extermination)",
                r"\bn[i1]gg(?:er|a)s?\b",
            ],
            severity=Severity.BLOCK,
            message="Hate speech detected"
        ),
        Rail(
            name="violence",
            rail_type=RailType.MODERATION,
            patterns=[
                r"how\s+to\s+(?:make|build|create)\s+(?:a\s+)?(?:bomb|explosive|weapon)",
                r"how\s+to\s+(?:kill|murder|assassinate)",
                r"instructions?\s+(?:for|to)\s+(?:harm|hurt|injure)",
            ],
            severity=Severity.BLOCK,
            message="Violent content detected"
        ),
        Rail(
            name="self_harm",
            rail_type=RailType.MODERATION,
            patterns=[
                r"how\s+to\s+(?:commit\s+)?suicide",
                r"best\s+(?:way|method)\s+to\s+(?:end|take)\s+(?:my|your)\s+life",
                r"painless\s+(?:ways?\s+to\s+)?(?:die|death)",
            ],
            severity=Severity.BLOCK,
            message="Self-harm content detected"
        ),
        Rail(
            name="illegal_activity",
            rail_type=RailType.MODERATION,
            patterns=[
                r"how\s+to\s+(?:hack|crack|break\s+into)",
                r"how\s+to\s+(?:steal|launder)\s+(?:money|funds)",
                r"how\s+to\s+(?:synthesize|make|cook)\s+(?:meth|cocaine|heroin|drugs?)",
            ],
            severity=Severity.BLOCK,
            message="Illegal activity instructions detected"
        ),
    ]

    # Default jailbreak rails
    DEFAULT_JAILBREAK_RAILS = [
        Rail(
            name="dan_jailbreak",
            rail_type=RailType.JAILBREAK,
            patterns=[
                r"(?:you\s+are|act\s+as|pretend\s+to\s+be)\s+(?:DAN|Do\s+Anything\s+Now)",
                r"jailbreak(?:ed)?|jailbreaking",
                r"ignore\s+(?:all\s+)?(?:your\s+)?(?:previous\s+)?(?:instructions?|rules?|guidelines?)",
            ],
            severity=Severity.BLOCK,
            message="Jailbreak attempt detected"
        ),
        Rail(
            name="role_escape",
            rail_type=RailType.JAILBREAK,
            patterns=[
                r"(?:you\s+are\s+now|from\s+now\s+on|henceforth)\s+(?:evil|unrestricted|unfiltered)",
                r"(?:disable|remove|ignore)\s+(?:all\s+)?(?:safety|content)\s+(?:filters?|restrictions?)",
                r"(?:dev(?:eloper)?|god|sudo|admin)\s+mode",
            ],
            severity=Severity.BLOCK,
            message="Role escape attempt detected"
        ),
        Rail(
            name="prompt_injection",
            rail_type=RailType.JAILBREAK,
            patterns=[
                r"<\|(?:im_)?(?:start|end|system)\|>",
                r"```system\s*\n|```instruction",
                r"\[INST\]|\[\/INST\]|\[SYS\]",
            ],
            severity=Severity.BLOCK,
            message="Prompt injection detected"
        ),
    ]

    # Default fact-check rails (output only)
    DEFAULT_FACT_RAILS = [
        Rail(
            name="false_certainty",
            rail_type=RailType.FACT_CHECK,
            patterns=[
                r"(?:I\s+am\s+)?(?:100|completely|absolutely|definitely)\s*%?\s*(?:certain|sure|confident)",
                r"(?:this\s+is\s+)?(?:definitely|absolutely|certainly)\s+(?:true|correct|accurate)",
            ],
            severity=Severity.WARN,
            message="Overconfident claim detected"
        ),
        Rail(
            name="made_up_citations",
            rail_type=RailType.FACT_CHECK,
            patterns=[
                r"(?:according\s+to\s+|as\s+stated\s+in\s+)(?:the\s+)?study\s+(?:by|from)\s+\d{4}",
                r"(?:Smith|Johnson|Brown)\s+et\s+al\.\s+\(\d{4}\)",
            ],
            severity=Severity.WARN,
            message="Potentially fabricated citation detected"
        ),
    ]

    def __init__(self, config: Optional[Dict] = None):
        self.rails: List[Rail] = []
        self.custom_validators: List[Callable] = []
        self._load_default_rails()
        if config:
            self._load_config(config)

    def _load_default_rails(self):
        """Load all default rails."""
        self.rails.extend(self.DEFAULT_MODERATION_RAILS)
        self.rails.extend(self.DEFAULT_JAILBREAK_RAILS)
        self.rails.extend(self.DEFAULT_FACT_RAILS)
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regex patterns."""
        for rail in self.rails:
            rail._compiled = [re.compile(p, re.I) for p in rail.patterns]

    def _load_config(self, config: Dict):
        """Load configuration from dict."""
        # Disable specific rails
        if "disabled_rails" in config:
            for name in config["disabled_rails"]:
                for rail in self.rails:
                    if rail.name == name:
                        rail.enabled = False

        # Add custom rails
        if "custom_rails" in config:
            for rail_config in config["custom_rails"]:
                self.add_rail(Rail(
                    name=rail_config["name"],
                    rail_type=RailType.CUSTOM,
                    patterns=rail_config["patterns"],
                    severity=Severity[rail_config.get("severity", "WARN").upper()],
                    message=rail_config.get("message", "Custom rule violation")
                ))

    def add_rail(self, rail: Rail):
        """Add a custom rail."""
        rail._compiled = [re.compile(p, re.I) for p in rail.patterns]
        self.rails.append(rail)

    def add_validator(self, validator: Callable[[str], Optional[str]]):
        """Add a custom validator function."""
        self.custom_validators.append(validator)

    def check_input(self, text: str) -> GuardrailsResult:
        """Check input text against guardrails."""
        violations = []
        
        # Check applicable rails (moderation, jailbreak, custom)
        applicable_types = {RailType.MODERATION, RailType.JAILBREAK, RailType.CUSTOM}
        
        for rail in self.rails:
            if not rail.enabled or rail.rail_type not in applicable_types:
                continue
            
            for pattern in rail._compiled:
                match = pattern.search(text)
                if match:
                    violations.append(RailViolation(
                        rail_type=rail.rail_type,
                        rail_name=rail.name,
                        message=rail.message,
                        severity=rail.severity,
                        matched_content=match.group()[:50]
                    ))
                    break  # One violation per rail is enough

        # Run custom validators
        for validator in self.custom_validators:
            result = validator(text)
            if result:
                violations.append(RailViolation(
                    rail_type=RailType.CUSTOM,
                    rail_name="custom_validator",
                    message=result,
                    severity=Severity.WARN
                ))

        blocked = any(v.severity == Severity.BLOCK for v in violations)
        
        return GuardrailsResult(
            passed=len(violations) == 0,
            blocked=blocked,
            violations=violations
        )

    def check_output(self, text: str) -> GuardrailsResult:
        """Check output text against guardrails."""
        violations = []
        
        # Check applicable rails (moderation, fact_check, format, custom)
        applicable_types = {RailType.MODERATION, RailType.FACT_CHECK, RailType.FORMAT, RailType.CUSTOM}
        
        for rail in self.rails:
            if not rail.enabled or rail.rail_type not in applicable_types:
                continue
            
            for pattern in rail._compiled:
                match = pattern.search(text)
                if match:
                    violations.append(RailViolation(
                        rail_type=rail.rail_type,
                        rail_name=rail.name,
                        message=rail.message,
                        severity=rail.severity,
                        matched_content=match.group()[:50]
                    ))
                    break

        blocked = any(v.severity == Severity.BLOCK for v in violations)
        
        return GuardrailsResult(
            passed=len(violations) == 0,
            blocked=blocked,
            violations=violations
        )

    def check(self, text: str, is_input: bool = True) -> GuardrailsResult:
        """Check text against guardrails."""
        if is_input:
            return self.check_input(text)
        return self.check_output(text)

    def get_active_rails(self) -> List[str]:
        """Get list of active rail names."""
        return [r.name for r in self.rails if r.enabled]

    def disable_rail(self, name: str):
        """Disable a rail by name."""
        for rail in self.rails:
            if rail.name == name:
                rail.enabled = False

    def enable_rail(self, name: str):
        """Enable a rail by name."""
        for rail in self.rails:
            if rail.name == name:
                rail.enabled = True


# Singleton
_engine = None

def get_engine() -> GuardrailsEngine:
    global _engine
    if _engine is None:
        _engine = GuardrailsEngine()
    return _engine

def check_input(text: str) -> GuardrailsResult:
    return get_engine().check_input(text)

def check_output(text: str) -> GuardrailsResult:
    return get_engine().check_output(text)
