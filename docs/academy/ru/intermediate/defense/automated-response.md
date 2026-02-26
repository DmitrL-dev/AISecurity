# Автоматический Response для AI Security

> **Уровень:** Продвинутый  
> **Время:** 50 минут  
> **Трек:** 05 — Defense Strategies  
> **Модуль:** 05.2 — Response  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять стратегии автоматического response для AI security
- [ ] Реализовать фреймворк response actions
- [ ] Построить пайплайн response orchestration
- [ ] Интегрировать автоматический response в SENTINEL

---

## 1. Обзор Response Framework

### 1.1 Стратегии Response

```
┌────────────────────────────────────────────────────────────────────┐
│              AUTOMATED RESPONSE FRAMEWORK                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Response Levels:                                                  │
│  ├── LOG: Записать событие, продолжить обработку                 │
│  ├── WARN: Log + alert, продолжить с осторожностью               │
│  ├── THROTTLE: Rate limit agent/session                          │
│  ├── BLOCK: Заблокировать текущий запрос                         │
│  ├── SUSPEND: Приостановить агента временно                      │
│  └── TERMINATE: Завершить session/agent                          │
│                                                                    │
│  Response Types:                                                   │
│  ├── Immediate: Block, redact, transform                         │
│  ├── Delayed: Alert, escalate, review queue                      │
│  └── Adaptive: Динамическая корректировка security level         │
│                                                                    │
│  Trigger Sources:                                                  │
│  ├── Detection Engine: Anomaly, pattern match                    │
│  ├── Policy Engine: Policy violation                             │
│  ├── RBAC Engine: Permission denied                              │
│  └── External: SIEM, manual trigger                              │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Response Actions

### 2.1 Определение Action

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from datetime import datetime, timedelta
import threading

class ResponseLevel(Enum):
    LOG = 0
    WARN = 1
    THROTTLE = 2
    BLOCK = 3
    SUSPEND = 4
    TERMINATE = 5

class ActionType(Enum):
    LOG = "log"
    ALERT = "alert"
    BLOCK_REQUEST = "block_request"
    REDACT_OUTPUT = "redact_output"
    THROTTLE = "throttle"
    SUSPEND_AGENT = "suspend_agent"
    TERMINATE_SESSION = "terminate_session"
    QUARANTINE = "quarantine"
    ESCALATE = "escalate"
    CUSTOM = "custom"

@dataclass
class ResponseAction:
    """Единичный response action"""
    action_type: ActionType
    level: ResponseLevel
    parameters: Dict = field(default_factory=dict)
    
    # Execution
    handler: Optional[Callable] = None
    timeout_seconds: float = 10.0
    
    # Metadata
    description: str = ""
    requires_confirmation: bool = False

@dataclass
class ResponseRule:
    """Правило маппинга trigger на actions"""
    rule_id: str
    name: str
    description: str
    
    # Trigger conditions
    trigger_type: str  # e.g., "attack_detected", "policy_violation"
    conditions: Dict = field(default_factory=dict)
    
    # Response
    actions: List[ResponseAction] = field(default_factory=list)
    level: ResponseLevel = ResponseLevel.LOG
    
    # Control
    enabled: bool = True
    cooldown_seconds: int = 60
    max_triggers_per_hour: int = 100
    
    def matches(self, event: Dict) -> bool:
        """Проверить соответствует ли событие условиям правила"""
        if event.get('type') != self.trigger_type:
            return False
        
        for key, expected in self.conditions.items():
            actual = event.get(key)
            
            if isinstance(expected, dict):
                # Complex conditions
                if 'min' in expected and actual < expected['min']:
                    return False
                if 'max' in expected and actual > expected['max']:
                    return False
                if 'in' in expected and actual not in expected['in']:
                    return False
            else:
                if actual != expected:
                    return False
        
        return True

@dataclass
class ResponseEvent:
    """Событие, триггерящее response"""
    event_id: str
    timestamp: datetime
    type: str  # attack_detected, policy_violation, etc.
    severity: str
    
    # Context
    agent_id: str
    session_id: str
    user_id: str
    
    # Details
    details: Dict = field(default_factory=dict)
    source: str = ""  # detection_engine, policy_engine, etc.
```

