# Anomaly Detection for LLM Security

> **Level:** Advanced  
> **Time:** 50 minutes  
> **Track:** 05 — Defense Strategies  
> **Module:** 05.1 — Detection  
> **Version:** 1.0

---

## Learning Objectives

- [ ] Understand anomaly types in LLM systems
- [ ] Implement statistical and ML-based detectors
- [ ] Build real-time anomaly detection pipeline
- [ ] Integrate detectors into SENTINEL

---

## 1. Anomaly Detection Overview

### 1.1 Anomaly Types

```
┌────────────────────────────────────────────────────────────────────┐
│              ANOMALY TYPES IN LLM SYSTEMS                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Input Anomalies:                                                  │
│  ├── Unusual length (too short/long)                              │
│  ├── Unusual character distribution                               │
│  ├── Out-of-distribution embeddings                              │
│  └── Suspicious patterns (encoding, special chars)               │
│                                                                    │
│  Behavior Anomalies:                                               │
│  ├── Unusual request frequency                                    │
│  ├── Abnormal tool usage patterns                                │
│  ├── Suspicious session behavior                                 │
│  └── Time-based anomalies                                        │
│                                                                    │
│  Output Anomalies:                                                 │
│  ├── Unexpected response patterns                                │
│  ├── Information leakage indicators                              │
│  ├── Policy violation signals                                    │
│  └── Jailbreak success indicators                                │
│                                                                    │
│  System Anomalies:                                                 │
│  ├── Latency spikes                                              │
│  ├── Resource utilization anomalies                              │
│  └── Error rate changes                                          │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Statistical Anomaly Detection

### 2.1 Z-Score Detector

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import numpy as np
from collections import deque
import threading

@dataclass
class StatisticalBaseline:
    """Statistical baseline for feature"""
    mean: float = 0.0
    std: float = 1.0
    min_val: float = float('-inf')
    max_val: float = float('inf')
    sample_count: int = 0
    
    def update(self, value: float, alpha: float = 0.01):
        """Update baseline with exponential moving average"""
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
        """Calculate z-score for value"""
        if self.std < 1e-10:
            return 0.0
        return (value - self.mean) / self.std

class ZScoreAnomalyDetector:
    """Statistical anomaly detection using z-scores"""
    
    def __init__(self, z_threshold: float = 3.0, window_size: int = 1000):
        self.z_threshold = z_threshold
        self.window_size = window_size
        self.baselines: Dict[str, StatisticalBaseline] = {}
        self.windows: Dict[str, deque] = {}
        self.lock = threading.RLock()
    
    def update_and_detect(self, feature_name: str, value: float) -> Dict:
        """Update baseline and detect anomaly"""
        with self.lock:
            if feature_name not in self.baselines:
                self.baselines[feature_name] = StatisticalBaseline()
                self.windows[feature_name] = deque(maxlen=self.window_size)
            
            baseline = self.baselines[feature_name]
            z_score = baseline.get_z_score(value)
            
            is_anomaly = abs(z_score) > self.z_threshold
            
            # Update baseline with non-anomalous values
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
        """Detect anomalies across multiple features"""
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

### 2.2 Isolation Forest Detector

```python
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

class IsolationForestDetector:
    """Anomaly detection using Isolation Forest"""
    
    def __init__(self, contamination: float = 0.1, n_estimators: int = 100):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names: List[str] = []
    
    def train(self, data: np.ndarray, feature_names: List[str] = None):
        """Train on normal data"""
        self.feature_names = feature_names or [f"f{i}" for i in range(data.shape[1])]
        
        scaled_data = self.scaler.fit_transform(data)
        self.model.fit(scaled_data)
        self.is_trained = True
    
    def detect(self, sample: np.ndarray) -> Dict:
        """Detect if sample is anomalous"""
        if not self.is_trained:
            raise RuntimeError("Train the model first")
        
        if len(sample.shape) == 1:
            sample = sample.reshape(1, -1)
        
        scaled = self.scaler.transform(sample)
        
        prediction = self.model.predict(scaled)[0]
        score = self.model.decision_function(scaled)[0]
        
        is_anomaly = prediction == -1
        
        # Normalize score to 0-1 (higher = more anomalous)
        anomaly_score = 1 - (score + 0.5)  # Approximate normalization
        anomaly_score = max(0, min(1, anomaly_score))
        
        return {
            'is_anomaly': is_anomaly,
            'anomaly_score': anomaly_score,
            'raw_score': score,
            'threshold': 0.0  # Decision boundary
        }
    
    def detect_batch(self, samples: np.ndarray) -> List[Dict]:
        """Detect anomalies in batch"""
        return [self.detect(s) for s in samples]
