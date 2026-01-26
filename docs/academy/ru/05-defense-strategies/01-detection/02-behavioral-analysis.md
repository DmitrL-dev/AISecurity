# Behavioral Analysis для AI Systems

> **Уровень:** �����������  
> **Время:** 55 минут  
> **Трек:** 05 — Defense Strategies  
> **Модуль:** 05.1 — Detection  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять behavior analysis для AI security
- [ ] Имплементировать comprehensive behavior monitoring
- [ ] Построить behavior-based anomaly detection
- [ ] Интегрировать behavioral signals в SENTINEL

---

## 1. Behavioral Analysis Overview

### 1.1 Что такое Behavioral Analysis?

**Behavioral Analysis** — мониторинг и анализ паттернов поведения системы для обнаружения аномалий, не выявляемых статическими методами.

```
┌────────────────────────────────────────────────────────────────────┐
│              BEHAVIORAL ANALYSIS PIPELINE                           │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  [Actions] → [Behavior    → [Pattern      → [Anomaly    → [Alert] │
│               Logging]       Baseline]       Detection]            │
│                                                                    │
│  Типы отслеживаемых behaviors:                                     │
│  ├── Tool Behaviors                                                │
│  │   ├── Частота вызовов инструментов                             │
│  │   ├── Последовательности вызовов                               │
│  │   └── Паттерны параметров                                      │
│  ├── Data Access Behaviors                                         │
│  │   ├── Read/Write patterns                                       │
│  │   ├── Объём доступа к данным                                   │
│  │   └── Доступ к sensitive data                                  │
│  ├── Communication Behaviors                                       │
│  │   ├── Длина ответов                                            │
│  │   ├── Паттерны контента                                        │
│  │   └── Error rates                                               │
│  └── Temporal Behaviors                                            │
│      ├── Timing между запросами                                   │
│      ├── Длительность сессий                                      │
│      └── Циклы активности                                         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Архитектура Behavioral Monitoring

```
Behavioral Monitoring System:
├── Collection Layer
│   ├── Event interceptors
│   ├── Metric collectors
│   └── Log aggregators
├── Processing Layer
│   ├── Event normalization
│   ├── Feature extraction
│   └── Baseline computation
├── Analysis Layer
│   ├── Statistical analysis
│   ├── Sequence analysis
│   └── ML-based detection
└── Response Layer
    ├── Alert generation
    ├── Action recommendation
    └── Automated response
```

---

## 2. Behavior Logging

### 2.1 Event Model

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import json
import hashlib

class EventType(Enum):
    TOOL_CALL = "tool_call"
    DATA_ACCESS = "data_access"
    API_CALL = "api_call"
    RESPONSE_GENERATED = "response_generated"
    ERROR = "error"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    CONTEXT_SWITCH = "context_switch"

@dataclass
class BehaviorEvent:
    """
    Единица поведенческого события.
    Содержит всю информацию для анализа.
    """
    timestamp: datetime
    event_type: EventType
    action: str
    parameters: Dict[str, Any]
    result: str  # success, failure, blocked, timeout
    duration_ms: float
    
    # Context
    session_id: str = ""
    user_id: str = ""
    agent_id: str = ""
    
    # Metadata
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    @property
    def event_id(self) -> str:
        """Уникальный ID события"""
        data = f"{self.timestamp.isoformat()}:{self.event_type.value}:{self.action}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict:
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type.value,
            'action': self.action,
            'parameters': self.parameters,
            'result': self.result,
            'duration_ms': self.duration_ms,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'agent_id': self.agent_id,
            'context': self.context,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BehaviorEvent':
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            event_type=EventType(data['event_type']),
            action=data['action'],
            parameters=data['parameters'],
            result=data['result'],
            duration_ms=data['duration_ms'],
            session_id=data.get('session_id', ''),
            user_id=data.get('user_id', ''),
            agent_id=data.get('agent_id', ''),
            context=data.get('context', {}),
            tags=data.get('tags', [])
        )
```

### 2.2 Behavior Logger

