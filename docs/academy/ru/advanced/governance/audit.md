# Audit Trail для AI систем

> **Уровень:** Продвинутый  
> **Время:** 45 минут  
> **Трек:** 07 — Governance  
> **Модуль:** 07.2 — Audit  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять требования к AI audit trail
- [ ] Реализовать комплексное audit логирование
- [ ] Построить возможности audit query и анализа
- [ ] Интегрировать audit trail в SENTINEL

---

## 1. Обзор Audit Trail

### 1.1 Зачем Audit Trail для AI?

```
┌────────────────────────────────────────────────────────────────────┐
│              ТРЕБОВАНИЯ К AI AUDIT TRAIL                           │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Регуляторные требования:                                          │
│  ├── EU AI Act: Хранить логи для high-risk систем                 │
│  ├── SOC 2: Демонстрировать эффективность контролей              │
│  └── GDPR: Записывать активности обработки данных                 │
│                                                                    │
│  Требования безопасности:                                          │
│  ├── Incident Investigation: Что произошло и когда               │
│  ├── Attack Detection: Pattern analysis по логам                  │
│  └── Forensics: Доказательства для security incidents             │
│                                                                    │
│  Операционные требования:                                          │
│  ├── Debugging: Трассировка issues до root cause                  │
│  ├── Performance: Идентификация bottlenecks                       │
│  └── Usage Analytics: Понимание использования системы             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Модель Audit Event

### 2.1 Основные сущности

```rust
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use serde::{Serialize, Deserialize};
use serde_json;
use sha2::{Sha256, Digest};

// Request/Response события
// Security события
// System события
// Agent события
// Approval события
#[derive(Clone, Debug, Serialize, Deserialize)]
enum AuditEventType {
    RequestReceived,
    ResponseGenerated,
    SecurityViolation,
    AccessDenied,
    AttackDetected,
    PolicyViolation,
    ToolInvoked,
    DataAccessed,
    ConfigChanged,
    AgentCreated,
    AgentPermissionChanged,
    AgentTerminated,
    ApprovalRequested,
    ApprovalGranted,
    ApprovalDenied,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
enum AuditSeverity {
    Debug,
    Info,
    Warning,
    Error,
    Critical,
}

/// Полное audit событие
#[derive(Clone, Debug, Serialize)]
struct AuditEvent {
    event_id: String,
    timestamp: DateTime<Utc>,
    event_type: AuditEventType,
    severity: AuditSeverity,

    // Контекст
    session_id: String,
    user_id: String,
    agent_id: String,
    system_id: String,

    // Детали события
    action: String,
    resource: String,
    outcome: String, // success, failure, blocked

    // Rich data
    request_data: HashMap<String, serde_json::Value>,
    response_data: HashMap<String, serde_json::Value>,
    metadata: HashMap<String, serde_json::Value>,

    // Tracing
    trace_id: String,
    parent_event_id: String,

    // Integrity
    event_hash: String,
    previous_hash: String,
}

impl AuditEvent {
    fn new(
        event_id: String, timestamp: DateTime<Utc>,
        event_type: AuditEventType, severity: AuditSeverity,
        session_id: String, user_id: String,
        agent_id: String, system_id: String,
        action: String, resource: String, outcome: String,
    ) -> Self {
        let mut event = Self {
            event_id, timestamp, event_type, severity,
            session_id, user_id, agent_id, system_id,
            action, resource, outcome,
            request_data: HashMap::new(),
            response_data: HashMap::new(),
            metadata: HashMap::new(),
            trace_id: String::new(),
            parent_event_id: String::new(),
            event_hash: String::new(),
            previous_hash: String::new(),
        };
        event.event_hash = event.compute_hash();
        event
    }

    /// Вычислить hash для верификации integrity
    fn compute_hash(&self) -> String {
        let data = serde_json::json!({
            "event_id": self.event_id,
            "timestamp": self.timestamp.to_rfc3339(),
            "event_type": format!("{:?}", self.event_type),
            "action": self.action,
            "resource": self.resource,
            "outcome": self.outcome,
            "previous_hash": self.previous_hash,
        });
        let content = serde_json::to_string(&data).unwrap();
        let hash = Sha256::digest(content.as_bytes());
        format!("{:x}", hash)
    }

    /// Проверить что событие не было изменено
    fn verify_integrity(&self) -> bool {
        self.event_hash == self.compute_hash()
    }

