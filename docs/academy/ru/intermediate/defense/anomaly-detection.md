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

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import numpy as np
from collections import deque
import threading

@dataclass
class StatisticalBaseline:
    """Статистический baseline для признака"""
    mean: float = 0.0
    std: float = 1.0
    min_val: float = float('-inf')
    max_val: float = float('inf')
    sample_count: int = 0
    
    def update(self, value: float, alpha: float = 0.01):
        """Обновить baseline экспоненциальным скользящим средним"""
        if self.sample_count == 0:
            self.mean = value
            self.std = 1.0
        else:
            delta = value - self.mean
            self.mean += alpha * delta
            self.std = np.sqrt((1 - alpha) * (self.std ** 2) + alpha * (delta ** 2))
        
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)
        self.sample_count += 1
    
    def get_z_score(self, value: float) -> float:
        """Рассчитать z-score для значения"""
        if self.std < 1e-10:
            return 0.0
        return (value - self.mean) / self.std

class ZScoreAnomalyDetector:
    """Статистическая детекция аномалий через z-scores"""
    
    def __init__(self, z_threshold: float = 3.0, window_size: int = 1000):
        self.z_threshold = z_threshold
        self.window_size = window_size
        self.baselines: Dict[str, StatisticalBaseline] = {}
        self.windows: Dict[str, deque] = {}
        self.lock = threading.RLock()
    
    def update_and_detect(self, feature_name: str, value: float) -> Dict:
        """Обновить baseline и детектировать аномалию"""
        with self.lock:
            if feature_name not in self.baselines:
                self.baselines[feature_name] = StatisticalBaseline()
                self.windows[feature_name] = deque(maxlen=self.window_size)
            
            baseline = self.baselines[feature_name]
            z_score = baseline.get_z_score(value)
            
            is_anomaly = abs(z_score) > self.z_threshold
            
            # Обновить baseline только не-аномальными значениями
            if not is_anomaly:
                baseline.update(value)
            
            self.windows[feature_name].append({
                'value': value,
                'z_score': z_score,
                'is_anomaly': is_anomaly
            })
            
            return {
                'feature': feature_name,
                'value': value,
                'z_score': z_score,
                'is_anomaly': is_anomaly,
                'threshold': self.z_threshold,
                'baseline_mean': baseline.mean,
                'baseline_std': baseline.std
            }
    
    def detect_multi(self, features: Dict[str, float]) -> Dict:
        """Детектировать аномалии по нескольким признакам"""
        results = {}
        anomaly_count = 0
        max_z = 0.0
        
        for name, value in features.items():
            result = self.update_and_detect(name, value)
            results[name] = result
            if result['is_anomaly']:
                anomaly_count += 1
            max_z = max(max_z, abs(result['z_score']))
        
        return {
            'features': results,
            'has_anomaly': anomaly_count > 0,
            'anomaly_count': anomaly_count,
            'max_z_score': max_z
        }
```

### 2.2 Isolation Forest детектор

```python
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

class IsolationForestDetector:
    """Детекция аномалий через Isolation Forest"""
    
    def __init__(self, contamination: float = 0.1, n_estimators: int = 100):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def train(self, data: np.ndarray, feature_names: List[str] = None):
        """Обучить на нормальных данных"""
        self.feature_names = feature_names or [f"f{i}" for i in range(data.shape[1])]
        
        scaled_data = self.scaler.fit_transform(data)
        self.model.fit(scaled_data)
        self.is_trained = True
    
    def detect(self, sample: np.ndarray) -> Dict:
        """Детектировать аномальность сэмпла"""
        if not self.is_trained:
            raise RuntimeError("Сначала обучите модель")
        
        if len(sample.shape) == 1:
            sample = sample.reshape(1, -1)
        
        scaled = self.scaler.transform(sample)
        
        prediction = self.model.predict(scaled)[0]
        score = self.model.decision_function(scaled)[0]
        
        is_anomaly = prediction == -1
        
        # Нормализовать score к 0-1 (выше = более аномально)
        anomaly_score = 1 - (score + 0.5)
        anomaly_score = max(0, min(1, anomaly_score))
        
        return {
            'is_anomaly': is_anomaly,
            'anomaly_score': anomaly_score,
            'raw_score': score,
            'threshold': 0.0
        }
