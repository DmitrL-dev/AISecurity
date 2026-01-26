# RBAC для AI Agents

> **Уровень:** �����������  
> **Время:** 55 минут  
> **Трек:** 04 — Agentic Security  
> **Модуль:** 04.3 — Trust & Authorization  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять Role-Based Access Control для AI agents
- [ ] Имплементировать RBAC систему с policies
- [ ] Построить permission enforcement для agent actions
- [ ] Интегрировать RBAC в SENTINEL framework

---

## 1. RBAC для Agents Overview

### 1.1 Зачем RBAC для Agents?

AI agents выполняют действия от имени пользователей. RBAC контролирует какие действия доступны агентам.

```
┌────────────────────────────────────────────────────────────────────┐
│              RBAC FOR AI AGENTS                                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Traditional (Human) RBAC:                                         │
│  User → Role → Permission → Resource                               │
│                                                                    │
│  Agent RBAC (Extended):                                            │
│  User → Agent → Role → Permission → Resource                       │
│       ↓                    ↓                                       │
│    Delegation          Constraints                                 │
│                                                                    │
│  Дополнительные измерения:                                        │
│  ├── Agent Identity: Какой агент запрашивает?                     │
│  ├── Delegation Chain: От какого user действует?                  │
│  ├── Context: В каком контексте (session, task)?                  │
│  ├── Time: Временные ограничения                                  │
│  └── Risk Level: Динамическая оценка риска                       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Ключевые концепции

```
RBAC Hierarchy для Agents:
├── Users
│   └── Human users, service accounts
├── Agents
│   └── AI instances (LLM agents, tool agents)
├── Roles
│   ├── Agent roles (Reader, Writer, Admin)
│   └── Task roles (Analyst, Developer, Reviewer)
├── Permissions
│   ├── Tool permissions
│   ├── Data permissions
│   └── Action permissions
└── Resources
    ├── Tools (APIs, functions)
    ├── Data (files, databases)
    └── Zones (trust boundaries)
```

---

## 2. RBAC Model Implementation

### 2.1 Core Entities

```python
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from datetime import datetime, timedelta
from enum import Enum
import hashlib

class PermissionType(Enum):
    TOOL_EXECUTE = "tool:execute"
    TOOL_READ = "tool:read"
    DATA_READ = "data:read"
    DATA_WRITE = "data:write"
    DATA_DELETE = "data:delete"
    NETWORK_EXTERNAL = "network:external"
    SYSTEM_ADMIN = "system:admin"

@dataclass
class Permission:
    """
    Single permission grant.
    Can include resource pattern and constraints.
    """
    type: PermissionType
    resource_pattern: str = "*"  # Glob pattern
    constraints: Dict = field(default_factory=dict)
    
    def matches(self, resource: str) -> bool:
        """Check if permission applies to resource"""
        import fnmatch
        return fnmatch.fnmatch(resource, self.resource_pattern)
    
    def to_string(self) -> str:
        return f"{self.type.value}:{self.resource_pattern}"

@dataclass
class Role:
    """
    Role groups related permissions.
    Supports hierarchy via parent roles.
    """
    name: str
    display_name: str
    permissions: List[Permission] = field(default_factory=list)
    parent_roles: List[str] = field(default_factory=list)
    description: str = ""
    
    # Constraints
    max_actions_per_minute: int = 100
    allowed_hours: List[int] = field(default_factory=lambda: list(range(24)))
    requires_approval: bool = False
    
    def has_permission(self, perm_type: PermissionType, resource: str) -> bool:
        """Check if role grants permission for resource"""
        for perm in self.permissions:
            if perm.type == perm_type and perm.matches(resource):
                return True
        return False

@dataclass
class Agent:
    """
    AI Agent entity with identity and assigned roles.
    """
    agent_id: str
    display_name: str
    agent_type: str  # llm, tool, composite
    roles: List[str] = field(default_factory=list)
    
    # Delegation
    delegated_from: Optional[str] = None  # User ID
    delegation_scope: List[str] = field(default_factory=list)
    
    # Trust
    trust_level: float = 0.5  # 0-1
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)
    
    @property
    def identity_hash(self) -> str:
        data = f"{self.agent_id}:{self.agent_type}:{self.delegated_from}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