    fn to_map(&self) -> HashMap<String, serde_json::Value> {
        let mut m = HashMap::new();
        m.insert("event_id".into(), json!(self.event_id));
        m.insert("timestamp".into(), json!(self.timestamp.to_rfc3339()));
        m.insert("event_type".into(), json!(format!("{:?}", self.event_type)));
        m.insert("severity".into(), json!(format!("{:?}", self.severity)));
        m.insert("session_id".into(), json!(self.session_id));
        m.insert("user_id".into(), json!(self.user_id));
        m.insert("agent_id".into(), json!(self.agent_id));
        m.insert("action".into(), json!(self.action));
        m.insert("resource".into(), json!(self.resource));
        m.insert("outcome".into(), json!(self.outcome));
        m.insert("event_hash".into(), json!(self.event_hash));
        m
    }
}

/// Цепочка audit событий с верификацией integrity
struct AuditChain {
    chain_id: String,
    events: Vec<AuditEvent>,
}

impl AuditChain {
    fn new(chain_id: String) -> Self {
        Self { chain_id, events: Vec::new() }
    }

    /// Добавить событие в цепочку с hash linking
    fn add_event(&mut self, mut event: AuditEvent) {
        if let Some(last) = self.events.last() {
            event.previous_hash = last.event_hash.clone();
            event.event_hash = event.compute_hash();
        }
        self.events.push(event);
    }

    /// Верифицировать integrity всей цепочки
    fn verify_chain(&self) -> bool {
        for (i, event) in self.events.iter().enumerate() {
            if !event.verify_integrity() {
                return false;
            }
            if i > 0 && event.previous_hash != self.events[i - 1].event_hash {
                return false;
            }
        }
        true
    }
}
```

---

## 3. Audit Logger

### 3.1 Реализация Logger

```rust
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::sync::mpsc;
use uuid::Uuid;

/// Абстрактный audit storage backend
trait AuditBackend: Send + Sync {
    fn write(&self, event: AuditEvent);
    fn query(&self, filters: &HashMap<String, String>) -> Vec<AuditEvent>;
}

/// In-memory backend для разработки
struct InMemoryAuditBackend {
    events: RwLock<Vec<AuditEvent>>,
    max_events: usize,
    // Индексы
    by_session: RwLock<HashMap<String, Vec<usize>>>,
    by_user: RwLock<HashMap<String, Vec<usize>>>,
    by_type: RwLock<HashMap<String, Vec<usize>>>,
}

impl InMemoryAuditBackend {
    fn new(max_events: usize) -> Self {
        Self {
            events: RwLock::new(Vec::new()),
            max_events,
            by_session: RwLock::new(HashMap::new()),
            by_user: RwLock::new(HashMap::new()),
            by_type: RwLock::new(HashMap::new()),
        }
    }
}

impl AuditBackend for InMemoryAuditBackend {
    fn write(&self, event: AuditEvent) {
        let mut events = self.events.write().unwrap();
        let idx = events.len();

        // Обновить индексы
        self.by_session.write().unwrap()
            .entry(event.session_id.clone()).or_default().push(idx);
        self.by_user.write().unwrap()
            .entry(event.user_id.clone()).or_default().push(idx);
        self.by_type.write().unwrap()
            .entry(format!("{:?}", event.event_type)).or_default().push(idx);

        events.push(event);

        // Trim при необходимости
        if events.len() > self.max_events {
            events.drain(0..events.len() / 4);
        }
    }