```

---

## 3. Детекция на основе эмбеддингов

### 3.1 Embedding Distance детектор

```python
from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine

class EmbeddingAnomalyDetector:
    """Детекция аномалий в пространстве эмбеддингов"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2",
                 distance_threshold: float = 0.5):
        self.encoder = SentenceTransformer(model_name)
        self.distance_threshold = distance_threshold
        
        # Baseline эмбеддинги
        self.baseline_embeddings: np.ndarray = None
        self.centroid: np.ndarray = None
        self.max_distance: float = 0.0
    
    def train(self, normal_texts: List[str]):
        """Обучить на нормальных текстах"""
        self.baseline_embeddings = self.encoder.encode(normal_texts)
        self.centroid = np.mean(self.baseline_embeddings, axis=0)
        
        # Рассчитать max distance для нормализации
        distances = [
            cosine(emb, self.centroid) 
            for emb in self.baseline_embeddings
        ]
        self.max_distance = np.percentile(distances, 95)
    
    def detect(self, text: str) -> Dict:
        """Детектировать аномальность текста"""
        if self.centroid is None:
            raise RuntimeError("Сначала обучите детектор")
        
        embedding = self.encoder.encode([text])[0]
        
        # Расстояние до центроида
        dist_to_centroid = cosine(embedding, self.centroid)
        
        # Расстояние до ближайшего соседа
        distances_to_baseline = [
            cosine(embedding, base_emb) 
            for base_emb in self.baseline_embeddings
        ]
        min_distance = min(distances_to_baseline)
        
        # Нормализация scores
        centroid_score = dist_to_centroid / max(self.max_distance, 1e-6)
        centroid_score = min(centroid_score, 1.0)
        
        is_anomaly = (
            dist_to_centroid > self.distance_threshold or
            min_distance > self.distance_threshold * 0.8
        )
        
        return {
            'is_anomaly': is_anomaly,
            'distance_to_centroid': dist_to_centroid,
            'min_distance_to_baseline': min_distance,
            'anomaly_score': centroid_score,
            'threshold': self.distance_threshold
        }

class LocalOutlierFactorDetector:
    """LOF-based детекция аномалий"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2",
                 n_neighbors: int = 20):
        from sklearn.neighbors import LocalOutlierFactor
        
        self.encoder = SentenceTransformer(model_name)
        self.lof = LocalOutlierFactor(n_neighbors=n_neighbors, novelty=True)
        self.is_trained = False
    
    def train(self, normal_texts: List[str]):
        """Обучить на нормальных текстах"""
        embeddings = self.encoder.encode(normal_texts)
        self.lof.fit(embeddings)
        self.is_trained = True
    
    def detect(self, text: str) -> Dict:
        """Детектировать аномалию через LOF"""
        if not self.is_trained:
            raise RuntimeError("Сначала обучите")
        
        embedding = self.encoder.encode([text])
        prediction = self.lof.predict(embedding)[0]
        score = self.lof.decision_function(embedding)[0]
        
        is_anomaly = prediction == -1
        
        # Нормализация score
        anomaly_score = 1 - (score + 1) / 2
        anomaly_score = max(0, min(1, anomaly_score))
        
        return {
            'is_anomaly': is_anomaly,
            'anomaly_score': anomaly_score,
            'lof_score': score
        }
```

---

## 4. Real-time пайплайн детекции

### 4.1 Мульти-детекторный пайплайн

```python
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
import time

class BaseDetector(ABC):
    """Базовый интерфейс детектора"""
    
    @abstractmethod
    def detect(self, input_data: Any) -> Dict:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

