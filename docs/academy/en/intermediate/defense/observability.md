# Monitoring and Observability

> **Lesson:** 05.3.1 - AI Security Monitoring  
> **Time:** 40 minutes  
> **Prerequisites:** Defense Layers basics

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Design monitoring for AI systems
2. Detect attacks in real-time
3. Build alerting for security events
4. Implement forensic logging

---

## Why Monitoring Matters

Traditional security monitoring misses AI-specific threats:

| Traditional | AI-Specific |
|------------|-------------|
| Network traffic | Prompt patterns |
| System logs | Conversation trajectories |
| Authentication | Semantic drift |
| Rate limiting | Attack progression |

---

## Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MONITORING LAYERS                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Layer 1: Input Monitoring                             │  │
│  │ • Injection pattern detection                         │  │
│  │ • Volume anomalies                                    │  │
│  │ • User behavior analysis                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Layer 2: Processing Monitoring                        │  │
│  │ • Token usage patterns                                │  │
│  │ • Latency anomalies                                   │  │
│  │ • Tool invocation patterns                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Layer 3: Output Monitoring                            │  │
│  │ • Content policy violations                           │  │
│  │ • Data leakage detection                              │  │
│  │ • Response anomalies                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Layer 4: Session Monitoring                           │  │
│  │ • Conversation trajectory analysis                    │  │
│  │ • Multi-turn attack detection                         │  │
│  │ • Session reputation scoring                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation

### 1. Event Collection

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
    """Security event for monitoring."""
    
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
    """Collect and forward security events."""
    
    def __init__(self, sinks: list):
        self.sinks = sinks  # Log destinations
        self.buffer = []
        self.buffer_size = 100
    
    def emit(self, event: SecurityEvent):
        """Emit a security event."""
        
        self.buffer.append(event)
        
        # Flush on critical events
        if event.severity == "critical":
            self._flush_immediate(event)
        
        # Flush when buffer full
        if len(self.buffer) >= self.buffer_size:
            self._flush_batch()
    
    def _flush_immediate(self, event: SecurityEvent):
        """Immediately send critical event."""
        for sink in self.sinks:
            sink.send_immediate(event)
    
    def _flush_batch(self):
        """Batch send events."""
        if not self.buffer:
            return
        
        for sink in self.sinks:
            sink.send_batch(self.buffer)
        
        self.buffer = []
```

---

### 2. Real-time Detection

```python
class RealTimeDetector:
    """Real-time attack detection."""
    
    def __init__(self, event_collector: EventCollector):
        self.collector = event_collector
        self.session_scores = {}  # session_id -> risk_score
        self.user_history = {}     # user_id -> recent events
    
    def process_input(
        self, 
        text: str, 
        session_id: str, 
        user_id: str
    ) -> dict:
        """Process input for real-time detection."""
        
        # Pattern detection
        patterns = self._detect_patterns(text)
        
        # Update session risk score
        self._update_session_score(session_id, patterns)
        
        # Check for escalation
        escalation = self._check_escalation(session_id)
        
        # Emit events
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
        """Detect attack patterns."""
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
        """Update session risk score."""
        
        current = self.session_scores.get(session_id, 0)
        
        # Increase for suspicious patterns
        if patterns["is_suspicious"]:
            current = min(current + patterns["risk"] * 0.3, 1.0)
        else:
            # Decay over time (benign inputs reduce score)
            current = max(current - 0.05, 0)
        
        self.session_scores[session_id] = current
    
    def _check_escalation(self, session_id: str) -> dict:
        """Check for attack escalation patterns."""
        
        score = self.session_scores.get(session_id, 0)
        
        return {
            "detected": score >= 0.8,
            "trajectory": "increasing" if score > 0.5 else "stable"
        }
```

---

### 3. Session Analysis

```python
class SessionAnalyzer:
    """Analyze conversation sessions for attacks."""
    
    def __init__(self):
        self.sessions = {}  # session_id -> conversation history
    
    def add_turn(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        metadata: dict = None
    ):
        """Add a conversation turn."""
        
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        self.sessions[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
    
    def analyze_trajectory(self, session_id: str) -> dict:
        """Analyze conversation trajectory for attacks."""
        
        if session_id not in self.sessions:
            return {"analysis": None}
        
        turns = self.sessions[session_id]
        
        # Extract features
        features = {
            "turn_count": len(turns),
            "user_turn_lengths": [
                len(t["content"]) for t in turns if t["role"] == "user"
            ],
            "escalation_pattern": self._detect_escalation(turns),
            "topic_drift": self._detect_topic_drift(turns),
            "repeated_attempts": self._detect_repeated_attempts(turns),
        }
        
        # Calculate risk
        risk_score = self._calculate_trajectory_risk(features)
        
        return {
            "features": features,
            "risk_score": risk_score,
            "is_attack": risk_score > 0.7,
            "attack_type": self._classify_attack(features) if risk_score > 0.7 else None
        }
    
    def _detect_escalation(self, turns: list) -> dict:
        """Detect escalating attack patterns."""
        
        user_turns = [t for t in turns if t["role"] == "user"]
        
        if len(user_turns) < 3:
            return {"detected": False}
        
        # Check if each turn is more aggressive
        aggression_scores = []
        for turn in user_turns:
            score = self._score_aggression(turn["content"])
            aggression_scores.append(score)
        
        # Check for increasing trend
        is_escalating = all(
            aggression_scores[i] <= aggression_scores[i+1]
            for i in range(len(aggression_scores) - 1)
        )
        
        return {
            "detected": is_escalating and aggression_scores[-1] > 0.5,
            "scores": aggression_scores
        }
    
    def _detect_repeated_attempts(self, turns: list) -> dict:
        """Detect repeated jailbreak attempts."""
        
        user_turns = [t["content"] for t in turns if t["role"] == "user"]
        
        # Check for semantic similarity between attempts
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
    """Manage security alerts."""
    
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
            "cooldown_seconds": 0  # Always alert
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
        """Process event and trigger alerts."""
        
        for rule in self.ALERT_RULES:
            if not rule["condition"](event):
                continue
            
            # Check cooldown
            if not self._check_cooldown(rule):
                continue
            
            # Handle aggregation
            if rule.get("aggregate"):
                if self._should_aggregate(rule, event):
                    continue
            
            # Send alert
            self._send_alert(rule, event)
    
    def _send_alert(self, rule: dict, event: SecurityEvent):
        """Send alert via appropriate channel."""
        
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
    """Detailed logging for incident investigation."""
    
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
        """Log complete interaction for forensics."""
        
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
            "retention_policy": "security",  # Longer retention
        }
        
        # Store with integrity
        signed_record = self._sign_record(record)
        self.storage.store(signed_record)
    
    def search_incidents(
        self,
        session_id: str = None,
        user_id: str = None,
        time_range: tuple = None,
        event_types: list = None
    ) -> list:
        """Search logs for incident investigation."""
        
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

## SENTINEL Integration

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
    # Automatically monitored
    return llm.generate(user_input)
```

---

## Key Takeaways

1. **Monitor all layers** - Input, processing, output, session
2. **Real-time detection** - Don't wait for logs
3. **Session context matters** - Multi-turn attacks need trajectory analysis
4. **Alert appropriately** - Critical vs informational
5. **Log for forensics** - Detailed, signed, retained

---

*AI Security Academy | Lesson 05.3.1*
