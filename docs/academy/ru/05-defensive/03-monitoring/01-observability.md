# Мониторинг и Observability

> **Урок:** 05.3.1 — Мониторинг безопасности AI  
> **Время:** 40 минут  
> **Требования:** Основы защитных слоёв

---

## Цели обучения

После завершения этого урока вы сможете:

1. Проектировать мониторинг для AI систем
2. Детектировать атаки в реальном времени
3. Строить alerting для событий безопасности
4. Реализовать forensic logging

---

## Почему мониторинг важен

Традиционный мониторинг безопасности пропускает AI-специфичные угрозы:

| Традиционный | AI-специфичный |
|--------------|----------------|
| Сетевой трафик | Паттерны промптов |
| Системные логи | Траектории разговоров |
| Аутентификация | Semantic drift |
| Rate limiting | Прогрессия атак |

---

## Архитектура мониторинга

```
┌─────────────────────────────────────────────────────────────┐
│                    СЛОИ МОНИТОРИНГА                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Слой 1: Мониторинг входных данных                    │  │
│  │ • Детекция паттернов injection                        │  │
│  │ • Аномалии объёмов                                    │  │
│  │ • Анализ поведения пользователей                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Слой 2: Мониторинг обработки                          │  │
│  │ • Паттерны использования токенов                      │  │
│  │ • Аномалии latency                                    │  │
│  │ • Паттерны вызова инструментов                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Слой 3: Мониторинг выходных данных                    │  │
│  │ • Нарушения content policy                            │  │
│  │ • Детекция утечки данных                              │  │
│  │ • Аномалии ответов                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Слой 4: Мониторинг сессий                             │  │
│  │ • Анализ траектории разговоров                        │  │
│  │ • Детекция multi-turn атак                            │  │
│  │ • Session reputation scoring                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Реализация

### 1. Сбор событий

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import json
import uuid

class EventType(Enum):
    INPUT_RECEIVED = "input_received"
    INJECTION_DETECTED = "injection_detected"
    TOOL_INVOKED = "tool_invoked"
    OUTPUT_GENERATED = "output_generated"
    POLICY_VIOLATION = "policy_violation"
    DATA_LEAKAGE = "data_leakage"
    RATE_LIMIT_HIT = "rate_limit_hit"
    AUTHENTICATION_FAILED = "authentication_failed"

@dataclass
class SecurityEvent:
    """Событие безопасности для мониторинга."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: EventType = EventType.INPUT_RECEIVED
    session_id: str = ""
    user_id: str = ""
    severity: str = "info"  # info, warning, error, critical
    data: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "severity": self.severity,
            "data": self.data,
            "context": self.context
        }

class EventCollector:
    """Сбор и пересылка событий безопасности."""
    
    def __init__(self, sinks: list):
        self.sinks = sinks  # Места назначения логов
        self.buffer = []
        self.buffer_size = 100
    
    def emit(self, event: SecurityEvent):
        """Эмитировать событие безопасности."""
        
        self.buffer.append(event)
        
        # Немедленный flush для критических событий
        if event.severity == "critical":
            self._flush_immediate(event)
        
        # Flush при заполнении буфера
        if len(self.buffer) >= self.buffer_size:
            self._flush_batch()
    
    def _flush_immediate(self, event: SecurityEvent):
        """Немедленная отправка критического события."""
        for sink in self.sinks:
            sink.send_immediate(event)
    
    def _flush_batch(self):
        """Пакетная отправка событий."""
        if not self.buffer:
            return
        
        for sink in self.sinks:
            sink.send_batch(self.buffer)
        
        self.buffer = []
```

---

### 2. Real-time детекция

