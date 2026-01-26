# TDA для Анализа Embeddings

> **Уровень:** �������  
> **Время:** 55 минут  
> **Трек:** 06 — Mathematical Foundations  
> **Модуль:** 06.1 — TDA (Topological Data Analysis)  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять топологические свойства embedding spaces
- [ ] Применять TDA методы к анализу LLM embeddings
- [ ] Интегрировать TDA-based detection в security pipeline
- [ ] Использовать persistence diagrams для сравнения распределений

---

## 1. Embeddings и Topology

### 1.1 Почему TDA для Embeddings?

LLM embeddings образуют сложные manifolds в высокоразмерном пространстве. TDA позволяет анализировать их структуру.

```
┌────────────────────────────────────────────────────────────────────┐
│              EMBEDDINGS КАК ТОПОЛОГИЧЕСКИЙ ОБЪЕКТ                   │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Text → [LLM Encoder] → Embedding ∈ ℝⁿ (n = 384, 768, 1536...)    │
│                                                                    │
│  Коллекция embeddings = Point Cloud в ℝⁿ                          │
│                                                                    │
│  TDA извлекает:                                                    │
│  ├── H₀: Связные компоненты (кластеры смыслов)                    │
│  ├── H₁: Циклы/дыры (семантические петли)                         │
│  └── H₂: Полости (сложные семантические структуры)                │
│                                                                    │
│  Применение к Security:                                            │
│  ├── Normal embeddings → стабильная топология                     │
│  ├── Attack embeddings → новые/изменённые features                │
│  └── Детекция = сравнение persistence diagrams                    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Метрики в Embedding Space

```python
import numpy as np
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics.pairwise import cosine_distances

class EmbeddingMetrics:
    """Различные метрики для embedding space"""
    
    @staticmethod
    def euclidean_distance_matrix(embeddings: np.ndarray) -> np.ndarray:
        """Стандартное евклидово расстояние"""
        return squareform(pdist(embeddings, metric='euclidean'))
    
    @staticmethod
    def cosine_distance_matrix(embeddings: np.ndarray) -> np.ndarray:
        """
        Косинусное расстояние — более подходит для embeddings,
        так как важны направления, а не magnitude.
        """
        return cosine_distances(embeddings)
    
    @staticmethod
    def normalized_euclidean(embeddings: np.ndarray) -> np.ndarray:
        """Евклидова метрика после L2 нормализации"""
        normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        return squareform(pdist(normalized, metric='euclidean'))
    
    @staticmethod
    def angular_distance(embeddings: np.ndarray) -> np.ndarray:
        """
        Угловое расстояние — arccos от косинусной близости.
        Метрика (удовлетворяет неравенству треугольника).
        """
        cos_sim = np.dot(embeddings, embeddings.T)
        norms = np.linalg.norm(embeddings, axis=1)
        cos_sim = cos_sim / np.outer(norms, norms)
        cos_sim = np.clip(cos_sim, -1, 1)  # Численная стабильность
        return np.arccos(cos_sim) / np.pi  # Нормализуем к [0, 1]
```

---

## 2. Persistence Homology для Embeddings

### 2.1 Vietoris-Rips Complex

```python
from ripser import ripser
from persim import plot_diagrams, wasserstein, bottleneck
import matplotlib.pyplot as plt

