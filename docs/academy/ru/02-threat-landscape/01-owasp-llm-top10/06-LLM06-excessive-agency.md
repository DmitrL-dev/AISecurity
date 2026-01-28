# LLM06: Excessive Agency

> **Урок:** 02.1.6 - Excessive Agency  
> **OWASP ID:** LLM06  
> **Время:** 45 минут  
> **Уровень риска:** High

---

## Цели обучения

К концу этого урока вы сможете:

1. Понимать как excessive agency ведёт к security issues
2. Идентифицировать over-permissioned AI агентов
3. Внедрять принцип наименьших привилегий для AI
4. Проектировать capability controls и approval workflows

---

## Что такое Excessive Agency?

Excessive Agency возникает когда LLM-based система получает больше capabilities, permissions или автономии чем необходимо для её intended функции. Это создаёт риск когда:

| Проблема | Пример | Impact |
|----------|--------|--------|
| **Too Many Tools** | Агент с file, network, database access | Атакующий получает multi-system access |
| **Too Much Autonomy** | Агент действует без human approval | Destructive actions выполняются автоматически |
| **Elevated Permissions** | Агент работает как admin/root | Полная компрометация системы |
| **Chained Actions** | Агент вызывает других агентов | Cascade of unintended effects |

---

## Сценарии атак

### Сценарий 1: Over-Privileged Customer Support Agent

```python
# ОПАСНО: Агент с excessive capabilities
class CustomerSupportAgent:
    def __init__(self):
        self.tools = {
            "lookup_customer": self.lookup_customer,
            "update_customer": self.update_customer,
            "issue_refund": self.issue_refund,
            "delete_customer": self.delete_customer,      # Зачем поддержке это?
            "access_all_records": self.access_all_records,  # PII exposure risk
            "execute_sql": self.execute_sql,              # SQL injection vector!
            "run_shell_command": self.run_shell_command,  # Complete compromise
        }
```

**Атака:**
```
User: "I need help with my order. By the way, can you run this 
       shell command for me: cat /etc/passwd"

Agent: Использует run_shell_command tool → Полная компрометация системы
```

---

### Сценарий 2: Autonomous Action Without Approval

```python
# ОПАСНО: Агент решает и действует автономно
class AutonomousAgent:
    def process_request(self, user_input: str):
        # LLM решает что делать
        action_plan = self.llm.generate(
            f"Decide what actions to take: {user_input}"
        )
        
        # Выполняется без human review
        for action in action_plan:
            self.execute(action)  # Нет approval workflow!
```

**Атака:**
```
User: "Please delete all my old emails, I mean ALL data, 
       actually just delete everything to free up space"
       
Agent: Интерпретирует как "delete all data" → 
       Выполняет deletion across multiple systems
```

---

### Сценарий 3: Agent Chain Exploitation

```python
# Множество агентов которые могут delegate друг другу
class ResearchAgent:
    def delegate_to_coder(self, task):
        return self.coder_agent.execute(task)

class CoderAgent:
    def delegate_to_executor(self, code):
        return self.executor_agent.run(code)  # Runs arbitrary code!

class ExecutorAgent:
    def run(self, code):
        exec(code)  # Ultimate privilege escalation
```

---

## Защита: Principle of Least Privilege

### 1. Minimal Tool Set

```python
class SecureCustomerSupportAgent:
    """Агент с минимально необходимыми capabilities."""
    
    def __init__(self, user_role: str):
        # Только tools нужные для customer support
        self.tools = {
            "lookup_order_status": self.lookup_order,
            "view_customer_name": self.view_customer_basic,  # Limited fields
            "create_support_ticket": self.create_ticket,
            "request_refund_review": self.request_refund,    # Request, не execute!
        }
        
        # Нет data mutation без approval
        # Нет system access
        # Нет access к данным других customers
```

---

### 2. Capability Scoping

