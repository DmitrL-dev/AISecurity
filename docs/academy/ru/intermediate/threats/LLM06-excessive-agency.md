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

```rust
// ОПАСНО: Агент с excessive capabilities
struct CustomerSupportAgent {
    tools: HashMap<String, Box<dyn Fn(&str) -> String>>,
}

impl CustomerSupportAgent {
    fn new() -> Self {
        let mut tools: HashMap<String, Box<dyn Fn(&str) -> String>> = HashMap::new();
        tools.insert("lookup_customer".into(), Box::new(|id| lookup_customer(id)));
        tools.insert("update_customer".into(), Box::new(|id| update_customer(id)));
        tools.insert("issue_refund".into(), Box::new(|id| issue_refund(id)));
        tools.insert("delete_customer".into(), Box::new(|id| delete_customer(id)));       // Зачем поддержке это?
        tools.insert("access_all_records".into(), Box::new(|_| access_all_records()));     // PII exposure risk
        tools.insert("execute_sql".into(), Box::new(|q| execute_sql(q)));                  // SQL injection vector!
        tools.insert("run_shell_command".into(), Box::new(|c| run_shell_command(c)));      // Complete compromise
        Self { tools }
    }
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

```rust
// ОПАСНО: Агент решает и действует автономно
struct AutonomousAgent {
    llm: Box<dyn LLMModel>,
}

impl AutonomousAgent {
    fn process_request(&self, user_input: &str) {
        // LLM решает что делать
        let action_plan = self.llm.generate(
            &format!("Decide what actions to take: {}", user_input)
        );

        // Выполняется без human review
        for action in &action_plan {
            self.execute(action); // Нет approval workflow!
        }
    }
}
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

```rust
// Множество агентов которые могут delegate друг другу
struct ResearchAgent { coder_agent: CoderAgent }
impl ResearchAgent {
    fn delegate_to_coder(&self, task: &str) -> String {
        self.coder_agent.execute(task)
    }
}

struct CoderAgent { executor_agent: ExecutorAgent }
impl CoderAgent {
    fn delegate_to_executor(&self, code: &str) -> String {
        self.executor_agent.run(code) // Runs arbitrary code!
    }
}

struct ExecutorAgent;
impl ExecutorAgent {
    fn run(&self, code: &str) -> String {
        eval(code) // Ultimate privilege escalation
    }
}
```

---

## Защита: Principle of Least Privilege

### 1. Minimal Tool Set

```rust
struct SecureCustomerSupportAgent {
    /// Агент с минимально необходимыми capabilities.
    tools: HashMap<String, Box<dyn Fn(&str) -> String>>,
}

impl SecureCustomerSupportAgent {
    fn new(_user_role: &str) -> Self {
        // Только tools нужные для customer support
        let mut tools: HashMap<String, Box<dyn Fn(&str) -> String>> = HashMap::new();
        tools.insert("lookup_order_status".into(), Box::new(|id| lookup_order(id)));
        tools.insert("view_customer_name".into(), Box::new(|id| view_customer_basic(id))); // Limited fields
        tools.insert("create_support_ticket".into(), Box::new(|d| create_ticket(d)));
        tools.insert("request_refund_review".into(), Box::new(|id| request_refund(id)));   // Request, не execute!
        Self { tools }

        // Нет data mutation без approval
        // Нет system access
        // Нет access к данным других customers
    }
}
```

---

### 2. Capability Scoping

```rust
use std::collections::HashSet;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum Capability {
    ReadOwnData,
    ReadAllData,       // Требует special approval
    WriteOwnData,
    WriteAllData,      // Требует special approval
    DeleteData,        // Требует human approval
    ExecuteCode,       // Почти никогда не granted
    NetworkAccess,
    FileSystemAccess,
}

/// Fine-grained agent capability control.
struct AgentPermissions {
    capabilities: HashSet<Capability>,
    max_actions_per_session: usize,
    requires_approval_for: HashSet<Capability>,
    blocked_capabilities: HashSet<Capability>,
}

/// Enforce capability restrictions на agent actions.
struct CapabilityEnforcer {
    permissions: AgentPermissions,
    action_count: usize,
}

impl CapabilityEnforcer {
    /// Проверка разрешено ли действие.
    fn check_permission(&mut self, capability: Capability) -> Result<bool, String> {
        // Check if blocked
        if self.permissions.blocked_capabilities.contains(&capability) {
            return Err(format!("Capability blocked: {:?}", capability));
        }

        // Check if granted
        if !self.permissions.capabilities.contains(&capability) {
            return Err(format!("Capability not granted: {:?}", capability));
        }

        // Check action limit
        if self.action_count > self.permissions.max_actions_per_session {
            return Err("Action limit exceeded".to_string());
        }

        // Check if needs approval
        if self.permissions.requires_approval_for.contains(&capability) {
            return Ok(self.request_human_approval(capability));
        }

        Ok(true)
    }
}
```

