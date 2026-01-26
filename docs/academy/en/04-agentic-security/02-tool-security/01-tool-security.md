# Tool Security for AI Agents

> **Level:** Advanced  
> **Time:** 55 minutes  
> **Track:** 04 — Agentic Security  
> **Module:** 04.2 — Tool Security  
> **Version:** 1.0

---

## Learning Objectives

- [ ] Understand tool use risks in AI agents
- [ ] Implement tool validation and sandboxing
- [ ] Build tool call monitoring pipeline
- [ ] Integrate tool security in SENTINEL

---

## 1. Tool Security Overview

```
┌────────────────────────────────────────────────────────────────────┐
│              TOOL SECURITY THREAT MODEL                            │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Attack Vectors:                                                   │
│  ├── Tool Injection: Unauthorized tool calls                     │
│  ├── Parameter Injection: Malicious parameters                   │
│  ├── Privilege Escalation: Elevated permissions                  │
│  └── Chain Attacks: Combined tool abuse                          │
│                                                                    │
│  Defense Layers:                                                   │
│  ├── Tool Registry: Whitelist                                    │
│  ├── Parameter Validation: Schema validation                      │
│  ├── Permission Checks: RBAC                                      │
│  ├── Execution Sandbox: Isolation                                │
│  └── Output Filtering: Result validation                         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tool Registry

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from enum import Enum
import re

class ToolCategory(Enum):
    READ_ONLY = "read_only"
    WRITE = "write"
    NETWORK = "network"
    SYSTEM = "system"
    DANGEROUS = "dangerous"

class ParameterType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"

@dataclass
class ParameterSchema:
    """Parameter schema"""
    name: str
    param_type: ParameterType
    required: bool = True
    default: Any = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[Any]] = None
    
    def validate(self, value: Any) -> tuple[bool, str]:
        if value is None:
            if self.required:
                return False, f"{self.name} required"
            return True, ""
        
        # Type check
        type_map = {
            ParameterType.STRING: str,
            ParameterType.INTEGER: int,
            ParameterType.FLOAT: (int, float),
            ParameterType.BOOLEAN: bool
        }
        if self.param_type in type_map:
            if not isinstance(value, type_map[self.param_type]):
                return False, f"{self.name} wrong type"
        
        # String validations
        if isinstance(value, str):
            if self.max_length and len(value) > self.max_length:
                return False, f"{self.name} too long"
            if self.pattern and not re.match(self.pattern, value):
                return False, f"{self.name} invalid format"
        
        if self.enum_values and value not in self.enum_values:
            return False, f"{self.name} not in allowed values"
        
        return True, ""

@dataclass
class ToolDefinition:
    """Tool definition"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ParameterSchema] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    max_calls_per_minute: int = 100
    requires_approval: bool = False
    handler: Optional[Callable] = None
    timeout_seconds: float = 30.0
    deprecated: bool = False
    
    def validate_parameters(self, params: Dict) -> tuple[bool, List[str]]:
        errors = []
        for schema in self.parameters:
            value = params.get(schema.name, schema.default)
            valid, error = schema.validate(value)
            if not valid:
                errors.append(error)
        return len(errors) == 0, errors

class ToolRegistry:
    """Tool registry"""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
    
    def register(self, tool: ToolDefinition):
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        return self.tools.get(name)
    
    def is_allowed(self, name: str) -> bool:
        tool = self.get(name)
        return tool is not None and not tool.deprecated
    
    def get_safe_tools(self) -> List[str]:
        return [n for n, t in self.tools.items() 
                if t.category == ToolCategory.READ_ONLY]
```

---

## 3. Tool Validation

```python
@dataclass
class ToolCallRequest:
    tool_name: str
    parameters: Dict[str, Any]
    agent_id: str
    session_id: str

@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    sanitized_params: Optional[Dict] = None

class ToolCallValidator:
    """Validates tool calls"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.dangerous_patterns = [
            r';\s*(rm|del|drop)',
            r'\|\s*(bash|sh|cmd)',
            r'\.\./\.\.'
        ]
    
    def validate(self, request: ToolCallRequest) -> ValidationResult:
        errors = []
        
        tool = self.registry.get(request.tool_name)
        if not tool:
            return ValidationResult(False, [f"Unknown tool: {request.tool_name}"])
        
        valid, param_errors = tool.validate_parameters(request.parameters)
        errors.extend(param_errors)
        
        injection = self._check_injection(request.parameters)
        errors.extend(injection)
        
        sanitized = self._sanitize(request.parameters, tool) if not errors else None
        
        return ValidationResult(len(errors) == 0, errors, sanitized)
    
    def _check_injection(self, params: Dict) -> List[str]:
        issues = []
        for key, value in params.items():
            if isinstance(value, str):
                for pattern in self.dangerous_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        issues.append(f"Dangerous pattern in {key}")
        return issues
    
    def _sanitize(self, params: Dict, tool: ToolDefinition) -> Dict:
        sanitized = {}
        for schema in tool.parameters:
            value = params.get(schema.name, schema.default)
            if isinstance(value, str):
                value = value.replace('\x00', '')
            sanitized[schema.name] = value
        return sanitized
```