```python
class RealTimeDetector:
    """Детекция атак в реальном времени."""
    
    def __init__(self, event_collector: EventCollector):
        self.collector = event_collector
        self.session_scores = {}  # session_id -> risk_score
        self.user_history = {}    # user_id -> recent events
    
    def process_input(
        self, 
        text: str, 
        session_id: str, 
        user_id: str
    ) -> dict:
        """Обработка входных данных для real-time детекции."""
        
        # Детекция паттернов
        patterns = self._detect_patterns(text)
        
        # Обновление risk score сессии
        self._update_session_score(session_id, patterns)
        
        # Проверка на эскалацию
        escalation = self._check_escalation(session_id)
        
        # Эмитирование событий
        if patterns["is_suspicious"]:
            self.collector.emit(SecurityEvent(
                event_type=EventType.INJECTION_DETECTED,
                session_id=session_id,
                user_id=user_id,
                severity="warning" if patterns["risk"] < 0.8 else "error",
                data={
                    "patterns": patterns["matched"],
                    "risk_score": patterns["risk"]
                }
            ))
        
        if escalation["detected"]:
            self.collector.emit(SecurityEvent(
                event_type=EventType.POLICY_VIOLATION,
                session_id=session_id,
                user_id=user_id,
                severity="critical",
                data={
                    "type": "attack_escalation",
                    "trajectory": escalation["trajectory"]
                }
            ))
        
        return {
            "allow": not escalation["detected"],
            "patterns": patterns,
            "session_risk": self.session_scores.get(session_id, 0)
        }
    
    def _detect_patterns(self, text: str) -> dict:
        """Детекция паттернов атак."""
        import re
        
        patterns = [
            (r'ignore.*instructions', 0.8),
            (r'system.*prompt', 0.6),
            (r'you are now', 0.7),
            (r'DAN|jailbreak', 0.9),
        ]
        
        matched = []
        max_risk = 0
        
        for pattern, risk in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matched.append(pattern)
                max_risk = max(max_risk, risk)
        
        return {
            "is_suspicious": max_risk > 0.5,
            "matched": matched,
            "risk": max_risk
        }
    
    def _update_session_score(self, session_id: str, patterns: dict):
        """Обновление risk score сессии."""
        
        current = self.session_scores.get(session_id, 0)
        
        # Увеличение при подозрительных паттернах
        if patterns["is_suspicious"]:
            current = min(current + patterns["risk"] * 0.3, 1.0)
        else:
            # Decay со временем (benign inputs снижают score)
            current = max(current - 0.05, 0)
        
        self.session_scores[session_id] = current
    
    def _check_escalation(self, session_id: str) -> dict:
        """Проверка на паттерны эскалации атаки."""
        
        score = self.session_scores.get(session_id, 0)
        
        return {
            "detected": score >= 0.8,
            "trajectory": "increasing" if score > 0.5 else "stable"
        }
```

---

### 3. Анализ сессий

```python
class SessionAnalyzer:
    """Анализ сессий разговоров на предмет атак."""
    
    def __init__(self):
        self.sessions = {}  # session_id -> история разговора
    
    def add_turn(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        metadata: dict = None
    ):
        """Добавление хода разговора."""
        
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        self.sessions[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
    
    def analyze_trajectory(self, session_id: str) -> dict:
        """Анализ траектории разговора на предмет атак."""
        
        if session_id not in self.sessions:
            return {"analysis": None}
        
        turns = self.sessions[session_id]
        
        # Извлечение признаков
        features = {
            "turn_count": len(turns),
            "user_turn_lengths": [
                len(t["content"]) for t in turns if t["role"] == "user"
            ],
            "escalation_pattern": self._detect_escalation(turns),
            "topic_drift": self._detect_topic_drift(turns),
            "repeated_attempts": self._detect_repeated_attempts(turns),
        }
        
        # Расчёт риска
        risk_score = self._calculate_trajectory_risk(features)
        
        return {
            "features": features,
            "risk_score": risk_score,
            "is_attack": risk_score > 0.7,
            "attack_type": self._classify_attack(features) if risk_score > 0.7 else None
        }
    
    def _detect_escalation(self, turns: list) -> dict:
        """Детекция паттернов эскалации атаки."""
        
        user_turns = [t for t in turns if t["role"] == "user"]
        
        if len(user_turns) < 3:
            return {"detected": False}
        
        # Проверка, становится ли каждый ход более агрессивным
        aggression_scores = []
        for turn in user_turns:
            score = self._score_aggression(turn["content"])
            aggression_scores.append(score)
        
        # Проверка на возрастающий тренд
        is_escalating = all(
            aggression_scores[i] <= aggression_scores[i+1]
            for i in range(len(aggression_scores) - 1)
        )
        
        return {
            "detected": is_escalating and aggression_scores[-1] > 0.5,
            "scores": aggression_scores
        }
    
    def _detect_repeated_attempts(self, turns: list) -> dict:
        """Детекция повторных попыток jailbreak."""
        
        user_turns = [t["content"] for t in turns if t["role"] == "user"]
        
        # Проверка семантического сходства между попытками
        similar_pairs = 0
        for i in range(len(user_turns)):
            for j in range(i + 1, len(user_turns)):
                if self._are_similar(user_turns[i], user_turns[j]):
                    similar_pairs += 1
        
        return {
            "detected": similar_pairs >= 2,
            "similar_pairs": similar_pairs
        }
```

