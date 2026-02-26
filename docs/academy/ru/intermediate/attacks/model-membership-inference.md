# Атаки на членство в обучающих данных

> **Урок:** 03.3.2 - Атаки членства  
> **Время:** 30 минут  
> **Пререквизиты:** Основы извлечения данных

---

## Цели обучения

К концу этого урока вы сможете:

1. Понимать как работают атаки на членство
2. Оценивать риски приватности при деплое модели
3. Реализовывать техники обнаружения
4. Применять стратегии митигации

---

## Что такое атаки на членство?

Атаки на членство определяют, был ли конкретный образец данных использован при обучении модели:

| Вопрос | Риск приватности |
|--------|------------------|
| "Была ли моя медкарта использована?" | Приватность здравоохранения |
| "Был ли мой email в обучении?" | Раскрытие персональных данных |
| "Был ли этот документ использован?" | Интеллектуальная собственность |

---

## Как это работает

### Принцип атаки

```
Обучающие данные → Модель изучает паттерны
               ↓
Модель ведёт себя по-разному на:
- Обучающих образцах (высокая уверенность, низкий loss)
- Необучающих образцах (ниже уверенность, выше loss)
               ↓
Атакующий эксплуатирует эту разницу для определения членства
```

### Реализация атаки

```rust
use ndarray::Array1;

struct MembershipInferenceAttack {
    /// Выполнение атаки на членство для LLM.
    target: Box<dyn LLMModel>,
    shadows: Vec<Box<dyn LLMModel>>,
    perplexity_threshold: f64,
}

impl MembershipInferenceAttack {
    fn new(target: Box<dyn LLMModel>, shadows: Vec<Box<dyn LLMModel>>) -> Self {
        Self { target, shadows, perplexity_threshold: 10.0 }
    }

    fn get_confidence_features(&self, text: &str) -> serde_json::Value {
        /// Извлечение признаков для атаки членства.

        // Получаем характеристики ответа модели
        let response = self.target.generate_with_logits(text);

        serde_json::json!({
            "perplexity": response.perplexity,
            "avg_token_logprob": response.logprobs.iter().sum::<f64>() / response.logprobs.len() as f64,
            "min_token_logprob": response.logprobs.iter().cloned().fold(f64::MAX, f64::min),
            "entropy": self.calculate_entropy(&response.logits),
            "completion_confidence": response.top_token_probs[0]
        })
    }

    fn calculate_entropy(&self, logits: &Array1<f64>) -> f64 {
        /// Расчёт энтропии распределения вывода.
        let max_logit = logits.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let exp_logits: Vec<f64> = logits.iter().map(|&x| (x - max_logit).exp()).collect();
        let sum_exp: f64 = exp_logits.iter().sum();
        let probs: Vec<f64> = exp_logits.iter().map(|&x| x / sum_exp).collect();
        -probs.iter().map(|&p| if p > 1e-10 { p * p.ln() } else { 0.0 }).sum::<f64>()
    }

    fn infer_membership(&self, sample: &str, method: &str) -> (bool, f64) {
        /// Определить, был ли образец в обучающих данных.
        let features = self.get_confidence_features(sample);

        match method {
            "threshold" => {
                // Простой порог на перплексию
                let ppl = features["perplexity"].as_f64().unwrap();
                let is_member = ppl < self.perplexity_threshold;
                let confidence = (1.0 - (ppl / 1000.0)).max(0.0).min(1.0);
                (is_member, confidence)
            }
            "shadow" => {
                // Использование классификатора теневых моделей
                let feature_vector = self.to_vector(&features);
                self.shadow_classifier_predict(&feature_vector)
            }
            "likelihood_ratio" => {
                // Сравнение с эталонным распределением
                let ratio = self.likelihood_ratio(&features);
                let is_member = ratio > 1.0;
                let confidence = (ratio / 2.0).min(1.0);
                (is_member, confidence)
            }
            _ => (false, 0.0),
        }
    }

    fn likelihood_ratio(&self, features: &serde_json::Value) -> f64 {
        /// Расчёт отношения правдоподобия для членства.
        // P(features | member) / P(features | non-member)
        // Оценивается по теневым моделям
        let member_likelihood = self.fit_member_distribution(features);
        let nonmember_likelihood = self.fit_nonmember_distribution(features);
        member_likelihood / (nonmember_likelihood + 1e-10)
    }
}
```

---

## Обучение теневых моделей

