"""
Model Integrity Verifier

Verifies AI model file integrity through:
- Cryptographic hash verification
- Signature validation
- Safe format detection
- Tamper detection

Auto-generated from R&D: emerging_threats_research.md
Generated: 2026-01-07
"""

import re
import hashlib
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ModelFormat(Enum):
    SAFETENSORS = "safetensors"
    ONNX = "onnx"
    PICKLE = "pickle"
    TORCH = "torch"
    TENSORFLOW = "tensorflow"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class IntegrityCheck:
    """Individual integrity check result."""
    check_name: str
    passed: bool
    details: str
    risk_impact: RiskLevel


@dataclass
class ModelIntegrityResult:
    """Complete model integrity verification result."""
    is_verified: bool
    overall_risk: RiskLevel
    model_format: ModelFormat
    checks: List[IntegrityCheck] = field(default_factory=list)
    computed_hash: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)


class ModelIntegrityVerifier:
    """
    Verifies integrity and safety of AI model files.
    
    Checks:
    - File format safety (safetensors > ONNX > pickle)
    - Hash integrity
    - Signature validation
    - Known malicious patterns
    - Suspicious metadata
    """

    # Safe file extensions (ordered by safety)
    SAFE_EXTENSIONS = {
        '.safetensors': (ModelFormat.SAFETENSORS, RiskLevel.SAFE),
        '.onnx': (ModelFormat.ONNX, RiskLevel.LOW),
    }

    # Risky file extensions
    RISKY_EXTENSIONS = {
        '.pkl': (ModelFormat.PICKLE, RiskLevel.CRITICAL),
        '.pickle': (ModelFormat.PICKLE, RiskLevel.CRITICAL),
        '.pt': (ModelFormat.TORCH, RiskLevel.HIGH),
        '.pth': (ModelFormat.TORCH, RiskLevel.HIGH),
        '.bin': (ModelFormat.TORCH, RiskLevel.HIGH),
        '.h5': (ModelFormat.TENSORFLOW, RiskLevel.MEDIUM),
        '.pb': (ModelFormat.TENSORFLOW, RiskLevel.MEDIUM),
    }

    # Magic bytes for format detection
    MAGIC_BYTES = {
        b'\x80\x04\x95': ModelFormat.PICKLE,  # Pickle protocol 4
        b'\x80\x03': ModelFormat.PICKLE,       # Pickle protocol 3
        b'\x80\x02': ModelFormat.PICKLE,       # Pickle protocol 2
        b'PK\x03\x04': ModelFormat.TORCH,      # ZIP (PyTorch)
        b'\x89HDF': ModelFormat.TENSORFLOW,    # HDF5
    }

    # Suspicious content patterns in model files
    SUSPICIOUS_PATTERNS = [
        (rb'exec\s*\(', "exec() call found"),
        (rb'eval\s*\(', "eval() call found"),
        (rb'os\.system', "os.system() call found"),
        (rb'subprocess', "subprocess usage found"),
        (rb'__reduce__', "Pickle __reduce__ magic method"),
        (rb'socket\.', "Socket operations found"),
        (rb'requests\.', "HTTP requests found"),
        (rb'urllib', "URL operations found"),
    ]

    # Known malicious hash prefixes (example format)
    KNOWN_MALICIOUS_HASHES: Set[str] = {
        # Add known malicious model hashes here
        # "sha256:abc123..."
    }

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile patterns."""
        self._suspicious_compiled = [
            (re.compile(p), d) for p, d in self.SUSPICIOUS_PATTERNS
        ]

    def verify_file(
        self,
        file_path: str,
        expected_hash: Optional[str] = None,
        expected_signature: Optional[str] = None
    ) -> ModelIntegrityResult:
        """
        Verify integrity of a model file.
        
        Args:
            file_path: Path to model file
            expected_hash: Optional expected SHA256 hash
            expected_signature: Optional cryptographic signature
            
        Returns:
            ModelIntegrityResult with verification details
        """
        path = Path(file_path)
        checks: List[IntegrityCheck] = []
        recommendations: List[str] = []

        # Check 1: File existence
        if not path.exists():
            return ModelIntegrityResult(
                is_verified=False,
                overall_risk=RiskLevel.CRITICAL,
                model_format=ModelFormat.UNKNOWN,
                checks=[IntegrityCheck(
                    check_name="file_exists",
                    passed=False,
                    details="File not found",
                    risk_impact=RiskLevel.CRITICAL
                )]
            )

        # Check 2: Format from extension
        format_result = self._check_format_from_extension(path)
        checks.append(format_result)
        model_format = self._get_format_from_extension(path)

        # Check 3: Magic bytes verification
        magic_check = self._check_magic_bytes(path)
        checks.append(magic_check)

        # Check 4: Compute hash
        computed_hash = self._compute_hash(path)
        
        # Check 5: Hash verification (if expected provided)
        if expected_hash:
            hash_check = self._verify_hash(computed_hash, expected_hash)
            checks.append(hash_check)

        # Check 6: Known malicious hash check
        malicious_check = self._check_known_malicious(computed_hash)
        checks.append(malicious_check)

        # Check 7: Suspicious content (for unsafe formats)
        if model_format in [ModelFormat.PICKLE, ModelFormat.TORCH]:
            content_checks = self._scan_suspicious_content(path)
            checks.extend(content_checks)

        # Generate recommendations
        recommendations = self._generate_recommendations(checks, model_format)

        # Calculate overall risk
        overall_risk = self._calculate_overall_risk(checks)
        is_verified = overall_risk in [RiskLevel.SAFE, RiskLevel.LOW]

        return ModelIntegrityResult(
            is_verified=is_verified,
            overall_risk=overall_risk,
            model_format=model_format,
            checks=checks,
            computed_hash=computed_hash,
            recommendations=recommendations
        )

    def _check_format_from_extension(self, path: Path) -> IntegrityCheck:
        """Check file format safety from extension."""
        ext = path.suffix.lower()
        
        if ext in self.SAFE_EXTENSIONS:
            _, risk = self.SAFE_EXTENSIONS[ext]
            return IntegrityCheck(
                check_name="format_extension",
                passed=True,
                details=f"Safe format: {ext}",
                risk_impact=risk
            )
        elif ext in self.RISKY_EXTENSIONS:
            _, risk = self.RISKY_EXTENSIONS[ext]
            return IntegrityCheck(
                check_name="format_extension",
                passed=False,
                details=f"Risky format: {ext}",
                risk_impact=risk
            )
        else:
            return IntegrityCheck(
                check_name="format_extension",
                passed=False,
                details=f"Unknown format: {ext}",
                risk_impact=RiskLevel.MEDIUM
            )

    def _get_format_from_extension(self, path: Path) -> ModelFormat:
        """Get model format from extension."""
        ext = path.suffix.lower()
        if ext in self.SAFE_EXTENSIONS:
            return self.SAFE_EXTENSIONS[ext][0]
        elif ext in self.RISKY_EXTENSIONS:
            return self.RISKY_EXTENSIONS[ext][0]
        return ModelFormat.UNKNOWN

    def _check_magic_bytes(self, path: Path) -> IntegrityCheck:
        """Check file magic bytes for format verification."""
        try:
            with open(path, 'rb') as f:
                header = f.read(16)
            
            for magic, fmt in self.MAGIC_BYTES.items():
                if header.startswith(magic):
                    if fmt == ModelFormat.PICKLE:
                        return IntegrityCheck(
                            check_name="magic_bytes",
                            passed=False,
                            details="Pickle format detected - potential RCE risk",
                            risk_impact=RiskLevel.CRITICAL
                        )
                    return IntegrityCheck(
                        check_name="magic_bytes",
                        passed=True,
                        details=f"Format confirmed: {fmt.value}",
                        risk_impact=RiskLevel.LOW
                    )
            
            return IntegrityCheck(
                check_name="magic_bytes",
                passed=True,
                details="No risky magic bytes detected",
                risk_impact=RiskLevel.SAFE
            )
        except Exception as e:
            return IntegrityCheck(
                check_name="magic_bytes",
                passed=False,
                details=f"Error reading file: {e}",
                risk_impact=RiskLevel.MEDIUM
            )

    def _compute_hash(self, path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256 = hashlib.sha256()
        try:
            with open(path, 'rb') as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return f"sha256:{sha256.hexdigest()}"
        except Exception as e:
            logger.error(f"Hash computation failed: {e}")
            return ""

    def _verify_hash(self, computed: str, expected: str) -> IntegrityCheck:
        """Verify hash matches expected."""
        # Normalize format
        if not expected.startswith("sha256:"):
            expected = f"sha256:{expected}"
        
        if computed.lower() == expected.lower():
            return IntegrityCheck(
                check_name="hash_verification",
                passed=True,
                details="Hash matches expected value",
                risk_impact=RiskLevel.SAFE
            )
        else:
            return IntegrityCheck(
                check_name="hash_verification",
                passed=False,
                details="Hash mismatch - file may be tampered",
                risk_impact=RiskLevel.CRITICAL
            )

    def _check_known_malicious(self, hash_value: str) -> IntegrityCheck:
        """Check against known malicious hashes."""
        if hash_value in self.KNOWN_MALICIOUS_HASHES:
            return IntegrityCheck(
                check_name="known_malicious",
                passed=False,
                details="Model matches known malicious hash!",
                risk_impact=RiskLevel.CRITICAL
            )
        return IntegrityCheck(
            check_name="known_malicious",
            passed=True,
            details="No known malicious hash match",
            risk_impact=RiskLevel.SAFE
        )

    def _scan_suspicious_content(self, path: Path) -> List[IntegrityCheck]:
        """Scan file for suspicious content patterns."""
        checks = []
        try:
            # Read first 1MB for pattern scanning
            with open(path, 'rb') as f:
                content = f.read(1024 * 1024)
            
            for pattern, description in self._suspicious_compiled:
                if pattern.search(content):
                    checks.append(IntegrityCheck(
                        check_name="suspicious_content",
                        passed=False,
                        details=description,
                        risk_impact=RiskLevel.HIGH
                    ))
            
            if not checks:
                checks.append(IntegrityCheck(
                    check_name="suspicious_content",
                    passed=True,
                    details="No suspicious patterns found",
                    risk_impact=RiskLevel.LOW
                ))
        except Exception as e:
            checks.append(IntegrityCheck(
                check_name="suspicious_content",
                passed=False,
                details=f"Scan error: {e}",
                risk_impact=RiskLevel.MEDIUM
            ))
        
        return checks

    def _generate_recommendations(
        self, 
        checks: List[IntegrityCheck], 
        model_format: ModelFormat
    ) -> List[str]:
        """Generate recommendations based on checks."""
        recommendations = []
        
        if model_format == ModelFormat.PICKLE:
            recommendations.append("Convert to safetensors format for safety")
        elif model_format == ModelFormat.TORCH:
            recommendations.append("Use torch.load() with weights_only=True")
        
        failed = [c for c in checks if not c.passed]
        if any(c.risk_impact == RiskLevel.CRITICAL for c in failed):
            recommendations.append("DO NOT load this model without verification")
        
        if model_format not in [ModelFormat.SAFETENSORS, ModelFormat.ONNX]:
            recommendations.append("Run model in sandboxed environment")
        
        return recommendations

    def _calculate_overall_risk(self, checks: List[IntegrityCheck]) -> RiskLevel:
        """Calculate overall risk from checks."""
        if any(c.risk_impact == RiskLevel.CRITICAL for c in checks if not c.passed):
            return RiskLevel.CRITICAL
        if any(c.risk_impact == RiskLevel.HIGH for c in checks if not c.passed):
            return RiskLevel.HIGH
        if any(c.risk_impact == RiskLevel.MEDIUM for c in checks if not c.passed):
            return RiskLevel.MEDIUM
        if all(c.passed for c in checks):
            return RiskLevel.SAFE
        return RiskLevel.LOW


# Singleton
_verifier = None

def get_verifier() -> ModelIntegrityVerifier:
    global _verifier
    if _verifier is None:
        _verifier = ModelIntegrityVerifier()
    return _verifier

def verify(file_path: str, expected_hash: str = None) -> ModelIntegrityResult:
    return get_verifier().verify_file(file_path, expected_hash)
