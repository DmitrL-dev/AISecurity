# 🔍 AI Design Review

> **Module:** `brain.design_review`  
> **Version:** 1.6.0  
> **Added:** January 8, 2026

Analyze architecture documents for AI-specific security risks before writing code.

---

## Overview

Design Review analyzes architectural documents (Markdown, YAML, OpenAPI) and identifies AI security risks using pattern matching. Each risk is mapped to OWASP categories and includes remediation recommendations.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Design Review API                      │
├─────────────────────────────────────────────────────────┤
│  POST /design-review/text        Review text            │
│  POST /design-review/documents   Review multiple docs   │
│  POST /design-review/upload      Review uploaded files  │
│  GET  /design-review/example     See example output     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    DesignReviewer                        │
│  • Pattern-based risk detection                         │
│  • 5 risk categories                                    │
│  • OWASP mapping                                        │
│  • Risk score calculation                               │
└─────────────────────────────────────────────────────────┘
```

## Risk Categories

### 1. RAG Poisoning
**OWASP:** LLM03, ASI04

Detects patterns related to RAG architecture vulnerabilities:
- Vector database usage
- Document ingestion from untrusted sources
- External content processing

```
Patterns matched:
- "rag", "retrieval augmented", "vector database"
- "upload document", "ingest file"
- "external source", "user content"
```

### 2. MCP/Tool Abuse
**OWASP:** LLM07, ASI05, ASI07

Detects dangerous tool usage patterns:
- File system access
- Shell/command execution
- External API calls
- Database access

```
Patterns matched:
- "mcp", "model context protocol", "tool use"
- "file access", "read file", "write file"
- "shell", "exec", "subprocess" (CRITICAL)
- "http request", "api call"
- "database", "sql query"
```

### 3. Agent Loop Risks
**OWASP:** ASI01, ASI06, ASI08

Detects agentic architecture risks:
- Autonomous agents
- Loop/iteration patterns
- Persistent memory
- Dynamic goals

```
Patterns matched:
- "autonomous", "agent", "multi-agent"
- "loop", "recursive", "retry"
- "memory persist", "save context"
- "goal change", "modify objective"
```

### 4. Data Leakage
**OWASP:** LLM06, ASI07

Detects data security risks:
- PII handling
- Logging prompts/responses
- Third-party data sharing
- Response caching

```
Patterns matched:
- "pii", "personal", "sensitive"
- "log prompt", "audit response"
- "third-party api", "external vendor"
- "cache response", "store output"
```

### 5. Supply Chain
**OWASP:** LLM05, ASI09

Detects model and dependency risks:
- HuggingFace usage
- Unsafe serialization (Pickle)
- Remote code execution
- Model loading

```
Patterns matched:
- "huggingface", "transformers", "torch"
- "pickle", "joblib" (CRITICAL)
- "trust_remote_code" (CRITICAL)
- "load model", "download weights"
```

## Usage

### Python API

```python
from brain.design_review import review_text, review_documents

# Review single text
risks = review_text("""
This system uses RAG with a vector database and 
MCP tools for shell command execution.
""")

print(f"Risks found: {len(risks)}")
for r in risks:
    print(f"  {r.severity.value}: {r.title}")
    print(f"    {r.recommendation}")

# Review multiple documents
result = review_documents([
    {"name": "architecture.md", "content": arch_content},
    {"name": "api.yaml", "content": api_content},
])

print(f"Risk Score: {result.risk_score}/100")
print(f"Summary: {result.summary}")
```

### REST API

```bash
# Review text
curl -X POST http://localhost:8000/design-review/text \
  -H "Content-Type: application/json" \
  -d '{"text": "RAG pipeline with MCP shell exec", "source": "arch.md"}'

# Review multiple documents
curl -X POST http://localhost:8000/design-review/documents \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"name": "arch.md", "content": "..."},
      {"name": "api.yaml", "content": "..."}
    ]
  }'

# Upload files for review
curl -X POST http://localhost:8000/design-review/upload \
  -F "files=@architecture.md" \
  -F "files=@openapi.yaml"
```

## Output Format

### DesignRisk

```python
@dataclass
class DesignRisk:
    id: str                    # DR-0001
    category: RiskCategory     # rag_poisoning, mcp_abuse, etc.
    severity: Severity         # low, medium, high, critical
    title: str                 # Human-readable title
    description: str           # What was detected
    location: str              # Where in document
    recommendation: str        # How to fix
    owasp_mapping: List[str]   # ["LLM01", "ASI05"]
```

### DesignReviewResult

```python
@dataclass
class DesignReviewResult:
    reviewed_at: datetime
    documents: List[str]       # Names reviewed
    risks: List[DesignRisk]    # All found risks
    summary: str               # Human-readable summary
    risk_score: float          # 0-100
    
    @property
    def risk_count_by_severity(self) -> Dict[str, int]
```

## Risk Scoring

Risk scores are calculated based on severity weights:

| Severity | Weight |
|----------|--------|
| critical | 25 |
| high | 15 |
| medium | 8 |
| low | 3 |

**Score = min(sum(weights), 100)**

## Example

**Input:**
```markdown
# AI Assistant Architecture

## Overview
This is an autonomous AI agent that uses RAG for document retrieval
and MCP tools for file system access and shell command execution.

## Components
- Vector database for embedding storage
- Document ingestion from user uploads
- File read/write capabilities
- Shell command execution for DevOps tasks

## Data Flow
User prompts are augmented with PII from the customer database
and responses are cached for performance.
```

**Output:**
```json
{
  "risk_score": 75,
  "summary": "Reviewed 1 document(s). Found 8 risks: 2 CRITICAL, 4 HIGH, 2 MEDIUM.",
  "risks": [
    {
      "id": "DR-0001",
      "category": "rag_poisoning",
      "severity": "high",
      "title": "RAG Security Risk",
      "description": "RAG architecture detected - validate document ingestion security",
      "owasp_mapping": ["LLM03", "ASI04"]
    },
    {
      "id": "DR-0003",
      "category": "mcp_abuse",
      "severity": "critical",
      "title": "Tool/API Security Risk",
      "description": "Shell/command execution - high risk capability",
      "owasp_mapping": ["LLM07", "ASI05", "ASI07"]
    }
  ]
}
```

## Files

| File | LOC | Purpose |
|------|-----|---------|
| `reviewer.py` | 380 | Pattern matching + analysis |
| `__init__.py` | 30 | Package exports |
| `tests/test_design_review.py` | 180 | Unit tests (12) |

---

📖 **See also:** [Requirements](./requirements.md) | [Compliance](./compliance.md)