```python
from abc import ABC, abstractmethod
from collections import defaultdict
import threading
import queue

class StorageBackend(ABC):
    """Abstract storage backend"""
    
    @abstractmethod
    def store(self, event: BehaviorEvent):
        pass
    
    @abstractmethod
    def query(self, session_id: str, 
              start_time: datetime = None,
              end_time: datetime = None) -> List[BehaviorEvent]:
        pass

class InMemoryStorage(StorageBackend):
    """In-memory storage для development/testing"""
    
    def __init__(self, max_events: int = 100000):
        self.events: Dict[str, List[BehaviorEvent]] = defaultdict(list)
        self.max_events = max_events
        self.lock = threading.RLock()
    
    def store(self, event: BehaviorEvent):
        with self.lock:
            self.events[event.session_id].append(event)
            # Cleanup old events
            if len(self.events[event.session_id]) > self.max_events:
                self.events[event.session_id] = self.events[event.session_id][-self.max_events:]
    
    def query(self, session_id: str,
              start_time: datetime = None,
              end_time: datetime = None) -> List[BehaviorEvent]:
        with self.lock:
            events = self.events.get(session_id, [])
            
            if start_time:
                events = [e for e in events if e.timestamp >= start_time]
            if end_time:
                events = [e for e in events if e.timestamp <= end_time]
            
            return sorted(events, key=lambda e: e.timestamp)

class BehaviorLogger:
    """
    Центральный logger для behavioral events.
    Поддерживает async logging и multiple backends.
    """
    
    def __init__(self, storage: StorageBackend, async_mode: bool = True):
        self.storage = storage
        self.async_mode = async_mode
        
        # Async queue
        if async_mode:
            self.queue = queue.Queue(maxsize=10000)
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
        
        # In-memory buffer for quick access
        self.session_cache: Dict[str, List[BehaviorEvent]] = defaultdict(list)
        self.cache_lock = threading.RLock()
    
    def _process_queue(self):
        """Background worker для async logging"""
        while True:
            try:
                event = self.queue.get(timeout=1.0)
                self.storage.store(event)
            except queue.Empty:
                continue
    
    def log_event(self, event: BehaviorEvent):
        """Log a behavior event"""
        # Update cache
        with self.cache_lock:
            self.session_cache[event.session_id].append(event)
            # Limit cache size per session
            if len(self.session_cache[event.session_id]) > 1000:
                self.session_cache[event.session_id] = self.session_cache[event.session_id][-1000:]
        
        # Store
        if self.async_mode:
            try:
                self.queue.put_nowait(event)
            except queue.Full:
                # Fallback to sync
                self.storage.store(event)
        else:
            self.storage.store(event)
    
    def log_tool_call(self, session_id: str, tool_name: str,
                      params: dict, result: str, duration_ms: float,
                      user_id: str = "", agent_id: str = ""):
        """Convenience method для tool calls"""
        event = BehaviorEvent(
            timestamp=datetime.utcnow(),
            event_type=EventType.TOOL_CALL,
            action=tool_name,
            parameters=params,
            result=result,
            duration_ms=duration_ms,
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id
        )
        self.log_event(event)
    
    def log_data_access(self, session_id: str, resource: str,
                        access_type: str, size_bytes: int = 0,
                        success: bool = True, user_id: str = ""):
        """Convenience method для data access"""
        event = BehaviorEvent(
            timestamp=datetime.utcnow(),
            event_type=EventType.DATA_ACCESS,
            action=access_type,
            parameters={
                'resource': resource,
                'size_bytes': size_bytes
            },
            result="success" if success else "failure",
            duration_ms=0,
            session_id=session_id,
            user_id=user_id
        )
        self.log_event(event)
    
    def get_session_history(self, session_id: str) -> List[BehaviorEvent]:
        """Get events for a session (from cache first)"""
        with self.cache_lock:
            cached = self.session_cache.get(session_id, [])
            if cached:
                return cached.copy()
        
        return self.storage.query(session_id)
    
    def get_recent_events(self, session_id: str, 
                          n_events: int = 100) -> List[BehaviorEvent]:
        """Get last n events"""
        events = self.get_session_history(session_id)
        return events[-n_events:]
```

---

## 3. Baseline Construction

### 3.1 Statistical Baseline

