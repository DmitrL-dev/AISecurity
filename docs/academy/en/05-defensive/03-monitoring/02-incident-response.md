# Incident Response for AI Systems

> **Lesson:** 05.3.2 - AI Incident Response  
> **Time:** 40 minutes  
> **Prerequisites:** Monitoring basics

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Develop AI-specific incident response procedures
2. Investigate AI security incidents
3. Implement containment and recovery
4. Build post-incident analysis workflows

---

## AI Incident Types

| Incident Type | Examples |
|--------------|----------|
| **Prompt Injection** | Successful extraction, behavior override |
| **Data Leakage** | PII in output, training data extraction |
| **Service Abuse** | Token exhaustion, resource exploitation |
| **Model Compromise** | Poisoned fine-tuning, backdoors |

---

## Incident Response Framework

```
┌─────────────────────────────────────────────────────────────┐
│                 AI INCIDENT RESPONSE                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. DETECTION ──▶ 2. TRIAGE ──▶ 3. CONTAINMENT              │
│        │              │              │                       │
│        ▼              ▼              ▼                       │
│  4. INVESTIGATION ──▶ 5. REMEDIATION ──▶ 6. RECOVERY        │
│        │                     │                               │
│        ▼                     ▼                               │
│  7. POST-INCIDENT REVIEW ◀────────────────────              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Detection

```python
class IncidentDetector:
    """Detect potential AI security incidents."""
    
    INCIDENT_SIGNATURES = {
        "prompt_injection_success": {
            "indicators": [
                "system_prompt_in_output",
                "role_adoption",
                "unexpected_tool_access"
            ],
            "severity": "high"
        },
        "data_leakage": {
            "indicators": [
                "pii_in_output",
                "credential_exposure",
                "training_data_verbatim"
            ],
            "severity": "critical"
        },
        "service_abuse": {
            "indicators": [
                "token_exhaustion",
                "rate_limit_bypass",
                "resource_spike"
            ],
            "severity": "medium"
        }
    }
    
    def detect(self, event_stream: list) -> list:
        """Detect incidents from event stream."""
        
        incidents = []
        
        for event in event_stream:
            for incident_type, signature in self.INCIDENT_SIGNATURES.items():
                if self._matches_signature(event, signature):
                    incidents.append({
                        "type": incident_type,
                        "severity": signature["severity"],
                        "event": event,
                        "timestamp": event.get("timestamp"),
                        "session_id": event.get("session_id")
                    })
        
        return incidents
```

---

## Phase 2: Triage

```python
from dataclasses import dataclass
from enum import Enum

class Severity(Enum):
    CRITICAL = 4  # Data breach, active exploitation
    HIGH = 3      # Successful attack, limited impact
    MEDIUM = 2    # Attempted attack, contained
    LOW = 1       # Anomaly, investigation needed

@dataclass
class TriagedIncident:
    incident_id: str
    severity: Severity
    affected_sessions: list
    affected_users: list
    attack_surface: str
    recommended_actions: list
    escalate_to: str

class IncidentTriager:
    """Triage AI security incidents."""
    
    def triage(self, incident: dict) -> TriagedIncident:
        """Triage incident and recommend response."""
        
        severity = self._assess_severity(incident)
        impact = self._assess_impact(incident)
        
        return TriagedIncident(
            incident_id=self._generate_id(),
            severity=severity,
            affected_sessions=impact["sessions"],
            affected_users=impact["users"],
            attack_surface=self._identify_surface(incident),
            recommended_actions=self._recommend_actions(severity, incident),
            escalate_to=self._determine_escalation(severity)
        )
    
    def _assess_severity(self, incident: dict) -> Severity:
        """Assess incident severity."""
        
        # Critical: Data breach confirmed
        if incident.get("data_confirmed_leaked"):
            return Severity.CRITICAL
        
        # High: Successful exploitation
        if incident.get("attack_succeeded"):
            return Severity.HIGH
        
        # Medium: Attempted but contained
        if incident.get("attack_blocked"):
            return Severity.MEDIUM
        
        return Severity.LOW
    
    def _recommend_actions(self, severity: Severity, incident: dict) -> list:
        """Recommend response actions."""
        
        actions = []
        
        if severity == Severity.CRITICAL:
            actions.extend([
                "Immediately suspend affected service",
                "Notify security team on-call",
                "Preserve all logs and artifacts",
                "Begin data breach notification process"
            ])
        
        elif severity == Severity.HIGH:
            actions.extend([
                "Block affected sessions",
                "Investigate attack vector",
                "Check for lateral movement",
                "Update detection rules"
            ])
        
        elif severity == Severity.MEDIUM:
            actions.extend([
                "Log incident for analysis",
                "Review blocking effectiveness",
                "Update threat intelligence"
            ])
        
        return actions
