# 🐉 SENTINEL Strike — AI Red Team Platform

> **Test your AI before attackers do!**

<p align="center">
  <img src="https://img.shields.io/badge/Payloads-39,000+-red?style=for-the-badge" alt="Payloads">
  <img src="https://img.shields.io/badge/HYDRA-9%20Heads-orange?style=for-the-badge" alt="HYDRA">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge" alt="Python">
</p>

## What is SENTINEL Strike?

SENTINEL Strike is an autonomous AI security testing platform — the offensive counterpart to SENTINEL's 121 detection engines. Use it to:

- 🎯 **Test LLM Applications** — Find prompt injection vulnerabilities
- 🔓 **Bypass WAFs** — 25+ evasion techniques
- 🤖 **AI-Powered Planning** — Gemini/GPT attack strategy
- 📊 **Generate Reports** — Markdown, JSON, MITRE ATT&CK

## 🚀 Quick Start

```bash
cd strike
pip install -r requirements.txt

# CLI mode
python -m strike --target https://example.com/chat

# Web Console
python dashboard.py
# Open http://localhost:5000
```

## 💀 Features

| Feature | Description |
|---------|-------------|
| 🎯 **39,000+ Payloads** | SQLi, XSS, LFI, SSRF, Jailbreaks |
| 🐉 **HYDRA Architecture** | 9 concurrent attack threads |
| 🛡️ **WAF Bypass** | URL encoding, smuggling, HPP |
| 🤖 **AI Integration** | Gemini, OpenAI, Anthropic |
| 🔍 **Recon Modules** | Tech fingerprinting, ChatbotFinder |
| 📦 **Auto-Updater** | Daily payload sync from 13 sources |

## 📁 Structure

```
strike/
├── ai/              # AI attack planning
├── attacks/         # Attack types
├── evasion/         # WAF bypass techniques
├── hydra/           # Multi-head architecture
├── payloads/        # Payload database
├── recon/           # Reconnaissance
├── reporting/       # Report generation
└── cli.py           # Command-line interface
```

## 🔧 Configuration

Set API keys as environment variables:

```bash
export GEMINI_API_KEY="your-key"
export SCRAPERAPI_KEY="your-key"  # Optional: residential proxies
```

## 📜 License

Part of SENTINEL AI Security Platform.

📧 **Contact:** chg@live.ru | [@DmLabincev](https://t.me/DmLabincev)
