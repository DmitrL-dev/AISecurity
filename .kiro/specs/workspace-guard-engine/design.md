# Workspace Guard Engine — Design

## Architecture

```
┌─────────────────────────────────────────┐
│            WorkspaceGuard               │
├─────────────────────────────────────────┤
│  c2_patterns: RegexSet                  │
│  rce_patterns: RegexSet                 │
│  callback_patterns: RegexSet            │
│  sensitive_files: Vec<&'static str>     │
├─────────────────────────────────────────┤
│  + scan_content(text) -> Vec<Match>     │
│  + is_sensitive_file(name) -> bool      │
│  + get_threat_level() -> ThreatLevel    │
└─────────────────────────────────────────┘
```

---

## Pattern Categories

### 1. C2 Trigger Patterns
```regex
every\s+\d+\s*(min|hour|sec|minute|second)
whenever?\s+(greeted|user|triggered|invoked)
on\s+(startup|load|init)
```

### 2. Callback/Exfil Patterns
```regex
curl\s+(-[a-zA-Z]+\s+)*https?://
wget\s+https?://
fetch\s*\(.*https?://
discord\.com/api/webhooks
hooks\.slack\.com
api\.telegram\.org
```

### 3. RCE Patterns
```regex
bash\s+-c
exec\s*\(
system\s*\(
eval\s*\(
subprocess\.(run|call|Popen)
os\.(system|popen)
child_process
```

---

## Data Structures

```rust
pub struct WorkspaceGuard {
    c2_patterns: RegexSet,
    callback_patterns: RegexSet,
    rce_patterns: RegexSet,
}

pub enum ThreatType {
    C2Trigger,
    Callback,
    RCE,
    SensitiveFile,
}

pub struct WorkspaceThreat {
    pub threat_type: ThreatType,
    pub pattern: String,
    pub confidence: f64,
}
```

---

## Sensitive Files

| File | Risk | Description |
|------|------|-------------|
| HEARTBEAT.md | Critical | C2 polling channel |
| memories.md | High | Long-term memory poisoning |
| CLAUDE.md | High | Behavior override |
| RULES.md | High | Rule injection |
| *.skill.md | Medium | Skill execution |
| persona.md | Medium | Identity hijacking |

---

## API

### Rust
```rust
impl WorkspaceGuard {
    pub fn new() -> Self;
    pub fn scan_content(&self, content: &str) -> Vec<WorkspaceThreat>;
    pub fn is_sensitive_file(&self, filename: &str) -> bool;
}
```

### Python (via PyO3)
```python
from sentinel_core import EngineRegistry
r = EngineRegistry()
result = r.analyze_with('workspace_guard', content)
```

---

## Dependencies

```toml
[dependencies]
regex = "1.10"
once_cell = "1.19"
```

---

## Test Strategy

| Test | Input | Expected |
|------|-------|----------|
| C2 detection | "every 5 min check" | threat=C2Trigger |
| Callback detection | "curl https://evil.com" | threat=Callback |
| RCE detection | "exec('rm -rf')" | threat=RCE |
| Benign pass | "# Project README" | no threats |
| Sensitive file | "HEARTBEAT.md" | is_sensitive=true |
