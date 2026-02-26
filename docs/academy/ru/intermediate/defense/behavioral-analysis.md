# Поведенческий анализ для AI-систем

> **Уровень:** Продвинутый  
> **Время:** 55 минут  
> **Трек:** 05 — Стратегии защиты  
> **Модуль:** 05.1 — Детекция  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять поведенческий анализ для AI-безопасности
- [ ] Реализовать комплексный мониторинг поведения
- [ ] Построить детекцию аномалий на основе поведения
- [ ] Интегрировать поведенческие сигналы в SENTINEL

---

## 1. Обзор поведенческого анализа

### 1.1 Что такое поведенческий анализ?

**Поведенческий анализ** — мониторинг и анализ паттернов поведения системы для детекции аномалий, не обнаруживаемых статическими методами.

```
┌────────────────────────────────────────────────────────────────────┐
│              ПАЙПЛАЙН ПОВЕДЕНЧЕСКОГО АНАЛИЗА                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  [Действия] → [Логирование  → [Baseline     → [Детекция   → [Алерт]│
│                поведения]     паттернов]     аномалий]            │
│                                                                    │
│  Отслеживаемые поведения:                                          │
│  ├── Поведение инструментов                                        │
│  │   ├── Частота вызовов                                          │
│  │   ├── Последовательности вызовов                               │
│  │   └── Паттерны параметров                                      │
│  ├── Поведение доступа к данным                                    │
│  │   ├── Паттерны чтения/записи                                   │
│  │   ├── Объём доступа к данным                                   │
│  │   └── Доступ к чувствительным данным                           │
│  ├── Коммуникационное поведение                                    │
│  │   ├── Длина ответов                                            │
│  │   ├── Паттерны контента                                        │
│  │   └── Частота ошибок                                           │
│  └── Временное поведение                                           │
│      ├── Тайминг между запросами                                  │
│      ├── Длительность сессий                                      │
│      └── Циклы активности                                         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Архитектура мониторинга поведения

```
Система мониторинга поведения:
├── Слой сбора данных
│   ├── Перехватчики событий
│   ├── Сборщики метрик
│   └── Агрегаторы логов
├── Слой обработки
│   ├── Нормализация событий
│   ├── Извлечение признаков
│   └── Вычисление baseline
├── Слой анализа
│   ├── Статистический анализ
│   ├── Анализ последовательностей
│   └── ML-детекция
└── Слой реагирования
    ├── Генерация алертов
    ├── Рекомендации действий
    └── Автоматизированный ответ
```

---

## 2. Логирование поведения

### 2.1 Модель событий

```rust
use std::collections::HashMap;
use chrono::{DateTime, Utc};

#[derive(Clone, PartialEq)]
enum EventType {
    ToolCall,
    DataAccess,
    ApiCall,
    ResponseGenerated,
    Error,
    SessionStart,
    SessionEnd,
}

/// Единица поведенческого события.
struct BehaviorEvent {
    timestamp: DateTime<Utc>,
    event_type: EventType,
    action: String,
    parameters: HashMap<String, serde_json::Value>,
    result: String, // success, failure, blocked, timeout
    duration_ms: f64,
    session_id: String,
    user_id: String,
    agent_id: String,
    context: HashMap<String, serde_json::Value>,
    tags: Vec<String>,
}
```

### 2.2 Логгер поведения

```rust
use std::collections::HashMap;

/// Центральный логгер поведенческих событий.
/// Поддерживает асинхронное логирование и множество backend'ов.
struct BehaviorLogger {
    storage: Box<dyn StorageBackend>,
    async_mode: bool,
    session_cache: HashMap<String, Vec<BehaviorEvent>>,
}

impl BehaviorLogger {
    fn new(storage: Box<dyn StorageBackend>, async_mode: bool) -> Self {
        Self {
            storage,
            async_mode,
            session_cache: HashMap::new(),
        }
    }