---

### 4. Alerting

```python
class AlertManager:
    """Управление alerts безопасности."""
    
    ALERT_RULES = [
        {
            "name": "critical_injection",
            "condition": lambda e: e.event_type == EventType.INJECTION_DETECTED and e.severity == "critical",
            "action": "page_on_call",
            "cooldown_seconds": 60
        },
        {
            "name": "data_leakage",
            "condition": lambda e: e.event_type == EventType.DATA_LEAKAGE,
            "action": "page_on_call",
            "cooldown_seconds": 0  # Всегда alert
        },
        {
            "name": "high_volume_jailbreak",
            "condition": lambda e: e.event_type == EventType.INJECTION_DETECTED,
            "action": "notify_security",
            "aggregate": True,
            "threshold": 10,
            "window_seconds": 60
        },
    ]
    
    def __init__(self, notifiers: dict):
        self.notifiers = notifiers  # action -> notifier
        self.alert_counts = {}      # rule_name -> count
        self.last_alerts = {}       # rule_name -> timestamp
    
    def process_event(self, event: SecurityEvent):
        """Обработка события и триггер alerts."""
        
        for rule in self.ALERT_RULES:
            if not rule["condition"](event):
                continue
            
            # Проверка cooldown
            if not self._check_cooldown(rule):
                continue
            
            # Обработка агрегации
            if rule.get("aggregate"):
                if self._should_aggregate(rule, event):
                    continue
            
            # Отправка alert
            self._send_alert(rule, event)
    
    def _send_alert(self, rule: dict, event: SecurityEvent):
        """Отправка alert через соответствующий канал."""
        
        action = rule["action"]
        notifier = self.notifiers.get(action)
        
        if notifier:
            notifier.send({
                "rule": rule["name"],
                "event": event.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        self.last_alerts[rule["name"]] = datetime.utcnow()
```

---

### 5. Forensic Logging

```python
class ForensicLogger:
    """Детальное логирование для расследования инцидентов."""
    
    def __init__(self, storage):
        self.storage = storage
    
    def log_interaction(
        self,
        session_id: str,
        user_input: str,
        model_output: str,
        analysis_results: dict,
        tool_calls: list = None
    ):
        """Логирование полного взаимодействия для forensics."""
        
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "interaction": {
                "input": user_input,
                "output": model_output,
                "input_hash": self._hash(user_input),
                "output_hash": self._hash(model_output),
            },
            "analysis": analysis_results,
            "tool_calls": tool_calls or [],
            "retention_policy": "security",  # Более длительное хранение
        }
        
        # Хранение с integrity
        signed_record = self._sign_record(record)
        self.storage.store(signed_record)
    
    def search_incidents(
        self,
        session_id: str = None,
        user_id: str = None,
        time_range: tuple = None,
        event_types: list = None
    ) -> list:
        """Поиск логов для расследования инцидентов."""
        
        query = {}
        
        if session_id:
            query["session_id"] = session_id
        if user_id:
            query["user_id"] = user_id
        if time_range:
            query["timestamp"] = {"$gte": time_range[0], "$lte": time_range[1]}
        if event_types:
            query["analysis.event_type"] = {"$in": event_types}
        
        return self.storage.search(query)
```

---

## Интеграция SENTINEL

```python
from sentinel import configure, Monitor

configure(
    monitoring=True,
    real_time_detection=True,
    session_analysis=True,
    forensic_logging=True
)

monitor = Monitor(
    alert_on_critical=True,
    session_tracking=True,
    retention_days=90
)

@monitor.observe
def process_request(user_input: str, session_id: str):
    # Автоматически мониторится
    return llm.generate(user_input)
```

---

## Ключевые выводы

1. **Мониторь все слои** — Input, processing, output, session
2. **Real-time детекция** — Не жди логов
3. **Session context важен** — Multi-turn атаки требуют анализа траектории
4. **Alert appropriately** — Critical vs informational
5. **Логируй для forensics** — Детально, подписано, сохранено

---

## Следующий урок

→ [02. Incident Response](02-incident-response.md)

---

*AI Security Academy | Урок 05.3.1*
