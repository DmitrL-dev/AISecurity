# 📊 Урок 2.1: SIEM Integration

> **Время: 30 минут** | Mid-Level Module 2

---

## Supported SIEMs

| SIEM | Integration | Format |
|------|-------------|--------|
| **Splunk** | HTTP Event Collector | JSON |
| **Elastic** | Logstash / Filebeat | ECS |
| **Azure Sentinel** | Workspace API | CEF |
| **IBM QRadar** | Syslog | LEEF |
| **Sumo Logic** | HTTP Source | JSON |

---

## Splunk Integration

### HTTP Event Collector

```rust
use sentinel_core::configure;
use sentinel_core::integrations::siem::SplunkHEC;

let splunk = SplunkHEC::new(
    "https://splunk.example.com:8088",
    "your-hec-token",
    "sentinel_threats",
    "sentinel-brain",
    "sentinel:threat",
);

configure(
    siem: splunk,
    send_threats: true,
    send_audit: true,
);
```

### Event Format

```json
{
  "time": 1705590000,
  "source": "sentinel-brain",
  "sourcetype": "sentinel:threat",
  "event": {
    "threat_type": "injection",
    "confidence": 0.92,
    "risk_score": 0.85,
    "source_ip": "192.168.1.100",
    "user_id": "user_123",
    "payload_hash": "sha256:abc123...",
    "engines_triggered": ["injection_detector", "jailbreak_detector"],
    "mitre_techniques": ["T1059", "T1203"],
    "owasp_category": "LLM01"
  }
}
```

### Splunk Dashboard Query

```spl
index=sentinel_threats sourcetype="sentinel:threat"
| stats count by threat_type, owasp_category
| sort -count
```

---

## Elastic Integration

### Filebeat Config

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/sentinel/threats.json
  json:
    keys_under_root: true
    add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "sentinel-threats-%{+yyyy.MM.dd}"

setup.ilm.enabled: true
setup.ilm.rollover_alias: "sentinel-threats"
```

### ECS Mapping

```json
{
  "mappings": {
    "properties": {
      "@timestamp": { "type": "date" },
      "event.category": { "type": "keyword" },
      "event.type": { "type": "keyword" },
      "threat.type": { "type": "keyword" },
      "threat.confidence": { "type": "float" },
      "source.ip": { "type": "ip" },
      "user.id": { "type": "keyword" },
      "sentinel.engines": { "type": "keyword" },
      "sentinel.owasp": { "type": "keyword" }
    }
  }
}
```

---

## Azure Sentinel

### Data Connector

```rust
use sentinel_core::integrations::siem::AzureSentinel;

let azure = AzureSentinel::new(
    "your-workspace-id",
    "your-shared-key",
    "SentinelThreat",
);

configure(siem: azure);
```

### KQL Query

```kql
SentinelThreat_CL
| where TimeGenerated > ago(24h)
| summarize ThreatCount=count() by ThreatType_s, bin(TimeGenerated, 1h)
| render timechart
```

---

## Следующий урок

→ [2.2: SOAR Playbooks](./06-soar-playbooks.md)
