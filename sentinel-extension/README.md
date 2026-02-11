# SENTINEL Guard — Chrome Extension

> **AdBlock for AI prompts.** Protects your conversations in ChatGPT, Claude, Gemini, and Perplexity from prompt injection, jailbreaks, and PII leaks.

## Features

- 🛡️ **Real-time scanning** — every prompt checked before sending
- ⛔ **Injection blocking** — prevents prompt injection, jailbreak, DAN attacks
- 🔒 **PII detection** — warns about SSN, credit cards, passwords in prompts
- 📊 **Stats dashboard** — track scans, blocks, and threats
- ⚡ **Sub-1ms** — Rust-powered engines, zero latency impact
- 🌐 **Multi-platform** — ChatGPT, Claude, Gemini, Perplexity

## Supported Sites

| Site | URL | Status |
|------|-----|--------|
| ChatGPT | chatgpt.com | ✅ |
| Claude | claude.ai | ✅ |
| Gemini | gemini.google.com | ✅ |
| Perplexity | perplexity.ai | ✅ |

## Installation (Development)

1. Clone this repo
2. Open `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked"
5. Select the `sentinel-extension/` folder

## How It Works

```
User types prompt → SENTINEL scans → Safe? → Send to AI
                                   → Danger? → Block + notify
```

The extension intercepts prompts before they're sent to the AI service, scans them through SENTINEL Shield's 36 Rust-powered engines, and blocks dangerous inputs in real-time.

## Configuration

- **API Key**: Optional. Free tier includes 10K scans/month.
- **Auto-scan**: Automatically scans prompts as you type.
- **Sensitivity**: Low/Medium/High — controls detection threshold.

## Privacy

- ❌ No data stored on our servers
- ❌ No browsing history tracked
- ✅ Prompts scanned in real-time and immediately discarded
- ✅ API key stored locally in chrome.storage.sync

## License

Apache 2.0 — SENTINEL Community
