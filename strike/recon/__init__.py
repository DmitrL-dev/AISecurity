"""
SENTINEL Strike — Reconnaissance Module

External and Internal scanning capabilities.
"""

from .external import ExternalScanner, ExternalScanResult, run_external_scan
from .internal import InternalScanner, InternalScanResult, MCPServerInfo, run_internal_scan
from .network_scanner import NetworkScanner, ScanResult, scan_target
from .tech_fingerprint import TechFingerprinter, TechFingerprint, fingerprint_url
from .semgrep_scanner import (
    SemgrepScanner, SemgrepFinding, SemgrepScanResult,
    scan_for_llm_vulns, scan_for_secrets, scan_github
)
from .ai_detector import AIDetector, AIDetectionResult, detect_hidden_ai

__all__ = [
    "ExternalScanner",
    "ExternalScanResult",
    "run_external_scan",
    "InternalScanner",
    "InternalScanResult",
    "MCPServerInfo",
    "run_internal_scan",
    "NetworkScanner",
    "ScanResult",
    "scan_target",
    "TechFingerprinter",
    "TechFingerprint",
    "fingerprint_url",
    # Semgrep
    "SemgrepScanner",
    "SemgrepFinding",
    "SemgrepScanResult",
    "scan_for_llm_vulns",
    "scan_for_secrets",
    "scan_github",
    # AI Detection
    "AIDetector",
    "AIDetectionResult",
    "detect_hidden_ai",
]
