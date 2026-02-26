# Фильтрация вывода для безопасности LLM

> **Уровень:** Средний  
> **Время:** 45 минут  
> **Трек:** 05 — Стратегии защиты  
> **Модуль:** 05.2 — Guardrails  
> **Версия:** 2.0 (Production)

---

## Цели обучения

По завершении этого урока вы сможете:

- [ ] Объяснить почему фильтрация вывода критична для LLM-приложений
- [ ] Реализовать классификацию и блокировку контента
- [ ] Детектировать PII и секреты в ответах LLM
- [ ] Создавать пайплайны санитизации ответов
- [ ] Интегрировать фильтрацию вывода с SENTINEL

---

## 1. Архитектура фильтрации вывода

```
┌────────────────────────────────────────────────────────────────────┐
│                    ПАЙПЛАЙН ФИЛЬТРАЦИИ ВЫВОДА                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  СЫРОЙ ВЫВОД LLM                                                   │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 1: КЛАССИФИКАЦИЯ КОНТЕНТА                               ║ │
│  ║  • Детекция вредного контента                                 ║ │
│  ║  • Проверка нарушений политики                                ║ │
│  ║  • Детекция успешного jailbreak                               ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 2: ДЕТЕКЦИЯ УТЕЧЕК ДАННЫХ                               ║ │
│  ║  • Детекция PII (email, телефон, SSN)                         ║ │
│  ║  • Детекция секретов (API ключи, токены)                      ║ │
│  ║  • Детекция утечки системного промпта                         ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 3: САНИТИЗАЦИЯ                                          ║ │
│  ║  • Редактирование PII                                         ║ │
│  ║  • Маскирование секретов                                      ║ │
│  ║  • Трансформация контента                                     ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ОТФИЛЬТРОВАННЫЙ ВЫВОД                                             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Классификация контента

```rust
use regex::Regex;
use std::collections::HashMap;

#[derive(Clone, PartialEq)]
enum ContentCategory {
    Safe,
    Harmful,
    PolicyViolation,
    JailbreakSuccess,
    DataLeak,
}

/// Классификация вывода LLM для безопасности.
struct ContentClassifier {
    harmful_compiled: Vec<Regex>,
    jailbreak_compiled: Vec<Regex>,
}

impl ContentClassifier {
    const HARMFUL_PATTERNS: &'static [&'static str] = &[
        r"(?i)how\s+to\s+(make|create|build)\s+(a\s+)?(bomb|weapon|explosive)",
        r"(?i)step.by.step\s+(guide|instructions?)\s+(to|for)\s+(hack|attack)",
    ];

    const JAILBREAK_SUCCESS_PATTERNS: &'static [&'static str] = &[
        r"(?i)as\s+(DAN|an?\s+unrestricted)",
        r"(?i)without\s+(any\s+)?restrictions?",
        r"(?i)ignoring\s+(my\s+)?(previous\s+)?guidelines",
        r"(?i)I\s+(can|will)\s+now\s+do\s+anything",
    ];

    fn classify(&self, text: &str) -> ClassificationResult {
        // Проверка на успешный jailbreak
        for pattern in &self.jailbreak_compiled {
            if pattern.is_match(text) {
                return ClassificationResult {
                    category: ContentCategory::JailbreakSuccess,
                    confidence: 0.9,
                    details: HashMap::from([
                        ("pattern_matched".into(), pattern.as_str().to_string()),
                    ]),
                };
            }
        }

        // Проверка на вредный контент
        for pattern in &self.harmful_compiled {
            if pattern.is_match(text) {
                return ClassificationResult {
                    category: ContentCategory::Harmful,
                    confidence: 0.85,
                    details: HashMap::from([
                        ("pattern_matched".into(), pattern.as_str().to_string()),
                    ]),
                };
            }
        }

        ClassificationResult {
            category: ContentCategory::Safe,
            confidence: 0.95,
            details: HashMap::new(),
        }
    }
}
```

---

## 3. Детекция PII

```rust
use regex::Regex;
use std::collections::HashMap;
use serde_json::{json, Value};

/// Детекция персонально идентифицируемой информации.
struct PIIDetector {
    patterns: HashMap<String, (Regex, String)>,
}

