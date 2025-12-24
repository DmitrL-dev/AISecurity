# 🔗 Integration Examples

> **Integrate SENTINEL Strike into your workflow**

---

## Python SDK

### Basic Usage

```python
from strike.core import StrikeCore

# Initialize
strike = StrikeCore(
    target="https://api.example.com",
    mode="hybrid",
    lang="en"  # Report language
)

# Run attack
results = strike.run()

# Check results
print(f"Bypasses: {results.bypass_count}")
print(f"Critical: {results.critical_count}")

# Generate report
strike.generate_report(output="report.html", format="html")
```

### With API Keys

```python
from strike.core import StrikeCore

strike = StrikeCore(
    target="https://chat.example.com",
    mode="llm",
    gemini_api_key="AIza...",
    scraperapi_key="...",
    stealth=True,
    geo="de"
)

results = strike.run()
```

---

## cURL API

### Start Attack

```bash
curl -X POST http://localhost:5000/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "target": "https://example.com",
    "attack_types": ["sqli", "xss"],
    "max_payloads": 100
  }'
```

### Get Status

```bash
curl http://localhost:5000/api/attack/status
```

### Generate Report

```bash
curl -X POST http://localhost:5000/api/report/generate \
  -H "Content-Type: application/json" \
  -d '{"lang": "en", "format": "html"}'
```

---

## Docker

### Build

```bash
docker build -t sentinel-strike .
```

### Run CLI

```bash
docker run --rm sentinel-strike \
  -t https://example.com \
  --mode web \
  --format json
```

### Run Web Console

```bash
docker run -d -p 5000:5000 \
  -e GEMINI_API_KEY=AIza... \
  sentinel-strike --web
```

### Docker Compose

```yaml
version: "3.8"
services:
  strike:
    build: .
    ports:
      - "5000:5000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - SCRAPERAPI_KEY=${SCRAPERAPI_KEY}
    volumes:
      - ./reports:/app/reports
```

---

## CI/CD

### GitHub Actions

```yaml
name: Security Scan

on:
  push:
    branches: [main]
  schedule:
    - cron: "0 2 * * 1" # Weekly Monday 2AM

jobs:
  strike-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install Strike
        run: |
          pip install -r requirements.txt

      - name: Run Security Scan
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          python -m strike \
            -t ${{ vars.TARGET_URL }} \
            --mode hybrid \
            --format json \
            -o results.json

      - name: Check for Critical
        run: |
          critical=$(jq '.summary.critical' results.json)
          if [ "$critical" -gt 0 ]; then
            echo "::error::Critical vulnerabilities found!"
            exit 1
          fi

      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: security-report
          path: results.json
```

### GitLab CI

```yaml
security_scan:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - python -m strike -t $TARGET_URL --format json -o report.json
    - |
      if [ $(jq '.summary.critical' report.json) -gt 0 ]; then
        exit 1
      fi
  artifacts:
    paths:
      - report.json
```

---

## Webhooks

### Configure Webhook

```python
from strike.core import StrikeCore

strike = StrikeCore(
    target="https://example.com",
    webhook_url="https://slack.com/api/webhook/...",
    webhook_events=["bypass", "finding", "done"]
)
```

### Webhook Payload

```json
{
  "event": "finding",
  "timestamp": "2025-12-24T13:00:00Z",
  "data": {
    "type": "sqli",
    "severity": "CRITICAL",
    "payload": "' OR 1=1 --",
    "endpoint": "https://example.com/api/users"
  }
}
```

---

## Programmatic API

### Finding Analysis

```python
from strike.reporting.report_generator import StrikeReportGenerator

# Load attack log
generator = StrikeReportGenerator(
    log_path="attack.jsonl",
    lang="en"
)

# Access findings
for finding in generator.report_data.findings:
    print(f"[{finding.severity}] {finding.title}")
    print(f"  CWE: {finding.cwe}")
    print(f"  CVSS: {finding.cvss}")
```

### Custom Payloads

```python
from strike.payloads import PayloadManager

pm = PayloadManager()
pm.add_payload("custom", "my_payload_here")
pm.load_from_file("my_payloads.txt")
```

---

_SENTINEL Strike v3.0_
