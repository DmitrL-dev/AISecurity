# Детекция аномалий для безопасности LLM

> **Уровень:** Продвинутый  
> **Время:** 50 минут  
> **Трек:** 05 — Стратегии защиты  
> **Модуль:** 05.1 — Детекция  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять типы аномалий в LLM системах
- [ ] Реализовать статистические и ML детекторы
- [ ] Построить real-time пайплайн детекции аномалий
- [ ] Интегрировать детекторы в SENTINEL

---

## 1. Обзор детекции аномалий

### 1.1 Типы аномалий

```
┌────────────────────────────────────────────────────────────────────┐
│              ТИПЫ АНОМАЛИЙ В LLM СИСТЕМАХ                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Аномалии ввода:                                                   │
│  ├── Необычная длина (слишком короткая/длинная)                   │
│  ├── Необычное распределение символов                             │
│  ├── Out-of-distribution эмбеддинги                               │
│  └── Подозрительные паттерны (кодировки, спецсимволы)            │
│                                                                    │
│  Поведенческие аномалии:                                           │
│  ├── Необычная частота запросов                                   │
│  ├── Аномальные паттерны использования инструментов               │
│  ├── Подозрительное поведение сессии                              │
│  └── Временные аномалии                                           │
│                                                                    │
│  Аномалии вывода:                                                  │
│  ├── Неожиданные паттерны ответов                                 │
│  ├── Индикаторы утечки информации                                 │
│  ├── Сигналы нарушения политик                                    │
│  └── Индикаторы успешного jailbreak                               │
│                                                                    │
│  Системные аномалии:                                               │
│  ├── Скачки латентности                                           │
│  ├── Аномалии использования ресурсов                              │
│  └── Изменения error rate                                         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Статистическая детекция аномалий

### 2.1 Z-Score детектор

```rust
use std::collections::{HashMap, VecDeque};
use std::sync::Mutex;

/// Статистический baseline для признака
struct StatisticalBaseline {
    mean: f64,
    std: f64,
    min_val: f64,
    max_val: f64,
    sample_count: usize,
}

impl StatisticalBaseline {
    fn new() -> Self {
        Self {
            mean: 0.0,
            std: 1.0,
            min_val: f64::NEG_INFINITY,
            max_val: f64::INFINITY,
            sample_count: 0,
        }
    }

    /// Обновить baseline экспоненциальным скользящим средним
    fn update(&mut self, value: f64, alpha: f64) {
        if self.sample_count == 0 {
            self.mean = value;
            self.std = 1.0;
        } else {
            let delta = value - self.mean;
            self.mean += alpha * delta;
            self.std = ((1.0 - alpha) * self.std.powi(2) + alpha * delta.powi(2)).sqrt();
        }
        self.min_val = self.min_val.min(value);
        self.max_val = self.max_val.max(value);
        self.sample_count += 1;
    }

    /// Рассчитать z-score для значения
    fn get_z_score(&self, value: f64) -> f64 {
        if self.std < 1e-10 {
            return 0.0;
        }
        (value - self.mean) / self.std
    }
}

/// Статистическая детекция аномалий через z-scores
struct ZScoreAnomalyDetector {
    z_threshold: f64,
    window_size: usize,
    baselines: Mutex<HashMap<String, StatisticalBaseline>>,
    windows: Mutex<HashMap<String, VecDeque<serde_json::Value>>>,
}

impl ZScoreAnomalyDetector {
    fn new(z_threshold: f64, window_size: usize) -> Self {
        Self {
            z_threshold,
            window_size,
            baselines: Mutex::new(HashMap::new()),
            windows: Mutex::new(HashMap::new()),
        }
    }

    /// Обновить baseline и детектировать аномалию
    fn update_and_detect(&self, feature_name: &str, value: f64) -> serde_json::Value {
        let mut baselines = self.baselines.lock().unwrap();
        let mut windows = self.windows.lock().unwrap();

        let baseline = baselines
            .entry(feature_name.to_string())
            .or_insert_with(StatisticalBaseline::new);
        windows
            .entry(feature_name.to_string())
            .or_insert_with(|| VecDeque::with_capacity(self.window_size));

        let z_score = baseline.get_z_score(value);
        let is_anomaly = z_score.abs() > self.z_threshold;

        // Обновить baseline только не-аномальными значениями
        if !is_anomaly {
            baseline.update(value, 0.01);
        }

        serde_json::json!({
            "feature": feature_name,
            "value": value,
            "z_score": z_score,
            "is_anomaly": is_anomaly,
            "threshold": self.z_threshold,
            "baseline_mean": baseline.mean,
            "baseline_std": baseline.std,
        })
    }