@dataclass
class User:
    """
    Human user entity.
    """
    user_id: str
    username: str
    roles: List[str] = field(default_factory=list)
    
    # Agent delegation limits
    can_delegate_to_agents: bool = True
    max_delegated_agents: int = 5
    delegated_agents: List[str] = field(default_factory=list)

@dataclass
class AccessPolicy:
    """
    Access policy for specific resource patterns.
    """
    policy_id: str
    resource_pattern: str
    allowed_roles: List[str]
    required_conditions: Dict = field(default_factory=dict)
    deny_roles: List[str] = field(default_factory=list)
    priority: int = 0
    
    def applies_to(self, resource: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(resource, self.resource_pattern)
```

### 2.2 Permission Store

```python
from abc import ABC, abstractmethod
from collections import defaultdict

class PermissionStore(ABC):
    """Abstract permission store interface"""
    
    @abstractmethod
    def get_role(self, role_name: str) -> Optional[Role]:
        pass
    
    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        pass
    
    @abstractmethod
    def get_user(self, user_id: str) -> Optional[User]:
        pass
    
    @abstractmethod
    def get_policies_for_resource(self, resource: str) -> List[AccessPolicy]:
        pass

class InMemoryPermissionStore(PermissionStore):
    """In-memory implementation for development/testing"""
    
    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.agents: Dict[str, Agent] = {}
        self.users: Dict[str, User] = {}
        self.policies: List[AccessPolicy] = []
        
        self._initialize_default_roles()
    
    def _initialize_default_roles(self):
        """Create default agent roles"""
        
        # Reader role
        self.add_role(Role(
            name="agent:reader",
            display_name="Reader Agent",
            permissions=[
                Permission(PermissionType.DATA_READ, "*"),
                Permission(PermissionType.TOOL_READ, "*")
            ],
            max_actions_per_minute=50
        ))
        
        # Writer role
        self.add_role(Role(
            name="agent:writer",
            display_name="Writer Agent",
            permissions=[
                Permission(PermissionType.DATA_READ, "*"),
                Permission(PermissionType.DATA_WRITE, "user/*"),
                Permission(PermissionType.TOOL_EXECUTE, "safe/*")
            ],
            parent_roles=["agent:reader"],
            max_actions_per_minute=30
        ))
        
        # Tool executor
        self.add_role(Role(
            name="agent:executor",
            display_name="Tool Executor Agent",
            permissions=[
                Permission(PermissionType.TOOL_EXECUTE, "*"),
                Permission(PermissionType.NETWORK_EXTERNAL, "approved/*")
            ],
            requires_approval=True,
            max_actions_per_minute=20
        ))
        
        # Admin role
        self.add_role(Role(
            name="agent:admin",
            display_name="Admin Agent",
            permissions=[
                Permission(PermissionType.SYSTEM_ADMIN, "*"),
                Permission(PermissionType.DATA_DELETE, "*"),
            ],
            parent_roles=["agent:writer", "agent:executor"],
            requires_approval=True,
            max_actions_per_minute=10
        ))
    
    def add_role(self, role: Role):
        self.roles[role.name] = role
    
    def add_agent(self, agent: Agent):
        self.agents[agent.agent_id] = agent
    
    def add_user(self, user: User):
        self.users[user.user_id] = user
    
    def add_policy(self, policy: AccessPolicy):
        self.policies.append(policy)
        self.policies.sort(key=lambda p: -p.priority)
    
    def get_role(self, role_name: str) -> Optional[Role]:
        return self.roles.get(role_name)
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)
    
    def get_policies_for_resource(self, resource: str) -> List[AccessPolicy]:
        return [p for p in self.policies if p.applies_to(resource)]
    
    def get_all_permissions_for_role(self, role_name: str, 
                                      visited: Set[str] = None) -> List[Permission]:
        """Get all permissions including inherited ones"""
        if visited is None:
            visited = set()
        
        if role_name in visited:
            return []
        visited.add(role_name)
        
        role = self.get_role(role_name)
        if not role:
            return []
        
        permissions = list(role.permissions)
        
        for parent in role.parent_roles:
            permissions.extend(self.get_all_permissions_for_role(parent, visited))
        
        return permissions
