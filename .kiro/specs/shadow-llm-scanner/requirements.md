# Requirements: Shadow LLM Scanner

## Описание

Network fingerprinting tool для обнаружения exposed LLM services в сети.
Источник: [Praetorian Julius](https://www.praetorian.com/blog/introducing-julius-open-source-llm-service-fingerprinting/)

---

## Проблема

- 14,000+ Ollama серверов публично доступны
- 20% с несанкционированным доступом
- Shadow AI — LLM инстансы вне корпоративного контроля

---

## User Stories

### US-01: Probe Single Target
**Как** security analyst  
**Хочу** проверить конкретный endpoint на наличие LLM  
**Чтобы** определить тип сервиса  

**Acceptance Criteria:**
- [ ] CLI: `sentinel-scan probe https://target:11434`
- [ ] Timeout 3s per probe
- [ ] Return: платформа (ollama/vllm/tgi) или "unknown"

---

### US-02: Scan Network Range
**Как** security analyst  
**Хочу** сканировать подсеть на LLM сервисы  
**Чтобы** найти Shadow AI инстансы  

**Acceptance Criteria:**
- [ ] CLI: `sentinel-scan sweep 192.168.1.0/24 --port 11434`
- [ ] Concurrent requests (tokio async)
- [ ] Output: JSON list found targets

---

### US-03: Platform Fingerprinting
**Как** system  
**Хочу** определять тип LLM платформы  
**Чтобы** классифицировать риски  

**Acceptance Criteria:**
- [ ] Detect: Ollama (`/api/tags`)
- [ ] Detect: vLLM (`/v1/models`)
- [ ] Detect: TGI (`/info`)
- [ ] Detect: LangServe (`/docs`)
- [ ] Detect: LocalAI (`/v1/models` + signature)

---

### US-04: Model Enumeration
**Как** security analyst  
**Хочу** получить список моделей на target  
**Чтобы** оценить exposure  

**Acceptance Criteria:**
- [ ] CLI: `sentinel-scan enum https://target:11434`
- [ ] Parse model list from API response
- [ ] Output model names, sizes

---

### US-05: Risk Scoring
**Как** system  
**Хочу** оценить риск exposed LLM  
**Чтобы** приоритизировать remediation  

**Acceptance Criteria:**
- [ ] No auth required → HIGH risk
- [ ] Dangerous models (code-gen) → HIGH risk
- [ ] Internal network → MEDIUM risk
- [ ] Public internet → CRITICAL risk

---

## Технические требования

| Requirement | Value |
|-------------|-------|
| Language | Rust |
| Runtime | tokio async |
| HTTP | reqwest |
| CLI | clap |
| Output | JSON + human-readable |
| Timeout | 3s per probe |
| Concurrency | 50 concurrent requests |

---

## Non-Goals

- Exploitation (только detection)
- Vulnerability scanning (только fingerprinting)
- Rate limiting bypass

---

## Dependencies

```toml
[dependencies]
tokio = { version = "1", features = ["full"] }
reqwest = { version = "0.12", features = ["json"] }
clap = { version = "4", features = ["derive"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
ipnet = "2"
```

---

## Effort Estimate

| Phase | Time |
|-------|------|
| TDD tests | 2h |
| Core fingerprinter | 4h |
| CLI wrapper | 2h |
| Network sweep | 4h |
| Model enum | 2h |
| Risk scoring | 2h |
| Integration | 2h |
| **Total** | ~18h (~3 days) |
