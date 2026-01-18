# 📊 Lesson 2.1: SIEM Integration

> **Time: 40 minutes** | Mid-Level Module 2

---

## Supported SIEMs

| SIEM | Protocol | Status |
|------|----------|--------|
| **Splunk** | HEC, Syslog | ✅ |
| **Elastic** | Elasticsearch, Logstash | ✅ |
| **Azure Sentinel** | REST API | ✅ |
| **QRadar** | Syslog | ✅ |

---

## Event Format

```json
{
  "timestamp": "2026-01-18T17:00:00Z",
  "event_type": "threat_detected",
  "severity": "high",
  "source_ip": "192.168.1.100",
  "threat_type": "injection",
  "confidence": 0.92,
  "payload_hash": "sha256:abc123...",
  "engine": "injection_detector_v3",
  "owasp": "LLM01",
  "action": "blocked"
}
```

---

## Splunk Integration

```python
from sentinel.integrations.splunk import SplunkHEC

splunk = SplunkHEC(
    url="https://splunk.example.com:8088",
    token="your-hec-token",
    index="sentinel"
)

# Auto-forward all threats
from sentinel import configure
configure(callbacks=[splunk.on_threat])
```

---

## Elastic Integration

```python
from sentinel.integrations.elastic import ElasticExporter

elastic = ElasticExporter(
    hosts=["https://elastic.example.com:9200"],
    index="sentinel-threats",
    api_key="your-api-key"
)

configure(callbacks=[elastic.on_threat])
```

---

## Sample Splunk Query

```spl
index=sentinel event_type=threat_detected
| stats count by threat_type, owasp
| sort -count
```

---

## Next Lesson

→ [2.2: SOAR Playbooks](./06-soar-playbooks.md)
