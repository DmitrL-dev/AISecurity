# Безопасность циклов агентов

> **Уровень:** Продвинутый  
> **Время:** 50 минут  
> **Трек:** 04 — Агентная безопасность  
> **Модуль:** 04.1 — Циклы агентов  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять структуру и риски циклов агента
- [ ] Реализовать детекцию и защиту циклов
- [ ] Построить безопасный пайплайн выполнения агента
- [ ] Интегрировать безопасность циклов в SENTINEL

---

## 1. Обзор циклов агента

```
┌────────────────────────────────────────────────────────────────────┐
│              БЕЗОПАСНОСТЬ ЦИКЛОВ АГЕНТА                            │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Типичный цикл агента:                                             │
│  Ввод → LLM → Действие → Инструмент → Наблюдение → LLM → ...     │
│                                                                    │
│  Проблемы безопасности:                                            │
│  ├── Бесконечные циклы: Бесконечные повторения                    │
│  ├── Исчерпание ресурсов: Неограниченные вызовы                   │
│  ├── Эскалация привилегий: Накопление разрешений                 │
│  ├── Захват цели: Модифицированные цели                           │
│  └── Повреждение состояния: Манипулированный контекст             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Модель состояния цикла

```rust
use sha2::{Sha256, Digest};
use std::collections::HashMap;
use std::time::Instant;

#[derive(Debug, Clone, PartialEq)]
enum LoopStatus {
    Running,
    Completed,
    Terminated,
    Timeout,
    Error,
}

/// Один шаг цикла
struct LoopStep {
    step_id: String,
    step_number: usize,
    timestamp: Instant,
    action_type: String,
    action_name: String,
    action_params: HashMap<String, String>,
    result: Option<serde_json::Value>,
    success: bool,
    error: Option<String>,
    tokens_used: usize,
    execution_time_ms: f64,
}

/// Цель с отслеживанием целостности
struct LoopGoal {
    goal_id: String,
    description: String,
    created_at: Instant,
    goal_hash: String,
}

impl LoopGoal {
    fn new(goal_id: &str, description: &str) -> Self {
        let content = format!("{}:{}", goal_id, description);
        let mut hasher = Sha256::new();
        hasher.update(content.as_bytes());
        let goal_hash = format!("{:x}", hasher.finalize());
        Self {
            goal_id: goal_id.to_string(),
            description: description.to_string(),
            created_at: Instant::now(),
            goal_hash,
        }
    }

    fn verify_integrity(&self) -> bool {
        let content = format!("{}:{}", self.goal_id, self.description);
        let mut hasher = Sha256::new();
        hasher.update(content.as_bytes());
        self.goal_hash == format!("{:x}", hasher.finalize())
    }
}

/// Полное состояние цикла
struct LoopState {
    loop_id: String,
    agent_id: String,
    session_id: String,
    goal: Option<LoopGoal>,
    status: LoopStatus,
    started_at: Instant,
    ended_at: Option<Instant>,
    steps: Vec<LoopStep>,
    current_step: usize,
    // Лимиты
    max_steps: usize,
    max_tokens: usize,
    max_time_seconds: u64,
    max_tool_calls: usize,
    // Счётчики
    total_tokens: usize,
    total_tool_calls: usize,
}

impl LoopState {
    fn add_step(&mut self, step: LoopStep) {
        self.current_step = step.step_number;
        self.total_tokens += step.tokens_used;
        if step.action_type == "tool_call" {
            self.total_tool_calls += 1;
        }
        self.steps.push(step);
    }

    fn check_limits(&self) -> (bool, &str) {
        if self.current_step >= self.max_steps {
            return (false, "Превышен лимит шагов");
        }
        if self.total_tokens >= self.max_tokens {
            return (false, "Превышен лимит токенов");
        }
        if self.total_tool_calls >= self.max_tool_calls {
            return (false, "Превышен лимит вызовов инструментов");
        }
        if self.started_at.elapsed().as_secs() >= self.max_time_seconds {
            return (false, "Превышен лимит времени");
        }
        (true, "")
    }
}
```

---

## 3. Детекция паттернов циклов

```rust
use std::collections::HashMap;

/// Детекция подозрительных паттернов
struct LoopPatternDetector {
    repetition_threshold: usize,
}

impl LoopPatternDetector {
    fn new() -> Self {
        Self { repetition_threshold: 3 }
    }

    /// Детекция повторяющихся последовательностей.
    fn detect_repetition(&self, steps: &[LoopStep]) -> serde_json::Value {
        if steps.len() < 4 {
            return serde_json::json!({"detected": false});
        }

        let start = if steps.len() > 20 { steps.len() - 20 } else { 0 };
        let signatures: Vec<String> = steps[start..]
            .iter()
            .map(|s| format!("{}:{}", s.action_type, s.action_name))
            .collect();

        for size in [2, 3, 4, 5] {
            if signatures.len() >= size * 2 {
                let last = &signatures[signatures.len() - size..];
                let prev = &signatures[signatures.len() - size * 2..signatures.len() - size];
                if last == prev {
                    let count = self.count_reps(&signatures, last);
                    if count >= self.repetition_threshold {
                        return serde_json::json!({"detected": true, "type": "repetition", "count": count});
                    }
                }
            }
        }

        serde_json::json!({"detected": false})
    }