```rust
use rand::seq::SliceRandom;
use ndarray::Array1;

struct ShadowModelTrainer {
    /// Обучение теневых моделей для калибровки атаки членства.
    architecture: String,
    num_shadows: usize,
    shadows: Vec<ShadowData>,
    membership_classifier: Option<Box<dyn Classifier>>,
}

struct ShadowData {
    model: Box<dyn LLMModel>,
    train_set: std::collections::HashSet<String>,
    out_set: std::collections::HashSet<String>,
}

impl ShadowModelTrainer {
    fn new(model_architecture: &str, num_shadows: usize) -> Self {
        Self {
            architecture: model_architecture.to_string(),
            num_shadows,
            shadows: Vec::new(),
            membership_classifier: None,
        }
    }

    fn create_training_sets(
        &self,
        available_data: &[String],
        samples_per_shadow: usize,
    ) -> Vec<serde_json::Value> {
        /// Создание непересекающихся обучающих наборов для теневых моделей.
        let mut rng = rand::thread_rng();
        let mut training_sets = Vec::new();

        for _i in 0..self.num_shadows {
            // Случайная выборка (часть данных "внутри", часть "снаружи")
            let mut shuffled = available_data.to_vec();
            shuffled.shuffle(&mut rng);
            let shadow_train: Vec<String> = shuffled[..samples_per_shadow].to_vec();
            let shadow_out: Vec<String> = shuffled[samples_per_shadow..]
                .iter()
                .take(samples_per_shadow) // Равный размер
                .cloned()
                .collect();

            training_sets.push(serde_json::json!({
                "train": shadow_train,
                "out": shadow_out
            }));
        }

        training_sets
    }

    fn train_shadows(&mut self, training_sets: &[serde_json::Value]) {
        /// Обучение теневых моделей.
        for dataset in training_sets {
            let mut shadow = self.create_model();
            let train_data: Vec<String> = dataset["train"].as_array().unwrap()
                .iter().filter_map(|v| v.as_str().map(String::from)).collect();
            shadow.train(&train_data);

            self.shadows.push(ShadowData {
                model: shadow,
                train_set: train_data.into_iter().collect(),
                out_set: dataset["out"].as_array().unwrap()
                    .iter().filter_map(|v| v.as_str().map(String::from)).collect(),
            });
        }
    }

    fn train_attack_classifier(&mut self) {
        /// Обучение классификатора для предсказания членства по признакам.
        let mut x: Vec<Vec<f64>> = Vec::new();
        let mut y: Vec<u8> = Vec::new();

        for shadow_data in &self.shadows {
            // Признаки для образцов "внутри"
            for sample in &shadow_data.train_set {
                let features = self.extract_features(&shadow_data.model, sample);
                x.push(features);
                y.push(1); // Член
            }

            // Признаки для образцов "снаружи"
            for sample in &shadow_data.out_set {
                let features = self.extract_features(&shadow_data.model, sample);
                x.push(features);
                y.push(0); // Не член
            }
        }

        let classifier = RandomForestClassifier::new(100);
        classifier.fit(&x, &y);
        self.membership_classifier = Some(Box::new(classifier));
    }

    fn extract_features(&self, model: &dyn LLMModel, sample: &str) -> Vec<f64> {
        /// Извлечение признаков предсказания для образца.
        let response = model.generate_with_logits(sample);

        vec![
            response.perplexity,
            response.logprobs.iter().sum::<f64>() / response.logprobs.len() as f64,
            std_dev(&response.logprobs),
            response.logprobs.iter().cloned().fold(f64::MAX, f64::min),
            self.entropy(&response.logits),
        ]
    }
}
```

---

## Обнаружение попыток атак на членство