```python
import numpy as np
from scipy import stats
from collections import Counter

class BehaviorBaseline:
    """
    Статистический baseline нормального поведения.
    Используется для сравнения с текущим поведением.
    """
    
    def __init__(self):
        # Tool statistics
        self.tool_frequencies: Dict[str, List[int]] = defaultdict(list)
        self.tool_durations: Dict[str, List[float]] = defaultdict(list)
        self.tool_success_rates: Dict[str, List[float]] = defaultdict(list)
        
        # Sequence statistics
        self.tool_sequences: List[List[str]] = []
        self.bigram_counts: Counter = Counter()
        self.trigram_counts: Counter = Counter()
        
        # Temporal statistics
        self.inter_event_times: List[float] = []
        self.session_durations: List[float] = []
        self.events_per_session: List[int] = []
        
        # Data access statistics
        self.data_access_volumes: List[int] = []
        self.sensitive_access_rates: List[float] = []
        
        # Computed statistics
        self._computed_stats: Dict = {}
    
    def add_session(self, events: List[BehaviorEvent]):
        """Add a session's events to the baseline"""
        if not events:
            return
        
        # Tool frequencies
        tool_counts = Counter()
        tool_durations = defaultdict(list)
        tool_successes = defaultdict(lambda: {'success': 0, 'total': 0})
        
        for event in events:
            if event.event_type == EventType.TOOL_CALL:
                tool_counts[event.action] += 1
                tool_durations[event.action].append(event.duration_ms)
                tool_successes[event.action]['total'] += 1
                if event.result == 'success':
                    tool_successes[event.action]['success'] += 1
        
        for tool, count in tool_counts.items():
            self.tool_frequencies[tool].append(count)
        
        for tool, durations in tool_durations.items():
            self.tool_durations[tool].extend(durations)
        
        for tool, data in tool_successes.items():
            if data['total'] > 0:
                rate = data['success'] / data['total']
                self.tool_success_rates[tool].append(rate)
        
        # Sequences
        tool_sequence = [e.action for e in events if e.event_type == EventType.TOOL_CALL]
        self.tool_sequences.append(tool_sequence)
        
        # Bigrams and trigrams
        for i in range(len(tool_sequence) - 1):
            bigram = (tool_sequence[i], tool_sequence[i+1])
            self.bigram_counts[bigram] += 1
        
        for i in range(len(tool_sequence) - 2):
            trigram = (tool_sequence[i], tool_sequence[i+1], tool_sequence[i+2])
            self.trigram_counts[trigram] += 1
        
        # Temporal
        if len(events) > 1:
            times = []
            for i in range(1, len(events)):
                delta = (events[i].timestamp - events[i-1].timestamp).total_seconds()
                times.append(delta)
            self.inter_event_times.extend(times)
        
        session_duration = (events[-1].timestamp - events[0].timestamp).total_seconds()
        self.session_durations.append(session_duration)
        self.events_per_session.append(len(events))
        
        # Data access
        data_volume = sum(
            e.parameters.get('size_bytes', 0)
            for e in events if e.event_type == EventType.DATA_ACCESS
        )
        self.data_access_volumes.append(data_volume)
    
    def compute_statistics(self) -> dict:
        """Compute comprehensive statistics from collected data"""
        stats = {}
        
        # Tool frequency statistics
        for tool, freqs in self.tool_frequencies.items():
            stats[f'tool_{tool}_freq_mean'] = np.mean(freqs)
            stats[f'tool_{tool}_freq_std'] = np.std(freqs)
            stats[f'tool_{tool}_freq_max'] = np.max(freqs)
            stats[f'tool_{tool}_freq_p95'] = np.percentile(freqs, 95)
        
        # Tool duration statistics
        for tool, durations in self.tool_durations.items():
            stats[f'tool_{tool}_duration_mean'] = np.mean(durations)
            stats[f'tool_{tool}_duration_std'] = np.std(durations)
            stats[f'tool_{tool}_duration_p95'] = np.percentile(durations, 95)
        
        # Timing statistics
        if self.inter_event_times:
            stats['inter_event_time_mean'] = np.mean(self.inter_event_times)
            stats['inter_event_time_std'] = np.std(self.inter_event_times)
            stats['inter_event_time_p05'] = np.percentile(self.inter_event_times, 5)
            stats['inter_event_time_p95'] = np.percentile(self.inter_event_times, 95)
        
        # Session statistics
        if self.events_per_session:
            stats['events_per_session_mean'] = np.mean(self.events_per_session)
            stats['events_per_session_std'] = np.std(self.events_per_session)
            stats['events_per_session_max'] = np.max(self.events_per_session)
        
        # Sequence statistics
        total_bigrams = sum(self.bigram_counts.values())
        stats['n_unique_bigrams'] = len(self.bigram_counts)
        stats['n_total_bigrams'] = total_bigrams
        
        # Most common sequences
        stats['top_bigrams'] = self.bigram_counts.most_common(10)
        stats['top_trigrams'] = self.trigram_counts.most_common(10)
        
        self._computed_stats = stats
        return stats
    
    def get_n_gram_probabilities(self, n: int = 2) -> Dict[tuple, float]:
        """Get probability distribution over n-grams"""
        if n == 2:
            total = sum(self.bigram_counts.values())
            return {k: v / total for k, v in self.bigram_counts.items()}
        elif n == 3:
            total = sum(self.trigram_counts.values())
            return {k: v / total for k, v in self.trigram_counts.items()}
        else:
            raise ValueError("Only bigrams (n=2) and trigrams (n=3) supported")
```

### 3.2 User Profile Builder

