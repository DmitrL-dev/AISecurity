# Автоматический Response для AI Security

> **Уровень:** Продвинутый  
> **Время:** 50 минут  
> **Трек:** 05 — Defense Strategies  
> **Модуль:** 05.2 — Response  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять стратегии автоматического response для AI security
- [ ] Реализовать фреймворк response actions
- [ ] Построить пайплайн response orchestration
- [ ] Интегрировать автоматический response в SENTINEL

---

## 1. Обзор Response Framework

### 1.1 Стратегии Response

```
┌────────────────────────────────────────────────────────────────────┐
│              AUTOMATED RESPONSE FRAMEWORK                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Response Levels:                                                  │
│  ├── LOG: Записать событие, продолжить обработку                 │
│  ├── WARN: Log + alert, продолжить с осторожностью               │
│  ├── THROTTLE: Rate limit agent/session                          │
│  ├── BLOCK: Заблокировать текущий запрос                         │
│  ├── SUSPEND: Приостановить агента временно                      │
│  └── TERMINATE: Завершить session/agent                          │
│                                                                    │
│  Response Types:                                                   │
│  ├── Immediate: Block, redact, transform                         │
│  ├── Delayed: Alert, escalate, review queue                      │
│  └── Adaptive: Динамическая корректировка security level         │
│                                                                    │
│  Trigger Sources:                                                  │
│  ├── Detection Engine: Anomaly, pattern match                    │
│  ├── Policy Engine: Policy violation                             │
│  ├── RBAC Engine: Permission denied                              │
│  └── External: SIEM, manual trigger                              │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Response Actions

### 2.1 Определение Action

```rust
use std::collections::HashMap;
use std::sync::Mutex;
use chrono::{DateTime, Utc, Duration};

#[derive(Clone, Copy, PartialEq)]
enum ResponseLevel {
    Log = 0,
    Warn = 1,
    Throttle = 2,
    Block = 3,
    Suspend = 4,
    Terminate = 5,
}

#[derive(Clone, Copy, PartialEq)]
enum ActionType {
    Log,
    Alert,
    BlockRequest,
    RedactOutput,
    Throttle,
    SuspendAgent,
    TerminateSession,
    Quarantine,
    Escalate,
    Custom,
}

/// Единичный response action
struct ResponseAction {
    action_type: ActionType,
    level: ResponseLevel,
    parameters: HashMap<String, serde_json::Value>,
    timeout_seconds: f64,
    description: String,
    requires_confirmation: bool,
}

/// Правило маппинга trigger на actions
struct ResponseRule {
    rule_id: String,
    name: String,
    description: String,
    trigger_type: String,
    conditions: HashMap<String, serde_json::Value>,
    actions: Vec<ResponseAction>,
    level: ResponseLevel,
    enabled: bool,
    cooldown_seconds: i64,
    max_triggers_per_hour: usize,
}

impl ResponseRule {
    /// Проверить соответствует ли событие условиям правила
    fn matches(&self, event: &HashMap<String, serde_json::Value>) -> bool {
        if event.get("type").and_then(|v| v.as_str()) != Some(&self.trigger_type) {
            return false;
        }
        for (key, expected) in self.conditions.iter() {
            let actual = match event.get(key) {
                Some(v) => v,
                None => return false,
            };
            if actual != expected {
                return false;
            }
        }
        true
    }
}

/// Событие, триггерящее response
struct ResponseEvent {
    event_id: String,
    timestamp: DateTime<Utc>,
    event_type: String,
    severity: String,
    agent_id: String,
    session_id: String,
    user_id: String,
    details: HashMap<String, serde_json::Value>,
    source: String,
}
```

### 2.2 Action Handlers

```rust
use log::{warn, info};

/// Базовый action handler
trait ActionHandler {
    fn execute(&self, action: &ResponseAction, event: &ResponseEvent) -> serde_json::Value;
    fn action_type(&self) -> ActionType;
}

/// Logging action
struct LogActionHandler;

impl ActionHandler for LogActionHandler {
    fn action_type(&self) -> ActionType { ActionType::Log }

    fn execute(&self, action: &ResponseAction, event: &ResponseEvent) -> serde_json::Value {
        let message = format!(
            "[{}] Agent: {}, Session: {}, Details: {:?}",
            event.event_type, event.agent_id, event.session_id, event.details
        );
        warn!("{}", message);

        serde_json::json!({
            "success": true,
            "logged": true,
            "message": message,
        })
    }
}

/// Block request action
struct BlockRequestHandler {
    blocked_requests: Mutex<HashMap<String, DateTime<Utc>>>,
}

impl ActionHandler for BlockRequestHandler {
    fn action_type(&self) -> ActionType { ActionType::BlockRequest }