    /// Детектировать аномалии по нескольким признакам
    fn detect_multi(&self, features: &HashMap<String, f64>) -> serde_json::Value {
        let mut results = serde_json::Map::new();
        let mut anomaly_count = 0u32;
        let mut max_z = 0.0f64;

        for (name, value) in features.iter() {
            let result = self.update_and_detect(name, *value);
            if result["is_anomaly"].as_bool().unwrap_or(false) {
                anomaly_count += 1;
            }
            let z = result["z_score"].as_f64().unwrap_or(0.0).abs();
            max_z = max_z.max(z);
            results.insert(name.clone(), result);
        }

        serde_json::json!({
            "features": results,
            "has_anomaly": anomaly_count > 0,
            "anomaly_count": anomaly_count,
            "max_z_score": max_z,
        })
    }
}
```

### 2.2 Isolation Forest детектор

```rust
use smartcore::ensemble::random_forest_classifier::RandomForestClassifier;

/// Детекция аномалий через Isolation Forest
struct IsolationForestDetector {
    contamination: f64,
    is_trained: bool,
    feature_names: Vec<String>,
    // В Rust используем smartcore или linfa для ML
}

impl IsolationForestDetector {
    fn new(contamination: f64, _n_estimators: usize) -> Self {
        Self {
            contamination,
            is_trained: false,
            feature_names: Vec::new(),
        }
    }

    /// Обучить на нормальных данных
    fn train(&mut self, data: &[Vec<f64>], feature_names: Option<Vec<String>>) {
        let n_features = data.first().map(|r| r.len()).unwrap_or(0);
        self.feature_names = feature_names.unwrap_or_else(|| {
            (0..n_features).map(|i| format!("f{}", i)).collect()
        });
        // model.fit(scaled_data)
        self.is_trained = true;
    }

    /// Детектировать аномальность сэмпла
    fn detect(&self, sample: &[f64]) -> Result<serde_json::Value, String> {
        if !self.is_trained {
            return Err("Сначала обучите модель".into());
        }

        // Нормализовать score к 0-1 (выше = более аномально)
        let score: f64 = 0.0; // model.decision_function(scaled)
        let is_anomaly = score < 0.0;
        let anomaly_score = (1.0 - (score + 0.5)).clamp(0.0, 1.0);

        Ok(serde_json::json!({
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "raw_score": score,
            "threshold": 0.0,
        }))
    }
}
```

---

## 3. Детекция на основе эмбеддингов

### 3.1 Embedding Distance детектор

```rust
/// Детекция аномалий в пространстве эмбеддингов
struct EmbeddingAnomalyDetector {
    distance_threshold: f64,
    baseline_embeddings: Option<Vec<Vec<f64>>>,
    centroid: Option<Vec<f64>>,
    max_distance: f64,
}

impl EmbeddingAnomalyDetector {
    fn new(distance_threshold: f64) -> Self {
        Self {
            distance_threshold,
            baseline_embeddings: None,
            centroid: None,
            max_distance: 0.0,
        }
    }

    /// Обучить на нормальных текстах
    fn train(&mut self, normal_texts: &[String]) {
        let embeddings = self.encode_batch(normal_texts);
        let centroid = Self::compute_centroid(&embeddings);

        // Рассчитать max distance для нормализации
        let mut distances: Vec<f64> = embeddings
            .iter()
            .map(|emb| Self::cosine_distance(emb, &centroid))
            .collect();
        distances.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let p95_idx = (distances.len() as f64 * 0.95) as usize;
        self.max_distance = distances[p95_idx.min(distances.len() - 1)];
        self.centroid = Some(centroid);
        self.baseline_embeddings = Some(embeddings);
    }

    /// Детектировать аномальность текста
    fn detect(&self, text: &str) -> Result<serde_json::Value, String> {
        let centroid = self.centroid.as_ref()
            .ok_or("Сначала обучите детектор")?;
        let baselines = self.baseline_embeddings.as_ref().unwrap();
        let embedding = self.encode(text);

        // Расстояние до центроида
        let dist_to_centroid = Self::cosine_distance(&embedding, centroid);

        // Расстояние до ближайшего соседа
        let min_distance = baselines.iter()
            .map(|base| Self::cosine_distance(&embedding, base))
            .fold(f64::INFINITY, f64::min);

        // Нормализация scores
        let centroid_score = (dist_to_centroid / self.max_distance.max(1e-6)).min(1.0);

        let is_anomaly = dist_to_centroid > self.distance_threshold
            || min_distance > self.distance_threshold * 0.8;

        Ok(serde_json::json!({
            "is_anomaly": is_anomaly,
            "distance_to_centroid": dist_to_centroid,
            "min_distance_to_baseline": min_distance,
            "anomaly_score": centroid_score,
            "threshold": self.distance_threshold,
        }))
    }