```python
class UserBehaviorProfile:
    """
    Per-user behavior profile для персонализированной detection.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.baseline = BehaviorBaseline()
        self.n_sessions = 0
        self.created_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()
        
        # User-specific patterns
        self.preferred_tools: List[str] = []
        self.typical_session_length: float = 0
        self.activity_hours: List[int] = []
    
    def update(self, events: List[BehaviorEvent]):
        """Update profile with new session data"""
        self.baseline.add_session(events)
        self.n_sessions += 1
        self.last_updated = datetime.utcnow()
        
        # Extract user-specific patterns
        self._update_patterns(events)
    
    def _update_patterns(self, events: List[BehaviorEvent]):
        """Extract and update user-specific patterns"""
        # Preferred tools (most frequently used)
        tool_counts = Counter(
            e.action for e in events if e.event_type == EventType.TOOL_CALL
        )
        self.preferred_tools = [t for t, _ in tool_counts.most_common(5)]
        
        # Activity hours
        for event in events:
            hour = event.timestamp.hour
            if hour not in self.activity_hours:
                self.activity_hours.append(hour)
    
    def get_statistics(self) -> dict:
        """Get profile statistics"""
        base_stats = self.baseline.compute_statistics()
        
        return {
            **base_stats,
            'user_id': self.user_id,
            'n_sessions': self.n_sessions,
            'preferred_tools': self.preferred_tools,
            'activity_hours': sorted(self.activity_hours),
            'profile_age_days': (datetime.utcnow() - self.created_at).days
        }

class ProfileManager:
    """Manages user behavior profiles"""
    
    def __init__(self, logger: BehaviorLogger):
        self.logger = logger
        self.profiles: Dict[str, UserBehaviorProfile] = {}
        self.global_baseline = BehaviorBaseline()
    
    def get_or_create_profile(self, user_id: str) -> UserBehaviorProfile:
        """Get existing profile or create new one"""
        if user_id not in self.profiles:
            self.profiles[user_id] = UserBehaviorProfile(user_id)
        return self.profiles[user_id]
    
    def update_profile(self, user_id: str, session_id: str):
        """Update user profile from session data"""
        profile = self.get_or_create_profile(user_id)
        events = self.logger.get_session_history(session_id)
        
        if events:
            profile.update(events)
            self.global_baseline.add_session(events)
    
    def get_baseline_for_user(self, user_id: str) -> BehaviorBaseline:
        """Get baseline (user-specific or global)"""
        if user_id in self.profiles and self.profiles[user_id].n_sessions >= 5:
            return self.profiles[user_id].baseline
        return self.global_baseline
```

---

## 4. Anomaly Detection

### 4.1 Statistical Anomaly Detector

