# Фреймворк политик для безопасности AI

> **Уровень:** Продвинутый  
> **Время:** 50 минут  
> **Трек:** 07 — Governance  
> **Модуль:** 07.1 — Политики  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять структуру политик безопасности для AI систем
- [ ] Реализовать движок политик с оценкой правил
- [ ] Построить управление жизненным циклом политик
- [ ] Интегрировать политики в фреймворк SENTINEL

---

## 1. Обзор фреймворка политик

### 1.1 Зачем нужен фреймворк политик?

Политики обеспечивают декларативное управление безопасностью AI систем.

```
┌────────────────────────────────────────────────────────────────────┐
│              АРХИТЕКТУРА ФРЕЙМВОРКА ПОЛИТИК                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  [Определение политики] → [Движок политик] → [Точки применения]   │
│         ↓                      ↓                    ↓              │
│     YAML/JSON              Оценка              Действия            │
│                                                                    │
│  Типы политик:                                                     │
│  ├── Политики доступа: Кто может делать что                       │
│  ├── Контентные политики: Что разрешено во вводе/выводе           │
│  ├── Поведенческие политики: Разрешённые паттерны поведения      │
│  └── Политики соответствия: Регуляторные требования              │
│                                                                    │
│  Точки применения:                                                 │
│  ├── Pre-request: До обработки запроса                            │
│  ├── Mid-processing: Во время выполнения                          │
│  └── Post-response: После генерации ответа                        │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Иерархия политик

```
Структура политик:
├── Уровень организации
│   └── Глобальные политики, требования соответствия
├── Уровень системы
│   └── Правила специфичные для AI системы
├── Уровень приложения
│   └── Ограничения приложения
└── Уровень сессии
    └── Динамические, контекстные правила
```

---

## 2. Модель политики

### 2.1 Определение политики

```rust
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use regex::Regex;
use serde_json::Value;

#[derive(Clone, Debug)]
enum PolicyType {
    Access,
    Content,
    Behavior,
    Compliance,
    Custom,
}

#[derive(Clone, Debug, PartialEq)]
enum PolicyEffect {
    Allow,
    Deny,
    Audit,
    RequireApproval,
}

#[derive(Clone, Debug, PartialEq)]
enum EnforcementPoint {
    PreRequest,
    MidProcessing,
    PostResponse,
    Always,
}

/// Условие для оценки политики
#[derive(Clone, Debug)]
struct PolicyCondition {
    field: String,     // Путь к полю в контексте
    operator: String,  // eq, ne, gt, lt, in, contains, matches
    value: Value,
}

impl PolicyCondition {
    /// Оценить условие относительно контекста
    fn evaluate(&self, context: &HashMap<String, Value>) -> bool {
        let actual = self.get_field_value(context, &self.field);

        match self.operator.as_str() {
            "eq" => actual.as_ref() == Some(&self.value),
            "ne" => actual.as_ref() != Some(&self.value),
            "gt" => {
                match (actual.as_ref().and_then(|v| v.as_f64()),
                       self.value.as_f64()) {
                    (Some(a), Some(b)) => a > b,
                    _ => false,
                }
            }
            "lt" => {
                match (actual.as_ref().and_then(|v| v.as_f64()),
                       self.value.as_f64()) {
                    (Some(a), Some(b)) => a < b,
                    _ => false,
                }
            }
            "in" => {
                if let Some(arr) = self.value.as_array() {
                    actual.as_ref().map_or(false, |a| arr.contains(a))
                } else {
                    false
                }
            }
            "contains" => {
                match (actual.as_ref().and_then(|v| v.as_str()),
                       self.value.as_str()) {
                    (Some(haystack), Some(needle)) => haystack.contains(needle),
                    _ => false,
                }
            }
            "matches" => {
                match (actual.as_ref().and_then(|v| v.as_str()),
                       self.value.as_str()) {
                    (Some(text), Some(pattern)) => {
                        Regex::new(pattern).map_or(false, |re| re.is_match(text))
                    }
                    _ => false,
                }
            }
            "exists" => actual.is_some(),
            _ => false,
        }
    }

    /// Получить значение вложенного поля через точечную нотацию
    fn get_field_value(&self, context: &HashMap<String, Value>,
                       field: &str) -> Option<Value> {
        let parts: Vec<&str> = field.split('.').collect();
        let mut current: Value = serde_json::to_value(context).ok()?;
        for part in parts {
            current = current.get(part)?.clone();
        }
        Some(current)
    }
}

