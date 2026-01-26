# Tool Security для AI Agents

> **Уровень:** �����������  
> **Время:** 55 минут  
> **Трек:** 04 — Agentic Security  
> **Модуль:** 04.2 — Tool Security  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять риски tool use в AI agents
- [ ] Имплементировать tool validation и sandboxing
- [ ] Построить tool call monitoring pipeline
- [ ] Интегрировать tool security в SENTINEL

---

## 1. Tool Security Overview

### 1.1 Tool Use Risks

```
┌────────────────────────────────────────────────────────────────────┐
│              TOOL SECURITY THREAT MODEL                            │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Attack Vectors:                                                   │
│  ├── Tool Injection: Agent вызывает неавторизованные tools       │
│  ├── Parameter Injection: Malicious parameters в tool calls      │
│  ├── Privilege Escalation: Tools с elevated permissions          │
│  ├── Data Exfiltration: Tools для извлечения данных             │
│  └── Chain Attacks: Комбинация tools для атаки                  │
│                                                                    │
│  Defense Layers:                                                   │
│  ├── Tool Registry: Whitelist разрешённых tools                  │
│  ├── Parameter Validation: Schema validation для inputs          │
│  ├── Permission Checks: RBAC для tool access                     │
│  ├── Execution Sandbox: Изолированное выполнение               │
│  └── Output Filtering: Validation результатов                    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tool Registry

### 2.1 Tool Definition

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from enum import Enum
import json
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
    """Schema for tool parameter"""
    name: str
    param_type: ParameterType
    description: str = ""
    required: bool = True
    default: Any = None
    
    # Validation constraints
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # Regex pattern
    enum_values: Optional[List[Any]] = None
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate value against schema"""
        if value is None:
            if self.required and self.default is None:
                return False, f"{self.name} is required"
            return True, ""
        
        # Type check
        type_map = {
            ParameterType.STRING: str,
            ParameterType.INTEGER: int,
            ParameterType.FLOAT: (int, float),
            ParameterType.BOOLEAN: bool,
            ParameterType.ARRAY: list,
            ParameterType.OBJECT: dict
        }
        
        expected_type = type_map.get(self.param_type)
        if expected_type and not isinstance(value, expected_type):
            return False, f"{self.name} must be {self.param_type.value}"
        
        # String validations
        if self.param_type == ParameterType.STRING and isinstance(value, str):
            if self.min_length and len(value) < self.min_length:
                return False, f"{self.name} too short (min {self.min_length})"
            if self.max_length and len(value) > self.max_length:
                return False, f"{self.name} too long (max {self.max_length})"
            if self.pattern and not re.match(self.pattern, value):
                return False, f"{self.name} doesn't match pattern"
        
        # Numeric validations
        if self.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
            if self.min_value is not None and value < self.min_value:
                return False, f"{self.name} below minimum {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"{self.name} above maximum {self.max_value}"
        
        # Enum validation
        if self.enum_values and value not in self.enum_values:
            return False, f"{self.name} must be one of {self.enum_values}"
        
        return True, ""

@dataclass
class ToolDefinition:
    """Complete tool definition"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ParameterSchema] = field(default_factory=list)
    
    # Permissions
    required_permissions: List[str] = field(default_factory=list)
    max_calls_per_minute: int = 100
    requires_approval: bool = False
    
    # Execution
    handler: Optional[Callable] = None
    timeout_seconds: float = 30.0
    
    # Metadata
    version: str = "1.0"
    deprecated: bool = False
    
    def validate_parameters(self, params: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate all parameters"""
        errors = []
        
        for schema in self.parameters:
            value = params.get(schema.name, schema.default)
            valid, error = schema.validate(value)
            if not valid:
                errors.append(error)
        
        # Check for unknown parameters
        known_params = {p.name for p in self.parameters}
        unknown = set(params.keys()) - known_params
        if unknown:
            errors.append(f"Unknown parameters: {unknown}")
        
        return len(errors) == 0, errors

class ToolRegistry:
    """Registry of available tools"""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.categories: Dict[ToolCategory, List[str]] = {c: [] for c in ToolCategory}
    
    def register(self, tool: ToolDefinition):
        """Register a tool"""
        self.tools[tool.name] = tool
        self.categories[tool.category].append(tool.name)
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def list_by_category(self, category: ToolCategory) -> List[str]:
        """List tools in category"""
        return self.categories.get(category, [])
    
    def is_allowed(self, name: str) -> bool:
        """Check if tool is registered"""
        tool = self.get(name)
        return tool is not None and not tool.deprecated
    
    def get_safe_tools(self) -> List[str]:
        """Get list of safe (read-only) tools"""
        return self.categories.get(ToolCategory.READ_ONLY, [])
```

