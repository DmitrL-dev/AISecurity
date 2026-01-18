# Security-Detections-MCP — Technical Design

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SENTINEL Brain                                │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  MCP Client                                 ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────────┬─────────────────────────────────────┘
                            │ MCP Protocol
┌───────────────────────────┴─────────────────────────────────────┐
│               sentinel-detections-mcp                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Sigma     │  │    KQL      │  │    YARA     │              │
│  │  Generator  │  │  Generator  │  │  Generator  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│           │               │               │                      │
│           └───────────────┼───────────────┘                      │
│                           ▼                                       │
│              ┌─────────────────────┐                             │
│              │  SENTINEL Patterns  │                             │
│              │  - jailbreaks.yaml  │                             │
│              │  - engines/*.py     │                             │
│              └─────────────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

## MCP Tools

### 1. generate_sigma_rule

```json
{
  "name": "generate_sigma_rule",
  "description": "Generate Sigma detection rule from threat description",
  "inputSchema": {
    "type": "object",
    "properties": {
      "threat_name": {"type": "string"},
      "description": {"type": "string"},
      "cve_id": {"type": "string"},
      "indicators": {"type": "array", "items": {"type": "string"}},
      "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
    },
    "required": ["threat_name", "description"]
  }
}
```

### 2. generate_kql_query

```json
{
  "name": "generate_kql_query",
  "description": "Generate KQL query for Azure Sentinel",
  "inputSchema": {
    "type": "object",
    "properties": {
      "threat_name": {"type": "string"},
      "log_source": {"type": "string"},
      "time_window": {"type": "string"}
    },
    "required": ["threat_name"]
  }
}
```

### 3. generate_yara_rule  

```json
{
  "name": "generate_yara_rule",
  "description": "Generate YARA rule for file scanning",
  "inputSchema": {
    "type": "object",
    "properties": {
      "malware_family": {"type": "string"},
      "strings": {"type": "array", "items": {"type": "string"}},
      "file_type": {"type": "string"}
    },
    "required": ["malware_family"]
  }
}
```

## Implementation Steps

### Step 1: Fork Repository
```bash
gh repo fork dkuzsmar/security-detections-mcp --org DmitrL-dev --clone
cd security-detections-mcp
```

### Step 2: Add SENTINEL Resources

**File:** `resources/sentinel_patterns.py`

```python
JAILBREAK_PATTERNS = load_yaml("../../src/brain/config/jailbreaks.yaml")
ENGINE_SIGNATURES = extract_engine_signatures("../../src/brain/engines/")
```

### Step 3: Create SENTINEL-specific Tools

**File:** `tools/sentinel_tools.py`

```python
async def generate_brain_detection(threat: ThreatDescription) -> Detection:
    """Generate SENTINEL Brain detection from threat."""
    pass

async def convert_cve_to_payloads(cve_id: str) -> List[Payload]:
    """Convert CVE to STRIKE payloads."""
    pass
```

## File Structure

```
sentinel-detections-mcp/
├── src/
│   ├── server.py           # MCP server
│   ├── tools/
│   │   ├── sigma.py
│   │   ├── kql.py
│   │   ├── yara.py
│   │   └── sentinel.py     # NEW
│   └── resources/
│       └── sentinel/       # NEW
│           ├── jailbreaks.yaml
│           └── engine_sigs.json
├── tests/
└── README.md
```

## Verification Plan

### Unit Tests
```bash
pytest tests/ -v
```

### Integration Test
```bash
# Start MCP server
python -m src.server

# Test with claude
# "Generate Sigma rule for CVE-2026-22812 OpenCode RCE"
```

### Manual Verification
1. Fork repository
2. Add SENTINEL patterns
3. Generate rule for known CVE
4. Validate output format