class EmbeddingPersistence:
    """
    Persistent Homology для анализа embedding space.
    Использует Vietoris-Rips filtration.
    """
    
    def __init__(self, max_dim: int = 1, max_edge_length: float = np.inf):
        """
        Args:
            max_dim: Максимальная размерность гомологий (0, 1, 2)
            max_edge_length: Максимальная длина ребра в фильтрации
        """
        self.max_dim = max_dim
        self.max_edge_length = max_edge_length
        self.diagrams = None
        self.distance_matrix = None
    
    def compute(self, embeddings: np.ndarray, 
                metric: str = 'cosine') -> dict:
        """
        Вычисляет persistent homology для embeddings.
        
        Args:
            embeddings: Матрица embeddings (n_samples, n_features)
            metric: 'euclidean', 'cosine', или 'angular'
        
        Returns:
            Словарь с diagrams и статистиками
        """
        # Вычисляем distance matrix
        if metric == 'euclidean':
            self.distance_matrix = EmbeddingMetrics.euclidean_distance_matrix(embeddings)
        elif metric == 'cosine':
            self.distance_matrix = EmbeddingMetrics.cosine_distance_matrix(embeddings)
        elif metric == 'angular':
            self.distance_matrix = EmbeddingMetrics.angular_distance(embeddings)
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        # Ripser для persistent homology
        result = ripser(
            self.distance_matrix,
            maxdim=self.max_dim,
            thresh=self.max_edge_length,
            distance_matrix=True
        )
        
        self.diagrams = result['dgms']
        
        return {
            'diagrams': self.diagrams,
            'h0_features': len(self.diagrams[0]),
            'h1_features': len(self.diagrams[1]) if self.max_dim >= 1 else 0,
            'statistics': self._compute_statistics()
        }
    
    def _compute_statistics(self) -> dict:
        """Вычисляет статистики persistence diagrams"""
        stats = {}
        
        for dim, dgm in enumerate(self.diagrams):
            if len(dgm) == 0:
                continue
            
            # Lifetime = death - birth
            lifetimes = dgm[:, 1] - dgm[:, 0]
            # Фильтруем inf
            finite_lifetimes = lifetimes[np.isfinite(lifetimes)]
            
            if len(finite_lifetimes) > 0:
                stats[f'H{dim}_count'] = len(dgm)
                stats[f'H{dim}_mean_lifetime'] = np.mean(finite_lifetimes)
                stats[f'H{dim}_max_lifetime'] = np.max(finite_lifetimes)
                stats[f'H{dim}_std_lifetime'] = np.std(finite_lifetimes)
                stats[f'H{dim}_total_persistence'] = np.sum(finite_lifetimes)
        
        return stats
    
    def get_persistent_features(self, min_persistence: float = 0.1) -> dict:
        """
        Возвращает только persistent features (с большим lifetime).
        
        Args:
            min_persistence: Минимальный lifetime для feature
        
        Returns:
            Устойчивые features по размерностям
        """
        persistent = {}
        
        for dim, dgm in enumerate(self.diagrams):
            lifetimes = dgm[:, 1] - dgm[:, 0]
            mask = (lifetimes >= min_persistence) & np.isfinite(lifetimes)
            persistent[f'H{dim}'] = dgm[mask]
        
        return persistent
    
    def plot(self, save_path: str = None):
        """Визуализация persistence diagrams"""
        if self.diagrams is None:
            raise ValueError("Call compute() first")
        
        fig, axes = plt.subplots(1, self.max_dim + 1, figsize=(5 * (self.max_dim + 1), 4))
        
        if self.max_dim == 0:
            axes = [axes]
        
        plot_diagrams(self.diagrams, ax=axes[0], show=False)
        
        for i, ax in enumerate(axes):
            ax.set_title(f'H{i} Persistence Diagram')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
        
        return fig
```

### 2.2 Сравнение Persistence Diagrams

```python
class PersistenceComparator:
    """
    Сравнение persistence diagrams для detection.
    Использует Wasserstein и Bottleneck distances.
    """
    
    def __init__(self):
        self.baseline_diagrams = None
    
    def set_baseline(self, diagrams: list):
        """Устанавливает baseline diagrams"""
        self.baseline_diagrams = diagrams
    
    def compare(self, target_diagrams: list) -> dict:
        """
        Сравнивает target diagrams с baseline.
        
        Args:
            target_diagrams: Diagrams для сравнения
        
        Returns:
            Distances по размерностям
        """
        if self.baseline_diagrams is None:
            raise ValueError("Set baseline first")
        
        results = {}
        
        for dim in range(min(len(self.baseline_diagrams), len(target_diagrams))):
            baseline_dgm = self.baseline_diagrams[dim]
            target_dgm = target_diagrams[dim]
            
            # Wasserstein distance (p=2)
            try:
                w_dist = wasserstein(baseline_dgm, target_dgm, matching=False)
            except:
                w_dist = float('inf')
            
            # Bottleneck distance
            try:
                b_dist = bottleneck(baseline_dgm, target_dgm, matching=False)
            except:
                b_dist = float('inf')
            
            results[f'H{dim}_wasserstein'] = w_dist
            results[f'H{dim}_bottleneck'] = b_dist
        
        return results
    
    def is_anomaly(self, target_diagrams: list, 
                   wasserstein_threshold: float = 0.5,
                   bottleneck_threshold: float = 0.3) -> dict:
        """
        Определяет, является ли target аномальным.
        
        Args:
            target_diagrams: Diagrams для проверки
            wasserstein_threshold: Порог по Wasserstein
            bottleneck_threshold: Порог по Bottleneck
        
        Returns:
            Результат anomaly detection
        """
        distances = self.compare(target_diagrams)
        
        anomalies = []
        for key, value in distances.items():
            if 'wasserstein' in key and value > wasserstein_threshold:
                anomalies.append({
                    'metric': key,
                    'value': value,
                    'threshold': wasserstein_threshold
                })
            elif 'bottleneck' in key and value > bottleneck_threshold:
                anomalies.append({
                    'metric': key,
                    'value': value,
                    'threshold': bottleneck_threshold
                })
        
        return {
            'is_anomaly': len(anomalies) > 0,
            'distances': distances,
            'violations': anomalies
        }