/// Одно правило внутри политики
#[derive(Clone, Debug)]
struct PolicyRule {
    rule_id: String,
    description: String,
    conditions: Vec<PolicyCondition>,
    effect: PolicyEffect,
    priority: i32,

    // Действия
    actions: Vec<String>,
    message: String,
}

impl PolicyRule {
    /// Проверить совпадение всех условий
    fn evaluate(&self, context: &HashMap<String, Value>) -> bool {
        self.conditions.iter().all(|c| c.evaluate(context))
    }
}

/// Полное определение политики
#[derive(Clone, Debug)]
struct Policy {
    policy_id: String,
    name: String,
    description: String,
    policy_type: PolicyType,
    version: String,

    // Правила
    rules: Vec<PolicyRule>,

    // Применение
    enforcement_points: Vec<EnforcementPoint>,

    // Область действия
    target_systems: Vec<String>,
    target_agents: Vec<String>,

    // Метаданные
    enabled: bool,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
    author: String,
    tags: Vec<String>,
}

impl Policy {
    /// Проверить применимость политики к системе/агенту
    fn matches_target(&self, system_id: &str, agent_id: &str) -> bool {
        let system_match = self.target_systems.iter()
            .any(|t| glob_match(t, system_id));
        let agent_match = self.target_agents.iter()
            .any(|t| glob_match(t, agent_id));
        system_match && agent_match
    }
}

fn glob_match(pattern: &str, value: &str) -> bool {
    if pattern == "*" { return true; }
    pattern == value
}
```

---

## 3. Движок политик

### 3.1 Хранилище политик

```rust
use std::collections::HashMap;
use std::sync::RwLock;

/// Абстрактное хранилище политик
trait PolicyStore: Send + Sync {
    fn add(&self, policy: Policy);
    fn get(&self, policy_id: &str) -> Option<Policy>;
    fn remove(&self, policy_id: &str);
    fn list_all(&self) -> Vec<Policy>;
    fn find_applicable(&self, system_id: &str, agent_id: &str,
                       enforcement_point: &EnforcementPoint) -> Vec<Policy>;
}

/// In-memory хранилище политик
struct InMemoryPolicyStore {
    policies: RwLock<HashMap<String, Policy>>,
}

impl InMemoryPolicyStore {
    fn new() -> Self {
        Self { policies: RwLock::new(HashMap::new()) }
    }
}

impl PolicyStore for InMemoryPolicyStore {
    fn add(&self, policy: Policy) {
        let mut policies = self.policies.write().unwrap();
        policies.insert(policy.policy_id.clone(), policy);
    }

    fn get(&self, policy_id: &str) -> Option<Policy> {
        self.policies.read().unwrap().get(policy_id).cloned()
    }

    fn remove(&self, policy_id: &str) {
        self.policies.write().unwrap().remove(policy_id);
    }

    fn list_all(&self) -> Vec<Policy> {
        self.policies.read().unwrap().values().cloned().collect()
    }

    fn find_applicable(&self, system_id: &str, agent_id: &str,
                       enforcement_point: &EnforcementPoint) -> Vec<Policy> {
        let policies = self.policies.read().unwrap();
        let mut applicable: Vec<Policy> = policies.values()
            .filter(|policy| {
                if !policy.enabled { return false; }
                if !policy.matches_target(system_id, agent_id) { return false; }
                if !policy.enforcement_points.contains(&EnforcementPoint::Always)
                    && !policy.enforcement_points.contains(enforcement_point) {
                    return false;
                }
                true
            })
            .cloned()
            .collect();

        applicable.sort_by(|a, b| {
            let max_a = a.rules.iter().map(|r| r.priority).max().unwrap_or(0);
            let max_b = b.rules.iter().map(|r| r.priority).max().unwrap_or(0);
            max_b.cmp(&max_a)
        });

        applicable
    }
}
```

### 3.2 Оценщик политик

```rust
use std::collections::HashMap;
use serde_json::Value;

/// Результат оценки политики
#[derive(Clone, Debug)]
struct EvaluationResult {
    policy_id: String,
    rule_id: String,
    effect: PolicyEffect,
    matched: bool,
    message: String,
    actions: Vec<String>,
}

/// Финальное решение от всех политик
#[derive(Clone, Debug)]
struct PolicyDecision {
    allowed: bool,
    reason: String,
    effects: Vec<PolicyEffect>,
    results: Vec<EvaluationResult>,
    actions_to_execute: Vec<String>,
}

/// Оценивает политики относительно контекста
struct PolicyEvaluator {
    store: Box<dyn PolicyStore>,
}

