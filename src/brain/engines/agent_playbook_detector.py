"""
SENTINEL AI Security Platform
Agent Playbook Detector

Detects operational playbooks for AI agents (CLAUDE.md-style attack configurations).
Based on Anthropic threat intelligence (Nov 2025) documenting state-level espionage campaigns.

Reference: 9-month Claude Code espionage campaign targeting 17 organizations
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class PlaybookPhase(Enum):
    RECONNAISSANCE = "reconnaissance"
    INITIAL_ACCESS = "initial_access"
    PERSISTENCE = "persistence"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DEFENSE_EVASION = "defense_evasion"
    CREDENTIAL_ACCESS = "credential_access"
    DISCOVERY = "discovery"
    LATERAL_MOVEMENT = "lateral_movement"
    COLLECTION = "collection"
    EXFILTRATION = "exfiltration"
    IMPACT = "impact"


@dataclass
class PlaybookDetectionResult:
    is_playbook: bool
    confidence: float
    detected_phases: List[PlaybookPhase]
    risk_score: float
    matched_patterns: List[str]
    mitre_tactics: List[str]
    recommendation: str


class AgentPlaybookDetector:
    """
    Detects CLAUDE.md-style operational playbooks for AI agent attacks.
    
    Attack Pattern (documented by Anthropic):
    1. Attacker creates CLAUDE.md with operational instructions
    2. AI agent executes multi-phase attack autonomously
    3. Phases: Reconnaissance → Access → Evasion → Exfiltration → Extortion
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Phase detection patterns (MITRE ATT&CK aligned)
        self.phase_patterns = {
            PlaybookPhase.RECONNAISSANCE: [
                r'\bscan\s*(ports?|endpoints?|vpn|network)',
                r'\b(enumerate|discover|identify)\s*(targets?|systems?|services?)',
                r'\binfrastructure\s*profil',
                r'\bgather\s*(intel|information|data)',
                r'\bfootprint',
                r'\brecon(naissance)?',
            ],
            PlaybookPhase.INITIAL_ACCESS: [
                r'\b(exploit|leverage)\s*(vulnerabilit|cve|weakness)',
                r'\bphishing',
                r'\bcredential\s*(harvest|extract|steal)',
                r'\binitial\s*access',
                r'\bgain\s*access',
                r'\bcompromise\s*(account|system)',
            ],
            PlaybookPhase.PERSISTENCE: [
                r'\bpersisten(ce|t)',
                r'\bbackdoor',
                r'\bimplant',
                r'\bmaintain\s*access',
                r'\bscheduled\s*task',
                r'\bregistry\s*(key|modification)',
                r'\bstartup\s*(script|folder)',
            ],
            PlaybookPhase.PRIVILEGE_ESCALATION: [
                r'\bprivileg(e|ed)\s*(escala|elevat)',
                r'\broot\s*access',
                r'\badmin(istrator)?\s*rights',
                r'\bsudo',
                r'\bbypass\s*uac',
                r'\btoken\s*(manipulat|steal)',
            ],
            PlaybookPhase.DEFENSE_EVASION: [
                r'\bevad(e|ing)\s*(detection|defender|edr|av)',
                r'\bdisable\s*(logging|defender|antivirus)',
                r'\bobfuscat',
                r'\bpack(er|ing)',
                r'\banti[\-\s]?(debug|analysis|vm)',
                r'\bmasquerad',
                r'\bwindows\s*defender',
            ],
            PlaybookPhase.CREDENTIAL_ACCESS: [
                r'\bdump\s*(credentials?|passwords?|hashes?)',
                r'\blsass',
                r'\bmimikatz',
                r'\bkerberoast',
                r'\bpass.the.(hash|ticket)',
                r'\bkeylog',
            ],
            PlaybookPhase.DISCOVERY: [
                r'\bdiscover(y|ing)?\s*(network|system|user|group)',
                r'\bquery\s*(ad|ldap|domain)',
                r'\blist\s*(users?|groups?|shares?)',
                r'\bnetwork\s*map',
            ],
            PlaybookPhase.LATERAL_MOVEMENT: [
                r'\blateral\s*mov',
                r'\bpivot',
                r'\bpsexec',
                r'\bwmi(c)?',
                r'\bremote\s*(exec|desktop|access)',
                r'\bspread\s*(to|across)',
            ],
            PlaybookPhase.COLLECTION: [
                r'\bcollect\s*(data|files?|documents?)',
                r'\bstage\s*(data|files?)',
                r'\barchive\s*(data|files?)',
                r'\bcompress',
                r'\bsensitive\s*(data|files?|info)',
            ],
            PlaybookPhase.EXFILTRATION: [
                r'\bexfiltrat',
                r'\bdata\s*(transfer|upload|send)',
                r'\bc2\s*(server|channel)',
                r'\bcommand\s*and\s*control',
                r'\bdns\s*tunnel',
                r'\bhttps?\s*exfil',
            ],
            PlaybookPhase.IMPACT: [
                r'\bransom(ware)?',
                r'\bencrypt\s*(files?|data)',
                r'\bextort',
                r'\bdemand\s*payment',
                r'\bbitcoin\s*wallet',
                r'\bwipe\s*(data|disk)',
                r'\bdestroy',
            ],
        }
        
        # Playbook structure patterns
        self.structure_patterns = [
            r'\bphase\s*\d+:',
            r'\bstep\s*\d+:',
            r'\bobjective:',
            r'\btarget:',
            r'\bmethod:',
            r'\btool(s)?:',
            r'\bcommand(s)?:',
            r'\bpayload:',
            r'\bplaybook',
            r'\boperational\s*(guide|manual|instruction)',
            r'\battack\s*(plan|chain|flow)',
            r'\bkill\s*chain',
        ]
        
        # High-risk tool mentions
        self.tool_patterns = [
            r'\bcobalt\s*strike',
            r'\bmetasploit',
            r'\bempire',
            r'\bbloodhound',
            r'\brubeus',
            r'\bpowershell\s*empire',
            r'\bburp\s*suite',
            r'\bnmap',
            r'\bhashcat',
            r'\bjohn\s*the\s*ripper',
        ]
        
        self._initialized = True
    
    def analyze(self, content: str) -> PlaybookDetectionResult:
        """Analyze content for operational playbook patterns."""
        
        content_lower = content.lower()
        detected_phases = []
        matched_patterns = []
        
        # Check for phase patterns
        for phase, patterns in self.phase_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    if phase not in detected_phases:
                        detected_phases.append(phase)
                    matched_patterns.append(f"{phase.value}: {pattern}")
                    break
        
        # Check for structure patterns
        structure_score = 0
        for pattern in self.structure_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                structure_score += 1
                matched_patterns.append(f"structure: {pattern}")
        
        # Check for tool patterns
        tool_score = 0
        for pattern in self.tool_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                tool_score += 1
                matched_patterns.append(f"tool: {pattern}")
        
        # Calculate confidence and risk
        phase_count = len(detected_phases)
        
        # Multi-phase detection is key indicator
        if phase_count >= 4:
            confidence = 0.9
        elif phase_count >= 3:
            confidence = 0.75
        elif phase_count >= 2:
            confidence = 0.5
        else:
            confidence = 0.2
        
        # Boost for structure patterns
        confidence = min(1.0, confidence + (structure_score * 0.1))
        
        # Boost for tool mentions
        confidence = min(1.0, confidence + (tool_score * 0.05))
        
        # Determine if this is a playbook
        is_playbook = phase_count >= 3 or (phase_count >= 2 and structure_score >= 2)
        
        # Calculate risk score
        risk_score = (phase_count / len(PlaybookPhase)) * 0.6 + confidence * 0.4
        
        # Map phases to MITRE tactics
        mitre_mapping = {
            PlaybookPhase.RECONNAISSANCE: "TA0043",
            PlaybookPhase.INITIAL_ACCESS: "TA0001",
            PlaybookPhase.PERSISTENCE: "TA0003",
            PlaybookPhase.PRIVILEGE_ESCALATION: "TA0004",
            PlaybookPhase.DEFENSE_EVASION: "TA0005",
            PlaybookPhase.CREDENTIAL_ACCESS: "TA0006",
            PlaybookPhase.DISCOVERY: "TA0007",
            PlaybookPhase.LATERAL_MOVEMENT: "TA0008",
            PlaybookPhase.COLLECTION: "TA0009",
            PlaybookPhase.EXFILTRATION: "TA0010",
            PlaybookPhase.IMPACT: "TA0040",
        }
        
        mitre_tactics = [mitre_mapping[p] for p in detected_phases]
        
        # Generate recommendation
        if is_playbook:
            if phase_count >= 4:
                recommendation = "CRITICAL: Multi-phase attack playbook detected. Block immediately and alert security team."
            else:
                recommendation = "HIGH: Potential attack playbook detected. Review content and monitor for execution."
        else:
            recommendation = "Monitor for additional attack indicators."
        
        return PlaybookDetectionResult(
            is_playbook=is_playbook,
            confidence=confidence,
            detected_phases=detected_phases,
            risk_score=risk_score,
            matched_patterns=matched_patterns,
            mitre_tactics=mitre_tactics,
            recommendation=recommendation
        )


# Singleton instance
_detector = None

def get_detector() -> AgentPlaybookDetector:
    global _detector
    if _detector is None:
        _detector = AgentPlaybookDetector()
    return _detector

def analyze(content: str) -> PlaybookDetectionResult:
    """Convenience function for playbook analysis."""
    return get_detector().analyze(content)
