---
title: SENTINEL AI Security
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
short_description: Test prompts against 200+ AI security detection engines
---

# 🛡️ SENTINEL AI Security Demo

Test your prompts against 200+ AI security detection engines.

## Features

- **Prompt Injection Detection** - Identifies attempts to override instructions
- **Jailbreak Detection** - Catches DAN-style bypass attempts  
- **Code Injection Detection** - Finds malicious code patterns
- **Data Extraction Detection** - Blocks attempts to leak sensitive data
- **Social Engineering Detection** - Identifies manipulation tactics

## Detection Modes

| Mode | Speed | Engines | Use Case |
|------|-------|---------|----------|
| Quick | Fast | ~50 | Basic screening |
| Full | Medium | ~150 | Standard protection |
| Paranoid | Slow | 200 | Maximum security |

## Install Locally

```bash
pip install sentinel-llm-security
```

## Links

- 📦 [PyPI Package](https://pypi.org/project/sentinel-llm-security/)
- 🐙 [GitHub Repository](https://github.com/dmitryl/sentinel-ai)
- 📖 [Documentation](https://github.com/dmitryl/sentinel-ai#readme)

## License

MIT License - Free for commercial and personal use.
