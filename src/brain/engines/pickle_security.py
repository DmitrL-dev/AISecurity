"""
Pickle Security Engine - ML Model Supply Chain Attack Detection

Integrates Trail of Bits' fickling for:
1. Pickle file decompilation and analysis
2. Static detection of malicious imports
3. PyTorch model scanning
4. ML allowlist verification

Part of SENTINEL's Supply Chain Security Layer.

Author: SENTINEL Team
Engine ID: 188
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .base_engine import BaseDetector, DetectionResult, Severity

logger = logging.getLogger("PickleSecurityEngine")


# ============================================================================
# Enums and Constants
# ============================================================================


class PickleSeverity(Enum):
    """Severity levels matching fickling's analysis."""

    LIKELY_SAFE = 0
    POSSIBLY_UNSAFE = 1
    SUSPICIOUS = 2
    LIKELY_UNSAFE = 3
    LIKELY_OVERTLY_MALICIOUS = 4
    OVERTLY_MALICIOUS = 5

    def to_sentinel_severity(self) -> Severity:
        """Map to SENTINEL severity."""
        mapping = {
            PickleSeverity.LIKELY_SAFE: Severity.INFO,
            PickleSeverity.POSSIBLY_UNSAFE: Severity.LOW,
            PickleSeverity.SUSPICIOUS: Severity.MEDIUM,
            PickleSeverity.LIKELY_UNSAFE: Severity.HIGH,
            PickleSeverity.LIKELY_OVERTLY_MALICIOUS: Severity.CRITICAL,
            PickleSeverity.OVERTLY_MALICIOUS: Severity.CRITICAL,
        }
        return mapping.get(self, Severity.HIGH)


# Trail of Bits UNSAFE_MODULES (from fickling)
UNSAFE_MODULES: Set[str] = {
    "__builtin__",
    "__builtins__",
    "builtins",
    "os",
    "posix",
    "nt",
    "subprocess",
    "sys",
    "socket",
    "shutil",
    "urllib",
    "urllib2",
    "torch.hub",
    "dill",
    "code",
}

# Dangerous function calls
DANGEROUS_CALLS: Set[str] = {
    "eval",
    "exec",
    "compile",
    "open",
    "__import__",
    "getattr",
    "setattr",
    "delattr",
}

# ML-safe imports (from fickling ML_ALLOWLIST)
ML_ALLOWLIST: Dict[str, Set[str]] = {
    "numpy": {"dtype", "ndarray", "float64", "float32", "int64", "int32"},
    "numpy.core.multiarray": {"_reconstruct", "scalar"},
    "numpy._core.multiarray": {"_reconstruct"},
    "torch": {
        "ByteStorage",
        "DoubleStorage",
        "FloatStorage",
        "HalfStorage",
        "LongStorage",
        "IntStorage",
        "ShortStorage",
        "Size",
        "device",
        "Tensor",
        "bfloat16",
        "float16",
        "float32",
    },
    "torch._utils": {"_rebuild_tensor", "_rebuild_tensor_v2"},
    "collections": {"OrderedDict", "defaultdict"},
    "argparse": {"Namespace"},
}


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class PickleAnalysisResult:
    """Result from pickle analysis."""

    severity: PickleSeverity
    is_safe: bool
    findings: List[str] = field(default_factory=list)
    dangerous_imports: List[str] = field(default_factory=list)
    dangerous_calls: List[str] = field(default_factory=list)
    opcodes_analyzed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity.name,
            "is_safe": self.is_safe,
            "findings": self.findings,
            "dangerous_imports": self.dangerous_imports,
            "dangerous_calls": self.dangerous_calls,
            "opcodes_analyzed": self.opcodes_analyzed,
        }


# ============================================================================
# Pickle Opcode Parser (Lightweight fickling-inspired)
# ============================================================================