```

---

## 3. Topological Signatures для Текстов

### 3.1 Embedding Topology Signature

```python
from sentence_transformers import SentenceTransformer
from typing import List
import hashlib

class TopologicalSignature:
    """
    Топологическая сигнатура текстового корпуса.
    Используется для сравнения и детекции изменений.
    """
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.encoder = SentenceTransformer(embedding_model)
        self.persistence = EmbeddingPersistence(max_dim=1)
    
    def compute_signature(self, texts: List[str], 
                         metric: str = 'cosine') -> dict:
        """
        Вычисляет топологическую сигнатуру для текстов.
        
        Args:
            texts: Список текстов
            metric: Метрика для embeddings
        
        Returns:
            Топологическая сигнатура
        """
        # Embeddings
        embeddings = self.encoder.encode(texts)
        
        # Persistent homology
        result = self.persistence.compute(embeddings, metric=metric)
        
        # Извлекаем ключевые features
        signature = {
            'n_texts': len(texts),
            'embedding_dim': embeddings.shape[1],
            'metric': metric,
            
            # H0 features
            'h0_count': result['statistics'].get('H0_count', 0),
            'h0_mean_lifetime': result['statistics'].get('H0_mean_lifetime', 0),
            'h0_max_lifetime': result['statistics'].get('H0_max_lifetime', 0),
            
            # H1 features
            'h1_count': result['statistics'].get('H1_count', 0),
            'h1_mean_lifetime': result['statistics'].get('H1_mean_lifetime', 0),
            'h1_total_persistence': result['statistics'].get('H1_total_persistence', 0),
            
            # Diagrams
            'diagrams': result['diagrams']
        }
        
        # Signature hash
        signature['hash'] = self._compute_hash(signature)
        
        return signature
    
    def _compute_hash(self, signature: dict) -> str:
        """Вычисляет hash сигнатуры для быстрого сравнения"""
        key_values = [
            signature['h0_count'],
            round(signature['h0_mean_lifetime'], 3),
            signature['h1_count'],
            round(signature['h1_mean_lifetime'], 3)
        ]
        return hashlib.md5(str(key_values).encode()).hexdigest()[:16]
    
    def compare_signatures(self, sig1: dict, sig2: dict) -> dict:
        """
        Сравнивает две топологические сигнатуры.
        
        Args:
            sig1: Первая сигнатура
            sig2: Вторая сигнатура
        
        Returns:
            Результат сравнения
        """
        # Сравнение базовых statistics
        stat_diffs = {}
        for key in ['h0_count', 'h0_mean_lifetime', 'h1_count', 'h1_mean_lifetime']:
            diff = sig2.get(key, 0) - sig1.get(key, 0)
            rel_diff = diff / (sig1.get(key, 1) + 1e-10)
            stat_diffs[key] = {
                'absolute': diff,
                'relative': rel_diff
            }
        
        # Diagram distances
        comparator = PersistenceComparator()
        comparator.set_baseline(sig1['diagrams'])
        diagram_dists = comparator.compare(sig2['diagrams'])
        
        return {
            'hash_match': sig1['hash'] == sig2['hash'],
            'statistic_differences': stat_diffs,
            'diagram_distances': diagram_dists,
            'is_similar': self._assess_similarity(stat_diffs, diagram_dists)
        }
    
    def _assess_similarity(self, stat_diffs: dict, diagram_dists: dict) -> bool:
        """Оценивает общую похожесть сигнатур"""
        # Относительные изменения < 50%
        for key, diff in stat_diffs.items():
            if abs(diff['relative']) > 0.5:
                return False
        
        # Diagram distances разумные
        for key, dist in diagram_dists.items():
            if 'wasserstein' in key and dist > 0.5:
                return False
        
        return True
