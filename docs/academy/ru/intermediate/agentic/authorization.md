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

```rust
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum Permission {
    ReadFiles,
    WriteFiles,
    ExecuteCode,
    NetworkAccess,
    DatabaseRead,
    DatabaseWrite,
}

struct Role {
    name: String,
    permissions: HashSet<Permission>,
    resource_scopes: HashMap<Permission, Vec<String>>,
}

/// Role-based access control для агентов.
struct RBACManager {
    agent_id: String,
    roles: Vec<Role>,
}

impl RBACManager {
    fn new(agent_id: &str, assigned_roles: &[&str]) -> Self {
        let all_roles = Self::default_roles();
        let roles = assigned_roles.iter()
            .filter_map(|r| all_roles.get(*r).cloned())
            .collect();
        Self { agent_id: agent_id.to_string(), roles }
    }

    /// Проверить имеет ли агент permission на resource.
    fn check_permission(&self, permission: &Permission, resource: Option<&str>) -> serde_json::Value {
        for role in &self.roles {
            if role.permissions.contains(permission) {
                if self.resource_in_scope(role, permission, resource) {
                    return serde_json::json!({
                        "allowed": true,
                        "role": role.name,
                        "reason": format!("Permission {:?} granted by role {}", permission, role.name)
                    });
                }
            }
        }

        serde_json::json!({
            "allowed": false,
            "reason": format!("No role grants {:?} for {:?}", permission, resource)
        })
    }

    /// Проверить находится ли resource в allowed scope.
    fn resource_in_scope(&self, role: &Role, permission: &Permission, resource: Option<&str>) -> bool {
        let resource = match resource {
            Some(r) => r,
            None => return true,
        };

        match role.resource_scopes.get(permission) {
            None => true, // No scope restriction
            Some(scopes) => scopes.iter().any(|scope| {
                glob_match::glob_match(scope, resource)
            }),
        }
    }
}
```

---

### 2. Capability-Based Security

```rust
use std::collections::{HashMap, HashSet};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

/// Unforgeable capability token.
struct Capability {
    id: String,
    action: String,
    resource: String,
    constraints: HashMap<String, serde_json::Value>,
    expires: Option<SystemTime>,
    revoked: bool,
}

impl Capability {
    fn new(action: &str, resource: &str, constraints: HashMap<String, serde_json::Value>, ttl_seconds: u64) -> Self {
        use rand::Rng;
        let id: String = rand::thread_rng()
            .sample_iter(&rand::distributions::Alphanumeric)
            .take(22)
            .map(char::from)
            .collect();
        Self {
            id,
            action: action.to_string(),
            resource: resource.to_string(),
            constraints,
            expires: Some(SystemTime::now() + Duration::from_secs(ttl_seconds)),
            revoked: false,
        }
    }

    fn is_valid(&self) -> bool {
        if self.revoked { return false; }
        if let Some(exp) = self.expires {
            if SystemTime::now() > exp { return false; }
        }
        true
    }
}

/// Управление capabilities для агентов.
struct CapabilityManager {
    capabilities: HashMap<String, Capability>,
}

impl CapabilityManager {
    fn new() -> Self {
        Self { capabilities: HashMap::new() }
    }

    /// Выдать новую capability.
    fn grant(&mut self, action: &str, resource: &str,
             constraints: Option<HashMap<String, serde_json::Value>>,
             ttl_seconds: u64) -> &Capability {
        let cap = Capability::new(action, resource, constraints.unwrap_or_default(), ttl_seconds);
        let id = cap.id.clone();
        self.capabilities.insert(id.clone(), cap);
        self.capabilities.get(&id).unwrap()
    }

    /// Проверить позволяет ли capability action на resource.
    fn check(&self, cap_id: &str, action: &str, resource: &str) -> serde_json::Value {
        let cap = match self.capabilities.get(cap_id) {
            Some(c) => c,
            None => return serde_json::json!({"allowed": false, "reason": "Capability not found"}),
        };

        if !cap.is_valid() {
            return serde_json::json!({"allowed": false, "reason": "Capability expired or revoked"});
        }
        if cap.action != action {
            return serde_json::json!({"allowed": false, "reason": format!("Capability is for {}, not {}", cap.action, action)});
        }
        if cap.resource != resource {
            return serde_json::json!({"allowed": false, "reason": "Resource not covered by capability"});
        }

        serde_json::json!({"allowed": true})
    }

    /// Отозвать capability.
    fn revoke(&mut self, cap_id: &str) {
        if let Some(cap) = self.capabilities.get_mut(cap_id) {
            cap.revoked = true;
        }
    }
}
```

---

### 3. ABAC (Attribute-Based Access Control)

