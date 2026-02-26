# Audit Trail для AI систем

> **Уровень:** Продвинутый  
> **Время:** 45 минут  
> **Трек:** 07 — Governance  
> **Модуль:** 07.2 — Audit  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять требования к AI audit trail
- [ ] Реализовать комплексное audit логирование
- [ ] Построить возможности audit query и анализа
- [ ] Интегрировать audit trail в SENTINEL

---

## 1. Обзор Audit Trail

### 1.1 Зачем Audit Trail для AI?

```
┌────────────────────────────────────────────────────────────────────┐
│              ТРЕБОВАНИЯ К AI AUDIT TRAIL                           │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Регуляторные требования:                                          │
│  ├── EU AI Act: Хранить логи для high-risk систем                 │
│  ├── SOC 2: Демонстрировать эффективность контролей              │
│  └── GDPR: Записывать активности обработки данных                 │
│                                                                    │
│  Требования безопасности:                                          │
│  ├── Incident Investigation: Что произошло и когда               │
│  ├── Attack Detection: Pattern analysis по логам                  │
│  └── Forensics: Доказательства для security incidents             │
│                                                                    │
│  Операционные требования:                                          │
│  ├── Debugging: Трассировка issues до root cause                  │
│  ├── Performance: Идентификация bottlenecks                       │
│  └── Usage Analytics: Понимание использования системы             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Модель Audit Event

### 2.1 Основные сущности

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import hashlib
import json

class AuditEventType(Enum):
    # Request/Response события
    REQUEST_RECEIVED = "request_received"
    RESPONSE_GENERATED = "response_generated"
    
    # Security события
    SECURITY_VIOLATION = "security_violation"
    ACCESS_DENIED = "access_denied"
    ATTACK_DETECTED = "attack_detected"
    POLICY_VIOLATION = "policy_violation"
    
    # System события
    TOOL_INVOKED = "tool_invoked"
    DATA_ACCESSED = "data_accessed"
    CONFIG_CHANGED = "config_changed"
    
    # Agent события
    AGENT_CREATED = "agent_created"
    AGENT_PERMISSION_CHANGED = "agent_permission_changed"
    AGENT_TERMINATED = "agent_terminated"
    
    # Approval события
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"

class AuditSeverity(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Полное audit событие"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    
    # Контекст
    session_id: str
    user_id: str
    agent_id: str
    system_id: str
    
    # Детали события
    action: str
    resource: str
    outcome: str  # success, failure, blocked
    
    # Rich data
    request_data: Dict = field(default_factory=dict)
    response_data: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    
    # Tracing
    trace_id: str = ""
    parent_event_id: str = ""
    
    # Integrity
    event_hash: str = ""
    previous_hash: str = ""
    
    def __post_init__(self):
        if not self.event_hash:
            self.event_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Вычислить hash для верификации integrity"""
        data = {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type.value,
            'action': self.action,
            'resource': self.resource,
            'outcome': self.outcome,
            'previous_hash': self.previous_hash
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Проверить что событие не было изменено"""
        return self.event_hash == self._compute_hash()
    
    def to_dict(self) -> dict:
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type.value,
            'severity': self.severity.value,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'agent_id': self.agent_id,
            'action': self.action,
            'resource': self.resource,
            'outcome': self.outcome,
            'metadata': self.metadata,
            'event_hash': self.event_hash
        }

@dataclass
class AuditChain:
    """Цепочка audit событий с верификацией integrity"""
    chain_id: str
    events: List[AuditEvent] = field(default_factory=list)
    
    def add_event(self, event: AuditEvent):
        """Добавить событие в цепочку с hash linking"""
        if self.events:
            event.previous_hash = self.events[-1].event_hash
            event.event_hash = event._compute_hash()
        self.events.append(event)
    
    def verify_chain(self) -> bool:
        """Верифицировать integrity всей цепочки"""
        for i, event in enumerate(self.events):
            if not event.verify_integrity():
                return False
            if i > 0 and event.previous_hash != self.events[i-1].event_hash:
                return False
        return True
```

---

## 3. Audit Logger

### 3.1 Реализация Logger