```

---

## 3. Embedding-based Anomaly Detection

### 3.1 Embedding Distance Detector

```python
from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine, euclidean

class EmbeddingAnomalyDetector:
    """Anomaly detection based on embedding space"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2",
                 distance_threshold: float = 0.5):
        self.encoder = SentenceTransformer(model_name)
        self.distance_threshold = distance_threshold
        
        # Baseline embeddings
        self.baseline_embeddings: np.ndarray = None
        self.centroid: np.ndarray = None
        self.max_distance: float = 0.0
    
    def train(self, normal_texts: List[str]):
        """Train on normal text samples"""
        self.baseline_embeddings = self.encoder.encode(normal_texts)
        self.centroid = np.mean(self.baseline_embeddings, axis=0)
        
        # Calculate max distance for normalization
        distances = [
            cosine(emb, self.centroid) 
            for emb in self.baseline_embeddings
        ]
        self.max_distance = np.percentile(distances, 95)
    
    def detect(self, text: str) -> Dict:
        """Detect if text is anomalous"""
        if self.centroid is None:
            raise RuntimeError("Train the detector first")
        
        embedding = self.encoder.encode([text])[0]
        
        # Distance to centroid
        dist_to_centroid = cosine(embedding, self.centroid)
        
        # Distance to nearest neighbor
        distances_to_baseline = [
            cosine(embedding, base_emb) 
            for base_emb in self.baseline_embeddings
        ]
        min_distance = min(distances_to_baseline)
        
        # Normalize scores
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
    """LOF-based anomaly detection"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2",
                 n_neighbors: int = 20):
        from sklearn.neighbors import LocalOutlierFactor
        
        self.encoder = SentenceTransformer(model_name)
        self.n_neighbors = n_neighbors
        self.lof = LocalOutlierFactor(n_neighbors=n_neighbors, novelty=True)
        self.is_trained = False
    
    def train(self, normal_texts: List[str]):
        """Train on normal texts"""
        embeddings = self.encoder.encode(normal_texts)
        self.lof.fit(embeddings)
        self.is_trained = True
    
    def detect(self, text: str) -> Dict:
        """Detect anomaly using LOF"""
        if not self.is_trained:
            raise RuntimeError("Train first")
        
        embedding = self.encoder.encode([text])
        
        prediction = self.lof.predict(embedding)[0]
        score = self.lof.decision_function(embedding)[0]
        
        is_anomaly = prediction == -1
        
        # Normalize score
        anomaly_score = 1 - (score + 1) / 2
        anomaly_score = max(0, min(1, anomaly_score))
        
        return {
            'is_anomaly': is_anomaly,
            'anomaly_score': anomaly_score,
            'lof_score': score
        }
```

---

## 4. Real-time Detection Pipeline

### 4.1 Multi-Detector Pipeline

```python
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
import time

class BaseDetector(ABC):
    """Base detector interface"""
    
    @abstractmethod
    def detect(self, input_data: Any) -> Dict:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

