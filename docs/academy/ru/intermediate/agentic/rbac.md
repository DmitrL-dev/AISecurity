# RBAC для AI агентов

> **Уровень:** Advanced  
> **Время:** 55 минут  
> **Трек:** 04 — Agentic Security  
> **Модуль:** 04.3 — Trust & Authorization  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять Role-Based Access Control для AI агентов
- [ ] Реализовать RBAC систему с policies
- [ ] Построить enforcement permissions для agent actions
- [ ] Интегрировать RBAC в SENTINEL framework

---

## 1. Обзор RBAC для агентов

### 1.1 Зачем RBAC для агентов?

AI агенты выполняют действия от имени пользователей. RBAC контролирует какие действия доступны агентам.

```
┌────────────────────────────────────────────────────────────────────┐
│              RBAC FOR AI AGENTS                                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Традиционный (Human) RBAC:                                        │
│  User → Role → Permission → Resource                               │
│                                                                    │
│  Agent RBAC (Extended):                                            │
│  User → Agent → Role → Permission → Resource                       │
│       ↓                    ↓                                       │
│    Delegation          Constraints                                 │
│                                                                    │
│  Дополнительные измерения:                                         │
│  ├── Agent Identity: Какой агент запрашивает?                     │
│  ├── Delegation Chain: От какого user действует?                  │
│  ├── Context: В каком контексте (session, task)?                  │
│  ├── Time: Временные ограничения                                  │
│  └── Risk Level: Динамическая оценка риска                        │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Ключевые концепции

```
RBAC иерархия для агентов:
├── Users
│   └── Человеческие пользователи, service accounts
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

## 2. Имплементация RBAC Model

### 2.1 Core Entities

```rust
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use sha2::{Sha256, Digest};

#[derive(Clone, PartialEq, Eq, Hash)]
enum PermissionType {
    ToolExecute,
    ToolRead,
    DataRead,
    DataWrite,
    DataDelete,
    NetworkExternal,
    SystemAdmin,
}

impl PermissionType {
    fn value(&self) -> &str {
        match self {
            Self::ToolExecute => "tool:execute",
            Self::ToolRead => "tool:read",
            Self::DataRead => "data:read",
            Self::DataWrite => "data:write",
            Self::DataDelete => "data:delete",
            Self::NetworkExternal => "network:external",
            Self::SystemAdmin => "system:admin",
        }
    }
}

/// Единичная permission grant.
/// Может включать resource pattern и constraints.
struct Permission {
    perm_type: PermissionType,
    resource_pattern: String, // Glob pattern
    constraints: HashMap<String, String>,
}

impl Permission {
    fn new(perm_type: PermissionType, resource_pattern: &str) -> Self {
        Self {
            perm_type,
            resource_pattern: resource_pattern.to_string(),
            constraints: HashMap::new(),
        }
    }

    /// Проверить применяется ли permission к resource
    fn matches(&self, resource: &str) -> bool {
        glob_match(&self.resource_pattern, resource)
    }

    fn to_string(&self) -> String {
        format!("{}:{}", self.perm_type.value(), self.resource_pattern)
    }
}

/// Role группирует связанные permissions.
/// Поддерживает иерархию через parent roles.
struct Role {
    name: String,
    display_name: String,
    permissions: Vec<Permission>,
    parent_roles: Vec<String>,
    description: String,
    // Constraints
    max_actions_per_minute: i32,
    allowed_hours: Vec<u32>,
    requires_approval: bool,
}

impl Role {
    /// Проверить выдаёт ли role permission для resource
    fn has_permission(&self, perm_type: &PermissionType, resource: &str) -> bool {
        for perm in &self.permissions {
            if perm.perm_type == *perm_type && perm.matches(resource) {
                return true;
            }
        }
        false
    }
}

/// AI Agent сущность с identity и assigned roles.
struct Agent {
    agent_id: String,
    display_name: String,
    agent_type: String, // llm, tool, composite
    roles: Vec<String>,
    // Delegation
    delegated_from: Option<String>, // User ID
    delegation_scope: Vec<String>,
    // Trust
    trust_level: f64, // 0-1
    last_activity: DateTime<Utc>,
    // Metadata
    created_at: DateTime<Utc>,
    metadata: HashMap<String, String>,
}

impl Agent {
    fn identity_hash(&self) -> String {
        let data = format!("{}:{}:{:?}", self.agent_id, self.agent_type, self.delegated_from);
        let mut hasher = Sha256::new();
        hasher.update(data.as_bytes());
        let result = hasher.finalize();
        format!("{:x}", result)[..16].to_string()
    }
}

/// Human user сущность.
struct User {
    user_id: String,
    username: String,
    roles: Vec<String>,
    // Agent delegation limits
    can_delegate_to_agents: bool,
    max_delegated_agents: usize,
    delegated_agents: Vec<String>,
}

/// Access policy для конкретных resource patterns.
struct AccessPolicy {
    policy_id: String,
    resource_pattern: String,
    allowed_roles: Vec<String>,
    required_conditions: HashMap<String, String>,
    deny_roles: Vec<String>,
    priority: i32,
}

impl AccessPolicy {
    fn applies_to(&self, resource: &str) -> bool {
        glob_match(&self.resource_pattern, resource)
    }
}
```

