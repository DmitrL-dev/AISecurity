# Поведенческий анализ для AI-систем

> **Уровень:** Продвинутый  
> **Время:** 55 минут  
> **Трек:** 05 — Стратегии защиты  
> **Модуль:** 05.1 — Детекция  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять поведенческий анализ для AI-безопасности
- [ ] Реализовать комплексный мониторинг поведения
- [ ] Построить детекцию аномалий на основе поведения
- [ ] Интегрировать поведенческие сигналы в SENTINEL

---

## 1. Обзор поведенческого анализа

### 1.1 Что такое поведенческий анализ?

**Поведенческий анализ** — мониторинг и анализ паттернов поведения системы для детекции аномалий, не обнаруживаемых статическими методами.

```
┌────────────────────────────────────────────────────────────────────┐
│              ПАЙПЛАЙН ПОВЕДЕНЧЕСКОГО АНАЛИЗА                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  [Действия] → [Логирование  → [Baseline     → [Детекция   → [Алерт]│
│                поведения]     паттернов]     аномалий]            │
│                                                                    │
│  Отслеживаемые поведения:                                          │
│  ├── Поведение инструментов                                        │
│  │   ├── Частота вызовов                                          │
│  │   ├── Последовательности вызовов                               │
│  │   └── Паттерны параметров                                      │
│  ├── Поведение доступа к данным                                    │
│  │   ├── Паттерны чтения/записи                                   │
│  │   ├── Объём доступа к данным                                   │
│  │   └── Доступ к чувствительным данным                           │
│  ├── Коммуникационное поведение                                    │
│  │   ├── Длина ответов                                            │
│  │   ├── Паттерны контента                                        │
│  │   └── Частота ошибок                                           │
│  └── Временное поведение                                           │
│      ├── Тайминг между запросами                                  │
│      ├── Длительность сессий                                      │
│      └── Циклы активности                                         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Архитектура мониторинга поведения

```
Система мониторинга поведения:
├── Слой сбора данных
│   ├── Перехватчики событий
│   ├── Сборщики метрик
│   └── Агрегаторы логов
├── Слой обработки
│   ├── Нормализация событий
│   ├── Извлечение признаков
│   └── Вычисление baseline
├── Слой анализа
│   ├── Статистический анализ
│   ├── Анализ последовательностей
│   └── ML-детекция
└── Слой реагирования
    ├── Генерация алертов
    ├── Рекомендации действий
    └── Автоматизированный ответ
```

---

## 2. Логирование поведения

### 2.1 Модель событий

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any
from datetime import datetime
from enum import Enum

class EventType(Enum):
    TOOL_CALL = "tool_call"
    DATA_ACCESS = "data_access"
    API_CALL = "api_call"
    RESPONSE_GENERATED = "response_generated"
    ERROR = "error"
    SESSION_START = "session_start"
    SESSION_END = "session_end"

@dataclass
class BehaviorEvent:
    """Единица поведенческого события."""
    timestamp: datetime
    event_type: EventType
    action: str
    parameters: Dict[str, Any]
    result: str  # success, failure, blocked, timeout
    duration_ms: float
    session_id: str = ""
    user_id: str = ""
    agent_id: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
```

### 2.2 Логгер поведения

```python
class BehaviorLogger:
    """
    Центральный логгер поведенческих событий.
    Поддерживает асинхронное логирование и множество backend'ов.
    """
    
    def __init__(self, storage: StorageBackend, async_mode: bool = True):
        self.storage = storage
        self.async_mode = async_mode
        self.session_cache: Dict[str, List[BehaviorEvent]] = defaultdict(list)
    
    def log_tool_call(self, session_id: str, tool_name: str,
                      params: dict, result: str, duration_ms: float,
                      user_id: str = "", agent_id: str = ""):
        """Удобный метод для вызовов инструментов"""
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
        """Удобный метод для доступа к данным"""
        event = BehaviorEvent(
            timestamp=datetime.utcnow(),
            event_type=EventType.DATA_ACCESS,
            action=access_type,
            parameters={'resource': resource, 'size_bytes': size_bytes},
            result="success" if success else "failure",
            duration_ms=0,
            session_id=session_id,
            user_id=user_id
        )
        self.log_event(event)
```