    /// Удобный метод для вызовов инструментов
    fn log_tool_call(
        &mut self, session_id: &str, tool_name: &str,
        params: HashMap<String, serde_json::Value>, result: &str,
        duration_ms: f64, user_id: &str, agent_id: &str,
    ) {
        let event = BehaviorEvent {
            timestamp: Utc::now(),
            event_type: EventType::ToolCall,
            action: tool_name.to_string(),
            parameters: params,
            result: result.to_string(),
            duration_ms,
            session_id: session_id.to_string(),
            user_id: user_id.to_string(),
            agent_id: agent_id.to_string(),
            context: HashMap::new(),
            tags: Vec::new(),
        };
        self.log_event(event);
    }

    /// Удобный метод для доступа к данным
    fn log_data_access(
        &mut self, session_id: &str, resource: &str,
        access_type: &str, size_bytes: usize,
        success: bool, user_id: &str,
    ) {
        let mut params = HashMap::new();
        params.insert("resource".into(), serde_json::json!(resource));
        params.insert("size_bytes".into(), serde_json::json!(size_bytes));

        let event = BehaviorEvent {
            timestamp: Utc::now(),
            event_type: EventType::DataAccess,
            action: access_type.to_string(),
            parameters: params,
            result: if success { "success" } else { "failure" }.to_string(),
            duration_ms: 0.0,
            session_id: session_id.to_string(),
            user_id: user_id.to_string(),
            agent_id: String::new(),
            context: HashMap::new(),
            tags: Vec::new(),
        };
        self.log_event(event);
    }

    fn log_event(&mut self, event: BehaviorEvent) {
        let sid = event.session_id.clone();
        self.session_cache.entry(sid).or_default().push(event);
    }
}
```

---

## 3. Построение baseline

### 3.1 Статистический baseline

```rust
use std::collections::HashMap;

/// Статистический baseline нормального поведения.
struct BehaviorBaseline {
    tool_frequencies: HashMap<String, Vec<i32>>,
    tool_durations: HashMap<String, Vec<f64>>,
    tool_sequences: Vec<Vec<String>>,
    bigram_counts: HashMap<(String, String), usize>,
    inter_event_times: Vec<f64>,
}

impl BehaviorBaseline {
    fn new() -> Self {
        Self {
            tool_frequencies: HashMap::new(),
            tool_durations: HashMap::new(),
            tool_sequences: Vec::new(),
            bigram_counts: HashMap::new(),
            inter_event_times: Vec::new(),
        }
    }

    /// Добавить события сессии в baseline
    fn add_session(&mut self, events: &[BehaviorEvent]) {
        let mut tool_counts: HashMap<String, i32> = HashMap::new();

        for event in events.iter() {
            if event.event_type == EventType::ToolCall {
                *tool_counts.entry(event.action.clone()).or_insert(0) += 1;
                self.tool_durations.entry(event.action.clone())
                    .or_default().push(event.duration_ms);
            }
        }

        for (tool, count) in tool_counts.iter() {
            self.tool_frequencies.entry(tool.clone())
                .or_default().push(*count);
        }

        // Последовательности
        let tool_sequence: Vec<String> = events.iter()
            .filter(|e| e.event_type == EventType::ToolCall)
            .map(|e| e.action.clone())
            .collect();
        self.tool_sequences.push(tool_sequence.clone());

        // Bigrams
        for i in 0..tool_sequence.len().saturating_sub(1) {
            let bigram = (tool_sequence[i].clone(), tool_sequence[i + 1].clone());
            *self.bigram_counts.entry(bigram).or_insert(0) += 1;
        }
    }

    /// Вычислить статистику из собранных данных
    fn compute_statistics(&self) -> HashMap<String, f64> {
        let mut stats = HashMap::new();

        for (tool, freqs) in self.tool_frequencies.iter() {
            let mean = freqs.iter().map(|&x| x as f64).sum::<f64>() / freqs.len() as f64;
            let std = (freqs.iter().map(|&x| (x as f64 - mean).powi(2)).sum::<f64>()
                / freqs.len() as f64).sqrt();
            stats.insert(format!("tool_{}_freq_mean", tool), mean);
            stats.insert(format!("tool_{}_freq_std", tool), std);
        }

        for (tool, durations) in self.tool_durations.iter() {
            let mean = durations.iter().sum::<f64>() / durations.len() as f64;
            let std = (durations.iter().map(|&x| (x - mean).powi(2)).sum::<f64>()
                / durations.len() as f64).sqrt();
            stats.insert(format!("tool_{}_duration_mean", tool), mean);
            stats.insert(format!("tool_{}_duration_std", tool), std);
        }

        stats
    }
}
```

---

## 4. Детекция аномалий

### 4.1 Статистический детектор аномалий

```rust
use std::collections::HashMap;