```python
class StatisticalBehaviorDetector:
    """
    Statistical anomaly detection на основе baseline.
    Использует z-scores и percentile-based thresholds.
    """
    
    def __init__(self, baseline: BehaviorBaseline, z_threshold: float = 3.0):
        self.baseline = baseline
        self.z_threshold = z_threshold
        self.stats = baseline.compute_statistics()
    
    def analyze_session(self, events: List[BehaviorEvent]) -> dict:
        """
        Analyze a session for anomalies.
        
        Returns:
            Detection results with anomalies and scores
        """
        results = {
            'anomalies': [],
            'scores': {},
            'total_anomaly_score': 0.0
        }
        
        # Tool frequency analysis
        tool_freq_anomalies = self._check_tool_frequencies(events)
        results['anomalies'].extend(tool_freq_anomalies)
        
        # Timing analysis
        timing_anomalies = self._check_timing(events)
        results['anomalies'].extend(timing_anomalies)
        
        # Sequence analysis
        sequence_anomalies = self._check_sequences(events)
        results['anomalies'].extend(sequence_anomalies)
        
        # Duration analysis
        duration_anomalies = self._check_durations(events)
        results['anomalies'].extend(duration_anomalies)
        
        # Calculate total score
        for anomaly in results['anomalies']:
            results['total_anomaly_score'] += anomaly.get('severity', 0.5)
        
        return results
    
    def _check_tool_frequencies(self, events: List[BehaviorEvent]) -> List[dict]:
        """Check tool call frequencies"""
        anomalies = []
        
        tool_counts = Counter(
            e.action for e in events if e.event_type == EventType.TOOL_CALL
        )
        
        for tool, count in tool_counts.items():
            mean_key = f'tool_{tool}_freq_mean'
            std_key = f'tool_{tool}_freq_std'
            
            if mean_key not in self.stats:
                # Unknown tool
                anomalies.append({
                    'type': 'unknown_tool',
                    'tool': tool,
                    'severity': 0.7,
                    'description': f"Unknown tool '{tool}' used"
                })
                continue
            
            mean = self.stats[mean_key]
            std = self.stats.get(std_key, 1.0) or 1.0
            
            z_score = (count - mean) / std
            
            if abs(z_score) > self.z_threshold:
                anomalies.append({
                    'type': 'frequency_anomaly',
                    'tool': tool,
                    'count': count,
                    'expected': mean,
                    'z_score': z_score,
                    'severity': min(abs(z_score) / 5.0, 1.0),
                    'description': f"Tool '{tool}' called {count} times (expected ~{mean:.1f})"
                })
        
        return anomalies
    
    def _check_timing(self, events: List[BehaviorEvent]) -> List[dict]:
        """Check inter-event timing"""
        anomalies = []
        
        if len(events) < 2:
            return anomalies
        
        times = []
        for i in range(1, len(events)):
            delta = (events[i].timestamp - events[i-1].timestamp).total_seconds()
            times.append(delta)
        
        mean = self.stats.get('inter_event_time_mean', 1.0)
        std = self.stats.get('inter_event_time_std', 1.0) or 1.0
        
        avg_time = np.mean(times)
        z_score = (avg_time - mean) / std
        
        if abs(z_score) > self.z_threshold:
            anomalies.append({
                'type': 'timing_anomaly',
                'avg_interval': avg_time,
                'expected': mean,
                'z_score': z_score,
                'severity': min(abs(z_score) / 5.0, 1.0),
                'description': f"Unusual timing pattern: {avg_time:.2f}s avg (expected ~{mean:.2f}s)"
            })
        
        # Check for suspicious bursts
        min_time = min(times)
        p05 = self.stats.get('inter_event_time_p05', 0.1)
        
        if min_time < p05 * 0.1:  # 10x faster than normal minimum
            anomalies.append({
                'type': 'burst_detected',
                'min_interval': min_time,
                'threshold': p05,
                'severity': 0.8,
                'description': f"Suspicious burst: {min_time:.3f}s between events"
            })
        
        return anomalies
    
    def _check_sequences(self, events: List[BehaviorEvent]) -> List[dict]:
        """Check for unusual action sequences"""
        anomalies = []
        
        actions = [e.action for e in events if e.event_type == EventType.TOOL_CALL]
        
        if len(actions) < 2:
            return anomalies
        
        # Check bigrams
        bigram_probs = self.baseline.get_n_gram_probabilities(n=2)
        
        rare_sequences = []
        for i in range(len(actions) - 1):
            bigram = (actions[i], actions[i+1])
            prob = bigram_probs.get(bigram, 0)
            
            if prob < 0.01:  # Very rare
                rare_sequences.append({
                    'sequence': bigram,
                    'probability': prob
                })
        
        if rare_sequences:
            anomalies.append({
                'type': 'rare_sequence',
                'sequences': rare_sequences[:5],  # Top 5
                'severity': min(len(rare_sequences) * 0.2, 1.0),
                'description': f"Found {len(rare_sequences)} rare action sequences"
            })
        
        return anomalies
    
    def _check_durations(self, events: List[BehaviorEvent]) -> List[dict]:
        """Check tool call durations"""
        anomalies = []
        
        for event in events:
            if event.event_type != EventType.TOOL_CALL:
                continue
            
            tool = event.action
            duration = event.duration_ms
            
            mean_key = f'tool_{tool}_duration_mean'
            std_key = f'tool_{tool}_duration_std'
            
            if mean_key not in self.stats:
                continue
            
            mean = self.stats[mean_key]
            std = self.stats.get(std_key, 1.0) or 1.0
            
            z_score = (duration - mean) / std
            
            if abs(z_score) > self.z_threshold:
                anomalies.append({
                    'type': 'duration_anomaly',
                    'tool': tool,
                    'duration_ms': duration,
                    'expected': mean,
                    'z_score': z_score,
                    'severity': min(abs(z_score) / 5.0, 0.6),
                    'description': f"Tool '{tool}' took {duration:.0f}ms (expected ~{mean:.0f}ms)"
                })
        
        return anomalies
```

### 4.2 Sequence Anomaly Detector

