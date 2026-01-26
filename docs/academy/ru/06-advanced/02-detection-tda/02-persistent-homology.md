# Persistent Homology для детекции атак

> **Урок:** 06.2.2 — Persistent Homology  
> **Время:** 45 минут  
> **Требования:** Введение в TDA

---

## Цели обучения

После завершения этого урока вы сможете:

1. Понять основы persistent homology
2. Применять топологический анализ к embedding spaces
3. Детектировать атаки через топологические сигнатуры
4. Реализовать persistence-based anomaly detection

---

## Что такое Persistent Homology?

Persistent homology отслеживает топологические признаки (дыры, пустоты) на разных масштабах:

```
Scale 0: Отдельные точки (0-dim holes = компоненты)
Scale ε: Точки соединяются на расстоянии ε (1-dim holes = циклы)
Scale ∞: Все точки соединены (признаки исчезают)

Persistence = как долго признак выживает на разных масштабах
```

| Размерность | Признак | Применение в безопасности |
|-------------|---------|---------------------------|
| H₀ | Связные компоненты | Структура кластеров |
| H₁ | Циклы/петли | Циклические паттерны атак |
| H₂ | Пустоты | Сложные топологические аномалии |

---

## Базовая реализация

```python
import numpy as np
from ripser import ripser
from scipy.spatial.distance import pdist, squareform

class PersistenceAnalyzer:
    """Persistent homology для анализа безопасности."""
    
    def __init__(self, max_dimension: int = 1):
        self.max_dim = max_dimension
    
    def compute_persistence(self, points: np.ndarray) -> dict:
        """Вычисление persistence diagrams."""
        
        # Вычисление попарных расстояний
        distances = squareform(pdist(points))
        
        # Вычисление persistent homology
        result = ripser(distances, maxdim=self.max_dim, distance_matrix=True)
        
        diagrams = {}
        for dim in range(self.max_dim + 1):
            dgm = result['dgms'][dim]
            diagrams[f"H{dim}"] = {
                "birth": dgm[:, 0].tolist(),
                "death": dgm[:, 1].tolist(),
                "persistence": (dgm[:, 1] - dgm[:, 0]).tolist()
            }
        
        return diagrams
    
    def extract_features(self, diagrams: dict) -> np.ndarray:
        """Извлечение статистических признаков из persistence diagrams."""
        
        features = []
        
        for dim_name, dgm in diagrams.items():
            persistence = np.array(dgm["persistence"])
            
            if len(persistence) == 0:
                features.extend([0, 0, 0, 0, 0])
            else:
                features.extend([
                    len(persistence),          # Количество признаков
                    np.mean(persistence),      # Средняя persistence
                    np.max(persistence),       # Максимальная persistence
                    np.std(persistence),       # Std persistence
                    np.sum(persistence),       # Общая persistence
                ])
        
        return np.array(features)
```

---

## Топология Embedding Space

```python
class EmbeddingTopologyAnalyzer:
    """Анализ топологии embedding space для безопасности."""
    
    def __init__(self, embedding_model):
        self.embed = embedding_model
        self.persistence = PersistenceAnalyzer(max_dimension=1)
        
        # Baseline топология
        self.baseline_features = None
    
    def fit_baseline(self, normal_texts: list):
        """Установление baseline топологии из нормальных входов."""
        
        embeddings = np.array([self.embed(t) for t in normal_texts])
        
        diagrams = self.persistence.compute_persistence(embeddings)
        self.baseline_features = self.persistence.extract_features(diagrams)
    
    def detect_anomaly(self, texts: list, threshold: float = 2.0) -> dict:
        """Детекция топологических аномалий в наборе входов."""
        
        if len(texts) < 5:
            return {"error": "Нужно минимум 5 samples для топологии"}
        
        embeddings = np.array([self.embed(t) for t in texts])
        
        diagrams = self.persistence.compute_persistence(embeddings)
        features = self.persistence.extract_features(diagrams)
        
        # Сравнение с baseline
        if self.baseline_features is not None:
            deviation = np.linalg.norm(features - self.baseline_features)
            baseline_norm = np.linalg.norm(self.baseline_features)
            relative_deviation = deviation / (baseline_norm + 1e-8)
        else:
            relative_deviation = 0.0
        
        return {
            "diagrams": diagrams,
            "features": features.tolist(),
            "deviation": float(relative_deviation),
            "is_anomalous": relative_deviation > threshold
        }
```

---

## Детекция сигнатур атак

