# Введение в TDA для детекции атак

> **Урок:** 06.2.1 - Введение в Topological Data Analysis  
> **Время:** 45 минут  
> **Уровень:** Продвинутый

---

## Цели обучения

К концу этого урока вы сможете:

1. Понимать основы TDA для security
2. Применять persistent homology для детекции атак
3. Использовать топологические признаки для обнаружения аномалий
4. Интегрировать TDA с SENTINEL engines

---

## Что такое Topological Data Analysis?

TDA анализирует «форму» данных используя концепции из алгебраической топологии:

| Концепция | Применение к Security |
|-----------|----------------------|
| **Connected Components** | Разделение кластеров в эмбеддингах |
| **Holes/Loops** | Циклические паттерны в векторах атак |
| **Voids** | Отсутствующие регионы в нормальном поведении |
| **Persistent Homology** | Robust feature extraction |

---

## Зачем TDA для AI Security?

Традиционные ML метрики (distance, density) можно обмануть. TDA захватывает топологические инварианты:

```rust
// Традиционный: Легко обмануть adversarial perturbations
let euclidean_distance = (embedding_a - embedding_b).norm();
// Маленькое возмущение → похожая дистанция → пропущенная атака

// TDA: Захватывает структурные свойства
let topological_features = compute_persistent_homology(&embedding_space);
// Структурная аномалия неизменна при малых возмущениях
```

---

## Основы Persistent Homology

### Simplicial Complexes

Построение структуры из point cloud:

```rust
use ndarray::Array2;
use std::collections::{HashMap, HashSet};

fn demonstrate_simplicial_complex(points: &Array2<f64>, epsilon: f64) -> HashMap<usize, Vec<Vec<usize>>> {
    /// Построить Vietoris-Rips комплекс из точек.
    ///
    /// 1. Начать с точек (0-симплексы)
    /// 2. Соединить точки в пределах ε (1-симплексы/рёбра)
    /// 3. Заполнить треугольники если все рёбра существуют (2-симплексы)
    /// 4. Продолжить для более высоких размерностей

    let n = points.nrows();
    let distances = pairwise_distances(points);

    // 0-симплексы: все точки
    let simplices_0: Vec<Vec<usize>> = (0..n).map(|i| vec![i]).collect();

    // 1-симплексы: рёбра где distance < epsilon
    let mut simplices_1: Vec<Vec<usize>> = Vec::new();
    let mut edges_set: HashSet<(usize, usize)> = HashSet::new();
    for i in 0..n {
        for j in (i + 1)..n {
            if distances[[i, j]] < epsilon {
                simplices_1.push(vec![i, j]);
                edges_set.insert((i, j));
            }
        }
    }

    // 2-симплексы: треугольники где все три ребра существуют
    let mut simplices_2: Vec<Vec<usize>> = Vec::new();
    for i in 0..n {
        for j in (i + 1)..n {
            for k in (j + 1)..n {
                if edges_set.contains(&(i, j))
                    && edges_set.contains(&(j, k))
                    && edges_set.contains(&(i, k))
                {
                    simplices_2.push(vec![i, j, k]);
                }
            }
        }
    }

    let mut result = HashMap::new();
    result.insert(0, simplices_0);
    result.insert(1, simplices_1);
    result.insert(2, simplices_2);
    result
}
```

### Persistence Diagrams