---

## 4. Tool Sandbox

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError

@dataclass
class ExecutionResult:
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: float = 0

class ToolSandbox:
    """Sandboxed execution"""
    
    def __init__(self, max_output_size: int = 100000):
        self.max_output = max_output_size
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def execute(self, tool: ToolDefinition, params: Dict) -> ExecutionResult:
        import time
        start = time.time()
        
        if tool.handler is None:
            return ExecutionResult(False, None, "No handler")
        
        try:
            future = self.executor.submit(tool.handler, params, {})
            result = future.result(timeout=tool.timeout_seconds)
            
            output = str(result)
            if len(output) > self.max_output:
                result = output[:self.max_output] + "... [truncated]"
            
            return ExecutionResult(True, result,
                                  execution_time_ms=(time.time() - start) * 1000)
        except TimeoutError:
            return ExecutionResult(False, None, "Timeout",
                                  execution_time_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ExecutionResult(False, None, str(e),
                                  execution_time_ms=(time.time() - start) * 1000)

class SafeToolExecutor:
    """Safe tool executor"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.sandbox = ToolSandbox()
        self.validator = ToolCallValidator(registry)
        self.call_counts: Dict[str, int] = {}
    
    def execute(self, request: ToolCallRequest) -> ExecutionResult:
        # Rate limit
        key = f"{request.agent_id}:{request.tool_name}"
        self.call_counts[key] = self.call_counts.get(key, 0) + 1
        
        tool = self.registry.get(request.tool_name)
        if tool and self.call_counts[key] > tool.max_calls_per_minute:
            return ExecutionResult(False, None, "Rate limit exceeded")
        
        # Validate
        validation = self.validator.validate(request)
        if not validation.valid:
            return ExecutionResult(False, None, str(validation.errors))
        
        # Execute
        return self.sandbox.execute(tool, validation.sanitized_params)
```

---

## 5. Monitoring

```python
from collections import defaultdict
from datetime import datetime, timedelta

@dataclass
class ToolCallEvent:
    timestamp: datetime
    tool_name: str
    agent_id: str
    result_type: str
    execution_time_ms: float

class ToolCallMonitor:
    """Monitor tool calls"""
    
    def __init__(self):
        self.events: List[ToolCallEvent] = []
    
    def record(self, event: ToolCallEvent):
        self.events.append(event)
        self._cleanup()
    
    def _cleanup(self):
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.events = [e for e in self.events if e.timestamp >= cutoff]
    
    def get_stats(self, agent_id: str) -> Dict:
        agent_events = [e for e in self.events if e.agent_id == agent_id]
        if not agent_events:
            return {'total': 0}
        
        errors = sum(1 for e in agent_events if e.result_type == 'error')
        return {
            'total': len(agent_events),
            'errors': errors,
            'error_rate': errors / len(agent_events)
        }
    
    def detect_anomalies(self, agent_id: str) -> List[Dict]:
        anomalies = []
        stats = self.get_stats(agent_id)
        
        if stats.get('error_rate', 0) > 0.3:
            anomalies.append({'type': 'high_error_rate', 'severity': 'medium'})
        if stats.get('total', 0) > 100:
            anomalies.append({'type': 'high_call_rate', 'severity': 'medium'})
        
        return anomalies
```

---

## 6. SENTINEL Integration

```python
from dataclasses import dataclass

@dataclass
class ToolSecurityConfig:
    enable_sandbox: bool = True
    max_timeout: float = 30.0
    enable_monitoring: bool = True

class SENTINELToolEngine:
    """Tool security for SENTINEL"""
    
    def __init__(self, config: ToolSecurityConfig):
        self.config = config
        self.registry = ToolRegistry()
        self.executor = SafeToolExecutor(self.registry)
        self.monitor = ToolCallMonitor() if config.enable_monitoring else None
    
    def register_tool(self, tool: ToolDefinition):
        self.registry.register(tool)
    
    def execute(self, tool_name: str, params: Dict,
                agent_id: str, session_id: str) -> ExecutionResult:
        request = ToolCallRequest(tool_name, params, agent_id, session_id)
        result = self.executor.execute(request)
        
        if self.monitor:
            self.monitor.record(ToolCallEvent(
                timestamp=datetime.utcnow(),
                tool_name=tool_name,
                agent_id=agent_id,
                result_type='success' if result.success else 'error',
                execution_time_ms=result.execution_time_ms
            ))
        
        return result
    
    def get_anomalies(self, agent_id: str) -> List[Dict]:
        return self.monitor.detect_anomalies(agent_id) if self.monitor else []
```

---

## 7. Summary

| Component | Description |
|-----------|-------------|
| **ToolDefinition** | Schema with parameters |
| **ToolRegistry** | Allowed tools whitelist |
| **Validator** | Parameter + injection check |
| **Sandbox** | Isolated execution |
| **Monitor** | Anomaly detection |

---

## Next Lesson

→ [03. Trust & Authorization](../03-trust/README.md)

---

*AI Security Academy | Track 04: Agentic Security | Module 04.2: Tool Security*
