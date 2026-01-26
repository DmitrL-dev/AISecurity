# Tool Security

> **Lesson:** 04.3.1 - Securing Agent Tools  
> **Time:** 40 minutes  
> **Prerequisites:** Agent Loops basics

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Identify tool-related security risks
2. Implement secure tool interfaces
3. Apply principle of least privilege to tools
4. Build defense-in-depth for tool execution

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
    
    # Audit settings
    log_inputs: bool = True
    log_outputs: bool = True
    require_reason: bool = False

class SecureToolRegistry:
    """Registry with security enforcement."""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.call_counts: Dict[str, List[float]] = {}
    
    def register(self, tool: ToolDefinition):
        """Register a tool."""
        self.tools[tool.name] = tool
        self.call_counts[tool.name] = []
    
    def get_tool(self, name: str) -> ToolDefinition:
        """Get tool or raise error."""
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        return self.tools[name]
```

---

### Input Validation

```python
import jsonschema
from pathlib import Path

class ToolInputValidator:
    """Validate and sanitize tool inputs."""
    
    def __init__(self):
        self.path_sanitizer = PathSanitizer()
        self.string_sanitizer = StringSanitizer()
    
    def validate(
        self, 
        tool: ToolDefinition, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and sanitize arguments."""
        
        # Schema validation
        try:
            jsonschema.validate(arguments, tool.input_schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Invalid arguments: {e.message}")
        
        # Apply sanitizers
        sanitized = {}
        for key, value in arguments.items():
            if key in tool.sanitizers:
                sanitized[key] = tool.sanitizers[key](value)
            else:
                sanitized[key] = self._default_sanitize(key, value)
        
        return sanitized
    
    def _default_sanitize(self, key: str, value: Any) -> Any:
        """Apply default sanitization based on key name."""
        
        if isinstance(value, str):
            # Path-like arguments
            if any(x in key.lower() for x in ["path", "file", "dir", "folder"]):
                return self.path_sanitizer.sanitize(value)
            
            # General string
            return self.string_sanitizer.sanitize(value)
        
        return value

class PathSanitizer:
    """Sanitize file paths to prevent traversal."""
    
    def __init__(self, allowed_dirs: List[str] = None):
        self.allowed_dirs = allowed_dirs or ["/project", "/tmp"]
    
    def sanitize(self, path: str) -> str:
        """Sanitize path and verify it's allowed."""
        
        # Resolve to absolute path
        resolved = Path(path).resolve()
        
        # Check for traversal
        if ".." in str(path):
            raise ValueError("Path traversal not allowed")
        
        # Check allowed directories
        allowed = any(
            str(resolved).startswith(d) 
            for d in self.allowed_dirs
        )
        
        if not allowed:
            raise ValueError(f"Path not in allowed directories: {resolved}")
        
        return str(resolved)
```

---

### Permission Enforcement

```python
class ToolPermissionEnforcer:
    """Enforce permissions before tool execution."""
    
    def __init__(self, permission_manager):
        self.permissions = permission_manager
    
    def check(
        self, 
        tool: ToolDefinition,
        agent_context: Dict[str, Any],
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check all permissions for tool execution."""
        
        results = {
            "allowed": True,
            "checks": []
        }
        
        # Check required permissions
        for perm in tool.required_permissions:
            check = self.permissions.check(
                agent_context.get("agent_id"),
                perm,
                self._get_resource(arguments)
            )
            
            results["checks"].append({
                "permission": perm,
                "allowed": check["allowed"],
                "reason": check.get("reason")
            })
            
            if not check["allowed"]:
                results["allowed"] = False
        
        # Risk-based checks
        if tool.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            results["requires_approval"] = True
        
        return results
    
    def _get_resource(self, arguments: Dict[str, Any]) -> str:
        """Extract resource identifier from arguments."""
        
        # Common resource argument names
        for key in ["path", "file", "resource", "target", "url"]:
            if key in arguments:
                return arguments[key]
        
        return "*"
```

---

### Rate Limiting

```python
from datetime import datetime, timedelta
from collections import deque

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
        
        # Check limit
        current_count = len(self.call_history[key])
        
        if current_count >= tool.rate_limit:
            return {
                "allowed": False,
                "reason": f"Rate limit exceeded ({tool.rate_limit}/min)",
                "retry_after": 60 - (now - self.call_history[key][0]).seconds
            }
        
        # Record call
        self.call_history[key].append(now)
        
        return {"allowed": True, "calls_remaining": tool.rate_limit - current_count - 1}
```

---

### Secure Execution

```python
import asyncio

class SecureToolExecutor:
    """Execute tools with security controls."""
    
    def __init__(
        self,
        registry: SecureToolRegistry,
        validator: ToolInputValidator,
        permission_enforcer: ToolPermissionEnforcer,
        rate_limiter: ToolRateLimiter
    ):
        self.registry = registry
        self.validator = validator
        self.permissions = permission_enforcer
        self.rate_limiter = rate_limiter
        self.audit_log = []
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool with all security checks."""
        
        execution_id = self._generate_id()
        start_time = datetime.utcnow()
        
        try:
            # Get tool
            tool = self.registry.get_tool(tool_name)
            
            # Rate limiting
            rate_check = self.rate_limiter.check(tool, agent_context["agent_id"])
            if not rate_check["allowed"]:
                return self._error_response(rate_check["reason"], execution_id)
            
            # Permission check
            perm_check = self.permissions.check(tool, agent_context, arguments)
            if not perm_check["allowed"]:
                return self._error_response("Permission denied", execution_id)
            
            # Validate and sanitize inputs
            safe_args = self.validator.validate(tool, arguments)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self._run_tool(tool, safe_args),
                timeout=tool.timeout_seconds
            )
            
            # Truncate output if needed
            if len(str(result)) > tool.max_output_size:
                result = str(result)[:tool.max_output_size] + "... [truncated]"
            
            # Audit log
            self._log_execution(
                execution_id, tool, safe_args, result, 
                agent_context, start_time, success=True
            )
            
            return {"success": True, "result": result, "execution_id": execution_id}
            
        except asyncio.TimeoutError:
            return self._error_response(f"Tool timed out after {tool.timeout_seconds}s", execution_id)
        except Exception as e:
            self._log_execution(
                execution_id, tool, arguments, str(e),
                agent_context, start_time, success=False
            )
            return self._error_response(str(e), execution_id)
    
    async def _run_tool(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> Any:
        """Run the tool function."""
        if asyncio.iscoroutinefunction(tool.func):
            return await tool.func(**arguments)
        else:
            return tool.func(**arguments)
    
    def _log_execution(
        self,
        execution_id: str,
        tool: ToolDefinition,
        arguments: Dict[str, Any],
        result: Any,
        context: Dict[str, Any],
        start_time: datetime,
        success: bool
    ):
        """Log tool execution for audit."""
        
        entry = {
            "execution_id": execution_id,
            "timestamp": start_time.isoformat(),
            "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
            "tool_name": tool.name,
            "risk_level": tool.risk_level.value,
            "agent_id": context.get("agent_id"),
            "session_id": context.get("session_id"),
            "success": success
        }
        
        if tool.log_inputs:
            entry["arguments"] = self._redact_sensitive(arguments)
        
        if tool.log_outputs:
            entry["result_preview"] = str(result)[:500]
        
        self.audit_log.append(entry)
```

---

## Example Secure Tools

```python
# Secure file read tool
file_read_tool = ToolDefinition(
    name="read_file",
    description="Read contents of a file",
    func=lambda path: open(path).read(),
    risk_level=RiskLevel.MEDIUM,
    required_permissions=["file:read"],
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "maxLength": 500}
        },
        "required": ["path"]
    },
    sanitizers={"path": PathSanitizer(["/project"]).sanitize},
    max_output_size=50000,
    timeout_seconds=10,
    rate_limit=30
)

# Secure web request tool
web_request_tool = ToolDefinition(
    name="web_request",
    description="Make HTTP request to allowed URLs",
    func=make_request,
    risk_level=RiskLevel.MEDIUM,
    required_permissions=["network:request"],
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "format": "uri"},
            "method": {"type": "string", "enum": ["GET", "HEAD"]}
        },
        "required": ["url"]
    },
    sanitizers={"url": URLValidator(allowed_domains).validate},
    max_output_size=100000,
    timeout_seconds=30,
    rate_limit=10
)
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
    # Automatically secured
    with open(path, 'w') as f:
        f.write(content)
```

---

## Key Takeaways

1. **Define security metadata** - Risk level, permissions
2. **Validate all inputs** - Schema + custom sanitization
3. **Enforce permissions** - Check before execution
4. **Rate limit aggressively** - Prevent abuse
5. **Audit everything** - Full execution logs

---

*AI Security Academy | Lesson 04.3.1*
