# Паттерны авторизации агентов

> **Урок:** 04.2.1 - Authorization for Agents  
> **Время:** 45 минут  
> **Пререквизиты:** Agentic System Basics

---

## Цели обучения

К концу этого урока вы сможете:

1. Проектировать модели авторизации для AI агентов
2. Реализовывать capability-based security
3. Применять принцип least-privilege
4. Строить аудируемые системы авторизации

---

## Зачем авторизация агентов?

AI агенты выполняют действия с реальными последствиями:

| Действие | Без авторизации | С авторизацией |
|----------|-----------------|----------------|
| **Доступ к файлам** | Любой файл доступен | Scope по директориям |
| **API вызовы** | Unlimited | Rate-limited, scoped |
| **Команды** | Shell access | Allowlisted операции |
| **Доступ к данным** | Все данные видны | Need-to-know basis |

---

## Модели авторизации

### 1. RBAC (Role-Based Access Control)

```python
from dataclasses import dataclass
from typing import Set, List
from enum import Enum

class Permission(Enum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    EXECUTE_CODE = "execute_code"
    NETWORK_ACCESS = "network_access"
    DATABASE_READ = "database_read"
    DATABASE_WRITE = "database_write"

@dataclass
class Role:
    name: str
    permissions: Set[Permission]
    resource_scopes: dict  # permission -> allowed resources

class RBACManager:
    """Role-based access control для агентов."""
    
    ROLES = {
        "assistant": Role(
            name="assistant",
            permissions={Permission.READ_FILES},
            resource_scopes={
                Permission.READ_FILES: ["/public/*", "/docs/*"]
            }
        ),
        "developer": Role(
            name="developer",
            permissions={
                Permission.READ_FILES, 
                Permission.WRITE_FILES,
                Permission.EXECUTE_CODE
            },
            resource_scopes={
                Permission.READ_FILES: ["/project/*"],
                Permission.WRITE_FILES: ["/project/src/*"],
                Permission.EXECUTE_CODE: ["python", "npm"]
            }
        ),
        "admin": Role(
            name="admin",
            permissions=set(Permission),
            resource_scopes={}  # All resources
        ),
    }
    
    def __init__(self, agent_id: str, assigned_roles: List[str]):
        self.agent_id = agent_id
        self.roles = [self.ROLES[r] for r in assigned_roles if r in self.ROLES]
    
    def check_permission(
        self, 
        permission: Permission, 
        resource: str = None
    ) -> dict:
        """Проверить имеет ли агент permission на resource."""
        
        for role in self.roles:
            if permission in role.permissions:
                if self._resource_in_scope(role, permission, resource):
                    return {
                        "allowed": True,
                        "role": role.name,
                        "reason": f"Permission {permission.value} granted by role {role.name}"
                    }
        
        return {
            "allowed": False,
            "reason": f"No role grants {permission.value} for {resource}"
        }
    
    def _resource_in_scope(
        self, 
        role: Role, 
        permission: Permission, 
        resource: str
    ) -> bool:
        """Проверить находится ли resource в allowed scope."""
        import fnmatch
        
        if permission not in role.resource_scopes:
            return True  # No scope restriction
        
        scopes = role.resource_scopes[permission]
        return any(fnmatch.fnmatch(resource, scope) for scope in scopes)
```

---

### 2. Capability-Based Security

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets

@dataclass
class Capability:
    """Unforgeable capability token."""
    
    id: str = field(default_factory=lambda: secrets.token_urlsafe(16))
    action: str = ""
    resource: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    expires: Optional[datetime] = None
    revoked: bool = False
    
    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if self.expires and datetime.utcnow() > self.expires:
            return False
        return True

class CapabilityManager:
    """Управление capabilities для агентов."""
    
    def __init__(self):
        self.capabilities: Dict[str, Capability] = {}
    
    def grant(
        self, 
        action: str, 
        resource: str,
        constraints: dict = None,
        ttl_seconds: int = 3600
    ) -> Capability:
        """Выдать новую capability."""
        
        cap = Capability(
            action=action,
            resource=resource,
            constraints=constraints or {},
            expires=datetime.utcnow() + timedelta(seconds=ttl_seconds)
        )
        
        self.capabilities[cap.id] = cap
        return cap
    
    def check(self, cap_id: str, action: str, resource: str) -> dict:
        """Проверить позволяет ли capability action на resource."""
        
        if cap_id not in self.capabilities:
            return {"allowed": False, "reason": "Capability not found"}
        
        cap = self.capabilities[cap_id]
        
        if not cap.is_valid():
            return {"allowed": False, "reason": "Capability expired or revoked"}
        
        if cap.action != action:
            return {"allowed": False, "reason": f"Capability is for {cap.action}, not {action}"}
        
        if not self._resource_matches(cap.resource, resource):
            return {"allowed": False, "reason": "Resource not covered by capability"}
        
        return {"allowed": True, "capability": cap}
    
    def revoke(self, cap_id: str):
        """Отозвать capability."""
        if cap_id in self.capabilities:
            self.capabilities[cap_id].revoked = True