    fn query(&self, filters: &HashMap<String, String>) -> Vec<AuditEvent> {
        let events = self.events.read().unwrap();
        let mut candidates: Option<Vec<usize>> = None;

        // Использовать индексы если доступны
        if let Some(sid) = filters.get("session_id") {
            let by_session = self.by_session.read().unwrap();
            let indices = by_session.get(sid).cloned().unwrap_or_default();
            candidates = Some(indices);
        }
        if let Some(uid) = filters.get("user_id") {
            let by_user = self.by_user.read().unwrap();
            let indices = by_user.get(uid).cloned().unwrap_or_default();
            candidates = Some(match candidates {
                Some(c) => c.into_iter()
                    .filter(|i| indices.contains(i)).collect(),
                None => indices,
            });
        }
        if let Some(et) = filters.get("event_type") {
            let by_type = self.by_type.read().unwrap();
            let indices = by_type.get(et).cloned().unwrap_or_default();
            candidates = Some(match candidates {
                Some(c) => c.into_iter()
                    .filter(|i| indices.contains(i)).collect(),
                None => indices,
            });
        }

        // Если индекс не использован, сканировать все
        let indices = candidates
            .unwrap_or_else(|| (0..events.len()).collect());

        let limit: usize = filters.get("limit")
            .and_then(|l| l.parse().ok()).unwrap_or(usize::MAX);

        indices.into_iter().rev()
            .filter_map(|idx| events.get(idx).cloned())
            .take(limit)
            .collect()
    }
}

/// Главный audit logger
struct AuditLogger {
    backend: Arc<dyn AuditBackend>,
    chain: RwLock<AuditChain>,
    sender: Option<mpsc::Sender<AuditEvent>>,
}

impl AuditLogger {
    fn new(backend: Arc<dyn AuditBackend>, async_mode: bool) -> Self {
        let chain = RwLock::new(AuditChain::new(Uuid::new_v4().to_string()));
        let sender = if async_mode {
            let (tx, rx) = mpsc::channel::<AuditEvent>();
            let be = backend.clone();
            std::thread::spawn(move || {
                for event in rx {
                    be.write(event);
                }
            });
            Some(tx)
        } else {
            None
        };
        Self { backend, chain, sender }
    }

    /// Логировать audit событие
    fn log(
        &self, event_type: AuditEventType, severity: AuditSeverity,
        session_id: &str, user_id: &str, agent_id: &str,
        action: &str, resource: &str, outcome: &str,
        request_data: Option<HashMap<String, serde_json::Value>>,
        response_data: Option<HashMap<String, serde_json::Value>>,
        metadata: Option<HashMap<String, serde_json::Value>>,
        system_id: &str,
    ) -> String {
        let mut event = AuditEvent::new(
            Uuid::new_v4().to_string(), Utc::now(),
            event_type, severity,
            session_id.into(), user_id.into(),
            agent_id.into(), system_id.into(),
            action.into(), resource.into(), outcome.into(),
        );
        event.request_data = request_data.unwrap_or_default();
        event.response_data = response_data.unwrap_or_default();
        event.metadata = metadata.unwrap_or_default();

        let event_id = event.event_id.clone();

        if let Some(ref sender) = self.sender {
            if sender.send(event.clone()).is_err() {
                self.chain.write().unwrap().add_event(event.clone());
                self.backend.write(event);
            }
        } else {
            self.chain.write().unwrap().add_event(event.clone());
            self.backend.write(event);
        }

        event_id
    }

    // Convenience методы
    fn log_request(&self, session_id: &str, user_id: &str,
                   agent_id: &str, request_data: HashMap<String, serde_json::Value>) -> String {
        self.log(
            AuditEventType::RequestReceived, AuditSeverity::Info,
            session_id, user_id, agent_id,
            "process_request", "input", "received",
            Some(request_data), None, None, "default",
        )
    }

    fn log_security_violation(&self, session_id: &str, user_id: &str,
                              agent_id: &str, violation_type: &str,
                              details: HashMap<String, serde_json::Value>) -> String {
        self.log(
            AuditEventType::SecurityViolation, AuditSeverity::Warning,
            session_id, user_id, agent_id,
            violation_type, "security", "blocked",
            None, None, Some(details), "default",
        )
    }

    fn log_attack_detected(&self, session_id: &str, user_id: &str,
                           agent_id: &str, attack_type: &str,
                           confidence: f64,
                           mut details: HashMap<String, serde_json::Value>) -> String {
        details.insert("confidence".into(), serde_json::json!(confidence));
        self.log(
            AuditEventType::AttackDetected, AuditSeverity::Critical,
            session_id, user_id, agent_id,
            attack_type, "security", "detected",
            None, None, Some(details), "default",
        )
    }

    fn query(&self, filters: &HashMap<String, String>) -> Vec<AuditEvent> {
        self.backend.query(filters)
    }

    fn verify_chain_integrity(&self) -> bool {
        self.chain.read().unwrap().verify_chain()
    }
}
```

---

## 4. Audit Analysis

### 4.1 Audit Analyzer

```rust
use std::collections::HashMap;

/// Анализ audit логов для insights
struct AuditAnalyzer {
    logger: Arc<AuditLogger>,
}

impl AuditAnalyzer {
    fn new(logger: Arc<AuditLogger>) -> Self {
        Self { logger }
    }