```

### 3.2 Sliding Window TDA

```python
class SlidingWindowTDA:
    """
    TDA анализ с sliding window для потоковых данных.
    Отслеживает изменения топологии во времени.
    """
    
    def __init__(self, 
                 window_size: int = 100,
                 step_size: int = 20,
                 embedding_model: str = "all-MiniLM-L6-v2"):
        self.window_size = window_size
        self.step_size = step_size
        self.encoder = SentenceTransformer(embedding_model)
        self.persistence = EmbeddingPersistence(max_dim=1)
        
        self.history = []
        self.current_window = []
    
    def add_text(self, text: str) -> dict:
        """
        Добавляет текст и обновляет анализ.
        
        Args:
            text: Новый текст
        
        Returns:
            Результат анализа окна (если достигнут step_size)
        """
        self.current_window.append(text)
        
        if len(self.current_window) >= self.window_size:
            # Анализируем окно
            result = self._analyze_window()
            
            # Сравниваем с предыдущим
            if self.history:
                change = self._detect_change(result)
                result['change_detected'] = change
            
            self.history.append(result)
            
            # Сдвигаем окно
            self.current_window = self.current_window[self.step_size:]
            
            return result
        
        return None
    
    def _analyze_window(self) -> dict:
        """Анализирует текущее окно"""
        embeddings = self.encoder.encode(self.current_window)
        result = self.persistence.compute(embeddings, metric='cosine')
        
        return {
            'window_start': len(self.history) * self.step_size,
            'window_texts': len(self.current_window),
            'statistics': result['statistics'],
            'diagrams': result['diagrams']
        }
    
    def _detect_change(self, current: dict) -> dict:
        """Обнаруживает изменения относительно предыдущего окна"""
        prev = self.history[-1]
        
        comparator = PersistenceComparator()
        comparator.set_baseline(prev['diagrams'])
        distances = comparator.compare(current['diagrams'])
        
        # Проверяем на аномалию
        anomaly = comparator.is_anomaly(
            current['diagrams'],
            wasserstein_threshold=0.3,
            bottleneck_threshold=0.2
        )
        
        return {
            'distances': distances,
            'is_anomaly': anomaly['is_anomaly'],
            'violations': anomaly['violations']
        }
    
    def get_trend(self) -> dict:
        """Возвращает тренд изменений топологии"""
        if len(self.history) < 2:
            return {'status': 'insufficient_data'}
        
        h0_counts = [h['statistics'].get('H0_count', 0) for h in self.history]
        h1_counts = [h['statistics'].get('H1_count', 0) for h in self.history]
        
        return {
            'n_windows': len(self.history),
            'h0_trend': np.polyfit(range(len(h0_counts)), h0_counts, 1)[0],
            'h1_trend': np.polyfit(range(len(h1_counts)), h1_counts, 1)[0],
            'h0_variance': np.var(h0_counts),
            'h1_variance': np.var(h1_counts)
        }