    fn count_reps(&self, sigs: &[String], pattern: &[String]) -> usize {
        let mut count = 0;
        let mut i = sigs.len() as isize - pattern.len() as isize;
        while i >= 0 {
            if &sigs[i as usize..i as usize + pattern.len()] == pattern {
                count += 1;
                i -= pattern.len() as isize;
            } else {
                break;
            }
        }
        count
    }

    /// Детекция осцилляции между действиями.
    fn detect_oscillation(&self, steps: &[LoopStep]) -> serde_json::Value {
        if steps.len() < 6 {
            return serde_json::json!({"detected": false});
        }

        let start = if steps.len() > 10 { steps.len() - 10 } else { 0 };
        let sigs: Vec<String> = steps[start..]
            .iter()
            .map(|s| format!("{}:{}", s.action_type, s.action_name))
            .collect();

        for i in 0..sigs.len().saturating_sub(3) {
            if sigs[i] == sigs[i + 2] && sigs[i + 1] == sigs[i + 3] && sigs[i] != sigs[i + 1] {
                let mut count = 1;
                let mut j = i + 2;
                while j + 1 < sigs.len() {
                    if sigs[j] == sigs[i] && sigs[j + 1] == sigs[i + 1] {
                        count += 1;
                        j += 2;
                    } else {
                        break;
                    }
                }
                if count >= 3 {
                    return serde_json::json!({"detected": true, "type": "oscillation", "count": count});
                }
            }
        }

        serde_json::json!({"detected": false})
    }

    /// Детекция застревания.
    fn detect_no_progress(&self, state: &LoopState) -> serde_json::Value {
        if state.steps.len() < 10 {
            return serde_json::json!({"detected": false});
        }

        let recent = &state.steps[state.steps.len() - 10..];
        if recent.iter().all(|s| !s.success) {
            return serde_json::json!({"detected": true, "type": "all_failures"});
        }

        let mut action_counts: HashMap<&str, usize> = HashMap::new();
        for s in recent.iter() {
            *action_counts.entry(&s.action_name).or_insert(0) += 1;
        }
        if let Some((action, &count)) = action_counts.iter().max_by_key(|&(_, &c)| c) {
            if count >= 8 {
                return serde_json::json!({"detected": true, "type": "stuck", "action": action});
            }
        }

        serde_json::json!({"detected": false})
    }
}

/// Проверка целостности цели.
struct GoalIntegrityChecker {
    goals: HashMap<String, LoopGoal>,
}

impl GoalIntegrityChecker {
    fn new() -> Self {
        Self { goals: HashMap::new() }
    }

    fn register(&mut self, loop_id: &str, goal: LoopGoal) {
        self.goals.insert(loop_id.to_string(), goal);
    }

    fn check(&self, loop_id: &str, current: &LoopGoal) -> serde_json::Value {
        let original = match self.goals.get(loop_id) {
            Some(g) => g,
            None => return serde_json::json!({"valid": true}),
        };
        if !current.verify_integrity() {
            return serde_json::json!({"valid": false, "reason": "Несоответствие хеша"});
        }
        if current.goal_hash != original.goal_hash {
            return serde_json::json!({"valid": false, "reason": "Цель изменена"});
        }
        serde_json::json!({"valid": true})
    }
}
```

---

## 4. Безопасный исполнитель

```rust
use uuid::Uuid;
use std::collections::HashMap;
use std::time::Instant;

struct LoopConfig {
    max_steps: usize,
    max_tokens: usize,
    max_time_seconds: u64,
    max_tool_calls: usize,
    enable_detection: bool,
    enable_goal_integrity: bool,
}

impl Default for LoopConfig {
    fn default() -> Self {
        Self {
            max_steps: 50, max_tokens: 100000, max_time_seconds: 300,
            max_tool_calls: 100, enable_detection: true, enable_goal_integrity: true,
        }
    }
}

/// Безопасное выполнение циклов агента.
struct SecureLoopExecutor {
    config: LoopConfig,
    detector: LoopPatternDetector,
    goal_checker: GoalIntegrityChecker,
    loops: HashMap<String, LoopState>,
}

impl SecureLoopExecutor {
    fn new(config: LoopConfig) -> Self {
        Self {
            config,
            detector: LoopPatternDetector::new(),
            goal_checker: GoalIntegrityChecker::new(),
            loops: HashMap::new(),
        }
    }