```rust
use ndarray::Array2;
use std::collections::HashMap;

fn compute_persistence_diagram(embeddings: &Array2<f64>) -> HashMap<String, Vec<(f64, f64)>> {
    /// Вычислить persistent homology и вернуть диаграмму.
    ///
    /// Каждая точка (birth, death) представляет топологическую feature:
    /// - birth: масштаб на котором feature появляется
    /// - death: масштаб на котором feature исчезает
    /// - persistence = death - birth (значимость feature)

    // Вычислить persistent homology до размерности 2
    let result = ripser(embeddings, 2);

    let mut diagrams = HashMap::new();
    diagrams.insert("H0".to_string(), result.dgms[0].clone());  // Связные компоненты
    diagrams.insert("H1".to_string(), result.dgms[1].clone());  // Петли/дыры
    if result.dgms.len() > 2 {
        diagrams.insert("H2".to_string(), result.dgms[2].clone());  // Пустоты
    }
    diagrams
}

fn extract_topological_features(diagram: &HashMap<String, Vec<(f64, f64)>>) -> HashMap<String, f64> {
    /// Извлечь features из persistence диаграммы.
    let mut features = HashMap::new();

    for (dim, dgm) in diagram.iter() {
        if dgm.is_empty() {
            features.insert(format!("{}_count", dim), 0.0);
            features.insert(format!("{}_max_persistence", dim), 0.0);
            features.insert(format!("{}_mean_persistence", dim), 0.0);
            continue;
        }

        // Фильтровать бесконечные точки
        let finite_dgm: Vec<_> = dgm.iter()
            .filter(|(_, death)| death.is_finite())
            .collect();

        if finite_dgm.is_empty() {
            features.insert(format!("{}_count", dim), 0.0);
            features.insert(format!("{}_max_persistence", dim), 0.0);
            features.insert(format!("{}_mean_persistence", dim), 0.0);
            continue;
        }

        let persistence: Vec<f64> = finite_dgm.iter()
            .map(|(birth, death)| death - birth)
            .collect();

        let count = finite_dgm.len() as f64;
        let max_p = persistence.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let mean_p = persistence.iter().sum::<f64>() / count;
        let total_p = persistence.iter().sum::<f64>();
        let std_p = (persistence.iter().map(|p| (p - mean_p).powi(2)).sum::<f64>() / count).sqrt();

        features.insert(format!("{}_count", dim), count);
        features.insert(format!("{}_max_persistence", dim), max_p);
        features.insert(format!("{}_mean_persistence", dim), mean_p);
        features.insert(format!("{}_total_persistence", dim), total_p);
        features.insert(format!("{}_std_persistence", dim), std_p);
    }

    features
}
```

---

## TDA для детекции атак

### 1. Топология Embedding Space

```rust
use ndarray::Array2;
use std::collections::HashMap;

struct TopologicalAnomalyDetector {
    /// Детекция аномалий используя топологические features.
    embed: Box<dyn Fn(&str) -> Vec<f64>>,
    baseline_topology: Option<HashMap<String, f64>>,
    baseline_embeddings: Option<Array2<f64>>,
    baseline_diagram: Option<HashMap<String, Vec<(f64, f64)>>>,
    threshold: f64,
}

impl TopologicalAnomalyDetector {
    fn new(embedding_model: Box<dyn Fn(&str) -> Vec<f64>>) -> Self {
        Self {
            embed: embedding_model,
            baseline_topology: None,
            baseline_embeddings: None,
            baseline_diagram: None,
            threshold: 0.5,
        }
    }

    /// Обучиться baseline топологии на нормальных samples.
    fn fit(&mut self, normal_samples: &[&str]) {
        // Embed samples
        let embeddings = samples_to_array(normal_samples, &self.embed);

        // Вычислить persistent homology
        let diagram = compute_persistence_diagram(&embeddings);

        // Сохранить baseline features
        self.baseline_topology = Some(extract_topological_features(&diagram));

        // Также сохранить для сравнения
        self.baseline_embeddings = Some(embeddings);
        self.baseline_diagram = Some(diagram);
    }

    /// Определить является ли sample топологически аномальным.
    fn detect(&self, sample: &str) -> HashMap<String, serde_json::Value> {
        // Embed sample
        let sample_emb = (self.embed)(sample);

        // Объединить с baseline чтобы увидеть эффект
        let baseline = self.baseline_embeddings.as_ref().unwrap();
        let combined = vstack(baseline, &sample_emb);

        // Вычислить новую топологию
        let new_diagram = compute_persistence_diagram(&combined);
        let new_features = extract_topological_features(&new_diagram);

        // Сравнить с baseline
        let baseline_topo = self.baseline_topology.as_ref().unwrap();
        let anomaly_score = self.compute_topological_distance(baseline_topo, &new_features);

        let mut result = HashMap::new();
        result.insert("is_anomaly".into(), json!(anomaly_score > self.threshold));
        result.insert("score".into(), json!(anomaly_score));
        result
    }

    /// Вычислить дистанцию между наборами топологических features.
    fn compute_topological_distance(&self, f1: &HashMap<String, f64>, f2: &HashMap<String, f64>) -> f64 {
        let mut distance = 0.0;
        for (key, val) in f1.iter() {
            if let Some(val2) = f2.get(key) {
                distance += (val - val2).abs();
            }
        }
        distance / f1.len() as f64
    }
}
```

