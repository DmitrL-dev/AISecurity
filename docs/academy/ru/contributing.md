# Участие в AI Security Academy

> **Помогите нам построить definitive платформу обучения AI security**

---

## Обзор

AI Security Academy — это проект, управляемый сообществом. Мы приветствуем вклад от security исследователей, разработчиков, преподавателей и практиков, которые хотят поделиться своими знаниями и улучшить образование в области AI security по всему миру.

---

## Способы участия

### 1. Создание новых уроков

Нам нужен контент по всем модулям:

| Модуль | Приоритетные области |
|--------|---------------------|
| **01-Fundamentals** | Новые архитектуры моделей, multimodal security |
| **02-Threats** | Emerging attack patterns, новые OWASP updates |
| **03-Attacks** | Novel техники, real-world case studies |
| **04-Agentic** | Новые протоколы, framework-specific guides |
| **05-Defense** | Улучшения detection, новые guardrail patterns |
| **06-Advanced** | Research implementations, mathematical foundations |
| **08-Labs** | Hands-on упражнения, CTF challenges |

### 2. Улучшение существующего контента

- Исправление технических ошибок или устаревшей информации
- Добавление примеров кода или уточнений
- Улучшение диаграмм и визуализаций
- Обновление для новых версий фреймворка

### 3. Переводы

Помогите сделать академию доступной:
- Переводите уроки на другие языки
- Проверяйте существующие переводы
- Адаптируйте примеры для региональных контекстов

### 4. Lab Exercises

Создавайте практический опыт обучения:
- Blue team detection challenges
- Red team attack сценарии
- CTF-style задачи
- Real-world симуляции

---

## Структура урока

Все уроки должны следовать этому шаблону:

```markdown
# Название урока

> **Урок:** XX.Y.Z - Короткое имя  
> **Время:** NN минут  
> **Prerequisites:** Список требуемых предыдущих уроков

---

## Цели обучения

К концу этого урока вы сможете:

1. Первая measurable цель
2. Вторая measurable цель
3. Третья measurable цель

---

## Основной контент

### Раздел 1: Введение концепции

Теория и объяснение...

### Раздел 2: Реализация

\`\`\`python
class ExampleImplementation:
    """Docstring объясняющий класс."""
    
    def __init__(self):
        self.attribute = "value"
\`\`\`

---

## Интеграция с SENTINEL

\`\`\`python
from sentinel import configure, Guard

configure(relevant_options=True)
guard = Guard(options=True)

@guard.protect
def example_usage():
    pass
\`\`\`

---

## Ключевые выводы

1. Первый ключевой момент
2. Второй ключевой момент
3. Третий ключевой момент

---

*AI Security Academy | Урок XX.Y.Z*
```

---

## Стандарты кода

### Python Style

- Используйте type hints
- Документируйте классы и сложные функции
- Используйте значимые имена переменных
- Добавляйте комментарии для неочевидной логики

### Требования к Code Blocks

- Всегда указывайте язык для syntax highlighting
- Включайте docstrings для классов и сложных функций
- Добавляйте inline комментарии для security-relevant логики
- Убедитесь что код запускается (протестирован перед отправкой)

---

## Content Guidelines

### Стиль написания

- **Ясный и прямой** — Избегайте жаргона без объяснения
- **Активный залог** — "Детектор сканирует паттерны" не "Паттерны сканируются"
- **Практический фокус** — Теория поддерживает hands-on применение
- **Security mindset** — Думайте как атакующий И защитник

### Техническая точность

- Весь код должен быть протестирован и работать
- Описания атак должны быть технически корректны
- Рекомендации по защите должны быть практичны
- Следите за быстро эволюционирующим ландшафтом угроз

---

## Процесс отправки

### 1. Fork и Clone

```bash
git clone https://github.com/YOUR-USERNAME/AISecurity.git
cd AISecurity/sentinel-community
```

### 2. Создание Branch

```bash
git checkout -b lesson/04-agentic-mcp-security
git checkout -b fix/03-injection-typo
git checkout -b improve/05-detection-examples
```

### 3. Написание контента

- Следуйте шаблону урока
- Тестируйте все примеры кода
- Включайте все необходимые разделы

### 4. Self-Review

Проверьте перед отправкой:
- [ ] Следует шаблону урока
- [ ] Весь код запускается без ошибок
- [ ] Цели обучения measurable
- [ ] Ключевые выводы резюмируют основные моменты
- [ ] Нет орфографических/грамматических ошибок
- [ ] Ссылки на другой контент работают

### 5. Submit Pull Request

```bash
git add .
git commit -m "Add lesson: MCP Protocol Security"
git push origin lesson/04-agentic-mcp-security
```

---

## Признание

Contributors признаются:
- Указаны в CONTRIBUTORS.md
- Credited в footer урока
- Featured в release notes
- Приглашены в contributor community

---

## Вопросы?

- **Вопросы по контенту**: Open GitHub Discussion
- **Технические проблемы**: Open GitHub Issue
- **Вопросы по процессу**: Email maintainers

---

*Спасибо за помощь в повышении безопасности AI систем!*

---

*AI Security Academy | Contributing Guide*
