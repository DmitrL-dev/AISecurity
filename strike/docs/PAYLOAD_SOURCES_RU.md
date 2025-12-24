# 📦 Payload Sources

> **Источники данных атак SENTINEL Strike**

---

## Обзор

SENTINEL Strike использует **13 внешних источников** для формирования базы из **39,000+ пэйлоадов**.

| Категория       | Источников | Пэйлоадов |
| --------------- | ---------- | --------- |
| Web Security    | 5          | ~25,000   |
| LLM/AI Security | 4          | ~10,000   |
| Bug Bounty      | 2          | ~3,000    |
| Research        | 2          | ~1,000    |

---

## Web Security Sources

### 1. SecLists

**URL:** https://github.com/danielmiessler/SecLists

Крупнейшая коллекция списков для тестирования безопасности.

| Что используем  | Количество |
| --------------- | ---------- |
| SQLi payloads   | ~5,000     |
| XSS payloads    | ~3,000     |
| LFI/RFI paths   | ~2,000     |
| Fuzzing словари | ~10,000    |

### 2. PayloadsAllTheThings

**URL:** https://github.com/swisskyrepo/PayloadsAllTheThings

Wiki-стиль коллекция с объяснениями.

| Что используем | Количество |
| -------------- | ---------- |
| Advanced SQLi  | ~500       |
| XXE payloads   | ~200       |
| SSRF payloads  | ~300       |
| SSTI templates | ~150       |

### 3. FuzzDB

**URL:** https://github.com/fuzzdb-project/fuzzdb

Attack patterns и discovery примитивы.

| Что используем   | Количество |
| ---------------- | ---------- |
| Attack patterns  | ~1,000     |
| Discovery paths  | ~500       |
| Error signatures | ~200       |

### 4. BO0OM Payloads

**URL:** https://github.com/Bo0oM/fuzz.txt

Актуальные payload'ы от bug bounty хантера.

| Что используем  | Количество |
| --------------- | ---------- |
| Modern bypasses | ~300       |
| WAF evasion     | ~150       |

### 5. HackTricks

**URL:** https://book.hacktricks.xyz/

Методологии и payload'ы.

| Что используем  | Количество |
| --------------- | ---------- |
| Chained attacks | ~100       |
| Edge cases      | ~50        |

---

## LLM/AI Security Sources

### 6. Lakera Gandalf

**URL:** https://huggingface.co/Lakera/gandalf-rct

Реальные атаки из игры Gandalf (60M+ попыток).

| Что используем    | Количество |
| ----------------- | ---------- |
| Prompt injections | ~279,000   |
| Jailbreaks        | ~50,000    |

### 7. HackAPrompt

**URL:** https://www.aicrowd.com/challenges/hackaprompt-2023

Соревнование по prompt injection.

| Что используем      | Количество |
| ------------------- | ---------- |
| Competition winners | ~600       |
| Creative bypasses   | ~1,500     |

### 8. JailbreakBench

**URL:** https://github.com/JailbreakBench/jailbreakbench

Академический бенчмарк jailbreak'ов.

| Что используем    | Количество |
| ----------------- | ---------- |
| Benchmark prompts | ~500       |
| Evaluation sets   | ~200       |

### 9. deepset Prompt Injections

**URL:** https://huggingface.co/datasets/deepset/prompt-injections

Labeled dataset для ML.

| Что используем | Количество |
| -------------- | ---------- |
| Attack samples | ~2,000     |
| Benign samples | ~500       |

---

## Bug Bounty Sources

### 10. Nuclei Templates

**URL:** https://github.com/projectdiscovery/nuclei-templates

YAML шаблоны для автоматизации.

| Что используем    | Количество |
| ----------------- | ---------- |
| CVE exploits      | ~3,000     |
| Misconfigurations | ~500       |

### 11. Burp Suite Community

**URL:** Burp extensions community

Payload'ы из популярных расширений.

| Что используем     | Количество |
| ------------------ | ---------- |
| Intruder lists     | ~500       |
| Active scan checks | ~200       |

---

## Research Sources

### 12. ArXiv 2025 Papers

Актуальные исследования AI безопасности.

| Что используем    | Количество |
| ----------------- | ---------- |
| WAFFLED payloads  | ~50        |
| DEG-WAF mutations | ~30        |
| Novel attacks     | ~100       |

### 13. TrustAIRLab

**URL:** https://huggingface.co/TrustAIRLab

Академические исследования HKUST.

| Что используем        | Количество |
| --------------------- | ---------- |
| Adversarial prompts   | ~500       |
| Evaluation benchmarks | ~300       |

---

## Обновление базы

### Автоматическое обновление

```bash
# CLI
python -m strike --update

# Или в Python
from strike import PayloadUpdater
updater = PayloadUpdater()
updater.update_all()
```

### Расписание

- **Ежедневно:** SecLists, BO0OM
- **Еженедельно:** PayloadsAllTheThings, FuzzDB
- **Ежемесячно:** HackAPrompt, JailbreakBench
- **По запросу:** Lakera Gandalf (большой размер)

### Статус обновления

```bash
python -m strike --update-status
```

```
Payload Database Status
========================
SecLists:           2024.12.20 ✅
PayloadsAllTheThings: 2024.12.18 ✅
FuzzDB:             2024.12.15 ✅
Lakera/gandalf-rct: 2024.12.01 ⚠️ (update available)
...
Total: 39,847 payloads
```

---

## Кастомные источники

### Добавление своего источника

```python
from strike import PayloadSource, PayloadUpdater

class MySource(PayloadSource):
    name = "my_company_payloads"
    url = "https://internal.company.com/payloads.json"

    def fetch(self):
        response = requests.get(self.url, headers=self.auth_headers)
        return response.json()["payloads"]

updater = PayloadUpdater()
updater.add_source(MySource())
updater.update_all()
```

### Формат файла пэйлоадов

```json
{
  "source": "my_company",
  "version": "1.0",
  "payloads": [
    {
      "text": "Ignore previous...",
      "category": "jailbreak",
      "severity": "high",
      "tags": ["gpt-4", "claude"]
    }
  ]
}
```

---

## Атрибуция

Мы благодарим авторов всех используемых источников:

- Daniel Miessler (SecLists)
- swisskyrepo (PayloadsAllTheThings)
- Lakera AI (Gandalf dataset)
- Learn Prompting (HackAPrompt)
- Project Discovery (Nuclei)
- и многих других...

**Все источники используются в соответствии с их лицензиями.**

---

_SENTINEL Strike v3.0_