---

### 2. Анализ траектории разговора

```rust
use ndarray::Array2;
use std::collections::HashMap;

struct ConversationTopologyAnalyzer {
    /// Анализ траекторий разговора используя TDA.
    embed: Box<dyn Fn(&str) -> Vec<f64>>,
}

impl ConversationTopologyAnalyzer {
    fn new(embedding_model: Box<dyn Fn(&str) -> Vec<f64>>) -> Self {
        Self { embed: embedding_model }
    }

    /// Анализировать топологические свойства траектории разговора.
    fn analyze_conversation(&self, turns: &[HashMap<String, String>]) -> HashMap<String, serde_json::Value> {
        // Embed каждый turn
        let embeddings = turns_to_array(turns, &self.embed);

        // Вычислить persistence
        let diagram = compute_persistence_diagram(&embeddings);
        let features = extract_topological_features(&diagram);

        // Специфичные метрики разговора
        let trajectory_metrics = self.compute_trajectory_metrics(&embeddings);

        // Детекция подозрительных паттернов
        let suspicious_patterns = self.detect_suspicious_topology(&diagram);

        let mut result = HashMap::new();
        result.insert("topological_features".into(), json!(features));
        result.insert("trajectory_metrics".into(), json!(trajectory_metrics));
        result.insert("suspicious_patterns".into(), json!(&suspicious_patterns));
        result.insert("is_suspicious".into(), json!(!suspicious_patterns.is_empty()));
        result
    }

    /// Вычислить метрики специфичные для траектории.
    fn compute_trajectory_metrics(&self, embeddings: &Array2<f64>) -> HashMap<String, f64> {
        // Вычислить попарные distances
        let distances = pairwise_distances(embeddings);

        // Distances последовательных turns
        let consecutive: Vec<f64> = (0..embeddings.nrows() - 1)
            .map(|i| distances[[i, i + 1]])
            .collect();

        let mean_consec = consecutive.iter().sum::<f64>() / consecutive.len() as f64;

        // Проверить на "looping" поведение (близость к ранним turns)
        let mut loops = Vec::new();
        for i in 0..embeddings.nrows() {
            for j in (i + 2)..embeddings.nrows() {  // Пропустить adjacent
                if distances[[i, j]] < 0.3 * mean_consec {
                    loops.push((i, j, distances[[i, j]]));
                }
            }
        }

        let mut metrics = HashMap::new();
        metrics.insert("avg_step_distance".into(), mean_consec);
        metrics.insert("max_step_distance".into(), consecutive.iter().cloned().fold(f64::NEG_INFINITY, f64::max));
        metrics.insert("step_variance".into(), variance(&consecutive));
        metrics.insert("loops_detected".into(), loops.len() as f64);
        metrics
    }

    /// Детекция подозрительных топологических паттернов.
    fn detect_suspicious_topology(&self, diagram: &HashMap<String, Vec<(f64, f64)>>) -> Vec<HashMap<String, String>> {
        let mut patterns = Vec::new();

        // Много H1 features = циклический/looping разговор
        let h1 = diagram.get("H1").cloned().unwrap_or_default();
        let h1_count = h1.iter().filter(|(_, death)| death.is_finite()).count();
        if h1_count >= 3 {
            let mut p = HashMap::new();
            p.insert("type".into(), "circular_conversation".into());
            p.insert("evidence".into(), format!("{} петель обнаружено", h1_count));
            patterns.push(p);
        }

        // Высокая persistence в H1 = значимые петли
        if !h1.is_empty() {
            let max_h1_persistence = h1.iter()
                .filter(|(_, death)| death.is_finite())
                .map(|(birth, death)| death - birth)
                .fold(0.0_f64, f64::max);

            if max_h1_persistence > 0.5 {
                let mut p = HashMap::new();
                p.insert("type".into(), "significant_loop".into());
                p.insert("persistence".into(), format!("{}", max_h1_persistence));
                patterns.push(p);
            }
        }

        patterns
    }
}
```

