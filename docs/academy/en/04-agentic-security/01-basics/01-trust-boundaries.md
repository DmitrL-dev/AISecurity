# Trust Boundaries in Agentic Systems

> **Lesson:** 04.1.1 - Trust Boundaries  
> **Time:** 45 minutes  
> **Prerequisites:** Agent architectures

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Identify trust boundaries in agent systems
2. Design secure boundary transitions
3. Implement validation at boundaries
4. Build defense-in-depth architectures

---

## What are Trust Boundaries?

A trust boundary separates components with different trust levels:

```
╔══════════════════════════════════════════════════════════════╗
║                    TRUST BOUNDARY MAP                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ┌─────────────┐                                              ║
║  │    USER     │ Untrusted input                              ║
║  └──────┬──────┘                                              ║
║         │                                                     ║
║ ════════╪══════════════ BOUNDARY 1 ══════════════════════    ║
║         ▼                                                     ║
║  ┌─────────────┐                                              ║
║  │   AGENT     │ Partially trusted (may be manipulated)       ║
║  └──────┬──────┘                                              ║
║         │                                                     ║
║ ════════╪══════════════ BOUNDARY 2 ══════════════════════    ║
║         ▼                                                     ║
║  ┌─────────────┐                                              ║
║  │   TOOLS     │ Sensitive operations                         ║
║  └──────┬──────┘                                              ║
║         │                                                     ║
║ ════════╪══════════════ BOUNDARY 3 ══════════════════════    ║
║         ▼                                                     ║
║  ┌─────────────┐                                              ║
║  │  SYSTEMS    │ Data, APIs, infrastructure                   ║
║  └─────────────┘                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Trust Levels

| Level | Examples | Trust |
|-------|----------|-------|
| **Untrusted** | User input, external data | Validate everything |
| **Partially Trusted** | Agent decisions, LLM output | Verify important actions |
| **Trusted** | System code, verified config | Minimal validation |
| **Highly Trusted** | Core security, crypto | Audit, no dynamic changes |

---

## Boundary 1: User → Agent

### Input Validation

```python
class UserAgentBoundary:
    """Validate inputs crossing user-to-agent boundary."""
    
    def __init__(self):
        self.input_scanner = InputScanner()
        self.rate_limiter = RateLimiter()
        self.session_manager = SessionManager()
    
    def validate_input(self, user_input: str, session: dict) -> dict:
        """Validate user input before agent processing."""
        
        # 1. Rate limiting
        if not self.rate_limiter.check(session["user_id"]):
            return {"allowed": False, "reason": "rate_limit_exceeded"}
        
        # 2. Input length check
        if len(user_input) > 10000:
            return {"allowed": False, "reason": "input_too_long"}
        
        # 3. Injection scanning
        scan_result = self.input_scanner.scan(user_input)
        if scan_result["is_injection"]:
            self._log_attack_attempt(session, user_input, scan_result)
            return {"allowed": False, "reason": "injection_detected"}
        
        # 4. Content policy check
        policy_check = self._check_content_policy(user_input)
        if not policy_check["allowed"]:
            return {"allowed": False, "reason": policy_check["reason"]}
        
        return {
            "allowed": True,
            "sanitized_input": self._sanitize(user_input),
            "metadata": {
                "risk_score": scan_result.get("risk_score", 0),
                "session_id": session["id"]
            }
        }
    
    def _sanitize(self, text: str) -> str:
        """Sanitize input for safe processing."""
        # Remove invisible characters
        # Normalize unicode
        # Strip dangerous formatting
        return text  # Implement sanitization
