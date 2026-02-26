# 🍯 Anti-Deception & Honeypot Detection

> **How SENTINEL Strike detects traps and false positives**

---

## Overview

SENTINEL Strike includes the **AI Adaptive Engine** — a system for detecting honeypots, tarpits, and deception technologies. This is critical for:

- ✅ Eliminating false positives
- ✅ Protecting the attacker from detection
- ✅ Saving time on irrelevant targets
- ✅ Accurate reports without "fake" vulnerabilities

---

## Threat Levels

Strike automatically classifies targets into 5 levels:

| Level             | Indicator                   | Action               |
| ----------------- | --------------------------- | -------------------- |
| 🟢 **NORMAL**     | Normal target               | Continue attack      |
| 🟡 **SUSPICIOUS** | Suspicious patterns         | Increase delay 3x    |
| 🔴 **HONEYPOT**   | High probability of trap    | Recommend abort      |
| 🐢 **TARPIT**     | Intentional slowdown        | Minimal requests 5x  |
| 🎭 **DECEPTION**  | Active deception technology | Abort + don't report |

---

## Detection Indicators

### 📊 Statistical Anomalies

| Indicator              | Weight | Description                     |
| ---------------------- | ------ | ------------------------------- |
| **Fast Responses**     | 30%    | > 50% responses < 10ms          |
| **High Bypass Rate**   | 25%    | > 70% bypass rate               |
| **Uniform Techniques** | 20%    | All techniques work equally     |
| **Consistent Timing**  | 15%    | Low response time variance      |
| **All Critical**       | 10%    | Everything marked as "CRITICAL" |

### 🔍 How It Works

```
1. ResponseAnalyzer collects metrics for last 100 requests
2. HoneypotDetector calculates weighted score (0.0 - 1.0)
3. If score > 0.7 → high probability of honeypot
4. StrategyAdapter adapts strategy (slowdown/abort)
5. Report findings are marked as "suspicious"
```

---

## Detection Examples

### 🔴 Honeypot Detection

```
⚠️ SENTINEL Strike detected honeypot indicators:

Honeypot Score: 0.82 (HIGH)

Breakdown:
  • fast_responses: 0.90 (45 of 50 responses < 10ms)
  • high_bypass_rate: 0.75 (85% bypass rate - too good to be true)
  • uniform_techniques: 0.80 (SQLi, XSS, LFI all work equally)
  • consistent_timing: 0.60 (avg response 5ms, variance 2ms)

🍯 RECOMMENDATION: This is likely a honeypot.
   Do NOT report these as real vulnerabilities.
   Consider aborting scan.
```

### 🟡 Suspicious Patterns

```
⚠️ SENTINEL Strike detected suspicious patterns:

Threat Level: SUSPICIOUS (confidence: 0.55)

Anomalies:
  • Abnormally high bypass rate: 72%
  • Too many fast responses (<10ms): 35%

🔍 RECOMMENDATION:
   • Verify findings manually before reporting
   • Increase delay between requests
   • Switch to cautious mode
```

---

## Web Console Configuration

In the right panel of the dashboard (Stats & AI):

| Option                     | Description                            |
| -------------------------- | -------------------------------------- |
| **AI Adaptive**            | Enable/disable adaptive mode           |
| **Analysis Interval**      | Analyze every N requests (default: 20) |
| **Auto-Abort on Honeypot** | Automatically abort when detected      |

---

## CLI Configuration

```bash
# Enable AI Adaptive (default ON)
python -m strike -t https://example.com --ai-adaptive

# Disable (for full scan despite suspicions)
python -m strike -t https://example.com --no-ai-adaptive

# Set analysis interval
python -m strike -t https://example.com --analysis-interval 10
```

---

## API Usage

```python
from strike.ai.ai_adaptive import AIAdaptiveEngine, ThreatLevel

# Initialize
engine = AIAdaptiveEngine(
    gemini_key="AIza...",  # For AI analysis (optional)
    analysis_interval=20,
    enabled=True
)

# Record response
engine.record_response(
    response_time_ms=5.2,
    status_code=200,
    content_length=1500,
    is_bypass=True,
    payload_type="sqli",
    technique="UNION-based"
)

# Check threat level
threat = engine.get_threat_level()
if threat == ThreatLevel.HONEYPOT:
    print("🍯 Honeypot detected! Aborting...")

# Get recommended delay
delay = engine.get_adjusted_delay(base_delay=500)  # May return 1500 for SUSPICIOUS

# Check if should continue
if not engine.should_continue():
    print("AI recommends to abort")
```

---

## Report Integration

When suspicious patterns are detected, the report contains:

### ⚠️ Honeypot Warning Section

```html
🍯 Suspicious responses detected 23 of 150 bypasses have anomalously fast
response time (<10ms). This may indicate: • Honeypot/Tarpit — fake
vulnerabilities to track attackers • Deception Technology — detection and
slowdown systems • WAF with fake signatures — intentionally passed requests for
analysis ⚠️ Recommendation: These findings require particularly careful manual
verification.
```

### 📊 False Positive Rates

The report includes typical FPR for each vulnerability type:

| Type               | FPR    | Reason                                  |
| ------------------ | ------ | --------------------------------------- |
| WAF Bypass         | 20-30% | WAF may pass without real vulnerability |
| SQL Injection      | 5-10%  | Response may change for other reasons   |
| XSS                | 15-20% | Payload may reflect but not execute     |
| LFI/Path Traversal | 10-15% | File may not exist                      |

---

## Best Practices

### ✅ Recommendations

1. **Always verify findings manually**

   - Use provided PoC
   - Check in Burp Suite / browser

2. **Pay attention to AI Warnings**

   - If Strike warns about honeypot — it's serious
   - Don't include suspicious findings in reports

3. **Use Gemini for deep analysis**

   - With API key, Strike uses Gemini for pattern analysis
   - More accurate deception technology detection

4. **Check response time distribution**
   - Real systems have variance in response time
   - Constant 5-10ms — red flag

### ⚠️ What to Do When Honeypot Detected

1. **DO NOT report** these findings as real vulnerabilities
2. **Document** the honeypot presence in your report
3. **Notify the client** that deception technology was detected
4. **Switch** to other targets/endpoints

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│              AI Adaptive Engine                      │
├─────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌───────────────────────────┐   │
│  │ Response      │  │ Honeypot Detector         │   │
│  │ Analyzer      │──│ • Statistical analysis    │   │
│  │ (Window: 100) │  │ • Gemini AI (optional)    │   │
│  └───────────────┘  │ • Score calculation       │   │
│                     └───────────────────────────┘   │
│                              │                       │
│                              ▼                       │
│                     ┌───────────────────────────┐   │
│                     │ Strategy Adapter          │   │
│                     │ • Delay multiplier        │   │
│                     │ • Technique selection     │   │
│                     │ • Abort decision          │   │
│                     └───────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

_SENTINEL Strike v3.0 — Smart enough to know when NOT to attack_