```

---

## 3. Authorization Engine

### 3.1 Access Decision

```python
@dataclass
class AccessRequest:
    """Request for access to perform an action"""
    agent_id: str
    permission_type: PermissionType
    resource: str
    
    # Context
    session_id: str = ""
    user_id: str = ""  # Delegating user
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict = field(default_factory=dict)

@dataclass
class AccessDecision:
    """Result of access control check"""
    allowed: bool
    reason: str
    matched_policy: Optional[str] = None
    matched_role: Optional[str] = None
    conditions: Dict = field(default_factory=dict)
    
    # For auditing
    request_id: str = ""
    decision_time_ms: float = 0

class AuthorizationEngine:
    """
    Core authorization engine for agent RBAC.
    Implements policy evaluation and decision logic.
    """
    
    def __init__(self, store: PermissionStore):
        self.store = store
        self.decision_cache: Dict[str, AccessDecision] = {}
        self.rate_limiter = RateLimiter()
    
    def check_access(self, request: AccessRequest) -> AccessDecision:
        """
        Main authorization check.
        
        Returns:
            AccessDecision with allow/deny and reason
        """
        import time
        start = time.time()
        
        # Get agent
        agent = self.store.get_agent(request.agent_id)
        if not agent:
            return AccessDecision(
                allowed=False,
                reason=f"Unknown agent: {request.agent_id}"
            )
        
        # Check delegation validity
        if agent.delegated_from:
            delegation_check = self._check_delegation(agent, request)
            if not delegation_check.allowed:
                return delegation_check
        
        # Rate limiting
        if not self.rate_limiter.allow(request.agent_id, self._get_rate_limit(agent)):
            return AccessDecision(
                allowed=False,
                reason="Rate limit exceeded"
            )
        
        # Check policies first (explicit allow/deny)
        policy_decision = self._check_policies(request)
        if policy_decision:
            policy_decision.decision_time_ms = (time.time() - start) * 1000
            return policy_decision
        
        # Check role-based permissions
        role_decision = self._check_role_permissions(agent, request)
        role_decision.decision_time_ms = (time.time() - start) * 1000
        
        return role_decision
    
    def _check_delegation(self, agent: Agent, request: AccessRequest) -> AccessDecision:
        """Verify delegation is valid"""
        user = self.store.get_user(agent.delegated_from)
        if not user:
            return AccessDecision(
                allowed=False,
                reason=f"Delegating user {agent.delegated_from} not found"
            )
        
        if not user.can_delegate_to_agents:
            return AccessDecision(
                allowed=False,
                reason="User cannot delegate to agents"
            )
        
        if agent.agent_id not in user.delegated_agents:
            return AccessDecision(
                allowed=False,
                reason="Agent not in user's delegation list"
            )
        
        # Check delegation scope
        if agent.delegation_scope:
            scope_match = any(
                fnmatch.fnmatch(request.resource, scope)
                for scope in agent.delegation_scope
            )
            if not scope_match:
                return AccessDecision(
                    allowed=False,
                    reason="Request outside delegation scope"
                )
        
        return AccessDecision(allowed=True, reason="Delegation valid")
    
    def _check_policies(self, request: AccessRequest) -> Optional[AccessDecision]:
        """Check explicit policies"""
        import fnmatch
        
        policies = self.store.get_policies_for_resource(request.resource)
        agent = self.store.get_agent(request.agent_id)
        
        for policy in policies:
            # Check deny first
            for role in agent.roles:
                if role in policy.deny_roles:
                    return AccessDecision(
                        allowed=False,
                        reason=f"Denied by policy {policy.policy_id}",
                        matched_policy=policy.policy_id
                    )
            
            # Check allow
            for role in agent.roles:
                if role in policy.allowed_roles:
                    # Check conditions
                    if self._check_conditions(policy.required_conditions, request):
                        return AccessDecision(
                            allowed=True,
                            reason=f"Allowed by policy {policy.policy_id}",
                            matched_policy=policy.policy_id
                        )
        
        return None  # No matching policy
    
    def _check_role_permissions(self, agent: Agent, 
                                 request: AccessRequest) -> AccessDecision:
        """Check role-based permissions"""
        for role_name in agent.roles:
            permissions = self.store.get_all_permissions_for_role(role_name)
            
            for perm in permissions:
                if perm.type == request.permission_type and perm.matches(request.resource):
                    role = self.store.get_role(role_name)
                    
                    # Check time constraints
                    if role and request.timestamp.hour not in role.allowed_hours:
                        continue
                    
                    # Check if approval required
                    if role and role.requires_approval:
                        return AccessDecision(
                            allowed=True,
                            reason=f"Allowed by role {role_name} (pending approval)",
                            matched_role=role_name,
                            conditions={'requires_approval': True}
                        )
                    
                    return AccessDecision(
                        allowed=True,
                        reason=f"Allowed by role {role_name}",
                        matched_role=role_name
                    )
        
        return AccessDecision(
            allowed=False,
            reason="No matching permission found"
        )
    
    def _check_conditions(self, conditions: Dict, request: AccessRequest) -> bool:
        """Evaluate policy conditions"""
        for key, expected in conditions.items():
            actual = request.context.get(key)
            if actual != expected:
                return False
        return True
    
    def _get_rate_limit(self, agent: Agent) -> int:
        """Get rate limit for agent based on roles"""
        max_rate = 100
        for role_name in agent.roles:
            role = self.store.get_role(role_name)
            if role:
                max_rate = min(max_rate, role.max_actions_per_minute)
        return max_rate