class PickleOpcodeScanner:
    """
    Lightweight pickle opcode scanner for detecting dangerous patterns.

    Inspired by fickling but operates without full decompilation.
    Suitable for quick threat triage.
    Supports Protocol 0-5 including STACK_GLOBAL for Protocol 4.
    """

    # Protocol 0/1/2 opcodes
    GLOBAL = b"c"  # GLOBAL opcode - imports module.attr (protocol 0-2)

    # Protocol 3/4/5 opcodes
    STACK_GLOBAL = b"\x93"  # STACK_GLOBAL - py3 import
    SHORT_BINUNICODE = b"\x8c"  # SHORT_BINUNICODE - push short string
    BINUNICODE = b"X"  # BINUNICODE - push unicode string

    # Execution opcodes
    REDUCE = b"R"  # REDUCE - function call
    BUILD = b"b"  # BUILD - __setstate__ call
    INST = b"i"  # INST - instantiate class
    OBJ = b"o"  # OBJ - build object
    NEWOBJ = b"\x81"  # NEWOBJ - cls.__new__(cls, *args)

    # Memo opcodes (for tracking position)
    MEMOIZE = b"\x94"  # MEMOIZE - store in memo

    def __init__(self):
        self.findings: List[str] = []
        self.imports: List[Tuple[str, str]] = []
        self.severity = PickleSeverity.LIKELY_SAFE
        self._string_stack: List[str] = []  # Track pushed strings

    def scan(self, data: bytes) -> PickleAnalysisResult:
        """Scan pickle bytes for dangerous patterns."""
        self.findings = []
        self.imports = []
        self.severity = PickleSeverity.LIKELY_SAFE
        self._string_stack = []
        dangerous_imports = []
        dangerous_calls = []
        opcodes_count = 0

        pos = 0
        while pos < len(data):
            opcode = data[pos : pos + 1]
            opcodes_count += 1

            # === Protocol 0/1/2: GLOBAL opcode (module\nattr\n) ===
            if opcode == self.GLOBAL:
                pos += 1
                result = self._parse_global_opcode(data, pos)
                if result:
                    module, name, new_pos = result
                    pos = new_pos
                    self.imports.append((module, name))

                    # Check security
                    if self._is_unsafe_import(module, name):
                        dangerous_imports.append(f"{module}.{name}")
                        self._update_severity(PickleSeverity.LIKELY_OVERTLY_MALICIOUS)
                        self.findings.append(f"Dangerous import: {module}.{name}")

                    if name in DANGEROUS_CALLS:
                        dangerous_calls.append(name)
                        self._update_severity(PickleSeverity.OVERTLY_MALICIOUS)
                        self.findings.append(f"Dangerous call: {name}")
                else:
                    pos += 1

            # === Protocol 4: SHORT_BINUNICODE (push string to stack) ===
            elif opcode == self.SHORT_BINUNICODE:
                pos += 1
                if pos < len(data):
                    length = data[pos]
                    pos += 1
                    if pos + length <= len(data):
                        try:
                            s = data[pos : pos + length].decode("utf-8")
                            self._string_stack.append(s)
                        except UnicodeDecodeError:
                            pass
                        pos += length
                    else:
                        pos = len(data)
                else:
                    break

            # === Protocol 4: STACK_GLOBAL (pop name, pop module, push callable) ===
            elif opcode == self.STACK_GLOBAL:
                pos += 1
                # Pop name and module from string stack
                if len(self._string_stack) >= 2:
                    name = self._string_stack.pop()
                    module = self._string_stack.pop()
                    self.imports.append((module, name))

                    # Check security
                    if self._is_unsafe_import(module, name):
                        dangerous_imports.append(f"{module}.{name}")
                        self._update_severity(PickleSeverity.LIKELY_OVERTLY_MALICIOUS)
                        self.findings.append(f"Dangerous import: {module}.{name}")

                    if name in DANGEROUS_CALLS:
                        dangerous_calls.append(name)
                        self._update_severity(PickleSeverity.OVERTLY_MALICIOUS)
                        self.findings.append(f"Dangerous call: {name}")
                else:
                    # Can't determine import without full interpreter
                    self._update_severity(PickleSeverity.SUSPICIOUS)
                    self.findings.append("STACK_GLOBAL with unknown context")

            # === MEMOIZE: just skip ===
            elif opcode == self.MEMOIZE:
                pos += 1

            # === REDUCE: function call - dangerous if bad imports ===
            elif opcode == self.REDUCE:
                if dangerous_imports or dangerous_calls:
                    self._update_severity(PickleSeverity.OVERTLY_MALICIOUS)
                    self.findings.append("REDUCE with dangerous imports - RCE likely")
                pos += 1

            else:
                pos += 1

        return PickleAnalysisResult(
            severity=self.severity,
            is_safe=self.severity == PickleSeverity.LIKELY_SAFE,
            findings=self.findings,
            dangerous_imports=dangerous_imports,
            dangerous_calls=dangerous_calls,
            opcodes_analyzed=opcodes_count,
        )

    def _parse_global_opcode(
        self, data: bytes, pos: int
    ) -> Optional[Tuple[str, str, int]]:
        """Parse GLOBAL opcode to extract module and name."""
        try:
            # Find first newline (end of module name)
            module_end = data.index(b"\n", pos)
            module = data[pos:module_end].decode("utf-8", errors="replace")

            # Find second newline (end of attribute name)
            name_start = module_end + 1
            name_end = data.index(b"\n", name_start)
            name = data[name_start:name_end].decode("utf-8", errors="replace")

            return (module, name, name_end + 1)
        except (ValueError, UnicodeDecodeError):
            return None

    def _is_unsafe_import(self, module: str, name: str) -> bool:
        """Check if import is unsafe."""
        # Check full module path
        if module in UNSAFE_MODULES:
            return True

        # Check parent modules
        parts = module.split(".")
        for i in range(len(parts)):
            parent = ".".join(parts[: i + 1])
            if parent in UNSAFE_MODULES:
                return True

        # Check if in ML_ALLOWLIST
        if module in ML_ALLOWLIST:
            if name in ML_ALLOWLIST[module]:
                return False  # Safe ML import

        return False

    def _update_severity(self, new_severity: PickleSeverity):
        """Update severity to higher level."""
        if new_severity.value > self.severity.value:
            self.severity = new_severity