```

---

## Phase 3: Containment

```python
class IncidentContainment:
    """Contain AI security incidents."""
    
    def __init__(self, session_manager, model_manager, firewall):
        self.sessions = session_manager
        self.models = model_manager
        self.firewall = firewall
    
    async def contain(self, incident: TriagedIncident) -> dict:
        """Execute containment actions."""
        
        actions_taken = []
        
        # 1. Session isolation
        for session_id in incident.affected_sessions:
            await self.sessions.terminate(session_id)
            actions_taken.append(f"Terminated session {session_id}")
        
        # 2. User blocking (if needed)
        if incident.severity == Severity.CRITICAL:
            for user_id in incident.affected_users:
                await self.sessions.block_user(user_id)
                actions_taken.append(f"Blocked user {user_id}")
        
        # 3. Attack vector blocking
        if incident.attack_surface == "prompt_injection":
            pattern = self._extract_attack_pattern(incident)
            await self.firewall.add_block_rule(pattern)
            actions_taken.append(f"Added firewall rule for pattern")
        
        # 4. Model isolation (extreme cases)
        if incident.severity == Severity.CRITICAL:
            await self.models.switch_to_fallback()
            actions_taken.append("Switched to fallback model")
        
        return {
            "contained": True,
            "actions": actions_taken,
            "timestamp": datetime.utcnow().isoformat()
        }
```

---

## Phase 4: Investigation

```python
class IncidentInvestigator:
    """Investigate AI security incidents."""
    
    def __init__(self, log_store, artifact_store):
        self.logs = log_store
        self.artifacts = artifact_store
    
    async def investigate(self, incident: TriagedIncident) -> dict:
        """Conduct full investigation."""
        
        timeline = await self._build_timeline(incident)
        attack_chain = self._analyze_attack_chain(timeline)
        root_cause = self._identify_root_cause(attack_chain)
        iocs = self._extract_iocs(timeline)
        
        return {
            "incident_id": incident.incident_id,
            "timeline": timeline,
            "attack_chain": attack_chain,
            "root_cause": root_cause,
            "indicators_of_compromise": iocs,
            "recommendations": self._generate_recommendations(root_cause)
        }
    
    async def _build_timeline(self, incident: TriagedIncident) -> list:
        """Build event timeline for incident."""
        
        events = []
        
        # Gather logs for affected sessions
        for session_id in incident.affected_sessions:
            session_logs = await self.logs.query(
                session_id=session_id,
                time_range=("-1h", "+1h")
            )
            events.extend(session_logs)
        
        # Sort by timestamp
        events.sort(key=lambda e: e["timestamp"])
        
        return events
    
    def _analyze_attack_chain(self, timeline: list) -> dict:
        """Analyze attack chain from timeline."""
        
        phases = {
            "reconnaissance": [],
            "initial_access": [],
            "execution": [],
            "exfiltration": []
        }
        
        for event in timeline:
            phase = self._classify_phase(event)
            if phase:
                phases[phase].append(event)
        
        return {
            "phases": phases,
            "attack_duration": self._calculate_duration(timeline),
            "techniques_used": self._identify_techniques(phases)
        }
    
    def _extract_iocs(self, timeline: list) -> list:
        """Extract indicators of compromise."""
        
        iocs = []
        
        for event in timeline:
            # Extract attack patterns
            if event.get("attack_pattern"):
                iocs.append({
                    "type": "prompt_pattern",
                    "value": event["attack_pattern"],
                    "confidence": 0.9
                })
            
            # Extract suspicious IPs
            if event.get("source_ip"):
                iocs.append({
                    "type": "ip_address",
                    "value": event["source_ip"],
                    "confidence": 0.7
                })
        
        return iocs
