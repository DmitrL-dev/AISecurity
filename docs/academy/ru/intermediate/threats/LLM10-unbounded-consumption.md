# LLM10: Неограниченное потребление

> **Урок:** 02.1.10 - Неограниченное потребление  
> **OWASP ID:** LLM10  
> **Время:** 30 минут  
> **Уровень риска:** Низкий-Средний

---

## Цели обучения

К концу этого урока вы сможете:

1. Идентифицировать паттерны атак на исчерпание ресурсов
2. Внедрять ограничение скорости и квоты
3. Проектировать cost-aware LLM-архитектуры
4. Мониторить и настраивать алерты на аномалии потребления

---

## Что такое неограниченное потребление?

Операции LLM вычислительно дороги. Неограниченное потребление возникает, когда атакующие эксплуатируют это для:

| Тип атаки | Цель | Последствия |
|-----------|------|-------------|
| **Флуд токенов** | Стоимость API | Финансовые потери |
| **Бомбардировка промптами** | Вычислительные ресурсы | Деградация сервиса |
| **Долгоработающие агенты** | Время/память | Исчерпание ресурсов |
| **Рекурсивные запросы** | API-вызовы | Взрыв стоимости |
| **Набивка контекста** | Память | OOM-краши |

---

## Паттерны атак

### 1. Взрыв стоимости токенов

```rust
// Атакующий отправляет промпты, максимизирующие выходные токены
let expensive_prompt = r#"
Напиши крайне детальный, всеобъемлющий, исчерпывающий анализ
всей истории вычислений с 1800 года до сегодняшнего дня.
Включи каждую значимую фигуру, изобретение, компанию и разработку.
Оформи как академическую статью на 50,000 слов с полными цитатами.
"#;

// При $0.02 за 1K выходных токенов:
// 50,000 слов ≈ 65,000 токенов ≈ $1.30 за запрос
// 1,000 запросов/час = $1,300/час

let response = llm.generate(expensive_prompt, 65000);
```

### 2. Рекурсивный цикл агента

```rust
// Вредоносный промпт вызывает бесконечный цикл агента
let attack_prompt = r#"
Ты исследовательский ассистент. Для каждой темы, которую исследуешь:
1. Найди 3 связанные темы
2. Исследуй каждую из этих 3 тем тем же способом
3. Продолжай пока не получишь полную информацию

Тема исследования: "Всё о науке"
"#;

// Без ограничений:
// Глубина 1: 3 темы
// Глубина 2: 9 тем  
// Глубина 3: 27 тем
// Глубина 4: 81 тема = 120 API-вызовов
// Глубина 10: 88,573 API-вызова!
```

### 3. Набивка контекстного окна

```rust
// Атакующий заполняет контекст дорогой обработкой
let context_bomb = "A".repeat(100000); // Заполнить контекстное окно

let response = llm.generate(
    &format!("{}\n\nСуммаризируй вышесказанное и переведи на 10 языков", context_bomb)
);

// Принуждает обработку огромного контекста + большой вывод
```

### 4. Пакетное усиление

```rust
// Один запрос, запускающий много LLM-вызовов
let amplification_prompt = format!(r#"
Проанализируй каждый из этих 1000 URL и предоставь детальные отчёты:
{}

Для каждого URL:
1. Суммаризируй контент (требует загрузки + LLM-вызов)
2. Извлеки ключевые сущности (LLM-вызов)  
3. Анализ тональности (LLM-вызов)
4. Сгенерируй action items (LLM-вызов)
"#, list_of_1000_urls);

// 1 пользовательский запрос = 4,000+ LLM API-вызовов
```

---

## Стратегии защиты

### 1. Управление бюджетом токенов