### 2.2 Permission Store

```rust
use std::collections::{HashMap, HashSet};

/// Абстрактный permission store interface
trait PermissionStore {
    fn get_role(&self, role_name: &str) -> Option<&Role>;
    fn get_agent(&self, agent_id: &str) -> Option<&Agent>;
    fn get_user(&self, user_id: &str) -> Option<&User>;
    fn get_policies_for_resource(&self, resource: &str) -> Vec<&AccessPolicy>;
}

/// In-memory implementation для development/testing
struct InMemoryPermissionStore {
    roles: HashMap<String, Role>,
    agents: HashMap<String, Agent>,
    users: HashMap<String, User>,
    policies: Vec<AccessPolicy>,
}

impl InMemoryPermissionStore {
    fn new() -> Self {
        let mut store = Self {
            roles: HashMap::new(),
            agents: HashMap::new(),
            users: HashMap::new(),
            policies: Vec::new(),
        };
        store.initialize_default_roles();
        store
    }

    /// Создать default agent roles
    fn initialize_default_roles(&mut self) {
        // Reader role
        self.add_role(Role {
            name: "agent:reader".into(),
            display_name: "Reader Agent".into(),
            permissions: vec![
                Permission::new(PermissionType::DataRead, "*"),
                Permission::new(PermissionType::ToolRead, "*"),
            ],
            parent_roles: vec![],
            description: String::new(),
            max_actions_per_minute: 50,
            allowed_hours: (0..24).collect(),
            requires_approval: false,
        });

        // Writer role
        self.add_role(Role {
            name: "agent:writer".into(),
            display_name: "Writer Agent".into(),
            permissions: vec![
                Permission::new(PermissionType::DataRead, "*"),
                Permission::new(PermissionType::DataWrite, "user/*"),
                Permission::new(PermissionType::ToolExecute, "safe/*"),
            ],
            parent_roles: vec!["agent:reader".into()],
            description: String::new(),
            max_actions_per_minute: 30,
            allowed_hours: (0..24).collect(),
            requires_approval: false,
        });

        // Tool executor
        self.add_role(Role {
            name: "agent:executor".into(),
            display_name: "Tool Executor Agent".into(),
            permissions: vec![
                Permission::new(PermissionType::ToolExecute, "*"),
                Permission::new(PermissionType::NetworkExternal, "approved/*"),
            ],
            parent_roles: vec![],
            description: String::new(),
            max_actions_per_minute: 20,
            allowed_hours: (0..24).collect(),
            requires_approval: true,
        });

        // Admin role
        self.add_role(Role {
            name: "agent:admin".into(),
            display_name: "Admin Agent".into(),
            permissions: vec![
                Permission::new(PermissionType::SystemAdmin, "*"),
                Permission::new(PermissionType::DataDelete, "*"),
            ],
            parent_roles: vec!["agent:writer".into(), "agent:executor".into()],
            description: String::new(),
            max_actions_per_minute: 10,
            allowed_hours: (0..24).collect(),
            requires_approval: true,
        });
    }

    fn add_role(&mut self, role: Role) {
        self.roles.insert(role.name.clone(), role);
    }

    fn add_agent(&mut self, agent: Agent) {
        self.agents.insert(agent.agent_id.clone(), agent);
    }

    fn add_user(&mut self, user: User) {
        self.users.insert(user.user_id.clone(), user);
    }

    fn add_policy(&mut self, policy: AccessPolicy) {
        self.policies.push(policy);
        self.policies.sort_by(|a, b| b.priority.cmp(&a.priority));
    }

    /// Получить все permissions включая inherited
    fn get_all_permissions_for_role(&self, role_name: &str, visited: &mut HashSet<String>) -> Vec<&Permission> {
        if visited.contains(role_name) {
            return vec![];
        }
        visited.insert(role_name.to_string());

        let role = match self.roles.get(role_name) {
            Some(r) => r,
            None => return vec![],
        };

        let mut permissions: Vec<&Permission> = role.permissions.iter().collect();

        for parent in &role.parent_roles {
            permissions.extend(self.get_all_permissions_for_role(parent, visited));
        }

        permissions
    }
}

impl PermissionStore for InMemoryPermissionStore {
    fn get_role(&self, role_name: &str) -> Option<&Role> {
        self.roles.get(role_name)
    }

    fn get_agent(&self, agent_id: &str) -> Option<&Agent> {
        self.agents.get(agent_id)
    }

    fn get_user(&self, user_id: &str) -> Option<&User> {
        self.users.get(user_id)
    }

    fn get_policies_for_resource(&self, resource: &str) -> Vec<&AccessPolicy> {
        self.policies.iter().filter(|p| p.applies_to(resource)).collect()
    }
}
```