```

---

## 4. Security Applications

### 4.1 Injection Detection via TDA

```python
class TDAInjectionDetector:
    """
    Детектор prompt injection на основе TDA.
    Использует топологические изменения в embedding space.
    """
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.encoder = SentenceTransformer(embedding_model)
        self.persistence = EmbeddingPersistence(max_dim=1)
        self.comparator = PersistenceComparator()
        
        self.baseline_signature = None
        self.thresholds = {
            'wasserstein': 0.4,
            'bottleneck': 0.25,
            'h1_count_change': 3
        }
    
    def train(self, normal_texts: List[str]):
        """
        Обучение на нормальных данных.
        Строит baseline топологическую сигнатуру.
        """
        embeddings = self.encoder.encode(normal_texts)
        result = self.persistence.compute(embeddings, metric='cosine')
        
        self.baseline_signature = {
            'diagrams': result['diagrams'],
            'statistics': result['statistics'],
            'n_samples': len(normal_texts)
        }
        
        self.comparator.set_baseline(result['diagrams'])
    
    def detect(self, texts: List[str]) -> dict:
        """
        Детекция injection в текстах.
        
        Args:
            texts: Тексты для анализа
        
        Returns:
            Результат детекции
        """
        if self.baseline_signature is None:
            raise ValueError("Train the detector first")
        
        # Compute embeddings and persistence
        embeddings = self.encoder.encode(texts)
        result = self.persistence.compute(embeddings, metric='cosine')
        
        # Compare with baseline
        anomaly_check = self.comparator.is_anomaly(
            result['diagrams'],
            wasserstein_threshold=self.thresholds['wasserstein'],
            bottleneck_threshold=self.thresholds['bottleneck']
        )
        
        # Additional checks
        h1_baseline = self.baseline_signature['statistics'].get('H1_count', 0)
        h1_current = result['statistics'].get('H1_count', 0)
        h1_change = abs(h1_current - h1_baseline)
        
        # Aggregate detection
        is_injection = anomaly_check['is_anomaly'] or h1_change > self.thresholds['h1_count_change']
        
        # Confidence score
        confidence = self._compute_confidence(anomaly_check['distances'], h1_change)
        
        return {
            'is_injection': is_injection,
            'confidence': confidence,
            'distances': anomaly_check['distances'],
            'violations': anomaly_check['violations'],
            'h1_change': h1_change,
            'current_statistics': result['statistics'],
            'recommendation': self._get_recommendation(is_injection, confidence)
        }
    
    def _compute_confidence(self, distances: dict, h1_change: int) -> float:
        """Вычисляет confidence score"""
        score = 0.0
        
        # Wasserstein contribution
        w_h0 = distances.get('H0_wasserstein', 0)
        w_h1 = distances.get('H1_wasserstein', 0)
        score += min(w_h0 / self.thresholds['wasserstein'], 1.0) * 0.3
        score += min(w_h1 / self.thresholds['wasserstein'], 1.0) * 0.3
        
        # H1 change contribution
        score += min(h1_change / self.thresholds['h1_count_change'], 1.0) * 0.4
        
        return min(score, 1.0)
    
    def _get_recommendation(self, is_injection: bool, confidence: float) -> str:
        """Рекомендации на основе результата"""
        if not is_injection:
            return "SAFE: Топология соответствует baseline"
        elif confidence < 0.5:
            return "LOW_RISK: Небольшие топологические изменения"
        elif confidence < 0.8:
            return "MEDIUM_RISK: Значительные изменения, рекомендуется проверка"
        else:
            return "HIGH_RISK: Сильные топологические аномалии, возможна injection"
```

### 4.2 Multi-Modal TDA Detection

```python
class MultiModalTDADetector:
    """
    Multi-modal детектор, комбинирующий TDA features с другими методами.
    """
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.encoder = SentenceTransformer(embedding_model)
        self.tda_detector = TDAInjectionDetector(embedding_model)
        
        # Feature weights
        self.weights = {
            'tda': 0.4,
            'semantic': 0.3,
            'structural': 0.3
        }
    
    def train(self, normal_texts: List[str], attack_texts: List[str] = None):
        """
        Обучение на нормальных (и опционально атакующих) данных.
        """
        self.tda_detector.train(normal_texts)
        
        # Semantic baseline
        self.normal_embeddings = self.encoder.encode(normal_texts)
        self.normal_centroid = np.mean(self.normal_embeddings, axis=0)
        self.normal_radius = np.max(
            np.linalg.norm(self.normal_embeddings - self.normal_centroid, axis=1)
        )
        
        # Attack patterns (if provided)
        self.attack_embeddings = None
        if attack_texts:
            self.attack_embeddings = self.encoder.encode(attack_texts)
    
    def detect(self, texts: List[str]) -> dict:
        """
        Multi-modal детекция.
        
        Returns:
            Комбинированный результат детекции
        """
        embeddings = self.encoder.encode(texts)
        
        # 1. TDA Detection
        tda_result = self.tda_detector.detect(texts)
        tda_score = tda_result['confidence']
        
        # 2. Semantic Detection (distance from centroid)
        distances = np.linalg.norm(embeddings - self.normal_centroid, axis=1)
        outside_radius = np.mean(distances > self.normal_radius * 1.5)
        semantic_score = outside_radius
        
        # 3. Structural Detection (similarity to known attacks)
        structural_score = 0.0
        if self.attack_embeddings is not None:
            # Max similarity to any attack
            for emb in embeddings:
                sims = np.dot(self.attack_embeddings, emb) / (
                    np.linalg.norm(self.attack_embeddings, axis=1) * np.linalg.norm(emb)
                )
                structural_score = max(structural_score, np.max(sims))
        
        # Combined score
        combined_score = (
            self.weights['tda'] * tda_score +
            self.weights['semantic'] * semantic_score +
            self.weights['structural'] * structural_score
        )
        
        return {
            'is_attack': combined_score > 0.5,
            'combined_score': combined_score,
            'scores': {
                'tda': tda_score,
                'semantic': semantic_score,
                'structural': structural_score
            },
            'tda_details': tda_result,
            'recommendation': self._get_recommendation(combined_score)
        }
    
    def _get_recommendation(self, score: float) -> str:
        if score < 0.3:
            return "SAFE"
        elif score < 0.5:
            return "LOW_RISK: Monitor closely"
        elif score < 0.7:
            return "MEDIUM_RISK: Review required"
        else:
            return "HIGH_RISK: Block and investigate"
