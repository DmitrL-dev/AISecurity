"""Unit tests for SecureREPL."""

import pytest
from rlm_toolkit.core.repl import SecureREPL, SecurityViolation, TimeoutError as REPLTimeoutError


class TestSecureREPLBasics:
    """Basic REPL functionality tests."""
    
    def test_simple_expression(self):
        """Test simple expression evaluation."""
        repl = SecureREPL()
        ns = {}
        result = repl.execute("print(1 + 2)", ns)
        assert "3" in result
    
    def test_variable_assignment(self):
        """Test variable assignment and retrieval."""
        repl = SecureREPL()
        ns = {}
        repl.execute("x = 42", ns)
        result = repl.execute("print(x)", ns)
        assert "42" in result
    
    def test_multiline_code(self):
        """Test multiline code execution."""
        repl = SecureREPL()
        ns = {}
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
result = factorial(5)
print(result)
"""
        result = repl.execute(code, ns)
        assert "120" in result
    
    def test_list_operations(self):
        """Test built-in list operations."""
        repl = SecureREPL()
        ns = {}
        code = """
numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
print(f"Sum: {total}")
"""
        result = repl.execute(code, ns)
        assert "Sum: 15" in result


class TestSecureREPLSecurity:
    """Security-related tests."""
    
    @pytest.mark.security
    def test_blocked_import_os(self):
        """Test that os import is blocked."""
        repl = SecureREPL()
        ns = {}
        with pytest.raises(SecurityViolation):
            repl.execute("import os", ns)
    
    @pytest.mark.security
    def test_blocked_import_subprocess(self):
        """Test that subprocess import is blocked."""
        repl = SecureREPL()
        ns = {}
        with pytest.raises(SecurityViolation):
            repl.execute("import subprocess", ns)
    
    @pytest.mark.security
    def test_blocked_import_socket(self):
        """Test that socket import is blocked."""
        repl = SecureREPL()
        ns = {}
        with pytest.raises(SecurityViolation):
            repl.execute("import socket", ns)
    
    @pytest.mark.security
    def test_blocked_dunder_import(self):
        """Test that __import__ is blocked."""
        repl = SecureREPL()
        ns = {}
        with pytest.raises(SecurityViolation):
            repl.execute("__import__('os')", ns)
    
    @pytest.mark.security
    def test_blocked_eval_with_import(self):
        """Test that eval containing import is blocked."""
        repl = SecureREPL()
        ns = {}
        with pytest.raises(SecurityViolation):
            repl.execute("eval('__import__(\"os\")')", ns)
    
    @pytest.mark.security
    def test_blocked_exec_with_import(self):
        """Test that exec containing import is blocked."""
        repl = SecureREPL()
        ns = {}
        with pytest.raises(SecurityViolation):
            repl.execute("exec('import os')", ns)
    
    @pytest.mark.security
    def test_blocked_getattr_builtins(self):
        """Test that getattr on builtins is blocked."""
        repl = SecureREPL()
        ns = {}
        with pytest.raises(SecurityViolation):
            repl.execute("getattr(__builtins__, '__import__')", ns)


class TestSecureREPLTimeout:
    """Timeout tests."""
    
    @pytest.mark.slow
    def test_infinite_loop_timeout(self):
        """Test that infinite loops are terminated."""
        repl = SecureREPL()
        repl.max_execution_time = 1.0  # Use correct attribute
        ns = {}
        # This should raise TimeoutError
        with pytest.raises(REPLTimeoutError):
            repl.execute("while True: pass", ns)