---

## 3. Authorization Engine

### 3.1 Access Decision

```rust
use std::collections::HashMap;
use chrono::{DateTime, Utc, Duration};

/// Запрос на доступ для выполнения действия
struct AccessRequest {
    agent_id: String,
    permission_type: PermissionType,
    resource: String,
    // Context
    session_id: String,
    user_id: String, // Delegating user
    timestamp: DateTime<Utc>,
    context: HashMap<String, String>,
}

/// Результат проверки access control
struct AccessDecision {
    allowed: bool,
    reason: String,
    matched_policy: Option<String>,
    matched_role: Option<String>,
    conditions: HashMap<String, bool>,
    // Для auditing
    request_id: String,
    decision_time_ms: f64,
}

/// Простой rate limiter
struct RateLimiter {
    requests: HashMap<String, Vec<DateTime<Utc>>>,
}

impl RateLimiter {
    fn new() -> Self {
        Self { requests: HashMap::new() }
    }

    fn allow(&mut self, agent_id: &str, limit_per_minute: i32) -> bool {
        let now = Utc::now();
        let minute_ago = now - Duration::minutes(1);

        // Очистить старые requests
        let entries = self.requests.entry(agent_id.to_string()).or_insert_with(Vec::new);
        entries.retain(|t| *t > minute_ago);

        if entries.len() as i32 >= limit_per_minute {
            return false;
        }

        entries.push(now);
        true
    }
}

/// Core authorization engine для agent RBAC.
/// Реализует policy evaluation и decision logic.
struct AuthorizationEngine {
    store: InMemoryPermissionStore,
    decision_cache: HashMap<String, AccessDecision>,
    rate_limiter: RateLimiter,
}

impl AuthorizationEngine {
    fn new(store: InMemoryPermissionStore) -> Self {
        Self {
            store,
            decision_cache: HashMap::new(),
            rate_limiter: RateLimiter::new(),
        }
    }

    /// Главная authorization проверка.
    fn check_access(&mut self, request: &AccessRequest) -> AccessDecision {
        let start = std::time::Instant::now();

        // Получить agent
        let agent = match self.store.get_agent(&request.agent_id) {
            Some(a) => a,
            None => return AccessDecision {
                allowed: false,
                reason: format!("Unknown agent: {}", request.agent_id),
                matched_policy: None, matched_role: None,
                conditions: HashMap::new(), request_id: String::new(),
                decision_time_ms: 0.0,
            },
        };

        // Проверить валидность delegation
        if let Some(ref delegated_from) = agent.delegated_from {
            let delegation_check = self.check_delegation(agent, request);
            if !delegation_check.allowed {
                return delegation_check;
            }
        }

        // Rate limiting
        let rate_limit = self.get_rate_limit(agent);
        if !self.rate_limiter.allow(&request.agent_id, rate_limit) {
            return AccessDecision {
                allowed: false,
                reason: "Rate limit exceeded".into(),
                matched_policy: None, matched_role: None,
                conditions: HashMap::new(), request_id: String::new(),
                decision_time_ms: start.elapsed().as_secs_f64() * 1000.0,
            };
        }

        // Проверить policies сначала (explicit allow/deny)
        if let Some(mut policy_decision) = self.check_policies(request, agent) {
            policy_decision.decision_time_ms = start.elapsed().as_secs_f64() * 1000.0;
            return policy_decision;
        }

        // Проверить role-based permissions
        let mut role_decision = self.check_role_permissions(agent, request);
        role_decision.decision_time_ms = start.elapsed().as_secs_f64() * 1000.0;
        role_decision
    }

    /// Проверить валидность delegation
    fn check_delegation(&self, agent: &Agent, request: &AccessRequest) -> AccessDecision {
        let delegated_from = agent.delegated_from.as_ref().unwrap();
        let user = match self.store.get_user(delegated_from) {
            Some(u) => u,
            None => return AccessDecision {
                allowed: false,
                reason: format!("Delegating user {} not found", delegated_from),
                matched_policy: None, matched_role: None,
                conditions: HashMap::new(), request_id: String::new(),
                decision_time_ms: 0.0,
            },
        };

        if !user.can_delegate_to_agents {
            return AccessDecision {
                allowed: false, reason: "User cannot delegate to agents".into(),
                matched_policy: None, matched_role: None,
                conditions: HashMap::new(), request_id: String::new(),
                decision_time_ms: 0.0,
            };
        }

        if !user.delegated_agents.contains(&agent.agent_id) {
            return AccessDecision {
                allowed: false, reason: "Agent not in user's delegation list".into(),
                matched_policy: None, matched_role: None,
                conditions: HashMap::new(), request_id: String::new(),
                decision_time_ms: 0.0,
            };
        }

        // Проверить delegation scope
        if !agent.delegation_scope.is_empty() {
            let scope_match = agent.delegation_scope.iter()
                .any(|scope| glob_match(scope, &request.resource));
            if !scope_match {
                return AccessDecision {
                    allowed: false, reason: "Request outside delegation scope".into(),
                    matched_policy: None, matched_role: None,
                    conditions: HashMap::new(), request_id: String::new(),
                    decision_time_ms: 0.0,
                };
            }
        }

        AccessDecision {
            allowed: true, reason: "Delegation valid".into(),
            matched_policy: None, matched_role: None,
            conditions: HashMap::new(), request_id: String::new(),
            decision_time_ms: 0.0,
        }
    }

    /// Проверить explicit policies
    fn check_policies(&self, request: &AccessRequest, agent: &Agent) -> Option<AccessDecision> {
        let policies = self.store.get_policies_for_resource(&request.resource);

        for policy in &policies {
            // Проверить deny сначала
            for role in &agent.roles {
                if policy.deny_roles.contains(role) {
                    return Some(AccessDecision {
                        allowed: false,
                        reason: format!("Denied by policy {}", policy.policy_id),
                        matched_policy: Some(policy.policy_id.clone()),
                        matched_role: None, conditions: HashMap::new(),
                        request_id: String::new(), decision_time_ms: 0.0,
                    });
                }
            }

            // Проверить allow
            for role in &agent.roles {
                if policy.allowed_roles.contains(role) {
                    // Проверить conditions
                    if self.check_conditions(&policy.required_conditions, request) {
                        return Some(AccessDecision {
                            allowed: true,
                            reason: format!("Allowed by policy {}", policy.policy_id),
                            matched_policy: Some(policy.policy_id.clone()),
                            matched_role: None, conditions: HashMap::new(),
                            request_id: String::new(), decision_time_ms: 0.0,
                        });
                    }
                }
            }
        }

        None // Нет matching policy
    }

    /// Проверить role-based permissions
    fn check_role_permissions(&self, agent: &Agent, request: &AccessRequest) -> AccessDecision {
        for role_name in &agent.roles {
            let mut visited = std::collections::HashSet::new();
            let permissions = self.store.get_all_permissions_for_role(role_name, &mut visited);

            for perm in &permissions {
                if perm.perm_type == request.permission_type && perm.matches(&request.resource) {
                    let role = self.store.get_role(role_name);

                    // Проверить time constraints
                    if let Some(r) = role {
                        if !r.allowed_hours.contains(&(request.timestamp.hour() as u32)) {
                            continue;
                        }

                        // Проверить нужен ли approval
                        if r.requires_approval {
                            let mut conditions = HashMap::new();
                            conditions.insert("requires_approval".into(), true);
                            return AccessDecision {
                                allowed: true,
                                reason: format!("Allowed by role {} (pending approval)", role_name),
                                matched_policy: None,
                                matched_role: Some(role_name.clone()),
                                conditions, request_id: String::new(),
                                decision_time_ms: 0.0,
                            };
                        }
                    }

                    return AccessDecision {
                        allowed: true,
                        reason: format!("Allowed by role {}", role_name),
                        matched_policy: None,
                        matched_role: Some(role_name.clone()),
                        conditions: HashMap::new(), request_id: String::new(),
                        decision_time_ms: 0.0,
                    };
                }
            }
        }

        AccessDecision {
            allowed: false, reason: "No matching permission found".into(),
            matched_policy: None, matched_role: None,
            conditions: HashMap::new(), request_id: String::new(),
            decision_time_ms: 0.0,
        }
    }

    /// Evaluate policy conditions
    fn check_conditions(&self, conditions: &HashMap<String, String>, request: &AccessRequest) -> bool {
        for (key, expected) in conditions {
            let actual = request.context.get(key);
            if actual.map(|v| v.as_str()) != Some(expected.as_str()) {
                return false;
            }
        }
        true
    }

    /// Получить rate limit для agent на основе roles
    fn get_rate_limit(&self, agent: &Agent) -> i32 {
        let mut max_rate = 100;
        for role_name in &agent.roles {
            if let Some(role) = self.store.get_role(role_name) {
                max_rate = max_rate.min(role.max_actions_per_minute);
            }
        }
        max_rate
    }
}
```