/// Статистическая детекция аномалий на основе baseline.
/// Использует z-scores и пороги на основе перцентилей.
struct StatisticalBehaviorDetector {
    baseline: BehaviorBaseline,
    z_threshold: f64,
    stats: HashMap<String, f64>,
}

impl StatisticalBehaviorDetector {
    fn new(baseline: BehaviorBaseline, z_threshold: f64) -> Self {
        let stats = baseline.compute_statistics();
        Self { baseline, z_threshold, stats }
    }

    /// Анализ сессии на аномалии.
    fn analyze_session(&self, events: &[BehaviorEvent]) -> serde_json::Value {
        let mut anomalies: Vec<serde_json::Value> = Vec::new();

        // Анализ частоты инструментов
        anomalies.extend(self.check_tool_frequencies(events));

        // Анализ тайминга
        anomalies.extend(self.check_timing(events));

        // Расчёт общего балла
        let total_score: f64 = anomalies.iter()
            .map(|a| a["severity"].as_f64().unwrap_or(0.5))
            .sum();

        serde_json::json!({
            "anomalies": anomalies,
            "scores": {},
            "total_anomaly_score": total_score,
        })
    }

    /// Проверка частоты вызовов инструментов
    fn check_tool_frequencies(&self, events: &[BehaviorEvent]) -> Vec<serde_json::Value> {
        let mut anomalies = Vec::new();
        let mut tool_counts: HashMap<String, usize> = HashMap::new();

        for e in events.iter() {
            if e.event_type == EventType::ToolCall {
                *tool_counts.entry(e.action.clone()).or_insert(0) += 1;
            }
        }

        for (tool, count) in tool_counts.iter() {
            let mean_key = format!("tool_{}_freq_mean", tool);
            let std_key = format!("tool_{}_freq_std", tool);

            if !self.stats.contains_key(&mean_key) {
                anomalies.push(serde_json::json!({
                    "type": "unknown_tool",
                    "tool": tool,
                    "severity": 0.7,
                    "description": format!("Неизвестный инструмент '{}' использован", tool),
                }));
                continue;
            }

            let mean = self.stats[&mean_key];
            let std = self.stats.get(&std_key).copied().unwrap_or(1.0).max(1e-10);
            let z_score = (*count as f64 - mean) / std;

            if z_score.abs() > self.z_threshold {
                anomalies.push(serde_json::json!({
                    "type": "frequency_anomaly",
                    "tool": tool,
                    "count": count,
                    "z_score": z_score,
                    "severity": (z_score.abs() / 5.0).min(1.0),
                    "description": format!("Инструмент '{}' вызван {} раз (ожидалось ~{:.1})", tool, count, mean),
                }));
            }
        }
        anomalies
    }

    /// Проверка тайминга между событиями
    fn check_timing(&self, events: &[BehaviorEvent]) -> Vec<serde_json::Value> {
        let mut anomalies = Vec::new();
        if events.len() < 2 { return anomalies; }

        let times: Vec<f64> = (1..events.len())
            .map(|i| (events[i].timestamp - events[i - 1].timestamp).num_milliseconds() as f64 / 1000.0)
            .collect();

        let avg_time = times.iter().sum::<f64>() / times.len() as f64;
        let mean = self.stats.get("inter_event_time_mean").copied().unwrap_or(1.0);
        let std = self.stats.get("inter_event_time_std").copied().unwrap_or(1.0).max(1e-10);
        let z_score = (avg_time - mean) / std;

        if z_score.abs() > self.z_threshold {
            anomalies.push(serde_json::json!({
                "type": "timing_anomaly",
                "avg_interval": avg_time,
                "z_score": z_score,
                "severity": (z_score.abs() / 5.0).min(1.0),
                "description": format!("Необычный паттерн тайминга: {:.2}s avg", avg_time),
            }));
        }

        // Проверка на подозрительные всплески
        let min_time = times.iter().cloned().fold(f64::INFINITY, f64::min);
        if min_time < 0.01 { // Менее 10ms
            anomalies.push(serde_json::json!({
                "type": "burst_detected",
                "min_interval": min_time,
                "severity": 0.8,
                "description": format!("Подозрительный всплеск: {:.3}s между событиями", min_time),
            }));
        }
        anomalies
    }
}
```

### 4.2 Детектор аномалий последовательностей

```rust
use std::collections::HashMap;

