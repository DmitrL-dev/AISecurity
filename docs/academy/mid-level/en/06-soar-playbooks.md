# 🤖 Lesson 2.2: SOAR Playbooks

> **Time: 25 minutes** | Mid-Level Module 2

---

## What is SOAR?

**Security Orchestration, Automation and Response** — automated incident response.

```
Threat Detected → Playbook Triggered → Automated Response
```

---

## Sample Playbook

```yaml
name: ai_injection_response
trigger:
  event: threat_detected
  conditions:
    threat_type: injection
    confidence: ">0.8"

actions:
  - name: block_ip
    type: firewall
    params:
      action: block
      duration: 1h
      
  - name: notify_team
    type: slack
    params:
      channel: "#security-alerts"
      message: "AI injection attack blocked from {{ source_ip }}"
      
  - name: create_ticket
    type: jira
    params:
      project: SEC
      issue_type: Incident
      priority: High
```

---

## Python API

```python
from sentinel.soar import Playbook, Action

playbook = Playbook(
    name="injection_response",
    trigger={"threat_type": "injection", "confidence": 0.8}
)

@playbook.action
async def block_source(event):
    await firewall.block(event.source_ip, duration="1h")

@playbook.action
async def alert_team(event):
    await slack.post(
        channel="#security",
        message=f"Blocked injection from {event.source_ip}"
    )

playbook.register()
```

---

## Built-in Actions

| Action | Description |
|--------|-------------|
| `block_ip` | Add to firewall blocklist |
| `rate_limit` | Reduce request rate |
| `notify_slack` | Send Slack message |
| `create_ticket` | Create JIRA/ServiceNow ticket |
| `quarantine_user` | Disable user account |

---

## Next Lesson

→ [2.3: Compliance Reporting](./07-compliance-reporting.md)