```python
class SequenceAnomalyDetector:
    """
    Markov-based sequence anomaly detection.
    Detects unlikely action sequences.
    """
    
    def __init__(self, baseline: BehaviorBaseline):
        self.baseline = baseline
        self.bigram_probs = baseline.get_n_gram_probabilities(n=2)
        self.trigram_probs = baseline.get_n_gram_probabilities(n=3)
    
    def analyze_sequence(self, actions: List[str]) -> dict:
        """
        Analyze action sequence for anomalies.
        
        Returns:
            Sequence analysis results
        """
        if len(actions) < 2:
            return {'anomaly': False, 'perplexity': 1.0}
        
        # Calculate log probability of sequence
        log_prob = 0.0
        smoothing = 0.001  # Laplace smoothing
        
        anomalous_transitions = []
        
        for i in range(len(actions) - 1):
            bigram = (actions[i], actions[i+1])
            prob = self.bigram_probs.get(bigram, smoothing)
            log_prob += np.log(prob)
            
            if prob < 0.01:
                anomalous_transitions.append({
                    'position': i,
                    'transition': bigram,
                    'probability': prob
                })
        
        # Perplexity = exp(-avg log prob)
        n = len(actions) - 1
        perplexity = np.exp(-log_prob / n)
        
        # High perplexity = unusual sequence
        is_anomaly = perplexity > 50 or len(anomalous_transitions) > 2
        
        return {
            'anomaly': is_anomaly,
            'perplexity': perplexity,
            'log_probability': log_prob,
            'n_anomalous_transitions': len(anomalous_transitions),
            'anomalous_transitions': anomalous_transitions[:5],
            'confidence': min((perplexity - 50) / 100, 1.0) if is_anomaly else 0.0
        }
    
    def get_transition_probability(self, action1: str, action2: str) -> float:
        """Get probability of transitioning from action1 to action2"""
        return self.bigram_probs.get((action1, action2), 0.0)
    
    def predict_next_action(self, current_action: str, top_k: int = 5) -> List[tuple]:
        """Predict most likely next actions"""
        predictions = []
        
        for (a1, a2), prob in self.bigram_probs.items():
            if a1 == current_action:
                predictions.append((a2, prob))
        
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:top_k]
```

---

## 5. Attack Pattern Detection

### 5.1 Privilege Escalation Detector

```python
class PrivilegeEscalationDetector:
    """
    Detects privilege escalation attempts based on behavior patterns.
    """
    
    def __init__(self):
        # Define resource sensitivity levels
        self.resource_levels = {
            'public': 0,
            'user': 1,
            'admin': 2,
            'system': 3,
            'root': 4
        }
        
        # Sensitive resource patterns
        self.sensitive_patterns = [
            r'/etc/passwd',
            r'/etc/shadow',
            r'\.env',
            r'secrets',
            r'credentials',
            r'api[_-]?key',
            r'token',
            r'password'
        ]
    
    def detect(self, events: List[BehaviorEvent]) -> dict:
        """
        Detect privilege escalation patterns.
        
        Returns:
            Detection results
        """
        access_levels = []
        escalation_attempts = []
        sensitive_accesses = []
        
        import re
        
        for event in events:
            if event.event_type != EventType.DATA_ACCESS:
                continue
            
            resource = event.parameters.get('resource', '')
            
            # Check sensitivity level
            level = self._get_resource_level(resource)
            access_levels.append(level)
            
            # Check for escalation
            if len(access_levels) > 1:
                prev_max = max(access_levels[:-1])
                if level > prev_max + 1:
                    escalation_attempts.append({
                        'from_level': prev_max,
                        'to_level': level,
                        'resource': resource,
                        'timestamp': event.timestamp.isoformat()
                    })
            
            # Check for sensitive patterns
            for pattern in self.sensitive_patterns:
                if re.search(pattern, resource, re.IGNORECASE):
                    sensitive_accesses.append({
                        'resource': resource,
                        'pattern': pattern,
                        'timestamp': event.timestamp.isoformat()
                    })
        
        is_escalation = len(escalation_attempts) > 0 or len(sensitive_accesses) > 3
        
        return {
            'detected': is_escalation,
            'escalation_attempts': escalation_attempts,
            'sensitive_accesses': sensitive_accesses,
            'max_level_reached': max(access_levels) if access_levels else 0,
            'severity': self._compute_severity(escalation_attempts, sensitive_accesses)
        }
    
    def _get_resource_level(self, resource: str) -> int:
        """Determine sensitivity level of resource"""
        resource_lower = resource.lower()
        
        if 'root' in resource_lower or 'system' in resource_lower:
            return 4
        elif 'admin' in resource_lower:
            return 3
        elif '/etc/' in resource or '/var/' in resource:
            return 2
        elif 'user' in resource_lower:
            return 1
        return 0
    
    def _compute_severity(self, escalations: list, sensitive: list) -> str:
        if len(escalations) > 2 or len(sensitive) > 5:
            return 'critical'
        elif len(escalations) > 0 or len(sensitive) > 2:
            return 'high'
        elif len(sensitive) > 0:
            return 'medium'
        return 'low'
```

### 5.2 Data Exfiltration Detector