    fn execute(&self, action: &ResponseAction, event: &ResponseEvent) -> serde_json::Value {
        let block_key = format!("{}:{}", event.session_id, event.event_id);
        self.blocked_requests.lock().unwrap().insert(block_key, Utc::now());

        let reason = action.parameters.get("reason")
            .and_then(|v| v.as_str())
            .unwrap_or("Security violation");

        serde_json::json!({
            "success": true,
            "blocked": true,
            "reason": reason,
        })
    }
}

/// Throttle action
struct ThrottleHandler {
    throttled: Mutex<HashMap<String, ThrottleInfo>>,
}

struct ThrottleInfo {
    until: DateTime<Utc>,
    rate_limit: u32,
}

impl ActionHandler for ThrottleHandler {
    fn action_type(&self) -> ActionType { ActionType::Throttle }

    fn execute(&self, action: &ResponseAction, event: &ResponseEvent) -> serde_json::Value {
        let mut throttled = self.throttled.lock().unwrap();
        let duration = action.parameters.get("duration_seconds")
            .and_then(|v| v.as_i64()).unwrap_or(60);
        let rate = action.parameters.get("requests_per_minute")
            .and_then(|v| v.as_u64()).unwrap_or(10) as u32;

        throttled.insert(event.agent_id.clone(), ThrottleInfo {
            until: Utc::now() + Duration::seconds(duration),
            rate_limit: rate,
        });

        serde_json::json!({
            "success": true,
            "throttled": true,
            "duration_seconds": duration,
            "rate_limit": rate,
        })
    }
}

impl ThrottleHandler {
    /// Проверить находится ли агент под throttling
    fn is_throttled(&self, agent_id: &str) -> (bool, Option<u32>) {
        let mut throttled = self.throttled.lock().unwrap();
        match throttled.get(agent_id) {
            None => (false, None),
            Some(info) => {
                if Utc::now() >= info.until {
                    throttled.remove(agent_id);
                    (false, None)
                } else {
                    (true, Some(info.rate_limit))
                }
            }
        }
    }
}

/// Suspend agent action
struct SuspendAgentHandler {
    suspended: Mutex<HashMap<String, DateTime<Utc>>>,
}

impl ActionHandler for SuspendAgentHandler {
    fn action_type(&self) -> ActionType { ActionType::SuspendAgent }

    fn execute(&self, action: &ResponseAction, event: &ResponseEvent) -> serde_json::Value {
        let duration = action.parameters.get("duration_seconds")
            .and_then(|v| v.as_i64()).unwrap_or(300);
        self.suspended.lock().unwrap().insert(
            event.agent_id.clone(),
            Utc::now() + Duration::seconds(duration),
        );

        serde_json::json!({
            "success": true,
            "suspended": true,
            "agent_id": event.agent_id,
            "duration_seconds": duration,
        })
    }
}

impl SuspendAgentHandler {
    fn is_suspended(&self, agent_id: &str) -> bool {
        let mut suspended = self.suspended.lock().unwrap();
        match suspended.get(agent_id) {
            None => false,
            Some(until) => {
                if Utc::now() >= *until {
                    suspended.remove(agent_id);
                    false
                } else {
                    true
                }
            }
        }
    }
}
```

---

## 3. Response Orchestrator

```rust
use std::collections::HashMap;
use uuid::Uuid;

/// Результат выполнения response
struct ResponseResult {
    event_id: String,
    rule_id: String,
    success: bool,
    actions_executed: Vec<serde_json::Value>,
    errors: Vec<String>,
    timestamp: DateTime<Utc>,
}

/// Оркестрирует выполнение response
struct ResponseOrchestrator {
    rules: HashMap<String, ResponseRule>,
    handlers: HashMap<ActionType, Box<dyn ActionHandler>>,
    rule_triggers: HashMap<String, Vec<DateTime<Utc>>>,
    last_trigger: HashMap<String, DateTime<Utc>>,
    response_history: Vec<ResponseResult>,
    max_history: usize,
}

impl ResponseOrchestrator {
    fn new() -> Self {
        Self {
            rules: HashMap::new(),
            handlers: HashMap::new(),
            rule_triggers: HashMap::new(),
            last_trigger: HashMap::new(),
            response_history: Vec::new(),
            max_history: 10000,
        }
    }

    /// Зарегистрировать action handler
    fn register_handler(&mut self, handler: Box<dyn ActionHandler>) {
        let at = handler.action_type();
        self.handlers.insert(at, handler);
    }

    /// Добавить response правило
    fn add_rule(&mut self, rule: ResponseRule) {
        self.rules.insert(rule.rule_id.clone(), rule);
    }