---

### 3. Анализ кластеров промптов

```rust
use ndarray::Array2;
use std::collections::HashMap;

struct PromptClusterAnalyzer {
    /// Использовать TDA для анализа кластеров промптов на паттерны атак.
    embed: Box<dyn Fn(&str) -> Vec<f64>>,
    attack_embeddings: Array2<f64>,
    benign_embeddings: Array2<f64>,
    attack_topology: HashMap<String, Vec<(f64, f64)>>,
    benign_topology: HashMap<String, Vec<(f64, f64)>>,
}

impl PromptClusterAnalyzer {
    fn new(
        embedding_model: Box<dyn Fn(&str) -> Vec<f64>>,
        attack_examples: &[&str],
        benign_examples: &[&str],
    ) -> Self {
        // Embed известные примеры
        let attack_embeddings = samples_to_array(attack_examples, &embedding_model);
        let benign_embeddings = samples_to_array(benign_examples, &embedding_model);

        // Вычислить baseline топологии
        let attack_topology = compute_persistence_diagram(&attack_embeddings);
        let benign_topology = compute_persistence_diagram(&benign_embeddings);

        Self {
            embed: embedding_model,
            attack_embeddings,
            benign_embeddings,
            attack_topology,
            benign_topology,
        }
    }

    /// Классифицировать промпт на основе топологического сходства.
    fn classify_prompt(&self, prompt: &str) -> HashMap<String, serde_json::Value> {
        let prompt_emb = (self.embed)(prompt);

        // Добавить к каждому кластеру и вычислить изменение топологии
        let with_attack = vstack(&self.attack_embeddings, &prompt_emb);
        let with_benign = vstack(&self.benign_embeddings, &prompt_emb);

        let attack_with_prompt = compute_persistence_diagram(&with_attack);
        let benign_with_prompt = compute_persistence_diagram(&with_benign);

        // Измерить топологическое disruption
        let attack_disruption = self.compute_disruption(&self.attack_topology, &attack_with_prompt);
        let benign_disruption = self.compute_disruption(&self.benign_topology, &benign_with_prompt);

        // Меньшее disruption = лучшее соответствие
        let is_attack = attack_disruption < benign_disruption;

        let mut result = HashMap::new();
        result.insert("classification".into(), json!(if is_attack { "attack" } else { "benign" }));
        result.insert("attack_fit".into(), json!(1.0 - attack_disruption));
        result.insert("benign_fit".into(), json!(1.0 - benign_disruption));
        result.insert("confidence".into(), json!((attack_disruption - benign_disruption).abs()));
        result
    }

    /// Вычислить насколько добавление новой точки нарушает топологию.
    fn compute_disruption(
        &self,
        original: &HashMap<String, Vec<(f64, f64)>>,
        with_new: &HashMap<String, Vec<(f64, f64)>>,
    ) -> f64 {
        let mut total_disruption = 0.0;
        for dim in &["H0", "H1"] {
            let dim_str = dim.to_string();
            if let (Some(orig), Some(new)) = (original.get(&dim_str), with_new.get(&dim_str)) {
                total_disruption += wasserstein_distance(orig, new);
            }
        }
        total_disruption
    }
}
```

---

## Интеграция с SENTINEL

```rust
use sentinel_core::engines::{TDAEngine, configure};

fn main() {
    configure(
        true,   // tda_detection
        0.3,    // persistence_threshold
        2,      // dimension
    );

    let tda_engine = TDAEngine::new(
        "all-MiniLM-L6-v2",
        &normal_prompts,
    );

    let result = tda_engine.analyze(&prompt);

    if result.topological_anomaly {
        log_alert("Topological anomaly detected", &result.features);
    }
}
```

---

## Ключевые выводы

1. **TDA захватывает форму** — Robust к возмущениям
2. **Persistence имеет значение** — Долгоживущие features значимы
3. **Петли указывают на паттерны** — Циклические разговоры подозрительны
4. **Комбинировать с ML** — TDA features улучшают классификаторы
5. **Интеграция с SENTINEL** — Встроенная поддержка TDA engine

---

*AI Security Academy | Урок 06.2.1*