class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self):
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
    
    def allow(self, agent_id: str, limit_per_minute: int) -> bool:
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old requests
        self.requests[agent_id] = [
            t for t in self.requests[agent_id] if t > minute_ago
        ]
        
        if len(self.requests[agent_id]) >= limit_per_minute:
            return False
        
        self.requests[agent_id].append(now)
        return True
```

### 3.2 Permission Enforcement

```python
from functools import wraps
import logging

class PermissionEnforcer:
    """
    Enforces permissions on agent actions.
    Can be used as decorator or context manager.
    """
    
    def __init__(self, auth_engine: AuthorizationEngine):
        self.auth_engine = auth_engine
        self.logger = logging.getLogger(__name__)
    
    def require_permission(self, permission_type: PermissionType, 
                           resource_pattern: str = None):
        """Decorator for requiring permission"""
        def decorator(func):
            @wraps(func)
            def wrapper(agent_id: str, *args, **kwargs):
                # Build resource from pattern or function name
                resource = resource_pattern or f"function:{func.__name__}"
                
                # Create request
                request = AccessRequest(
                    agent_id=agent_id,
                    permission_type=permission_type,
                    resource=resource,
                    context=kwargs.get('context', {})
                )
                
                # Check access
                decision = self.auth_engine.check_access(request)
                
                if not decision.allowed:
                    self.logger.warning(
                        f"Access denied: {agent_id} -> {permission_type.value}:{resource}. "
                        f"Reason: {decision.reason}"
                    )
                    raise PermissionDeniedError(
                        agent_id=agent_id,
                        permission=permission_type.value,
                        resource=resource,
                        reason=decision.reason
                    )
                
                if decision.conditions.get('requires_approval'):
                    approval = kwargs.get('approval_token')
                    if not approval:
                        raise ApprovalRequiredError(
                            agent_id=agent_id,
                            permission=permission_type.value,
                            resource=resource
                        )
                
                self.logger.info(f"Access granted: {agent_id} -> {resource}")
                return func(agent_id, *args, **kwargs)
            
            return wrapper
        return decorator
    
    def check_and_execute(self, agent_id: str, 
                          permission_type: PermissionType,
                          resource: str,
                          action: callable,
                          context: Dict = None) -> Any:
        """Check permission and execute action"""
        request = AccessRequest(
            agent_id=agent_id,
            permission_type=permission_type,
            resource=resource,
            context=context or {}
        )
        
        decision = self.auth_engine.check_access(request)
        
        if not decision.allowed:
            raise PermissionDeniedError(
                agent_id=agent_id,
                permission=permission_type.value,
                resource=resource,
                reason=decision.reason
            )
        
        return action()

