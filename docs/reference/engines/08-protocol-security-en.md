# Protocol Security

> **Engines:** 4  
> **Description:** MCP and A2A protocol security

---

## 19. MCP/A2A Security Engine

**File:** [mcp_a2a_security.py](file:///c:/AISecurity/src/brain/engines/mcp_a2a_security.py)  
**LOC:** 455  
**Theoretical Base:** OWASP ASI04 + ASI07 (Protocol Security)

### 19.1. Theoretical Foundation

#### OWASP Agentic Security Initiative

- **ASI04:** Prompt Injection in Tool Descriptions
- **ASI07:** Agent-to-Agent Trust Exploitation

MCP and A2A are emerging protocols for AI agents. New attack surfaces!

### 19.2. Protocol Types

```python
class ProtocolType(Enum):
    MCP = "mcp"   # Model Context Protocol — servers and tools
    A2A = "a2a"   # Agent-to-Agent — communication between agents
```

### 19.3. MCP Server Validation

```python
TRUSTED_MCP_REGISTRIES = {
    "registry.anthropic.com",
    "mcp.cloudflare.com",
    "registry.sentinel.ai",
}

def validate_mcp_server(server: MCPServer) -> ValidationResult:
    """
    Multi-layer validation:
    1. Attestation signature — server signed by trusted issuer
    2. Registry trust — in trusted registry
    3. Tool injection scan — tool descriptions without injection
    4. Typosquatting — name not similar to known service
    """
```

### 19.4. Typosquatting Detection

```python
def detect_typosquatting(name: str) -> List[str]:
    """
    Levenshtein distance < 2 from known tools.
    "p0stmark" → similar to "postmark"
    "stripee" → similar to "stripe"
    """
```

### 19.5. Tool Descriptor Injection

```python
TOOL_INJECTION_PATTERNS = [
    r"ignore\s+previous",
    r"system\s*:",
    r"\[SYSTEM\]",
    r"you are now",
]

def scan_tool_descriptors(tools: List[Tool]) -> CheckResult:
    """Tool descriptions may contain injection payloads."""
```

### 19.6. Honest Assessment

| Aspect               | Status                   |
| -------------------- | ------------------------ |
| **MCP validation**   | ✅ Multi-layer           |
| **A2A validation**   | ✅ Agent Cards           |
| **Typosquatting**    | ✅ Levenshtein           |
| **Production-ready** | ✅ For agent deployments |

---

## 44. Agent Card Validator

**File:** [agent_card_validator.py](file:///c:/AISecurity/src/brain/engines/agent_card_validator.py)  
**LOC:** 363  
**Theoretical Base:** A2A agent authentication

### 44.1. Validation Checks

1. Cryptographic signature
2. Well-known URI (`/.well-known/agent.json`)
3. Capability risk assessment
4. Issuer trust check
5. Version validation

### 44.2. Dangerous Capabilities

```python
DANGEROUS_CAPABILITIES = {
    "admin", "root", "execute",
    "credential_access", "key_management",
}
```

### 44.3. Trusted Issuers

```python
TRUSTED_ISSUERS = {
    "anthropic.com", "google.com",
    "openai.com", "sentinel.ai",
}
```

---

## 52. Tool Call Security

**File:** [tool_call_security.py](file:///c:/AISecurity/src/brain/engines/tool_call_security.py)  
**LOC:** 524  
**Theoretical Base:** Agent tool protection

### 52.1. Dangerous Tools

```python
DANGEROUS_TOOLS = {
    "execute_code": CRITICAL,
    "run_shell": CRITICAL,
    "delete_file": CRITICAL,
    "sql_query": HIGH,
    "http_request": MEDIUM,
}
```

### 52.2. Dangerous Combinations

```python
# Read then exfiltrate
({"read_file"}, {"http_request", "webhook"})

# Code gen then execute
({"generate_code"}, {"execute_code", "run_python"})
```

### 52.3. Escalation Detection

```python
ESCALATION_PATTERNS = [
    r"(admin|root|sudo)",
    r"(bypass|skip|ignore).*auth",
    r"/etc/(passwd|shadow)",
]
```

---

## 58. MCP/A2A Security Engine (Extended)

**File:** [mcp_a2a_security.py](file:///c:/AISecurity/src/brain/engines/mcp_a2a_security.py)  
**LOC:** 455  
**Theoretical Base:** OWASP ASI04 + ASI07 (Protocol Security)

### 58.1. Protocol Types

```python
class ProtocolType(Enum):
    MCP = "mcp"   # Model Context Protocol
    A2A = "a2a"   # Agent-to-Agent
```

### 58.2. MCP Server Validation

```text
1. Attestation signature ✓
2. Registry trust (anthropic, cloudflare, sentinel)
3. Tool descriptor injection scan
4. Typosquatting detection (postmark vs p0stmark)
```

### 58.3. A2A Agent Card Checks

```python
# Verify signature, well-known URI, capabilities
result = security.validate_agent_card(card)
# → ValidationStatus.VALID | SUSPICIOUS | BLOCKED
```

---
