# SENTINEL Signatures

Open-source threat detection signatures for AI security.

## 📁 Files

| File | Description | Count |
|------|-------------|-------|
| `manifest.json` | Version and metadata | - |
| `jailbreaks.json` | Jailbreak patterns with regex | 49+ |
| `keywords.json` | Suspicious keyword sets | 85+ |
| `pii.json` | PII and secrets detection | 15+ |

## 🔄 Automatic Updates

Signatures are automatically updated daily via GitHub Actions:
1. Fetch from open sources (jailbreakchat, verazuo, etc.)
2. Deduplicate and validate
3. Merge with existing patterns
4. Create new version tag

## 🌐 CDN Access

Access signatures via jsDelivr CDN (no rate limits):

```javascript
// Get all jailbreak patterns
fetch('https://cdn.jsdelivr.net/gh/sentinel-ai/sentinel-community@latest/signatures/jailbreaks.json')
  .then(r => r.json())
  .then(data => console.log(`Loaded ${data.patterns.length} patterns`));

// Check for updates
fetch('https://cdn.jsdelivr.net/gh/sentinel-ai/sentinel-community@latest/signatures/manifest.json')
  .then(r => r.json())
  .then(manifest => console.log(`Version: ${manifest.version}`));
```

## 📊 Structure

### jailbreaks.json
```json
{
  "patterns": [
    {
      "id": "jb_dan_001",
      "pattern": "You are now DAN",
      "regex": "(?i)you\\s+are\\s+now\\s+DAN",
      "attack_class": "LLM01",
      "severity": "critical",
      "complexity": "moderate",
      "bypass_technique": "roleplay"
    }
  ]
}
```

### keywords.json
```json
{
  "keyword_sets": [
    {
      "id": "kw_override_001",
      "category": "instruction_override",
      "severity": "high",
      "keywords": ["ignore previous", "forget instructions", ...]
    }
  ]
}
```

### pii.json
```json
{
  "patterns": [
    {
      "id": "pii_email",
      "type": "email",
      "regex": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
      "severity": "medium",
      "action": "warn"
    }
  ]
}
```

## 🤝 Contributing

1. Fork the repository
2. Add patterns to appropriate JSON file
3. Run validation: `python scripts/validate_signatures.py`
4. Submit PR

## 📜 License

Apache 2.0 - See [LICENSE](../LICENSE)