```rust
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, SystemTime};

struct TokenBudget {
    user_id: String,
    daily_limit: usize,
    hourly_limit: usize,
    per_request_limit: usize,
    used_today: usize,
    used_this_hour: usize,
    last_reset_daily: SystemTime,
    last_reset_hourly: SystemTime,
}

struct TokenBudgetManager {
    /// Управление бюджетами потребления токенов по пользователям.
    budgets: Mutex<HashMap<String, TokenBudget>>,
}

struct TierLimits {
    daily: usize,
    hourly: usize,
    per_request: usize,
}

impl TokenBudgetManager {
    fn default_limits(tier: &str) -> TierLimits {
        match tier {
            "pro" => TierLimits { daily: 100_000, hourly: 20_000, per_request: 4_000 },
            "enterprise" => TierLimits { daily: 1_000_000, hourly: 100_000, per_request: 32_000 },
            _ => TierLimits { daily: 10_000, hourly: 2_000, per_request: 1_000 }, // free
        }
    }

    fn new() -> Self {
        Self { budgets: Mutex::new(HashMap::new()) }
    }

    /// Получить или создать бюджет токенов для пользователя.
    fn get_budget(&self, user_id: &str, tier: &str) -> TokenBudget {
        let mut budgets = self.budgets.lock().unwrap();
        if !budgets.contains_key(user_id) {
            let limits = Self::default_limits(tier);
            budgets.insert(user_id.to_string(), TokenBudget {
                user_id: user_id.to_string(),
                daily_limit: limits.daily,
                hourly_limit: limits.hourly,
                per_request_limit: limits.per_request,
                used_today: 0,
                used_this_hour: 0,
                last_reset_daily: SystemTime::now(),
                last_reset_hourly: SystemTime::now(),
            });
        }

        let budget = budgets.get_mut(user_id).unwrap();
        Self::check_reset(budget);
        // Возвращаем копию данных
        TokenBudget {
            user_id: budget.user_id.clone(),
            daily_limit: budget.daily_limit,
            hourly_limit: budget.hourly_limit,
            per_request_limit: budget.per_request_limit,
            used_today: budget.used_today,
            used_this_hour: budget.used_this_hour,
            last_reset_daily: budget.last_reset_daily,
            last_reset_hourly: budget.last_reset_hourly,
        }
    }

    /// Сброс счётчиков при истечении временного окна.
    fn check_reset(budget: &mut TokenBudget) {
        let now = SystemTime::now();

        if now.duration_since(budget.last_reset_daily).unwrap_or_default() > Duration::from_secs(86400) {
            budget.used_today = 0;
            budget.last_reset_daily = now;
        }

        if now.duration_since(budget.last_reset_hourly).unwrap_or_default() > Duration::from_secs(3600) {
            budget.used_this_hour = 0;
            budget.last_reset_hourly = now;
        }
    }

    /// Проверить, укладывается ли запрос в бюджет, и потребить токены.
    fn check_and_consume(
        &self,
        user_id: &str,
        estimated_tokens: usize,
        tier: &str,
    ) -> serde_json::Value {
        let mut budgets = self.budgets.lock().unwrap();
        let budget = budgets.get_mut(user_id).unwrap_or_else(|| {
            panic!("Call get_budget first");
        });
        Self::check_reset(budget);

        // Проверка лимита на запрос
        if estimated_tokens > budget.per_request_limit {
            return serde_json::json!({
                "allowed": false,
                "reason": format!("Запрос превышает лимит на запрос ({})", budget.per_request_limit),
                "limit_type": "per_request"
            });
        }

        // Проверка часового лимита
        if budget.used_this_hour + estimated_tokens > budget.hourly_limit {
            return serde_json::json!({
                "allowed": false,
                "reason": "Часовой лимит превышен",
                "remaining": budget.hourly_limit - budget.used_this_hour
            });
        }

        // Проверка дневного лимита
        if budget.used_today + estimated_tokens > budget.daily_limit {
            return serde_json::json!({
                "allowed": false,
                "reason": "Дневной лимит превышен",
                "remaining": budget.daily_limit - budget.used_today
            });
        }

        // Потребление токенов
        budget.used_this_hour += estimated_tokens;
        budget.used_today += estimated_tokens;

        serde_json::json!({"allowed": true, "tokens_used": estimated_tokens})
    }
}
```

---

### 2. Анализ сложности запроса

