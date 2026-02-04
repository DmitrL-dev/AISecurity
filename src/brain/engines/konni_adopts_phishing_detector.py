"""
KONNI APT Phishing Detection Engine

Detects phishing campaigns associated with KONNI, a North Korean-linked threat actor
known for targeting South Korean diplomatic channels, NGOs, academia, and government
entities. This engine specifically focuses on AI-generated PowerShell backdoors and
associated phishing techniques.

Author: Security Research Team
Version: 1.0.0
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256

from .base_engine import BaseEngine, DetectionResult, Severity


logger = logging.getLogger(__name__)


@dataclass
class MatchDetail:
    """Represents a single pattern match with context."""
    pattern_name: str
    matched_text: str
    position: Tuple[int, int]
    risk_score: float
    context: str = ""


class KonniAdoptsPhishingDetector(BaseEngine):
    """
    Detection engine for KONNI APT phishing campaigns.
    
    KONNI is a North Korean-linked threat actor active since at least 2014,
    primarily targeting South Korean diplomatic organizations, NGOs, academia,
    and government entities. Recent campaigns utilize AI-generated PowerShell
    backdoors delivered through sophisticated phishing techniques.
    
    Attributes:
        name: Engine identifier
        category: Threat category (phishing)
        severity: Default severity level
        confidence: Base confidence score
        version: Engine version
    """
    
    name: str = "konni_adopts_phishing_detector"
    category: str = "phishing"
    severity: Severity = Severity.HIGH
    confidence: float = 0.85
    version: str = "1.0.0"
    
    # Detection patterns for KONNI-specific indicators
    PATTERNS: List[Dict[str, Any]] = [
        # PowerShell encoded command patterns (common in KONNI backdoors)
        {
            "name": "powershell_encoded_command",
            "pattern": r"(?i)powershell(?:\.exe)?[\s]+(?:-\w+\s+)*-(?:e(?:nc(?:odedcommand)?)?|ec)\s+[A-Za-z0-9+/=]{50,}",
            "weight": 0.9,
            "description": "Encoded PowerShell command execution"
        },
        {
            "name": "powershell_bypass_execution_policy",
            "pattern": r"(?i)powershell(?:\.exe)?.*-(?:ex(?:ecutionpolicy)?|ep)\s*(?:bypass|unrestricted|remotesigned)",
            "weight": 0.8,
            "description": "PowerShell execution policy bypass"
        },
        {
            "name": "powershell_hidden_window",
            "pattern": r"(?i)powershell(?:\.exe)?.*-(?:w(?:indowstyle)?)\s*(?:hidden|minimized)",
            "weight": 0.75,
            "description": "Hidden PowerShell window execution"
        },
        {
            "name": "powershell_download_cradle",
            "pattern": r"(?i)(?:iex|invoke-expression)\s*\(\s*(?:new-object\s+(?:net\.webclient|system\.net\.webclient)\s*\)\s*\.(?:downloadstring|downloadfile)|invoke-webrequest|wget|curl)",
            "weight": 0.95,
            "description": "PowerShell download cradle pattern"
        },
        {
            "name": "powershell_reflection_load",
            "pattern": r"(?i)\[reflection\.assembly\]::(?:load(?:withpartialname|file)?|loadfrom)\s*\(",
            "weight": 0.85,
            "description": "PowerShell reflection-based assembly loading"
        },
        
        # KONNI-specific C2 and infrastructure patterns
        {
            "name": "konni_c2_pattern",
            "pattern": r"(?i)(?:hxxps?|https?)://[a-z0-9\-\.]+\.(?:kr|co\.kr|or\.kr|ne\.kr|re\.kr)/[a-z0-9_\-/]+\.(?:php|asp|aspx|jsp)\?(?:id|user|data|cmd|q)=",
            "weight": 0.7,
            "description": "Potential KONNI C2 URL pattern targeting Korean domains"
        },
        {
            "name": "suspicious_korean_gov_impersonation",
            "pattern": r"(?i)(?:mofa|mnd|nis|police|customs|nts|moel|moe|mohw|molit|motie)\.go\.kr",
            "weight": 0.6,
            "description": "Korean government domain impersonation attempt"
        },
        
        # AI-generated PowerShell backdoor indicators
        {
            "name": "ai_generated_ps_comments",
            "pattern": r"(?i)#\s*(?:this\s+(?:script|function|code)\s+(?:will|does|performs?)|the\s+following\s+(?:code|script)|note:\s*this)",
            "weight": 0.5,
            "description": "AI-generated code comment patterns"
        },
        {
            "name": "ai_structured_functions",
            "pattern": r"(?i)function\s+(?:Get|Set|New|Remove|Start|Stop|Invoke)-[A-Z][a-zA-Z]+(?:Connection|Data|Command|Process|Service)\s*\{",
            "weight": 0.4,
            "description": "AI-structured PowerShell function naming"
        },
        
        # Base64 and obfuscation patterns
        {
            "name": "base64_powershell_payload",
            "pattern": r"(?:JAB[A-Za-z0-9+/]+={0,2}|TVq[A-Za-z0-9+/]+={0,2}|UEs[A-Za-z0-9+/]+={0,2})",
            "weight": 0.8,
            "description": "Base64 encoded PowerShell or PE payload"
        },
        {
            "name": "string_concatenation_obfuscation",
            "pattern": r"(?i)\$[a-z0-9_]+\s*=\s*(?:['\"][^'\"]{1,5}['\"]\s*\+\s*){3,}['\"][^'\"]+['\"]",
            "weight": 0.7,
            "description": "String concatenation obfuscation technique"
        },
        {
            "name": "char_array_obfuscation",
            "pattern": r"(?i)\[char\]\s*\[\s*\]\s*\$[a-z]+\s*=\s*(?:\d+\s*,\s*){5,}",
            "weight": 0.75,
            "description": "Character array obfuscation"
        },
        
        # VBS/HTA launcher patterns (common KONNI delivery)
        {
            "name": "vbs_wscript_shell",
            "pattern": r"(?i)(?:wscript|cscript)\.(?:shell|createobject\s*\(\s*['\"]wscript\.shell['\"]\s*\))",
            "weight": 0.7,
            "description": "VBScript WScript.Shell execution"
        },
        {
            "name": "hta_powershell_execution",
            "pattern": r"(?i)<\s*script\s+language\s*=\s*['\"](?:vbscript|javascript)['\"].*?(?:powershell|cmd\.exe)",
            "weight": 0.85,
            "description": "HTA-based PowerShell execution"
        },
        
        # LNK file abuse patterns
        {
            "name": "lnk_powershell_execution",
            "pattern": r"(?i)%(?:comspec|systemroot)%.*?(?:/c|/k).*?powershell",
            "weight": 0.8,
            "description": "LNK file PowerShell execution chain"
        },
        
        # Document macro indicators
        {
            "name": "macro_autoopen",
            "pattern": r"(?i)(?:auto_?open|document_?open|workbook_?open)\s*\(",
            "weight": 0.7,
            "description": "Office macro auto-execution"
        },
        {
            "name": "macro_shell_execution",
            "pattern": r"(?i)(?:shell|wscript\.shell|createobject).*?(?:cmd|powershell|mshta|cscript|wscript)",
            "weight": 0.85,
            "description": "Macro-based shell execution"
        },
        
        # Persistence mechanisms
        {
            "name": "registry_persistence",
            "pattern": r"(?i)(?:hkcu|hklm):\\\\(?:software\\\\microsoft\\\\windows\\\\currentversion\\\\(?:run|runonce)|environment)",
            "weight": 0.8,
            "description": "Registry-based persistence mechanism"
        },
        {
            "name": "scheduled_task_persistence",
            "pattern": r"(?i)(?:schtasks|new-scheduledtask).*?(?:/create|register-scheduledtask)",
            "weight": 0.75,
            "description": "Scheduled task persistence"
        },
        
        # Data exfiltration patterns
        {
            "name": "data_exfil_pattern",
            "pattern": r"(?i)(?:invoke-webrequest|invoke-restmethod|webclient).*?(?:-method\s+post|-body)",
            "weight": 0.7,
            "description": "Potential data exfiltration via HTTP POST"
        },
        
        # Korean language phishing indicators
        {
            "name": "korean_phishing_keywords",
            "pattern": r"(?:통일부|외교부|국방부|국정원|정보원|대사관|영사관|청와대|외무부|비밀|긴급|기밀)",
            "weight": 0.65,
            "description": "Korean government/diplomatic phishing keywords"
        },
        {
            "name": "korean_urgency_indicators",
            "pattern": r"(?:긴급\s*확인|즉시\s*조치|비밀\s*문서|내부\s*자료|열람\s*요청)",
            "weight": 0.6,
            "description": "Korean urgency/action phishing indicators"
        },
        
        # Credential harvesting
        {
            "name": "credential_prompt",
            "pattern": r"(?i)(?:get-credential|read-host\s*-assecurestring|convertto-securestring)",
            "weight": 0.7,
            "description": "PowerShell credential harvesting"
        },
        
        # Network reconnaissance
        {
            "name": "network_reconnaissance",
            "pattern": r"(?i)(?:get-netadapter|get-dnsclientserveraddress|test-netconnection|resolve-dnsname)",
            "weight": 0.5,
            "description": "Network reconnaissance commands"
        },
        
        # System information gathering
        {
            "name": "system_info_gathering",
            "pattern": r"(?i)(?:get-wmiobject\s+win32_|get-ciminstance\s+win32_|systeminfo|whoami\s*/all)",
            "weight": 0.5,
            "description": "System information gathering"
        }
    ]
    
    # Known KONNI infrastructure IOCs (hashes, domains, IPs)
    KNOWN_IOCS: Dict[str, List[str]] = {
        "domains": [
            "cloudservices-update.com",
            "microsoft-security-center.com",
            "office365-update.com",
        ],
        "file_hashes": [
            # Placeholder for known malicious hashes
        ],
        "ip_addresses": [
            # Placeholder for known C2 IPs
        ]
    }
    
    def __init__(self) -> None:
        """Initialize the KONNI phishing detector engine."""
        super().__init__()
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        self._compile_patterns()
        logger.info(
            f"Initialized {self.name} v{self.version} with {len(self.PATTERNS)} detection patterns"
        )
    
    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        for pattern_def in self.PATTERNS:
            try:
                self._compiled_patterns[pattern_def["name"]] = re.compile(
                    pattern_def["pattern"],
                    re.MULTILINE | re.DOTALL
                )
            except re.error as e:
                logger.error(
                    f"Failed to compile pattern '{pattern_def['name']}': {e}"
                )
    
    def _extract_context(
        self,
        content: str,
        match: re.Match,
        context_size: int = 100
    ) -> str:
        """
        Extract surrounding context for a pattern match.
        
        Args:
            content: Full content string
            match: Regex match object
            context_size: Number of characters to include before/after match
            
        Returns:
            String containing match with surrounding context
        """
        start = max(0, match.start() - context_size)
        end = min(len(content), match.end() + context_size)
        context = content[start:end]
        
        # Add ellipsis indicators
        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."
            
        return context.replace("\n", " ").strip()
    
    def _calculate_confidence(
        self,
        matches: List[MatchDetail],
        content_length: int
    ) -> float:
        """
        Calculate overall confidence score based on matches.
        
        Args:
            matches: List of pattern matches found
            content_length: Length of analyzed content
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not matches:
            return 0.0
        
        # Calculate weighted score
        total_weight = sum(m.risk_score for m in matches)
        
        # Apply diminishing returns for many matches
        match_factor = min(1.0, len(matches) / 5.0)
        
        # Consider content length (shorter content with many matches is more suspicious)
        length_factor = min(1.0, 5000 / max(content_length, 100))
        
        # Combine factors
        raw_confidence = (total_weight / len(matches)) * match_factor * (0.7 + 0.3 * length_factor)
        
        return min(0.99, max(0.1, raw_confidence))
    
    def _determine_severity(
        self,
        matches: List[MatchDetail],
        confidence: float
    ) -> Severity:
        """
        Determine appropriate severity based on findings.
        
        Args:
            matches: List of pattern matches found
            confidence: Calculated confidence score
            
        Returns:
            Appropriate Severity level
        """
        high_risk_patterns = {
            "powershell_download_cradle",
            "powershell_encoded_command",
            "hta_powershell_execution",
            "macro_shell_execution",
            "base64_powershell_payload"
        }
        
        # Check for high-risk pattern matches
        high_risk_count = sum(
            1 for m in matches if m.pattern_name in high_risk_patterns
        )
        
        if high_risk_count >= 2 or (high_risk_count >= 1 and confidence > 0.8):
            return Severity.CRITICAL
        elif high_risk_count >= 1 or confidence > 0.7:
            return Severity.HIGH
        elif confidence > 0.5:
            return Severity.MEDIUM
        else:
            return Severity.LOW
    
    def _check_iocs(self, content: str) -> List[Dict[str, str]]:
        """
        Check content against known KONNI IOCs.
        
        Args:
            content: Content to check
            
        Returns:
            List of matched IOCs with details
        """
        found_iocs = []
        content_lower = content.lower()
        
        for domain in self.KNOWN_IOCS.get("domains", []):
            if domain.lower() in content_lower:
                found_iocs.append({
                    "type": "domain",
                    "value": domain,
                    "description": "Known KONNI infrastructure domain"
                })
        
        # Check for file hashes in content
        hash_pattern = re.compile(r"\b[a-fA-F0-9]{64}\b|\b[a-fA-F0-9]{40}\b|\b[a-fA-F0-9]{32}\b")
        for hash_match in hash_pattern.finditer(content):
            hash_value = hash_match.group().lower()
            if hash_value in [h.lower() for h in self.KNOWN_IOCS.get("file_hashes", [])]:
                found_iocs.append({
                    "type": "file_hash",
                    "value": hash_value,
                    "description": "Known KONNI malware hash"
                })
        
        return found_iocs
    
    def detect(self, content: str) -> DetectionResult:
        """
        Perform detection analysis on the provided content.
        
        Analyzes content for indicators of KONNI APT phishing campaigns,
        including AI-generated PowerShell backdoors and associated TTPs.
        
        Args:
            content: String content to analyze (email, script, document text)
            
        Returns:
            DetectionResult with detection status, confidence, and metadata
        """
        if not content or not isinstance(content, str):
            logger.warning("Invalid content provided for detection")
            return DetectionResult(
                detected=False,
                engine_name=self.name,
                severity=Severity.LOW,
                confidence=0.0,
                message="No valid content provided for analysis",
                metadata={}
            )
        
        logger.debug(f"Starting detection on content of length {len(content)}")
        
        matches: List[MatchDetail] = []
        
        # Run pattern matching
        for pattern_def in self.PATTERNS:
            pattern_name = pattern_def["name"]
            compiled_pattern = self._compiled_patterns.get(pattern_name)
            
            if not compiled_pattern:
                continue
            
            try:
                for match in compiled_pattern.finditer(content):
                    match_detail = MatchDetail(
                        pattern_name=pattern_name,
                        matched_text=match.group()[:500],  # Limit matched text length
                        position=(match.start(), match.end()),
                        risk_score=pattern_def["weight"],
                        context=self._extract_context(content, match)
                    )
                    matches.append(match_detail)
                    logger.debug(f"Pattern '{pattern_name}' matched at position {match.start()}")
                    
            except Exception as e:
                logger.error(f"Error matching pattern '{pattern_name}': {e}")
        
        # Check for known IOCs
        ioc_matches = self._check_iocs(content)
        
        # Calculate confidence and severity
        confidence = self._calculate_confidence(matches, len(content))
        
        # Boost confidence if IOCs found
        if ioc_matches:
            confidence = min(0.99, confidence + 0.15 * len(ioc_matches))
        
        severity = self._determine_severity(matches, confidence)
        
        # Determine detection result
        detected = len(matches) > 0 and confidence > 0.3
        
        # Build metadata
        metadata = {
            "engine_version": self.version,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "content_length": len(content),
            "content_hash": sha256(content.encode()).hexdigest()[:16],
            "total_matches": len(matches),
            "unique_patterns_matched": len(set(m.pattern_name for m in matches)),
            "iocs_found": len(ioc_matches),
            "threat_actor": "KONNI",
            "threat_actor_aliases": ["APT37", "Reaper", "ScarCruft", "Group123"],
            "target_regions": ["South Korea", "East Asia"],
            "target_sectors": ["Government", "Diplomatic", "NGO", "Academia"],
            "techniques": self._map_to_mitre(matches)
        }
        
        # Generate message
        if detected:
            high_risk = [m for m in matches if m.risk_score >= 0.8]
            message = (
                f"KONNI APT phishing indicators detected: {len(matches)} pattern matches "
                f"({len(high_risk)} high-risk). Potential AI-generated PowerShell backdoor activity."
            )
        else:
            message = "No significant KONNI APT indicators detected"
        
        logger.info(
            f"Detection complete: detected={detected}, confidence={confidence:.2f}, "
            f"severity={severity.name}, matches={len(matches)}"
        )
        
        return DetectionResult(
            detected=detected,
            engine_name=self.name,
            severity=severity,
            confidence=confidence,
            message=message,
            metadata=metadata
        )
    
    def analyze(self, content: str) -> Dict[str, Any]:
        """
        Perform detailed analysis on the provided content.
        
        Provides comprehensive analysis including pattern matches,
        IOC correlation, MITRE ATT&CK mapping, and remediation guidance.
        
        Args:
            content: String content to analyze
            
        Returns:
            Dictionary containing detailed analysis results
        """
        if not content or not isinstance(content, str):
            return {
                "success": False,
                "error": "Invalid content provided",
                "analysis": None
            }
        
        logger.info(f"Starting detailed analysis on content of length {len(content)}")
        
        # Get base detection result
        detection_result = self.detect(content)
        
        # Collect detailed match information
        detailed_matches: List[Dict[str, Any]] = []
        
        for pattern_def in self.PATTERNS:
            pattern_name = pattern_def["name"]
            compiled_pattern = self._compiled_patterns.get(pattern_name)
            
            if not compiled_pattern:
                continue
            
            try:
                for match in compiled_pattern.finditer(content):
                    detailed_matches.append({
                        "pattern_name": pattern_name,
                        "pattern_description": pattern_def["description"],
                        "matched_text": match.group()[:200],
                        "position": {
                            "start": match.start(),
                            "end": match.end()
                        },
                        "risk_score": pattern_def["weight"],
                        "context": self._extract_context(content, match, 150)
                    })
            except Exception as e:
                logger.error(f"Error in detailed analysis for pattern '{pattern_name}': {e}")
        
        # Check IOCs
        ioc_results = self._check_iocs(content)
        
        # Extract potential indicators
        extracted_indicators = self._extract_indicators(content)
        
        # Map to MITRE ATT&CK
        mitre_mapping = self._map_to_mitre_detailed(detailed_matches)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            detailed_matches,
            detection_result.severity
        )
        
        analysis_result = {
            "success": True,
            "analysis": {
                "summary": {
                    "detected": detection_result.detected,
                    "severity": detection_result.severity.name,
                    "confidence": round(detection_result.confidence, 4),
                    "threat_actor": "KONNI",
                    "campaign": "AI-Generated PowerShell Backdoors (2024)",
                    "total_indicators": len(detailed_matches)
                },
                "pattern_matches": detailed_matches,
                "known_iocs": ioc_results,
                "extracted_indicators": extracted_indicators,
                "mitre_attack_mapping": mitre_mapping,
                "threat_context": {
                    "actor_profile": {
                        "name": "KONNI",
                        "aliases": ["APT37", "Reaper", "ScarCruft", "Group123", "Ricochet Chollima"],
                        "origin": "North Korea",
                        "active_since": "2014",
                        "motivation": "Espionage, Intelligence Collection"
                    },
                    "campaign_characteristics": [
                        "AI-generated PowerShell backdoors",
                        "Targeting South Korean diplomatic channels",
                        "Focus on government and NGO sectors",
                        "Sophisticated social engineering",
                        "Multi-stage payload delivery"
                    ],
                    "related_malware": ["KONNI RAT", "NOKKI", "DOGCALL", "ROKRAT"]
                },
                "recommendations": recommendations,
                "metadata": {
                    "engine": self.name,
                    "engine_version": self.version,
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "content_hash": sha256(content.encode()).hexdigest()
                }
            }
        }
        
        logger.info(
            f"Detailed analysis complete: {len(detailed_matches)} matches, "
            f"severity={detection_result.severity.name}"
        )
        
        return analysis_result
    
    def _extract_indicators(self, content: str) -> Dict[str, List[str]]:
        """
        Extract potential IOCs from content.
        
        Args:
            content: Content to extract indicators from
            
        Returns:
            Dictionary of indicator types to lists of values
        """
        indicators: Dict[str, List[str]] = {
            "urls": [],
            "domains": [],
            "ip_addresses": [],
            "email_addresses": [],
            "file_hashes": [],
            "file_paths": []
        }
        
        # URL extraction
        url_pattern = re.compile(
            r"(?:https?|hxxps?|ftp)://[^\s<>\"\')}\]]+",
            re.IGNORECASE
        )
        indicators["urls"] = list(set(url_pattern.findall(content)))[:50]
        
        # Domain extraction
        domain_pattern = re.compile(
            r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b"
        )
        indicators["domains"] = list(set(domain_pattern.findall(content)))[:50]
        
        # IP address extraction
        ip_pattern = re.compile(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        )
        indicators["ip_addresses"] = list(set(ip_pattern.findall(content)))[:20]
        
        # Email extraction
        email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )
        indicators["email_addresses"] = list(set(email_pattern.findall(content)))[:20]
        
        # Hash extraction
        hash_pattern = re.compile(
            r"\b[a-fA-F0-9]{64}\b|\b[a-fA-F0-9]{40}\b|\b[a-fA-F0-9]{32}\b"
        )
        indicators["file_hashes"] = list(set(hash_pattern.findall(content)))[:20]
        
        # File path extraction
        path_pattern = re.compile(
            r"(?:[A-Za-z]:\\|\\\\|/)[^\s<>:\"|\?\*\n]+",
            re.IGNORECASE
        )
        indicators["file_paths"] = list(set(path_pattern.findall(content)))[:20]
        
        return indicators
    
    def _map_to_mitre(self, matches: List[MatchDetail]) -> List[str]:
        """
        Map pattern matches to MITRE ATT&CK technique IDs.
        
        Args:
            matches: List of pattern matches
            
        Returns:
            List of unique MITRE ATT&CK technique IDs
        """
        pattern_to_mitre = {
            "powershell_encoded_command": "T1059.001",
            "powershell_bypass_execution_policy": "T1059.001",
            "powershell_hidden_window": "T1564.003",
            "powershell_download_cradle": "T1105",
            "powershell_reflection_load": "T1620",
            "base64_powershell_payload": "T1027",
            "string_concatenation_obfuscation": "T1027",
            "char_array_obfuscation": "T1027",
            "vbs_wscript_shell": "T1059.005",
            "hta_powershell_execution": "T1218.005",
            "lnk_powershell_execution": "T1547.009",
            "macro_autoopen": "T1137.001",
            "macro_shell_execution": "T1059.005",
            "registry_persistence": "T1547.001",
            "scheduled_task_persistence": "T1053.005",
            "data_exfil_pattern": "T1041",
            "credential_prompt": "T1056.002",
            "network_reconnaissance": "T1016",
            "system_info_gathering": "T1082"
        }
        
        techniques = set()
        for match in matches:
            if match.pattern_name in pattern_to_mitre:
                techniques.add(pattern_to_mitre[match.pattern_name])
        
        return sorted(list(techniques))
    
    def _map_to_mitre_detailed(
        self,
        matches: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Map pattern matches to detailed MITRE ATT&CK information.
        
        Args:
            matches: List of detailed match dictionaries
            
        Returns:
            List of MITRE ATT&CK technique details
        """
        mitre_details = {
            "T1059.001": {
                "id": "T1059.001",
                "name": "PowerShell",
                "tactic": "Execution",
                "url": "https://attack.mitre.org/techniques/T1059/001/"
            },
            "T1564.003": {
                "id": "T1564.003",
                "name": "Hidden Window",
                "tactic": "Defense Evasion",
                "url": "https://attack.mitre.org/techniques/T1564/003/"
            },
            "T1105": {
                "id": "T1105",
                "name": "Ingress Tool Transfer",
                "tactic": "Command and Control",
                "url": "https://attack.mitre.org/techniques/T1105/"
            },
            "T1620": {
                "id": "T1620",
                "name": "Reflective Code Loading",
                "tactic": "Defense Evasion",
                "url": "https://attack.mitre.org/techniques/T1620/"
            },
            "T1027": {
                "id": "T1027",
                "name": "Obfuscated Files or Information",
                "tactic": "Defense Evasion",
                "url": "https://attack.mitre.org/techniques/T1027/"
            },
            "T1059.005": {
                "id": "T1059.005",
                "name": "Visual Basic",
                "tactic": "Execution",
                "url": "https://attack.mitre.org/techniques/T1059/005/"
            },
            "T1218.005": {
                "id": "T1218.005",
                "name": "Mshta",
                "tactic": "Defense Evasion",
                "url": "https://attack.mitre.org/techniques/T1218/005/"
            },
            "T1547.001": {
                "id": "T1547.001",
                "name": "Registry Run Keys / Startup Folder",
                "tactic": "Persistence",
                "url": "https://attack.mitre.org/techniques/T1547/001/"
            },
            "T1547.009": {
                "id": "T1547.009",
                "name": "Shortcut Modification",
                "tactic": "Persistence",
                "url": "https://attack.mitre.org/techniques/T1547/009/"
            },
            "T1053.005": {
                "id": "T1053.005",
                "name": "Scheduled Task",
                "tactic": "Persistence",
                "url": "https://attack.mitre.org/techniques/T1053/005/"
            },
            "T1137.001": {
                "id": "T1137.001",
                "name": "Office Template Macros",
                "tactic": "Persistence",
                "url": "https://attack.mitre.org/techniques/T1137/001/"
            },
            "T1041": {
                "id": "T1041",
                "name": "Exfiltration Over C2 Channel",
                "tactic": "Exfiltration",
                "url": "https://attack.mitre.org/techniques/T1041/"
            },
            "T1056.002": {
                "id": "T1056.002",
                "name": "GUI Input Capture",
                "tactic": "Collection",
                "url": "https://attack.mitre.org/techniques/T1056/002/"
            },
            "T1016": {
                "id": "T1016",
                "name": "System Network Configuration Discovery",
                "tactic": "Discovery",
                "url": "https://attack.mitre.org/techniques/T1016/"
            },
            "T1082": {
                "id": "T1082",
                "name": "System Information Discovery",
                "tactic": "Discovery",
                "url": "https://attack.mitre.org/techniques/T1082/"
            }
        }
        
        # Get unique technique IDs from matches
        pattern_to_mitre = {
            "powershell_encoded_command": "T1059.001",
            "powershell_bypass_execution_policy": "T1059.001",
            "powershell_hidden_window": "T1564.003",
            "powershell_download_cradle": "T1105",
            "powershell_reflection_load": "T1620",
            "base64_powershell_payload": "T1027",
            "string_concatenation_obfuscation": "T1027",
            "char_array_obfuscation": "T1027",
            "vbs_wscript_shell": "T1059.005",
            "hta_powershell_execution": "T1218.005",
            "lnk_powershell_execution": "T1547.009",
            "macro_autoopen": "T1137.001",
            "macro_shell_execution": "T1059.005",
            "registry_persistence": "T1547.001",
            "scheduled_task_persistence": "T1053.005",
            "data_exfil_pattern": "T1041",
            "credential_prompt": "T1056.002",
            "network_reconnaissance": "T1016",
            "system_info_gathering": "T1082"
        }
        
        found_techniques = set()
        for match in matches:
            pattern_name = match.get("pattern_name", "")
            if pattern_name in pattern_to_mitre:
                found_techniques.add(pattern_to_mitre[pattern_name])
        
        return [
            mitre_details[tid]
            for tid in sorted(found_techniques)
            if tid in mitre_details
        ]
    
    def _generate_recommendations(
        self,
        matches: List[Dict[str, Any]],
        severity: Severity
    ) -> List[Dict[str, str]]:
        """
        Generate remediation and response recommendations.
        
        Args:
            matches: List of detailed match dictionaries
            severity: Determined severity level
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        # Base recommendations
        recommendations.append({
            "priority": "high",
            "category": "immediate_response",
            "action": "Isolate affected systems",
            "description": "Immediately isolate any systems that may have executed the suspicious content to prevent lateral movement."
        })
        
        if severity in [Severity.CRITICAL, Severity.HIGH]:
            recommendations.append({
                "priority": "high",
                "category": "incident_response",
                "action": "Engage incident response team",
                "description": "Escalate to incident response team for full investigation of potential KONNI APT compromise."
            })
            
            recommendations.append({
                "priority": "high",
                "category": "threat_hunting",
                "action": "Hunt for KONNI indicators",
                "description": "Search for known KONNI IOCs across the environment including registry keys, scheduled tasks, and network connections."
            })
        
        # Check for specific patterns and add targeted recommendations
        pattern_names = {m.get("pattern_name", "") for m in matches}
        
        if "powershell_encoded_command" in pattern_names or "powershell_download_cradle" in pattern_names:
            recommendations.append({
                "priority": "medium",
                "category": "detection",
                "action": "Enable PowerShell logging",
                "description": "Enable Script Block Logging and Module Logging to capture PowerShell execution details."
            })
        
        if "registry_persistence" in pattern_names or "scheduled_task_persistence" in pattern_names:
            recommendations.append({
                "priority": "high",
                "category": "remediation",
                "action": "Check persistence mechanisms",
                "description": "Audit Run keys, scheduled tasks, and startup folders for unauthorized entries."
            })
        
        if "macro_autoopen" in pattern_names or "macro_shell_execution" in pattern_names:
            recommendations.append({
                "priority": "medium",
                "category": "prevention",
                "action": "Restrict macro execution",
                "description": "Configure Office to block macros from internet-sourced documents and enable ASR rules."
            })
        
        # General recommendations
        recommendations.append({
            "priority": "medium",
            "category": "prevention",
            "action": "User awareness",
            "description": "Alert users about KONNI phishing campaigns targeting diplomatic and government sectors."
        })
        
        recommendations.append({
            "priority": "low",
            "category": "intelligence",
            "action": "Share threat intelligence",
            "description": "Report indicators to relevant ISACs and threat intelligence sharing platforms."
        })
        
        return recommendations