### 3.2 Permission Enforcement

```rust
use std::collections::HashMap;
use std::fmt;

/// Raised когда permission denied
struct PermissionDeniedError {
    agent_id: String,
    permission: String,
    resource: String,
    reason: String,
}

impl fmt::Display for PermissionDeniedError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Permission denied: {} cannot {} on {}. {}",
            self.agent_id, self.permission, self.resource, self.reason)
    }
}

/// Raised когда требуется approval
struct ApprovalRequiredError {
    agent_id: String,
    permission: String,
    resource: String,
}

impl fmt::Display for ApprovalRequiredError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Approval required: {} needs approval for {} on {}",
            self.agent_id, self.permission, self.resource)
    }
}

/// Enforces permissions на agent actions.
/// Может использоваться как middleware или guard.
struct PermissionEnforcer {
    auth_engine: AuthorizationEngine,
}

impl PermissionEnforcer {
    fn new(auth_engine: AuthorizationEngine) -> Self {
        Self { auth_engine }
    }

    /// Проверить permission и выполнить action
    fn check_and_execute<F, R>(
        &mut self,
        agent_id: &str,
        permission_type: PermissionType,
        resource: &str,
        action: F,
        context: Option<HashMap<String, String>>,
    ) -> Result<R, String>
    where
        F: FnOnce() -> R,
    {
        let request = AccessRequest {
            agent_id: agent_id.to_string(),
            permission_type,
            resource: resource.to_string(),
            session_id: String::new(),
            user_id: String::new(),
            timestamp: Utc::now(),
            context: context.unwrap_or_default(),
        };

        let decision = self.auth_engine.check_access(&request);

        if !decision.allowed {
            log::warn!(
                "Access denied: {} -> {}:{}. Reason: {}",
                agent_id, permission_type.value(), resource, decision.reason
            );
            return Err(format!(
                "Permission denied: {} cannot {} on {}. {}",
                agent_id, permission_type.value(), resource, decision.reason
            ));
        }

        if decision.conditions.get("requires_approval").copied().unwrap_or(false) {
            return Err(format!(
                "Approval required: {} needs approval for {} on {}",
                agent_id, permission_type.value(), resource
            ));
        }

        log::info!("Access granted: {} -> {}", agent_id, resource);
        Ok(action())
    }
}
```

