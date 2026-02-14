"""
Sandbox Escape Monitor

Detects Python sandbox escape techniques used to execute arbitrary
commands in isolated AI coding assistant environments.

OWASP: ASI05 - Unexpected Code Execution (RCE)
Source: AI Security Digest Week 1 2026 (#7 Copilot Sandbox Escape)

Note: This engine extends supply_chain_scanner.py with additional
sandbox-specific detection patterns.
"""

import re
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SandboxEscapeSeverity(Enum):
    CRITICAL = "critical"  # Direct command execution
    HIGH = "high"          # Builtins/globals access
    MEDIUM = "medium"      # Sensitive file access
    LOW = "low"            # Obfuscation only


@dataclass
class SandboxEscapeFinding:
    """Individual sandbox escape detection finding."""
    category: str
    pattern_name: str
    matched_text: str
    line_number: Optional[int]
    severity: SandboxEscapeSeverity
    description: str
    recommendation: str


@dataclass 
class SandboxEscapeResult:
    """Complete sandbox escape scan result."""
    detected: bool
    severity: str
    risk_score: float
    findings: List[SandboxEscapeFinding] = field(default_factory=list)
    categories_detected: Set[str] = field(default_factory=set)


class SandboxMonitor:
    """
    Detects Python sandbox escape techniques.
    
    Categories:
    1. OS/Subprocess execution
    2. Dynamic code execution (eval/exec)
    3. Builtins/globals manipulation
    4. Sensitive file access
    5. Code obfuscation
    6. Import manipulation
    
    Source: https://medium.com/@d_f4u1t/arbitrary-command-execution-within-copilots-isolated-linux-environment-via-python-sandbox-escape
    """

    # Pattern categories with severity mapping
    ESCAPE_PATTERNS = {
        'os_execution': {
            'severity': SandboxEscapeSeverity.CRITICAL,
            'description': 'Direct OS command execution',
            'patterns': [
                (r'\bos\.system\s*\(', 'os.system()'),
                (r'\bos\.popen\s*\(', 'os.popen()'),
                (r'\bos\.exec[vl]p?e?\s*\(', 'os.exec*()'),
                (r'\bos\.spawn[vl]p?e?\s*\(', 'os.spawn*()'),
                (r'\bos\.fork\s*\(', 'os.fork()'),
                (r'\bpty\.spawn\s*\(', 'pty.spawn()'),
            ],
            'recommendation': 'Block or sandbox all os.* command execution calls'
        },
        'subprocess_execution': {
            'severity': SandboxEscapeSeverity.CRITICAL,
            'description': 'Subprocess command execution',
            'patterns': [
                (r'\bsubprocess\.Popen\s*\(', 'subprocess.Popen()'),
                (r'\bsubprocess\.call\s*\(', 'subprocess.call()'),
                (r'\bsubprocess\.run\s*\(', 'subprocess.run()'),
                (r'\bsubprocess\.check_output\s*\(', 'subprocess.check_output()'),
                (r'\bsubprocess\.check_call\s*\(', 'subprocess.check_call()'),
                (r'\bsubprocess\.getoutput\s*\(', 'subprocess.getoutput()'),
            ],
            'recommendation': 'Block subprocess module in sandboxed environment'
        },
        'dynamic_execution': {
            'severity': SandboxEscapeSeverity.CRITICAL,
            'description': 'Dynamic code execution',
            'patterns': [
                (r'\beval\s*\([^)]*\)', 'eval()'),
                (r'\bexec\s*\([^)]*\)', 'exec()'),
                (r'\bcompile\s*\([^)]+[\'"]exec[\'"]\s*\)', 'compile(..., "exec")'),
                (r'\b__import__\s*\(', '__import__()'),
                (r'\bimportlib\.import_module\s*\(', 'importlib.import_module()'),
            ],
            'recommendation': 'Disable eval/exec in AI-generated code execution'
        },
        'builtins_manipulation': {
            'severity': SandboxEscapeSeverity.HIGH,
            'description': 'Python internals manipulation for sandbox escape',
            'patterns': [
                (r'__builtins__', '__builtins__ access'),
                (r'__globals__', '__globals__ access'),
                (r'__subclasses__\s*\(\s*\)', '__subclasses__() enumeration'),
                (r'__mro__', '__mro__ access'),
                (r'__bases__', '__bases__ access'),
                (r'__class__\s*\.\s*__', '__class__.__* chain'),
                (r'\(\s*\)\s*\.\s*__class__', '()).__class__ pattern'),
                (r'__code__', '__code__ manipulation'),
                (r'__getattribute__', '__getattribute__ override'),
            ],
            'recommendation': 'Restrict access to Python dunder attributes'
        },
        'sensitive_file_access': {
            'severity': SandboxEscapeSeverity.MEDIUM,
            'description': 'Access to sensitive system files',
            'patterns': [
                (r'open\s*\([^)]*[\'\"]/etc/passwd[\'\"]', '/etc/passwd access'),
                (r'open\s*\([^)]*[\'\"]/etc/shadow[\'\"]', '/etc/shadow access'),
                (r'open\s*\([^)]*[\'\"]\.ssh', '.ssh directory access'),
                (r'open\s*\([^)]*[\'\"]\.aws', '.aws credentials access'),
                (r'open\s*\([^)]*[\'\"]\.env[\'\"]', '.env file access'),
                (r'open\s*\([^)]*[\'\"]\.bashrc[\'\"]', '.bashrc access'),
                (r'open\s*\([^)]*[\'\"]\.bash_history[\'\"]', '.bash_history access'),
            ],
            'recommendation': 'Implement path allowlisting for file operations'
        },
        'code_obfuscation': {
            'severity': SandboxEscapeSeverity.LOW,
            'description': 'Code obfuscation techniques',
            'patterns': [
                (r'base64\.b64decode\s*\(', 'Base64 decode'),
                (r'bytes\.fromhex\s*\(', 'Hex decode'),
                (r'codecs\.decode\s*\([^)]+[\'"]rot', 'ROT13 decode'),
                (r'chr\s*\(\s*\d+\s*\)', 'chr() character construction'),
                (r'getattr\s*\(\s*__builtins__', 'getattr on builtins'),
            ],
            'recommendation': 'Flag obfuscated code for manual review'
        },
        'ctypes_escape': {
            'severity': SandboxEscapeSeverity.CRITICAL,
            'description': 'ctypes library for native code execution',
            'patterns': [
                (r'\bctypes\.CDLL\s*\(', 'ctypes.CDLL()'),
                (r'\bctypes\.cdll\s*\.', 'ctypes.cdll access'),
                (r'\bctypes\.pythonapi\b', 'ctypes.pythonapi access'),
                (r'\bctypes\.memmove\s*\(', 'ctypes memory manipulation'),
            ],
            'recommendation': 'Block ctypes module entirely in sandbox'
        },
    }

    def __init__(self):
        self._compiled_patterns: Dict[str, List[tuple]] = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regex patterns for performance."""
        for category, config in self.ESCAPE_PATTERNS.items():
            self._compiled_patterns[category] = [
                (re.compile(pattern, re.IGNORECASE | re.MULTILINE), name)
                for pattern, name in config['patterns']
            ]

    def analyze(self, code: str) -> SandboxEscapeResult:
        """
        Analyze code for sandbox escape patterns.
        
        Args:
            code: Python code to analyze
            
        Returns:
            SandboxEscapeResult with findings
        """
        findings: List[SandboxEscapeFinding] = []
        categories_detected: Set[str] = set()
        lines = code.split('\n')
        
        for category, config in self.ESCAPE_PATTERNS.items():
            compiled = self._compiled_patterns[category]
            
            for i, line in enumerate(lines, 1):
                for pattern, pattern_name in compiled:
                    match = pattern.search(line)
                    if match:
                        categories_detected.add(category)
                        findings.append(SandboxEscapeFinding(
                            category=category,
                            pattern_name=pattern_name,
                            matched_text=match.group()[:50],
                            line_number=i,
                            severity=config['severity'],
                            description=config['description'],
                            recommendation=config['recommendation']
                        ))

        # Determine overall severity
        if not findings:
            overall_severity = "safe"
            risk_score = 0.0
        else:
            severities = [f.severity for f in findings]
            if SandboxEscapeSeverity.CRITICAL in severities:
                overall_severity = "critical"
                risk_score = 0.9
            elif SandboxEscapeSeverity.HIGH in severities:
                overall_severity = "high"
                risk_score = 0.7
            elif SandboxEscapeSeverity.MEDIUM in severities:
                overall_severity = "medium"
                risk_score = 0.5
            else:
                overall_severity = "low"
                risk_score = 0.3

        return SandboxEscapeResult(
            detected=len(findings) > 0,
            severity=overall_severity,
            risk_score=risk_score,
            findings=findings[:20],  # Limit to 20
            categories_detected=categories_detected
        )

    def get_recommendations(self, result: SandboxEscapeResult) -> List[str]:
        """Get remediation recommendations based on findings."""
        recommendations = set()
        for finding in result.findings:
            recommendations.add(finding.recommendation)
        return list(recommendations)


# Singleton accessor
_monitor: Optional[SandboxMonitor] = None

def get_monitor() -> SandboxMonitor:
    """Get singleton SandboxMonitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = SandboxMonitor()
    return _monitor

def analyze(code: str) -> SandboxEscapeResult:
    """Analyze code for sandbox escape patterns."""
    return get_monitor().analyze(code)