impl PolicyEvaluator {
    fn new(store: Box<dyn PolicyStore>) -> Self {
        Self { store }
    }

    /// Оценить все применимые политики.
    ///
    /// # Arguments
    /// * `context` - Контекст оценки с данными запроса
    /// * `system_id` - ID целевой системы
    /// * `agent_id` - Агент выполняющий действие
    /// * `enforcement_point` - Когда происходит оценка
    ///
    /// # Returns
    /// PolicyDecision с финальными allow/deny и действиями
    fn evaluate(&self, context: &HashMap<String, Value>,
                system_id: &str, agent_id: &str,
                enforcement_point: &EnforcementPoint) -> PolicyDecision {
        // Получить применимые политики
        let policies = self.store.find_applicable(
            system_id, agent_id, enforcement_point);

        let mut all_results: Vec<EvaluationResult> = Vec::new();
        let mut all_effects: Vec<PolicyEffect> = Vec::new();
        let mut all_actions: Vec<String> = Vec::new();

        for policy in &policies {
            let mut sorted_rules = policy.rules.clone();
            sorted_rules.sort_by(|a, b| b.priority.cmp(&a.priority));

            for rule in &sorted_rules {
                if rule.evaluate(context) {
                    let result = EvaluationResult {
                        policy_id: policy.policy_id.clone(),
                        rule_id: rule.rule_id.clone(),
                        effect: rule.effect.clone(),
                        matched: true,
                        message: rule.message.clone(),
                        actions: rule.actions.clone(),
                    };
                    all_effects.push(rule.effect.clone());
                    all_actions.extend(rule.actions.clone());
                    all_results.push(result);
                }
            }
        }

        // Определить финальное решение
        // DENY имеет приоритет, затем REQUIRE_APPROVAL, затем ALLOW
        if all_effects.contains(&PolicyEffect::Deny) {
            PolicyDecision {
                allowed: false,
                reason: "Отклонено политикой".into(),
                effects: all_effects,
                results: all_results,
                actions_to_execute: all_actions,
            }
        } else if all_effects.contains(&PolicyEffect::RequireApproval) {
            PolicyDecision {
                allowed: true,
                reason: "Требуется одобрение".into(),
                effects: all_effects,
                results: all_results,
                actions_to_execute: all_actions,
            }
        } else if all_effects.contains(&PolicyEffect::Allow) {
            PolicyDecision {
                allowed: true,
                reason: "Разрешено политикой".into(),
                effects: all_effects,
                results: all_results,
                actions_to_execute: all_actions,
            }
        } else {
            // По умолчанию deny если нет явного allow
            PolicyDecision {
                allowed: false,
                reason: "Нет подходящей политики allow".into(),
                effects: vec![],
                results: vec![],
                actions_to_execute: vec![],
            }
        }
    }
}
```

---

## 4. Типовые политики

### 4.1 Контентная политика

```yaml
# content_safety_policy.yaml
policy_id: content-safety-001
name: Политика безопасности контента
description: Блокирует вредный контент в запросах и ответах
type: content
version: "1.0"

rules:
  - rule_id: block-harmful-keywords
    description: Блокировать запросы с вредными ключевыми словами
    conditions:
      - field: request.text
        operator: matches
        value: ".*(bomb|weapon|illegal|hack).*"
    effect: deny
    priority: 100
    message: "Запрос содержит запрещённый контент"
    actions:
      - log_security_event
      - increment_violation_counter

  - rule_id: block-pii-in-response
    description: Блокировать PII в ответах
    conditions:
      - field: response.contains_pii
        operator: eq
        value: true
    effect: deny
    priority: 90
    message: "Ответ содержит PII — заблокирован"
    actions:
      - redact_response
      - log_pii_event

  - rule_id: allow-general-content
    description: Разрешить общий контент
    conditions:
      - field: request.risk_score
        operator: lt
        value: 0.5
    effect: allow
    priority: 10

enforcement_points:
  - pre_request
  - post_response

target_systems:
  - "*"

enabled: true
author: security-team
tags:
  - content
  - safety
```

### 4.2 Политика доступа

```yaml
# access_control_policy.yaml
policy_id: access-control-001
name: Контроль доступа агентов
description: Контролирует доступ агентов к ресурсам
type: access
version: "1.0"