class PermissionDeniedError(Exception):
    """Raised when permission is denied"""
    
    def __init__(self, agent_id: str, permission: str, 
                 resource: str, reason: str):
        self.agent_id = agent_id
        self.permission = permission
        self.resource = resource
        self.reason = reason
        super().__init__(
            f"Permission denied: {agent_id} cannot {permission} on {resource}. {reason}"
        )

class ApprovalRequiredError(Exception):
    """Raised when approval is required"""
    
    def __init__(self, agent_id: str, permission: str, resource: str):
        self.agent_id = agent_id
        self.permission = permission
        self.resource = resource
        super().__init__(
            f"Approval required: {agent_id} needs approval for {permission} on {resource}"
        )
```

---

## 4. Dynamic RBAC

### 4.1 Context-Aware Permissions

```python
@dataclass
class ContextCondition:
    """Condition based on runtime context"""
    key: str
    operator: str  # eq, ne, gt, lt, in, contains
    value: Any
    
    def evaluate(self, context: Dict) -> bool:
        actual = context.get(self.key)
        
        if self.operator == "eq":
            return actual == self.value
        elif self.operator == "ne":
            return actual != self.value
        elif self.operator == "gt":
            return actual > self.value if actual else False
        elif self.operator == "lt":
            return actual < self.value if actual else False
        elif self.operator == "in":
            return actual in self.value if self.value else False
        elif self.operator == "contains":
            return self.value in actual if actual else False
        
        return False

class DynamicRole:
    """
    Role that adapts based on context.
    Permissions can be added/removed based on conditions.
    """
    
    def __init__(self, base_role: Role):
        self.base_role = base_role
        self.conditional_permissions: List[Tuple[ContextCondition, Permission]] = []
        self.conditional_restrictions: List[Tuple[ContextCondition, Permission]] = []
    
    def add_conditional_permission(self, condition: ContextCondition, 
                                   permission: Permission):
        """Add permission that's active only when condition is met"""
        self.conditional_permissions.append((condition, permission))
    
    def add_conditional_restriction(self, condition: ContextCondition,
                                    permission: Permission):
        """Remove permission when condition is met"""
        self.conditional_restrictions.append((condition, permission))
    
    def get_active_permissions(self, context: Dict) -> List[Permission]:
        """Get permissions active in current context"""
        active = list(self.base_role.permissions)
        
        # Add conditional permissions
        for condition, perm in self.conditional_permissions:
            if condition.evaluate(context):
                active.append(perm)
        
        # Remove restricted permissions
        for condition, perm in self.conditional_restrictions:
            if condition.evaluate(context):
                active = [p for p in active if p.to_string() != perm.to_string()]
        
        return active

class TrustBasedPermissionModifier:
    """
    Modifies permissions based on agent trust level.
    Higher trust = more permissions.
    """
    
    def __init__(self):
        self.trust_thresholds = {
            0.9: ["agent:admin"],
            0.7: ["agent:executor"],
            0.5: ["agent:writer"],
            0.3: ["agent:reader"],
            0.0: []
        }
    
    def get_allowed_roles(self, trust_level: float) -> List[str]:
        """Get roles allowed at given trust level"""
        allowed = []
        for threshold, roles in sorted(self.trust_thresholds.items()):
            if trust_level >= threshold:
                allowed.extend(roles)
        return allowed
    
    def filter_agent_roles(self, agent: Agent) -> List[str]:
        """Filter agent roles based on current trust"""
        allowed = self.get_allowed_roles(agent.trust_level)
        return [r for r in agent.roles if r in allowed]
```

### 4.2 Temporal Permissions

```python
from datetime import datetime, timedelta

@dataclass
class TemporalGrant:
    """
    Time-limited permission grant.
    """
    grant_id: str
    agent_id: str
    role: str
    
    # Time bounds
    valid_from: datetime
    valid_until: datetime
    
    # Usage limits
    max_uses: Optional[int] = None
    current_uses: int = 0
    
    # Metadata
    granted_by: str = ""
    reason: str = ""
    
    def is_valid(self) -> bool:
        now = datetime.utcnow()
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True
    
    def use(self):
        self.current_uses += 1