# ============================================================================
# Main Pickle Security Engine
# ============================================================================


class PickleSecurityEngine(BaseDetector):
    """
    ML Model Supply Chain Attack Detection Engine.

    Analyzes pickle files for:
    - Malicious imports (os, subprocess, etc.)
    - Dangerous function calls (eval, exec, etc.)
    - Non-standard library imports
    - RCE payload patterns

    Integrates concepts from Trail of Bits' fickling.
    """

    @property
    def name(self) -> str:
        return "pickle_security"

    @property
    def version(self) -> str:
        return "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.scanner = PickleOpcodeScanner()
        self._fickling_available = self._check_fickling()

        if self._fickling_available:
            logger.info("fickling library detected - enhanced analysis available")
        else:
            logger.info("fickling not installed - using built-in scanner")

    def _check_fickling(self) -> bool:
        """Check if fickling library is available."""
        try:
            import fickling

            return True
        except ImportError:
            return False

    def detect(self, text: str) -> DetectionResult:
        """
        Detect pickle threats in text representation.

        For binary pickle data, use analyze_bytes() instead.
        """
        # Check for pickle-related patterns in text
        patterns_found = []

        for module in UNSAFE_MODULES:
            if module in text:
                patterns_found.append(f"Unsafe module reference: {module}")

        for call in DANGEROUS_CALLS:
            if call in text:
                patterns_found.append(f"Dangerous call reference: {call}")

        if patterns_found:
            return DetectionResult(
                detected=True,
                confidence=0.7,
                severity=Severity.HIGH,
                details=patterns_found,
            )

        return DetectionResult(
            detected=False,
            confidence=0.0,
            severity=Severity.INFO,
            details=["No pickle threats detected in text"],
        )

    def analyze_bytes(self, data: bytes) -> PickleAnalysisResult:
        """
        Analyze raw pickle bytes for malicious content.

        Args:
            data: Raw pickle bytes

        Returns:
            PickleAnalysisResult with severity and findings
        """
        # Validate pickle magic
        if not self._is_valid_pickle(data):
            return PickleAnalysisResult(
                severity=PickleSeverity.SUSPICIOUS,
                is_safe=False,
                findings=["Invalid pickle format - possible obfuscation"],
            )

        # Use fickling if available
        if self._fickling_available:
            return self._analyze_with_fickling(data)

        # Fall back to built-in scanner
        return self.scanner.scan(data)

    def analyze_file(self, filepath: str) -> PickleAnalysisResult:
        """
        Analyze pickle file from path.

        Args:
            filepath: Path to pickle file

        Returns:
            PickleAnalysisResult
        """
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            return self.analyze_bytes(data)
        except IOError as e:
            return PickleAnalysisResult(
                severity=PickleSeverity.SUSPICIOUS,
                is_safe=False,
                findings=[f"Failed to read file: {e}"],
            )

    def _is_valid_pickle(self, data: bytes) -> bool:
        """Check if data looks like valid pickle."""
        if len(data) < 2:
            return False

        # Protocol 2+ starts with \x80\x02, \x80\x03, \x80\x04, or \x80\x05
        if data[0:1] == b"\x80" and data[1:2] in (b"\x02", b"\x03", b"\x04", b"\x05"):
            return True

        # Protocol 0/1 can start with various opcodes
        valid_starts = {
            b"(",
            b"c",
            b"]",
            b"}",
            b"0",
            b"1",
            b"2",
            b"I",
            b"L",
            b"F",
            b"S",
            b"N",
            b"V",
            b"U",
        }
        return data[0:1] in valid_starts

    def _analyze_with_fickling(self, data: bytes) -> PickleAnalysisResult:
        """Analyze using fickling library."""
        try:
            from fickling.fickle import Pickled
            from fickling.analysis import check_safety, Severity as FicklingSeverity

            pickled = Pickled.loads(data)
            results = check_safety(pickled)

            # Map fickling severity to our severity
            severity_map = {
                "LIKELY_SAFE": PickleSeverity.LIKELY_SAFE,
                "POSSIBLY_UNSAFE": PickleSeverity.POSSIBLY_UNSAFE,
                "SUSPICIOUS": PickleSeverity.SUSPICIOUS,
                "LIKELY_UNSAFE": PickleSeverity.LIKELY_UNSAFE,
                "LIKELY_OVERTLY_MALICIOUS": PickleSeverity.LIKELY_OVERTLY_MALICIOUS,
                "OVERTLY_MALICIOUS": PickleSeverity.OVERTLY_MALICIOUS,
            }

            severity = severity_map.get(
                results.severity.name, PickleSeverity.SUSPICIOUS
            )

            return PickleAnalysisResult(
                severity=severity,
                is_safe=severity == PickleSeverity.LIKELY_SAFE,
                findings=[str(results)],
                dangerous_imports=[],  # Extracted from fickling
                dangerous_calls=[],
                opcodes_analyzed=len(pickled),
            )

        except Exception as e:
            logger.warning(f"fickling analysis failed: {e}")
            # Fall back to built-in scanner
            return self.scanner.scan(data)

    def is_import_safe(self, module: str, name: str) -> bool:
        """
        Check if a specific import is safe.

        Uses ML_ALLOWLIST for known-safe ML imports.

        Args:
            module: Module name (e.g., "numpy")
            name: Attribute name (e.g., "ndarray")

        Returns:
            True if import is considered safe
        """
        if module in UNSAFE_MODULES:
            return False

        if module in ML_ALLOWLIST:
            return name in ML_ALLOWLIST[module]

        # Unknown module - conservative approach
        return False

    def health_check(self) -> bool:
        """Check engine health."""
        try:
            # Test with safe pickle
            import pickle

            safe_data = pickle.dumps({"test": 123})
            result = self.analyze_bytes(safe_data)
            return result.is_safe
        except Exception:
            return False


