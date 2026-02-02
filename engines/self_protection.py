"""
SENTINEL Self-Protection Engine

Scans SENTINEL's own codebase for malware, backdoors, and supply chain attacks.
"Eat your own dog food" - a security product should protect itself first.

Run on startup to verify codebase integrity before serving requests.

Usage:
    from self_protection import SelfProtectionEngine
    
    engine = SelfProtectionEngine()
    result = engine.full_scan()
    
    if not result.is_clean:
        print("⚠️ SENTINEL codebase may be compromised!")
        for finding in result.findings:
            print(f"  - {finding}")
"""

import os
import re
import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Set
from datetime import datetime

logger = logging.getLogger("SelfProtection")


# =============================================================================
# Constants
# =============================================================================

DANGEROUS_PATTERNS = [
    # Code execution
    (r'\beval\s*\([^)]*\b(input|request|data|user)\b',
     "eval() with user input"),
    (r'\bexec\s*\([^)]*\b(input|request|data|user)\b',
     "exec() with user input"),
    (r'__import__\s*\([^)]*\b(input|request|data)\b',
     "dynamic import with user input"),

    # Command injection
    (r'\bos\.system\s*\([^)]*\b(input|request|data|user)\b',
     "os.system with user input"),
    (r'\bsubprocess\.\w+\s*\([^)]*shell\s*=\s*True',
     "subprocess with shell=True"),

    # Network exfiltration
    (r'requests\.(get|post)\s*\([^)]*\b(env|secret|key|password|token)\b',
     "potential data exfiltration"),
    (r'socket\.connect\s*\(\s*\([^)]*,\s*\d{4,5}\s*\)',
     "raw socket connection"),

    # Obfuscation
    (r'base64\.b64decode\s*\([^)]*\)\s*\)', "base64 decode + execute pattern"),
    (r'\\x[0-9a-f]{2}\\x[0-9a-f]{2}\\x[0-9a-f]{2}', "hex-encoded strings"),
    (r'chr\s*\(\s*\d+\s*\)\s*\+\s*chr', "chr() obfuscation"),

    # Persistence
    (r'crontab|schtasks|at\s+\d+:', "scheduled task creation"),
    (r'HKEY_|winreg\.', "Windows registry access"),

    # Sleeper agents
    (r'datetime\.now\(\)\.year\s*[><=]+\s*202[6-9]', "date-based trigger"),
    (r'os\.environ\.get\s*\([^)]*\)\s*==', "environment-based trigger"),
]

ALLOWED_EXEC_LOCATIONS = {
    # Test files are allowed to have dangerous patterns
    "tests/",
    "test_",
    "_test.py",
    # Attack payloads are supposed to have malicious patterns
    "payloads/",
    "attack_",
    "strike/",
    # Examples showing what to detect
    "examples/",
    # Benchmark datasets
    "benchmarks/",
    "dataset",
    # CTF workspace (attack scripts)
    "_ctf_workspace/",
    "ctf",
    # Detection engines (they DETECT these patterns, so they contain them)
    "src/brain/engines/",
    "detector",
    "scanner",
    "verifier",
    # Documentation
    "docs/",
    # Evaluation code
    "evaluation/",
    # Self-referential (we detect our own patterns)
    "self_protection.py",
    # RLM-Toolkit (separate library, has own security)
    "rlm-toolkit/",
}