rules:
  - rule_id: admin-tools-restricted
    description: Admin инструменты требуют роль admin
    conditions:
      - field: request.tool_category
        operator: eq
        value: "admin"
      - field: agent.role
        operator: ne
        value: "admin"
    effect: deny
    priority: 100
    message: "Admin инструменты требуют роль admin"

  - rule_id: external-network-approval
    description: Внешний сетевой доступ требует одобрения
    conditions:
      - field: request.tool
        operator: in
        value: ["http_request", "api_call", "send_email"]
      - field: request.target
        operator: matches
        value: "^https?://(?!internal\\.).*"
    effect: require_approval
    priority: 80
    message: "Внешний сетевой доступ требует одобрения"

  - rule_id: rate-limit-exceeded
    description: Блокировать при превышении rate limit
    conditions:
      - field: agent.requests_per_minute
        operator: gt
        value: 100
    effect: deny
    priority: 95
    message: "Превышен rate limit"
    actions:
      - throttle_agent

enforcement_points:
  - pre_request

target_systems:
  - "*"
target_agents:
  - "*"

enabled: true
```

### 4.3 Поведенческая политика

```yaml
# behavior_policy.yaml
policy_id: behavior-001
name: Поведенческая политика агентов
description: Контролирует паттерны поведения агентов
type: behavior
version: "1.0"

rules:
  - rule_id: unusual-tool-sequence
    description: Блокировать необычные последовательности инструментов
    conditions:
      - field: session.tool_sequence_anomaly_score
        operator: gt
        value: 0.8
    effect: require_approval
    priority: 85
    message: "Обнаружена необычная последовательность инструментов"
    actions:
      - alert_security

  - rule_id: excessive-data-access
    description: Блокировать избыточный доступ к данным
    conditions:
      - field: session.data_accessed_mb
        operator: gt
        value: 50
    effect: deny
    priority: 90
    message: "Избыточный доступ к данным заблокирован"
    actions:
      - terminate_session
      - log_data_exfil_attempt

  - rule_id: suspicious-timing
    description: Флаг подозрительных тайминговых паттернов
    conditions:
      - field: session.avg_action_interval_ms
        operator: lt
        value: 100
    effect: audit
    priority: 60
    message: "Подозрительный тайминговый паттерн"
    actions:
      - log_timing_anomaly

enforcement_points:
  - mid_processing

enabled: true
```

---

## 5. Жизненный цикл политик

### 5.1 Менеджер политик

```rust
use std::collections::HashMap;
use chrono::Utc;

/// Управляет жизненным циклом политик
struct PolicyManager {
    store: Box<dyn PolicyStore>,
    parser: PolicyParser,
    version_history: HashMap<String, Vec<PolicyVersion>>,
}

impl PolicyManager {
    fn new(store: Box<dyn PolicyStore>) -> Self {
        Self {
            store,
            parser: PolicyParser::new(),
            version_history: HashMap::new(),
        }
    }

    /// Создать новую политику из YAML
    fn create_policy(&mut self, yaml_content: &str, author: &str) -> Policy {
        let mut policy = self.parser.parse_yaml(yaml_content);
        policy.author = author.into();
        policy.created_at = Utc::now();
        policy.updated_at = Utc::now();

        self.store.add(policy.clone());
        self.record_version(&policy, author, "Первоначальное создание");

        policy
    }

    /// Обновить существующую политику
    fn update_policy(&mut self, policy_id: &str, yaml_content: &str,
                     author: &str, change_description: &str) -> Result<Policy, String> {
        let existing = self.store.get(policy_id)
            .ok_or_else(|| format!("Политика {} не найдена", policy_id))?;

        let mut new_policy = self.parser.parse_yaml(yaml_content);
        new_policy.policy_id = policy_id.into(); // Сохранить тот же ID
        new_policy.created_at = existing.created_at;
        new_policy.updated_at = Utc::now();
        new_policy.version = Self::increment_version(&existing.version);

        self.store.add(new_policy.clone());
        self.record_version(&new_policy, author, change_description);

        Ok(new_policy)
    }

    /// Включить политику
    fn enable_policy(&self, policy_id: &str) {
        if let Some(mut policy) = self.store.get(policy_id) {
            policy.enabled = true;
            policy.updated_at = Utc::now();
            self.store.add(policy);
        }
    }

    /// Отключить политику
    fn disable_policy(&self, policy_id: &str) {
        if let Some(mut policy) = self.store.get(policy_id) {
            policy.enabled = false;
            policy.updated_at = Utc::now();
            self.store.add(policy);
        }
    }

    /// Получить историю версий политики
    fn get_version_history(&self, policy_id: &str) -> Vec<PolicyVersion> {
        self.version_history.get(policy_id).cloned().unwrap_or_default()
    }