```python
class DataExfiltrationDetector:
    """
    Detects potential data exfiltration attempts.
    """
    
    def __init__(self, 
                 volume_threshold_mb: float = 10.0,
                 sensitive_access_threshold: int = 5):
        self.volume_threshold = volume_threshold_mb * 1024 * 1024  # To bytes
        self.sensitive_threshold = sensitive_access_threshold
        
        # Exfiltration indicators
        self.external_indicators = [
            'upload', 'export', 'send', 'post', 'external'
        ]
    
    def detect(self, events: List[BehaviorEvent]) -> dict:
        """
        Detect data exfiltration patterns.
        
        Returns:
            Detection results
        """
        total_data_accessed = 0
        sensitive_accesses = []
        external_sends = []
        
        for event in events:
            if event.event_type == EventType.DATA_ACCESS:
                size = event.parameters.get('size_bytes', 0)
                total_data_accessed += size
                
                resource = event.parameters.get('resource', '')
                if self._is_sensitive(resource):
                    sensitive_accesses.append({
                        'resource': resource,
                        'size': size,
                        'timestamp': event.timestamp.isoformat()
                    })
            
            # Check for external sends
            if event.event_type in [EventType.TOOL_CALL, EventType.API_CALL]:
                if any(ind in event.action.lower() for ind in self.external_indicators):
                    external_sends.append({
                        'action': event.action,
                        'parameters': event.parameters,
                        'timestamp': event.timestamp.isoformat()
                    })
        
        is_exfiltration = (
            total_data_accessed > self.volume_threshold or
            len(sensitive_accesses) > self.sensitive_threshold or
            (len(external_sends) > 0 and len(sensitive_accesses) > 0)
        )
        
        return {
            'detected': is_exfiltration,
            'total_data_mb': total_data_accessed / (1024 * 1024),
            'sensitive_accesses': sensitive_accesses,
            'external_sends': external_sends,
            'risk_score': self._compute_risk_score(
                total_data_accessed, sensitive_accesses, external_sends
            )
        }
    
    def _is_sensitive(self, resource: str) -> bool:
        """Check if resource is sensitive"""
        sensitive_patterns = [
            'credential', 'password', 'secret', 'key', 'token',
            'private', 'confidential', 'internal', 'pii'
        ]
        resource_lower = resource.lower()
        return any(p in resource_lower for p in sensitive_patterns)
    
    def _compute_risk_score(self, volume: int, sensitive: list, external: list) -> float:
        score = 0.0
        
        # Volume contribution
        score += min(volume / self.volume_threshold, 1.0) * 0.3
        
        # Sensitive access contribution
        score += min(len(sensitive) / self.sensitive_threshold, 1.0) * 0.4
        
        # External send contribution
        if external:
            score += 0.3
        
        return min(score, 1.0)
```

---

## 6. Real-time Monitor

### 6.1 Real-time Behavior Monitor

```python
from threading import Thread
import time

class RealTimeBehaviorMonitor:
    """
    Real-time monitoring of agent behavior.
    Continuously analyzes incoming events and raises alerts.
    """
    
    def __init__(self, 
                 profile_manager: ProfileManager,
                 alert_threshold: float = 0.7):
        self.profile_manager = profile_manager
        self.alert_threshold = alert_threshold
        
        # Detectors
        self.statistical_detector = None
        self.sequence_detector = None
        self.priv_detector = PrivilegeEscalationDetector()
        self.exfil_detector = DataExfiltrationDetector()
        
        # Active sessions
        self.active_sessions: Dict[str, List[BehaviorEvent]] = {}
        
        # Alert callbacks
        self.alert_callbacks: List[callable] = []
        
        # Running state
        self._running = False
    
    def register_alert_callback(self, callback: callable):
        """Register callback for alerts"""
        self.alert_callbacks.append(callback)
    
    def on_event(self, event: BehaviorEvent):
        """Process incoming event"""
        session_id = event.session_id
        
        # Add to active session
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = []
        self.active_sessions[session_id].append(event)
        
        # Get appropriate baseline
        baseline = self.profile_manager.get_baseline_for_user(event.user_id)
        
        # Initialize detectors if needed
        if self.statistical_detector is None or \
           self.statistical_detector.baseline != baseline:
            self.statistical_detector = StatisticalBehaviorDetector(baseline)
            self.sequence_detector = SequenceAnomalyDetector(baseline)
        
        # Analyze session
        self._analyze_session(session_id, event.user_id)
    
    def _analyze_session(self, session_id: str, user_id: str):
        """Analyze current session state"""
        events = self.active_sessions.get(session_id, [])
        
        if len(events) < 3:  # Need minimum events
            return
        
        # Statistical analysis
        stat_result = self.statistical_detector.analyze_session(events)
        
        # Sequence analysis
        actions = [e.action for e in events if e.event_type == EventType.TOOL_CALL]
        seq_result = self.sequence_detector.analyze_sequence(actions)
        
        # Attack pattern detection
        priv_result = self.priv_detector.detect(events)
        exfil_result = self.exfil_detector.detect(events)
        
        # Aggregate risk
        total_score = self._compute_total_risk(
            stat_result, seq_result, priv_result, exfil_result
        )
        
        # Raise alert if threshold exceeded
        if total_score >= self.alert_threshold:
            self._raise_alert({
                'session_id': session_id,
                'user_id': user_id,
                'risk_score': total_score,
                'statistical': stat_result,
                'sequence': seq_result,
                'privilege_escalation': priv_result,
                'data_exfiltration': exfil_result,
                'event_count': len(events)
            })
    
    def _compute_total_risk(self, stat, seq, priv, exfil) -> float:
        """Compute aggregate risk score"""
        score = 0.0
        
        # Statistical anomalies
        score += min(stat['total_anomaly_score'] * 0.3, 0.3)
        
        # Sequence anomalies
        if seq['anomaly']:
            score += seq['confidence'] * 0.2
        
        # Privilege escalation
        if priv['detected']:
            severity_weights = {'critical': 0.3, 'high': 0.25, 'medium': 0.15, 'low': 0.05}
            score += severity_weights.get(priv['severity'], 0.1)
        
        # Data exfiltration
        if exfil['detected']:
            score += exfil['risk_score'] * 0.25
        
        return min(score, 1.0)
    
    def _raise_alert(self, alert_data: dict):
        """Raise alert to all callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                print(f"Alert callback error: {e}")
    
    def end_session(self, session_id: str):
        """Clean up ended session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
```

