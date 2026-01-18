# 🤖 Урок 2.2: SOAR Playbooks

> **Время: 25 минут** | Mid-Level Module 2

---

## SOAR Integration

SENTINEL интегрируется с SOAR платформами для автоматического реагирования:

| Platform | Integration |
|----------|-------------|
| Splunk SOAR (Phantom) | Custom App |
| Palo Alto XSOAR | Integration Pack |
| IBM Resilient | Python SDK |
| Microsoft Sentinel | Logic Apps |

---

## Playbook: Prompt Injection Response

```yaml
# playbook_injection_response.yaml
name: AI Prompt Injection Response
trigger:
  source: sentinel
  event_type: threat_detected
  threat_type: injection
  
actions:
  - name: Enrich Alert
    type: lookup
    params:
      source_ip: "{{ event.source_ip }}"
      user_id: "{{ event.user_id }}"
      
  - name: Block User (High Risk)
    type: conditional
    condition: "{{ event.risk_score > 0.9 }}"
    action:
      type: api_call
      endpoint: /api/users/{{ event.user_id }}/block
      
  - name: Create Ticket
    type: ticketing
    system: jira
    params:
      project: SEC
      type: Incident
      priority: "{{ 'High' if event.risk_score > 0.8 else 'Medium' }}"
      summary: "AI Injection Attack: {{ event.threat_type }}"
      
  - name: Notify SOC
    type: notification
    channel: slack
    message: |
      🚨 *AI Security Alert*
      Type: {{ event.threat_type }}
      Risk: {{ event.risk_score }}
      User: {{ event.user_id }}
```

---

## SENTINEL Runbook API

```python
from sentinel.runbook import Runbook, Action, Trigger

# Define runbook programmatically
runbook = Runbook(
    name="injection_response",
    trigger=Trigger(
        event_type="threat_detected",
        filters={"threat_type": "injection"}
    ),
    actions=[
        Action.log_event(),
        Action.block_user(duration="1h"),
        Action.create_ticket(system="jira"),
        Action.notify(channel="slack", severity="high")
    ]
)

# Register
runbook.register()
```

---

## Response Actions

| Action | API | Effect |
|--------|-----|--------|
| `block_user` | POST /users/{id}/block | Temporary ban |
| `quarantine_session` | POST /sessions/{id}/quarantine | Isolate session |
| `rate_limit` | PUT /users/{id}/rate-limit | Reduce limits |
| `escalate` | POST /escalations | Page on-call |
| `snapshot` | POST /audit/snapshot | Preserve evidence |

---

## Следующий урок

→ [2.3: Compliance Reporting](./07-compliance-reporting.md)
