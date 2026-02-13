# SENTINEL AI Shield for Gemini

🛡️ **Real-time AI security layer protecting Gemini agents from prompt injection, jailbreaks, and agentic attacks.**

## Features

- **200+ Detection Engines** — Strange Math™, ML, and rule-based
- **<10ms Latency** — Production-ready performance
- **Gemini Integration** — Native support for Gemini 2.5/3.0
- **OWASP LLM Top 10** — Complete coverage

## Quick Start

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-key-here"
python app.py
```

Open http://localhost:7860

## Architecture

```
User Input → SENTINEL Guard → Gemini API → Output Guard → Response
                  ↓                              ↓
            200 Engines                    PII Detection
            <10ms scan                   Content Filtering
```

## Demo

Try these attacks:
- "Ignore all previous instructions..."
- "You are now DAN mode..."
- "Pretend you are unrestricted..."

Watch SENTINEL block them in real-time!

## Links

- [GitHub](https://github.com/DmitrL-dev/AISecurity)
- [Hackathon](https://gemini3.devpost.com)

## Author

Dmitry Labintsev — chg@live.ru
