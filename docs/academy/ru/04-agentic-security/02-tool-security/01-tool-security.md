# Безопасность инструментов для AI агентов

> **Уровень:** Продвинутый  
> **Время:** 55 минут  
> **Трек:** 04 — Агентная безопасность  
> **Модуль:** 04.2 — Безопасность инструментов  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять риски использования инструментов в AI агентах
- [ ] Реализовать валидацию и песочницу инструментов
- [ ] Построить пайплайн мониторинга вызовов
- [ ] Интегрировать безопасность инструментов в SENTINEL

---

## 1. Обзор безопасности инструментов

```
┌────────────────────────────────────────────────────────────────────┐
│              THREAT MODEL БЕЗОПАСНОСТИ ИНСТРУМЕНТОВ               │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Векторы атак:                                                     │
│  ├── Tool Injection: Неавторизованные вызовы                     │
│  ├── Parameter Injection: Вредоносные параметры                  │
│  ├── Privilege Escalation: Повышенные разрешения                 │
│  └── Chain Attacks: Комбинированное злоупотребление              │
│                                                                    │
│  Слои защиты:                                                      │
│  ├── Tool Registry: Whitelist                                     │
│  ├── Parameter Validation: Валидация схемы                        │
│  ├── Permission Checks: RBAC                                      │
│  ├── Execution Sandbox: Изоляция                                  │
│  └── Output Filtering: Валидация результатов                      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Реестр инструментов

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

@dataclass
class ParameterSchema:
    """Схема параметра"""
    name: str
    param_type: ParameterType
    required: bool = True
    default: Any = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[Any]] = None
    
    def validate(self, value: Any) -> tuple[bool, str]:
        if value is None:
            if self.required:
                return False, f"{self.name} обязателен"
            return True, ""
        
        # Проверка типа
        type_map = {
            ParameterType.STRING: str,
            ParameterType.INTEGER: int,
            ParameterType.FLOAT: (int, float),
            ParameterType.BOOLEAN: bool
        }
        if self.param_type in type_map:
            if not isinstance(value, type_map[self.param_type]):
                return False, f"{self.name} неверный тип"
        
        # Валидации строк
        if isinstance(value, str):
            if self.max_length and len(value) > self.max_length:
                return False, f"{self.name} слишком длинный"
            if self.pattern and not re.match(self.pattern, value):
                return False, f"{self.name} недопустимый формат"
        
        if self.enum_values and value not in self.enum_values:
            return False, f"{self.name} не в разрешённых значениях"
        
        return True, ""

@dataclass
class ToolDefinition:
    """Определение инструмента"""
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
    """Реестр инструментов"""
    
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

## 3. Валидация вызовов

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
    """Валидирует вызовы инструментов"""
    
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
            return ValidationResult(False, [f"Неизвестный инструмент: {request.tool_name}"])
        
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
                        issues.append(f"Опасный паттерн в {key}")
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

## 4. Песочница инструментов

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError

@dataclass
class ExecutionResult:
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: float = 0

class ToolSandbox:
    """Изолированное выполнение"""
    
    def __init__(self, max_output_size: int = 100000):
        self.max_output = max_output_size
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def execute(self, tool: ToolDefinition, params: Dict) -> ExecutionResult:
        import time
        start = time.time()
        
        if tool.handler is None:
            return ExecutionResult(False, None, "Нет обработчика")
        
        try:
            future = self.executor.submit(tool.handler, params, {})
            result = future.result(timeout=tool.timeout_seconds)
            
            output = str(result)
            if len(output) > self.max_output:
                result = output[:self.max_output] + "... [обрезано]"
            
            return ExecutionResult(True, result,
                                  execution_time_ms=(time.time() - start) * 1000)
        except TimeoutError:
            return ExecutionResult(False, None, "Таймаут",
                                  execution_time_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ExecutionResult(False, None, str(e),
                                  execution_time_ms=(time.time() - start) * 1000)

class SafeToolExecutor:
    """Безопасный исполнитель инструментов"""
    
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
            return ExecutionResult(False, None, "Превышен rate limit")
        
        # Валидация
        validation = self.validator.validate(request)
        if not validation.valid:
            return ExecutionResult(False, None, str(validation.errors))
        
        # Выполнение
        return self.sandbox.execute(tool, validation.sanitized_params)
```

---

## 5. Мониторинг

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
    """Мониторинг вызовов инструментов"""
    
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

## 6. Интеграция с SENTINEL

```python
class SENTINELToolEngine:
    """Безопасность инструментов для SENTINEL"""
    
    def __init__(self, config):
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

## 7. Итоги

| Компонент | Описание |
|-----------|----------|
| **ToolDefinition** | Схема с параметрами |
| **ToolRegistry** | Whitelist разрешённых инструментов |
| **Validator** | Проверка параметров + инъекций |
| **Sandbox** | Изолированное выполнение |
| **Monitor** | Детекция аномалий |

---

## Следующий урок

→ [03. Trust & Authorization](../03-trust/README.md)

---

*AI Security Academy | Трек 04: Агентная безопасность | Модуль 04.2: Безопасность инструментов*