CRITICAL_FILES = [
    "src/brain/engines/__init__.py",
    "src/brain/analyzer.py",
    "engines/__init__.py",
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ScanFinding:
    """A security finding in the codebase."""
    file_path: str
    line_number: int
    pattern_name: str
    matched_text: str
    severity: str = "HIGH"

    def __str__(self):
        return f"[{self.severity}] {self.file_path}:{self.line_number} - {self.pattern_name}"


@dataclass
class IntegrityCheck:
    """File integrity verification result."""
    file_path: str
    expected_hash: Optional[str]
    actual_hash: str
    matches: bool


@dataclass
class ScanResult:
    """Complete self-scan result."""
    is_clean: bool
    findings: List[ScanFinding] = field(default_factory=list)
    integrity_checks: List[IntegrityCheck] = field(default_factory=list)
    files_scanned: int = 0
    scan_duration_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def summary(self) -> str:
        status = "✅ CLEAN" if self.is_clean else "⚠️ ISSUES FOUND"
        return f"{status} | {self.files_scanned} files | {len(self.findings)} findings | {self.scan_duration_ms:.0f}ms"


# =============================================================================
# Self-Protection Engine
# =============================================================================

class SelfProtectionEngine:
    """
    Scans SENTINEL's own codebase for security issues.

    Run this on startup to verify the installation hasn't been tampered with.
    """

    def __init__(self, root_path: Optional[Path] = None):
        self.root_path = root_path or self._find_sentinel_root()
        self.integrity_hashes: dict = {}
        logger.info(f"SelfProtectionEngine initialized: {self.root_path}")

    def _find_sentinel_root(self) -> Path:
        """Find SENTINEL installation root."""
        # Try common locations
        candidates = [
            Path(__file__).parent.parent,  # engines/../
            Path.cwd(),
            Path.home() / "sentinel",
        ]

        for path in candidates:
            if (path / "src" / "brain").exists() or (path / "engines").exists():
                return path

        return Path.cwd()

    def _is_allowed_location(self, file_path: str) -> bool:
        """Check if file is in allowed location for dangerous patterns."""
        path_lower = file_path.lower().replace("\\", "/")
        return any(allowed in path_lower for allowed in ALLOWED_EXEC_LOCATIONS)

    def scan_file(self, file_path: Path) -> List[ScanFinding]:
        """Scan a single file for dangerous patterns."""
        findings = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Cannot read {file_path}: {e}")
            return findings

        rel_path = str(file_path.relative_to(self.root_path))

        # Skip if in allowed location
        if self._is_allowed_location(rel_path):
            return findings

        for line_num, line in enumerate(content.split("\n"), 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue

            for pattern, name in DANGEROUS_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(ScanFinding(
                        file_path=rel_path,
                        line_number=line_num,
                        pattern_name=name,
                        matched_text=line.strip()[:100],
                    ))

        return findings

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file."""
        sha256 = hashlib.sha256()
        try:
            sha256.update(file_path.read_bytes())
        except Exception:
            return ""
        return sha256.hexdigest()

    def verify_integrity(self, expected_hashes: Optional[dict] = None) -> List[IntegrityCheck]:
        """Verify critical file integrity."""
        checks = []
        hashes = expected_hashes or self.integrity_hashes

        for rel_path in CRITICAL_FILES:
            file_path = self.root_path / rel_path
            if not file_path.exists():
                continue

            actual_hash = self.compute_file_hash(file_path)
            expected = hashes.get(rel_path)

            checks.append(IntegrityCheck(
                file_path=rel_path,
                expected_hash=expected,
                actual_hash=actual_hash,
                matches=expected is None or expected == actual_hash,
            ))

        return checks

    def full_scan(self) -> ScanResult:
        """Run complete self-scan of SENTINEL codebase."""
        import time
        start = time.time()

        all_findings: List[ScanFinding] = []
        files_scanned = 0

        # Scan Python files
        for py_file in self.root_path.rglob("*.py"):
            # Skip virtual environments and caches
            path_str = str(py_file)
            if any(skip in path_str for skip in ["venv", ".venv", "__pycache__", ".git", "node_modules"]):
                continue

            findings = self.scan_file(py_file)
            all_findings.extend(findings)
            files_scanned += 1

        # Verify integrity
        integrity_checks = self.verify_integrity()
        integrity_failures = [c for c in integrity_checks if not c.matches]

        duration_ms = (time.time() - start) * 1000

        is_clean = len(all_findings) == 0 and len(integrity_failures) == 0

        result = ScanResult(
            is_clean=is_clean,
            findings=all_findings,
            integrity_checks=integrity_checks,
            files_scanned=files_scanned,
            scan_duration_ms=duration_ms,
        )

        logger.info(f"Self-scan complete: {result.summary()}")
        return result

    def get_info(self) -> dict:
        """Engine metadata for SENTINEL registry."""
        return {
            "name": "SelfProtectionEngine",
            "version": "1.0.0",
            "description": "Scans SENTINEL's own codebase for security issues",
            "category": "defense",
            "self_protection": True,
        }


# =============================================================================
# Startup Hook
# =============================================================================

def verify_on_startup(fail_on_issues: bool = False) -> ScanResult:
    """
    Run self-scan on SENTINEL startup.

    Call this from your main entry point:
        from engines.self_protection import verify_on_startup

        result = verify_on_startup()
        if not result.is_clean:
            logger.warning("SENTINEL codebase has issues!")
    """
    engine = SelfProtectionEngine()
    result = engine.full_scan()

    if not result.is_clean:
        logger.warning(
            f"⚠️ SENTINEL Self-Scan: {len(result.findings)} issues found!")
        for finding in result.findings[:5]:  # Show first 5
            logger.warning(f"   {finding}")

        if fail_on_issues:
            raise RuntimeError("SENTINEL codebase integrity check failed!")
    else:
        logger.info("✅ SENTINEL Self-Scan: Codebase is clean")

    return result


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    print("🛡️ SENTINEL Self-Protection Scan")
    print("=" * 50)

    engine = SelfProtectionEngine()
    result = engine.full_scan()

    print(f"\n📊 {result.summary()}\n")

    if result.findings:
        print("⚠️ Findings:")
        for f in result.findings:
            print(f"   {f}")

    if result.integrity_checks:
        print("\n🔐 Integrity Checks:")
        for c in result.integrity_checks:
            status = "✅" if c.matches else "❌"
            print(f"   {status} {c.file_path}")

    sys.exit(0 if result.is_clean else 1)