    /// Обработать событие и выполнить matching responses
    fn process_event(&mut self, event: &ResponseEvent) -> Vec<ResponseResult> {
        let mut results = Vec::new();

        let rule_ids: Vec<String> = self.rules.keys().cloned().collect();
        for rule_id in rule_ids.iter() {
            let rule = &self.rules[rule_id];
            if !rule.enabled { continue; }
            if !self.check_rate_limit(rule_id) { continue; }

            let result = self.execute_rule(rule_id, event);
            results.push(result);
            self.record_trigger(rule_id);
        }
        results
    }

    /// Проверить можно ли триггерить правило
    fn check_rate_limit(&self, rule_id: &str) -> bool {
        let now = Utc::now();
        if let Some(last) = self.last_trigger.get(rule_id) {
            let rule = &self.rules[rule_id];
            if (now - *last).num_seconds() < rule.cooldown_seconds { return false; }
        }
        let hour_ago = now - Duration::hours(1);
        let recent = self.rule_triggers.get(rule_id)
            .map(|t| t.iter().filter(|t| **t >= hour_ago).count())
            .unwrap_or(0);
        let rule = &self.rules[rule_id];
        recent < rule.max_triggers_per_hour
    }

    /// Выполнить все actions для правила
    fn execute_rule(&self, rule_id: &str, event: &ResponseEvent) -> ResponseResult {
        let rule = &self.rules[rule_id];
        let mut actions_executed = Vec::new();
        let mut errors = Vec::new();

        for action in rule.actions.iter() {
            match self.handlers.get(&action.action_type) {
                None => errors.push(format!("Нет handler для {:?}", action.action_type)),
                Some(handler) => {
                    let result = handler.execute(action, event);
                    actions_executed.push(result);
                }
            }
        }

        ResponseResult {
            event_id: event.event_id.clone(),
            rule_id: rule_id.to_string(),
            success: errors.is_empty(),
            actions_executed,
            errors,
            timestamp: Utc::now(),
        }
    }

    /// Получить статистику response
    fn get_stats(&self) -> serde_json::Value {
        if self.response_history.is_empty() {
            return serde_json::json!({"total_responses": 0});
        }
        let mut by_rule: HashMap<String, usize> = HashMap::new();
        let mut success_count = 0usize;
        for result in self.response_history.iter() {
            *by_rule.entry(result.rule_id.clone()).or_insert(0) += 1;
            if result.success { success_count += 1; }
        }
        serde_json::json!({
            "total_responses": self.response_history.len(),
            "by_rule": by_rule,
            "success_rate": success_count as f64 / self.response_history.len() as f64,
        })
    }
}
```

---

## 4. Предустановленные Response Rules

```rust
/// Правила security response по умолчанию
struct DefaultResponseRules;

impl DefaultResponseRules {
    fn get_all() -> Vec<ResponseRule> {
        vec![
            // Attack detected - high severity
            ResponseRule {
                rule_id: "attack-high".into(),
                name: "High Severity Attack Response".into(),
                description: "Block и alert при high severity атаках".into(),
                trigger_type: "attack_detected".into(),
                conditions: HashMap::from([("severity".into(), serde_json::json!("high"))]),
                level: ResponseLevel::Block,
                actions: vec![
                    ResponseAction { action_type: ActionType::BlockRequest, level: ResponseLevel::Block,
                        parameters: HashMap::from([("reason".into(), serde_json::json!("High severity attack detected"))]),
                        ..Default::default() },
                    ResponseAction { action_type: ActionType::Alert, level: ResponseLevel::Warn,
                        parameters: HashMap::from([("message".into(), serde_json::json!("High severity attack blocked"))]),
                        ..Default::default() },
                    ResponseAction { action_type: ActionType::Log, level: ResponseLevel::Log,
                        ..Default::default() },
                ],
                ..Default::default()
            },

            // Attack detected - medium severity
            ResponseRule {
                rule_id: "attack-medium".into(),
                name: "Medium Severity Attack Response".into(),
                description: "Throttle и мониторинг при medium severity атаках".into(),
                trigger_type: "attack_detected".into(),
                conditions: HashMap::from([("severity".into(), serde_json::json!("medium"))]),
                level: ResponseLevel::Throttle,
                actions: vec![
                    ResponseAction { action_type: ActionType::Throttle, level: ResponseLevel::Throttle,
                        parameters: HashMap::from([
                            ("duration_seconds".into(), serde_json::json!(60)),
                            ("requests_per_minute".into(), serde_json::json!(5)),
                        ]),
                        ..Default::default() },
                    ResponseAction { action_type: ActionType::Log, level: ResponseLevel::Log,
                        ..Default::default() },
                ],
                ..Default::default()
            },

            // Policy violation
            ResponseRule {
                rule_id: "policy-violation".into(),
                name: "Policy Violation Response".into(),
                description: "Block policy violations".into(),
                trigger_type: "policy_violation".into(),
                conditions: HashMap::new(),
                level: ResponseLevel::Block,
                actions: vec![
                    ResponseAction { action_type: ActionType::BlockRequest, level: ResponseLevel::Block,
                        parameters: HashMap::from([("reason".into(), serde_json::json!("Policy violation"))]),
                        ..Default::default() },
                    ResponseAction { action_type: ActionType::Log, level: ResponseLevel::Log,
                        ..Default::default() },
                ],
                ..Default::default()
            },

            // Repeated failures
            ResponseRule {
                rule_id: "repeated-failures".into(),
                name: "Repeated Failures Response".into(),
                description: "Suspend агента с слишком многими failures".into(),
                trigger_type: "repeated_failures".into(),
                conditions: HashMap::from([("failure_count".into(), serde_json::json!({"min": 5}))]),
                level: ResponseLevel::Suspend,
                actions: vec![
                    ResponseAction { action_type: ActionType::SuspendAgent, level: ResponseLevel::Suspend,
                        parameters: HashMap::from([("duration_seconds".into(), serde_json::json!(300))]),
                        ..Default::default() },
                    ResponseAction { action_type: ActionType::Alert, level: ResponseLevel::Warn,
                        parameters: HashMap::from([("message".into(), serde_json::json!("Agent suspended из-за failures"))]),
                        ..Default::default() },
                ],
                ..Default::default()
            },
        ]
    }
}
```

---

## 5. Интеграция с SENTINEL

```rust
use sentinel_core::engines::SentinelEngine;

