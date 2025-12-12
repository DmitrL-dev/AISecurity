# Installation Guide

## Prerequisites

- Python 3.10+
- pip
- Docker (optional)

## Quick Install

```bash
pip install sentinel-community
```

## From Source

```bash
git clone https://github.com/your-org/sentinel-community.git
cd sentinel-community
pip install -r requirements.txt
```

## Docker

```bash
docker-compose up -d
```

## Verify Installation

```python
from sentinel import InjectionDetector

detector = InjectionDetector()
result = detector.analyze("Hello, world!")
print(f"Safe: {result.is_safe}")
```

## System Dependencies

For VLM protection (OCR):

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

---

## Next Steps

- [Quick Start](quickstart.md)
- [Configuration](../guides/configuration.md)
- [API Reference](../reference/api.md)