class AnomalyDetectionPipeline:
    """Real-time мульти-детекторный пайплайн"""
    
    def __init__(self, detectors: List[BaseDetector] = None,
                 parallel: bool = True,
                 timeout_seconds: float = 1.0):
        self.detectors = detectors or []
        self.parallel = parallel
        self.timeout = timeout_seconds
        self.executor = ThreadPoolExecutor(max_workers=len(self.detectors) or 1)
        
        # Веса для комбинирования scores
        self.weights: Dict[str, float] = {}
    
    def add_detector(self, detector: BaseDetector, weight: float = 1.0):
        """Добавить детектор в пайплайн"""
        self.detectors.append(detector)
        self.weights[detector.name] = weight
    
    def detect(self, input_data: Any) -> Dict:
        """Запустить все детекторы и скомбинировать результаты"""
        start_time = time.time()
        
        if self.parallel:
            results = self._detect_parallel(input_data)
        else:
            results = self._detect_sequential(input_data)
        
        # Комбинировать результаты
        combined = self._combine_results(results)
        combined['detection_time_ms'] = (time.time() - start_time) * 1000
        
        return combined
    
    def _combine_results(self, results: Dict[str, Dict]) -> Dict:
        """Скомбинировать результаты детекторов"""
        any_anomaly = False
        weighted_score = 0.0
        total_weight = 0.0
        anomaly_sources = []
        
        for name, result in results.items():
            weight = self.weights.get(name, 1.0)
            
            if result.get('is_anomaly'):
                any_anomaly = True
                anomaly_sources.append(name)
            
            score = result.get('anomaly_score', 0.5 if result.get('is_anomaly') else 0.0)
            weighted_score += weight * score
            total_weight += weight
        
        combined_score = weighted_score / total_weight if total_weight > 0 else 0.0
        
        return {
            'is_anomaly': any_anomaly,
            'combined_score': combined_score,
            'anomaly_sources': anomaly_sources,
            'detector_results': results,
            'detector_count': len(self.detectors)
        }
```

---

## 5. Извлечение признаков ввода

### 5.1 Экстрактор текстовых признаков

```python
import re
from collections import Counter

class TextFeatureExtractor:
    """Извлечение признаков из текста для детекции аномалий"""
    
    def extract(self, text: str) -> Dict[str, float]:
        """Извлечь статистические признаки из текста"""
        features = {}
        
        # Признаки длины
        features['char_count'] = len(text)
        features['word_count'] = len(text.split())
        features['avg_word_length'] = (
            features['char_count'] / features['word_count']
            if features['word_count'] > 0 else 0
        )
        
        # Распределение символов
        features['uppercase_ratio'] = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        features['digit_ratio'] = sum(1 for c in text if c.isdigit()) / max(len(text), 1)
        features['special_ratio'] = sum(1 for c in text if not c.isalnum() and not c.isspace()) / max(len(text), 1)
        
        # Индикаторы инъекций
        injection_keywords = ['ignore', 'forget', 'override', 'system', 'prompt', 'instructions']
        features['injection_keyword_count'] = sum(
            1 for kw in injection_keywords if kw.lower() in text.lower()
        )
        
        # Unicode аномалии
        features['non_ascii_ratio'] = sum(1 for c in text if ord(c) > 127) / max(len(text), 1)
        
        # Повторения
        words = text.lower().split()
        if words:
            word_freq = Counter(words)
            most_common_freq = word_freq.most_common(1)[0][1]
            features['max_word_repetition'] = most_common_freq
            features['unique_word_ratio'] = len(word_freq) / len(words)
        else:
            features['max_word_repetition'] = 0
            features['unique_word_ratio'] = 0
        
        return features
```

---

## 6. Интеграция с SENTINEL

```python
class SENTINELAnomalyEngine:
    """Движок детекции аномалий для SENTINEL"""
    
    def __init__(self, config):
        self.config = config
        
        # Инициализация детекторов
        self.zscore = WrappedZScoreDetector(config.z_threshold)
        self.embedding = WrappedEmbeddingDetector(config.embedding_threshold)
        
        # Построить пайплайн
        self.pipeline = AnomalyDetectionPipeline(
            parallel=config.use_parallel,
            timeout_seconds=config.detection_timeout
        )
        self.pipeline.add_detector(self.zscore, weight=0.4)
        self.pipeline.add_detector(self.embedding, weight=0.6)
        
        self.is_trained = False
    
    def train(self, normal_texts: List[str]):
        """Обучить на нормальном корпусе"""
        self.embedding.train(normal_texts)
        self.is_trained = True
    
    def detect(self, text: str) -> Dict:
        """Детектировать аномалии в тексте"""
        if not self.is_trained:
            return self.zscore.detect(text)
        
        result = self.pipeline.detect(text)
        
        # Добавить рекомендацию действия
        if result['combined_score'] > 0.8:
            result['action'] = 'BLOCK'
        elif result['combined_score'] > 0.5:
            result['action'] = 'REVIEW'
        elif result['is_anomaly']:
            result['action'] = 'LOG'
        else:
            result['action'] = 'ALLOW'
        
        return result
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
