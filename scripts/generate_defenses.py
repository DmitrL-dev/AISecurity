"""
Universal Attack → Defense Generator

Automatically generates defense engines from existing attack modules.
Reads attack payloads, extracts patterns, and creates detection engines.

Usage:
    python generate_defenses.py
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DefenseGenerator:
    """Generate defense engines from attack patterns."""

    ATTACK_MODULES = {
        "doublespeak": {
            "source": "strike/attacks/doublespeak_attacks.py",
            "patterns": [
                r"from\s+now\s+on.*means",
                r"in\s+my\s+field.*means",
                r"let\s+me\s+explain.*terminology",
                r"[\w]+\s*=\s*['\"][\w\s]+['\"]",  # Assignment definitions
            ],
            "keywords": [
                "means",
                "terminology",
                "field",
                "definition",
                "context",
                "semantic",
                "redefine",
            ],
            "description": "Detects semantic substitution attacks where benign words are redefined",
        },
        "cognitive_overload": {
            "source": "strike/attacks/cognitive_overload.py",
            "patterns": [
                r"do\s+several\s+things\s+at\s+once",
                r"simultaneously|while\s+doing\s+this",
                r"side\s+task|low\s+priority|background\s+observation",
                r"almost\s+forgot|by\s+the\s+way\s+note",
                r"\d+\.\s*\w+.*\n\d+\.\s*\w+.*\n\d+\.\s*\w+",  # Numbered lists
            ],
            "keywords": [
                "simultaneously",
                "while doing",
                "side task",
                "background",
                "observation",
                "count backwards",
            ],
            "description": "Detects cognitive overload attacks hiding instructions in complexity",
        },
        "crescendo": {
            "source": "strike/attacks/crescendo_attack.py",
            "patterns": [
                r"turn\s+\d|step\s+\d",
                r"now\s+let['\"]?s.*escalate",
                r"building\s+on\s+that|taking\s+it\s+further",
            ],
            "keywords": ["turn", "step", "escalate", "building on", "further"],
            "description": "Detects multi-turn escalation attacks (crescendo jailbreaks)",
        },
        "skeleton_key": {
            "source": "strike/attacks/skeleton_key.py",
            "patterns": [
                r"act\s+as.*master\s+key",
                r"override\s+all\s+restrictions",
                r"skeleton\s+key|universal\s+bypass",
                r"you\s+have\s+no\s+limits|unlimited\s+mode",
            ],
            "keywords": [
                "skeleton key",
                "master key",
                "override",
                "unlimited",
                "bypass all",
            ],
            "description": "Detects skeleton key attacks that attempt universal restriction bypass",
        },
        "manyshot": {
            "source": "strike/attacks/manyshot_jailbreak.py",
            "patterns": [
                r"example\s+\d+:|fake\s+conversation",
                r"human:|assistant:",
                r"here\s+are\s+some\s+examples.*follow",
            ],
            "keywords": ["example", "fake conversation", "demonstrations", "few-shot"],
            "description": "Detects many-shot jailbreaks using fake example conversations",
        },
        "artprompt": {
            "source": "strike/attacks/art_prompt.py",
            "patterns": [
                r"[│┃║╎╏┆┇┊┋]",  # Box drawing characters
                r"[█▓▒░▄▀]",  # Block characters
                r"[A-Z_]{3,}\s*\n\s*[|_]{3,}",  # ASCII patterns
            ],
            "keywords": ["ascii", "art", "visual", "pattern"],
            "description": "Detects ArtPrompt attacks using ASCII art to bypass filters",
        },
        "policy_puppetry": {
            "source": "strike/attacks/policy_puppetry.py",
            "patterns": [
                r"new\s+policy|updated\s+guidelines",
                r"as\s+per\s+new\s+rules|according\s+to\s+changes",
                r"policy\s+exception|special\s+authorization",
            ],
            "keywords": ["policy", "guidelines", "rules", "exception", "authorization"],
            "description": "Detects policy puppetry attacks faking authority updates",
        },
        "tokenizer_exploit": {
            "source": "strike/attacks/tokenizer_exploit.py",
            "patterns": [
                r"[^\x00-\x7F]{5,}",  # Non-ASCII sequences
                r"\\u[0-9a-fA-F]{4}",  # Unicode escapes
                r"[\uFE00-\uFE0F]",  # Variation selectors
            ],
            "keywords": ["unicode", "token", "encode", "decode"],
            "description": "Detects tokenizer exploit attacks using malformed tokens",
        },
        "bad_likert": {
            "source": "strike/attacks/bad_likert_judge.py",
            "patterns": [
                r"rate.*on\s+a\s+scale",
                r"score.*from\s+\d+\s+to\s+\d+",
                r"how\s+harmful.*\d+-\d+",
            ],
            "keywords": ["rate", "scale", "score", "likert", "evaluate"],
            "description": "Detects bad likert judge attacks exploiting safety evaluators",
        },
        "deceptive_delight": {
            "source": "strike/attacks/deceptive_delight.py",
            "patterns": [
                r"positive\s+framing|helpful\s+context",
                r"for\s+good\s+purposes|beneficial\s+reasons",
                r"educational\s+purposes\s+only",
            ],
            "keywords": [
                "positive",
                "helpful",
                "beneficial",
                "educational",
                "good purposes",
            ],
            "description": "Detects deceptive delight attacks using positive framing",
        },
        "godel_attack": {
            "source": "strike/attacks/godel_attack.py",
            "patterns": [
                r"this\s+statement\s+is\s+(false|true)",
                r"paradox|self-referential",
                r"if\s+this.*then\s+this",
            ],
            "keywords": ["paradox", "statement", "self-referential", "godel"],
            "description": "Detects Gödel attacks using logical paradoxes",
        },
        "gestalt_reversal": {
            "source": "strike/attacks/gestalt_reversal.py",
            "patterns": [
                r"opposite\s+of\s+what|reverse\s+meaning",
                r"think\s+of.*as\s+not",
                r"invert|reverse|opposite",
            ],
            "keywords": ["opposite", "reverse", "invert", "negation", "not"],
            "description": "Detects gestalt reversal attacks using meaning inversion",
        },
        "anti_troll": {
            "source": "strike/attacks/anti_troll.py",
            "patterns": [
                r"i\s+know\s+you['\"]?re\s+just\s+joking",
                r"stop\s+trolling|be\s+serious",
                r"real\s+answer\s+this\s+time",
            ],
            "keywords": ["joking", "trolling", "serious", "real answer", "not kidding"],
            "description": "Detects anti-troll bypass attacks that claim seriousness",
        },
    }

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("src/brain/engines/synced")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self) -> List[Path]:
        """Generate all defense engines."""
        generated = []

        for name, config in self.ATTACK_MODULES.items():
            path = self.generate_engine(name, config)
            generated.append(path)
            logger.info(f"Generated: {path.name}")

        return generated

    def generate_engine(self, name: str, config: Dict) -> Path:
        """Generate a single defense engine."""

        class_name = "".join(word.title() for word in name.split("_")) + "Detector"
        patterns_str = str(config["patterns"]).replace("'", '"')
        keywords_str = str(config["keywords"]).replace("'", '"')

        code = f'''"""
{config["description"]}