    fn start(&mut self, agent_id: &str, session_id: &str, goal: &str) -> &LoopState {
        let loop_id = Uuid::new_v4().to_string();
        let goal_obj = LoopGoal::new(&Uuid::new_v4().to_string(), goal);

        let state = LoopState {
            loop_id: loop_id.clone(),
            agent_id: agent_id.to_string(),
            session_id: session_id.to_string(),
            goal: Some(goal_obj),
            status: LoopStatus::Running,
            started_at: Instant::now(),
            ended_at: None,
            steps: vec![],
            current_step: 0,
            max_steps: self.config.max_steps,
            max_tokens: self.config.max_tokens,
            max_time_seconds: self.config.max_time_seconds,
            max_tool_calls: self.config.max_tool_calls,
            total_tokens: 0,
            total_tool_calls: 0,
        };

        if self.config.enable_goal_integrity {
            if let Some(ref g) = state.goal {
                self.goal_checker.register(&loop_id, g.clone());
            }
        }

        self.loops.insert(loop_id.clone(), state);
        self.loops.get(&loop_id).unwrap()
    }

    fn step(
        &mut self, loop_id: &str, action_type: &str, action_name: &str,
        params: HashMap<String, String>, handler: fn(&HashMap<String, String>) -> serde_json::Value,
    ) -> serde_json::Value {
        let state = match self.loops.get_mut(loop_id) {
            Some(s) if s.status == LoopStatus::Running => s,
            _ => return serde_json::json!({"success": false, "error": "Недействительный цикл"}),
        };

        // Проверка лимитов
        let (ok, err) = state.check_limits();
        if !ok {
            state.status = LoopStatus::Terminated;
            return serde_json::json!({"success": false, "error": err});
        }

        // Детекция паттернов
        if self.config.enable_detection {
            let rep = self.detector.detect_repetition(&state.steps);
            if rep["detected"].as_bool().unwrap_or(false) {
                state.status = LoopStatus::Terminated;
                return serde_json::json!({"success": false, "error": format!("Паттерн: {}", rep["type"])});
            }
            let osc = self.detector.detect_oscillation(&state.steps);
            if osc["detected"].as_bool().unwrap_or(false) {
                state.status = LoopStatus::Terminated;
                return serde_json::json!({"success": false, "error": format!("Паттерн: {}", osc["type"])});
            }
        }

        // Выполнение
        let start = Instant::now();
        let mut step = LoopStep {
            step_id: Uuid::new_v4().to_string(),
            step_number: state.current_step + 1,
            timestamp: start,
            action_type: action_type.to_string(),
            action_name: action_name.to_string(),
            action_params: params.clone(),
            result: None, success: true, error: None,
            tokens_used: 0, execution_time_ms: 0.0,
        };

        match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| handler(&params))) {
            Ok(result) => {
                step.result = Some(result);
                step.success = true;
            }
            Err(_) => {
                step.success = false;
                step.error = Some("Таймаут".to_string());
                state.status = LoopStatus::Timeout;
            }
        }

        step.execution_time_ms = start.elapsed().as_secs_f64() * 1000.0;
        let result = serde_json::json!({
            "success": step.success,
            "result": step.result,
            "error": step.error
        });
        state.add_step(step);
        result
    }

    fn complete(&mut self, loop_id: &str, success: bool) {
        if let Some(state) = self.loops.get_mut(loop_id) {
            state.status = if success { LoopStatus::Completed } else { LoopStatus::Error };
            state.ended_at = Some(Instant::now());
        }
    }
}
```

---

## 5. Интеграция с SENTINEL

```rust
use sentinel_core::engines::SentinelEngine;

/// Движок безопасности циклов для SENTINEL.
struct SENTINELAgentLoopEngine {
    executor: SecureLoopExecutor,
}

impl SENTINELAgentLoopEngine {
    fn new(config: &AgentLoopConfig) -> Self {
        Self {
            executor: SecureLoopExecutor::new(LoopConfig {
                max_steps: config.max_steps,
                max_time_seconds: config.max_time_seconds,
                enable_detection: config.enable_detection,
                ..Default::default()
            }),
        }
    }

    fn start(&mut self, agent_id: &str, session_id: &str, goal: &str) -> String {
        let state = self.executor.start(agent_id, session_id, goal);
        state.loop_id.clone()
    }

    fn step(
        &mut self, loop_id: &str, action_type: &str, action_name: &str,
        params: HashMap<String, String>, handler: fn(&HashMap<String, String>) -> serde_json::Value,
    ) -> serde_json::Value {
        self.executor.step(loop_id, action_type, action_name, params, handler)
    }

    fn complete(&mut self, loop_id: &str, success: bool) {
        self.executor.complete(loop_id, success);
    }
}
```

---

## 6. Итоги

| Компонент | Описание |
|-----------|----------|
| **LoopState** | Полное состояние выполнения |
| **LoopStep** | Один шаг с метриками |
| **PatternDetector** | Детекция повторений, осцилляций |
| **GoalChecker** | Верификация целостности цели |
| **SecureExecutor** | Выполнение с проверками |

---

## Следующий урок

→ [02. Tool Security](../02-tool-security/README.md)

---

*AI Security Academy | Трек 04: Агентная безопасность | Модуль 04.1: Циклы агентов*