    /// Получить сводку security событий
    fn get_security_summary(&self, hours: i64) -> HashMap<String, serde_json::Value> {
        let start = Utc::now() - chrono::Duration::hours(hours);

        let security_types = vec![
            "AttackDetected", "SecurityViolation",
            "AccessDenied", "PolicyViolation",
        ];

        let mut events: Vec<AuditEvent> = Vec::new();
        for event_type in &security_types {
            let mut filters = HashMap::new();
            filters.insert("event_type".into(), event_type.to_string());
            events.extend(self.logger.query(&filters));
        }

        // Агрегация
        let mut by_type: HashMap<String, usize> = HashMap::new();
        let mut by_severity: HashMap<String, usize> = HashMap::new();
        let mut by_agent: HashMap<String, usize> = HashMap::new();
        let mut by_user: HashMap<String, usize> = HashMap::new();

        for e in &events {
            *by_type.entry(format!("{:?}", e.event_type)).or_insert(0) += 1;
            *by_severity.entry(format!("{:?}", e.severity)).or_insert(0) += 1;
            *by_agent.entry(e.agent_id.clone()).or_insert(0) += 1;
            *by_user.entry(e.user_id.clone()).or_insert(0) += 1;
        }

        let mut result = HashMap::new();
        result.insert("total_events".into(), json!(events.len()));
        result.insert("by_type".into(), json!(by_type));
        result.insert("by_severity".into(), json!(by_severity));
        result.insert("top_agents".into(), json!(by_agent));
        result.insert("top_users".into(), json!(by_user));
        result.insert("period_hours".into(), json!(hours));
        result
    }

    /// Детекция аномалий в сессии
    fn detect_anomalies(&self, session_id: &str) -> Vec<HashMap<String, serde_json::Value>> {
        let mut filters = HashMap::new();
        filters.insert("session_id".into(), session_id.to_string());
        let events = self.logger.query(&filters);

        let mut anomalies = Vec::new();

        // Проверка rapid requests
        if events.len() > 1 {
            let times: Vec<DateTime<Utc>> = events.iter().map(|e| e.timestamp).collect();
            let has_rapid = times.windows(2)
                .any(|w| (w[1] - w[0]).num_milliseconds() < 100);

            if has_rapid {
                let mut a = HashMap::new();
                a.insert("type".into(), json!("rapid_requests"));
                a.insert("severity".into(), json!("medium"));
                a.insert("description".into(),
                    json!("Обнаружен необычно высокий rate запросов"));
                anomalies.push(a);
            }
        }

        // Проверка many failures
        let failures: Vec<&AuditEvent> = events.iter()
            .filter(|e| e.outcome == "failure").collect();
        if failures.len() > events.len() / 2 {
            let mut a = HashMap::new();
            a.insert("type".into(), json!("high_failure_rate"));
            a.insert("severity".into(), json!("high"));
            a.insert("description".into(),
                json!(format!("{} failures из {} событий", failures.len(), events.len())));
            anomalies.push(a);
        }

        // Проверка security events
        let security_events: Vec<&AuditEvent> = events.iter()
            .filter(|e| matches!(e.event_type,
                AuditEventType::SecurityViolation |
                AuditEventType::AccessDenied |
                AuditEventType::AttackDetected))
            .collect();
        if !security_events.is_empty() {
            let mut a = HashMap::new();
            a.insert("type".into(), json!("security_events"));
            a.insert("severity".into(), json!("critical"));
            a.insert("description".into(),
                json!(format!("{} security событий в сессии", security_events.len())));
            a.insert("events".into(),
                json!(security_events.iter().map(|e| e.event_id.clone()).collect::<Vec<_>>()));
            anomalies.push(a);
        }

        anomalies
    }