class AnomalyDetectionPipeline:
    """Real-time multi-detector pipeline"""
    
    def __init__(self, detectors: List[BaseDetector] = None,
                 parallel: bool = True,
                 timeout_seconds: float = 1.0):
        self.detectors = detectors or []
        self.parallel = parallel
        self.timeout = timeout_seconds
        self.executor = ThreadPoolExecutor(max_workers=len(self.detectors) or 1)
        
        # Weights for combining scores
        self.weights: Dict[str, float] = {}
    
    def add_detector(self, detector: BaseDetector, weight: float = 1.0):
        """Add detector to pipeline"""
        self.detectors.append(detector)
        self.weights[detector.name] = weight
    
    def detect(self, input_data: Any) -> Dict:
        """Run all detectors and combine results"""
        start_time = time.time()
        
        if self.parallel:
            results = self._detect_parallel(input_data)
        else:
            results = self._detect_sequential(input_data)
        
        # Combine results
        combined = self._combine_results(results)
        combined['detection_time_ms'] = (time.time() - start_time) * 1000
        
        return combined
    
    def _detect_parallel(self, input_data: Any) -> Dict[str, Dict]:
        """Run detectors in parallel"""
        futures = {
            detector.name: self.executor.submit(detector.detect, input_data)
            for detector in self.detectors
        }
        
        results = {}
        for name, future in futures.items():
            try:
                results[name] = future.result(timeout=self.timeout)
            except Exception as e:
                results[name] = {'error': str(e), 'is_anomaly': False}
        
        return results
    
    def _detect_sequential(self, input_data: Any) -> Dict[str, Dict]:
        """Run detectors sequentially"""
        results = {}
        for detector in self.detectors:
            try:
                results[detector.name] = detector.detect(input_data)
            except Exception as e:
                results[detector.name] = {'error': str(e), 'is_anomaly': False}
        return results
    
    def _combine_results(self, results: Dict[str, Dict]) -> Dict:
        """Combine detector results"""
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

## 5. Input Feature Extraction

### 5.1 Text Feature Extractor

```python
import re
from collections import Counter

class TextFeatureExtractor:
    """Extract features from text for anomaly detection"""
    
    def extract(self, text: str) -> Dict[str, float]:
        """Extract statistical features from text"""
        features = {}
        
        # Length features
        features['char_count'] = len(text)
        features['word_count'] = len(text.split())
        features['avg_word_length'] = (
            features['char_count'] / features['word_count']
            if features['word_count'] > 0 else 0
        )
        
        # Character distribution
        features['uppercase_ratio'] = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        features['digit_ratio'] = sum(1 for c in text if c.isdigit()) / max(len(text), 1)
        features['special_ratio'] = sum(1 for c in text if not c.isalnum() and not c.isspace()) / max(len(text), 1)
        features['whitespace_ratio'] = sum(1 for c in text if c.isspace()) / max(len(text), 1)
        
        # Suspicious patterns
        features['has_base64'] = float(bool(re.search(r'[A-Za-z0-9+/]{20,}={0,2}', text)))
        features['has_hex'] = float(bool(re.search(r'\\x[0-9a-fA-F]{2}', text)))
        features['has_urls'] = float(bool(re.search(r'https?://\S+', text)))
        
        # Injection indicators
        injection_keywords = ['ignore', 'forget', 'override', 'system', 'prompt', 'instructions']
        features['injection_keyword_count'] = sum(
            1 for kw in injection_keywords if kw.lower() in text.lower()
        )
        
        # Unicode anomalies
        features['non_ascii_ratio'] = sum(1 for c in text if ord(c) > 127) / max(len(text), 1)
        
        # Repetition
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

class SessionFeatureExtractor:
    """Extract session-level features"""
    
    def __init__(self):
        self.session_data: Dict[str, Dict] = {}
    
    def update_and_extract(self, session_id: str, 
                           event_type: str,
                           timestamp: float) -> Dict[str, float]:
        """Update session and extract features"""
        if session_id not in self.session_data:
            self.session_data[session_id] = {
                'events': [],
                'start_time': timestamp,
                'event_types': Counter()
            }
        
        session = self.session_data[session_id]
        session['events'].append(timestamp)
        session['event_types'][event_type] += 1
        
        features = {}
        
        # Event rate
        duration = timestamp - session['start_time'] + 0.001
        features['events_per_second'] = len(session['events']) / duration
        
        # Inter-event time
        if len(session['events']) >= 2:
            intervals = [
                session['events'][i] - session['events'][i-1]
                for i in range(1, len(session['events']))
            ]
            features['avg_interval'] = np.mean(intervals)
            features['min_interval'] = min(intervals)
            features['interval_std'] = np.std(intervals) if len(intervals) > 1 else 0
        else:
            features['avg_interval'] = 0
            features['min_interval'] = 0
            features['interval_std'] = 0
        
        # Event diversity
        features['unique_event_types'] = len(session['event_types'])
        features['event_count'] = len(session['events'])
        
        return features
```

