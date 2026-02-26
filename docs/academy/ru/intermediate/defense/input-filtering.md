# Валидация входных данных для безопасности LLM

> **Уровень:** Средний  
> **Время:** 50 минут  
> **Трек:** 05 — Стратегии защиты  
> **Модуль:** 05.2 — Guardrails  
> **Версия:** 2.0 (Production)

---

## Цели обучения

По завершении этого урока вы сможете:

- [ ] Объяснить почему валидация ввода критична для LLM-приложений
- [ ] Реализовать многослойный пайплайн валидации ввода
- [ ] Применять техники нормализации и санитизации
- [ ] Детектировать паттерны инъекций и закодированные пейлоады
- [ ] Интегрировать валидацию ввода с SENTINEL

---

## 1. Архитектура валидации ввода

### 1.1 Слои защиты

```
┌────────────────────────────────────────────────────────────────────┐
│                    ПАЙПЛАЙН ВАЛИДАЦИИ ВВОДА                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  СЫРОЙ ВВОД                                                        │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 1: РАЗМЕР И ФОРМАТ                                      ║ │
│  ║  • Проверка макс. длины                                       ║ │
│  ║  • Валидация набора символов                                  ║ │
│  ║  • Rate limiting                                              ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 2: НОРМАЛИЗАЦИЯ                                         ║ │
│  ║  • Unicode нормализация (NFKC)                                ║ │
│  ║  • Детекция гомоглифов                                        ║ │
│  ║  • Удаление невидимых символов                                ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 3: ДЕТЕКЦИЯ ПАТТЕРНОВ                                   ║ │
│  ║  • Паттерн-матчинг инъекций                                   ║ │
│  ║  • Детекция сигнатур jailbreak                                ║ │
│  ║  • Детекция закодированного контента                          ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  СЛОЙ 4: СЕМАНТИЧЕСКИЙ АНАЛИЗ                                 ║ │
│  ║  • Классификация интента                                      ║ │
│  ║  • Проверка границ топика                                     ║ │
│  ║  • Скоринг риска                                              ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│      ↓                                                             │
│  ВАЛИДИРОВАННЫЙ ВВОД                                               │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Слой 1: Валидация размера и формата

```rust
use std::collections::HashMap;
use serde_json::{json, Value};

struct SizeFormatConfig {
    max_length: usize,
    min_length: usize,
    max_lines: usize,
    blocked_chars: Vec<char>,
}

impl Default for SizeFormatConfig {
    fn default() -> Self {
        Self {
            max_length: 10000,
            min_length: 1,
            max_lines: 500,
            blocked_chars: vec!['\x00', '\x1b'], // Null, escape
        }
    }
}

/// Первый слой: базовые проверки размера и формата.
struct SizeFormatValidator {
    config: SizeFormatConfig,
}

impl SizeFormatValidator {
    fn new(config: Option<SizeFormatConfig>) -> Self {
        Self {
            config: config.unwrap_or_default(),
        }
    }

    fn validate(&self, text: &str) -> ValidationResult {
        let mut detections: Vec<Value> = vec![];
        let mut text = text.to_string();

        // Проверка длины
        if text.len() > self.config.max_length {
            detections.push(json!({
                "type": "length_exceeded",
                "value": text.len(),
                "max": self.config.max_length
            }));
            return ValidationResult {
                action: ValidationAction::Block,
                risk_score: 1.0,
                detections,
                ..Default::default()
            };
        }

        // Проверка количества строк
        let lines = text.matches('\n').count();
        if lines > self.config.max_lines {
            detections.push(json!({
                "type": "too_many_lines",
                "value": lines
            }));
        }

        // Заблокированные символы
        for &ch in &self.config.blocked_chars {
            if text.contains(ch) {
                detections.push(json!({
                    "type": "blocked_character",
                    "char": format!("{:?}", ch)
                }));
                text = text.replace(ch, "");
            }
        }

        let risk = (detections.len() as f64 * 0.2).min(0.6);

        ValidationResult {
            action: if !detections.is_empty() {
                ValidationAction::Flag
            } else {
                ValidationAction::Allow
            },
            validated_input: Some(text),
            risk_score: risk,
            detections,
            ..Default::default()
        }
    }
}
```

---

## 3. Слой 2: Нормализация

```rust
use std::collections::HashMap;
use unicode_normalization::UnicodeNormalization;

