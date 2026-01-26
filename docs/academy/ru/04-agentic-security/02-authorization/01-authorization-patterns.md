# Agent Authorization Patterns

> **Урок:** 04.2.1 - Authorization for Agents  
> **Время:** 45 минут  
> **Prerequisites:** Agentic System Basics

---

## Цели обучения

После завершения этого урока вы сможете:

1. Проектировать authorization models для AI agents
2. Реализовать capability-based security
3. Применять least-privilege principles
4. Строить auditable authorization systems

---

## Why Agent Authorization?

AI agents perform actions with real-world consequences:

| Action | Without Authorization | With Authorization |
|--------|----------------------|-------------------|
| **File access** | Any file accessible | Scoped to directories |
| **API calls** | Unlimited | Rate-limited, scoped |
| **Commands** | Shell access | Allowlisted operations |
| **Data access** | All data visible | Need-to-know basis |

---

## Authorization Models

### 1. Role-Based Access Control (RBAC)

```python
from dataclasses import dataclass
from typing import Set, List
from enum import Enum

class Permission(Enum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    EXECUTE_CODE = "execute_code"
    NETWORK_ACCESS = "network_access"

@dataclass
class Role:
    name: str
    permissions: Set[Permission]
    resource_scopes: dict

class RBACManager:
    """Role-based access control for agents."""
    
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
                Permission.WRITE_FILES: ["/project/src/*"]
            }
        ),
    }
    
    def check_permission(
        self, 
        permission: Permission, 
        resource: str = None
    ) -> dict:
        """Check if agent has permission for resource."""
        
        for role in self.roles:
            if permission in role.permissions:
                if self._resource_in_scope(role, permission, resource):
                    return {"allowed": True, "role": role.name}
        
        return {"allowed": False, "reason": f"No role grants {permission.value}"}
```

---

### 2. Capability-Based Security

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import secrets

@dataclass
class Capability:
    """Unforgeable capability token."""
    
    id: str = field(default_factory=lambda: secrets.token_urlsafe(16))
    action: str = ""
    resource: str = ""
    expires: Optional[datetime] = None
    revoked: bool = False
    
    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if self.expires and datetime.utcnow() > self.expires:
            return False
        return True

class CapabilityManager:
    """Manage capabilities for agents."""
    
    def __init__(self):
        self.capabilities: Dict[str, Capability] = {}
    
    def grant(
        self, 
        action: str, 
        resource: str,
        ttl_seconds: int = 3600
    ) -> Capability:
        """Grant a new capability."""
        
        cap = Capability(
            action=action,
            resource=resource,
            expires=datetime.utcnow() + timedelta(seconds=ttl_seconds)
        )
        
        self.capabilities[cap.id] = cap
        return cap
    
    def check(self, cap_id: str, action: str, resource: str) -> dict:
        """Check if capability allows action on resource."""
        
        if cap_id not in self.capabilities:
            return {"allowed": False, "reason": "Capability not found"}
        
        cap = self.capabilities[cap_id]
        
        if not cap.is_valid():
            return {"allowed": False, "reason": "Capability expired"}
        
        if cap.action != action:
            return {"allowed": False, "reason": f"Capability is for {cap.action}"}
        
        return {"allowed": True, "capability": cap}
```

---

### 3. Attribute-Based Access Control (ABAC)

```python
@dataclass
class Policy:
    """ABAC policy with conditions."""
    
    name: str
    effect: str  # "allow" or "deny"
    actions: list
    resources: list
    condition: Callable[[Dict[str, Any]], bool]

# Example policies
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

## SENTINEL Integration

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
    with open(path, 'w') as f:
        f.write(content)
```

---

## Ключевые выводы

1. **Least privilege by default** - Start minimal, grant as needed
2. **Capabilities over roles** - Unforgeable, time-limited tokens
3. **Context-aware decisions** - Use ABAC for complex rules
4. **Audit everything** - Log all decisions for forensics
5. **Support escalation** - But require human approval

---

*AI Security Academy | Урок 04.2.1*