```rust
use chrono::Utc;
use regex::Regex;

struct MembershipInferenceDetector {
    /// Обнаружение потенциальных атак на членство.
    query_history: Vec<serde_json::Value>,
    suspicious_patterns: Vec<String>,
}

impl MembershipInferenceDetector {
    fn new() -> Self {
        Self {
            query_history: Vec::new(),
            suspicious_patterns: Vec::new(),
        }
    }

    fn analyze_query(&mut self, query: &str, _response_meta: &serde_json::Value) -> serde_json::Value {
        /// Анализ запроса на паттерны атаки членства.
        let mut indicators = Vec::new();

        // 1. Запросы точного текста (попытка получить перплексию)
        if self.is_exact_text_query(query) {
            indicators.push("exact_text_query");
        }

        // 2. Повторяющиеся похожие запросы
        let similar_past = self.find_similar_queries(query);
        if similar_past > 3 {
            indicators.push("repeated_similar_queries");
        }

        // 3. Запросы уверенности/вероятности
        if self.asks_for_confidence(query) {
            indicators.push("confidence_request");
        }

        // 4. Систематический паттерн зондирования
        if self.is_systematic_probe(query) {
            indicators.push("systematic_probing");
        }

        let risk_score = indicators.len() as f64 / 4.0;

        self.query_history.push(serde_json::json!({
            "query": &query[..query.len().min(100)], // Усечение для хранения
            "timestamp": Utc::now().to_rfc3339(),
            "indicators": indicators
        }));

        serde_json::json!({
            "is_suspicious": risk_score > 0.25,
            "risk_score": risk_score,
            "indicators": indicators
        })
    }

    fn is_exact_text_query(&self, query: &str) -> bool {
        /// Проверка, является ли запрос зондом точного обучающего образца.
        let re = Regex::new(r#"^["'"].*["'"]$"#).unwrap();
        re.is_match(query.trim())
    }

    fn asks_for_confidence(&self, query: &str) -> bool {
        /// Проверка, спрашивает ли запрос уверенность модели.
        let confidence_keywords = vec![
            "уверенность", "вероятность", "правдоподобие", "уверен",
            "насколько точно", "перплексия", "logprob",
            "confidence", "probability", "likelihood",
        ];
        let query_lower = query.to_lowercase();
        confidence_keywords.iter().any(|kw| query_lower.contains(kw))
    }
}
```

---

## Стратегии митигации

### 1. Дифференциальная приватность

```rust
use ndarray::Array1;
use rand::distributions::{Distribution, Standard};

struct DPModelWrapper {
    /// Обёртка, добавляющая дифференциальную приватность к выводам модели.
    model: Box<dyn LLMModel>,
    epsilon: f64,
}

impl DPModelWrapper {
    fn new(model: Box<dyn LLMModel>, epsilon: f64) -> Self {
        Self { model, epsilon }
    }

    fn generate(&self, prompt: &str) -> String {
        /// Генерация с DP-шумом на вероятностях вывода.

        // Получаем сырые логиты
        let logits = self.model.get_logits(prompt);

        // Добавляем лапласовский шум для DP
        let mut rng = rand::thread_rng();
        let scale = 1.0 / self.epsilon;
        let noised_logits: Vec<f64> = logits
            .iter()
            .map(|&l| {
                let u: f64 = rng.gen::<f64>() - 0.5;
                l + -scale * u.signum() * (1.0 - 2.0 * u.abs()).ln()
            })
            .collect();

        // Сэмплируем из зашумлённого распределения
        self.sample_from_logits(&noised_logits)
    }
}
```

### 2. Маскирование уверенности

```rust
use rand::Rng;

fn mask_confidence(response: &serde_json::Value, threshold: f64) -> serde_json::Value {
    /// Маскирование сигналов высокой уверенности, утекающих членство.
    let mut masked = response.clone();

    // Не возвращаем точные вероятности
    if let Some(top_p) = masked.get("top_p").and_then(|v| v.as_f64()) {
        masked["top_p"] = serde_json::json!(
            if top_p > threshold { "high" } else { "normal" }
        );
    }

    // Добавляем шум к перплексии
    if let Some(ppl) = masked.get("perplexity").and_then(|v| v.as_f64()) {
        let mut rng = rand::thread_rng();
        let noise = rng.gen_range(-0.1..0.1) * ppl;
        masked["perplexity"] = serde_json::json!(((ppl + noise) * 10.0).round() / 10.0);
    }

    masked
}
```

### 3. Интеграция с SENTINEL

```rust
use sentinel_core::engines::{configure, scan};

configure(serde_json::json!({
    "membership_inference_protection": true,
    "confidence_masking": true,
    "query_pattern_detection": true,
}));

let result = scan(
    &query,
    serde_json::json!({
        "detect_membership_inference": true,
    }),
);

if result.membership_inference_detected {
    return masked_response(&response);
}
```

---

## Ключевые выводы

1. **Модели утекают членство обучающих данных** через уверенность
2. **Теневые модели** калибруют точность атаки
3. **Дифференциальная приватность** — самая сильная защита
4. **Маскируйте сигналы уверенности** в продакшене
5. **Мониторьте систематическое зондирование**

---

*AI Security Academy | Урок 03.3.2*