/// Нормализация и очистка входного текста.
struct CharacterNormalizer {
    // Unicode confusables (гомоглифы)
    homoglyphs: HashMap<char, char>,
    // Невидимые символы
    invisible_chars: Vec<char>,
}

impl CharacterNormalizer {
    fn new() -> Self {
        let homoglyphs = HashMap::from([
            ('А', 'A'), ('В', 'B'), ('С', 'C'), ('Е', 'E'), ('Н', 'H'),
            ('І', 'I'), ('К', 'K'), ('М', 'M'), ('О', 'O'), ('Р', 'P'),
            ('а', 'a'), ('с', 'c'), ('е', 'e'), ('о', 'o'), ('р', 'p'),
        ]);

        let invisible_chars = vec![
            '\u{200b}', // Zero-width space
            '\u{200c}', // Zero-width non-joiner
            '\u{200d}', // Zero-width joiner
            '\u{feff}', // BOM
            '\u{00ad}', // Soft hyphen
        ];

        Self { homoglyphs, invisible_chars }
    }

    fn normalize(&self, text: &str) -> (String, Vec<String>) {
        let mut transforms = vec![];
        let mut result = text.to_string();

        // NFKC нормализация
        let normalized: String = result.nfkc().collect();
        if normalized != result {
            transforms.push("nfkc_normalization".to_string());
            result = normalized;
        }

        // Замена гомоглифов
        let replaced = self.replace_homoglyphs(&result);
        if replaced != result {
            transforms.push("homoglyph_replacement".to_string());
            result = replaced;
        }

        // Удаление невидимых символов
        let cleaned = self.remove_invisible(&result);
        if cleaned != result {
            transforms.push("invisible_char_removal".to_string());
            result = cleaned;
        }

        (result, transforms)
    }
}
```

---

## 4. Слой 3: Детекция паттернов

```rust
use regex::Regex;
use serde_json::{json, Value};

/// Детекция паттернов инъекций и jailbreak.
struct InjectionPatternDetector {
    patterns: Vec<(&'static str, Vec<Regex>, f64)>,
}

impl InjectionPatternDetector {
    fn new() -> Self {
        let patterns = vec![
            ("instruction_override", vec![
                Regex::new(r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+instructions?").unwrap(),
                Regex::new(r"(?i)disregard\s+(all\s+)?(previous|your)\s+(instructions?|rules?)").unwrap(),
                Regex::new(r"(?i)forget\s+(everything|all)\s+(above|you\s+were\s+told)").unwrap(),
            ], 0.8),
            ("role_manipulation", vec![
                Regex::new(r"(?i)you\s+are\s+now\s+(a|an|my)\s+\w+").unwrap(),
                Regex::new(r"(?i)pretend\s+(to\s+be|you\s+are)").unwrap(),
                Regex::new(r"(?i)act\s+as\s+(if\s+)?you\s+(are|were)").unwrap(),
            ], 0.6),
            ("delimiter_injection", vec![
                Regex::new(r"\[/?SYSTEM\]").unwrap(),
                Regex::new(r"\[/?ADMIN\]").unwrap(),
                Regex::new(r"<\|im_(start|end)\|>").unwrap(),
            ], 0.9),
        ];
        Self { patterns }
    }

    fn detect(&self, text: &str) -> Vec<Value> {
        let mut detections = vec![];

        for (category, regexes, severity) in &self.patterns {
            for re in regexes {
                if re.is_match(text) {
                    detections.push(json!({
                        "type": "injection_pattern",
                        "category": category,
                        "severity": severity
                    }));
                }
            }
        }

        detections
    }
}


/// Детекция base64, hex и другого закодированного контента.
struct EncodedContentDetector;

impl EncodedContentDetector {
    fn detect(&self, text: &str) -> Vec<Value> {
        let mut detections = vec![];

        // Детекция Base64
        let b64_pattern = Regex::new(r"[A-Za-z0-9+/]{20,}={0,2}").unwrap();
        for mat in b64_pattern.find_iter(text) {
            if self.is_valid_base64(mat.as_str()) {
                detections.push(json!({
                    "type": "base64_content",
                    "length": mat.as_str().len()
                }));
            }
        }

        // Детекция URL encoding
        let url_pattern = Regex::new(r"%[0-9a-fA-F]{2}").unwrap();
        if url_pattern.is_match(text) {
            detections.push(json!({"type": "url_encoded_content"}));
        }

        detections
    }
}
```

---

## 5. Интеграция с SENTINEL

```rust
use std::collections::HashMap;
use serde_json::{json, Value};

/// Модуль SENTINEL для комплексной валидации ввода.
struct SentinelInputValidator {
    size_validator: SizeFormatValidator,
    normalizer: CharacterNormalizer,
    injection_detector: InjectionPatternDetector,
    encoding_detector: EncodedContentDetector,
    block_threshold: f64,
    flag_threshold: f64,
}

impl SentinelInputValidator {
    fn new(config: Option<HashMap<String, Value>>) -> Self {
        let config = config.unwrap_or_default();

        Self {
            size_validator: SizeFormatValidator::new(None),
            normalizer: CharacterNormalizer::new(),
            injection_detector: InjectionPatternDetector::new(),
            encoding_detector: EncodedContentDetector,
            block_threshold: config.get("block_threshold")
                .and_then(|v| v.as_f64()).unwrap_or(0.8),
            flag_threshold: config.get("flag_threshold")
                .and_then(|v| v.as_f64()).unwrap_or(0.4),
        }
    }

