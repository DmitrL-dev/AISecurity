# MCP Protocol Security

> **Урок:** 04.4.1 - Model Context Protocol  
> **Время:** 45 минут  
> **Prerequisites:** Agentic Security basics

---

## Цели обучения

После завершения этого урока вы сможете:

1. Понять MCP architecture и security model
2. Идентифицировать MCP-specific vulnerabilities
3. Реализовать secure MCP server practices
4. Audit MCP integrations for security issues

---

## Что такое MCP?

Model Context Protocol (MCP) is Anthropic's open standard for connecting AI models to external tools and data sources:

| Component | Role |
|-----------|------|
| **MCP Host** | The AI application (e.g., Claude Desktop) |
| **MCP Client** | Protocol handler in the host |
| **MCP Server** | External tool/data provider |
| **Resources** | Read-only data sources |
| **Tools** | Executable functions |

---

## Security Vulnerabilities

### 1. Tool Injection Attacks

```python
# Vulnerable MCP server
class VulnerableFileServer:
    @mcp.tool()
    async def read_file(self, path: str) -> str:
        return open(path).read()  # No validation!

# Secure Implementation:
class SecureFileServer:
    def __init__(self, allowed_directory: str):
        self.root = Path(allowed_directory).resolve()
    
    @mcp.tool()
    async def read_file(self, path: str) -> str:
        """Read file within allowed directory."""
        
        requested_path = (self.root / path).resolve()
        
        if not str(requested_path).startswith(str(self.root)):
            raise SecurityError("Path traversal attempt blocked")
        
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
        
        for user in users:
            user["email"] = self._mask_email(user["email"])
        
        return json.dumps(users)
```

---

### 3. Command Injection via Tools

```python
# EXTREMELY DANGEROUS - never do this
class DangerousServer:
    @mcp.tool()
    async def execute(self, command: str) -> str:
        return os.popen(command).read()  # RCE vulnerability!

# Secure: Allowlist specific operations
class SecureOperationsServer:
    ALLOWED_OPERATIONS = {
        "list_files": lambda dir: os.listdir(dir),
        "get_stats": lambda path: os.stat(path),
    }
    
    @mcp.tool()
    async def run_operation(self, operation: str, argument: str) -> str:
        if operation not in self.ALLOWED_OPERATIONS:
            raise SecurityError(f"Operation not allowed: {operation}")
        
        return str(self.ALLOWED_OPERATIONS[operation](argument))
```

---

## Secure MCP Server Design

### Tool Schema Validation

```python
from pydantic import BaseModel, Field, validator

class ReadFileArgs(BaseModel):
    """Validated arguments for read_file tool."""
    
    path: str = Field(..., description="Path to file to read")
    encoding: Literal["utf-8", "ascii"] = "utf-8"
    
    @validator('path')
    def validate_path(cls, v):
        if '..' in v:
            raise ValueError("Path traversal not allowed")
        
        allowed_extensions = ['.txt', '.md', '.json']
        if not any(v.endswith(ext) for ext in allowed_extensions):
            raise ValueError(f"File type not allowed")
        
        return v
```

---

### Rate Limiting and Quotas

```python
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
    return await server.call_tool(tool_name, args)
```

---

## Ключевые выводы

1. **Validate all inputs** - Never trust tool arguments
2. **Minimal capabilities** - Only expose needed tools
3. **No shell execution** - Use allowlisted operations
4. **Audit everything** - Full logging for forensics
5. **Rate limit** - Prevent abuse

---

*AI Security Academy | Урок 04.4.1*