    /// Сгенерировать полный отчёт сессии
    fn generate_session_report(&self, session_id: &str) -> HashMap<String, serde_json::Value> {
        let mut filters = HashMap::new();
        filters.insert("session_id".into(), session_id.to_string());
        let mut events = self.logger.query(&filters);

        if events.is_empty() {
            let mut r = HashMap::new();
            r.insert("session_id".into(), json!(session_id));
            r.insert("status".into(), json!("not_found"));
            return r;
        }

        events.sort_by_key(|e| e.timestamp);

        let mut event_types: HashMap<String, usize> = HashMap::new();
        let mut outcomes: HashMap<String, usize> = HashMap::new();
        let mut agents: Vec<String> = Vec::new();

        for e in &events {
            *event_types.entry(format!("{:?}", e.event_type)).or_insert(0) += 1;
            *outcomes.entry(e.outcome.clone()).or_insert(0) += 1;
            if !agents.contains(&e.agent_id) {
                agents.push(e.agent_id.clone());
            }
        }

        let duration = (events.last().unwrap().timestamp
            - events.first().unwrap().timestamp).num_seconds();

        let mut r = HashMap::new();
        r.insert("session_id".into(), json!(session_id));
        r.insert("start_time".into(), json!(events.first().unwrap().timestamp.to_rfc3339()));
        r.insert("end_time".into(), json!(events.last().unwrap().timestamp.to_rfc3339()));
        r.insert("duration_seconds".into(), json!(duration));
        r.insert("total_events".into(), json!(events.len()));
        r.insert("event_types".into(), json!(event_types));
        r.insert("outcomes".into(), json!(outcomes));
        r.insert("agents_involved".into(), json!(agents));
        r.insert("anomalies".into(), json!(self.detect_anomalies(session_id)));
        r
    }
}
```

---

## 5. Интеграция с SENTINEL

```rust
use std::sync::Arc;

/// Конфигурация audit engine
struct AuditConfig {
    async_mode: bool,
    max_events: usize,
    retention_days: u32,
    enable_integrity_check: bool,
}

impl Default for AuditConfig {
    fn default() -> Self {
        Self {
            async_mode: true,
            max_events: 100_000,
            retention_days: 90,
            enable_integrity_check: true,
        }
    }
}

/// Audit engine для SENTINEL framework
struct SENTINELAuditEngine {
    config: AuditConfig,
    backend: Arc<InMemoryAuditBackend>,
    logger: Arc<AuditLogger>,
    analyzer: AuditAnalyzer,
}

impl SENTINELAuditEngine {
    fn new(config: AuditConfig) -> Self {
        let backend = Arc::new(InMemoryAuditBackend::new(config.max_events));
        let logger = Arc::new(AuditLogger::new(backend.clone(), config.async_mode));
        let analyzer = AuditAnalyzer::new(logger.clone());
        Self { config, backend, logger, analyzer }
    }

    fn log_request(&self, session_id: &str, user_id: &str,
                   agent_id: &str, request: HashMap<String, serde_json::Value>) -> String {
        self.logger.log_request(session_id, user_id, agent_id, request)
    }

    fn log_response(&self, session_id: &str, user_id: &str,
                    agent_id: &str, response: HashMap<String, serde_json::Value>,
                    outcome: &str) -> String {
        self.logger.log(
            AuditEventType::ResponseGenerated, AuditSeverity::Info,
            session_id, user_id, agent_id,
            "generate_response", "output", outcome,
            None, Some(response), None, "default",
        )
    }

    fn log_attack(&self, session_id: &str, user_id: &str,
                  agent_id: &str, attack_type: &str,
                  confidence: f64, details: HashMap<String, serde_json::Value>) -> String {
        self.logger.log_attack_detected(
            session_id, user_id, agent_id,
            attack_type, confidence, details,
        )
    }

    fn get_security_summary(&self, hours: i64) -> HashMap<String, serde_json::Value> {
        self.analyzer.get_security_summary(hours)
    }

    fn get_session_report(&self, session_id: &str) -> HashMap<String, serde_json::Value> {
        self.analyzer.generate_session_report(session_id)
    }

    fn verify_integrity(&self) -> bool {
        if !self.config.enable_integrity_check {
            return true;
        }
        self.logger.verify_chain_integrity()
    }
}
```

---

## 6. Итоги

| Компонент | Описание |
|-----------|----------|
| **AuditEvent** | Единица audit лога с hash |
| **AuditChain** | Цепочка событий с integrity |
| **Backend** | Storage (in-memory, DB) |
| **Logger** | Async логирование с convenience методами |
| **Analyzer** | Security summary, anomaly detection |

---

## Следующий урок

→ [Трек 08: Research](../../08-research/README.md)

---

*AI Security Academy | Трек 07: Governance | Модуль 07.2: Audit*
