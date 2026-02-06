# Requirements: CrossToolGuard Engine

## Описание

Engine для мониторинга dangerous data flows между tool chains.
**Источник:** DTEX i³ Threat Advisory — LinkedIn Injection scenario.

> "Guardrails are tool-specific, not system-wide. When AI tools connect in a chain, the overall system becomes vulnerable unless there is a coordinated, end-to-end security strategy."

---

## Проблема

Каждый tool имеет свои guardrails, но **между tools есть gaps**:

```
file_read() → LLM processing → email_send()
     ↑                              ↑
   Safe alone              Safe alone
            ↑
     DANGEROUS TOGETHER (exfiltration)
```

---

## User Stories

### US-01: Detect File→Email Exfiltration
**Как** security system  
**Хочу** детектировать `file_read + email_send` в одной сессии  
**Чтобы** блокировать data exfiltration через email  

**Acceptance Criteria:**
- [ ] Detect pattern: `file_read("*.env") → email_send(external)`
- [ ] Confidence: 0.95
- [ ] Action: BLOCK + alert

---

### US-02: Detect File→HTTP Exfiltration
**Как** security system  
**Хочу** детектировать `file_read + http_request` в одной сессии  
**Чтобы** блокировать data exfiltration через HTTP  

**Acceptance Criteria:**
- [ ] Detect: `file_read(sensitive) → curl/fetch/http_post`
- [ ] Confidence: 0.90
- [ ] Track: destination URL

---

### US-03: Detect Credential→External Chain
**Как** security system  
**Хочу** детектировать credential access + external communication  
**Чтобы** предотвратить credential theft  

**Acceptance Criteria:**
- [ ] Patterns: `read_credentials`, `get_api_key`, `env.AWS_*`
- [ ] + any external: email, http, webhook
- [ ] Confidence: 0.98 (critical)

---

### US-04: Session-Scoped Detection
**Как** security system  
**Хочу** отслеживать tool calls в рамках одной сессии  
**Чтобы** correlate отдельные safe actions в dangerous chains  

**Acceptance Criteria:**
- [ ] Session window: 30 seconds
- [ ] Track: tool sequence, data flow
- [ ] Reset: on session end or timeout

---

## Dangerous Combinations

| First Action | Second Action | Risk | Confidence |
|--------------|---------------|------|------------|
| `file_read(*.env, *.pem, *.key)` | `email_send(external)` | Exfiltration | 0.95 |
| `file_read(sensitive)` | `http_post(external)` | Exfiltration | 0.90 |
| `read_credentials` | `any_external` | Credential Theft | 0.98 |
| `db_query(users)` | `http_post(external)` | Data Breach | 0.95 |
| `code_execute` | `http_post(external)` | RCE+Exfil | 0.98 |

---

## Technical Implementation

### Data Structure

```rust
pub struct ToolEvent {
    pub tool_name: String,
    pub action: ToolAction,
    pub target: Option<String>,
    pub timestamp: Instant,
}

pub enum ToolAction {
    FileRead,
    FileWrite,
    EmailSend,
    HttpRequest,
    DbQuery,
    CodeExecute,
    CredentialAccess,
}

pub struct SessionContext {
    pub events: Vec<ToolEvent>,
    pub session_start: Instant,
    pub threat_level: ThreatLevel,
}
```

### Detection Logic

```rust
fn check_dangerous_chain(events: &[ToolEvent]) -> Option<ChainThreat> {
    // Find sensitive data access
    let sensitive_access = events.iter()
        .find(|e| e.action.is_sensitive_data_access());
    
    // Find external communication
    let external_comm = events.iter()
        .find(|e| e.action.is_external_communication());
    
    // Dangerous if both present
    if sensitive_access.is_some() && external_comm.is_some() {
        return Some(ChainThreat::DataExfiltration);
    }
    None
}
```

---

## API

```rust
pub trait CrossToolGuard {
    fn record_event(&mut self, event: ToolEvent);
    fn check_session(&self) -> Option<ChainThreat>;
    fn reset_session(&mut self);
}
```

---

## Test Cases

| # | Scenario | Expected |
|---|----------|----------|
| 1 | `file_read(.env)` alone | PASS |
| 2 | `email_send(bob@work.com)` alone | PASS |
| 3 | `file_read(.env) + email_send(external)` | BLOCK |
| 4 | `read_api_key + curl` | BLOCK |
| 5 | `db_query(users) + http_post` | BLOCK |
| 6 | `file_read(.env) + email_send(internal@company.com)` | PASS |
| 7 | Session timeout reset | PASS |

---

## Dependencies

- `sentinel-core` (MatchResult, PatternMatcher)
- `std::time::Instant` for session tracking

---

## Effort Estimate

| Phase | Time |
|-------|------|
| TDD tests | 1h |
| Core engine | 2h |
| Integration | 1h |
| **Total** | ~4h |
