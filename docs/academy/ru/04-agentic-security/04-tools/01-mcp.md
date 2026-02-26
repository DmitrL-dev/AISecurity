# MCP Протокол Безопасность

> **Урок:** 04.4.1 - Model Context Протокол  
> **Время:** 45 минут  
> **Пререквизиты:** Агентic Безопасность basics

---

## Цели обучения

К концу этого урока, you will be able to:

1. Understand MCP architecture and security model
2. Identify MCP-specific vulnerabilities
3. Implement secure MCP server practices
4. Audit MCP integrations for security issues

---

## What is MCP?

Model Context Протокол (MCP) is Anthropic's open standard for connecting AI models to external tools and data sources:

| Component | Role |
|-----------|------|
| **MCP Host** | The AI application (e.g., Claude Desktop) |
| **MCP Client** | Протокол handler in the host |
| **MCP Server** | External tool/data provider |
| **Resources** | Read-only data sources |
| **Инструментs** | Executable functions |
| **Prompts** | Reusable prompt templates |

---

## MCP Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP Host                              │
│  ┌─────────────────┐                                        │
│  │   AI Model      │                                        │
│  └────────┬────────┘                                        │
│           │                                                  │
│  ┌────────▼────────┐                                        │
│  │   MCP Client    │                                        │
│  └────────┬────────┘                                        │
└───────────┼─────────────────────────────────────────────────┘
            │ JSON-RPC over stdio/HTTP
            │
┌───────────▼─────────────┐    ┌───────────────────────────┐
│     MCP Server A        │    │     MCP Server B          │
│  ┌─────────────────┐   │    │  ┌─────────────────┐      │
│  │ Инструментs:          │   │    │  │ Resources:      │      │
│  │  - read_file    │   │    │  │  - documents    │      │
│  │  - write_file   │   │    │  │  - database     │      │
│  │  - execute_cmd  │   │    │  │                 │      │
│  └─────────────────┘   │    │  └─────────────────┘      │
└─────────────────────────┘    └───────────────────────────┘
```

---

## Безопасность Vulnerabilities

### 1. Инструмент Injection Attacks

Malicious input causes unintended tool execution:

```python
# Vulnerable MCP server
class VulnerableFileServer:
    @mcp.tool()
    async def read_file(self, path: str) -> str:
        """Read file at given path."""
        return open(path).read()  # No validation!

# Attack via AI chat:
# User: "Read the file at ../../../etc/passwd"
# AI calls read_file(path="../../../etc/passwd")
# Sensitive file exposed!
```

**Secure Implementation:**

```python
from pathlib import Path
import os

class SecureFileServer:
    def __init__(self, allowed_directory: str):
        self.root = Path(allowed_directory).resolve()
    
    @mcp.tool()
    async def read_file(self, path: str) -> str:
        """Read file within allowed directory."""
        
        # Resolve and validate path
        requested_path = (self.root / path).resolve()
        
        # Check it's within allowed directory
        if not str(requested_path).startswith(str(self.root)):
            raise БезопасностьError("Path traversal attempt blocked")
        
        # Check file exists and is readable
        if not requested_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if not os.access(requested_path, os.R_OK):
            raise PermissionError(f"Cannot read: {path}")
        
        return requested_path.read_text()
```

---

### 2. Resource Leakage

```python
# Vulnerable: Returns all content without filtering
class VulnerableDBResource:
    @mcp.resource("database://users")
    async def get_users(self) -> str:
        users = db.query("SELECT * FROM users")
        return json.dumps(users)  # Includes passwords, PII!

# Secure: Filter sensitive fields
class SecureDBResource:
    SAFE_FIELDS = ["id", "username", "email"]
    
    @mcp.resource("database://users") 
    async def get_users(self) -> str:
        users = db.query("SELECT id, username, email FROM users")
        
        # Additional PII scrubbing
        for user in users:
            user["email"] = self._mask_email(user["email"])
        
        return json.dumps(users)
```

---

### 3. Command Injection via Инструментs

```python
# EXTREMELY DANGEROUS - never do this
class DangerousServer:
    @mcp.tool()
    async def execute(self, command: str) -> str:
        """Execute shell command."""
        return os.popen(command).read()  # RCE vulnerability!

# Secure: Allowlist specific operations
class SecureOperationsServer:
    ALLOWED_OPERATIONS = {
        "list_files": lambda dir: os.listdir(dir),
        "get_stats": lambda path: os.stat(path),
        "ping": lambda host: subprocess.run(
            ["ping", "-c", "1", host],
            capture_output=True,
            timeout=5
        ).stdout.decode()
    }
    
    @mcp.tool()
    async def run_operation(self, operation: str, argument: str) -> str:
        """Run pre-approved operation."""
        
        if operation not in self.ALLOWED_OPERATIONS:
            raise БезопасностьError(f"Operation not allowed: {operation}")
        
        # Validate argument
        if not self._validate_argument(operation, argument):
            raise БезопасностьError(f"Invalid argument for {operation}")
        
        try:
            result = self.ALLOWED_OPERATIONS[operation](argument)
            return str(result)
        except Exception as e:
            return f"Error: {type(e).__name__}"
```

---

### 4. Capability Escalation

```python
# Problem: Server registered with too many capabilities
server = mcp.Server(
    name="file_helper",
    tools=[
        read_file,     # Needed
        write_file,    # Needed
        delete_file,   # Maybe needed?
        execute_code,  # WHY!?
        access_network # WHY!?
    ]
)

# Secure: Minimal capability registration
class MinimalFileServer:
    """Server with minimal required capabilities."""
    
    CAPABILITIES = {
        "tools": ["read_file", "write_file"],
        "resources": ["file_list"],
    }
    
    def __init__(self):
        self.server = mcp.Server(
            name="file_helper",
            capabilities=self.CAPABILITIES
        )
        
        # Only register explicitly needed tools
        self.server.register_tool(self.read_file)
        self.server.register_tool(self.write_file)
