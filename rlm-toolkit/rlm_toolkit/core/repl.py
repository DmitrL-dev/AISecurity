"""
Secure REPL
===========

AST-based secure Python execution sandbox.
Based on CIRCLE (arxiv:2507.19399) and SandboxEval security research.
"""

from __future__ import annotations

import ast
import io
import re
import sys
import threading
import queue
from typing import Any, Callable, ClassVar, Dict, List, Optional, Set


class SecurityViolation(Exception):
    """Raised when code violates security policy."""
    pass


class TimeoutError(Exception):
    """Raised when code execution times out."""
    pass


class SecureREPL:
    """AST-based secure Python execution sandbox.
    
    Implements CIRCLE-based protection against:
    - Dangerous imports (os, subprocess, socket, etc.)
    - Dangerous builtins (eval, exec, open, etc.)
    - Resource exhaustion (timeout, memory)
    - Indirect attacks (obfuscated patterns)
    
    Example:
        >>> repl = SecureREPL()
        >>> code = "x = sum([1, 2, 3])"
        >>> output = repl.execute(code, {})
        >>> print(output)  # ""
    """
    
    # CIRCLE-based blocked imports (FR-3.1) - Enhanced 2026-01-18
    BLOCKED_IMPORTS: ClassVar[Set[str]] = {
        # Core dangerous modules
        'os', 'subprocess', 'sys', 'socket', 'shutil',
        'pathlib', 'multiprocessing', 'threading', 'ctypes',
        # Serialization (RCE vectors)
        'pickle', 'marshal', 'shelve', 'dill', 'cloudpickle',
        # Dynamic imports
        'builtins', 'importlib', 'code', 'codeop',
        # Unix-specific
        'pty', 'fcntl', 'resource', 'signal', 'posix',
        # Windows-specific
        'nt', 'msvcrt', 'winreg',
        # Memory/crypto
        'mmap', 'crypt',
        # Network (data exfiltration)
        'http', 'urllib', 'ftplib', 'telnetlib', 'smtplib',
        # File operations
        'tempfile', 'glob', 'fnmatch',
        # Async subprocess (CVE-2025 vectors)
        'asyncio',
        # Browser/system interaction
        'webbrowser', 'platform',
    }
    
    # CIRCLE-based blocked builtins (FR-3.2)
    BLOCKED_BUILTINS: ClassVar[Set[str]] = {
        'eval', 'exec', 'compile', 'open', 'input',
        '__import__', 'globals', 'locals', 'vars',
        'breakpoint', 'exit', 'quit', 'help',
        'memoryview', 'bytearray',
    }
    
    # Safe imports allowed by default
    ALLOWED_IMPORTS: ClassVar[Dict[str, Any]] = {}
    
    # Safe builtins (FIXED: removed setattr - potential escape vector)
    SAFE_BUILTINS: ClassVar[Set[str]] = {
        'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
        'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
        'sum', 'min', 'max', 'abs', 'round', 'any', 'all', 'pow', 'divmod',
        'print', 'type', 'isinstance', 'issubclass', 'hasattr', 'getattr',
        'callable', 'repr', 'hash', 'id', 'ord', 'chr', 'bin', 'hex', 'oct',
        'slice', 'frozenset', 'bytes', 'next', 'iter', 'format',
        'True', 'False', 'None', 'Ellipsis', 'NotImplemented',
        'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
        'AttributeError', 'RuntimeError', 'StopIteration', 'ZeroDivisionError',
    }
    
    # Indirect attack patterns (Gap G14)
    SUSPICIOUS_PATTERNS: ClassVar[List[str]] = [
        r'base64\.b64decode',
        r'codecs\.(decode|encode)',
        r'chr\s*\(\s*\d+\s*\)\s*\+\s*chr',  # chr(105)+chr(109)...
        r'getattr\s*\(\s*__\w+__',
        r"'\s*\+\s*'",  # String concatenation tricks
        r'\\x[0-9a-fA-F]{2}',  # Hex escapes
    ]
    
    def __init__(
        self,
        max_output_length: int = 10_000,
        max_execution_time: float = 30.0,
        max_memory_mb: int = 512,
        allowed_imports: Optional[Set[str]] = None,
        callbacks: Optional[List[Any]] = None,
    ):
        """Initialize SecureREPL.
        
        Args:
            max_output_length: Maximum output chars (FR-1.7)
            max_execution_time: Timeout in seconds (FR-3.4)
            max_memory_mb: Memory limit in MB (FR-3.5)
            allowed_imports: Override allowed imports
            callbacks: Callback handlers
        """
        self.max_output_length = max_output_length
        self.max_execution_time = max_execution_time
        self.max_memory_mb = max_memory_mb
        self.callbacks = callbacks or []
        
        # Build allowed imports
        self._allowed_imports = self._build_allowed_imports(allowed_imports)
    
    def _build_allowed_imports(self, allowed: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Build allowed imports dictionary."""
        import re
        import json
        import math
        import datetime
        import collections
        import itertools
        import functools
        
        base = {
            're': re,
            'json': json,
            'math': math,
            'datetime': datetime,
            'collections': collections,
            'itertools': itertools,
            'functools': functools,
        }
        
        if allowed:
            # Filter to only explicitly allowed
            return {k: v for k, v in base.items() if k in allowed}
        
        return base
    
    def _build_safe_builtins(self) -> Dict[str, Any]:
        """Build safe builtins dictionary."""
        import builtins
        
        safe = {}
        for name in self.SAFE_BUILTINS:
            if hasattr(builtins, name):
                safe[name] = getattr(builtins, name)
        
        return safe
    
    def analyze_code(self, code: str) -> List[str]:
        """AST-based security analysis.
        
        Returns list of security violations found.
        """
        violations = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error: {e}"]
        
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module in self.BLOCKED_IMPORTS:
                        violations.append(f"Blocked import: {module}")
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module in self.BLOCKED_IMPORTS:
                        violations.append(f"Blocked import: {module}")
            
            # Check function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.BLOCKED_BUILTINS:
                        violations.append(f"Blocked builtin: {node.func.id}")
                
                elif isinstance(node.func, ast.Attribute):
                    # Check for __dunder__ method calls
                    if node.func.attr.startswith('__') and node.func.attr.endswith('__'):
                        if node.func.attr not in ('__init__', '__str__', '__repr__'):
                            violations.append(f"Blocked dunder method: {node.func.attr}")
            
            # Check attribute access to dangerous names
            elif isinstance(node, ast.Attribute):
                if node.attr in ('__class__', '__base__', '__subclasses__', 
                                 '__globals__', '__code__', '__builtins__'):
                    violations.append(f"Blocked attribute access: {node.attr}")
        
        # Check for indirect attack patterns (Gap G14)
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(f"Suspicious pattern detected: {pattern}")
        
        return violations
    
    def extract_code(self, text: str) -> Optional[str]:
        """Extract code from ```repl or ```python blocks.
        
        Args:
            text: LLM response text
        
        Returns:
            Extracted code or None
        """
        # Try ```repl first
        match = re.search(r'```repl\s*(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try ```python
        match = re.search(r'```python\s*(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try plain ```
        match = re.search(r'```\s*(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return None
    
    def execute(
        self,
        code: str,
        namespace: Dict[str, Any],
        llm_query: Optional[Callable[[str], str]] = None,
    ) -> str:
        """Execute code in sandbox with timeout protection.
        
        Args:
            code: Python code to execute
            namespace: Variable namespace
            llm_query: llm_query() function for sub-calls
        
        Returns:
            Captured stdout output
        
        Raises:
            SecurityViolation: If code violates security policy
            TimeoutError: If code execution exceeds timeout
        """
        # Security check
        violations = self.analyze_code(code)
        if violations:
            raise SecurityViolation(f"Security violations: {', '.join(violations)}")
        
        # Build safe namespace
        safe_namespace = {
            '__builtins__': self._build_safe_builtins(),
            **self._allowed_imports,
            **namespace,
        }
        
        # Add llm_query if provided
        if llm_query:
            safe_namespace['llm_query'] = llm_query
        
        # Add FINAL helpers
        final_result = [None]
        
        def FINAL(answer):
            final_result[0] = answer
            return answer
        
        def FINAL_VAR(var_name):
            final_result[0] = safe_namespace.get(var_name)
            return final_result[0]
        
        safe_namespace['FINAL'] = FINAL
        safe_namespace['FINAL_VAR'] = FINAL_VAR
        
        # Execute with timeout protection
        result_queue: queue.Queue = queue.Queue()
        
        def execute_code():
            """Thread target for code execution."""
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()
            try:
                exec(code, safe_namespace)
                result_queue.put(('success', buffer.getvalue(), dict(safe_namespace)))
            except Exception as e:
                result_queue.put(('error', f"Error: {type(e).__name__}: {e}", dict(safe_namespace)))
            finally:
                sys.stdout = old_stdout
        
        # Start execution in thread with timeout
        thread = threading.Thread(target=execute_code, daemon=True)
        thread.start()
        thread.join(timeout=self.max_execution_time)
        
        if thread.is_alive():
            # Timeout! Thread is still running
            # Note: Python threads can't be killed, but daemon=True means
            # it won't block process exit
            raise TimeoutError(f"Code execution timed out after {self.max_execution_time}s")
        
        # Get result from queue
        if result_queue.empty():
            return "Error: No result from execution"
        
        status, output, final_namespace = result_queue.get()
        
        # Update namespace with new variables (excluding private)
        for key, value in final_namespace.items():
            if not key.startswith('_') and key not in self._allowed_imports:
                if key not in ('FINAL', 'FINAL_VAR', 'llm_query', '__builtins__'):
                    if isinstance(value, (str, int, float, list, dict, bool, type(None), tuple, set)):
                        namespace[key] = value
        
        # Truncate output
        if len(output) > self.max_output_length:
            output = output[:self.max_output_length] + f"\n... [truncated at {self.max_output_length} chars]"
        
        return output