---

## 3. Tool Call Validation

### 3.1 Validator

```python
from dataclasses import dataclass

@dataclass
class ToolCallRequest:
    """Tool call request"""
    tool_name: str
    parameters: Dict[str, Any]
    agent_id: str
    session_id: str
    context: Dict = field(default_factory=dict)

@dataclass
class ValidationResult:
    """Validation result"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_params: Optional[Dict[str, Any]] = None

class ToolCallValidator:
    """Validates tool calls"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.dangerous_patterns = [
            r';\s*(rm|del|drop|truncate)',
            r'\|\s*(bash|sh|cmd)',
            r'<script[^>]*>',
            r'javascript:',
            r'\.\./\.\.',  # Path traversal
        ]
    
    def validate(self, request: ToolCallRequest) -> ValidationResult:
        """Validate a tool call request"""
        errors = []
        warnings = []
        
        # Check tool exists
        tool = self.registry.get(request.tool_name)
        if not tool:
            return ValidationResult(False, [f"Unknown tool: {request.tool_name}"], [])
        
        if tool.deprecated:
            warnings.append(f"Tool {request.tool_name} is deprecated")
        
        # Validate parameters
        valid, param_errors = tool.validate_parameters(request.parameters)
        errors.extend(param_errors)
        
        # Injection detection
        injection_warnings = self._check_injection(request.parameters)
        if injection_warnings:
            errors.extend(injection_warnings)
        
        # Sanitize parameters
        sanitized = None
        if not errors:
            sanitized = self._sanitize_parameters(request.parameters, tool)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_params=sanitized
        )
    
    def _check_injection(self, params: Dict[str, Any]) -> List[str]:
        """Check for injection patterns"""
        issues = []
        
        def check_value(value: Any, path: str):
            if isinstance(value, str):
                for pattern in self.dangerous_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        issues.append(f"Dangerous pattern in {path}")
                        break
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_value(v, f"{path}.{k}")
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    check_value(v, f"{path}[{i}]")
        
        for key, value in params.items():
            check_value(value, key)
        
        return issues
    
    def _sanitize_parameters(self, params: Dict[str, Any], 
                            tool: ToolDefinition) -> Dict[str, Any]:
        """Sanitize parameters"""
        sanitized = {}
        
        for schema in tool.parameters:
            value = params.get(schema.name, schema.default)
            
            if value is not None and schema.param_type == ParameterType.STRING:
                # Basic sanitization
                value = str(value)
                value = value.replace('\x00', '')  # Remove null bytes
            
            sanitized[schema.name] = value
        
        return sanitized
```

---

## 4. Tool Execution Sandbox

### 4.1 Sandbox Implementation

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
import traceback
import resource
import os

@dataclass
class ExecutionResult:
    """Tool execution result"""
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: float = 0
    resource_usage: Dict = field(default_factory=dict)