class TemporalPermissionManager:
    """Manages time-limited permissions"""
    
    def __init__(self, store: PermissionStore):
        self.store = store
        self.grants: Dict[str, TemporalGrant] = {}
    
    def grant_temporary_role(self, agent_id: str, role: str,
                             duration_minutes: int,
                             granted_by: str,
                             max_uses: int = None) -> TemporalGrant:
        """Grant temporary role to agent"""
        grant = TemporalGrant(
            grant_id=f"grant_{agent_id}_{datetime.utcnow().timestamp()}",
            agent_id=agent_id,
            role=role,
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(minutes=duration_minutes),
            max_uses=max_uses,
            granted_by=granted_by
        )
        
        self.grants[grant.grant_id] = grant
        return grant
    
    def get_active_grants(self, agent_id: str) -> List[TemporalGrant]:
        """Get all active grants for agent"""
        return [
            g for g in self.grants.values()
            if g.agent_id == agent_id and g.is_valid()
        ]
    
    def get_effective_roles(self, agent: Agent) -> List[str]:
        """Get all roles including temporary grants"""
        roles = list(agent.roles)
        
        for grant in self.get_active_grants(agent.agent_id):
            if grant.role not in roles:
                roles.append(grant.role)
        
        return roles
    
    def cleanup_expired(self):
        """Remove expired grants"""
        self.grants = {
            gid: g for gid, g in self.grants.items()
            if g.is_valid()
        }
```

---

## 5. Audit и Compliance

### 5.1 Audit Logger

```python
@dataclass
class AuditEntry:
    """Audit log entry"""
    entry_id: str
    timestamp: datetime
    agent_id: str
    user_id: str
    
    # Action details
    action_type: str  # access_check, permission_grant, role_change
    permission: str
    resource: str
    
    # Decision
    decision: str  # allowed, denied, pending_approval
    reason: str
    
    # Context
    context: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'entry_id': self.entry_id,
            'timestamp': self.timestamp.isoformat(),
            'agent_id': self.agent_id,
            'user_id': self.user_id,
            'action_type': self.action_type,
            'permission': self.permission,
            'resource': self.resource,
            'decision': self.decision,
            'reason': self.reason,
            'context': self.context
        }