    fn cosine_distance(a: &[f64], b: &[f64]) -> f64 { /* ... */ 0.0 }
    fn compute_centroid(vecs: &[Vec<f64>]) -> Vec<f64> { /* ... */ vec![] }
    fn encode(&self, _text: &str) -> Vec<f64> { vec![] }
    fn encode_batch(&self, _texts: &[String]) -> Vec<Vec<f64>> { vec![] }
}

/// LOF-based детекция аномалий
struct LocalOutlierFactorDetector {
    n_neighbors: usize,
    is_trained: bool,
}

impl LocalOutlierFactorDetector {
    fn new(n_neighbors: usize) -> Self {
        Self { n_neighbors, is_trained: false }
    }

    /// Обучить на нормальных текстах
    fn train(&mut self, _normal_texts: &[String]) {
        // lof.fit(embeddings)
        self.is_trained = true;
    }

    /// Детектировать аномалию через LOF
    fn detect(&self, _text: &str) -> Result<serde_json::Value, String> {
        if !self.is_trained {
            return Err("Сначала обучите".into());
        }

        let score: f64 = 0.0; // lof.decision_function(embedding)
        let is_anomaly = score < 0.0;

        // Нормализация score
        let anomaly_score = (1.0 - (score + 1.0) / 2.0).clamp(0.0, 1.0);

        Ok(serde_json::json!({
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "lof_score": score,
        }))
    }
}
```

---

## 4. Real-time пайплайн детекции

### 4.1 Мульти-детекторный пайплайн

```rust
use std::collections::HashMap;
use std::time::Instant;

/// Базовый интерфейс детектора
trait BaseDetector: Send + Sync {
    fn detect(&self, input_data: &str) -> serde_json::Value;
    fn name(&self) -> &str;
}

/// Real-time мульти-детекторный пайплайн
struct AnomalyDetectionPipeline {
    detectors: Vec<Box<dyn BaseDetector>>,
    parallel: bool,
    timeout_ms: u64,
    weights: HashMap<String, f64>,
}

impl AnomalyDetectionPipeline {
    fn new(parallel: bool, timeout_seconds: f64) -> Self {
        Self {
            detectors: Vec::new(),
            parallel,
            timeout_ms: (timeout_seconds * 1000.0) as u64,
            weights: HashMap::new(),
        }
    }

    /// Добавить детектор в пайплайн
    fn add_detector(&mut self, detector: Box<dyn BaseDetector>, weight: f64) {
        self.weights.insert(detector.name().to_string(), weight);
        self.detectors.push(detector);
    }

    /// Запустить все детекторы и скомбинировать результаты
    fn detect(&self, input_data: &str) -> serde_json::Value {
        let start = Instant::now();

        let mut results = HashMap::new();
        for detector in self.detectors.iter() {
            let result = detector.detect(input_data);
            results.insert(detector.name().to_string(), result);
        }

        // Комбинировать результаты
        let mut combined = self.combine_results(&results);
        let elapsed_ms = start.elapsed().as_secs_f64() * 1000.0;
        combined["detection_time_ms"] = serde_json::json!(elapsed_ms);
        combined
    }

    /// Скомбинировать результаты детекторов
    fn combine_results(&self, results: &HashMap<String, serde_json::Value>) -> serde_json::Value {
        let mut any_anomaly = false;
        let mut weighted_score = 0.0;
        let mut total_weight = 0.0;
        let mut anomaly_sources = Vec::new();

        for (name, result) in results.iter() {
            let weight = self.weights.get(name).copied().unwrap_or(1.0);
            if result["is_anomaly"].as_bool().unwrap_or(false) {
                any_anomaly = true;
                anomaly_sources.push(name.clone());
            }
            let score = result["anomaly_score"].as_f64().unwrap_or(0.0);
            weighted_score += weight * score;
            total_weight += weight;
        }

        let combined_score = if total_weight > 0.0 {
            weighted_score / total_weight
        } else {
            0.0
        };

        serde_json::json!({
            "is_anomaly": any_anomaly,
            "combined_score": combined_score,
            "anomaly_sources": anomaly_sources,
            "detector_results": results,
            "detector_count": self.detectors.len(),
        })
    }
}
```

---

## 5. Извлечение признаков ввода

### 5.1 Экстрактор текстовых признаков

```rust
use std::collections::HashMap;
use regex::Regex;

/// Извлечение признаков из текста для детекции аномалий
struct TextFeatureExtractor;