---

## 4. Dynamic RBAC

### 4.1 Context-Aware Permissions

```rust
use std::collections::HashMap;

/// Condition на основе runtime context
struct ContextCondition {
    key: String,
    operator: String, // eq, ne, gt, lt, in, contains
    value: serde_json::Value,
}

impl ContextCondition {
    fn evaluate(&self, context: &HashMap<String, serde_json::Value>) -> bool {
        let actual = match context.get(&self.key) {
            Some(v) => v,
            None => return false,
        };

        match self.operator.as_str() {
            "eq" => actual == &self.value,
            "ne" => actual != &self.value,
            "gt" => {
                actual.as_f64().unwrap_or(0.0) > self.value.as_f64().unwrap_or(0.0)
            }
            "lt" => {
                actual.as_f64().unwrap_or(0.0) < self.value.as_f64().unwrap_or(0.0)
            }
            "in" => {
                if let Some(arr) = self.value.as_array() {
                    arr.contains(actual)
                } else {
                    false
                }
            }
            "contains" => {
                if let (Some(a), Some(v)) = (actual.as_str(), self.value.as_str()) {
                    a.contains(v)
                } else {
                    false
                }
            }
            _ => false,
        }
    }
}

/// Role которая адаптируется на основе context.
/// Permissions могут быть добавлены/удалены на основе conditions.
struct DynamicRole {
    base_role: Role,
    conditional_permissions: Vec<(ContextCondition, Permission)>,
    conditional_restrictions: Vec<(ContextCondition, Permission)>,
}

impl DynamicRole {
    fn new(base_role: Role) -> Self {
        Self {
            base_role,
            conditional_permissions: Vec::new(),
            conditional_restrictions: Vec::new(),
        }
    }

    /// Добавить permission активную только когда condition met
    fn add_conditional_permission(&mut self, condition: ContextCondition, permission: Permission) {
        self.conditional_permissions.push((condition, permission));
    }

    /// Убрать permission когда condition met
    fn add_conditional_restriction(&mut self, condition: ContextCondition, permission: Permission) {
        self.conditional_restrictions.push((condition, permission));
    }

    /// Получить permissions активные в текущем context
    fn get_active_permissions(&self, context: &HashMap<String, serde_json::Value>) -> Vec<&Permission> {
        let mut active: Vec<&Permission> = self.base_role.permissions.iter().collect();

        // Добавить conditional permissions
        for (condition, perm) in &self.conditional_permissions {
            if condition.evaluate(context) {
                active.push(perm);
            }
        }

        // Убрать restricted permissions
        for (condition, perm) in &self.conditional_restrictions {
            if condition.evaluate(context) {
                let perm_str = perm.to_string();
                active.retain(|p| p.to_string() != perm_str);
            }
        }

        active
    }
}

/// Модифицирует permissions на основе agent trust level.
/// Выше trust = больше permissions.
struct TrustBasedPermissionModifier {
    trust_thresholds: Vec<(f64, Vec<String>)>,
}

impl TrustBasedPermissionModifier {
    fn new() -> Self {
        Self {
            trust_thresholds: vec![
                (0.9, vec!["agent:admin".into()]),
                (0.7, vec!["agent:executor".into()]),
                (0.5, vec!["agent:writer".into()]),
                (0.3, vec!["agent:reader".into()]),
                (0.0, vec![]),
            ],
        }
    }

    /// Получить roles разрешённые при данном trust level
    fn get_allowed_roles(&self, trust_level: f64) -> Vec<String> {
        let mut allowed = Vec::new();
        let mut sorted = self.trust_thresholds.clone();
        sorted.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
        for (threshold, roles) in &sorted {
            if trust_level >= *threshold {
                allowed.extend(roles.clone());
            }
        }
        allowed
    }

    /// Фильтровать agent roles на основе текущего trust
    fn filter_agent_roles(&self, agent: &Agent) -> Vec<String> {
        let allowed = self.get_allowed_roles(agent.trust_level);
        agent.roles.iter()
            .filter(|r| allowed.contains(r))
            .cloned()
            .collect()
    }
}
```