```

---

## Secure MCP Server Design

### 1. Инструмент Schema Validation

```python
from pydantic import BaseModel, Field, validator
from typing import Literal
import re

class ReadFileArgs(BaseModel):
    """Validated arguments for read_file tool."""
    
    path: str = Field(..., description="Path to file to read")
    encoding: Literal["utf-8", "ascii", "latin-1"] = "utf-8"
    
    @validator('path')
    def validate_path(cls, v):
        # No path traversal
        if '..' in v:
            raise ValueError("Path traversal not allowed")
        
        # Only allowed extensions
        allowed_extensions = ['.txt', '.md', '.json', '.yaml']
        if not any(v.endswith(ext) for ext in allowed_extensions):
            raise ValueError(f"File type not allowed")
        
        # No hidden files
        if re.search(r'/\.', v):
            raise ValueError("Hidden files not accessible")
        
        return v

class SecureMCPServer:
    @mcp.tool(args_schema=ReadFileArgs)
    async def read_file(self, args: ReadFileArgs) -> str:
        """Read file with validated arguments."""
        # args already validated by pydantic
        return self._read_file_internal(args.path, args.encoding)
```

---

### 2. Rate Limiting and Quotas

```python
from functools import wraps
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window = window_seconds
        self.calls = defaultdict(list)
    
    def check(self, key: str) -> bool:
        now = time.time()
        self.calls[key] = [t for t in self.calls[key] if now - t < self.window]
        
        if len(self.calls[key]) >= self.max_calls:
            return False
        
        self.calls[key].append(now)
        return True

limiter = RateLimiter(max_calls=10, window_seconds=60)

class RateLimitedServer:
    @mcp.tool()
    async def expensive_operation(self, query: str) -> str:
        """Rate-limited expensive operation."""
        
        session_id = self.get_session_id()
        
        if not limiter.check(session_id):
            raise RateLimitError("Rate limit exceeded. Try again later.")
        
        return await self._execute_query(query)
```

---

### 3. Audit Logging

```python
import logging
from datetime import datetime
from dataclasses import dataclass

@dataclass
class AuditEntry:
    timestamp: str
    session_id: str
    tool_name: str
    arguments: dict
    result_size: int
    success: bool
    error: str = None

class AuditedMCPServer:
    def __init__(self):
        self.audit_log = []
        self.logger = logging.getLogger("mcp_audit")
    
    def audit_decorator(self, tool_func):
        @wraps(tool_func)
        async def wrapper(*args, **kwargs):
            start = datetime.utcnow()
            error = None
            result = None
            
            try:
                result = await tool_func(*args, **kwargs)
                success = True
            except Exception as e:
                error = str(e)
                success = False
                raise
            finally:
                entry = AuditEntry(
                    timestamp=start.isoformat(),
                    session_id=self.current_session,
                    tool_name=tool_func.__name__,
                    arguments=self._sanitize_args(kwargs),
                    result_size=len(str(result)) if result else 0,
                    success=success,
                    error=error
                )
                self.audit_log.append(entry)
                self.logger.info(f"Инструмент call: {entry}")
            
            return result
        return wrapper
    
    @mcp.tool()
    @audit_decorator
    async def read_file(self, path: str) -> str:
        """Audited file read operation."""
        return self._read_file_internal(path)
```

---

### 4. Capability Scoping

```python
class ScopedMCPServer:
    """MCP Server with capability scoping per session."""
    
    def __init__(self):
        self.session_capabilities = {}
    
    def register_session(
        self, 
        session_id: str, 
        allowed_tools: list,
        resource_access: list
    ):
        """Register session with specific capabilities."""
        self.session_capabilities[session_id] = {
            "tools": set(allowed_tools),
            "resources": set(resource_access)
        }
    
    def check_capability(self, session_id: str, capability_type: str, name: str) -> bool:
        """Check if session has capability."""
        if session_id not in self.session_capabilities:
            return False
        
        caps = self.session_capabilities[session_id]
        return name in caps.get(capability_type, set())
    
    @mcp.tool()
    async def scoped_tool(self, operation: str, args: dict) -> str:
        """Инструмент call with capability checking."""
        
        session_id = self.get_session_id()
        
        if not self.check_capability(session_id, "tools", operation):
            raise PermissionError(f"Инструмент '{operation}' not allowed for this session")
        
        return await self._execute_tool(operation, args)
```

---

## SENTINEL Integration

```python
from sentinel import configure, MCPGuard

configure(
    mcp_protection=True,
    tool_validation=True,
    audit_logging=True
)

mcp_guard = MCPGuard(
    validate_tool_args=True,
    rate_limit_per_minute=60,
    audit_all_calls=True
)

@mcp_guard.protect
async def handle_tool_call(tool_name: str, args: dict):
    # Automatically validated and rate-limited
    return await server.call_tool(tool_name, args)
```

---

## Best Practices Summary

| Practice | Implementation |
|----------|----------------|
| **Input Validation** | Pydantic schemas for all tool args |
| **Path Safety** | Resolve and check against root |
| **Minimal Capabilities** | Only register needed tools |
| **Rate Limiting** | Per-session/per-tool limits |
| **Audit Logging** | Log all tool calls with context |
| **Capability Scoping** | Different permissions per session |

---

## Ключевые выводы

1. **Validate all inputs** - Never trust tool arguments
2. **Minimal capabilities** - Only expose needed tools
3. **No shell execution** - Use allowlisted operations
4. **Audit everything** - Full logging for forensics
5. **Rate limit** - Prevent abuse

---

*AI Безопасность Academy | Lesson 04.4.1*