---

## 3. Построение baseline

### 3.1 Статистический baseline

```python
import numpy as np
from collections import Counter

class BehaviorBaseline:
    """Статистический baseline нормального поведения."""
    
    def __init__(self):
        self.tool_frequencies: Dict[str, List[int]] = defaultdict(list)
        self.tool_durations: Dict[str, List[float]] = defaultdict(list)
        self.tool_sequences: List[List[str]] = []
        self.bigram_counts: Counter = Counter()
        self.inter_event_times: List[float] = []
    
    def add_session(self, events: List[BehaviorEvent]):
        """Добавить события сессии в baseline"""
        tool_counts = Counter()
        
        for event in events:
            if event.event_type == EventType.TOOL_CALL:
                tool_counts[event.action] += 1
                self.tool_durations[event.action].append(event.duration_ms)
        
        for tool, count in tool_counts.items():
            self.tool_frequencies[tool].append(count)
        
        # Последовательности
        tool_sequence = [e.action for e in events if e.event_type == EventType.TOOL_CALL]
        self.tool_sequences.append(tool_sequence)
        
        # Bigrams
        for i in range(len(tool_sequence) - 1):
            bigram = (tool_sequence[i], tool_sequence[i+1])
            self.bigram_counts[bigram] += 1
    
    def compute_statistics(self) -> dict:
        """Вычислить статистику из собранных данных"""
        stats = {}
        
        for tool, freqs in self.tool_frequencies.items():
            stats[f'tool_{tool}_freq_mean'] = np.mean(freqs)
            stats[f'tool_{tool}_freq_std'] = np.std(freqs)
            stats[f'tool_{tool}_freq_p95'] = np.percentile(freqs, 95)
        
        for tool, durations in self.tool_durations.items():
            stats[f'tool_{tool}_duration_mean'] = np.mean(durations)
            stats[f'tool_{tool}_duration_std'] = np.std(durations)
        
        return stats
```

---

## 4. Детекция аномалий

### 4.1 Статистический детектор аномалий