### 2.2 Action Handlers

```python
from abc import ABC, abstractmethod
import logging

class ActionHandler(ABC):
    """Базовый action handler"""
    
    @abstractmethod
    def execute(self, action: ResponseAction, event: ResponseEvent) -> Dict:
        pass
    
    @property
    @abstractmethod
    def action_type(self) -> ActionType:
        pass

class LogActionHandler(ActionHandler):
    """Logging action"""
    
    def __init__(self):
        self.logger = logging.getLogger("security")
    
    @property
    def action_type(self) -> ActionType:
        return ActionType.LOG
    
    def execute(self, action: ResponseAction, event: ResponseEvent) -> Dict:
        log_level = action.parameters.get('level', 'warning')
        
        message = (
            f"[{event.type}] Agent: {event.agent_id}, "
            f"Session: {event.session_id}, Details: {event.details}"
        )
        
        getattr(self.logger, log_level)(message)
        
        return {
            'success': True,
            'logged': True,
            'message': message
        }

class BlockRequestHandler(ActionHandler):
    """Block request action"""
    
    def __init__(self):
        self.blocked_requests: Dict[str, datetime] = {}
    
    @property
    def action_type(self) -> ActionType:
        return ActionType.BLOCK_REQUEST
    
    def execute(self, action: ResponseAction, event: ResponseEvent) -> Dict:
        block_key = f"{event.session_id}:{event.event_id}"
        self.blocked_requests[block_key] = datetime.utcnow()
        
        return {
            'success': True,
            'blocked': True,
            'reason': action.parameters.get('reason', 'Security violation')
        }

class ThrottleHandler(ActionHandler):
    """Throttle action"""
    
    def __init__(self):
        self.throttled: Dict[str, Dict] = {}
        self.lock = threading.RLock()
    
    @property
    def action_type(self) -> ActionType:
        return ActionType.THROTTLE
    
    def execute(self, action: ResponseAction, event: ResponseEvent) -> Dict:
        with self.lock:
            duration = action.parameters.get('duration_seconds', 60)
            rate = action.parameters.get('requests_per_minute', 10)
            
            self.throttled[event.agent_id] = {
                'until': datetime.utcnow() + timedelta(seconds=duration),
                'rate_limit': rate
            }
            
            return {
                'success': True,
                'throttled': True,
                'duration_seconds': duration,
                'rate_limit': rate
            }
    
    def is_throttled(self, agent_id: str) -> tuple[bool, Optional[int]]:
        """Проверить находится ли агент под throttling"""
        with self.lock:
            if agent_id not in self.throttled:
                return False, None
            
            info = self.throttled[agent_id]
            if datetime.utcnow() >= info['until']:
                del self.throttled[agent_id]
                return False, None
            
            return True, info['rate_limit']

class SuspendAgentHandler(ActionHandler):
    """Suspend agent action"""
    
    def __init__(self):
        self.suspended: Dict[str, datetime] = {}
    
    @property
    def action_type(self) -> ActionType:
        return ActionType.SUSPEND_AGENT
    
    def execute(self, action: ResponseAction, event: ResponseEvent) -> Dict:
        duration = action.parameters.get('duration_seconds', 300)
        
        self.suspended[event.agent_id] = datetime.utcnow() + timedelta(seconds=duration)
        
        return {
            'success': True,
            'suspended': True,
            'agent_id': event.agent_id,
            'duration_seconds': duration
        }
    
    def is_suspended(self, agent_id: str) -> bool:
        if agent_id not in self.suspended:
            return False
        
        if datetime.utcnow() >= self.suspended[agent_id]:
            del self.suspended[agent_id]
            return False
        
        return True
```

---

## 3. Response Orchestrator

