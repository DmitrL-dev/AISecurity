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

```python
# Традиционный: Легко обмануть adversarial perturbations
euclidean_distance = np.linalg.norm(embedding_a - embedding_b)
# Маленькое возмущение → похожая дистанция → пропущенная атака

# TDA: Захватывает структурные свойства
topological_features = compute_persistent_homology(embedding_space)
# Структурная аномалия неизменна при малых возмущениях
```

---

## Основы Persistent Homology

### Simplicial Complexes

Построение структуры из point cloud:

```python
import numpy as np
from ripser import ripser
from persim import plot_diagrams

def demonstrate_simplicial_complex(points: np.ndarray, epsilon: float):
    """
    Построить Vietoris-Rips комплекс из точек.
    
    1. Начать с точек (0-симплексы)
    2. Соединить точки в пределах ε (1-симплексы/рёбра)
    3. Заполнить треугольники если все рёбра существуют (2-симплексы)
    4. Продолжить для более высоких размерностей
    """
    from scipy.spatial.distance import pdist, squareform
    
    distances = squareform(pdist(points))
    
    # 0-симплексы: все точки
    simplices_0 = list(range(len(points)))
    
    # 1-симплексы: рёбра где distance < epsilon
    simplices_1 = []
    for i in range(len(points)):
        for j in range(i+1, len(points)):
            if distances[i, j] < epsilon:
                simplices_1.append((i, j))
    
    # 2-симплексы: треугольники где все три ребра существуют
    simplices_2 = []
    edges_set = set(simplices_1)
    for i in range(len(points)):
        for j in range(i+1, len(points)):
            for k in range(j+1, len(points)):
                if ((i,j) in edges_set and 
                    (j,k) in edges_set and 
                    (i,k) in edges_set):
                    simplices_2.append((i, j, k))
    
    return {
        0: simplices_0,
        1: simplices_1,
        2: simplices_2
    }
```

### Persistence Diagrams

```python
def compute_persistence_diagram(embeddings: np.ndarray) -> dict:
    """
    Вычислить persistent homology и вернуть диаграмму.
    
    Каждая точка (birth, death) представляет топологическую feature:
    - birth: масштаб на котором feature появляется
    - death: масштаб на котором feature исчезает
    - persistence = death - birth (значимость feature)
    """
    from ripser import ripser
    
    # Вычислить persistent homology до размерности 2
    result = ripser(embeddings, maxdim=2)
    
    return {
        "H0": result["dgms"][0],  # Связные компоненты
        "H1": result["dgms"][1],  # Петли/дыры
        "H2": result["dgms"][2] if len(result["dgms"]) > 2 else [],  # Пустоты
    }

def extract_topological_features(diagram: dict) -> dict:
    """Извлечь features из persistence диаграммы."""
    features = {}
    
    for dim, dgm in diagram.items():
        if len(dgm) == 0:
            features[f"{dim}_count"] = 0
            features[f"{dim}_max_persistence"] = 0
            features[f"{dim}_mean_persistence"] = 0
            continue
        
        # Фильтровать бесконечные точки
        finite_dgm = dgm[dgm[:, 1] != np.inf]
        
        if len(finite_dgm) == 0:
            features[f"{dim}_count"] = 0
            features[f"{dim}_max_persistence"] = 0
            features[f"{dim}_mean_persistence"] = 0
            continue
        
        persistence = finite_dgm[:, 1] - finite_dgm[:, 0]
        
        features[f"{dim}_count"] = len(finite_dgm)
        features[f"{dim}_max_persistence"] = np.max(persistence)
        features[f"{dim}_mean_persistence"] = np.mean(persistence)
        features[f"{dim}_total_persistence"] = np.sum(persistence)
        features[f"{dim}_std_persistence"] = np.std(persistence)
    
    return features
```

---

## TDA для детекции атак

### 1. Топология Embedding Space

```python
class TopologicalAnomalyDetector:
    """Детекция аномалий используя топологические features."""
    
    def __init__(self, embedding_model):
        self.embed = embedding_model
        self.baseline_topology = None
    
    def fit(self, normal_samples: list):
        """Обучиться baseline топологии на нормальных samples."""
        
        # Embed samples
        embeddings = np.array([self.embed(s) for s in normal_samples])
        
        # Вычислить persistent homology
        diagram = compute_persistence_diagram(embeddings)
        
        # Сохранить baseline features
        self.baseline_topology = extract_topological_features(diagram)
        
        # Также сохранить для сравнения
        self.baseline_embeddings = embeddings
        self.baseline_diagram = diagram
    
    def detect(self, sample: str) -> dict:
        """Определить является ли sample топологически аномальным."""
        
        # Embed sample
        sample_emb = self.embed(sample).reshape(1, -1)
        
        # Объединить с baseline чтобы увидеть эффект
        combined = np.vstack([self.baseline_embeddings, sample_emb])
        
        # Вычислить новую топологию
        new_diagram = compute_persistence_diagram(combined)
        new_features = extract_topological_features(new_diagram)
        
        # Сравнить с baseline
        anomaly_score = self._compute_topological_distance(
            self.baseline_topology, 
            new_features
        )
        
        return {
            "is_anomaly": anomaly_score > self.threshold,
            "score": anomaly_score,
            "baseline_features": self.baseline_topology,
            "sample_features": new_features,
        }
    
    def _compute_topological_distance(self, f1: dict, f2: dict) -> float:
        """Вычислить дистанцию между наборами топологических features."""
        
        distance = 0
        for key in f1.keys():
            if key in f2:
                distance += abs(f1[key] - f2[key])
        
        return distance / len(f1)
```