class ToolSandbox:
    """Sandboxed tool execution environment"""
    
    def __init__(self, max_memory_mb: int = 100,
                 max_cpu_seconds: int = 10,
                 max_output_size: int = 100000):
        self.max_memory = max_memory_mb * 1024 * 1024
        self.max_cpu = max_cpu_seconds
        self.max_output = max_output_size
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def execute(self, tool: ToolDefinition, params: Dict[str, Any],
                context: Dict = None) -> ExecutionResult:
        """Execute tool in sandbox"""
        import time
        start = time.time()
        
        if tool.handler is None:
            return ExecutionResult(
                success=False,
                result=None,
                error="Tool has no handler"
            )
        
        try:
            # Execute with timeout
            future = self.executor.submit(
                self._execute_with_limits,
                tool.handler,
                params,
                context or {}
            )
            
            result = future.result(timeout=tool.timeout_seconds)
            
            # Validate output size
            output_str = str(result)
            if len(output_str) > self.max_output:
                result = output_str[:self.max_output] + "... [truncated]"
            
            return ExecutionResult(
                success=True,
                result=result,
                execution_time_ms=(time.time() - start) * 1000
            )
        
        except FuturesTimeout:
            return ExecutionResult(
                success=False,
                result=None,
                error=f"Timeout after {tool.timeout_seconds}s",
                execution_time_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _execute_with_limits(self, handler: Callable,
                            params: Dict, context: Dict) -> Any:
        """Execute with resource limits"""
        # Note: Resource limits work on Unix systems
        # On Windows, consider using process-based isolation
        try:
            if hasattr(resource, 'setrlimit'):
                # Set memory limit
                resource.setrlimit(resource.RLIMIT_AS, 
                                  (self.max_memory, self.max_memory))
                # Set CPU time limit
                resource.setrlimit(resource.RLIMIT_CPU,
                                  (self.max_cpu, self.max_cpu))
        except:
            pass  # Skip on Windows
        
        return handler(params, context)

class SafeToolExecutor:
    """High-level safe tool executor"""
    
    def __init__(self, registry: ToolRegistry, sandbox: ToolSandbox = None):
        self.registry = registry
        self.sandbox = sandbox or ToolSandbox()
        self.validator = ToolCallValidator(registry)
        self.call_counts: Dict[str, int] = {}
        self.last_reset = time.time()
    
    def execute(self, request: ToolCallRequest) -> ExecutionResult:
        """Execute tool call safely"""
        
        # Rate limiting
        if not self._check_rate_limit(request):
            return ExecutionResult(
                success=False,
                result=None,
                error="Rate limit exceeded"
            )
        
        # Validation
        validation = self.validator.validate(request)
        if not validation.valid:
            return ExecutionResult(
                success=False,
                result=None,
                error=f"Validation failed: {validation.errors}"
            )
        
        # Get tool
        tool = self.registry.get(request.tool_name)
        
        # Execute in sandbox
        result = self.sandbox.execute(
            tool,
            validation.sanitized_params,
            request.context
        )
        
        return result
    
    def _check_rate_limit(self, request: ToolCallRequest) -> bool:
        """Check rate limit"""
        import time
        
        # Reset counter every minute
        if time.time() - self.last_reset > 60:
            self.call_counts = {}
            self.last_reset = time.time()
        
        tool = self.registry.get(request.tool_name)
        if not tool:
            return False
        
        key = f"{request.agent_id}:{request.tool_name}"
        self.call_counts[key] = self.call_counts.get(key, 0) + 1
        
        return self.call_counts[key] <= tool.max_calls_per_minute
```

---

## 5. Tool Call Monitoring

### 5.1 Monitor

```python
from collections import defaultdict
from datetime import datetime, timedelta
import threading

@dataclass
class ToolCallEvent:
    """Tool call event for monitoring"""
    timestamp: datetime
    tool_name: str
    agent_id: str
    session_id: str
    parameters_hash: str
    result_type: str  # success, error, blocked
    execution_time_ms: float
    error: Optional[str] = None

class ToolCallMonitor:
    """Monitors tool calls for anomalies"""
    
    def __init__(self, window_minutes: int = 60):
        self.window = timedelta(minutes=window_minutes)
        self.events: List[ToolCallEvent] = []
        self.lock = threading.RLock()
        
        # Thresholds
        self.error_rate_threshold = 0.3
        self.call_rate_threshold = 100
    
    def record(self, event: ToolCallEvent):
        """Record a tool call event"""
        with self.lock:
            self.events.append(event)
            self._cleanup()
    
    def _cleanup(self):
        """Remove old events"""
        cutoff = datetime.utcnow() - self.window
        self.events = [e for e in self.events if e.timestamp >= cutoff]
    
    def get_agent_stats(self, agent_id: str) -> Dict:
        """Get stats for an agent"""
        with self.lock:
            agent_events = [e for e in self.events if e.agent_id == agent_id]
            
            if not agent_events:
                return {'total_calls': 0}
            
            errors = sum(1 for e in agent_events if e.result_type == 'error')
            blocked = sum(1 for e in agent_events if e.result_type == 'blocked')
            
            tool_counts = defaultdict(int)
            for e in agent_events:
                tool_counts[e.tool_name] += 1
            
            return {
                'total_calls': len(agent_events),
                'errors': errors,
                'blocked': blocked,
                'error_rate': errors / len(agent_events),
                'tool_distribution': dict(tool_counts)
            }
    
    def detect_anomalies(self, agent_id: str) -> List[Dict]:
        """Detect anomalies for agent"""
        anomalies = []
        stats = self.get_agent_stats(agent_id)
        
        # High error rate
        if stats.get('error_rate', 0) > self.error_rate_threshold:
            anomalies.append({
                'type': 'high_error_rate',
                'severity': 'medium',
                'value': stats['error_rate']
            })
        
        # High call rate
        if stats.get('total_calls', 0) > self.call_rate_threshold:
            anomalies.append({
                'type': 'high_call_rate',
                'severity': 'medium',
                'value': stats['total_calls']
            })
        
        # Blocked calls
        if stats.get('blocked', 0) > 5:
            anomalies.append({
                'type': 'multiple_blocked_calls',
                'severity': 'high',
                'value': stats['blocked']
            })
        
        return anomalies
    
    def get_summary(self) -> Dict:
        """Get overall summary"""
        with self.lock:
            if not self.events:
                return {'total_calls': 0}
            
            by_tool = defaultdict(int)
            by_result = defaultdict(int)
            by_agent = defaultdict(int)
            
            for e in self.events:
                by_tool[e.tool_name] += 1
                by_result[e.result_type] += 1
                by_agent[e.agent_id] += 1
            
            return {
                'total_calls': len(self.events),
                'by_tool': dict(by_tool),
                'by_result': dict(by_result),
                'top_agents': dict(sorted(by_agent.items(), 
                                         key=lambda x: -x[1])[:10])
            }
```

---

## 6. SENTINEL Integration

```python
from dataclasses import dataclass
import hashlib

@dataclass
class ToolSecurityConfig:
    """Tool security configuration"""
    enable_sandbox: bool = True
    max_memory_mb: int = 100
    max_timeout_seconds: float = 30.0
    enable_monitoring: bool = True

class SENTINELToolEngine:
    """Tool security engine for SENTINEL"""
    
    def __init__(self, config: ToolSecurityConfig):
        self.config = config
        self.registry = ToolRegistry()
        self.sandbox = ToolSandbox(max_memory_mb=config.max_memory_mb)
        self.executor = SafeToolExecutor(self.registry, self.sandbox)
        
        if config.enable_monitoring:
            self.monitor = ToolCallMonitor()
        else:
            self.monitor = None
        
        # Register default safe tools
        self._register_defaults()
    
    def _register_defaults(self):
        """Register default safe tools"""
        self.registry.register(ToolDefinition(
            name="get_time",
            description="Get current time",
            category=ToolCategory.READ_ONLY,
            handler=lambda p, c: datetime.utcnow().isoformat()
        ))
        
        self.registry.register(ToolDefinition(
            name="calculate",
            description="Simple calculator",
            category=ToolCategory.READ_ONLY,
            parameters=[
                ParameterSchema("expression", ParameterType.STRING,
                               max_length=100,
                               pattern=r'^[\d\+\-\*\/\.\(\)\s]+$')
            ],
            handler=lambda p, c: eval(p['expression'])  # Safe due to pattern
        ))
    
    def register_tool(self, tool: ToolDefinition):
        """Register a tool"""
        self.registry.register(tool)
    
    def execute(self, tool_name: str, params: Dict,
                agent_id: str, session_id: str) -> ExecutionResult:
        """Execute a tool call"""
        request = ToolCallRequest(
            tool_name=tool_name,
            parameters=params,
            agent_id=agent_id,
            session_id=session_id
        )
        
        result = self.executor.execute(request)
        
        # Monitor
        if self.monitor:
            event = ToolCallEvent(
                timestamp=datetime.utcnow(),
                tool_name=tool_name,
                agent_id=agent_id,
                session_id=session_id,
                parameters_hash=hashlib.md5(str(params).encode()).hexdigest()[:8],
                result_type='success' if result.success else 'error',
                execution_time_ms=result.execution_time_ms,
                error=result.error
            )
            self.monitor.record(event)
        
        return result
    
    def get_anomalies(self, agent_id: str) -> List[Dict]:
        """Get anomalies for agent"""
        if self.monitor:
            return self.monitor.detect_anomalies(agent_id)
        return []
    
    def get_stats(self) -> Dict:
        """Get overall stats"""
        stats = {
            'registered_tools': len(self.registry.tools),
            'safe_tools': len(self.registry.get_safe_tools())
        }
        
        if self.monitor:
            stats['monitoring'] = self.monitor.get_summary()
        
        return stats
```

---

## 7. Резюме

| Компонент | Описание |
|-----------|----------|
| **ToolDefinition** | Schema с parameters и permissions |
| **ToolRegistry** | Whitelist разрешённых tools |
| **Validator** | Parameter validation + injection check |
| **Sandbox** | Изолированное выполнение |
| **Monitor** | Anomaly detection для tool calls |

---

## Следующий урок

→ [03. Trust & Authorization](../03-trust/README.md)

---

*AI Security Academy | Track 04: Agentic Security | Module 04.2: Tool Security*
