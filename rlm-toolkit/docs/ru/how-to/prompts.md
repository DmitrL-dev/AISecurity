# How-to: Prompt Engineering

Рецепты эффективного дизайна промптов.

## Системные промпты

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

rlm.set_system_prompt("""
Ты полезный ассистент по программированию на Python.
Всегда предоставляй рабочие примеры кода.
Форматируй код с правильными отступами.
""")

response = rlm.run("Как прочитать JSON файл?")
```

## Шаблоны промптов

```python
from rlm_toolkit.prompts import PromptTemplate

template = PromptTemplate("""
Проанализируй следующий {document_type}:

{content}

Предоставь:
1. Резюме
2. Ключевые моменты
3. Рекомендации
""")

prompt = template.format(
    document_type="контракт",
    content="..."
)
```

## Chat шаблоны промптов

```python
from rlm_toolkit.prompts import ChatPromptTemplate

template = ChatPromptTemplate.from_messages([
    ("system", "Ты {role}"),
    ("human", "{question}")
])

messages = template.format(
    role="эксперт по Python",
    question="Что такое декоратор?"
)
```

## Few-Shot промптинг

```python
from rlm_toolkit.prompts import FewShotPromptTemplate

examples = [
    {"input": "счастливый", "output": "грустный"},
    {"input": "большой", "output": "маленький"},
    {"input": "быстрый", "output": "медленный"}
]

template = FewShotPromptTemplate(
    examples=examples,
    prefix="Дай противоположное для каждого слова:",
    suffix="Ввод: {input}\nВывод:",
    example_prompt="Ввод: {input}\nВывод: {output}"
)

prompt = template.format(input="горячий")
```

## Chain-of-Thought

```python
rlm = RLM.from_openai("gpt-4o")

response = rlm.run("""
Решай пошагово:

В магазине 25 яблок. Продали 12 и получили ещё 8.
Сколько яблок теперь?

Продумай каждый шаг:
""")
```

## Форматирование вывода

```python
from rlm_toolkit import RLM, RLMConfig

# JSON режим
config = RLMConfig(json_mode=True)
rlm = RLM.from_openai("gpt-4o", config=config)

response = rlm.run("""
Извлеки информацию о человеке как JSON:
"Иван Петров, 30 лет"

Формат: {"name": str, "age": int}
""")
```

## Структурированный вывод

```python
from pydantic import BaseModel
from rlm_toolkit import RLM

class Person(BaseModel):
    name: str
    age: int
    city: str

rlm = RLM.from_openai("gpt-4o")
person = rlm.run_structured(
    "Извлеки: Иван, 30, живёт в Москве",
    output_schema=Person
)
print(person.name)  # "Иван"
```

## Role-Based промпты

```python
roles = {
    "expert": "Ты senior Python разработчик с 20 годами опыта.",
    "teacher": "Ты терпеливый учитель, объясняющий начинающим.",
    "critic": "Ты code reviewer, ищущий баги и улучшения."
}

rlm.set_system_prompt(roles["expert"])
```

## Инъекция контекста

```python
from rlm_toolkit.prompts import PromptTemplate

template = PromptTemplate("""
Контекст: {context}

На основе контекста выше, ответь: {question}

Если контекст не содержит ответа, скажи "Не знаю".
""")
```

## Связанное

- [How-to: Провайдеры](./providers.md)
- [Туториал: Первое приложение](../tutorials/01-first-app.md)