```

---

### 3. ABAC (Attribute-Based Access Control)

```python
from dataclasses import dataclass
from typing import Callable, Dict, Any

@dataclass
class Policy:
    """ABAC policy с условиями."""
    
    name: str
    effect: str  # "allow" или "deny"
    actions: list
    resources: list
    condition: Callable[[Dict[str, Any]], bool]

class ABACManager:
    """Attribute-based access control."""
    
    def __init__(self):
        self.policies: list[Policy] = []
    
    def add_policy(self, policy: Policy):
        self.policies.append(policy)
    
    def evaluate(
        self, 
        action: str, 
        resource: str, 
        context: Dict[str, Any]
    ) -> dict:
        """Evaluate policies для решения авторизации."""
        
        applicable_policies = []
        
        for policy in self.policies:
            if self._action_matches(action, policy.actions):
                if self._resource_matches(resource, policy.resources):
                    if policy.condition(context):
                        applicable_policies.append(policy)
        
        # Deny имеет приоритет
        for policy in applicable_policies:
            if policy.effect == "deny":
                return {
                    "allowed": False,
                    "policy": policy.name,
                    "reason": f"Denied by policy: {policy.name}"
                }
        
        # Any allow grants access
        for policy in applicable_policies:
            if policy.effect == "allow":
                return {
                    "allowed": True,
                    "policy": policy.name
                }
        
        # Default deny
        return {"allowed": False, "reason": "No policy grants access"}

# Примеры policies
time_based_policy = Policy(
    name="business_hours_only",
    effect="deny",
    actions=["write", "delete"],
    resources=["*"],
    condition=lambda ctx: not (9 <= ctx.get("hour", 12) <= 17)
)

high_risk_review = Policy(
    name="require_review_for_production",
    effect="deny",
    actions=["deploy", "delete"],
    resources=["production/*"],
    condition=lambda ctx: not ctx.get("human_approved", False)
)
```

---

## Паттерны имплементации

### 1. Authorization Middleware

```python
class AuthorizationMiddleware:
    """Middleware для авторизации tool агентов."""
    
    def __init__(self, authz_manager):
        self.authz = authz_manager
        self.audit_log = []
    
    def wrap_tool(self, tool_func, required_permission: Permission):
        """Обернуть tool с проверкой авторизации."""
        
        async def wrapped(agent_context: dict, *args, **kwargs):
            # Извлечь resource из аргументов
            resource = self._extract_resource(tool_func.__name__, args, kwargs)
            
            # Проверить авторизацию
            result = self.authz.check_permission(
                required_permission, 
                resource
            )
            
            # Залогировать попытку
            self._log_attempt(
                agent_context.get("agent_id"),
                tool_func.__name__,
                resource,
                result
            )
            
            if not result["allowed"]:
                raise PermissionError(result["reason"])
            
            # Выполнить tool
            return await tool_func(*args, **kwargs)
        
        return wrapped
```

---

### 2. Dynamic Permission Escalation

```python
class DynamicEscalationManager:
    """Обработка временной эскалации permissions."""
    
    def __init__(self, base_manager, approval_callback):
        self.base = base_manager
        self.approve = approval_callback
        self.temporary_grants = {}
    
    async def request_escalation(
        self, 
        agent_id: str,
        permission: Permission,
        resource: str,
        justification: str
    ) -> dict:
        """Запросить временные elevated permissions."""
        
        # Проверить нужна ли эскалация
        base_check = self.base.check_permission(permission, resource)
        if base_check["allowed"]:
            return base_check
        
        # Запросить human approval
        approval = await self.approve({
            "agent_id": agent_id,
            "permission": permission.value,
            "resource": resource,
            "justification": justification
        })
        
        if approval["approved"]:
            # Выдать temporary capability
            grant_id = self._grant_temporary(
                agent_id, permission, resource,
                ttl_seconds=approval.get("ttl", 300)
            )
            
            return {
                "allowed": True,
                "grant_id": grant_id,
                "temporary": True,
                "expires_in": approval.get("ttl", 300)
            }
        
        return {
            "allowed": False,
            "reason": "Escalation request denied"
        }
```

---

## Интеграция с SENTINEL

```python
from sentinel import configure, AuthorizationGuard

configure(
    authorization=True,
    audit_logging=True,
    escalation_workflow=True
)

auth_guard = AuthorizationGuard(
    default_role="assistant",
    require_capability=True,
    audit_all_decisions=True
)

@auth_guard.require(Permission.WRITE_FILES, resource_arg="path")
async def write_file(path: str, content: str):
    # Автоматически авторизовано перед выполнением
    with open(path, 'w') as f:
        f.write(content)
```

---

## Ключевые выводы

1. **Least privilege по умолчанию** — Начинать минимально, выдавать по необходимости
2. **Capabilities над roles** — Unforgeable, time-limited tokens
3. **Context-aware решения** — Использовать ABAC для сложных правил
4. **Аудит всего** — Логировать все решения для forensics
5. **Поддержка эскалации** — Но требовать human approval

---

*AI Security Academy | Урок 04.2.1*
