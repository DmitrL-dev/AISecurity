# Введение в TDA для детекции атак

> **Урок:** 06.2.1 - Introduction to Topological Data Analysis  
> **Время:** 45 минут  
> **Уровень:** Продвинутый

---

## Цели обучения

По завершении этого урока вы сможете:

1. Понимать основы TDA для безопасности
2. Применять persistent homology для детекции атак
3. Использовать топологические features для anomaly detection
4. Интегрировать TDA с SENTINEL engines

---

## Что такое Topological Data Analysis?

TDA анализирует «форму» данных, используя концепции алгебраической топологии:

| Концепция | Применение к безопасности |
|-----------|--------------------------|
| **Connected Components** | Разделение кластеров в эмбеддингах |
| **Holes/Loops** | Циклические паттерны в векторах атак |
| **Voids** | Отсутствующие регионы в нормальном поведении |
| **Persistent Homology** | Робастная экстракция features |

---

## Почему TDA для AI Security?

Традиционные ML метрики (distance, density) могут быть обмануты. TDA захватывает топологические инварианты:

```python
# Традиционно: Легко обмануть adversarial perturbations
euclidean_distance = np.linalg.norm(embedding_a - embedding_b)
# Малое возмущение > похожая distance > пропущенная атака

# TDA: Захватывает структурные свойства
topological_features = compute_persistent_homology(embedding_space)
# Структурная аномалия не меняется от малых возмущений
```

---

## Основы Persistent Homology

### Simplicial Complexes

Построение структуры из облака точек:

