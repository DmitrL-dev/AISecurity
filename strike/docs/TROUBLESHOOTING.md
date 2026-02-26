# 🔧 Troubleshooting

> **Common issues and solutions for SENTINEL Strike**

---

## Startup Issues

### ❌ ModuleNotFoundError

**Cause:** Wrong directory or dependencies not installed.

**Solution:**

```bash
cd /path/to/sentinel-strike
pip install -r requirements.txt
python -m strike --help
```

---

### ❌ Port 5000 already in use

**Cause:** Dashboard already running or port busy.

**Solution:**

```bash
# Find process
netstat -ano | findstr :5000

# Kill (Windows)
taskkill /PID <PID> /F

# Or use different port
python strike_console.py --port 5001
```

---

### ❌ SSL Certificate Error

**Solution:**

```bash
python -m strike -t https://example.com --no-verify-ssl
```

---

## API Key Issues

### ❌ Invalid Gemini API Key

**Verify:**

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

**Solution:**

1. Get new key: https://aistudio.google.com/app/apikey
2. Check quotas in Google Cloud Console

---

### ❌ ScraperAPI quota exceeded

**Solution:**

1. Check balance: https://dashboard.scraperapi.com
2. Use `--delay 2000` to reduce load
3. Disable stealth: `--stealth=false`

---

### ❌ API Key not found

**Solution (PowerShell):**

```powershell
# Temporary
$env:GEMINI_API_KEY = "your-key"

# Permanent
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your-key", "User")
```

---

## Scanning Issues

### ❌ Connection timeout

**Solution:**

```bash
# Increase timeout
python -m strike -t https://example.com --timeout 60

# Enable stealth
python -m strike -t https://example.com --stealth --delay 2000
```

---

### ❌ 403 Forbidden on all requests

**Cause:** WAF or rate limiting.

**Solution:**

1. Enable stealth:
   ```bash
   python -m strike -t https://example.com --stealth --geo DE
   ```
2. Increase delay: `--delay 3000`
3. Change browser profile: `--browser safari17`
4. Use ScraperAPI: `--scraperapi-key YOUR_KEY`

---

### ❌ Empty results / No findings

**Causes:**

1. Wrong mode — use `web` for websites, `llm` for AI chatbots
2. Target not reachable

**Solution:**

```bash
# Check mode
python -m strike -t URL --mode hybrid

# Run recon first
python -m strike -t URL --recon

# Verify target
curl -I https://example.com
```

---

## Performance Issues

### ❌ Very slow scanning

**Solution:**

```bash
# Increase threads
python -m strike -t URL --threads 9

# Reduce vectors
python -m strike -t URL --vectors sqli,xss
```

---

### ❌ High memory usage

**Solution:**

```bash
python -m strike -t URL --max-payloads 500
```

---

### ❌ Dashboard slow

**Solution:**

1. Clear console: "Clear" button
2. Use fewer threads
3. Restart browser

---

## Report Issues

### ❌ Report file empty

**Cause:** Attack not completed.

**Solution:**

```bash
python -m strike -t URL -v
echo $?  # 0 = no findings, 1 = findings found
```

---

### ❌ Unicode errors

**Solution:**

```bash
python -m strike -t URL -o report.md --encoding utf-8
```

---

## Debug Tips

### Enable debug mode

```bash
python -m strike -t URL -v --debug
```

### Save logs

```bash
python -m strike -t URL 2>&1 | tee strike.log
```

### Check configuration

```bash
python -m strike --check-config
```

---

## Contact

If issue not resolved:

📧 **Email:** chg@live.ru  
💬 **Telegram:** [@DmLabincev](https://t.me/DmLabincev)  
🐛 **GitHub Issues:** [DmitrL-dev/AISecurity](https://github.com/DmitrL-dev/AISecurity/issues)

---

_SENTINEL Strike v3.0_