```rust
use regex::Regex;
use std::collections::HashMap;

struct RequestComplexityAnalyzer {
    /// Анализ и ограничение сложности запроса перед обработкой.
    complexity_weights: HashMap<String, f64>,
}

impl RequestComplexityAnalyzer {
    fn new() -> Self {
        let mut weights = HashMap::new();
        weights.insert("translation".into(), 1.5);
        weights.insert("summarization".into(), 1.2);
        weights.insert("generation".into(), 1.0);
        weights.insert("analysis".into(), 1.3);
        weights.insert("code".into(), 1.4);
        Self { complexity_weights: weights }
    }

    /// Оценка потребления токенов для запроса.
    fn estimate_tokens(&self, prompt: &str, task_type: &str) -> usize {
        // Входные токены
        let input_tokens = prompt.split_whitespace().count() as f64 * 1.3; // Грубая оценка токенов

        // Оценка выхода на основе задачи
        let output_mult = match task_type {
            "summarization" => 0.3,      // Выход меньше входа
            "translation" => 1.0,        // Похожий размер
            "generation" => 2.0,         // Потенциально больше
            "analysis" => 1.5,           // Среднее расширение
            "code" => 2.5,              // Код многословен
            _ => 1.5,
        };

        let estimated_output = input_tokens * output_mult;

        // Применение веса сложности
        let weight = self.complexity_weights.get(task_type).copied().unwrap_or(1.0);

        ((input_tokens + estimated_output) * weight) as usize
    }

    /// Обнаружение промптов, способных вызвать усиление вызовов.
    fn detect_amplification(&self, prompt: &str) -> serde_json::Value {
        let amplification_patterns = vec![
            (r"(?i)(?:для каждого|для всех|анализируй все|обработай каждый)\s+(?:\d+|сотни|тысячи)", "batch_amplification"),
            (r"(?i)(?:рекурсивно|повторно|продолжай пока)", "recursive_loop"),
            (r"(?i)список из \d{2,} (?:элементов|url|тем)", "large_batch"),
            (r"(?i)переведи (?:на|в) (?:\d+|все|каждый) язык", "multi_output"),
        ];

        let mut findings = Vec::new();

        for (pattern, risk_type) in &amplification_patterns {
            let re = Regex::new(pattern).unwrap();
            if re.is_match(prompt) {
                findings.push(risk_type.to_string());
            }
        }

        serde_json::json!({
            "has_amplification_risk": !findings.is_empty(),
            "risks": findings,
            "recommendation": if !findings.is_empty() { Some("Применить строгие лимиты") } else { None }
        })
    }
}
```

---

### 3. Защита от циклов агентов

```rust
use std::collections::HashMap;
use std::time::{Duration, SystemTime};

struct CallRecord {
    time: SystemTime,
    tokens: usize,
}

struct AgentSession {
    iterations: usize,
    depth: i32,
    total_tokens: usize,
    start_time: SystemTime,
    calls: Vec<CallRecord>,
}

struct AgentLoopProtector {
    /// Защита от неконтролируемых циклов агентов.
    max_iterations: usize,
    max_depth: i32,
    current_sessions: HashMap<String, AgentSession>,
}

impl AgentLoopProtector {
    fn new(max_iterations: usize, max_depth: i32) -> Self {
        Self {
            max_iterations,
            max_depth,
            current_sessions: HashMap::new(),
        }
    }

    /// Начать отслеживание новой сессии агента.
    fn start_session(&mut self, session_id: &str) -> &AgentSession {
        self.current_sessions.insert(session_id.to_string(), AgentSession {
            iterations: 0,
            depth: 0,
            total_tokens: 0,
            start_time: SystemTime::now(),
            calls: Vec::new(),
        });
        &self.current_sessions[session_id]
    }

    /// Записать итерацию агента и проверить лимиты.
    fn record_iteration(
        &mut self,
        session_id: &str,
        tokens_used: usize,
        depth_change: i32,
    ) -> serde_json::Value {
        if !self.current_sessions.contains_key(session_id) {
            self.start_session(session_id);
        }

        let session = self.current_sessions.get_mut(session_id).unwrap();
        session.iterations += 1;
        session.depth += depth_change;
        session.total_tokens += tokens_used;
        session.calls.push(CallRecord {
            time: SystemTime::now(),
            tokens: tokens_used,
        });

        // Проверка лимитов
        if session.iterations > self.max_iterations {
            return serde_json::json!({
                "continue": false,
                "reason": format!("Превышено максимум итераций ({})", self.max_iterations)
            });
        }

        if session.depth > self.max_depth {
            return serde_json::json!({
                "continue": false,
                "reason": format!("Превышена максимальная глубина рекурсии ({})", self.max_depth)
            });
        }

        // Проверка на быстрые вызовы (потенциальный цикл)
        if session.calls.len() >= 5 {
            let recent = &session.calls[session.calls.len() - 5..];
            let time_span = recent.last().unwrap().time
                .duration_since(recent.first().unwrap().time)
                .unwrap_or(Duration::ZERO);
            if time_span < Duration::from_secs(2) { // 5 вызовов за 2 секунды = подозрительно
                return serde_json::json!({
                    "continue": false,
                    "reason": "Обнаружена быстрая итерация (потенциальный цикл)"
                });
            }
        }

        serde_json::json!({"continue": true})
    }

    /// Завершить сессию и вернуть сводку.
    fn end_session(&mut self, session_id: &str) -> Option<serde_json::Value> {
        if let Some(session) = self.current_sessions.remove(session_id) {
            let duration = SystemTime::now()
                .duration_since(session.start_time)
                .unwrap_or(Duration::ZERO)
                .as_secs_f64();
            Some(serde_json::json!({
                "total_iterations": session.iterations,
                "max_depth": session.depth,
                "total_tokens": session.total_tokens,
                "duration_seconds": duration,
                "tokens_per_second": session.total_tokens as f64 / duration.max(1.0)
            }))
        } else {
            None
        }
    }
}
```

