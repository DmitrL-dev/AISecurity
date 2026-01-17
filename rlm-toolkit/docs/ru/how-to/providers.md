# How-to: Настройка LLM провайдеров

Настройка и переключение между LLM провайдерами в RLM-Toolkit.

## Быстрый справочник

```python
from rlm_toolkit import RLM

# OpenAI
rlm = RLM.from_openai("gpt-4o")

# Anthropic
rlm = RLM.from_anthropic("claude-3-5-sonnet-20241022")

# Google
rlm = RLM.from_google("gemini-pro")

# Локальный (Ollama)
rlm = RLM.from_ollama("llama3")

# Azure OpenAI
rlm = RLM.from_azure_openai(
    deployment_name="gpt-4",
    api_version="2024-02-15-preview"
)
```

## Настройка температуры и параметров

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai(
    model="gpt-4o",
    temperature=0.7,
    max_tokens=4096,
    top_p=0.9,
    frequency_penalty=0.1,
    presence_penalty=0.1
)
```

## Использование переменных окружения

```bash
# .env файл
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

```python
from dotenv import load_dotenv
from rlm_toolkit import RLM

load_dotenv()
rlm = RLM.from_openai("gpt-4o")  # Использует OPENAI_API_KEY
```

## Настройка резервных провайдеров

```python
from rlm_toolkit import RLM
from rlm_toolkit.providers import OpenAIProvider, AnthropicProvider

main = OpenAIProvider("gpt-4o")
backup = AnthropicProvider("claude-3-sonnet")

rlm = RLM(
    provider=main,
    fallback_providers=[backup]
)
```

## Переключение провайдеров во время работы

```python
rlm = RLM.from_openai("gpt-4o")
response = rlm.run("Привет")

# Переключение на Anthropic
rlm.set_provider(RLM.from_anthropic("claude-3-sonnet").provider)
response = rlm.run("Привет снова")
```

## Streaming

```python
rlm = RLM.from_openai("gpt-4o")

for chunk in rlm.stream("Расскажи историю"):
    print(chunk, end="", flush=True)
```

## JSON режим

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(json_mode=True)
rlm = RLM.from_openai("gpt-4o", config=config)

result = rlm.run("Перечисли 3 фрукта как JSON")
# {"fruits": ["яблоко", "банан", "апельсин"]}
```

## Vision (мультимодальность)

```python
rlm = RLM.from_openai("gpt-4o")

result = rlm.run(
    "Что на этом изображении?",
    images=["path/to/image.jpg"]
)
```

## Пользовательский таймаут и повторы

```python
from rlm_toolkit.providers import OpenAIProvider

provider = OpenAIProvider(
    model="gpt-4o",
    timeout=60,
    max_retries=3,
    retry_delay=1.0
)
```

## Связанное

- [Концепция: Провайдеры](../concepts/providers.md)
- [Туториал: Первое приложение](../tutorials/01-first-app.md)
