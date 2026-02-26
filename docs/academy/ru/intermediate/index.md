# Средний уровень

Знания AI-безопасности для production. Для security-инженеров и senior-разработчиков.

!!! info "Требования"
    Пройдите [трек для начинающих](../beginner/index.md) или имейте эквивалентный опыт.

## Модули

### Основы ИИ
Глубокое понимание моделей, которые вы защищаете.

- [Transformers](ai-fundamentals/01-transformers.md) · [Encoder-Only](ai-fundamentals/02-encoder-only.md) · [Decoder-Only](ai-fundamentals/03-decoder-only.md) · [Vision Transformers](ai-fundamentals/05-vision-transformers.md) · [MoE](ai-fundamentals/07-mixture-of-experts.md) · [Обучение](ai-fundamentals/12-finetuning-rlhf.md) · [Токенизация](ai-fundamentals/14-tokenization-embeddings.md)

### Ландшафт угроз
Стандарты OWASP в глубину — каждая уязвимость с реальными примерами.

- [LLM01–LLM10](threats/LLM01-prompt-injection.md) — Полный OWASP LLM Top 10
- [ASI01](threats/ASI01-agentic-injection.md) — Agentic AI Top 10

### Векторы атак
Практическое понимание работы атак.

- [Прямая инъекция](attacks/prompt-injection-direct.md) · [Косвенная инъекция](attacks/prompt-injection-indirect.md)
- [DAN](attacks/jailbreak-dan.md) · [Crescendo](attacks/jailbreak-crescendo.md) · [Policy Puppetry](attacks/jailbreak-policy-puppetry.md) · [Time Bandit](attacks/jailbreak-time-bandit.md)
- [Извлечение данных](attacks/model-data-extraction.md) · [Угрозы MCP](attacks/mcp-security-threats.md)

### Безопасность агентов
Защита AI-агентов, инструментов и мульти-агентных систем.

- [Архитектуры](agentic/react-pattern.md) · [Мульти-агент](agentic/multi-agent.md) · [Память](agentic/memory.md) · [Зоны доверия](agentic/trust-zones.md)
- [MCP](agentic/mcp.md) · [A2A](agentic/a2a.md) · [Авторизация](agentic/authorization.md)

### Стратегии защиты
Детекция, guardrails и интеграция Sentinel.

- [Паттерн-матчинг](defense/pattern-matching.md) · [Поведенческий анализ](defense/behavioral-analysis.md) · [Guardrails](defense/guardrails-frameworks.md)
- [Архитектура Sentinel](defense/sentinel-engine-architecture.md) · [Практическая интеграция](defense/sentinel-practical-integration.md)

### Production
Деплой, масштабирование, мониторинг, compliance.

- [Архитектура](production/architecture.md) · [Docker](production/docker.md) · [Kubernetes](production/kubernetes.md)
- [SIEM](production/siem-integration.md) · [SOAR](production/soar-playbooks.md) · [Мониторинг](production/monitoring.md) · [Производительность](production/performance.md)

### Red Teaming
Наступательная безопасность со STRIKE.

- [STRIKE](red-team/strike.md) · [Пейлоады](red-team/payloads.md) · [Автоматический пентест](red-team/pentesting.md)

## Что дальше?

Готовы к исследовательскому уровню? Переходите к [**Продвинутому →**](../advanced/index.md) — TDA, формальные методы, разработка движков.
