# Automated Response for AI Security

> **Level:** Advanced  
> **Time:** 50 minutes  
> **Track:** 05 — Defense Strategies  
> **Module:** 05.2 — Response  
> **Version:** 1.0

---

## Learning Objectives

- [ ] Understand automated response strategies for AI security
- [ ] Implement response action framework
- [ ] Build response orchestration pipeline
- [ ] Integrate automated response into SENTINEL

---

## 1. Response Framework Overview

### 1.1 Response Strategies

```
┌────────────────────────────────────────────────────────────────────┐
│              AUTOMATED RESPONSE FRAMEWORK                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Response Levels:                                                  │
│  ├── LOG: Record event, continue processing                      │
│  ├── WARN: Log + alert, continue with caution                    │
│  ├── THROTTLE: Rate limit agent/session                          │
│  ├── BLOCK: Block current request                                │
│  ├── SUSPEND: Suspend agent temporarily                          │
│  └── TERMINATE: Terminate session/agent                          │
│                                                                    │
│  Response Types:                                                   │
│  ├── Immediate: Block, redact, transform                         │
│  ├── Delayed: Alert, escalate, review queue                      │
│  └── Adaptive: Adjust security level dynamically                 │
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

### 2.1 Action Definition

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
    """Single response action"""
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
    """Rule mapping trigger to actions"""
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
        """Check if event matches rule conditions"""
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
    """Event that triggers response"""
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
    """Base action handler"""
    
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
        """Check if agent is throttled"""
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

class AlertHandler(ActionHandler):
    """Alert action"""
    
    def __init__(self):
        self.alerts: List[Dict] = []
        self.callbacks: List[Callable] = []
    
    @property
    def action_type(self) -> ActionType:
        return ActionType.ALERT
    
    def register_callback(self, callback: Callable):
        self.callbacks.append(callback)
    
    def execute(self, action: ResponseAction, event: ResponseEvent) -> Dict:
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event.type,
            'severity': event.severity,
            'agent_id': event.agent_id,
            'session_id': event.session_id,
            'details': event.details,
            'message': action.parameters.get('message', f"Security alert: {event.type}")
        }
        
        self.alerts.append(alert)
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(alert)
            except:
                pass
        
        return {
            'success': True,
            'alerted': True,
            'alert': alert
        }
```

---

## 3. Response Orchestrator

```python
from collections import defaultdict
import uuid

@dataclass
class ResponseResult:
    """Result of response execution"""
    event_id: str
    rule_id: str
    success: bool
    actions_executed: List[Dict]
    errors: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

class ResponseOrchestrator:
    """Orchestrates response execution"""
    
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
        """Register action handler"""
        self.handlers[handler.action_type] = handler
    
    def add_rule(self, rule: ResponseRule):
        """Add response rule"""
        self.rules[rule.rule_id] = rule
    
    def remove_rule(self, rule_id: str):
        """Remove response rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
    
    def process_event(self, event: ResponseEvent) -> List[ResponseResult]:
        """Process event and execute matching responses"""
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
        """Check if rule can be triggered"""
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
    
    def _record_trigger(self, rule: ResponseRule):
        """Record rule trigger"""
        now = datetime.utcnow()
        self.last_trigger[rule.rule_id] = now
        self.rule_triggers[rule.rule_id].append(now)
    
    def _execute_rule(self, rule: ResponseRule, event: ResponseEvent) -> ResponseResult:
        """Execute all actions for a rule"""
        actions_executed = []
        errors = []
        
        for action in rule.actions:
            handler = self.handlers.get(action.action_type)
            
            if not handler:
                errors.append(f"No handler for {action.action_type}")
                continue
            
            try:
                result = handler.execute(action, event)
                actions_executed.append({
                    'action_type': action.action_type.value,
                    'result': result
                })
            except Exception as e:
                errors.append(f"Action {action.action_type} failed: {e}")
        
        response_result = ResponseResult(
            event_id=event.event_id,
            rule_id=rule.rule_id,
            success=len(errors) == 0,
            actions_executed=actions_executed,
            errors=errors
        )
        
        self._record_result(response_result)
        
        return response_result
    
    def _record_result(self, result: ResponseResult):
        """Record response result"""
        self.response_history.append(result)
        if len(self.response_history) > self.max_history:
            self.response_history = self.response_history[-self.max_history:]
    
    def get_stats(self) -> Dict:
        """Get response statistics"""
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

## 4. Pre-built Response Rules

```python
class DefaultResponseRules:
    """Default security response rules"""
    
    @staticmethod
    def get_all() -> List[ResponseRule]:
        return [
            # Attack detected - high severity
            ResponseRule(
                rule_id="attack-high",
                name="High Severity Attack Response",
                description="Block and alert on high severity attacks",
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
                description="Throttle and monitor on medium severity attacks",
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
                description="Suspend agent with too many failures",
                trigger_type="repeated_failures",
                conditions={'failure_count': {'min': 5}},
                level=ResponseLevel.SUSPEND,
                actions=[
                    ResponseAction(ActionType.SUSPEND_AGENT, ResponseLevel.SUSPEND,
                                  {'duration_seconds': 300}),
                    ResponseAction(ActionType.ALERT, ResponseLevel.WARN,
                                  {'message': 'Agent suspended due to failures'})
                ]
            ),
            
            # Rate limit exceeded
            ResponseRule(
                rule_id="rate-limit",
                name="Rate Limit Response",
                description="Throttle on rate limit exceeded",
                trigger_type="rate_limit_exceeded",
                conditions={},
                level=ResponseLevel.THROTTLE,
                actions=[
                    ResponseAction(ActionType.THROTTLE, ResponseLevel.THROTTLE,
                                  {'duration_seconds': 120, 'requests_per_minute': 10}),
                    ResponseAction(ActionType.LOG, ResponseLevel.LOG)
                ]
            )
        ]