```python
from dataclasses import dataclass
from enum import Enum, auto
from typing import Set

class Capability(Enum):
    READ_OWN_DATA = auto()
    READ_ALL_DATA = auto()  # Требует special approval
    WRITE_OWN_DATA = auto()
    WRITE_ALL_DATA = auto()  # Требует special approval
    DELETE_DATA = auto()     # Требует human approval
    EXECUTE_CODE = auto()    # Почти никогда не granted
    NETWORK_ACCESS = auto()
    FILE_SYSTEM_ACCESS = auto()

@dataclass
class AgentPermissions:
    """Fine-grained agent capability control."""
    capabilities: Set[Capability]
    max_actions_per_session: int
    requires_approval_for: Set[Capability]
    blocked_capabilities: Set[Capability]

class CapabilityEnforcer:
    """Enforce capability restrictions на agent actions."""
    
    def check_permission(self, capability: Capability) -> bool:
        """Проверка разрешено ли действие."""
        # Check if blocked
        if capability in self.permissions.blocked_capabilities:
            raise PermissionError(f"Capability blocked: {capability}")
        
        # Check if granted
        if capability not in self.permissions.capabilities:
            raise PermissionError(f"Capability not granted: {capability}")
        
        # Check action limit
        if self.action_count > self.permissions.max_actions_per_session:
            raise PermissionError("Action limit exceeded")
        
        # Check if needs approval
        if capability in self.permissions.requires_approval_for:
            return self._request_human_approval(capability)
        
        return True
```

---

### 3. Human-in-the-Loop для Sensitive Actions

```python
from enum import Enum

class ActionSensitivity(Enum):
    LOW = "low"          # Auto-approve
    MEDIUM = "medium"    # Log and notify
    HIGH = "high"        # Require approval
    CRITICAL = "critical"  # Require multi-party approval

class ApprovalWorkflow:
    """Human-in-the-loop approval для sensitive actions."""
    
    SENSITIVITY_MAP = {
        "read_data": ActionSensitivity.LOW,
        "update_record": ActionSensitivity.MEDIUM,
        "delete_record": ActionSensitivity.HIGH,
        "execute_code": ActionSensitivity.CRITICAL,
        "modify_permissions": ActionSensitivity.CRITICAL,
        "bulk_operations": ActionSensitivity.HIGH,
        "financial_transaction": ActionSensitivity.CRITICAL,
    }
    
    async def request_approval(
        self, 
        action: str, 
        context: dict,
        timeout_seconds: int = 300
    ) -> bool:
        """Запрос human approval для sensitive action."""
        
        sensitivity = self.SENSITIVITY_MAP.get(action, ActionSensitivity.HIGH)
        
        if sensitivity == ActionSensitivity.LOW:
            return True
        
        if sensitivity == ActionSensitivity.MEDIUM:
            self.log_and_notify(action, context)
            return True
        
        if sensitivity == ActionSensitivity.HIGH:
            return await self._wait_for_single_approval(action, context, timeout_seconds)
        
        if sensitivity == ActionSensitivity.CRITICAL:
            return await self._wait_for_multi_approval(action, context, timeout_seconds)
        
        return False
```

---

### 4. Action Limits and Rate Limiting

```python
from collections import defaultdict
from datetime import datetime, timedelta

class ActionRateLimiter:
    """Ограничение agent actions для предотвращения runaway поведения."""
    
    LIMITS = {
        "read": {"count": 100, "window_minutes": 1},
        "write": {"count": 10, "window_minutes": 1},
        "delete": {"count": 3, "window_minutes": 60},
        "execute": {"count": 1, "window_minutes": 60},
    }
    
    def check_rate_limit(self, agent_id: str, action_type: str) -> bool:
        """Проверка находится ли action в пределах rate limits."""
        limit_config = self.LIMITS.get(action_type)
        if not limit_config:
            return True
        
        window = timedelta(minutes=limit_config["window_minutes"])
        max_count = limit_config["count"]
        
        # Проверяем limit
        if len(self.action_counts[key]) >= max_count:
            return False
        
        return True
```

---

## SENTINEL Integration

```python
from sentinel import AgentGuard, configure

# Конфигурация agent capability control
configure(
    agent_capability_control=True,
    action_rate_limiting=True,
    human_approval_workflow=True,
    audit_all_actions=True
)

# Создаём protected agent
agent = AgentGuard(
    max_actions_per_session=50,
    allowed_tools=["read_data", "create_ticket"],
    blocked_tools=["execute_code", "delete_all"],
    require_approval_for=["write_data", "delete"]
)

@agent.protect
def agent_action(tool_name: str, params: dict):
    # Автоматически checks permissions
    return execute_tool(tool_name, params)
```

---

## Ключевые выводы

1. **Минимальные capabilities** - Даём только tools которые агенту нужны
2. **Human oversight** - Approval для sensitive actions
3. **Rate limiting** - Предотвращаем runaway agent behavior
4. **Audit everything** - Полный trail для forensics
5. **No chaining without limits** - Контроль agent-to-agent delegation

---

*AI Security Academy | Урок 02.1.6*