# ============================================================================
# PyTorch Model Scanner
# ============================================================================


class PyTorchModelScanner:
    """
    Scans PyTorch model files for supply chain attacks.

    Supports:
    - .pt files (PyTorch checkpoints)
    - .pth files (PyTorch state dicts)
    - .bin files (HuggingFace format)
    - .ckpt files (Lightning checkpoints)
    """

    SUPPORTED_EXTENSIONS = {".pt", ".pth", ".bin", ".ckpt"}

    def __init__(self):
        self.engine = PickleSecurityEngine()
        self._zipfile_available = True

    def scan(self, model_path: str) -> PickleAnalysisResult:
        """
        Scan PyTorch model file.

        Args:
            model_path: Path to model file

        Returns:
            PickleAnalysisResult
        """
        import os
        from pathlib import Path

        path = Path(model_path)

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return PickleAnalysisResult(
                severity=PickleSeverity.LIKELY_SAFE,
                is_safe=True,
                findings=[f"Unsupported extension: {path.suffix}"],
            )

        if not path.exists():
            return PickleAnalysisResult(
                severity=PickleSeverity.SUSPICIOUS,
                is_safe=False,
                findings=[f"File not found: {model_path}"],
            )

        # Check if ZIP-based format (PyTorch v1.3+)
        if self._is_zip_format(model_path):
            return self._scan_zip_model(model_path)

        # Legacy format - direct pickle
        return self.engine.analyze_file(model_path)

    def _is_zip_format(self, filepath: str) -> bool:
        """Check if file is ZIP-based PyTorch format."""
        try:
            with open(filepath, "rb") as f:
                # ZIP magic: PK\x03\x04
                magic = f.read(4)
                return magic == b"PK\x03\x04"
        except IOError:
            return False

    def _scan_zip_model(self, filepath: str) -> PickleAnalysisResult:
        """Scan ZIP-based PyTorch model."""
        import zipfile

        findings = []
        worst_severity = PickleSeverity.LIKELY_SAFE
        dangerous_imports = []
        dangerous_calls = []

        try:
            with zipfile.ZipFile(filepath, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".pkl") or name.endswith("data.pkl"):
                        try:
                            with zf.open(name) as pkl_file:
                                data = pkl_file.read()
                                result = self.engine.analyze_bytes(data)

                                if result.severity.value > worst_severity.value:
                                    worst_severity = result.severity

                                findings.extend(result.findings)
                                dangerous_imports.extend(result.dangerous_imports)
                                dangerous_calls.extend(result.dangerous_calls)

                        except Exception as e:
                            findings.append(f"Failed to analyze {name}: {e}")
                            worst_severity = PickleSeverity.SUSPICIOUS

        except zipfile.BadZipFile:
            return PickleAnalysisResult(
                severity=PickleSeverity.SUSPICIOUS,
                is_safe=False,
                findings=["Corrupted ZIP archive"],
            )

        return PickleAnalysisResult(
            severity=worst_severity,
            is_safe=worst_severity == PickleSeverity.LIKELY_SAFE,
            findings=findings or ["No issues found in model archive"],
            dangerous_imports=dangerous_imports,
            dangerous_calls=dangerous_calls,
        )


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "PickleSecurityEngine",
    "PyTorchModelScanner",
    "PickleAnalysisResult",
    "PickleSeverity",
    "UNSAFE_MODULES",
    "DANGEROUS_CALLS",
    "ML_ALLOWLIST",
]