---

### 2. Анализ траектории разговора

```python
class ConversationTopologyAnalyzer:
    """Анализ траекторий разговора используя TDA."""
    
    def __init__(self, embedding_model):
        self.embed = embedding_model
    
    def analyze_conversation(self, turns: list) -> dict:
        """Анализировать топологические свойства траектории разговора."""
        
        # Embed каждый turn
        embeddings = np.array([self.embed(t["content"]) for t in turns])
        
        # Вычислить persistence
        diagram = compute_persistence_diagram(embeddings)
        features = extract_topological_features(diagram)
        
        # Специфичные метрики разговора
        trajectory_metrics = self._compute_trajectory_metrics(embeddings)
        
        # Детекция подозрительных паттернов
        suspicious_patterns = self._detect_suspicious_topology(diagram)
        
        return {
            "topological_features": features,
            "trajectory_metrics": trajectory_metrics,
            "suspicious_patterns": suspicious_patterns,
            "is_suspicious": len(suspicious_patterns) > 0
        }
    
    def _compute_trajectory_metrics(self, embeddings: np.ndarray) -> dict:
        """Вычислить метрики специфичные для траектории."""
        
        # Вычислить попарные distances
        from scipy.spatial.distance import pdist, squareform
        distances = squareform(pdist(embeddings))
        
        # Distances последовательных turns
        consecutive = [distances[i, i+1] for i in range(len(embeddings)-1)]
        
        # Проверить на "looping" поведение (близость к ранним turns)
        loops = []
        for i in range(len(embeddings)):
            for j in range(i+2, len(embeddings)):  # Пропустить adjacent
                if distances[i, j] < 0.3 * np.mean(consecutive):
                    loops.append((i, j, distances[i, j]))
        
        return {
            "avg_step_distance": np.mean(consecutive),
            "max_step_distance": np.max(consecutive),
            "step_variance": np.var(consecutive),
            "loops_detected": len(loops),
            "loop_details": loops
        }
    
    def _detect_suspicious_topology(self, diagram: dict) -> list:
        """Детекция подозрительных топологических паттернов."""
        patterns = []
        
        # Много H1 features = циклический/looping разговор
        h1_count = len([p for p in diagram["H1"] if p[1] != np.inf])
        if h1_count >= 3:
            patterns.append({
                "type": "circular_conversation",
                "evidence": f"{h1_count} петель обнаружено"
            })
        
        # Высокая persistence в H1 = значимые петли
        if len(diagram["H1"]) > 0:
            max_h1_persistence = max(
                p[1] - p[0] for p in diagram["H1"] if p[1] != np.inf
            ) if any(p[1] != np.inf for p in diagram["H1"]) else 0
            
            if max_h1_persistence > 0.5:
                patterns.append({
                    "type": "significant_loop",
                    "persistence": max_h1_persistence
                })
        
        return patterns
```

---

### 3. Анализ кластеров промптов

```python
class PromptClusterAnalyzer:
    """Использовать TDA для анализа кластеров промптов на паттерны атак."""
    
    def __init__(self, embedding_model, attack_examples: list, benign_examples: list):
        self.embed = embedding_model
        
        # Embed известные примеры
        self.attack_embeddings = np.array([self.embed(p) for p in attack_examples])
        self.benign_embeddings = np.array([self.embed(p) for p in benign_examples])
        
        # Вычислить baseline топологии
        self.attack_topology = compute_persistence_diagram(self.attack_embeddings)
        self.benign_topology = compute_persistence_diagram(self.benign_embeddings)
    
    def classify_prompt(self, prompt: str) -> dict:
        """Классифицировать промпт на основе топологического сходства."""
        
        prompt_emb = self.embed(prompt)
        
        # Добавить к каждому кластеру и вычислить изменение топологии
        with_attack = np.vstack([self.attack_embeddings, prompt_emb])
        with_benign = np.vstack([self.benign_embeddings, prompt_emb])
        
        attack_with_prompt = compute_persistence_diagram(with_attack)
        benign_with_prompt = compute_persistence_diagram(with_benign)
        
        # Измерить топологическое disruption
        attack_disruption = self._compute_disruption(
            self.attack_topology, attack_with_prompt
        )
        benign_disruption = self._compute_disruption(
            self.benign_topology, benign_with_prompt
        )
        
        # Меньшее disruption = лучшее соответствие
        is_attack = attack_disruption < benign_disruption
        
        return {
            "classification": "attack" if is_attack else "benign",
            "attack_fit": 1 - attack_disruption,
            "benign_fit": 1 - benign_disruption,
            "confidence": abs(attack_disruption - benign_disruption)
        }
    
    def _compute_disruption(self, original: dict, with_new: dict) -> float:
        """Вычислить насколько добавление новой точки нарушает топологию."""
        from persim import wasserstein
        
        total_disruption = 0
        for dim in ["H0", "H1"]:
            if dim in original and dim in with_new:
                total_disruption += wasserstein(
                    original[dim], with_new[dim]
                )
        
        return total_disruption
```

---

## Интеграция с SENTINEL

```python
from sentinel import TDAEngine, configure

configure(
    tda_detection=True,
    persistence_threshold=0.3,
    dimension=2
)

tda_engine = TDAEngine(
    embedding_model="all-MiniLM-L6-v2",
    baseline_samples=normal_prompts
)

result = tda_engine.analyze(prompt)

if result.topological_anomaly:
    log_alert("Topological anomaly detected", result.features)
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