```python
from abc import ABC, abstractmethod
from collections import defaultdict
import threading
import queue
import uuid

class AuditBackend(ABC):
    """Абстрактный audit storage backend"""
    
    @abstractmethod
    def write(self, event: AuditEvent):
        pass
    
    @abstractmethod
    def query(self, filters: Dict) -> List[AuditEvent]:
        pass

class InMemoryAuditBackend(AuditBackend):
    """In-memory backend для разработки"""
    
    def __init__(self, max_events: int = 100000):
        self.events: List[AuditEvent] = []
        self.max_events = max_events
        self.lock = threading.RLock()
        
        # Индексы
        self.by_session: Dict[str, List[int]] = defaultdict(list)
        self.by_user: Dict[str, List[int]] = defaultdict(list)
        self.by_type: Dict[str, List[int]] = defaultdict(list)
    
    def write(self, event: AuditEvent):
        with self.lock:
            idx = len(self.events)
            self.events.append(event)
            
            # Обновить индексы
            self.by_session[event.session_id].append(idx)
            self.by_user[event.user_id].append(idx)
            self.by_type[event.event_type.value].append(idx)
            
            # Trim при необходимости
            if len(self.events) > self.max_events:
                self._trim()
    
    def query(self, filters: Dict) -> List[AuditEvent]:
        with self.lock:
            candidates = None
            
            # Использовать индексы если доступны
            if 'session_id' in filters:
                indices = self.by_session.get(filters['session_id'], [])
                candidates = set(indices)
            
            if 'user_id' in filters:
                indices = self.by_user.get(filters['user_id'], [])
                if candidates is None:
                    candidates = set(indices)
                else:
                    candidates &= set(indices)
            
            if 'event_type' in filters:
                indices = self.by_type.get(filters['event_type'], [])
                if candidates is None:
                    candidates = set(indices)
                else:
                    candidates &= set(indices)
            
            # Если индекс не использован, сканировать все
            if candidates is None:
                candidates = set(range(len(self.events)))
            
            # Фильтровать кандидатов
            results = []
            for idx in sorted(candidates, reverse=True):
                event = self.events[idx]
                if self._matches_filters(event, filters):
                    results.append(event)
                    if 'limit' in filters and len(results) >= filters['limit']:
                        break
            
            return results
    
    def _matches_filters(self, event: AuditEvent, filters: Dict) -> bool:
        if 'start_time' in filters and event.timestamp < filters['start_time']:
            return False
        if 'end_time' in filters and event.timestamp > filters['end_time']:
            return False
        if 'severity' in filters and event.severity.value != filters['severity']:
            return False
        if 'outcome' in filters and event.outcome != filters['outcome']:
            return False
        return True

class AuditLogger:
    """Главный audit logger"""
    
    def __init__(self, backend: AuditBackend, async_mode: bool = True):
        self.backend = backend
        self.async_mode = async_mode
        self.chain = AuditChain(chain_id=str(uuid.uuid4()))
        
        if async_mode:
            self.queue = queue.Queue(maxsize=10000)
            self.worker = threading.Thread(target=self._process_queue, daemon=True)
            self.worker.start()
    
    def log(self, event_type: AuditEventType, severity: AuditSeverity,
            session_id: str, user_id: str, agent_id: str,
            action: str, resource: str, outcome: str,
            request_data: Dict = None, response_data: Dict = None,
            metadata: Dict = None, system_id: str = "default") -> str:
        """Логировать audit событие"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            system_id=system_id,
            action=action,
            resource=resource,
            outcome=outcome,
            request_data=request_data or {},
            response_data=response_data or {},
            metadata=metadata or {}
        )
        
        if self.async_mode:
            try:
                self.queue.put_nowait(event)
            except queue.Full:
                self.chain.add_event(event)
                self.backend.write(event)
        else:
            self.chain.add_event(event)
            self.backend.write(event)
        
        return event.event_id
    
    # Convenience методы
    def log_request(self, session_id: str, user_id: str, agent_id: str,
                    request_data: Dict) -> str:
        return self.log(
            AuditEventType.REQUEST_RECEIVED,
            AuditSeverity.INFO,
            session_id, user_id, agent_id,
            "process_request", "input",
            "received",
            request_data=request_data
        )
    
    def log_security_violation(self, session_id: str, user_id: str, agent_id: str,
                               violation_type: str, details: Dict) -> str:
        return self.log(
            AuditEventType.SECURITY_VIOLATION,
            AuditSeverity.WARNING,
            session_id, user_id, agent_id,
            violation_type, "security",
            "blocked",
            metadata=details
        )
    
    def log_attack_detected(self, session_id: str, user_id: str, agent_id: str,
                            attack_type: str, confidence: float, details: Dict) -> str:
        return self.log(
            AuditEventType.ATTACK_DETECTED,
            AuditSeverity.CRITICAL,
            session_id, user_id, agent_id,
            attack_type, "security",
            "detected",
            metadata={**details, 'confidence': confidence}
        )
    
    def query(self, **filters) -> List[AuditEvent]:
        return self.backend.query(filters)
    
    def verify_chain_integrity(self) -> bool:
        return self.chain.verify_chain()
```

---

## 4. Audit Analysis

### 4.1 Audit Analyzer