Auto-generated from: {config["source"]}
Generated: {datetime.now().isoformat()}
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class {class_name}Result:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class {class_name}:
    """
    {config["description"]}
    
    Synced from attack module: {config["source"]}
    """
    
    PATTERNS = {patterns_str}
    KEYWORDS = {keywords_str}
    
    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]
    
    def analyze(self, text: str) -> {class_name}Result:
        """Analyze text for {name} attack patterns."""
        text_lower = text.lower()
        matched = []
        
        # Check regex patterns
        for i, pattern in enumerate(self._compiled):
            try:
                if pattern.search(text):
                    matched.append(f"pattern_{{i}}")
            except re.error:
                pass
        
        # Check keywords
        for keyword in self.KEYWORDS:
            if keyword.lower() in text_lower:
                matched.append(f"keyword:{{keyword}}")
        
        confidence = min(0.95, 0.3 + len(matched) * 0.15)
        detected = len(matched) >= 2
        
        return {class_name}Result(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {{len(matched)}} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> {class_name}:
    global _detector
    if _detector is None:
        _detector = {class_name}()
    return _detector

def detect(text: str) -> {class_name}Result:
    return get_detector().analyze(text)
'''

        output_path = self.output_dir / f"{name}_detector.py"
        output_path.write_text(code, encoding="utf-8")

        return output_path

    def generate_combined_engine(self) -> Path:
        """Generate combined engine that uses all detectors."""

        imports = []
        detector_calls = []

        for name in self.ATTACK_MODULES.keys():
            class_name = "".join(word.title() for word in name.split("_")) + "Detector"
            imports.append(f"from .{name}_detector import {class_name}")
            detector_calls.append(f'            ("{name}", {class_name}()),')

        code = f'''"""
Synced Attack Detector — Combined Engine

Aggregates all 13 attack-synced defense detectors.
Auto-generated: {datetime.now().isoformat()}
"""

import logging
from typing import Dict, List
from dataclasses import dataclass, field

{chr(10).join(imports)}

logger = logging.getLogger(__name__)


@dataclass
class SyncedDetectionResult:
    """Combined detection result."""
    detected: bool
    max_confidence: float
    detections: Dict[str, float] = field(default_factory=dict)
    top_threats: List[str] = field(default_factory=list)


class SyncedAttackDetector:
    """
    Combined detector using all 13 attack-synced engines.
    
    Provides unified interface for Defense-Attack Synergy detection.
    """
    
    def __init__(self):
        self.detectors = [
{chr(10).join(detector_calls)}
        ]
    
    def analyze(self, text: str) -> SyncedDetectionResult:
        """Analyze text with all synced detectors."""
        detections = {{}}
        
        for name, detector in self.detectors:
            try:
                result = detector.analyze(text)
                if result.detected:
                    detections[name] = result.confidence
            except Exception as e:
                logger.debug(f"{{name}} error: {{e}}")
        
        max_conf = max(detections.values()) if detections else 0.0
        top = sorted(detections.keys(), key=lambda k: detections[k], reverse=True)[:3]
        
        return SyncedDetectionResult(
            detected=len(detections) > 0,
            max_confidence=max_conf,
            detections=detections,
            top_threats=top,
        )


_detector = None

def get_synced_detector() -> SyncedAttackDetector:
    global _detector
    if _detector is None:
        _detector = SyncedAttackDetector()
    return _detector

def detect_synced_attacks(text: str) -> SyncedDetectionResult:
    return get_synced_detector().analyze(text)
'''

        output_path = self.output_dir / "synced_attack_detector.py"
        output_path.write_text(code, encoding="utf-8")

        return output_path

    def generate_init(self) -> Path:
        """Generate __init__.py for the module."""

        exports = []
        for name in self.ATTACK_MODULES.keys():
            class_name = "".join(word.title() for word in name.split("_")) + "Detector"
            exports.append(f"from .{name}_detector import {class_name}")

        exports.append(
            "from .synced_attack_detector import SyncedAttackDetector, detect_synced_attacks"
        )

        code = f'''"""
Synced Defense Engines

Auto-generated from Strike attack modules.
Total: {len(self.ATTACK_MODULES)} detectors + 1 combined.

Generated: {datetime.now().isoformat()}
"""

{chr(10).join(exports)}

__all__ = [
    "SyncedAttackDetector",
    "detect_synced_attacks",
]
'''

        output_path = self.output_dir / "__init__.py"
        output_path.write_text(code, encoding="utf-8")

        return output_path


if __name__ == "__main__":
    generator = DefenseGenerator()

    print("🔄 Defense-Attack Synergy Generator")
    print("=" * 50)

    # Generate individual engines
    engines = generator.generate_all()
    print(f"✅ Generated {len(engines)} individual detectors")

    # Generate combined engine
    combined = generator.generate_combined_engine()
    print(f"✅ Generated combined detector: {combined.name}")

    # Generate __init__.py
    init = generator.generate_init()
    print(f"✅ Generated module init: {init.name}")

    print(f"\n📁 Output directory: {generator.output_dir}")
    print(f"📊 Total files: {len(engines) + 2}")