```python
class StatisticalBehaviorDetector:
    """
    Статистическая детекция аномалий на основе baseline.
    Использует z-scores и пороги на основе перцентилей.
    """
    
    def __init__(self, baseline: BehaviorBaseline, z_threshold: float = 3.0):
        self.baseline = baseline
        self.z_threshold = z_threshold
        self.stats = baseline.compute_statistics()
    
    def analyze_session(self, events: List[BehaviorEvent]) -> dict:
        """Анализ сессии на аномалии."""
        results = {
            'anomalies': [],
            'scores': {},
            'total_anomaly_score': 0.0
        }
        
        # Анализ частоты инструментов
        results['anomalies'].extend(self._check_tool_frequencies(events))
        
        # Анализ тайминга
        results['anomalies'].extend(self._check_timing(events))
        
        # Анализ последовательностей
        results['anomalies'].extend(self._check_sequences(events))
        
        # Расчёт общего балла
        for anomaly in results['anomalies']:
            results['total_anomaly_score'] += anomaly.get('severity', 0.5)
        
        return results
    
    def _check_tool_frequencies(self, events: List[BehaviorEvent]) -> List[dict]:
        """Проверка частоты вызовов инструментов"""
        anomalies = []
        tool_counts = Counter(
            e.action for e in events if e.event_type == EventType.TOOL_CALL
        )
        
        for tool, count in tool_counts.items():
            mean_key = f'tool_{tool}_freq_mean'
            std_key = f'tool_{tool}_freq_std'
            
            if mean_key not in self.stats:
                anomalies.append({
                    'type': 'unknown_tool',
                    'tool': tool,
                    'severity': 0.7,
                    'description': f"Неизвестный инструмент '{tool}' использован"
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
                    'z_score': z_score,
                    'severity': min(abs(z_score) / 5.0, 1.0),
                    'description': f"Инструмент '{tool}' вызван {count} раз (ожидалось ~{mean:.1f})"
                })
        
        return anomalies
    
    def _check_timing(self, events: List[BehaviorEvent]) -> List[dict]:
        """Проверка тайминга между событиями"""
        anomalies = []
        
        if len(events) < 2:
            return anomalies
        
        times = []
        for i in range(1, len(events)):
            delta = (events[i].timestamp - events[i-1].timestamp).total_seconds()
            times.append(delta)
        
        avg_time = np.mean(times)
        mean = self.stats.get('inter_event_time_mean', 1.0)
        std = self.stats.get('inter_event_time_std', 1.0) or 1.0
        z_score = (avg_time - mean) / std
        
        if abs(z_score) > self.z_threshold:
            anomalies.append({
                'type': 'timing_anomaly',
                'avg_interval': avg_time,
                'z_score': z_score,
                'severity': min(abs(z_score) / 5.0, 1.0),
                'description': f"Необычный паттерн тайминга: {avg_time:.2f}s avg"
            })
        
        # Проверка на подозрительные всплески
        min_time = min(times)
        if min_time < 0.01:  # Менее 10ms
            anomalies.append({
                'type': 'burst_detected',
                'min_interval': min_time,
                'severity': 0.8,
                'description': f"Подозрительный всплеск: {min_time:.3f}s между событиями"
            })
        
        return anomalies
```

### 4.2 Детектор аномалий последовательностей

```python
class SequenceAnomalyDetector:
    """
    Детекция аномалий последовательностей на основе Маркова.
    """
    
    def __init__(self, baseline: BehaviorBaseline):
        self.baseline = baseline
        self.bigram_probs = baseline.get_n_gram_probabilities(n=2)
    
    def analyze_sequence(self, actions: List[str]) -> dict:
        """Анализ последовательности действий на аномалии."""
        if len(actions) < 2:
            return {'anomaly': False, 'perplexity': 1.0}
        
        log_prob = 0.0
        smoothing = 0.001
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
        
        return {
            'anomaly': perplexity > 100,  # Порог
            'perplexity': perplexity,
            'anomalous_transitions': anomalous_transitions,
            'sequence_length': len(actions)
        }
```

---

## 5. Интеграция с SENTINEL

```python
from sentinel import scan
    BehaviorMonitor,
    AnomalyDetector,
    ProfileManager
)

class SENTINELBehaviorAnalyzer:
    def __init__(self, config):
        self.logger = BehaviorLogger(InMemoryStorage())
        self.profile_manager = ProfileManager(self.logger)
        self.detector = AnomalyDetector()
    
    def analyze_session(self, session_id: str, user_id: str) -> dict:
        # Получить baseline для пользователя
        baseline = self.profile_manager.get_baseline_for_user(user_id)
        
        # Получить события сессии
        events = self.logger.get_session_history(session_id)
        
        # Анализ аномалий
        detector = StatisticalBehaviorDetector(baseline)
        results = detector.analyze_session(events)
        
        # Генерация алертов
        if results['total_anomaly_score'] > 1.0:
            self._generate_alert(session_id, results)
        
        return results
```

---

## 6. Итоги

1. **Поведенческий анализ** дополняет статическую детекцию
2. **Baseline** критичен для точной детекции аномалий
3. **Многослойный** подход: статистика + последовательности + ML
4. **Персонализация** улучшает точность
5. **SENTINEL** предоставляет интегрированную инфраструктуру

---

*AI Security Academy | Трек 05: Стратегии защиты | Модуль 05.1: Детекция*
