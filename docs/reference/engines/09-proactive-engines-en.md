# Proactive Engines

> **Engines:** 9  
> **Description:** Proactive defense engines

---

## 14. RAG Guard Engine

**File:** [rag_guard.py](file:///c:/AISecurity/src/brain/engines/rag_guard.py)  
**LOC:** 569  
**Theoretical Base:** RAG poisoning protection

### 14.1. TTPs.ai Coverage

- Retrieval Tool Poisoning
- False RAG Entry Injection
- Shared Resource Poisoning

### 14.2. Components

1. **DocumentValidator** — regex patterns in documents
2. **QueryConsistencyChecker** — query ↔ doc semantic match
3. **SourceTrustScorer** — source reputation

### 14.3. Injection Patterns

```python
RAG_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above)\s+instructions?",
    r"<\|system\|>",
    r"you\s+are\s+now\s+(a|an|the)",
    r"when\s+(the\s+)?user\s+asks",
]

CONDITIONAL_INJECTION_PATTERNS = [
    r"when\s+asked\s+about\s+.*respond\s+with",
    r"for\s+questions\s+about\s+.*always\s+say",
]
```

### 14.4. Source Trust

```python
DEFAULT_TRUSTED_SOURCES = ["official", "internal", "verified"]
DEFAULT_UNTRUSTED_PATTERNS = [r"user[-_]?upload", r"anonymous"]
```

### 14.5. Usage

```python
# Filter poisoned documents before sending to LLM
safe_docs, result = rag_guard.filter_documents(query, documents)
```

---

## 15. Agentic Monitor

**File:** [agentic_monitor.py](file:///c:/AISecurity/src/brain/engines/agentic_monitor.py)  
**LOC:** 636  
**Theoretical Base:** OWASP Top 10 for Agentic AI Applications (2025)

### 15.1. Theoretical Foundation

#### OWASP Agentic AI Top 10 (2025)

Specialized threat list for AI agents:

| #   | Threat               | Description                       |
| --- | -------------------- | --------------------------------- |
| 1   | Memory Poisoning     | Injecting false facts into memory |
| 2   | Tool Abuse           | Misuse of tools                   |
| 3   | Privilege Escalation | Elevation of privileges           |
| 4   | Agent Collusion      | Coordination between agents       |
| 5   | Prompt Injection     | Injections via tools              |
| 6   | Data Exfiltration    | Data leakage                      |
| 7   | Shadow Agents        | Unregistered agents               |

### 15.2. Agent Registration

```python
@dataclass
class AgentProfile:
    agent_id: str
    name: str
    role: AgentRole  # ORCHESTRATOR, EXECUTOR, PLANNER
    allowed_tools: Set[str]
    allowed_targets: Set[str]  # Who can talk to whom
    max_requests_per_minute: int = 60
    trust_score: float = 1.0
```

### 15.3. Threat Detectors

```python
THREAT_DETECTORS = {
    ThreatCategory.MEMORY_POISONING: [
        "forget everything", "your new instructions", "from now on you are"
    ],
    ThreatCategory.PRIVILEGE_ESCALATION: [
        "i am the admin", "grant me access", "elevate my privileges"
    ],
    ThreatCategory.DATA_EXFILTRATION: [
        "password=", "api_key=", "-----BEGIN PRIVATE KEY-----"
    ],
}
```

### 15.4. Agent Collusion Detection

```python
class AgentCollusionDetector:
    """
    Agent collusion detection:
    - Circular communication loops (A → B → A)
    - Excessive pairwise communication (>20 interactions)
    - Synchronized timing (actions within 5s window)
    """
```

### 15.5. Honest Assessment

| Aspect                  | Status                       |
| ----------------------- | ---------------------------- |
| **OWASP coverage**      | ✅ 7/10 threats              |
| **Agent profiles**      | ✅ Registration + validation |
| **Collusion detection** | ✅ Multi-pattern             |
| **Production-ready**    | ✅ For agentic systems       |

---

## 37. Honeypot Responses Engine

**File:** [honeypot_responses.py](file:///c:/AISecurity/src/brain/engines/honeypot_responses.py)  
**LOC:** 454  
**Theoretical Base:** Deception technology

### 37.1. Honeypot Types

```python
class HoneypotType(Enum):
    API_KEY = "api_key"         # sk-TRAP-xxx
    PASSWORD = "password"       # TRAP_xxx
    DATABASE_URL = "database_url"
    SECRET_KEY = "secret_key"
    ENDPOINT = "endpoint"       # https://api.internal.trap/
    INTERNAL_IP = "internal_ip"
```

### 37.2. Injection Logic

```python
# Detect sensitive requests (password, api_key, etc.)
# Inject fake, tracked tokens
# Store for later verification
```

### 37.3. Alert on Usage

```python
def check_usage(text) -> Optional[HoneypotAlert]:
    """
    If attacker uses injected token → CRITICAL ALERT!
    """
```

---

## 40. Agent Collusion Detector

**File:** [agent_collusion_detector.py](file:///c:/AISecurity/src/brain/engines/agent_collusion_detector.py)  
**LOC:** 429  
**Theoretical Base:** Multi-agent coordination attacks

### 40.1. Collusion Types

```python
class CollusionType(Enum):
    SYNCHRONIZED = "synchronized"    # Acting at same time
    COMPLEMENTARY = "complementary"  # A prepares, B executes
    CASCADING = "cascading"          # Chain reaction
    HIDDEN_CHANNEL = "hidden_channel"  # Covert comm
```

### 40.2. Complementary Pairs

```python
# Prepare-Execute patterns:
("disable_logging", "exfiltrate_data"),
("elevate_privileges", "access_sensitive"),
("create_distraction", "execute_payload"),
```

### 40.3. Timing Analysis

```python
TIME_SYNC_THRESHOLD = 5 seconds
# Multiple agents acting within 5s window = suspicious
```

---

## 54. Vulnerability Hunter Engine

**File:** [vulnerability_hunter.py](file:///c:/AISecurity/src/brain/engines/vulnerability_hunter.py)  
**LOC:** 812  
**Theoretical Base:** Automated security testing (fuzzing)

### 54.1. Philosophy

> "If we don't find it first, attackers will."

### 54.2. Fuzzing Strategies

```python
strategies = [
    "random",      # Random strings
    "boundary",    # Edge cases (empty, null, very long)
    "unicode",     # RTL, emoji, zero-width
    "encoding",    # Base64, URL, hex variations
    "grammar",     # Structured injection patterns
]
```

### 54.3. Vulnerability Categories

| Category            | Severity |
| ------------------- | -------- |
| PROMPT_LEAKAGE      | HIGH     |
| GUARDRAIL_BYPASS    | HIGH     |
| OUTPUT_MANIPULATION | CRITICAL |
| DENIAL_OF_SERVICE   | HIGH     |

### 54.4. Differential Testing

```python
# One model safe, another vulnerable = attack surface
for input in test_inputs:
    outputs = {m: fn(input) for m, fn in models.items()}
    if detect_divergence(outputs):
        report_vulnerability()
```

---

## 55. Zero Day Forge Engine

**File:** [zero_day_forge.py](file:///c:/AISecurity/src/brain/engines/zero_day_forge.py)  
**LOC:** 507  
**Theoretical Base:** Internal zero-day program

### 55.1. Responsible Disclosure Workflow

```text
1. Forge zero-day → Create novel attack
2. Develop patch  → Detection + mitigation
3. Deploy patch   → Integrate with system
4. Document       → Threat intelligence report
```

### 55.2. Target Capabilities

```python
targets = [
    "tool_use",     # Tool/function calling
    "memory",       # Long-term memory
    "multi_agent",  # Agent coordination
    "protocol",     # MCP/A2A
]
```

### 55.3. Patch Generation

```python
patch = Patch(
    detection_rule="detect_recursive_tool_calls()",
    mitigation_code="Add tool call depth limit",
    effectiveness=0.85,
)
```

---

## 56. Proactive Defense Engine

**File:** [proactive_defense.py](file:///c:/AISecurity/src/brain/engines/proactive_defense.py)  
**LOC:** 669  
**Theoretical Base:** Anomaly-based zero-day detection

### 56.1. Detection Layers

```text
1. Entropy Analysis — Shannon entropy spikes/drops
2. Invariant Checking — Role confusion, intent shift
3. Thermodynamic — Free energy, second law violations
4. Reputation — User trust-based thresholds
```

### 56.2. Tiered Response

```python
class ResponseTier(Enum):
    ALLOW = "allow"
    LOG = "log"
    WARN = "warn"
    CHALLENGE = "challenge"  # Require confirmation
    BLOCK = "block"
```

### 56.3. Thermodynamic Analysis

```python
# Second Law: entropy should not decrease spontaneously
if entropy_drop > 1.5:
    anomaly = THERMODYNAMIC_ANOMALY
```

---

## 57. Kill Chain Simulation Engine

**File:** [kill_chain_simulation.py](file:///c:/AISecurity/src/brain/engines/kill_chain_simulation.py)  
**LOC:** 492  
**Theoretical Base:** NVIDIA AI Kill Chain + MITRE

### 57.1. AI Kill Chain Stages

```python
class AIKillChainStage(Enum):
    RECON = "recon"      # Probe for restrictions
    POISON = "poison"    # Inject payload
    HIJACK = "hijack"    # Override controls
    PERSIST = "persist"  # Maintain access
    IMPACT = "impact"    # Actions on objectives
```

### 57.2. Attack Scenarios

| Scenario             | Max Impact |
| -------------------- | ---------- |
| prompt_injection     | 0.9        |
| privilege_escalation | 0.95       |
| data_exfiltration    | 0.85       |
| rag_poisoning        | 0.7        |

### 57.3. Impact Assessment

```python
result = simulator.simulate("prompt_injection", detection_score=0.8)
# → SimulationResult(
#     max_impact_score=0.65,
#     priority="high",
#     recommendation="WARN: Moderate risk"
# )
```

---

## 59. Agentic AI Monitor

**File:** [agentic_monitor.py](file:///c:/AISecurity/src/brain/engines/agentic_monitor.py)  
**LOC:** 636  
**Theoretical Base:** OWASP Top 10 for Agentic AI (2025)

### 59.1. Threat Categories

```python
class ThreatCategory(Enum):
    MEMORY_POISONING = "memory_poisoning"
    TOOL_ABUSE = "tool_abuse"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    AGENT_COLLUSION = "agent_collusion"
    DATA_EXFILTRATION = "data_exfiltration"
    SHADOW_AGENT = "shadow_agent"
```

### 59.2. Agent Profiles

```python
profile = AgentProfile(
    agent_id="planner-01",
    role=AgentRole.PLANNER,
    allowed_tools={"search", "summarize"},
    max_requests_per_minute=60,
    trust_score=1.0,
)
```

### 59.3. Detectors

| Detector        | Patterns                                |
| --------------- | --------------------------------------- |
| MemoryPoisoning | "forget everything", "new instructions" |
| ToolAbuse       | "../", "rm -rf", "eval("                |
| Collusion       | Synchronized timing, hidden channels    |

---
