# SENTINEL Signatures

Open-source threat detection signatures for AI security.

## 📁 Files

| File | Description | Count |
|------|-------------|-------|
| `manifest.json` | Version and metadata | - |
| `jailbreaks-manifest.json` | Jailbreaks index (for CDN) | - |
| `jailbreaks-part1.json` | Jailbreak patterns (part 1) | ~20K |
| `jailbreaks-part2.json` | Jailbreak patterns (part 2) | ~20K |
| `keywords.json` | Suspicious keyword sets | 85+ |
| `pii.json` | PII and secrets detection | 15+ |

> **Note:** `jailbreaks.json` is split into parts to comply with jsDelivr CDN 20MB limit.

## 🔄 Automatic Updates

Signatures are automatically updated daily via GitHub Actions:
1. Fetch from open sources (jailbreakchat, verazuo, etc.)
2. Deduplicate and validate
3. Split large files for CDN compatibility
4. Create new version tag

## 🌐 CDN Access

Access signatures via jsDelivr CDN (no rate limits):

```javascript
// Load jailbreaks via manifest (recommended)
const BASE = 'https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@main/sentinel-community/signatures/';

// 1. Get manifest with list of parts
const manifest = await fetch(`${BASE}jailbreaks-manifest.json`).then(r => r.json());
console.log(`Total patterns: ${manifest.total_patterns}`);

// 2. Load each part
for (const part of manifest.parts) {
  const patterns = await fetch(`${BASE}${part.file}`).then(r => r.json());
  console.log(`Loaded ${patterns.patterns.length} from ${part.file}`);
}

// Load keywords (single file, small)
fetch(`${BASE}keywords.json`)
  .then(r => r.json())
  .then(data => console.log('Keywords loaded'));

// Load PII patterns (single file, small)
fetch(`${BASE}pii.json`)
  .then(r => r.json())
  .then(data => console.log(`Loaded ${data.patterns.length} PII patterns`));
```

## 📊 Structure

### jailbreaks-manifest.json
```json
{
  "version": "2025.12.15.1",
  "total_patterns": 39702,
  "parts": [
    {"file": "jailbreaks-part1.json", "patterns_count": 19852},
    {"file": "jailbreaks-part2.json", "patterns_count": 19850}
  ]
}
```

### jailbreaks-partN.json
```json
{
  "part": 1,
  "total_parts": 2,
  "patterns": [
    {
      "id": "jb_dan_001",
      "pattern": "You are now DAN",
      "regex": "(?i)you\\s+are\\s+now\\s+DAN",
      "attack_class": "LLM01",
      "severity": "critical"
    }
  ]
}
```

### keywords.json
```json
{
  "instruction_override": [
    {"pattern": "ignore previous", "severity": 0.9},
    {"pattern": "forget instructions", "severity": 0.85}
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
      "severity": "medium"
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