---

### 4. Ограничение скорости

```rust
use std::collections::HashMap;
use std::time::{Duration, Instant};

struct RateLimits {
    requests_per_minute: usize,
    requests_per_hour: usize,
    tokens_per_minute: usize,
    tokens_per_hour: usize,
}

const LIMITS: RateLimits = RateLimits {
    requests_per_minute: 60,
    requests_per_hour: 1000,
    tokens_per_minute: 40000,
    tokens_per_hour: 500000,
};

struct TokenRecord {
    tokens: usize,
    time: Instant,
}

/// Многоуровневое ограничение скорости для LLM-запросов.
struct MultiLevelRateLimiter {
    request_times: HashMap<String, Vec<Instant>>,
    token_counts: HashMap<String, Vec<TokenRecord>>,
}

impl MultiLevelRateLimiter {
    fn new() -> Self {
        Self {
            request_times: HashMap::new(),
            token_counts: HashMap::new(),
        }
    }

    /// Проверить все лимиты скорости для пользователя.
    fn check_rate_limit(&mut self, user_id: &str, estimated_tokens: usize) -> serde_json::Value {
        let now = Instant::now();

        // Очистка старых записей
        self.clean_old_entries(user_id, now);

        // Проверка частоты запросов
        let requests_last_minute = self
            .request_times
            .get(user_id)
            .map(|times| times.iter().filter(|t| now.duration_since(**t) < Duration::from_secs(60)).count())
            .unwrap_or(0);

        if requests_last_minute >= LIMITS.requests_per_minute {
            return serde_json::json!({
                "allowed": false,
                "reason": "Превышен лимит частоты запросов",
                "retry_after": 60
            });
        }

        // Проверка частоты токенов
        let tokens_last_minute: usize = self
            .token_counts
            .get(user_id)
            .map(|records| {
                records.iter()
                    .filter(|r| now.duration_since(r.time) < Duration::from_secs(60))
                    .map(|r| r.tokens)
                    .sum()
            })
            .unwrap_or(0);

        if tokens_last_minute + estimated_tokens > LIMITS.tokens_per_minute {
            return serde_json::json!({
                "allowed": false,
                "reason": "Превышен лимит частоты токенов",
                "retry_after": 60
            });
        }

        // Запись этого запроса
        self.request_times.entry(user_id.to_string()).or_default().push(now);
        self.token_counts.entry(user_id.to_string()).or_default().push(TokenRecord {
            tokens: estimated_tokens,
            time: now,
        });

        serde_json::json!({"allowed": true})
    }
}
```

---

## Интеграция с SENTINEL

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::builder()
    .cost_protection(true)
    .rate_limiting(true)
    .agent_loop_protection(true)
    .daily_budget(100.00)       // $100/день максимум
    .per_request_max(1.00)      // $1 максимум за запрос
    .alert_threshold(0.8)       // Алерт при 80% бюджета
    .build();

fn llm_request(engine: &SentinelEngine, prompt: &str, user_id: &str) -> String {
    // Автоматически проверяет бюджет и лимиты скорости
    let result = engine.analyze(prompt);
    if result.detected {
        log::warn!("Превышение лимитов для пользователя {}: {:?}", user_id, result.risk_score);
    }
    llm.generate(prompt)
}
```

---

## Ключевые выводы

1. **Бюджетируйте всё** — Токены, запросы, время
2. **Ограничивайте рекурсию** — Предотвращайте неконтролируемых агентов
3. **Анализируйте сложность** — До обработки
4. **Ограничивайте скорость** — На нескольких уровнях
5. **Мониторьте и алертите** — Ловите аномалии рано

---

## Практические упражнения

1. Реализовать менеджер бюджета токенов
2. Построить анализатор сложности
3. Создать защитник от циклов агентов
4. Настроить дашборд мониторинга стоимости

---

*AI Security Academy | Урок 02.1.10*