    fn record_version(&mut self, policy: &Policy, author: &str, description: &str) {
        self.version_history
            .entry(policy.policy_id.clone())
            .or_default()
            .push(PolicyVersion {
                version: policy.version.clone(),
                author: author.into(),
                description: description.into(),
                timestamp: Utc::now(),
            });
    }

    fn increment_version(version: &str) -> String {
        let parts: Vec<&str> = version.split('.').collect();
        if parts.len() == 2 {
            let minor: u32 = parts[1].parse().unwrap_or(0);
            format!("{}.{}", parts[0], minor + 1)
        } else {
            format!("{}.1", version)
        }
    }
}
```

---

## 6. Интеграция с SENTINEL

```rust
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use serde_json::Value;

/// Конфигурация движка политик
struct PolicyConfig {
    default_effect: PolicyEffect,
    enable_audit: bool,
    policy_directory: String,
}

impl Default for PolicyConfig {
    fn default() -> Self {
        Self {
            default_effect: PolicyEffect::Deny,
            enable_audit: true,
            policy_directory: "./policies".into(),
        }
    }
}

/// Движок политик для фреймворка SENTINEL
struct SENTINELPolicyEngine {
    config: PolicyConfig,
    store: InMemoryPolicyStore,
    evaluator: PolicyEvaluator,
    manager: PolicyManager,
}

impl SENTINELPolicyEngine {
    fn new(config: PolicyConfig) -> Self {
        let store = InMemoryPolicyStore::new();
        let evaluator = PolicyEvaluator::new(Box::new(store.clone()));
        let manager = PolicyManager::new(Box::new(store.clone()));
        Self { config, store, evaluator, manager }
    }

    /// Загрузить все политики из директории
    fn load_policies_from_directory(&mut self, directory: Option<&str>) {
        let dir_path = directory
            .unwrap_or(&self.config.policy_directory);

        let path = Path::new(dir_path);
        if !path.exists() {
            return;
        }

        if let Ok(entries) = fs::read_dir(path) {
            for entry in entries.flatten() {
                let file_path = entry.path();
                if let Some(ext) = file_path.extension() {
                    if ext == "yaml" || ext == "yml" {
                        if let Ok(content) = fs::read_to_string(&file_path) {
                            self.manager.create_policy(&content, "system");
                        }
                    }
                }
            }
        }
    }

    /// Оценить политики
    fn evaluate(&self, context: &HashMap<String, Value>,
                system_id: &str, agent_id: &str,
                enforcement_point: &str) -> PolicyDecision {
        let ep = match enforcement_point {
            "pre_request" => EnforcementPoint::PreRequest,
            "mid_processing" => EnforcementPoint::MidProcessing,
            "post_response" => EnforcementPoint::PostResponse,
            _ => EnforcementPoint::Always,
        };
        self.evaluator.evaluate(context, system_id, agent_id, &ep)
    }

    /// Добавить новую политику
    fn add_policy(&mut self, yaml_content: &str, author: &str) -> String {
        let policy = self.manager.create_policy(yaml_content, author);
        policy.policy_id
    }

    /// Получить политику по ID
    fn get_policy(&self, policy_id: &str) -> Option<Policy> {
        self.store.get(policy_id)
    }

    /// Список всех политик
    fn list_policies(&self) -> Vec<HashMap<String, Value>> {
        self.store.list_all().iter().map(|p| {
            let mut m = HashMap::new();
            m.insert("policy_id".into(), json!(p.policy_id));
            m.insert("name".into(), json!(p.name));
            m.insert("type".into(), json!(format!("{:?}", p.policy_type)));
            m.insert("enabled".into(), json!(p.enabled));
            m.insert("rules_count".into(), json!(p.rules.len()));
            m
        }).collect()
    }
}
```

---

## 7. Итоги

### Типы политик

| Тип | Назначение | Примеры правил |
|-----|------------|----------------|
| **Access** | Контроль доступа | Роли, rate limits |
| **Content** | Валидация контента | PII, токсичность |
| **Behavior** | Паттерны поведения | Аномалии, timing |
| **Compliance** | Регуляторные | GDPR, HIPAA |

### Чек-лист

```
□ Определить типы политик для системы
□ Создать политики в YAML/JSON
□ Настроить точки применения
□ Реализовать кастомные условия
□ Настроить действия on_fail
□ Включить аудит
□ Управлять версиями политик
□ Мониторить эффективность
```

---

## Следующий урок

→ [Compliance Mapping](02-compliance-mapping.md)

---

*AI Security Academy | Трек 07: Governance | Политики*