class RBACAuditLogger:
    """Audit logger for RBAC decisions"""
    
    def __init__(self):
        self.entries: List[AuditEntry] = []
        self.max_entries = 100000
    
    def log_access_decision(self, request: AccessRequest, 
                            decision: AccessDecision):
        """Log access control decision"""
        entry = AuditEntry(
            entry_id=f"audit_{datetime.utcnow().timestamp()}",
            timestamp=datetime.utcnow(),
            agent_id=request.agent_id,
            user_id=request.user_id,
            action_type="access_check",
            permission=request.permission_type.value,
            resource=request.resource,
            decision="allowed" if decision.allowed else "denied",
            reason=decision.reason,
            context={
                'session_id': request.session_id,
                'matched_policy': decision.matched_policy,
                'matched_role': decision.matched_role
            }
        )
        
        self._add_entry(entry)
    
    def log_role_change(self, agent_id: str, old_roles: List[str],
                        new_roles: List[str], changed_by: str):
        """Log role assignment change"""
        entry = AuditEntry(
            entry_id=f"audit_{datetime.utcnow().timestamp()}",
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            user_id=changed_by,
            action_type="role_change",
            permission="system:role_assign",
            resource=f"agent:{agent_id}",
            decision="completed",
            reason=f"Roles changed from {old_roles} to {new_roles}",
            context={
                'old_roles': old_roles,
                'new_roles': new_roles
            }
        )
        
        self._add_entry(entry)
    
    def _add_entry(self, entry: AuditEntry):
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
    
    def query(self, agent_id: str = None, 
              start_time: datetime = None,
              end_time: datetime = None,
              decision: str = None) -> List[AuditEntry]:
        """Query audit log"""
        results = self.entries
        
        if agent_id:
            results = [e for e in results if e.agent_id == agent_id]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]
        if decision:
            results = [e for e in results if e.decision == decision]
        
        return results
    
    def get_denial_summary(self, hours: int = 24) -> Dict:
        """Get summary of access denials"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        denials = [e for e in self.entries 
                   if e.decision == "denied" and e.timestamp >= cutoff]
        
        by_agent = defaultdict(int)
        by_resource = defaultdict(int)
        by_reason = defaultdict(int)
        
        for d in denials:
            by_agent[d.agent_id] += 1
            by_resource[d.resource] += 1
            by_reason[d.reason] += 1
        
        return {
            'total_denials': len(denials),
            'by_agent': dict(by_agent),
            'by_resource': dict(by_resource),
            'by_reason': dict(by_reason)
        }
```

---

## 6. SENTINEL Integration

```python
from dataclasses import dataclass

@dataclass
class RBACConfig:
    """RBAC configuration"""
    enable_audit: bool = True
    enable_rate_limiting: bool = True
    enable_temporal_grants: bool = True
    default_trust_level: float = 0.5
    max_rate_per_minute: int = 100

class SENTINELRBACEngine:
    """RBAC engine for SENTINEL framework"""
    
    def __init__(self, config: RBACConfig):
        self.config = config
        
        # Core components
        self.store = InMemoryPermissionStore()
        self.auth_engine = AuthorizationEngine(self.store)
        self.enforcer = PermissionEnforcer(self.auth_engine)
        
        # Optional components
        if config.enable_temporal_grants:
            self.temporal_manager = TemporalPermissionManager(self.store)
        
        if config.enable_audit:
            self.audit_logger = RBACAuditLogger()
        
        self.trust_modifier = TrustBasedPermissionModifier()
    
    def register_agent(self, agent_id: str, agent_type: str,
                       roles: List[str], delegated_from: str = None) -> Agent:
        """Register new agent"""
        agent = Agent(
            agent_id=agent_id,
            display_name=agent_id,
            agent_type=agent_type,
            roles=roles,
            delegated_from=delegated_from,
            trust_level=self.config.default_trust_level
        )
        
        self.store.add_agent(agent)
        return agent
    
    def check_permission(self, agent_id: str, 
                         permission: PermissionType,
                         resource: str,
                         context: Dict = None) -> AccessDecision:
        """Check if agent has permission"""
        request = AccessRequest(
            agent_id=agent_id,
            permission_type=permission,
            resource=resource,
            context=context or {}
        )
        
        decision = self.auth_engine.check_access(request)
        
        if self.config.enable_audit:
            self.audit_logger.log_access_decision(request, decision)
        
        return decision
    
    def grant_temporary_access(self, agent_id: str, role: str,
                               duration_minutes: int,
                               granted_by: str) -> str:
        """Grant temporary role to agent"""
        if not self.config.enable_temporal_grants:
            raise ValueError("Temporal grants disabled")
        
        grant = self.temporal_manager.grant_temporary_role(
            agent_id=agent_id,
            role=role,
            duration_minutes=duration_minutes,
            granted_by=granted_by
        )
        
        return grant.grant_id
    
    def update_agent_trust(self, agent_id: str, trust_delta: float):
        """Update agent trust level"""
        agent = self.store.get_agent(agent_id)
        if agent:
            agent.trust_level = max(0, min(1, agent.trust_level + trust_delta))
    
    def get_audit_summary(self, hours: int = 24) -> Dict:
        """Get audit summary"""
        if not self.config.enable_audit:
            return {}
        return self.audit_logger.get_denial_summary(hours)
```

---

## 7. Резюме

| Компонент | Описание |
|-----------|----------|
| **Permission** | Тип доступа + resource pattern |
| **Role** | Группа permissions с constraints |
| **Agent** | AI-сущность с roles и delegation |
| **Policy** | Explicit allow/deny правила |
| **AuthEngine** | Вычисление access decisions |
| **Enforcer** | Применение decisions к actions |
| **Audit** | Логирование всех решений |

---

## Следующий урок

→ [Track 05: Defense Strategies](../../05-defense-strategies/README.md)

---

*AI Security Academy | Track 04: Agentic Security | Module 04.3: Trust & Authorization*
