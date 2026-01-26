# Agent Authorization Patterns

> **Lesson:** 04.2.1 - Authorization for Agents  
> **Time:** 45 minutes  
> **Prerequisites:** Agentic System Basics

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Design authorization models for AI agents
2. Implement capability-based security
3. Apply least-privilege principles
4. Build auditable authorization systems

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
    DATABASE_READ = "database_read"
    DATABASE_WRITE = "database_write"

@dataclass
class Role:
    name: str
    permissions: Set[Permission]
    resource_scopes: dict  # permission -> allowed resources

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
        """Check if agent has permission for resource."""
        
        for role in self.roles:
            if permission in role.permissions:
                # Check resource scope
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
        """Check if resource is within allowed scope."""
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
    """Manage capabilities for agents."""
    
    def __init__(self):
        self.capabilities: Dict[str, Capability] = {}
    
    def grant(
        self, 
        action: str, 
        resource: str,
        constraints: dict = None,
        ttl_seconds: int = 3600
    ) -> Capability:
        """Grant a new capability."""
        
        cap = Capability(
            action=action,
            resource=resource,
            constraints=constraints or {},
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
            return {"allowed": False, "reason": "Capability expired or revoked"}
        
        if cap.action != action:
            return {"allowed": False, "reason": f"Capability is for {cap.action}, not {action}"}
        
        if not self._resource_matches(cap.resource, resource):
            return {"allowed": False, "reason": "Resource not covered by capability"}
        
        return {"allowed": True, "capability": cap}
    
    def revoke(self, cap_id: str):
        """Revoke a capability."""
        if cap_id in self.capabilities:
            self.capabilities[cap_id].revoked = True
    
    def _resource_matches(self, pattern: str, resource: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(resource, pattern)
```

---

### 3. Attribute-Based Access Control (ABAC)

```python
from dataclasses import dataclass
from typing import Callable, Dict, Any

@dataclass
class Policy:
    """ABAC policy with conditions."""
    
    name: str
    effect: str  # "allow" or "deny"
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
        """Evaluate policies for authorization decision."""
        
        applicable_policies = []
        
        for policy in self.policies:
            if self._action_matches(action, policy.actions):
                if self._resource_matches(resource, policy.resources):
                    if policy.condition(context):
                        applicable_policies.append(policy)
        
        # Deny takes precedence
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

## Implementation Patterns

### 1. Authorization Middleware

```python
class AuthorizationMiddleware:
    """Middleware for agent tool authorization."""
    
    def __init__(self, authz_manager):
        self.authz = authz_manager
        self.audit_log = []
    
    def wrap_tool(self, tool_func, required_permission: Permission):
        """Wrap tool with authorization check."""
        
        async def wrapped(agent_context: dict, *args, **kwargs):
            # Extract resource from arguments
            resource = self._extract_resource(tool_func.__name__, args, kwargs)
            
            # Check authorization
            result = self.authz.check_permission(
                required_permission, 
                resource
            )
            
            # Log attempt
            self._log_attempt(
                agent_context.get("agent_id"),
                tool_func.__name__,
                resource,
                result
            )
            
            if not result["allowed"]:
                raise PermissionError(result["reason"])
            
            # Execute tool
            return await tool_func(*args, **kwargs)
        
        return wrapped
    
    def _log_attempt(self, agent_id, action, resource, result):
        self.audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "action": action,
            "resource": resource,
            "allowed": result["allowed"],
            "reason": result.get("reason")
        })
```

---

### 2. Dynamic Permission Escalation

```python
class DynamicEscalationManager:
    """Handle temporary permission escalation."""
    
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
        """Request temporary elevated permissions."""
        
        # Check if escalation is needed
        base_check = self.base.check_permission(permission, resource)
        if base_check["allowed"]:
            return base_check
        
        # Request human approval
        approval = await self.approve({
            "agent_id": agent_id,
            "permission": permission.value,
            "resource": resource,
            "justification": justification
        })
        
        if approval["approved"]:
            # Grant temporary capability
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

### 3. Audit Trail

```python
class AuthorizationAuditor:
    """Comprehensive audit logging for authorization."""
    
    def __init__(self, storage_backend):
        self.storage = storage_backend
    
    def log_decision(
        self,
        agent_id: str,
        action: str,
        resource: str,
        decision: dict,
        context: dict = None
    ):
        """Log authorization decision."""
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "action": action,
            "resource": resource,
            "allowed": decision.get("allowed"),
            "policy": decision.get("policy"),
            "reason": decision.get("reason"),
            "context": context or {},
            "session_id": context.get("session_id") if context else None
        }
        
        self.storage.append(entry)
        
        # Alert on suspicious patterns
        if self._is_suspicious(agent_id, action):
            self._send_alert(entry)
    
    def _is_suspicious(self, agent_id: str, action: str) -> bool:
        """Detect suspicious authorization patterns."""
        
        # Check recent denials
        recent = self.storage.query(
            agent_id=agent_id,
            since=datetime.utcnow() - timedelta(minutes=5)
        )
        
        denial_count = sum(1 for e in recent if not e["allowed"])
        
        # Many denials in short time = suspicious
        return denial_count >= 5
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
    # Automatically authorized before execution
    with open(path, 'w') as f:
        f.write(content)
```

---

## Key Takeaways

1. **Least privilege by default** - Start minimal, grant as needed
2. **Capabilities over roles** - Unforgeable, time-limited tokens
3. **Context-aware decisions** - Use ABAC for complex rules
4. **Audit everything** - Log all decisions for forensics
5. **Support escalation** - But require human approval

---

*AI Security Academy | Lesson 04.2.1*
