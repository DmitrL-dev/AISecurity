# Tool Security

> **Урок:** 04.3.1 - Securing Agent Tools  
> **Время:** 40 минут  
> **Prerequisites:** Agent Loops basics

---

## Цели обучения

После завершения этого урока вы сможете:

1. Идентифицировать tool-related security risks
2. Реализовать secure tool interfaces
3. Применять principle of least privilege to tools
4. Строить defense-in-depth for tool execution

---

## Tool Attack Surface

```
Agent Request → Tool Interface → Validation → Execution → Output
     ↓              ↓              ↓            ↓          ↓
 Injection      Bypass        Exploit      Abuse      Leak
```

| Risk | Example |
|------|---------|
| **Argument Injection** | `file_read("../../../../etc/passwd")` |
| **Permission Bypass** | Claiming admin role to access restricted tools |
| **Resource Abuse** | Requesting gigabyte file reads |
| **Chained Exploitation** | Using one tool to compromise another |

---

## Secure Tool Design

### Tool Definition Framework

```python
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List
from enum import Enum

class RiskLevel(Enum):
    LOW = "low"         # Read-only, non-sensitive
    MEDIUM = "medium"   # Write access, limited scope
    HIGH = "high"       # System access, sensitive data
    CRITICAL = "critical"  # Irreversible, dangerous

@dataclass
class ToolDefinition:
    """Secure tool definition with metadata."""
    
    name: str
    description: str
    func: Callable
    
    # Security metadata
    risk_level: RiskLevel
    required_permissions: List[str]
    
    # Input validation
    input_schema: Dict[str, Any]
    sanitizers: Dict[str, Callable] = field(default_factory=dict)
    
    # Execution constraints
    max_output_size: int = 10000
    timeout_seconds: int = 30
    rate_limit: int = 10  # calls per minute
```

---

### Input Validation

```python
class ToolInputValidator:
    """Validate and sanitize tool inputs."""
    
    def validate(
        self, 
        tool: ToolDefinition, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and sanitize arguments."""
        
        # Schema validation
        jsonschema.validate(arguments, tool.input_schema)
        
        # Apply sanitizers
        sanitized = {}
        for key, value in arguments.items():
            if key in tool.sanitizers:
                sanitized[key] = tool.sanitizers[key](value)
            else:
                sanitized[key] = self._default_sanitize(key, value)
        
        return sanitized

class PathSanitizer:
    """Sanitize file paths to prevent traversal."""
    
    def __init__(self, allowed_dirs: List[str] = None):
        self.allowed_dirs = allowed_dirs or ["/project", "/tmp"]
    
    def sanitize(self, path: str) -> str:
        """Sanitize path and verify it's allowed."""
        
        resolved = Path(path).resolve()
        
        if ".." in str(path):
            raise ValueError("Path traversal not allowed")
        
        allowed = any(
            str(resolved).startswith(d) 
            for d in self.allowed_dirs
        )
        
        if not allowed:
            raise ValueError(f"Path not in allowed directories")
        
        return str(resolved)
```

---

### Rate Limiting

```python
class ToolRateLimiter:
    """Rate limiting for tool calls."""
    
    def __init__(self):
        self.call_history: Dict[str, deque] = {}
    
    def check(
        self, 
        tool: ToolDefinition,
        agent_id: str
    ) -> Dict[str, Any]:
        """Check if call is within rate limits."""
        
        key = f"{agent_id}:{tool.name}"
        now = datetime.utcnow()
        window = timedelta(minutes=1)
        
        if key not in self.call_history:
            self.call_history[key] = deque()
        
        # Remove old entries
        while self.call_history[key]:
            if now - self.call_history[key][0] > window:
                self.call_history[key].popleft()
            else:
                break
        
        current_count = len(self.call_history[key])
        
        if current_count >= tool.rate_limit:
            return {
                "allowed": False,
                "reason": f"Rate limit exceeded ({tool.rate_limit}/min)"
            }
        
        self.call_history[key].append(now)
        return {"allowed": True}
```

---

## SENTINEL Integration

```python
from sentinel import configure, ToolGuard

configure(
    tool_security=True,
    input_validation=True,
    permission_enforcement=True
)

tool_guard = ToolGuard(
    rate_limiting=True,
    audit_logging=True,
    sandbox_execution=True
)

@tool_guard.secure(
    risk_level="high",
    permissions=["file:write"]
)
def write_file(path: str, content: str):
    with open(path, 'w') as f:
        f.write(content)
```

---

## Ключевые выводы

1. **Define security metadata** - Risk level, permissions
2. **Validate all inputs** - Schema + custom sanitization
3. **Enforce permissions** - Check before execution
4. **Rate limit aggressively** - Prevent abuse
5. **Audit everything** - Full execution logs

---

*AI Security Academy | Урок 04.3.1*