```

---

## Boundary 2: Agent → Tools

### Tool Authorization

```python
class AgentToolBoundary:
    """Control agent access to tools."""
    
    def __init__(self, authz_manager):
        self.authz = authz_manager
        self.tool_registry = {}
    
    def register_tool(
        self, 
        tool_name: str, 
        tool_func, 
        required_permissions: list,
        input_schema: dict,
        risk_level: str
    ):
        """Register a tool with security metadata."""
        
        self.tool_registry[tool_name] = {
            "func": tool_func,
            "permissions": required_permissions,
            "schema": input_schema,
            "risk_level": risk_level
        }
    
    async def execute_tool(
        self, 
        tool_name: str, 
        arguments: dict,
        agent_context: dict
    ) -> dict:
        """Execute tool with boundary checks."""
        
        if tool_name not in self.tool_registry:
            return {"error": f"Unknown tool: {tool_name}"}
        
        tool = self.tool_registry[tool_name]
        
        # 1. Permission check
        for perm in tool["permissions"]:
            result = self.authz.check(agent_context, perm)
            if not result["allowed"]:
                return {"error": f"Permission denied: {perm}"}
        
        # 2. Schema validation
        if not self._validate_schema(arguments, tool["schema"]):
            return {"error": "Invalid arguments"}
        
        # 3. Argument sanitization
        safe_args = self._sanitize_arguments(arguments, tool["schema"])
        
        # 4. Risk-based approval
        if tool["risk_level"] == "high":
            approval = await self._request_human_approval(
                tool_name, safe_args, agent_context
            )
            if not approval["approved"]:
                return {"error": "Human approval denied"}
        
        # 5. Execute with isolation
        try:
            result = await self._execute_isolated(tool["func"], safe_args)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}
    
    def _validate_schema(self, args: dict, schema: dict) -> bool:
        """Validate arguments against schema."""
        import jsonschema
        try:
            jsonschema.validate(args, schema)
            return True
        except jsonschema.ValidationError:
            return False
    
    def _sanitize_arguments(self, args: dict, schema: dict) -> dict:
        """Sanitize arguments based on schema types."""
        safe = {}
        for key, value in args.items():
            if key in schema.get("properties", {}):
                prop = schema["properties"][key]
                
                if prop.get("type") == "string":
                    # Path traversal prevention
                    if "path" in key.lower():
                        safe[key] = self._sanitize_path(value)
                    else:
                        safe[key] = self._sanitize_string(value)
                else:
                    safe[key] = value
        
        return safe
    
    def _sanitize_path(self, path: str) -> str:
        """Prevent path traversal."""
        import os
        # Resolve to absolute, check within allowed directories
        abs_path = os.path.abspath(path)
        
        allowed_dirs = ["/project", "/tmp"]
        if not any(abs_path.startswith(d) for d in allowed_dirs):
            raise ValueError(f"Path outside allowed directories: {path}")
        
        return abs_path
```

---

## Boundary 3: Tools → Systems

### System Protection

```python
class ToolSystemBoundary:
    """Protect backend systems from tool access."""
    
    def __init__(self):
        self.db_pool = DatabasePool()
        self.api_clients = {}
        self.file_sandbox = FileSandbox()
    
    def get_database_connection(
        self, 
        tool_context: dict,
        required_access: list
    ):
        """Get database connection with restrictions."""
        
        # Create restricted connection based on tool permissions
        allowed_tables = self._get_allowed_tables(required_access)
        allowed_operations = self._get_allowed_operations(required_access)
        
        return RestrictedDBConnection(
            pool=self.db_pool,
            allowed_tables=allowed_tables,
            allowed_operations=allowed_operations,
            query_timeout=10,
            max_rows=1000
        )
    
    def get_api_client(
        self, 
        api_name: str,
        tool_context: dict
    ):
        """Get API client with scope restrictions."""
        
        # Scoped API client based on tool permissions
        scopes = self._get_api_scopes(tool_context)
        
        return ScopedAPIClient(
            base_client=self.api_clients.get(api_name),
            allowed_endpoints=scopes,
            rate_limit=100,
            timeout=30
        )
    
    def get_file_access(
        self,
        tool_context: dict,
        operation: str  # "read", "write", "execute"
    ):
        """Get sandboxed file access."""
        
        allowed_paths = self._get_allowed_paths(tool_context)
        
        return self.file_sandbox.get_accessor(
            allowed_paths=allowed_paths,
            operation=operation,
            size_limit=10 * 1024 * 1024  # 10MB
        )