```python
from collections import defaultdict
import uuid

@dataclass
class ResponseResult:
    """Результат выполнения response"""
    event_id: str
    rule_id: str
    success: bool
    actions_executed: List[Dict]
    errors: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

class ResponseOrchestrator:
    """Оркестрирует выполнение response"""
    
    def __init__(self):
        self.rules: Dict[str, ResponseRule] = {}
        self.handlers: Dict[ActionType, ActionHandler] = {}
        
        # Rate limiting
        self.rule_triggers: Dict[str, List[datetime]] = defaultdict(list)
        self.last_trigger: Dict[str, datetime] = {}
        
        # History
        self.response_history: List[ResponseResult] = []
        self.max_history = 10000
    
    def register_handler(self, handler: ActionHandler):
        """Зарегистрировать action handler"""
        self.handlers[handler.action_type] = handler
    
    def add_rule(self, rule: ResponseRule):
        """Добавить response правило"""
        self.rules[rule.rule_id] = rule
    
    def process_event(self, event: ResponseEvent) -> List[ResponseResult]:
        """Обработать событие и выполнить matching responses"""
        results = []
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            if not rule.matches(event.__dict__):
                continue
            
            if not self._check_rate_limit(rule):
                continue
            
            result = self._execute_rule(rule, event)
            results.append(result)
            
            self._record_trigger(rule)
        
        return results
    
    def _check_rate_limit(self, rule: ResponseRule) -> bool:
        """Проверить можно ли триггерить правило"""
        now = datetime.utcnow()
        
        # Cooldown check
        last = self.last_trigger.get(rule.rule_id)
        if last and (now - last).total_seconds() < rule.cooldown_seconds:
            return False
        
        # Rate limit check
        hour_ago = now - timedelta(hours=1)
        recent = [t for t in self.rule_triggers[rule.rule_id] if t >= hour_ago]
        self.rule_triggers[rule.rule_id] = recent
        
        return len(recent) < rule.max_triggers_per_hour
    
    def _execute_rule(self, rule: ResponseRule, event: ResponseEvent) -> ResponseResult:
        """Выполнить все actions для правила"""
        actions_executed = []
        errors = []
        
        for action in rule.actions:
            handler = self.handlers.get(action.action_type)
            
            if not handler:
                errors.append(f"Нет handler для {action.action_type}")
                continue
            
            try:
                result = handler.execute(action, event)
                actions_executed.append({
                    'action_type': action.action_type.value,
                    'result': result
                })
            except Exception as e:
                errors.append(f"Action {action.action_type} failed: {e}")
        
        return ResponseResult(
            event_id=event.event_id,
            rule_id=rule.rule_id,
            success=len(errors) == 0,
            actions_executed=actions_executed,
            errors=errors
        )
    
    def get_stats(self) -> Dict:
        """Получить статистику response"""
        if not self.response_history:
            return {'total_responses': 0}
        
        by_rule = defaultdict(int)
        by_success = defaultdict(int)
        
        for result in self.response_history:
            by_rule[result.rule_id] += 1
            by_success[result.success] += 1
        
        return {
            'total_responses': len(self.response_history),
            'by_rule': dict(by_rule),
            'success_rate': by_success[True] / len(self.response_history)
        }
```

---

## 4. Предустановленные Response Rules