### 4.2 Temporal Permissions

```rust
use chrono::{DateTime, Utc, Duration};
use std::collections::HashMap;

/// Time-limited permission grant.
struct TemporalGrant {
    grant_id: String,
    agent_id: String,
    role: String,
    // Time bounds
    valid_from: DateTime<Utc>,
    valid_until: DateTime<Utc>,
    // Usage limits
    max_uses: Option<usize>,
    current_uses: usize,
    // Metadata
    granted_by: String,
    reason: String,
}

impl TemporalGrant {
    fn is_valid(&self) -> bool {
        let now = Utc::now();
        if now < self.valid_from || now > self.valid_until {
            return false;
        }
        if let Some(max) = self.max_uses {
            if self.current_uses >= max {
                return false;
            }
        }
        true
    }

    fn use_grant(&mut self) {
        self.current_uses += 1;
    }
}

/// Управляет time-limited permissions
struct TemporalPermissionManager {
    grants: HashMap<String, TemporalGrant>,
}

impl TemporalPermissionManager {
    fn new() -> Self {
        Self { grants: HashMap::new() }
    }

    /// Выдать temporary role агенту
    fn grant_temporary_role(
        &mut self,
        agent_id: &str,
        role: &str,
        duration_minutes: i64,
        granted_by: &str,
        max_uses: Option<usize>,
    ) -> &TemporalGrant {
        let now = Utc::now();
        let grant_id = format!("grant_{}_{}", agent_id, now.timestamp());
        let grant = TemporalGrant {
            grant_id: grant_id.clone(),
            agent_id: agent_id.to_string(),
            role: role.to_string(),
            valid_from: now,
            valid_until: now + Duration::minutes(duration_minutes),
            max_uses,
            current_uses: 0,
            granted_by: granted_by.to_string(),
            reason: String::new(),
        };

        self.grants.insert(grant_id.clone(), grant);
        self.grants.get(&grant_id).unwrap()
    }

    /// Получить все активные grants для agent
    fn get_active_grants(&self, agent_id: &str) -> Vec<&TemporalGrant> {
        self.grants.values()
            .filter(|g| g.agent_id == agent_id && g.is_valid())
            .collect()
    }

    /// Получить все roles включая temporary grants
    fn get_effective_roles(&self, agent: &Agent) -> Vec<String> {
        let mut roles = agent.roles.clone();

        for grant in self.get_active_grants(&agent.agent_id) {
            if !roles.contains(&grant.role) {
                roles.push(grant.role.clone());
            }
        }

        roles
    }

    /// Удалить expired grants
    fn cleanup_expired(&mut self) {
        self.grants.retain(|_, g| g.is_valid());
    }
}
```

---