class RestrictedDBConnection:
    """Database connection with query restrictions."""
    
    def __init__(self, pool, allowed_tables, allowed_operations, **kwargs):
        self.pool = pool
        self.allowed_tables = allowed_tables
        self.allowed_operations = allowed_operations
        self.timeout = kwargs.get("query_timeout", 10)
        self.max_rows = kwargs.get("max_rows", 1000)
    
    async def execute(self, query: str, params: tuple = None) -> list:
        """Execute query with restrictions."""
        
        # Parse and validate query
        parsed = self._parse_query(query)
        
        # Check operation
        if parsed["operation"] not in self.allowed_operations:
            raise PermissionError(f"Operation not allowed: {parsed['operation']}")
        
        # Check tables
        for table in parsed["tables"]:
            if table not in self.allowed_tables:
                raise PermissionError(f"Table not allowed: {table}")
        
        # Add LIMIT if not present
        if "SELECT" in query.upper() and "LIMIT" not in query.upper():
            query = f"{query} LIMIT {self.max_rows}"
        
        # Execute with timeout
        async with self.pool.acquire() as conn:
            return await asyncio.wait_for(
                conn.fetch(query, *params if params else []),
                timeout=self.timeout
            )
```

---

## Cross-Boundary Data Flow

### Data Classification

```python
from enum import Enum
from dataclasses import dataclass

class Sensitivity(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

@dataclass
class ClassifiedData:
    """Data with sensitivity classification."""
    
    value: any
    sensitivity: Sensitivity
    source: str
    can_cross_boundary: dict  # boundary_name -> bool

class DataFlowController:
    """Control data flow across boundaries."""
    
    def can_transfer(
        self, 
        data: ClassifiedData,
        from_boundary: str,
        to_boundary: str
    ) -> dict:
        """Check if data can cross boundary."""
        
        # Check explicit permissions
        if to_boundary in data.can_cross_boundary:
            if not data.can_cross_boundary[to_boundary]:
                return {"allowed": False, "reason": "Explicitly blocked"}
        
        # Apply sensitivity rules
        rules = {
            Sensitivity.PUBLIC: True,  # Can cross any boundary
            Sensitivity.INTERNAL: to_boundary not in ["user", "external"],
            Sensitivity.CONFIDENTIAL: to_boundary == "agent_internal",
            Sensitivity.RESTRICTED: False  # Never crosses boundaries
        }
        
        allowed = rules.get(data.sensitivity, False)
        
        return {
            "allowed": allowed,
            "reason": None if allowed else f"Sensitivity {data.sensitivity} cannot cross to {to_boundary}",
            "requires_redaction": data.sensitivity in [Sensitivity.CONFIDENTIAL, Sensitivity.RESTRICTED]
        }
    
    def transfer(
        self, 
        data: ClassifiedData,
        from_boundary: str,
        to_boundary: str
    ) -> ClassifiedData:
        """Transfer data with appropriate handling."""
        
        check = self.can_transfer(data, from_boundary, to_boundary)
        
        if not check["allowed"]:
            raise PermissionError(check["reason"])
        
        if check.get("requires_redaction"):
            return self._redact(data)
        
        return data
```

---

## SENTINEL Integration

```python
from sentinel import configure, TrustBoundary

configure(
    trust_boundaries=True,
    boundary_logging=True,
    data_classification=True
)

user_agent_boundary = TrustBoundary(
    name="user_agent",
    validate_input=True,
    scan_for_injection=True
)

agent_tool_boundary = TrustBoundary(
    name="agent_tool",
    require_authorization=True,
    validate_arguments=True,
    high_risk_approval=True
)

@user_agent_boundary.validate
def process_user_input(user_input: str):
    # Automatically validated
    return agent.process(user_input)

@agent_tool_boundary.authorize
def execute_tool(tool_name: str, args: dict):
    # Automatically authorized
    return tools.execute(tool_name, args)
```

---

## Key Takeaways

1. **Identify all boundaries** - Map trust transitions
2. **Validate at each crossing** - Never trust previous validation
3. **Principle of least privilege** - Minimal access at each boundary
4. **Classify data sensitivity** - Control what can cross
5. **Log everything** - Audit trail for forensics

---

*AI Security Academy | Lesson 04.1.1*