impl TextFeatureExtractor {
    /// Извлечь статистические признаки из текста
    fn extract(&self, text: &str) -> HashMap<String, f64> {
        let mut features = HashMap::new();

        // Признаки длины
        let char_count = text.len() as f64;
        let words: Vec<&str> = text.split_whitespace().collect();
        let word_count = words.len() as f64;
        features.insert("char_count".into(), char_count);
        features.insert("word_count".into(), word_count);
        features.insert("avg_word_length".into(),
            if word_count > 0.0 { char_count / word_count } else { 0.0 });

        // Распределение символов
        let len = char_count.max(1.0);
        features.insert("uppercase_ratio".into(),
            text.chars().filter(|c| c.is_uppercase()).count() as f64 / len);
        features.insert("digit_ratio".into(),
            text.chars().filter(|c| c.is_ascii_digit()).count() as f64 / len);
        features.insert("special_ratio".into(),
            text.chars().filter(|c| !c.is_alphanumeric() && !c.is_whitespace()).count() as f64 / len);

        // Индикаторы инъекций
        let injection_keywords = ["ignore", "forget", "override", "system", "prompt", "instructions"];
        let lower = text.to_lowercase();
        let kw_count = injection_keywords.iter()
            .filter(|kw| lower.contains(*kw))
            .count();
        features.insert("injection_keyword_count".into(), kw_count as f64);

        // Unicode аномалии
        features.insert("non_ascii_ratio".into(),
            text.chars().filter(|c| *c as u32 > 127).count() as f64 / len);

        // Повторения
        let lower_words: Vec<String> = words.iter().map(|w| w.to_lowercase()).collect();
        if !lower_words.is_empty() {
            let mut freq: HashMap<&str, usize> = HashMap::new();
            for w in lower_words.iter() {
                *freq.entry(w.as_str()).or_insert(0) += 1;
            }
            let max_rep = freq.values().copied().max().unwrap_or(0);
            features.insert("max_word_repetition".into(), max_rep as f64);
            features.insert("unique_word_ratio".into(),
                freq.len() as f64 / lower_words.len() as f64);
        } else {
            features.insert("max_word_repetition".into(), 0.0);
            features.insert("unique_word_ratio".into(), 0.0);
        }

        features
    }
}
```

---

## 6. Интеграция с SENTINEL

```rust
use sentinel_core::engines::SentinelEngine;

/// Движок детекции аномалий для SENTINEL
struct SENTINELAnomalyEngine {
    config: AnomalyDetectionConfig,
    zscore: WrappedZScoreDetector,
    embedding: WrappedEmbeddingDetector,
    pipeline: AnomalyDetectionPipeline,
    is_trained: bool,
}

impl SENTINELAnomalyEngine {
    fn new(config: AnomalyDetectionConfig) -> Self {
        let zscore = WrappedZScoreDetector::new(config.z_threshold);
        let embedding = WrappedEmbeddingDetector::new(config.embedding_threshold);

        // Построить пайплайн
        let mut pipeline = AnomalyDetectionPipeline::new(
            config.use_parallel,
            config.detection_timeout,
        );
        pipeline.add_detector(Box::new(zscore.clone()), 0.4);
        pipeline.add_detector(Box::new(embedding.clone()), 0.6);

        Self { config, zscore, embedding, pipeline, is_trained: false }
    }

    /// Обучить на нормальном корпусе
    fn train(&mut self, normal_texts: &[String]) {
        self.embedding.train(normal_texts);
        self.is_trained = true;
    }

    /// Детектировать аномалии в тексте
    fn detect(&self, text: &str) -> serde_json::Value {
        if !self.is_trained {
            return self.zscore.detect(text);
        }

        let mut result = self.pipeline.detect(text);

        // Добавить рекомендацию действия
        let score = result["combined_score"].as_f64().unwrap_or(0.0);
        let is_anomaly = result["is_anomaly"].as_bool().unwrap_or(false);
        let action = if score > 0.8 {
            "BLOCK"
        } else if score > 0.5 {
            "REVIEW"
        } else if is_anomaly {
            "LOG"
        } else {
            "ALLOW"
        };
        result["action"] = serde_json::json!(action);

        result
    }
}
```

---

## 7. Итоги

| Компонент | Описание |
|-----------|----------|
| **Z-Score** | Статистическая детекция по признакам |
| **Isolation Forest** | ML-based детекция выбросов |
| **Embedding** | Расстояние в пространстве эмбеддингов |
| **LOF** | Local Outlier Factor |
| **Pipeline** | Комбинация нескольких детекторов |
| **Feature Extractor** | Извлечение признаков текста/сессии |

---

## Следующий урок

→ [02. Behavioral Analysis](02-behavioral-analysis.md)

---

*AI Security Academy | Трек 05: Стратегии защиты | Модуль 05.1: Детекция*
