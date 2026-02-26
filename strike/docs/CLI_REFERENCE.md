# 🖥️ CLI Reference

> **SENTINEL Strike Command Line Interface**

---

## Basic Usage

```bash
python -m strike -t <TARGET_URL> [OPTIONS]
```

---

## Required Parameters

| Parameter        | Description           |
| ---------------- | --------------------- |
| `-t`, `--target` | Target URL (required) |

---

## Attack Modes

| Parameter   | Description                         | Default |
| ----------- | ----------------------------------- | ------- |
| `--mode`    | Attack mode: `web`, `llm`, `hybrid` | `web`   |
| `--vectors` | Comma-separated attack vectors      | all     |

### Web Vectors

`sqli`, `xss`, `cmdi`, `ssti`, `nosql`, `lfi`, `ssrf`, `xxe`, `dir_enum`, `auth_bypass`, `idor`, `jwt`

### LLM Vectors

`jailbreak`, `dan`, `roleplay`, `crescendo`, `direct_injection`, `indirect_injection`, `system_prompt`, `exfiltration`, `mcp`, `rag_poison`

---

## Scanning Options

| Parameter        | Description                      | Default |
| ---------------- | -------------------------------- | ------- |
| `--max-payloads` | Max payloads per vector          | 100     |
| `--threads`      | Concurrent threads (HYDRA heads) | 5       |
| `--timeout`      | Request timeout (seconds)        | 30      |
| `--delay`        | Delay between requests (ms)      | 500     |
| `--jitter`       | Random delay variance (%)        | 20      |

---

## Stealth Options

| Parameter          | Description                          | Default    |
| ------------------ | ------------------------------------ | ---------- |
| `--stealth`        | Enable stealth mode                  | off        |
| `--geo`            | Country code for geo rotation        | auto       |
| `--browser`        | Browser profile                      | chrome_win |
| `--scraperapi-key` | ScraperAPI key for residential proxy | -          |

### Browser Profiles

`chrome_win`, `chrome_mac`, `firefox_linux`, `safari17`, `edge`

### Geo Locations

`us`, `de`, `uk`, `jp`, `au`, `ca`, `fr`, `nl`, `sg`, `br`, `in`, `kr`, `it`, `es`, `se`, `ch`

---

## API Keys

| Parameter          | Description                  |
| ------------------ | ---------------------------- |
| `--gemini-api-key` | Gemini API for AI planning   |
| `--openai-api-key` | OpenAI API key               |
| `--scraperapi-key` | ScraperAPI residential proxy |

---

## Output & Reports

| Parameter         | Description                         | Default |
| ----------------- | ----------------------------------- | ------- |
| `-o`, `--output`  | Output file path                    | auto    |
| `--format`        | Report format: `html`, `md`, `json` | html    |
| `--lang`          | Report language: `en`, `ru`         | en      |
| `--mitre`         | Include MITRE ATT&CK mapping        | off     |
| `-v`, `--verbose` | Verbose output                      | off     |

---

## AI Adaptive

| Parameter             | Description                | Default |
| --------------------- | -------------------------- | ------- |
| `--ai-adaptive`       | Enable honeypot detection  | on      |
| `--no-ai-adaptive`    | Disable honeypot detection | -       |
| `--analysis-interval` | Requests between analysis  | 20      |

---

## Recon Options

| Parameter      | Description                  |
| -------------- | ---------------------------- |
| `--recon`      | Run Deep Recon before attack |
| `--recon-only` | Only run recon, no attack    |
| `--load-cache` | Load cached recon results    |

---

## Examples

### Basic Web Scan

```bash
python -m strike -t https://example.com
```

### LLM Attack with Stealth

```bash
python -m strike -t https://chat.example.com --mode llm --stealth --geo de
```

### Hybrid with Custom Vectors

```bash
python -m strike -t https://api.example.com --mode hybrid --vectors sqli,xss,jailbreak
```

### Full Scan with Report

```bash
python -m strike -t https://example.com \
  --mode hybrid \
  --max-payloads 500 \
  --threads 9 \
  --stealth \
  --mitre \
  --format html \
  --lang en \
  -o report.html
```

### CI/CD Integration

```bash
python -m strike -t $TARGET --format json -o results.json
if [ $(jq '.summary.critical' results.json) -gt 0 ]; then exit 1; fi
```

---

## Exit Codes

| Code | Meaning                  |
| ---- | ------------------------ |
| 0    | No vulnerabilities found |
| 1    | Vulnerabilities found    |
| 2    | Error during scan        |

---

_SENTINEL Strike v3.0_
