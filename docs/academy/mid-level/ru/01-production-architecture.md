# 🏗️ Урок 1.1: Production Architecture

> **Время: 30 минут** | Mid-Level Module 1

---

## Reference Architectures

### Architecture A: Simple (Startup)

```
┌─────────────────────────────────────────────────────────────┐
│                      Your Application                        │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│    │  FastAPI │───▶│ SENTINEL │───▶│   LLM    │            │
│    │   API    │    │  Guard   │    │  (GPT-4) │            │
│    └──────────┘    └──────────┘    └──────────┘            │
│                          │                                   │
│                    ┌─────▼─────┐                            │
│                    │   Logs    │                            │
│                    └───────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

**Use when:**
- Single service
- <10K requests/day
- Team <5 developers

**Components:**
- SENTINEL as Python library
- Logging to file/stdout
- No separate infrastructure

---

### Architecture B: Standard (Scale-up)

```
┌─────────────────────────────────────────────────────────────┐
│                        Load Balancer                         │
│                             │                                │
│         ┌───────────────────┼───────────────────┐           │
│         ▼                   ▼                   ▼           │
│    ┌─────────┐         ┌─────────┐         ┌─────────┐     │
│    │ API Pod │         │ API Pod │         │ API Pod │     │
│    └────┬────┘         └────┬────┘         └────┬────┘     │
│         │                   │                   │           │
│         └───────────────────┼───────────────────┘           │
│                             ▼                                │
│                    ┌───────────────┐                        │
│                    │   SENTINEL    │                        │
│                    │    Service    │                        │
│                    └───────┬───────┘                        │
│                            │                                 │
│              ┌─────────────┼─────────────┐                  │
│              ▼             ▼             ▼                  │
│         ┌────────┐   ┌──────────┐   ┌────────┐             │
│         │ Redis  │   │ Postgres │   │  Logs  │             │
│         │ Cache  │   │ History  │   │ (ELK)  │             │
│         └────────┘   └──────────┘   └────────┘             │
└─────────────────────────────────────────────────────────────┘
```

**Use when:**
- Multiple services
- 10K-1M requests/day
- Team 5-20 developers

**Components:**
- SENTINEL as microservice
- Redis for caching + rate limiting
- PostgreSQL for audit trail
- ELK stack for logs

---

### Architecture C: Enterprise (Fortune 500)

```
┌─────────────────────────────────────────────────────────────┐
│                         DMZ Layer                            │
│    ┌──────────────────────────────────────────────────┐     │
│    │                   SHIELD (C)                      │     │
│    │              AI Security Gateway                  │     │
│    └──────────────────────────────────────────────────┘     │
│                             │                                │
├─────────────────────────────┼────────────────────────────────┤
│                      Internal Layer                          │
│    ┌───────────┐    ┌───────────┐    ┌───────────┐         │
│    │   BRAIN   │    │   BRAIN   │    │   BRAIN   │         │
│    │  Cluster  │    │  Cluster  │    │  Cluster  │         │
│    └─────┬─────┘    └─────┬─────┘    └─────┬─────┘         │
│          │                │                │                 │
│          └────────────────┼────────────────┘                 │
│                           ▼                                  │
│    ┌──────────────────────────────────────────────────┐     │
│    │                  Data Layer                       │     │
│    │  ┌────────┐  ┌──────────┐  ┌────────────────┐   │     │
│    │  │ Redis  │  │PostgreSQL│  │ Elasticsearch  │   │     │
│    │  │Cluster │  │  HA      │  │    Cluster     │   │     │
│    │  └────────┘  └──────────┘  └────────────────┘   │     │
│    └──────────────────────────────────────────────────┘     │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                     Integration Layer                        │
│    ┌────────┐  ┌────────┐  ┌────────┐  ┌─────────────┐     │
│    │ SIEM   │  │ SOAR   │  │  IAM   │  │ Compliance  │     │
│    │Splunk  │  │Phantom │  │ Okta   │  │  Reports    │     │
│    └────────┘  └────────┘  └────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

**Use when:**
- Enterprise-scale
- 1M+ requests/day
- Compliance requirements
- SOC team

---

## Component Deep Dive

### SHIELD (DMZ Gateway)

```yaml
# shield-config.yaml
shield:
  mode: production
  tls:
    enabled: true
    cert: /etc/ssl/shield.crt
    key: /etc/ssl/shield.key
  upstream:
    brain:
      url: http://brain-cluster:8080
      timeout: 100ms
  rate_limit:
    enabled: true
    requests_per_second: 1000
```

### BRAIN (Detection Cluster)

```yaml
# brain-config.yaml
brain:
  engines:
    enabled: all
    tier1:  # Fast, <10ms
      - injection_detector
      - keyword_filter
    tier2:  # Medium, <50ms
      - jailbreak_detector
      - encoding_detector
    tier3:  # Slow, <200ms
      - ml_classifier
      - tda_analyzer
  cache:
    redis_url: redis://redis-cluster:6379
    ttl_seconds: 300
```

---

## Latency Budget

| Layer | Target | Max |
|-------|--------|-----|
| Shield (network) | 1ms | 5ms |
| Brain Tier 1 | 5ms | 10ms |
| Brain Tier 2 | 20ms | 50ms |
| Brain Tier 3 | 100ms | 200ms |
| **Total** | **<50ms** | **<200ms** |

---

## Следующий урок

→ [1.2: Docker Deployment](./02-docker-deployment.md)