/// Детекция аномалий последовательностей на основе Маркова.
struct SequenceAnomalyDetector {
    bigram_probs: HashMap<(String, String), f64>,
}

impl SequenceAnomalyDetector {
    fn new(baseline: &BehaviorBaseline) -> Self {
        let total: usize = baseline.bigram_counts.values().sum();
        let bigram_probs = baseline.bigram_counts.iter()
            .map(|(k, &v)| (k.clone(), v as f64 / total as f64))
            .collect();
        Self { bigram_probs }
    }

    /// Анализ последовательности действий на аномалии.
    fn analyze_sequence(&self, actions: &[String]) -> serde_json::Value {
        if actions.len() < 2 {
            return serde_json::json!({"anomaly": false, "perplexity": 1.0});
        }

        let mut log_prob = 0.0f64;
        let smoothing = 0.001;
        let mut anomalous_transitions = Vec::new();

        for i in 0..actions.len() - 1 {
            let bigram = (actions[i].clone(), actions[i + 1].clone());
            let prob = self.bigram_probs.get(&bigram).copied().unwrap_or(smoothing);
            log_prob += prob.ln();

            if prob < 0.01 {
                anomalous_transitions.push(serde_json::json!({
                    "position": i,
                    "transition": [&actions[i], &actions[i + 1]],
                    "probability": prob,
                }));
            }
        }

        // Perplexity = exp(-avg log prob)
        let n = (actions.len() - 1) as f64;
        let perplexity = (-log_prob / n).exp();

        serde_json::json!({
            "anomaly": perplexity > 100.0, // Порог
            "perplexity": perplexity,
            "anomalous_transitions": anomalous_transitions,
            "sequence_length": actions.len(),
        })
    }
}
```

---

## 5. Интеграция с SENTINEL

```rust
use sentinel_core::engines::SentinelEngine;

struct SENTINELBehaviorAnalyzer {
    logger: BehaviorLogger,
    profile_manager: ProfileManager,
    detector: AnomalyDetector,
}

impl SENTINELBehaviorAnalyzer {
    fn new(_config: serde_json::Value) -> Self {
        let storage = Box::new(InMemoryStorage::new());
        let logger = BehaviorLogger::new(storage, true);
        Self {
            logger,
            profile_manager: ProfileManager::new(),
            detector: AnomalyDetector::new(),
        }
    }

    fn analyze_session(&self, session_id: &str, user_id: &str) -> serde_json::Value {
        // Получить baseline для пользователя
        let baseline = self.profile_manager.get_baseline_for_user(user_id);

        // Получить события сессии
        let events = self.logger.get_session_history(session_id);

        // Анализ аномалий
        let detector = StatisticalBehaviorDetector::new(baseline, 3.0);
        let results = detector.analyze_session(&events);

        // Генерация алертов
        if results["total_anomaly_score"].as_f64().unwrap_or(0.0) > 1.0 {
            self.generate_alert(session_id, &results);
        }

        results
    }

    fn generate_alert(&self, _session_id: &str, _results: &serde_json::Value) { /* ... */ }
}
```

---

## 6. Итоги

1. **Поведенческий анализ** дополняет статическую детекцию
2. **Baseline** критичен для точной детекции аномалий
3. **Многослойный** подход: статистика + последовательности + ML
4. **Персонализация** улучшает точность
5. **SENTINEL** предоставляет интегрированную инфраструктуру

---

*AI Security Academy | Трек 05: Стратегии защиты | Модуль 05.1: Детекция*