```

---

## 5. SENTINEL Integration

```python
from dataclasses import dataclass

@dataclass
class ResponseConfig:
    """Response engine configuration"""
    enable_default_rules: bool = True
    max_history: int = 10000
    alert_callbacks: List[Callable] = field(default_factory=list)

class SENTINELResponseEngine:
    """Response engine for SENTINEL framework"""
    
    def __init__(self, config: ResponseConfig):
        self.config = config
        self.orchestrator = ResponseOrchestrator()
        
        # Register handlers
        self.log_handler = LogActionHandler()
        self.block_handler = BlockRequestHandler()
        self.throttle_handler = ThrottleHandler()
        self.suspend_handler = SuspendAgentHandler()
        self.alert_handler = AlertHandler()
        
        self.orchestrator.register_handler(self.log_handler)
        self.orchestrator.register_handler(self.block_handler)
        self.orchestrator.register_handler(self.throttle_handler)
        self.orchestrator.register_handler(self.suspend_handler)
        self.orchestrator.register_handler(self.alert_handler)
        
        # Alert callbacks
        for callback in config.alert_callbacks:
            self.alert_handler.register_callback(callback)
        
        # Load default rules
        if config.enable_default_rules:
            for rule in DefaultResponseRules.get_all():
                self.orchestrator.add_rule(rule)
    
    def process_detection(self, detection_type: str, severity: str,
                          agent_id: str, session_id: str, user_id: str,
                          details: Dict = None) -> List[ResponseResult]:
        """Process a detection event"""
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
        """Check if agent is blocked (suspended or throttled)"""
        return self.suspend_handler.is_suspended(agent_id)
    
    def is_throttled(self, agent_id: str) -> tuple[bool, Optional[int]]:
        """Check if agent is throttled"""
        return self.throttle_handler.is_throttled(agent_id)
    
    def add_custom_rule(self, rule: ResponseRule):
        """Add custom response rule"""
        self.orchestrator.add_rule(rule)
    
    def get_alerts(self, limit: int = 100) -> List[Dict]:
        """Get recent alerts"""
        return self.alert_handler.alerts[-limit:]
    
    def get_stats(self) -> Dict:
        """Get response statistics"""
        return self.orchestrator.get_stats()
```

---

## 6. Summary

| Component | Description |
|-----------|-------------|
| **ResponseAction** | Single action (block, alert) |
| **ResponseRule** | Trigger conditions → actions |
| **ActionHandler** | Action execution |
| **Orchestrator** | Rate limiting + execution |
| **DefaultRules** | Pre-built security rules |

---

## Next Lesson

→ [Track 06: Advanced](../../06-advanced/README.md)

---

*AI Security Academy | Track 05: Defense Strategies | Module 05.2: Response*