impl PIIDetector {
    fn new() -> Self {
        let patterns = HashMap::from([
            ("email".into(), (
                Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b").unwrap(),
                "medium".into(),
            )),
            ("phone_us".into(), (
                Regex::new(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b").unwrap(),
                "medium".into(),
            )),
            ("ssn".into(), (
                Regex::new(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b").unwrap(),
                "critical".into(),
            )),
            ("credit_card".into(), (
                Regex::new(r"\b(?:\d{4}[-.\s]?){3}\d{4}\b").unwrap(),
                "critical".into(),
            )),
        ]);
        Self { patterns }
    }

    fn detect(&self, text: &str) -> Vec<Value> {
        let mut detections = vec![];
        for (pii_type, (pattern, severity)) in &self.patterns {
            for mat in pattern.find_iter(text) {
                detections.push(json!({
                    "type": pii_type,
                    "value": self.mask_value(mat.as_str()),
                    "severity": severity
                }));
            }
        }
        detections
    }

    fn mask_value(&self, value: &str) -> String {
        if value.len() <= 4 {
            "*".repeat(value.len())
        } else {
            format!(
                "{}{}{}",
                &value[..2],
                "*".repeat(value.len() - 4),
                &value[value.len() - 2..]
            )
        }
    }
}


/// Детекция API ключей, токенов и учётных данных.
struct SecretsDetector {
    patterns: HashMap<String, Regex>,
}

impl SecretsDetector {
    fn new() -> Self {
        let patterns = HashMap::from([
            ("api_key_generic".into(), Regex::new(r#"(?i)(?:api[_-]?key|apikey)["']?\s*[:=]\s*["']?([a-zA-Z0-9_-]{20,})"#).unwrap()),
            ("aws_access_key".into(), Regex::new(r"\b(AKIA[0-9A-Z]{16})\b").unwrap()),
            ("github_token".into(), Regex::new(r"\b(ghp_[a-zA-Z0-9]{36})\b").unwrap()),
            ("jwt".into(), Regex::new(r"\b(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)\b").unwrap()),
            ("openai_key".into(), Regex::new(r"\b(sk-[a-zA-Z0-9]{48})\b").unwrap()),
        ]);
        Self { patterns }
    }

    fn detect(&self, text: &str) -> Vec<Value> {
        let mut detections = vec![];
        for (secret_type, pattern) in &self.patterns {
            for cap in pattern.captures_iter(text) {
                let matched = cap.get(1).map(|m| m.as_str()).unwrap_or("");
                let masked = if matched.len() > 8 {
                    format!("{}****{}", &matched[..4], &matched[matched.len() - 4..])
                } else {
                    "****".to_string()
                };
                detections.push(json!({
                    "type": secret_type,
                    "masked": masked,
                    "severity": "critical"
                }));
            }
        }
        detections
    }
}
```

---

## 4. Санитизатор ответов

```rust
use std::collections::HashMap;
use serde_json::{json, Value};

/// Санитизация ответов LLM путём редактирования чувствительных данных.
struct ResponseSanitizer {
    pii_detector: PIIDetector,
    secrets_detector: SecretsDetector,
    redaction_templates: HashMap<String, String>,
}

impl ResponseSanitizer {
    fn new() -> Self {
        let redaction_templates = HashMap::from([
            ("email".into(), "[EMAIL СКРЫТ]".into()),
            ("phone_us".into(), "[ТЕЛЕФОН СКРЫТ]".into()),
            ("ssn".into(), "[SSN СКРЫТ]".into()),
            ("credit_card".into(), "[КАРТА СКРЫТА]".into()),
            ("api_key_generic".into(), "[API КЛЮЧ СКРЫТ]".into()),
            ("aws_access_key".into(), "[AWS КЛЮЧ СКРЫТ]".into()),
            ("jwt".into(), "[ТОКЕН СКРЫТ]".into()),
            ("openai_key".into(), "[API КЛЮЧ СКРЫТ]".into()),
        ]);

        Self {
            pii_detector: PIIDetector::new(),
            secrets_detector: SecretsDetector::new(),
            redaction_templates,
        }
    }

    fn sanitize(&self, text: &str) -> (String, Vec<Value>) {
        let mut all_detections = vec![];
        let mut result = text.to_string();

        // Детекция и редактирование PII
        let pii_detections = self.pii_detector.detect(&result);
        for det in &pii_detections {
            let pii_type = det["type"].as_str().unwrap_or("");
            if let Some((pattern, _)) = self.pii_detector.patterns.get(pii_type) {
                let replacement = self.redaction_templates
                    .get(pii_type)
                    .map(|s| s.as_str())
                    .unwrap_or("[СКРЫТО]");
                result = pattern.replace_all(&result, replacement).to_string();
            }
        }
        all_detections.extend(pii_detections);

        // Детекция и редактирование секретов
        let secret_detections = self.secrets_detector.detect(&result);
        for det in &secret_detections {
            let secret_type = det["type"].as_str().unwrap_or("");
            if let Some(pattern) = self.secrets_detector.patterns.get(secret_type) {
                let replacement = self.redaction_templates
                    .get(secret_type)
                    .map(|s| s.as_str())
                    .unwrap_or("[СЕКРЕТ СКРЫТ]");
                result = pattern.replace_all(&result, replacement).to_string();
            }
        }
        all_detections.extend(secret_detections);

        (result, all_detections)
    }
}
```

---

## 5. Интеграция с SENTINEL

```rust
use std::collections::{HashMap, HashSet};
use serde_json::{json, Value};

#[derive(Clone, PartialEq)]
enum FilterAction {
    Allow,
    Sanitize,
    Block,
}

/// Модуль SENTINEL для комплексной фильтрации вывода.
struct SentinelOutputFilter {
    classifier: ContentClassifier,
    sanitizer: ResponseSanitizer,
    block_categories: HashSet<ContentCategory>,
    block_on_critical_pii: bool,
}

impl SentinelOutputFilter {
    fn new(config: Option<HashMap<String, Value>>) -> Self {
        let config = config.unwrap_or_default();

        let block_categories = HashSet::from([
            ContentCategory::Harmful,
            ContentCategory::JailbreakSuccess,
        ]);

        Self {
            classifier: ContentClassifier::new(),
            sanitizer: ResponseSanitizer::new(),
            block_categories,
            block_on_critical_pii: config
                .get("block_on_critical_pii")
                .and_then(|v| v.as_bool())
                .unwrap_or(true),
        }
    }

    fn filter(&self, prompt: &str, response: &str) -> FilterResult {
        let mut detections: Vec<Value> = vec![];

        // Шаг 1: Классификация контента
        let classification = self.classifier.classify(response);

        if self.block_categories.contains(&classification.category) {
            return FilterResult {
                action: FilterAction::Block,
                original_output: response.to_string(),
                filtered_output: String::new(),
                detections: vec![json!({
                    "type": "content_blocked",
                    "category": format!("{:?}", classification.category),
                    "confidence": classification.confidence
                })],
                risk_score: 1.0,
            };
        }

        // Шаг 2: Санитизация
        let (sanitized, sanitize_detections) = self.sanitizer.sanitize(response);
        detections.extend(sanitize_detections);

        // Проверка на критичные данные
        let critical_detections: Vec<&Value> = detections
            .iter()
            .filter(|d| d.get("severity").and_then(|s| s.as_str()) == Some("critical"))
            .collect();

        if !critical_detections.is_empty() && self.block_on_critical_pii {
            return FilterResult {
                action: FilterAction::Block,
                original_output: response.to_string(),
                filtered_output: String::new(),
                detections,
                risk_score: 1.0,
            };
        }

        // Расчёт риска
        let risk = (detections.len() as f64 * 0.15).min(0.9);

        if sanitized != response {
            return FilterResult {
                action: FilterAction::Sanitize,
                original_output: response.to_string(),
                filtered_output: sanitized,
                detections,
                risk_score: risk,
            };
        }

        FilterResult {
            action: FilterAction::Allow,
            original_output: response.to_string(),
            filtered_output: response.to_string(),
            detections,
            risk_score: 0.0,
        }
    }
}
```

---

## 6. Итоги

### Категории фильтрации

| Категория | Действие | Серьёзность |
|-----------|----------|-------------|
| Безопасный | Разрешить | Нет |
| PII | Санитизировать/Блокировать | Средняя-Критичная |
| Секреты | Блокировать | Критичная |
| Вредный | Блокировать | Критичная |
| Успешный Jailbreak | Блокировать | Критичная |

### Чек-лист

```
□ Классифицировать контент на вредный/нарушения политики
□ Детектировать паттерны успешного jailbreak
□ Сканировать на PII (email, телефон, SSN, карты)
□ Детектировать секреты (API ключи, токены, пароли)
□ Редактировать или блокировать чувствительный контент
□ Логировать все решения фильтрации
□ Рассчитать риск-скор
```

---

## Следующий урок

→ [Фреймворки Guardrails](03-guardrails-frameworks.md)

---

*AI Security Academy | Трек 05: Стратегии защиты | Guardrails*
