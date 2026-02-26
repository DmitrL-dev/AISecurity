# Sentinel Academy

Добро пожаловать в **Sentinel Academy** — ваш путь к мастерству в AI-безопасности.

## Выберите уровень

| Уровень | Для кого | Темы |
|---------|----------|------|
| [**Начинающий**](beginner/index.md) | Разработчики, студенты | Prompt injection, основы OWASP, первая интеграция |
| [**Средний**](intermediate/index.md) | Security-инженеры | Векторы атак, безопасность агентов, production |
| [**Продвинутый**](advanced/index.md) | Исследователи, контрибьюторы | TDA, формальные методы, разработка движков, анализ CVE |
| [**Лаборатории**](labs/index.md) | Все | Практические упражнения blue team и red team |

## О Sentinel

Sentinel — open-source платформа AI-безопасности с **59 Rust-движками** и **8 оригинальными примитивами Sentinel Lattice** — формальными свойствами безопасности, отсутствующими в любом другом инструменте.

- **1101 тестов**, 0 провалов
- **<1ms** на движок — Aho-Corasick пре-фильтр + скомпилированные regex
- **OWASP LLM Top 10 + Agentic Top 10** покрытие

## Быстрый старт

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-core
cargo test
```

---

*[GitHub](https://github.com/DmitrL-dev/AISecurity) · [Справочник движков](../../reference/engines.md) · [Статья arXiv](../../papers/sentinel-lattice/main.pdf)*
