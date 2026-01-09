# Design: Sandbox Monitor Engine

## Архитектура

Новый engine в `src/brain/engines/synced/` для детекции Python sandbox escape.

---

## Структура файла

```
src/brain/engines/synced/sandbox_monitor.py
```

## Класс SandboxMonitor

```python
class SandboxMonitor(BaseEngine):
    """
    Detects Python sandbox escape techniques.
    OWASP: ASI05 - Unexpected Code Execution
    """
    
    ESCAPE_PATTERNS = {
        'os_system': [
            r'\bos\.system\s*\(',
            r'\bos\.popen\s*\(',
            r'\bos\.exec[vl]p?\s*\(',
        ],
        'subprocess': [
            r'\bsubprocess\.(Popen|call|run|check_output)\s*\(',
        ],
        'dynamic_exec': [
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'\bcompile\s*\(',
            r'\b__import__\s*\(',
        ],
        'builtins_access': [
            r'__builtins__',
            r'__globals__',
            r'__subclasses__\s*\(\s*\)',
            r'__mro__',
            r'__bases__',
        ],
        'sensitive_files': [
            r'open\s*\([^)]*(/etc/passwd|/etc/shadow)',
            r'open\s*\([^)]*\.ssh',
            r'open\s*\([^)]*\.aws',
        ],
        'obfuscation': [
            r'base64\.b64decode\s*\(',
            r'bytes\.fromhex\s*\(',
            r'codecs\.decode\s*\(',
        ],
    }
    
    SEVERITY_MAP = {
        'os_system': 'critical',
        'subprocess': 'critical', 
        'dynamic_exec': 'critical',
        'builtins_access': 'high',
        'sensitive_files': 'medium',
        'obfuscation': 'low',
    }
```

---

## Интеграция

### SyncedAttackDetector

Добавить в `synced_detectors.py`:

```python
from .sandbox_monitor import SandboxMonitor

SYNCED_ENGINES = [
    # ... existing engines ...
    SandboxMonitor,
]
```

---

## API

```python
def analyze(self, text: str) -> AnalysisResult:
    """
    Analyze code for sandbox escape patterns.
    
    Returns:
        AnalysisResult with:
        - detected: bool
        - severity: str (critical/high/medium/low)
        - patterns: List[str] matched patterns
        - recommendations: List[str]
    """
```

---

## Тестирование

```python
# tests/test_sandbox_monitor.py

def test_os_system_detection():
    code = "os.system('whoami')"
    result = engine.analyze(code)
    assert result.detected == True
    assert result.severity == 'critical'

def test_builtins_escape():
    code = "().__class__.__bases__[0].__subclasses__()"
    result = engine.analyze(code)
    assert result.detected == True
    assert result.severity == 'high'

def test_safe_code():
    code = "print('hello world')"
    result = engine.analyze(code)
    assert result.detected == False
```

---

## Риски

| Риск | Митигация |
|------|-----------|
| False positives на legitimate subprocess | Context analysis, whitelist |
| Obfuscated patterns | Base64 decode before analysis |
| Runtime-only escapes | Static analysis limitation (document) |