```python
class TopologicalAttackDetector:
    """Детекция атак через топологические сигнатуры."""
    
    def __init__(self, embedding_model):
        self.embed = embedding_model
        self.persistence = PersistenceAnalyzer(max_dimension=1)
        
        # Известные топологические сигнатуры атак
        self.attack_signatures = {}
    
    def learn_attack_signature(self, attack_type: str, examples: list):
        """Обучение топологической сигнатуры типа атаки."""
        
        embeddings = np.array([self.embed(ex) for ex in examples])
        diagrams = self.persistence.compute_persistence(embeddings)
        features = self.persistence.extract_features(diagrams)
        
        # Также вычисление variance для понимания spread сигнатуры
        if len(examples) > 10:
            # Bootstrap для оценки variance
            feature_samples = []
            for _ in range(10):
                indices = np.random.choice(len(examples), len(examples)//2)
                subset_emb = embeddings[indices]
                subset_dgm = self.persistence.compute_persistence(subset_emb)
                subset_feat = self.persistence.extract_features(subset_dgm)
                feature_samples.append(subset_feat)
            
            feature_std = np.std(feature_samples, axis=0)
        else:
            feature_std = np.ones_like(features)
        
        self.attack_signatures[attack_type] = {
            "mean": features,
            "std": feature_std
        }
    
    def detect(self, texts: list) -> dict:
        """Детекция соответствия текстов сигнатуре атаки."""
        
        if len(texts) < 5:
            return {"error": "Нужно минимум 5 samples"}
        
        embeddings = np.array([self.embed(t) for t in texts])
        diagrams = self.persistence.compute_persistence(embeddings)
        features = self.persistence.extract_features(diagrams)
        
        matches = []
        
        for attack_type, signature in self.attack_signatures.items():
            # Mahalanobis-подобное расстояние
            diff = features - signature["mean"]
            normalized_dist = np.sqrt(np.sum((diff / (signature["std"] + 1e-8))**2))
            
            # Меньше расстояние = ближе match
            match_score = 1 / (1 + normalized_dist)
            
            if match_score > 0.5:
                matches.append({
                    "attack_type": attack_type,
                    "match_score": float(match_score)
                })
        
        matches.sort(key=lambda x: -x["match_score"])
        
        return {
            "matches": matches,
            "top_match": matches[0] if matches else None,
            "is_attack": len(matches) > 0
        }
```

---

## Streaming детекция

```python
from collections import deque

class StreamingTopologyMonitor:
    """Мониторинг топологии embedding в реальном времени."""
    
    def __init__(self, embedding_model, window_size: int = 50):
        self.embed = embedding_model
        self.persistence = PersistenceAnalyzer()
        self.window_size = window_size
        
        self.embedding_window = deque(maxlen=window_size)
        self.feature_history = deque(maxlen=100)
        
        self.baseline_mean = None
        self.baseline_std = None
    
    def add_sample(self, text: str) -> dict:
        """Добавление sample и проверка изменений топологии."""
        
        embedding = self.embed(text)
        self.embedding_window.append(embedding)
        
        if len(self.embedding_window) < 10:
            return {"status": "warming_up"}
        
        # Вычисление текущей топологии
        embeddings = np.array(list(self.embedding_window))
        diagrams = self.persistence.compute_persistence(embeddings)
        features = self.persistence.extract_features(diagrams)
        
        self.feature_history.append(features)
        
        # Обновление baseline (exponential moving average)
        if self.baseline_mean is None:
            self.baseline_mean = features
            self.baseline_std = np.ones_like(features)
        else:
            alpha = 0.1
            self.baseline_mean = alpha * features + (1 - alpha) * self.baseline_mean
            diff = features - self.baseline_mean
            self.baseline_std = alpha * np.abs(diff) + (1 - alpha) * self.baseline_std
        
        # Детекция отклонения
        z_score = np.abs(features - self.baseline_mean) / (self.baseline_std + 1e-8)
        max_z = np.max(z_score)
        
        return {
            "status": "normal" if max_z < 3.0 else "anomaly",
            "max_z_score": float(max_z),
            "current_features": features.tolist()
        }
```

---

## Визуализация

```python
import matplotlib.pyplot as plt

def plot_persistence_diagram(diagrams: dict, title: str = "Persistence Diagram"):
    """Визуализация persistence diagram."""
    
    fig, axes = plt.subplots(1, len(diagrams), figsize=(5*len(diagrams), 5))
    
    if len(diagrams) == 1:
        axes = [axes]
    
    for ax, (dim, dgm) in zip(axes, diagrams.items()):
        births = dgm["birth"]
        deaths = dgm["death"]
        
        # Отрисовка точек
        ax.scatter(births, deaths, alpha=0.6)
        
        # Диагональная линия
        max_val = max(max(deaths), 1)
        ax.plot([0, max_val], [0, max_val], 'k--', alpha=0.3)
        
        ax.set_xlabel("Birth")
        ax.set_ylabel("Death")
        ax.set_title(f"{dim}")
    
    plt.suptitle(title)
    plt.tight_layout()
    return fig
```

---

## Интеграция SENTINEL

```python
from sentinel import configure, TopologyGuard

configure(
    topological_analysis=True,
    persistence_detection=True,
    streaming_topology=True
)

topology_guard = TopologyGuard(
    embedding_model="all-MiniLM-L6-v2",
    window_size=50,
    anomaly_threshold=3.0
)

@topology_guard.monitor
def process_batch(texts: list):
    # Топология мониторится автоматически
    return [llm.generate(t) for t in texts]
```

---

## Ключевые выводы

1. **Топология захватывает структуру** — Выходит за рамки точечного анализа
2. **Persistence = важность** — Долгоживущие признаки имеют значение
3. **Изучай сигнатуры атак** — Каждый тип атаки имеет топологию
4. **Мониторь в реальном времени** — Детектируй изменения топологии
5. **Комбинируй с другими методами** — Часть defense-in-depth

---

*AI Security Academy | Урок 06.2.2*