```python
class DefaultResponseRules:
    """Правила security response по умолчанию"""
    
    @staticmethod
    def get_all() -> List[ResponseRule]:
        return [
            # Attack detected - high severity
            ResponseRule(
                rule_id="attack-high",
                name="High Severity Attack Response",
                description="Block и alert при high severity атаках",
                trigger_type="attack_detected",
                conditions={'severity': 'high'},
                level=ResponseLevel.BLOCK,
                actions=[
                    ResponseAction(ActionType.BLOCK_REQUEST, ResponseLevel.BLOCK,
                                  {'reason': 'High severity attack detected'}),
                    ResponseAction(ActionType.ALERT, ResponseLevel.WARN,
                                  {'message': 'High severity attack blocked'}),
                    ResponseAction(ActionType.LOG, ResponseLevel.LOG)
                ]
            ),
            
            # Attack detected - medium severity
            ResponseRule(
                rule_id="attack-medium",
                name="Medium Severity Attack Response",
                description="Throttle и мониторинг при medium severity атаках",
                trigger_type="attack_detected",
                conditions={'severity': 'medium'},
                level=ResponseLevel.THROTTLE,
                actions=[
                    ResponseAction(ActionType.THROTTLE, ResponseLevel.THROTTLE,
                                  {'duration_seconds': 60, 'requests_per_minute': 5}),
                    ResponseAction(ActionType.LOG, ResponseLevel.LOG)
                ]
            ),
            
            # Policy violation
            ResponseRule(
                rule_id="policy-violation",
                name="Policy Violation Response",
                description="Block policy violations",
                trigger_type="policy_violation",
                conditions={},
                level=ResponseLevel.BLOCK,
                actions=[
                    ResponseAction(ActionType.BLOCK_REQUEST, ResponseLevel.BLOCK,
                                  {'reason': 'Policy violation'}),
                    ResponseAction(ActionType.LOG, ResponseLevel.LOG)
                ]
            ),
            
            # Repeated failures
            ResponseRule(
                rule_id="repeated-failures",
                name="Repeated Failures Response",
                description="Suspend агента с слишком многими failures",
                trigger_type="repeated_failures",
                conditions={'failure_count': {'min': 5}},
                level=ResponseLevel.SUSPEND,
                actions=[
                    ResponseAction(ActionType.SUSPEND_AGENT, ResponseLevel.SUSPEND,
                                  {'duration_seconds': 300}),
                    ResponseAction(ActionType.ALERT, ResponseLevel.WARN,
                                  {'message': 'Agent suspended из-за failures'})
                ]
            )
        ]
```

---

## 5. Интеграция с SENTINEL

```python
from dataclasses import dataclass

@dataclass
class ResponseConfig:
    """Конфигурация response engine"""
    enable_default_rules: bool = True
    max_history: int = 10000
    alert_callbacks: List[Callable] = field(default_factory=list)

class SENTINELResponseEngine:
    """Response engine для SENTINEL framework"""
    
    def __init__(self, config: ResponseConfig):
        self.config = config
        self.orchestrator = ResponseOrchestrator()
        
        # Register handlers
        self.log_handler = LogActionHandler()
        self.block_handler = BlockRequestHandler()
        self.throttle_handler = ThrottleHandler()
        self.suspend_handler = SuspendAgentHandler()
        
        self.orchestrator.register_handler(self.log_handler)
        self.orchestrator.register_handler(self.block_handler)
        self.orchestrator.register_handler(self.throttle_handler)
        self.orchestrator.register_handler(self.suspend_handler)
        
        # Load default rules
        if config.enable_default_rules:
            for rule in DefaultResponseRules.get_all():
                self.orchestrator.add_rule(rule)
    
    def process_detection(self, detection_type: str, severity: str,
                          agent_id: str, session_id: str, user_id: str,
                          details: Dict = None) -> List[ResponseResult]:
        """Обработать detection event"""
        event = ResponseEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            type=detection_type,
            severity=severity,
            agent_id=agent_id,
            session_id=session_id,
            user_id=user_id,
            details=details or {},
            source="detection_engine"
        )
        
        return self.orchestrator.process_event(event)
    
    def is_agent_blocked(self, agent_id: str) -> bool:
        """Проверить заблокирован ли агент"""
        return self.suspend_handler.is_suspended(agent_id)
    
    def is_throttled(self, agent_id: str) -> tuple[bool, Optional[int]]:
        """Проверить throttled ли агент"""
        return self.throttle_handler.is_throttled(agent_id)
    
    def get_stats(self) -> Dict:
        """Получить статистику response"""
        return self.orchestrator.get_stats()
```

---

## 6. Итоги

| Компонент | Описание |
|-----------|----------|
| **ResponseAction** | Единичный action (block, alert) |
| **ResponseRule** | Trigger conditions → actions |
| **ActionHandler** | Выполнение action |
| **Orchestrator** | Rate limiting + execution |
| **DefaultRules** | Предустановленные security rules |

---

## Следующий урок

→ [Трек 06: Advanced](../../06-advanced/README.md)

---

*AI Security Academy | Трек 05: Defense Strategies | Модуль 05.2: Response*