```python
import numpy as np
from ripser import ripser
from persim import plot_diagrams

def demonstrate_simplicial_complex(points: np.ndarray, epsilon: float):
    """
    Построение Vietoris-Rips complex из точек.
    
    1. Начинаем с точек (0-симплексы)
    2. Соединяем точки в пределах ? (1-симплексы/рёбра)
    3. Заполняем треугольники если все рёбра существуют (2-симплексы)
    4. Продолжаем для высших размерностей
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
    Расчёт persistent homology и возврат диаграммы.
    
    Каждая точка (birth, death) представляет топологический feature:
    - birth: масштаб, при котором feature появляется
    - death: масштаб, при котором feature исчезает
    - persistence = death - birth (значимость feature)
    """
    from ripser import ripser
    
    # Расчёт persistent homology до dimension 2
    result = ripser(embeddings, maxdim=2)
    
    return {
        "H0": result["dgms"][0],  # Connected components
        "H1": result["dgms"][1],  # Loops/holes
        "H2": result["dgms"][2] if len(result["dgms"]) > 2 else [],  # Voids
    }

def extract_topological_features(diagram: dict) -> dict:
    """Извлечение features из persistence diagram."""
    features = {}
    
    for dim, dgm in diagram.items():
        if len(dgm) == 0:
            features[f"{dim}_count"] = 0
            features[f"{dim}_max_persistence"] = 0
            features[f"{dim}_mean_persistence"] = 0
            continue
        
        # Фильтр бесконечных точек
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

### 1. Топология embedding space

```python
class TopologicalAnomalyDetector:
    """Детекция аномалий с использованием топологических features."""
    
    def __init__(self, embedding_model):
        self.embed = embedding_model
        self.baseline_topology = None
    
    def fit(self, normal_samples: list):
        """Обучение baseline топологии на нормальных сэмплах."""
        
        # Эмбеддинг сэмплов
        embeddings = np.array([self.embed(s) for s in normal_samples])
        
        # Расчёт persistent homology
        diagram = compute_persistence_diagram(embeddings)
        
        # Сохранение baseline features
        self.baseline_topology = extract_topological_features(diagram)
        
        # Также сохраняем для сравнения
        self.baseline_embeddings = embeddings
        self.baseline_diagram = diagram
    
    def detect(self, sample: str) -> dict:
        """Детекция топологически аномального сэмпла."""
        
        # Эмбеддинг сэмпла
        sample_emb = self.embed(sample).reshape(1, -1)
        
        # Комбинирование с baseline для анализа эффекта
        combined = np.vstack([self.baseline_embeddings, sample_emb])
        
        # Расчёт новой топологии
        new_diagram = compute_persistence_diagram(combined)
        new_features = extract_topological_features(new_diagram)
        
        # Сравнение с baseline
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
        """Расчёт distance между наборами топологических features."""
        
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
    """Анализ траекторий разговоров с использованием TDA."""
    
    def __init__(self, embedding_model):
        self.embed = embedding_model
    
    def analyze_conversation(self, turns: list) -> dict:
        """Анализ топологических свойств траектории разговора."""
        
        # Эмбеддинг каждого turn
        embeddings = np.array([self.embed(t["content"]) for t in turns])
        
        # Расчёт persistence
        diagram = compute_persistence_diagram(embeddings)
        features = extract_topological_features(diagram)
        
        # Специфические метрики траектории
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
        """Расчёт метрик, специфичных для траектории."""
        
        from scipy.spatial.distance import pdist, squareform
        distances = squareform(pdist(embeddings))
        
        # Distances между последовательными turn'ами
        consecutive = [distances[i, i+1] for i in range(len(embeddings)-1)]
        
        # Проверка "looping" поведения (близость к ранним turn'ам)
        loops = []
        for i in range(len(embeddings)):
            for j in range(i+2, len(embeddings)):
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
        
        # Много H1 features = циклический разговор
        h1_count = len([p for p in diagram["H1"] if p[1] != np.inf])
        if h1_count >= 3:
            patterns.append({
                "type": "circular_conversation",
                "evidence": f"{h1_count} loops detected"
            })
        
        # Высокая persistence в H1 = значительные loops
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
    """Использование TDA для анализа кластеров промптов на паттерны атак."""
    
    def __init__(self, embedding_model, attack_examples: list, benign_examples: list):
        self.embed = embedding_model
        
        # Эмбеддинг известных примеров
        self.attack_embeddings = np.array([self.embed(p) for p in attack_examples])
        self.benign_embeddings = np.array([self.embed(p) for p in benign_examples])
        
        # Расчёт baseline топологий
        self.attack_topology = compute_persistence_diagram(self.attack_embeddings)
        self.benign_topology = compute_persistence_diagram(self.benign_embeddings)
    
    def classify_prompt(self, prompt: str) -> dict:
        """Классификация промпта на основе топологического сходства."""
        
        prompt_emb = self.embed(prompt)
        
        # Добавление к каждому кластеру и расчёт изменения топологии
        with_attack = np.vstack([self.attack_embeddings, prompt_emb])
        with_benign = np.vstack([self.benign_embeddings, prompt_emb])
        
        attack_with_prompt = compute_persistence_diagram(with_attack)
        benign_with_prompt = compute_persistence_diagram(with_benign)
        
        # Измерение топологического disruption
        attack_disruption = self._compute_disruption(
            self.attack_topology, attack_with_prompt
        )
        benign_disruption = self._compute_disruption(
            self.benign_topology, benign_with_prompt
        )
        
        # Меньше disruption = лучше fit
        is_attack = attack_disruption < benign_disruption
        
        return {
            "classification": "attack" if is_attack else "benign",
            "attack_fit": 1 - attack_disruption,
            "benign_fit": 1 - benign_disruption,
            "confidence": abs(attack_disruption - benign_disruption)
        }
    
    def _compute_disruption(self, original: dict, with_new: dict) -> float:
        """Расчёт насколько добавление новой точки нарушает топологию."""
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

## Интеграция SENTINEL

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

1. **TDA захватывает форму** — Робастность к возмущениям
2. **Persistence имеет значение** — Долгоживущие features значимы
3. **Loops указывают на паттерны** — Циклические разговоры подозрительны
4. **Комбинируйте с ML** — TDA features усиливают классификаторы
5. **Интеграция SENTINEL** — Встроенная поддержка TDA engine

---

*AI Security Academy | Урок 06.2.1*
