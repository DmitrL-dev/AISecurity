# Templates

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Шаблоны промптов** для консистентных, переиспользуемых промптов

## Быстрый старт

```python
from rlm_toolkit.templates import PromptTemplate

template = PromptTemplate(
    template="Ответь на вопрос: {question}\nКонтекст: {context}",
    input_variables=["question", "context"]
)

prompt = template.format(
    question="Какая столица?",
    context="Франция в Европе"
)
```

## Типы шаблонов

### PromptTemplate

```python
from rlm_toolkit.templates import PromptTemplate

# Простой шаблон
template = PromptTemplate(
    template="Суммаризируй: {text}",
    input_variables=["text"]
)

# С валидацией
template = PromptTemplate(
    template="Переведи на {language}: {text}",
    input_variables=["language", "text"],
    validate_template=True
)
```

### ChatPromptTemplate

```python
from rlm_toolkit.templates import ChatPromptTemplate, SystemMessage, HumanMessage

template = ChatPromptTemplate.from_messages([
    SystemMessage("Ты полезный ассистент"),
    HumanMessage("{user_input}")
])

messages = template.format_messages(user_input="Привет!")
```

### FewShotPromptTemplate

```python
from rlm_toolkit.templates import FewShotPromptTemplate

examples = [
    {"input": "2+2", "output": "4"},
    {"input": "3*3", "output": "9"}
]

template = FewShotPromptTemplate(
    examples=examples,
    example_template="Вход: {input}\nВыход: {output}",
    prefix="Реши математические задачи:",
    suffix="Вход: {question}\nВыход:",
    input_variables=["question"]
)
```

## Встроенные шаблоны

```python
from rlm_toolkit.templates import (
    QA_TEMPLATE,
    SUMMARIZE_TEMPLATE,
    TRANSLATE_TEMPLATE,
    CODE_REVIEW_TEMPLATE,
    EXTRACT_TEMPLATE
)

# Использование готовых шаблонов
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
result = rlm.run(QA_TEMPLATE.format(
    question="Что такое AI?",
    context="AI — это искусственный интеллект..."
))
```

## Связанное

- [Optimize](optimize.md)
- [Agents](agents.md)
