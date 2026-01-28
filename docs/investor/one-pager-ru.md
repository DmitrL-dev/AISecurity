# SENTINEL — Инвестиционный Меморандум

## Executive Summary

**SENTINEL** — платформа защиты AI-систем от кибератак. 

Мы создаём "антивирус для искусственного интеллекта" — решение, которое защищает корпоративные LLM-приложения (чат-боты, AI-ассистенты, автономные агенты) от взлома, утечки данных и манипуляций.

---

## 1. Проблема: AI-системы уязвимы

### 1.1 Новый класс угроз

Традиционная кибербезопасность защищает сети, серверы, базы данных. Но AI-системы имеют **принципиально новую поверхность атаки**: они принимают инструкции на естественном языке.

> **Prompt Injection** — атака, при которой злоумышленник через текстовый ввод заставляет AI-систему выполнить вредоносные действия.

Это эквивалент SQL Injection, но для искусственного интеллекта.

### 1.2 Реальные инциденты 2025-2026

| Дата | Инцидент | Источник |
|------|----------|----------|
| **Март 2025** | Fortune 500 финансовая компания: AI customer service agent раскрыл конфиденциальные данные клиентов | Industry reports |
| **Июнь-Сен 2025** | **ShadowLeak**: Zero-click эксплойт ChatGPT Deep Research — извлечение данных из Gmail, Google Drive, GitHub | [Radware Research](https://www.radware.com) |
| **Июль-Сен 2025** | **Salesforce Agentforce "ForcedLeak"**: Prompt injection в CRM через AI-агента | [The Hacker News](https://thehackernews.com) |
| **Окт 2025** | **Microsoft 365 Copilot Mermaid Attack**: Эксфильтрация корпоративной почты через Office документы | [CSO Online](https://www.csoonline.com) |
| **Янв 2026** | **ZombieAgent**: Persistent zero-click атака на ChatGPT — implant в long-term memory, worm-like propagation | [GBHackers](https://gbhackers.com), [eWeek](https://www.eweek.com) |

> **Примечание:** Полные ссылки на статьи предоставляются по запросу. Инциденты подтверждены Radware, Tenable, и независимыми исследователями.

### 1.3 Масштаб проблемы

- **OWASP LLM Top 10 (2025)**: Prompt Injection — угроза #1
- **78% Enterprise** компаний используют LLM в production (Gartner, 2026)
- **Каждая AI-интеграция** создаёт потенциальный вектор атаки

---

## 2. Рынок: AI Security

### 2.1 Размер и прогноз

| Источник | 2025 | 2026 | 2030 | CAGR |
|----------|------|------|------|------|
| **Gartner** | $25.9 млрд | $51.3 млрд | — | 73.9% |
| **Grand View Research** | $25.35 млрд | — | $93.75 млрд | 24.4% |
| **Mordor Intelligence** | $30.92 млрд | — | $86.34 млрд | 22.8% |

> **Источники:**
> - [Grand View Research: AI in Cybersecurity Market](https://www.grandviewresearch.com/industry-analysis/artificial-intelligence-ai-cyber-security-market)
> - [Mordor Intelligence: AI Cybersecurity Solutions](https://www.mordorintelligence.com/industry-reports/ai-in-cybersecurity-market)

**Agentic AI Security** (подсегмент): $1.83 млрд (2025) → $7.84 млрд (2030), **CAGR 33.8%** — Mordor Intelligence

**CAGR: 22-24%** — один из самых быстрорастущих сегментов cybersecurity.

### 2.2 Драйверы роста

1. **AI Adoption** — взрывной рост внедрения LLM в enterprise
2. **Регуляция** — EU AI Act, требования к безопасности AI-систем
3. **Инциденты** — громкие взломы создают спрос на защиту
4. **Agentic AI** — автономные агенты с доступом к инструментам повышают риски

### 2.3 Целевые сегменты

| Сегмент | Почему покупают | Примеры |
|---------|----------------|---------|
| **Финтех/Банки** | Compliance, защита клиентских данных | Deutsche Bank, Тинькофф |
| **Здравоохранение** | HIPAA, конфиденциальность пациентов | Epic Systems, Philips |
| **Enterprise SaaS** | Защита AI-функций продукта | Salesforce, ServiceNow |
| **Консалтинг** | Защита внутренних AI-ассистентов | Deloitte, McKinsey |

---

## 3. Talent Market: Дефицит специалистов

### 3.1 Silicon Valley

| Метрика | Значение | Источник |
|---------|----------|----------|
| **Рост AI-вакансий** | +156% | [The IET](https://theiet.org) |
| **Рост спроса на AI Security skills** | +298% | The IET |
| **Salary premium** (AI + Security) | +28-43% vs обычные инженеры | [Investopedia](https://investopedia.com) |
| **AI Security Engineer (Silicon Valley)** | $175,000 - $250,000+ в год | [PatentPC](https://patentpc.com) |

### 3.2 Глобальный дефицит

- **Cybersecurity workforce gap**: 3.5+ млн незакрытых позиций глобально
- **AI Security** — ещё более узкая специализация с меньшим предложением
- **Рост запросов**: +31% к 2029 (US Bureau of Labor Statistics)

### 3.3 Что это значит для SENTINEL

Компании **не могут нанять** достаточно AI Security специалистов → покупают **решения** вместо найма → **SaaS модель** для SENTINEL.

---

## 4. Решение: SENTINEL

### 4.1 Что мы делаем

**SENTINEL** — защитный слой между пользователем и AI-моделью:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│  SENTINEL   │────▶│   LLM/AI    │
│   Input     │     │   Guard     │     │   Model     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │ Block/Alert │
                    └─────────────┘
```

### 4.2 Ключевые компоненты

| Компонент | Функция | Аналог |
|-----------|---------|--------|
| **Input Guard** | Блокирует вредоносные запросы | Web Application Firewall |
| **Output Guard** | Предотвращает утечку данных | Data Loss Prevention |
| **Agent Guard** | Контроль действий AI-агентов | Endpoint Protection |
| **Monitoring** | Real-time мониторинг и алерты | SIEM |

### 4.3 RLM: Следующее поколение AI-фреймворков

**RLM (Relational Language Memory)** — AI-агентный фреймворк нового поколения. Прямой конкурент **LangChain** с фокусом на enterprise и security.

#### Почему не LangChain?

LangChain стал стандартом для прототипов, но имеет критические ограничения:

| Проблема LangChain | Решение RLM |
|-------------------|-------------|
| **Нет persistent memory** — агент "забывает" между сессиями | **Hierarchical Memory** — 4 уровня памяти с TTL |
| **Нет security by design** — атаки через tools и prompts | **Встроенная интеграция с SENTINEL** |
| **Сложная отладка** — "черный ящик" решений | **Causal Chains** — полная история решений с причинами |
| **Token bloat** — неэффективное использование контекста | **Semantic Routing** — только релевантный контекст |
| **Enterprise не готов** — нет audit, compliance | **Built for Enterprise** — логирование, RBAC, audit trails |

#### Архитектура RLM

```
┌─────────────────────────────────────────────────────────────┐
│                        RLM Platform                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Memory     │  │  Reasoning  │  │  Security Layer     │  │
│  │  Bridge     │  │  Engine     │  │  (SENTINEL)         │  │
│  ├─────────────┤  ├─────────────┤  ├─────────────────────┤  │
│  │ L0: Rules   │  │ Causal      │  │ Input Guard         │  │
│  │ L1: Context │  │ Chains      │  │ Output Guard        │  │
│  │ L2: Working │  │ Decision    │  │ Tool Sandboxing     │  │
│  │ L3: Session │  │ Tracking    │  │ Audit Logging       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### Рыночная позиция

| Метрика | LangChain | RLM |
|---------|-----------|-----|
| **Funding** | $25M+ Series A | Seed |
| **Focus** | Developer tools, prototyping | Enterprise, production, security |
| **Memory** | Нет (3rd party) | Native, hierarchical |
| **Security** | Нет | Native (SENTINEL) |
| **Enterprise features** | Ограниченно | Полный набор |

#### Потенциал

| Метрика | Значение |
|---------|----------|
| **LangChain valuation** | $200M+ (2024) |
| **Наш TAM** | Тот же рынок, но enterprise segment |
| **Дифференциатор** | Security-first + Memory-native |
| **Timing** | Enterprise переходят от PoC к production → нужен RLM |

#### Аналогия

> **LangChain = jQuery для AI** — быстрый старт, но не для серьёзных проектов.
> 
> **RLM = React/Next.js для AI** — production-ready, enterprise-grade.

**Инвестиционный тезис:** LangChain доказал рынок. Мы забираем enterprise-сегмент с security + memory.

---

### 4.4 Почему SENTINEL + RLM, а не конкуренты

| Наш подход | Альтернативы |
|------------|--------------|
| **Open-source core** → доверие, transparency | Закрытые black-box решения |
| **Специализация на AI Security** | Общие security platforms с AI-модулем |
| **Интеграция за 5 минут** | Сложные enterprise deployments |
| **Academy + Community** | Только продукт без образования |
| **Memory + Security в одном** | Разрозненные решения |

---

## 5. Бизнес-модель

### 5.1 Продукты

| Продукт | Модель | Целевая цена |
|---------|--------|--------------|
| **SENTINEL Cloud** | SaaS, per-request | $0.001-0.01 за запрос |
| **SENTINEL Enterprise** | Annual license | $50,000 - $500,000/год |
| **Managed Security** | SOC-as-a-Service для AI | $10,000 - $50,000/мес |
| **Training/Certification** | AI Security Academy | $1,000 - $5,000/курс |

### 5.2 Unit Economics

| Метрика | Target |
|---------|--------|
| **Gross Margin** | 80%+ (software) |
| **CAC** | Низкий (compliance-driven, inbound) |
| **LTV/CAC** | >5x |
| **Net Revenue Retention** | 120%+ (expansion) |

### 5.3 Go-to-Market

1. **Open Source** → community adoption → enterprise conversion
2. **Academy** → lead generation → enterprise sales
3. **Partnerships** → AI platform integrations (Azure, AWS, GCP)
4. **Compliance** → "checkbox" для regulators

---

## 6. Traction

| Что есть | Детали |
|----------|--------|
| **MVP** | Working product, open-source на GitHub |
| **Academy** | 159 уроков, EN/RU версии |
| **DevKit** | Инструменты для разработчиков |
| **Pipeline** | Переговоры с enterprise клиентами |

---

## 7. Команда

- **Технический основатель**: 10+ лет опыта в разработке, ML и Security
- **Open-source подход**: Community-driven development
- **Текущий фокус**: Product-market fit и первые enterprise клиенты

---

## 8. Запрос на инвестиции

### 8.1 Раунд

**Seed: $[XXX]**

### 8.2 Использование средств

| Направление | % | Цель |
|-------------|---|------|
| **Команда** | 50% | 3-5 инженеров + sales |
| **GTM** | 25% | Marketing, conferences, content |
| **Compliance** | 15% | SOC2, ISO27001 сертификации |
| **Infrastructure** | 10% | Cloud, monitoring, security |

### 8.3 Milestones на 12 месяцев

- [ ] 10+ paying enterprise клиентов
- [ ] $[XXX] ARR
- [ ] SOC2 Type II
- [ ] Series A ready

---

## 9. Почему инвестировать сейчас

1. **Timing**: AI adoption взрывной рост, security lagging behind
2. **Regulatory tailwinds**: EU AI Act создаёт обязательный спрос
3. **First-mover advantage**: Рынок AI Security только формируется
4. **Proven model**: Повторяем путь WAF/EDR/SIEM для нового класса угроз

---