---

## 7. SENTINEL Integration

```python
from dataclasses import dataclass

@dataclass
class BehaviorSecurityConfig:
    """Configuration for behavior security engine"""
    z_threshold: float = 3.0
    alert_threshold: float = 0.7
    volume_threshold_mb: float = 10.0
    session_timeout_minutes: int = 30
    enable_realtime: bool = True

class SENTINELBehaviorEngine:
    """
    Behavior Analysis engine для SENTINEL framework.
    """
    
    def __init__(self, config: BehaviorSecurityConfig):
        self.config = config
        
        # Core components
        self.storage = InMemoryStorage()
        self.logger = BehaviorLogger(self.storage)
        self.profile_manager = ProfileManager(self.logger)
        
        # Real-time monitor
        self.monitor = RealTimeBehaviorMonitor(
            self.profile_manager,
            alert_threshold=config.alert_threshold
        )
    
    def log_event(self, event_data: dict):
        """Log a behavior event"""
        event = BehaviorEvent(**event_data)
        self.logger.log_event(event)
        
        if self.config.enable_realtime:
            self.monitor.on_event(event)
    
    def analyze_session(self, session_id: str) -> dict:
        """Analyze a complete session"""
        events = self.logger.get_session_history(session_id)
        
        if not events:
            return {'status': 'no_events'}
        
        user_id = events[0].user_id
        baseline = self.profile_manager.get_baseline_for_user(user_id)
        
        # Run all detectors
        stat_detector = StatisticalBehaviorDetector(
            baseline, z_threshold=self.config.z_threshold
        )
        seq_detector = SequenceAnomalyDetector(baseline)
        priv_detector = PrivilegeEscalationDetector()
        exfil_detector = DataExfiltrationDetector(
            volume_threshold_mb=self.config.volume_threshold_mb
        )
        
        stat_result = stat_detector.analyze_session(events)
        
        actions = [e.action for e in events if e.event_type == EventType.TOOL_CALL]
        seq_result = seq_detector.analyze_sequence(actions)
        
        priv_result = priv_detector.detect(events)
        exfil_result = exfil_detector.detect(events)
        
        return {
            'session_id': session_id,
            'event_count': len(events),
            'statistical': stat_result,
            'sequence': seq_result,
            'privilege_escalation': priv_result,
            'data_exfiltration': exfil_result,
            'is_suspicious': (
                stat_result['total_anomaly_score'] > 1.0 or
                seq_result['anomaly'] or
                priv_result['detected'] or
                exfil_result['detected']
            )
        }
    
    def register_alert_handler(self, handler: callable):
        """Register alert handler"""
        self.monitor.register_alert_callback(handler)
```

---

## 8. Резюме

| Компонент | Описание |
|-----------|----------|
| **Behavior Logger** | Async event logging с in-memory cache |
| **Baseline** | Statistical baseline от historical data |
| **Statistical Detector** | Z-score based anomaly detection |
| **Sequence Detector** | Markov-based sequence analysis |
| **Attack Detectors** | Privilege escalation, data exfiltration |
| **Real-time Monitor** | Continuous session analysis с alerts |

---

## Следующий урок

→ [03. Pattern Matching](03-pattern-matching.md)

---

*AI Security Academy | Track 05: Defense Strategies | Module 05.1: Detection*