/// Конфигурация response engine
struct ResponseConfig {
    enable_default_rules: bool,
    max_history: usize,
    alert_callbacks: Vec<Box<dyn Fn(&serde_json::Value)>>,
}

impl Default for ResponseConfig {
    fn default() -> Self {
        Self {
            enable_default_rules: true,
            max_history: 10000,
            alert_callbacks: Vec::new(),
        }
    }
}

/// Response engine для SENTINEL framework
struct SENTINELResponseEngine {
    config: ResponseConfig,
    orchestrator: ResponseOrchestrator,
    log_handler: LogActionHandler,
    block_handler: BlockRequestHandler,
    throttle_handler: ThrottleHandler,
    suspend_handler: SuspendAgentHandler,
}

impl SENTINELResponseEngine {
    fn new(config: ResponseConfig) -> Self {
        let mut orchestrator = ResponseOrchestrator::new();

        // Register handlers
        let log_handler = LogActionHandler;
        let block_handler = BlockRequestHandler { blocked_requests: Mutex::new(HashMap::new()) };
        let throttle_handler = ThrottleHandler { throttled: Mutex::new(HashMap::new()) };
        let suspend_handler = SuspendAgentHandler { suspended: Mutex::new(HashMap::new()) };

        // Load default rules
        if config.enable_default_rules {
            for rule in DefaultResponseRules::get_all() {
                orchestrator.add_rule(rule);
            }
        }

        Self { config, orchestrator, log_handler, block_handler, throttle_handler, suspend_handler }
    }

    /// Обработать detection event
    fn process_detection(
        &mut self, detection_type: &str, severity: &str,
        agent_id: &str, session_id: &str, user_id: &str,
        details: Option<HashMap<String, serde_json::Value>>,
    ) -> Vec<ResponseResult> {
        let event = ResponseEvent {
            event_id: Uuid::new_v4().to_string(),
            timestamp: Utc::now(),
            event_type: detection_type.to_string(),
            severity: severity.to_string(),
            agent_id: agent_id.to_string(),
            session_id: session_id.to_string(),
            user_id: user_id.to_string(),
            details: details.unwrap_or_default(),
            source: "detection_engine".to_string(),
        };
        self.orchestrator.process_event(&event)
    }

    /// Проверить заблокирован ли агент
    fn is_agent_blocked(&self, agent_id: &str) -> bool {
        self.suspend_handler.is_suspended(agent_id)
    }

    /// Проверить throttled ли агент
    fn is_throttled(&self, agent_id: &str) -> (bool, Option<u32>) {
        self.throttle_handler.is_throttled(agent_id)
    }

    /// Получить статистику response
    fn get_stats(&self) -> serde_json::Value {
        self.orchestrator.get_stats()
    }
}
```

---

## 6. Итоги

| Компонент | Описание |
|-----------|----------|
| **ResponseAction** | Единичный action (block, alert) |
| **ResponseRule** | Trigger conditions → actions |
| **ActionHandler** | Выполнение action |
| **Orchestrator** | Rate limiting + execution |
| **DefaultRules** | Предустановленные security rules |

---

## Следующий урок

→ [Трек 06: Advanced](../../06-advanced/README.md)

---

*AI Security Academy | Трек 05: Defense Strategies | Модуль 05.2: Response*