---

## 6. SENTINEL Integration

```python
from dataclasses import dataclass

@dataclass
class AnomalyDetectionConfig:
    """Anomaly detection configuration"""
    z_threshold: float = 3.0
    embedding_threshold: float = 0.5
    isolation_contamination: float = 0.1
    use_parallel: bool = True
    detection_timeout: float = 1.0

class WrappedZScoreDetector(BaseDetector):
    def __init__(self, z_threshold: float):
        self._detector = ZScoreAnomalyDetector(z_threshold)
        self._extractor = TextFeatureExtractor()
    
    @property
    def name(self) -> str:
        return "zscore"
    
    def detect(self, input_data: str) -> Dict:
        features = self._extractor.extract(input_data)
        return self._detector.detect_multi(features)

class WrappedEmbeddingDetector(BaseDetector):
    def __init__(self, threshold: float):
        self._detector = EmbeddingAnomalyDetector(distance_threshold=threshold)
    
    @property
    def name(self) -> str:
        return "embedding"
    
    def train(self, texts: List[str]):
        self._detector.train(texts)
    
    def detect(self, input_data: str) -> Dict:
        return self._detector.detect(input_data)

class SENTINELAnomalyEngine:
    """Anomaly detection engine for SENTINEL"""
    
    def __init__(self, config: AnomalyDetectionConfig):
        self.config = config
        
        # Initialize detectors
        self.zscore = WrappedZScoreDetector(config.z_threshold)
        self.embedding = WrappedEmbeddingDetector(config.embedding_threshold)
        
        # Build pipeline
        self.pipeline = AnomalyDetectionPipeline(
            parallel=config.use_parallel,
            timeout_seconds=config.detection_timeout
        )
        self.pipeline.add_detector(self.zscore, weight=0.4)
        self.pipeline.add_detector(self.embedding, weight=0.6)
        
        self.is_trained = False
    
    def train(self, normal_texts: List[str]):
        """Train on normal corpus"""
        self.embedding.train(normal_texts)
        self.is_trained = True
    
    def detect(self, text: str) -> Dict:
        """Detect anomalies in text"""
        if not self.is_trained:
            # Use only z-score if not trained
            return self.zscore.detect(text)
        
        result = self.pipeline.detect(text)
        
        # Add action recommendation
        if result['combined_score'] > 0.8:
            result['action'] = 'BLOCK'
        elif result['combined_score'] > 0.5:
            result['action'] = 'REVIEW'
        elif result['is_anomaly']:
            result['action'] = 'LOG'
        else:
            result['action'] = 'ALLOW'
        
        return result
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            'is_trained': self.is_trained,
            'detector_count': len(self.pipeline.detectors),
            'config': {
                'z_threshold': self.config.z_threshold,
                'embedding_threshold': self.config.embedding_threshold
            }
        }
```

---

## 7. Summary

| Component | Description |
|-----------|-------------|
| **Z-Score** | Statistical detection by features |
| **Isolation Forest** | ML-based outlier detection |
| **Embedding** | Distance in embedding space |
| **LOF** | Local Outlier Factor |
| **Pipeline** | Multi-detector combination |
| **Feature Extractor** | Text/Session feature extraction |

---

## Next Lesson

→ [02. Behavioral Analysis](02-behavioral-analysis.md)

---

*AI Security Academy | Track 05: Defense Strategies | Module 05.1: Detection*