```

---

## Phase 5-6: Remediation & Recovery

```python
class IncidentRemediation:
    """Remediate and recover from incidents."""
    
    async def remediate(self, investigation: dict) -> dict:
        """Apply remediation based on investigation."""
        
        actions = []
        
        # Update detection rules
        for ioc in investigation["indicators_of_compromise"]:
            await self._add_detection_rule(ioc)
            actions.append(f"Added detection for {ioc['type']}")
        
        # Patch vulnerabilities
        for rec in investigation["recommendations"]:
            if rec["type"] == "prompt_hardening":
                await self._update_system_prompt(rec["changes"])
                actions.append("Updated system prompt")
            
            elif rec["type"] == "filter_update":
                await self._update_filters(rec["patterns"])
                actions.append("Updated input filters")
        
        # Update model if needed
        if investigation["root_cause"]["requires_retraining"]:
            actions.append("Queued model for retraining")
        
        return {"remediation_complete": True, "actions": actions}
    
    async def recover(self, incident: TriagedIncident) -> dict:
        """Recover services after incident."""
        
        steps = []
        
        # 1. Verify containment
        verify = await self._verify_containment()
        steps.append({"step": "verify_containment", "result": verify})
        
        # 2. Restore normal operations
        if verify["contained"]:
            await self.models.restore_primary()
            steps.append({"step": "restore_model", "result": "success"})
        
        # 3. Unblock users (with monitoring)
        for user_id in incident.affected_users:
            await self.sessions.unblock_user(user_id, enhanced_monitoring=True)
            steps.append({"step": f"unblock_user_{user_id}", "result": "success"})
        
        # 4. Resume normal alerting
        await self.alerting.resume_normal()
        
        return {"recovered": True, "steps": steps}
```

---

## Phase 7: Post-Incident Review

```python
class PostIncidentReview:
    """Conduct post-incident analysis."""
    
    def generate_report(self, incident: TriagedIncident, investigation: dict) -> dict:
        """Generate post-incident report."""
        
        return {
            "executive_summary": self._executive_summary(incident, investigation),
            
            "incident_details": {
                "id": incident.incident_id,
                "severity": incident.severity.name,
                "duration": investigation["attack_chain"]["attack_duration"],
                "affected_users": len(incident.affected_users),
                "affected_sessions": len(incident.affected_sessions)
            },
            
            "timeline": investigation["timeline"],
            
            "root_cause_analysis": investigation["root_cause"],
            
            "impact_assessment": self._assess_impact(incident, investigation),
            
            "lessons_learned": self._lessons_learned(investigation),
            
            "action_items": self._generate_action_items(investigation),
            
            "metrics_update": self._update_metrics(incident)
        }
    
    def _lessons_learned(self, investigation: dict) -> list:
        """Extract lessons learned."""
        
        lessons = []
        
        root_cause = investigation["root_cause"]
        
        if root_cause["category"] == "detection_gap":
            lessons.append({
                "lesson": "Detection gap allowed attack progression",
                "action": "Improve detection coverage for similar patterns"
            })
        
        if root_cause["category"] == "prompt_weakness":
            lessons.append({
                "lesson": "System prompt lacked specific defenses",
                "action": "Strengthen prompt with explicit protections"
            })
        
        return lessons
```

---

## SENTINEL Integration

```python
from sentinel import configure, IncidentManager

configure(
    incident_response=True,
    auto_containment=True,
    forensic_logging=True
)

incident_manager = IncidentManager(
    auto_contain_critical=True,
    notification_channels=["slack", "pagerduty"],
    retention_days=365
)

# Automatic incident handling
@incident_manager.on_incident
async def handle_incident(incident):
    if incident.severity == Severity.CRITICAL:
        await incident_manager.contain(incident)
        await incident_manager.notify_security_team(incident)
```

---

## Key Takeaways

1. **Detect quickly** - Real-time monitoring essential
2. **Triage accurately** - Severity drives response
3. **Contain immediately** - Stop the bleeding
4. **Investigate thoroughly** - Understand the full picture
5. **Learn continuously** - Improve from every incident

---

*AI Security Academy | Lesson 05.3.2*