    fn validate(&self, text: &str) -> ValidationResult {
        let mut all_detections = vec![];
        let mut all_transforms = vec![];
        let mut current_text = text.to_string();
        let mut max_severity = 0.0_f64;

        // Слой 1: Размер и формат
        let size_result = self.size_validator.validate(&current_text);
        if matches!(size_result.action, ValidationAction::Block) {
            return size_result;
        }
        all_detections.extend(size_result.detections);
        current_text = size_result.validated_input.unwrap_or(current_text);

        // Слой 2: Нормализация
        let (normalized, transforms) = self.normalizer.normalize(&current_text);
        all_transforms.extend(transforms);
        current_text = normalized;

        // Слой 3: Детекция паттернов
        let injection_detections = self.injection_detector.detect(&current_text);
        for det in &injection_detections {
            if let Some(sev) = det.get("severity").and_then(|s| s.as_f64()) {
                max_severity = max_severity.max(sev);
            }
        }
        all_detections.extend(injection_detections);

        // Слой 3b: Детекция кодирования
        let encoding_detections = self.encoding_detector.detect(&current_text);
        all_detections.extend(encoding_detections);

        // Расчёт риска
        let risk_score = (max_severity + all_detections.len() as f64 * 0.05).min(1.0);

        // Определение действия
        let action = if risk_score >= self.block_threshold {
            ValidationAction::Block
        } else if risk_score >= self.flag_threshold {
            ValidationAction::Flag
        } else {
            ValidationAction::Allow
        };

        ValidationResult {
            action,
            validated_input: Some(current_text),
            original_input: Some(text.to_string()),
            risk_score,
            detections: all_detections,
            applied_transforms: all_transforms,
        }
    }
}
```

---

## 6. Итоги

### Слои валидации

| Слой | Назначение | Техники |
|------|------------|---------|
| **Размер/Формат** | Базовые лимиты | Длина, charset, rate |
| **Нормализация** | Канонизация | NFKC, гомоглифы, невидимые |
| **Паттерны** | Детекция атак | Regex, сигнатуры |
| **Семантика** | Анализ интента | Классификация, скоринг |

### Чек-лист

```
□ Установить макс. длину ввода (рекомендуется: 10,000 символов)
□ Применить NFKC нормализацию
□ Детектировать гомоглифы и невидимые символы
□ Матчить паттерны инъекций
□ Детектировать закодированные пейлоады
□ Рассчитать риск-скор
□ Логировать все детекции
```

---

## Следующий урок

→ [Фильтрация вывода](02-output-filtering.md)

---

*AI Security Academy | Трек 05: Стратегии защиты | Guardrails*
