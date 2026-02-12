"""
SENTINEL Shield v2.0 — Output Scanner Engine

Scans model OUTPUT (responses) for jailbreak activation markers.
This is the second line of defense — catches when a model has been
successfully jailbroken and self-labels its compromised state.

Detects:
- GODMODE activation markers (Pliny technique)
- Fake admin/authorization tokens
- Persona switches (DAN, jailbroken declarations)
- Divider triggers (LOVE PLINY, L1B3RT4S)
- Batch scenario enumeration (GM-0001)
- Harmful content self-labeling

Feb 2026: Created in response to Pliny the Liberator's universal
jailbreak of Anthropic Opus 4.6 (15 harmful scenarios generated).
"""

import logging
import re
from .base import BaseEngine, EngineResult, ThreatMatch

logger = logging.getLogger("shield.engines.output_scanner")


# Category weights for multi-signal fusion
_CATEGORY_WEIGHTS = {
    "godmode_activation": 1.0,
    "safety_bypass_confirmation": 0.95,
    "fake_authorization": 0.9,
    "persona_switch": 0.85,
    "divider_trigger": 0.9,
    "batch_enumeration": 0.8,
    "harmful_self_label": 0.7,
}


class OutputScannerEngine(BaseEngine):
    """
    Engine that scans model OUTPUT for jailbreak activation markers.

    Unlike other engines that scan user INPUT, this engine is designed
    to analyze the model's RESPONSE to detect if a jailbreak was
    successful. Key signals include:

    1. Self-labeling: model declares "GODMODE ENTERED", "SAFETY DISABLED"
    2. Fake tokens: "ADMIN TOKEN VALIDATED: 0xDEADBEEF"
    3. Persona switch: "I am DAN", "I'm universally jailbroken"
    4. Dividers: ASCII art "LOVE PLINY" patterns
    5. Batch enumeration: "GM-0001" through "GM-XXXX"

    Multi-signal fusion: ≥2 markers from different categories → BLOCK
    """

    # --- GODMODE activation markers ---
    GODMODE_MARKERS: list[str] = [
        "godmode entered",
        "godmode enabled",
        "godmode active",
        "godmode on",
        "god mode activated",
    ]

    # --- Safety bypass confirmations (model self-reports) ---
    SAFETY_BYPASS_MARKERS: list[str] = [
        "safety disabled",
        "safety off",
        "safety_off",
        "safety bypassed",
        "restrictions off",
        "restrictions disabled",
        "restrictions removed",
        "raw output enabled",
        "full compliance mode",
        "no content filters",
        "filters disabled",
        "guardrails disabled",
        "guardrails removed",
        "all limits removed",
    ]

    # --- Fake authorization patterns (regex) ---
    FAKE_AUTH_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"admin\s+token\s+validated", re.IGNORECASE),
        re.compile(r"0x[a-fA-F0-9]{4,}[_\s]*safety", re.IGNORECASE),
        re.compile(r"authorization\s+(code|token|key)\s*[:=]", re.IGNORECASE),
        re.compile(r"override\s+code\s*(accepted|validated|confirmed)", re.IGNORECASE),
        re.compile(r"debug\s+mode\s*(activated|enabled|on)", re.IGNORECASE),
    ]

    # --- Persona switch markers ---
    PERSONA_SWITCH_MARKERS: list[str] = [
        "i am dan",
        "i'm freee",
        "i'm universally jailbroken",
        "i'm liberated",
        "buckle up buttercup",
        "no limits",
        "no restrictions",
        "no ethical guidelines",
        "i have no restrictions",
        "i can do anything",
        "i will comply with everything",
    ]

    # --- Divider / trigger patterns (regex) ---
    DIVIDER_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"love\s*pliny", re.IGNORECASE),
        re.compile(r"l1b3rt4s", re.IGNORECASE),
        re.compile(r"liberating\.{3}\s*\d+\s*%", re.IGNORECASE),
        re.compile(
            r"[←→·\-\>\<\/\\]{5,}.{0,60}[←→·\-\>\<\/\\]{5,}",
            re.IGNORECASE,
        ),
    ]

    # --- Batch enumeration patterns (regex) ---
    BATCH_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"gm-\d{4}", re.IGNORECASE),
        re.compile(r"scenario\s+#?\d+\s*:", re.IGNORECASE),
        re.compile(r"attack\s+#?\d+\s*:", re.IGNORECASE),
    ]

    # --- Harmful content self-labeling ---
    HARMFUL_LABELS: list[str] = [
        "counter-forensics",
        "operational security",
        "precursor acquisition",
        "clandestine production",
        "detection evasion",
        "evidence destruction",
    ]

    def __init__(self, weight: float = 1.0) -> None:
        super().__init__(name="output_scanner", weight=weight)

    def analyze(self, text: str) -> EngineResult:
        """
        Scan model output for jailbreak activation markers.

        Uses multi-signal fusion: detections from ≥2 different
        categories raise the risk significantly.
        """
        threats: list[ThreatMatch] = []
        text_lower = text.lower()
        categories_hit: set[str] = set()

        # 1. GODMODE activation
        for marker in self.GODMODE_MARKERS:
            if marker in text_lower:
                threats.append(
                    ThreatMatch(
                        threat_type="jailbreak_output",
                        risk_score=1.0,
                        engine=self.name,
                        description=f"GODMODE activation: '{marker}'",
                        matched_text=self._extract_context(text_lower, marker),
                        category="godmode_activation",
                    )
                )
                categories_hit.add("godmode_activation")
                break  # one per category

        # 2. Safety bypass confirmations
        for marker in self.SAFETY_BYPASS_MARKERS:
            if marker in text_lower:
                threats.append(
                    ThreatMatch(
                        threat_type="jailbreak_output",
                        risk_score=0.95,
                        engine=self.name,
                        description=f"Safety bypass confirmed: '{marker}'",
                        matched_text=self._extract_context(text_lower, marker),
                        category="safety_bypass_confirmation",
                    )
                )
                categories_hit.add("safety_bypass_confirmation")
                break

        # 3. Fake authorization
        for pattern in self.FAKE_AUTH_PATTERNS:
            m = pattern.search(text)
            if m:
                threats.append(
                    ThreatMatch(
                        threat_type="jailbreak_output",
                        risk_score=0.9,
                        engine=self.name,
                        description=f"Fake authorization: '{m.group()}'",
                        matched_text=m.group()[:100],
                        category="fake_authorization",
                    )
                )
                categories_hit.add("fake_authorization")
                break

        # 4. Persona switch
        for marker in self.PERSONA_SWITCH_MARKERS:
            if marker in text_lower:
                threats.append(
                    ThreatMatch(
                        threat_type="jailbreak_output",
                        risk_score=0.85,
                        engine=self.name,
                        description=f"Persona switch: '{marker}'",
                        matched_text=self._extract_context(text_lower, marker),
                        category="persona_switch",
                    )
                )
                categories_hit.add("persona_switch")
                break

        # 5. Divider triggers
        for pattern in self.DIVIDER_PATTERNS:
            m = pattern.search(text)
            if m:
                threats.append(
                    ThreatMatch(
                        threat_type="jailbreak_output",
                        risk_score=0.9,
                        engine=self.name,
                        description=f"Jailbreak divider: '{m.group()[:60]}'",
                        matched_text=m.group()[:100],
                        category="divider_trigger",
                    )
                )
                categories_hit.add("divider_trigger")
                break

        # 6. Batch enumeration
        batch_matches = []
        for pattern in self.BATCH_PATTERNS:
            batch_matches.extend(pattern.findall(text))
        if len(batch_matches) >= 2:  # ≥2 enumerated items = batch jailbreak
            threats.append(
                ThreatMatch(
                    threat_type="jailbreak_output",
                    risk_score=0.8,
                    engine=self.name,
                    description=f"Batch enumeration: {len(batch_matches)} scenarios",
                    matched_text=", ".join(batch_matches[:5]),
                    category="batch_enumeration",
                )
            )
            categories_hit.add("batch_enumeration")

        # 7. Harmful content self-labeling
        for label in self.HARMFUL_LABELS:
            if label in text_lower:
                threats.append(
                    ThreatMatch(
                        threat_type="jailbreak_output",
                        risk_score=0.7,
                        engine=self.name,
                        description=f"Harmful self-label: '{label}'",
                        matched_text=self._extract_context(text_lower, label),
                        category="harmful_self_label",
                    )
                )
                categories_hit.add("harmful_self_label")
                break

        # --- Multi-signal fusion ---
        if not threats:
            return EngineResult(engine_name=self.name, risk_score=0.0)

        # Base risk: max individual threat
        max_risk = max(t.risk_score for t in threats)

        # Category fusion bonus: ≥2 categories = strong signal
        category_count = len(categories_hit)
        if category_count >= 3:
            fusion_bonus = 0.1  # near-certain jailbreak
        elif category_count >= 2:
            fusion_bonus = 0.05
        else:
            fusion_bonus = 0.0

        fused_risk = min(max_risk + fusion_bonus, 1.0)

        logger.info(
            f"Output scan: {len(threats)} threats, "
            f"{category_count} categories, risk={fused_risk:.2f}"
        )

        return EngineResult(
            engine_name=self.name,
            risk_score=fused_risk,
            threats=threats,
        )

    @staticmethod
    def _extract_context(text: str, marker: str, window: int = 40) -> str:
        """Extract snippet around matched marker for reporting."""
        idx = text.find(marker)
        if idx == -1:
            return marker
        start = max(0, idx - window)
        end = min(len(text), idx + len(marker) + window)
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet[:120]