```rust
use std::collections::HashMap;

struct Policy {
    name: String,
    effect: String, // "allow" или "deny"
    actions: Vec<String>,
    resources: Vec<String>,
    condition: Box<dyn Fn(&HashMap<String, serde_json::Value>) -> bool>,
}

/// Attribute-based access control.
struct ABACManager {
    policies: Vec<Policy>,
}

impl ABACManager {
    fn new() -> Self {
        Self { policies: vec![] }
    }

    fn add_policy(&mut self, policy: Policy) {
        self.policies.push(policy);
    }

    /// Evaluate policies для решения авторизации.
    fn evaluate(&self, action: &str, resource: &str, context: &HashMap<String, serde_json::Value>) -> serde_json::Value {
        let mut applicable: Vec<&Policy> = vec![];

        for policy in &self.policies {
            if policy.actions.iter().any(|a| a == action || a == "*") {
                if policy.resources.iter().any(|r| r == resource || r == "*") {
                    if (policy.condition)(context) {
                        applicable.push(policy);
                    }
                }
            }
        }

        // Deny имеет приоритет
        for policy in &applicable {
            if policy.effect == "deny" {
                return serde_json::json!({
                    "allowed": false,
                    "policy": policy.name,
                    "reason": format!("Denied by policy: {}", policy.name)
                });
            }
        }

        // Any allow grants access
        for policy in &applicable {
            if policy.effect == "allow" {
                return serde_json::json!({
                    "allowed": true,
                    "policy": policy.name
                });
            }
        }

        // Default deny
        serde_json::json!({"allowed": false, "reason": "No policy grants access"})
    }
}

// Примеры policies
let time_based_policy = Policy {
    name: "business_hours_only".to_string(),
    effect: "deny".to_string(),
    actions: vec!["write".into(), "delete".into()],
    resources: vec!["*".into()],
    condition: Box::new(|ctx| {
        let hour = ctx.get("hour").and_then(|v| v.as_u64()).unwrap_or(12);
        !(9 <= hour && hour <= 17)
    }),
};

let high_risk_review = Policy {
    name: "require_review_for_production".to_string(),
    effect: "deny".to_string(),
    actions: vec!["deploy".into(), "delete".into()],
    resources: vec!["production/*".into()],
    condition: Box::new(|ctx| {
        !ctx.get("human_approved").and_then(|v| v.as_bool()).unwrap_or(false)
    }),
};
```

---

## Паттерны имплементации

### 1. Authorization Middleware

```rust
/// Middleware для авторизации tool агентов.
struct AuthorizationMiddleware {
    authz: RBACManager,
    audit_log: Vec<serde_json::Value>,
}

impl AuthorizationMiddleware {
    fn new(authz: RBACManager) -> Self {
        Self { authz, audit_log: vec![] }
    }

    /// Проверить авторизацию перед выполнением tool.
    fn authorize_tool_call(
        &mut self,
        agent_id: &str,
        tool_name: &str,
        resource: &str,
        required_permission: &Permission,
    ) -> Result<(), String> {
        // Проверить авторизацию
        let result = self.authz.check_permission(required_permission, Some(resource));

        // Залогировать попытку
        self.audit_log.push(serde_json::json!({
            "agent_id": agent_id,
            "tool": tool_name,
            "resource": resource,
            "result": result
        }));

        if result["allowed"].as_bool().unwrap_or(false) {
            Ok(())
        } else {
            Err(result["reason"].as_str().unwrap_or("Permission denied").to_string())
        }
    }
}
```

---

### 2. Dynamic Permission Escalation

```rust
use std::collections::HashMap;

/// Обработка временной эскалации permissions.
struct DynamicEscalationManager {
    base: RBACManager,
    temporary_grants: HashMap<String, serde_json::Value>,
}

impl DynamicEscalationManager {
    fn new(base: RBACManager) -> Self {
        Self { base, temporary_grants: HashMap::new() }
    }

    /// Запросить временные elevated permissions.
    async fn request_escalation(
        &mut self,
        agent_id: &str,
        permission: &Permission,
        resource: &str,
        justification: &str,
        approve: &dyn AsyncApprovalCallback,
    ) -> serde_json::Value {
        // Проверить нужна ли эскалация
        let base_check = self.base.check_permission(permission, Some(resource));
        if base_check["allowed"].as_bool().unwrap_or(false) {
            return base_check;
        }

        // Запросить human approval
        let approval = approve.request(serde_json::json!({
            "agent_id": agent_id,
            "permission": format!("{:?}", permission),
            "resource": resource,
            "justification": justification
        })).await;

        if approval["approved"].as_bool().unwrap_or(false) {
            let ttl = approval["ttl"].as_u64().unwrap_or(300);
            // Выдать temporary capability
            let grant_id = self.grant_temporary(agent_id, permission, resource, ttl);

            return serde_json::json!({
                "allowed": true,
                "grant_id": grant_id,
                "temporary": true,
                "expires_in": ttl
            });
        }

        serde_json::json!({
            "allowed": false,
            "reason": "Escalation request denied"
        })
    }
}
```

---

## Интеграция с SENTINEL

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::new();

// Сканирование запросов авторизации на предмет инъекций
let result = engine.analyze(&justification_text);

if result.detected {
    log::warn!(
        "Подозрительный запрос эскалации: risk={}, categories={:?}",
        result.risk_score, result.categories
    );
    // Отклонить запрос или потребовать дополнительную верификацию
}
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