## 5. Audit and Compliance

### 5.1 Audit Logger

```rust
use std::collections::HashMap;
use chrono::{DateTime, Utc, Duration};

/// Audit log entry
struct AuditEntry {
    entry_id: String,
    timestamp: DateTime<Utc>,
    agent_id: String,
    user_id: String,
    // Action details
    action_type: String, // access_check, permission_grant, role_change
    permission: String,
    resource: String,
    // Decision
    decision: String, // allowed, denied, pending_approval
    reason: String,
    // Context
    context: HashMap<String, String>,
}

impl AuditEntry {
    fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.to_rfc3339(),
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "permission": self.permission,
            "resource": self.resource,
            "decision": self.decision,
            "reason": self.reason,
            "context": self.context
        })
    }
}

/// Audit logger для RBAC decisions
struct RBACAuditLogger {
    entries: Vec<AuditEntry>,
    max_entries: usize,
}

impl RBACAuditLogger {
    fn new() -> Self {
        Self { entries: Vec::new(), max_entries: 100000 }
    }

    /// Залогировать access control decision
    fn log_access_decision(&mut self, request: &AccessRequest, decision: &AccessDecision) {
        let now = Utc::now();
        let entry = AuditEntry {
            entry_id: format!("audit_{}", now.timestamp()),
            timestamp: now,
            agent_id: request.agent_id.clone(),
            user_id: request.user_id.clone(),
            action_type: "access_check".into(),
            permission: request.permission_type.value().to_string(),
            resource: request.resource.clone(),
            decision: if decision.allowed { "allowed" } else { "denied" }.into(),
            reason: decision.reason.clone(),
            context: HashMap::from([
                ("session_id".into(), request.session_id.clone()),
                ("matched_policy".into(), decision.matched_policy.clone().unwrap_or_default()),
                ("matched_role".into(), decision.matched_role.clone().unwrap_or_default()),
            ]),
        };
        self.add_entry(entry);
    }

    /// Залогировать изменение role assignment
    fn log_role_change(&mut self, agent_id: &str, old_roles: &[String],
                       new_roles: &[String], changed_by: &str) {
        let now = Utc::now();
        let entry = AuditEntry {
            entry_id: format!("audit_{}", now.timestamp()),
            timestamp: now,
            agent_id: agent_id.to_string(),
            user_id: changed_by.to_string(),
            action_type: "role_change".into(),
            permission: "system:role_assign".into(),
            resource: format!("agent:{}", agent_id),
            decision: "completed".into(),
            reason: format!("Roles changed from {:?} to {:?}", old_roles, new_roles),
            context: HashMap::new(),
        };
        self.add_entry(entry);
    }

    fn add_entry(&mut self, entry: AuditEntry) {
        self.entries.push(entry);
        if self.entries.len() > self.max_entries {
            let start = self.entries.len() - self.max_entries;
            self.entries = self.entries.split_off(start);
        }
    }

    /// Запрос audit log
    fn query(&self, agent_id: Option<&str>, start_time: Option<DateTime<Utc>>,
             end_time: Option<DateTime<Utc>>, decision_filter: Option<&str>) -> Vec<&AuditEntry> {
        let mut results: Vec<&AuditEntry> = self.entries.iter().collect();

        if let Some(aid) = agent_id {
            results.retain(|e| e.agent_id == aid);
        }
        if let Some(start) = start_time {
            results.retain(|e| e.timestamp >= start);
        }
        if let Some(end) = end_time {
            results.retain(|e| e.timestamp <= end);
        }
        if let Some(dec) = decision_filter {
            results.retain(|e| e.decision == dec);
        }

        results
    }

    /// Получить summary access denials
    fn get_denial_summary(&self, hours: i64) -> serde_json::Value {
        let cutoff = Utc::now() - Duration::hours(hours);
        let denials: Vec<&AuditEntry> = self.entries.iter()
            .filter(|e| e.decision == "denied" && e.timestamp >= cutoff)
            .collect();

        let mut by_agent: HashMap<String, usize> = HashMap::new();
        let mut by_resource: HashMap<String, usize> = HashMap::new();
        let mut by_reason: HashMap<String, usize> = HashMap::new();

        for d in &denials {
            *by_agent.entry(d.agent_id.clone()).or_insert(0) += 1;
            *by_resource.entry(d.resource.clone()).or_insert(0) += 1;
            *by_reason.entry(d.reason.clone()).or_insert(0) += 1;
        }

        serde_json::json!({
            "total_denials": denials.len(),
            "by_agent": by_agent,
            "by_resource": by_resource,
            "by_reason": by_reason
        })
    }
}
```

---

## 6. Интеграция с SENTINEL