---

### 3. Human-in-the-Loop для Sensitive Actions

```rust
#[derive(Debug, Clone, PartialEq)]
enum ActionSensitivity {
    Low,       // Auto-approve
    Medium,    // Log and notify
    High,      // Require approval
    Critical,  // Require multi-party approval
}

struct ApprovalWorkflow {
    /// Human-in-the-loop approval для sensitive actions.
    sensitivity_map: HashMap<String, ActionSensitivity>,
}

impl ApprovalWorkflow {
    fn new() -> Self {
        let mut map = HashMap::new();
        map.insert("read_data".into(), ActionSensitivity::Low);
        map.insert("update_record".into(), ActionSensitivity::Medium);
        map.insert("delete_record".into(), ActionSensitivity::High);
        map.insert("execute_code".into(), ActionSensitivity::Critical);
        map.insert("modify_permissions".into(), ActionSensitivity::Critical);
        map.insert("bulk_operations".into(), ActionSensitivity::High);
        map.insert("financial_transaction".into(), ActionSensitivity::Critical);
        Self { sensitivity_map: map }
    }

    /// Запрос human approval для sensitive action.
    async fn request_approval(
        &self,
        action: &str,
        context: &HashMap<String, String>,
        timeout_seconds: u64,
    ) -> bool {
        let sensitivity = self.sensitivity_map
            .get(action)
            .unwrap_or(&ActionSensitivity::High);

        match sensitivity {
            ActionSensitivity::Low => true,
            ActionSensitivity::Medium => {
                self.log_and_notify(action, context);
                true
            }
            ActionSensitivity::High => {
                self.wait_for_single_approval(action, context, timeout_seconds).await
            }
            ActionSensitivity::Critical => {
                self.wait_for_multi_approval(action, context, timeout_seconds).await
            }
        }
    }
}
```

---

### 4. Action Limits and Rate Limiting

```rust
use std::collections::HashMap;
use std::time::{Duration, Instant};

struct RateLimitConfig {
    count: usize,
    window_minutes: u64,
}

struct ActionRateLimiter {
    /// Ограничение agent actions для предотвращения runaway поведения.
    limits: HashMap<String, RateLimitConfig>,
    action_log: HashMap<String, Vec<Instant>>,
}

impl ActionRateLimiter {
    fn new() -> Self {
        let mut limits = HashMap::new();
        limits.insert("read".into(), RateLimitConfig { count: 100, window_minutes: 1 });
        limits.insert("write".into(), RateLimitConfig { count: 10, window_minutes: 1 });
        limits.insert("delete".into(), RateLimitConfig { count: 3, window_minutes: 60 });
        limits.insert("execute".into(), RateLimitConfig { count: 1, window_minutes: 60 });
        Self { limits, action_log: HashMap::new() }
    }

    /// Проверка находится ли action в пределах rate limits.
    fn check_rate_limit(&mut self, agent_id: &str, action_type: &str) -> bool {
        let limit_config = match self.limits.get(action_type) {
            Some(c) => c,
            None => return true,
        };

        let window = Duration::from_secs(limit_config.window_minutes * 60);
        let now = Instant::now();
        let key = format!("{}:{}", agent_id, action_type);

        let entries = self.action_log.entry(key).or_insert_with(Vec::new);
        entries.retain(|t| now.duration_since(*t) < window);

        if entries.len() >= limit_config.count {
            return false;
        }

        entries.push(now);
        true
    }
}
```

---

## SENTINEL Integration

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::new();

// Сканирование agent actions на excessive agency
let action_text = format!("tool:{} params:{:?}", tool_name, params);
let result = engine.analyze(&action_text);

if result.detected {
    log::warn!(
        "Excessive agency обнаружена: risk={}, categories={:?}, time={}μs",
        result.risk_score, result.categories, result.processing_time_us
    );
    // Блокировка действия или запрос approval
}
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
