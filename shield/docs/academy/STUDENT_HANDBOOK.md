# SENTINEL Academy — Student Handbook

## Добро пожаловать

Ты начинаешь путь в AI Security.

Этот handbook — твой гайд.

---

## Структура программы

### Уровни сертификации

```
         SSE (Expert)
              ↑
     ┌────────┴────────┐
     ↓                 ↓
   SRTS             SBTS
 (Red Team)      (Blue Team)
     └────────┬────────┘
              ↓
         SSP (Professional)
              ↑
              ↓
         SSA (Associate)
```

---

## SSA (Associate)

### Кому подходит

- Разработчики
- Junior security инженеры
- Те, кто хочет понять AI Security

### Требования

- Базовые знания C
- Понимание HTTP/REST
- Опыт работы с Linux/CLI

### Путь обучения

| Модуль | Тема                        | Время      |
| ------ | --------------------------- | ---------- |
| 0      | Почему AI небезопасен       | 1 час      |
| 1      | Атаки на AI                 | 4 часа     |
| 2      | Архитектура Shield          | 4 часа     |
| 3      | Установка                   | 3 часа     |
| 4      | Правила и Паттерны          | 4 часа     |
| 5      | Интеграция в код            | 4 часа     |
| **5B** | **CLI Reference (194 cmd)** | **3 часа** |

**Всего: ~23 часа**

### Лабораторные

- LAB-101: Установка Shield
- LAB-102: Базовая конфигурация
- LAB-103: Блокировка Injection
- LAB-104: Docker Deployment

### Экзамен SSA-100

- 60 вопросов
- 90 минут
- 70% для прохождения

---

## SSP (Professional)

### Кому подходит

- Security инженеры
- DevSecOps
- Архитекторы

### Требования

- SSA сертификация
- Опыт C/C++
- Понимание сетей

### Модули

- Advanced Architecture
- Guards Deep Dive
- Protocols (6 базовых)
- **Protocols Extended (14 дополнительных) — 7B**
- High Availability
- Monitoring

**Всего: ~90 часов (4-5 недель)**

### Экзамен SSP-200

- 80 вопросов
- 120 минут
- 75% для прохождения

---

## SSE (Expert)

### Кому подходит

- Senior architects
- Security leads
- Те, кто хочет контрибьютить

### Требования

- SSP сертификация
- 6+ месяцев работы с Shield

### Модули

- Internals
- Custom Guard Development
- Plugin System
- Protocol Development
- Performance Engineering
- **Policy Engine & eBPF — 16**
- Capstone Project

**Всего: ~180 часов (8-10 недель)**

### Экзамен SSE-300

- Теория: 60 вопросов
- Практика: 4 часа hands-on
- 80% для прохождения

---

## Специализации

### SRTS (Red Team)

После SSP. Фокус на атаке:

- Offensive AI Security
- Attack Methodology
- Evasion Techniques
- Payload Development

### SBTS (Blue Team)

После SSP. Фокус на защите:

- Defensive AI Security
- Threat Detection
- Incident Response
- Forensics

---

## Как учиться

### Золотые правила

1. **Читай модуль полностью** — не пропускай
2. **Делай лабы** — практика важнее теории
3. **Экспериментируй** — меняй параметры
4. **Документируй** — записывай что узнал
5. **Задавай вопросы** — в community

### Порядок

```
1. Прочитай Module
2. Выполни Labs
3. Пройди Quiz
4. Повтори сложное
5. Перейди к следующему
```

---

## Ресурсы

### Документация

| Файл                        | Назначение              |
| --------------------------- | ----------------------- |
| `docs/academy/MODULE_*.md`  | Учебные модули          |
| `docs/academy/LABS.md`      | Лабораторные            |
| `docs/academy/EXAM_BANK.md` | Вопросы для подготовки  |
| `docs/tutorials/*.md`       | Практические тьюториалы |

### API Reference

```
docs/API_REFERENCE.md
docs/CLI_REFERENCE.md
```

### Community

- GitHub Discussions
- Discord (coming soon)

---

## FAQ

**Q: Нужен ли опыт с Python?**
A: Нет. Shield написан на чистом C. Python не используется.

**Q: Сколько времени нужно на SSA?**
A: 2-3 недели при 2-3 часах в день.

**Q: Можно ли пропустить уровни?**
A: Нет. Каждый уровень строится на предыдущем.

**Q: Где сдать экзамен?**
A: Online через SENTINEL Academy Portal (coming soon).

---

## Принципы

1. **Глубина важнее скорости**
2. **Практика = Знание**
3. **Чистый C — без компромиссов**
4. **Профессиональный уровень**

---

_"Лёгкая дорога не всегда правильная."_

_SENTINEL Academy_