```python
from collections import Counter

class AuditAnalyzer:
    """Анализ audit логов для insights"""
    
    def __init__(self, logger: AuditLogger):
        self.logger = logger
    
    def get_security_summary(self, hours: int = 24) -> Dict:
        """Получить сводку security событий"""
        from datetime import timedelta
        start = datetime.utcnow() - timedelta(hours=hours)
        
        security_types = [
            AuditEventType.SECURITY_VIOLATION.value,
            AuditEventType.ACCESS_DENIED.value,
            AuditEventType.ATTACK_DETECTED.value,
            AuditEventType.POLICY_VIOLATION.value
        ]
        
        events = []
        for event_type in security_types:
            events.extend(self.logger.query(
                event_type=event_type,
                start_time=start
            ))
        
        # Агрегация
        by_type = Counter(e.event_type.value for e in events)
        by_severity = Counter(e.severity.value for e in events)
        by_agent = Counter(e.agent_id for e in events)
        by_user = Counter(e.user_id for e in events)
        
        return {
            'total_events': len(events),
            'by_type': dict(by_type),
            'by_severity': dict(by_severity),
            'top_agents': dict(by_agent.most_common(5)),
            'top_users': dict(by_user.most_common(5)),
            'period_hours': hours
        }
    
    def detect_anomalies(self, session_id: str) -> List[Dict]:
        """Детекция аномалий в сессии"""
        events = self.logger.query(session_id=session_id)
        
        anomalies = []
        
        # Проверка rapid requests
        if len(events) > 1:
            times = [e.timestamp for e in events]
            intervals = [(times[i+1] - times[i]).total_seconds() 
                        for i in range(len(times)-1)]
            
            if any(i < 0.1 for i in intervals):
                anomalies.append({
                    'type': 'rapid_requests',
                    'severity': 'medium',
                    'description': 'Обнаружен необычно высокий rate запросов'
                })
        
        # Проверка many failures
        failures = [e for e in events if e.outcome == 'failure']
        if len(failures) > len(events) * 0.5:
            anomalies.append({
                'type': 'high_failure_rate',
                'severity': 'high',
                'description': f'{len(failures)} failures из {len(events)} событий'
            })
        
        # Проверка security events
        security_events = [e for e in events 
                         if e.event_type in [AuditEventType.SECURITY_VIOLATION,
                                            AuditEventType.ACCESS_DENIED,
                                            AuditEventType.ATTACK_DETECTED]]
        if security_events:
            anomalies.append({
                'type': 'security_events',
                'severity': 'critical',
                'description': f'{len(security_events)} security событий в сессии',
                'events': [e.event_id for e in security_events]
            })
        
        return anomalies
    
    def generate_session_report(self, session_id: str) -> Dict:
        """Сгенерировать полный отчёт сессии"""
        events = self.logger.query(session_id=session_id)
        
        if not events:
            return {'session_id': session_id, 'status': 'not_found'}
        
        events = sorted(events, key=lambda e: e.timestamp)
        
        return {
            'session_id': session_id,
            'start_time': events[0].timestamp.isoformat(),
            'end_time': events[-1].timestamp.isoformat(),
            'duration_seconds': (events[-1].timestamp - events[0].timestamp).total_seconds(),
            'total_events': len(events),
            'event_types': dict(Counter(e.event_type.value for e in events)),
            'outcomes': dict(Counter(e.outcome for e in events)),
            'agents_involved': list(set(e.agent_id for e in events)),
            'anomalies': self.detect_anomalies(session_id)
        }
```

---

## 5. Интеграция с SENTINEL

```python
from dataclasses import dataclass

@dataclass
class AuditConfig:
    """Конфигурация audit engine"""
    async_mode: bool = True
    max_events: int = 100000
    retention_days: int = 90
    enable_integrity_check: bool = True

class SENTINELAuditEngine:
    """Audit engine для SENTINEL framework"""
    
    def __init__(self, config: AuditConfig):
        self.config = config
        self.backend = InMemoryAuditBackend(config.max_events)
        self.logger = AuditLogger(self.backend, config.async_mode)
        self.analyzer = AuditAnalyzer(self.logger)
    
    def log_request(self, session_id: str, user_id: str, agent_id: str,
                    request: Dict) -> str:
        return self.logger.log_request(session_id, user_id, agent_id, request)
    
    def log_response(self, session_id: str, user_id: str, agent_id: str,
                     response: Dict, outcome: str = "success") -> str:
        return self.logger.log(
            AuditEventType.RESPONSE_GENERATED,
            AuditSeverity.INFO,
            session_id, user_id, agent_id,
            "generate_response", "output",
            outcome,
            response_data=response
        )
    
    def log_attack(self, session_id: str, user_id: str, agent_id: str,
                   attack_type: str, confidence: float, details: Dict) -> str:
        return self.logger.log_attack_detected(
            session_id, user_id, agent_id,
            attack_type, confidence, details
        )
    
    def get_security_summary(self, hours: int = 24) -> Dict:
        return self.analyzer.get_security_summary(hours)
    
    def get_session_report(self, session_id: str) -> Dict:
        return self.analyzer.generate_session_report(session_id)
    
    def verify_integrity(self) -> bool:
        if not self.config.enable_integrity_check:
            return True
        return self.logger.verify_chain_integrity()
```

---

## 6. Итоги

| Компонент | Описание |
|-----------|----------|
| **AuditEvent** | Единица audit лога с hash |
| **AuditChain** | Цепочка событий с integrity |
| **Backend** | Storage (in-memory, DB) |
| **Logger** | Async логирование с convenience методами |
| **Analyzer** | Security summary, anomaly detection |

---

## Следующий урок

→ [Трек 08: Research](../../08-research/README.md)

---

*AI Security Academy | Трек 07: Governance | Модуль 07.2: Audit*