```rust
use sentinel_core::engines::SentinelEngine;
use std::collections::HashMap;

struct RBACConfig {
    /// RBAC конфигурация
    enable_audit: bool,
    enable_rate_limiting: bool,
    enable_temporal_grants: bool,
    default_trust_level: f64,
    max_rate_per_minute: i32,
}

impl Default for RBACConfig {
    fn default() -> Self {
        Self {
            enable_audit: true,
            enable_rate_limiting: true,
            enable_temporal_grants: true,
            default_trust_level: 0.5,
            max_rate_per_minute: 100,
        }
    }
}

/// RBAC engine для SENTINEL framework
struct SENTINELRBACEngine {
    config: RBACConfig,
    store: InMemoryPermissionStore,
    auth_engine: AuthorizationEngine,
    enforcer: PermissionEnforcer,
    temporal_manager: Option<TemporalPermissionManager>,
    audit_logger: Option<RBACAuditLogger>,
    trust_modifier: TrustBasedPermissionModifier,
}

impl SENTINELRBACEngine {
    fn new(config: RBACConfig) -> Self {
        let store = InMemoryPermissionStore::new();
        let auth_engine = AuthorizationEngine::new(store.clone());
        let enforcer = PermissionEnforcer::new(auth_engine.clone());

        let temporal_manager = if config.enable_temporal_grants {
            Some(TemporalPermissionManager::new())
        } else {
            None
        };

        let audit_logger = if config.enable_audit {
            Some(RBACAuditLogger::new())
        } else {
            None
        };

        Self {
            config,
            store,
            auth_engine,
            enforcer,
            temporal_manager,
            audit_logger,
            trust_modifier: TrustBasedPermissionModifier::new(),
        }
    }

    /// Зарегистрировать нового агента
    fn register_agent(&mut self, agent_id: &str, agent_type: &str,
                      roles: Vec<String>, delegated_from: Option<String>) -> &Agent {
        let agent = Agent {
            agent_id: agent_id.to_string(),
            display_name: agent_id.to_string(),
            agent_type: agent_type.to_string(),
            roles,
            delegated_from,
            delegation_scope: Vec::new(),
            trust_level: self.config.default_trust_level,
            last_activity: Utc::now(),
            created_at: Utc::now(),
            metadata: HashMap::new(),
        };
        self.store.add_agent(agent);
        self.store.get_agent(agent_id).unwrap()
    }

    /// Проверить имеет ли агент permission
    fn check_permission(&mut self, agent_id: &str, permission: PermissionType,
                        resource: &str, context: Option<HashMap<String, String>>) -> AccessDecision {
        let request = AccessRequest {
            agent_id: agent_id.to_string(),
            permission_type: permission,
            resource: resource.to_string(),
            session_id: String::new(),
            user_id: String::new(),
            timestamp: Utc::now(),
            context: context.unwrap_or_default(),
        };

        let decision = self.auth_engine.check_access(&request);

        if let Some(ref mut logger) = self.audit_logger {
            logger.log_access_decision(&request, &decision);
        }

        decision
    }

    /// Выдать temporary role агенту
    fn grant_temporary_access(&mut self, agent_id: &str, role: &str,
                              duration_minutes: i64, granted_by: &str) -> Result<String, String> {
        let manager = self.temporal_manager.as_mut()
            .ok_or("Temporal grants disabled")?;

        let grant = manager.grant_temporary_role(
            agent_id, role, duration_minutes, granted_by, None,
        );
        Ok(grant.grant_id.clone())
    }

    /// Обновить agent trust level
    fn update_agent_trust(&mut self, agent_id: &str, trust_delta: f64) {
        if let Some(agent) = self.store.agents.get_mut(agent_id) {
            agent.trust_level = (agent.trust_level + trust_delta).clamp(0.0, 1.0);
        }
    }

    /// Получить audit summary
    fn get_audit_summary(&self, hours: i64) -> serde_json::Value {
        match &self.audit_logger {
            Some(logger) => logger.get_denial_summary(hours),
            None => serde_json::json!({}),
        }
    }
}
```

---

## 7. Итоги

| Компонент | Описание |
|-----------|----------|
| **Permission** | Access type + resource pattern |
| **Role** | Permission group с constraints |
| **Agent** | AI сущность с roles и delegation |
| **Policy** | Explicit allow/deny правила |
| **AuthEngine** | Вычисление access decisions |
| **Enforcer** | Применение decisions к actions |
| **Audit** | Логирование всех decisions |

---

## Следующий урок

→ [Трек 05: Defense Strategies](../../05-defense-strategies/README.md)

---

*AI Security Academy | Трек 04: Agentic Security | Модуль 04.3: Trust & Authorization*