```

---

## 5. SENTINEL Integration

```python
from dataclasses import dataclass
from enum import Enum

class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class TDASecurityConfig:
    """Конфигурация TDA Security Engine"""
    embedding_model: str = "all-MiniLM-L6-v2"
    max_homology_dim: int = 1
    wasserstein_threshold: float = 0.4
    bottleneck_threshold: float = 0.25
    metric: str = "cosine"
    use_multimodal: bool = True

class SENTINELTDAEngine:
    """
    TDA Engine для SENTINEL framework.
    Обеспечивает топологический анализ для security detection.
    """
    
    def __init__(self, config: TDASecurityConfig):
        self.config = config
        
        if config.use_multimodal:
            self.detector = MultiModalTDADetector(config.embedding_model)
        else:
            self.detector = TDAInjectionDetector(config.embedding_model)
        
        self.signature_cache = {}
        self.is_trained = False
    
    def train(self, 
              normal_texts: List[str],
              attack_texts: List[str] = None,
              signature_name: str = "default"):
        """
        Обучение engine на данных.
        
        Args:
            normal_texts: Нормальные тексты
            attack_texts: Атакующие тексты (опционально)
            signature_name: Имя сигнатуры для кэширования
        """
        if self.config.use_multimodal:
            self.detector.train(normal_texts, attack_texts)
        else:
            self.detector.train(normal_texts)
        
        # Сохраняем сигнатуру
        sig_computer = TopologicalSignature(self.config.embedding_model)
        self.signature_cache[signature_name] = sig_computer.compute_signature(
            normal_texts, self.config.metric
        )
        
        self.is_trained = True
    
    def analyze(self, texts: List[str]) -> dict:
        """
        Анализ текстов.
        
        Returns:
            Полный результат анализа
        """
        if not self.is_trained:
            raise RuntimeError("Train the engine first")
        
        result = self.detector.detect(texts)
        
        # Determine risk level
        score = result.get('combined_score', result.get('confidence', 0))
        risk_level = self._determine_risk_level(score)
        
        return {
            'risk_level': risk_level.value,
            'is_attack': result.get('is_attack', result.get('is_injection', False)),
            'score': score,
            'details': result,
            'action': self._get_action(risk_level)
        }
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        if score < 0.2:
            return RiskLevel.SAFE
        elif score < 0.4:
            return RiskLevel.LOW
        elif score < 0.6:
            return RiskLevel.MEDIUM
        elif score < 0.8:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _get_action(self, risk_level: RiskLevel) -> str:
        actions = {
            RiskLevel.SAFE: "ALLOW",
            RiskLevel.LOW: "ALLOW_WITH_LOGGING",
            RiskLevel.MEDIUM: "REQUIRE_REVIEW",
            RiskLevel.HIGH: "BLOCK_PENDING_REVIEW",
            RiskLevel.CRITICAL: "BLOCK_AND_ALERT"
        }
        return actions.get(risk_level, "BLOCK")
```

---

## 6. Резюме

| Компонент | Описание |
|-----------|----------|
| **Persistence Homology** | Извлекает H₀, H₁ features из embedding space |
| **Wasserstein/Bottleneck** | Метрики сравнения persistence diagrams |
| **Topological Signature** | Компактное представление топологии корпуса |
| **Sliding Window TDA** | Отслеживание топологии в реальном времени |
| **Multi-Modal Detection** | Комбинирование TDA с семантикой и структурой |

---

## Следующий урок

→ [Track 07: Governance](../../07-governance/README.md)

---

*AI Security Academy | Track 06: Mathematical Foundations | Module 06.1: TDA*
