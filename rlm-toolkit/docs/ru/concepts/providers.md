# Провайдеры LLM

RLM-Toolkit поддерживает 75+ LLM-провайдеров с унифицированным интерфейсом.

## Поддерживаемые провайдеры

### Облачные провайдеры

| Провайдер | Модели | Функции |
|-----------|--------|---------|
| **OpenAI** | GPT-4o, GPT-4, GPT-3.5 | Function calling, streaming, JSON mode |
| **Anthropic** | Claude 3.5, Claude 3, Claude 2 | Длинный контекст, vision |
| **Google** | Gemini Pro, Gemini Ultra, PaLM 2 | Мультимодальность, grounding |
| **Azure OpenAI** | GPT-4, GPT-3.5 (Azure hosted) | Enterprise compliance |
| **AWS Bedrock** | Claude, Titan, Llama 2 | AWS интеграция |
| **Cohere** | Command, Command-R | RAG оптимизация |
| **Mistral AI** | Mistral-7B, Mixtral-8x7B | Open-weight модели |

### Локальные провайдеры

| Провайдер | Описание |
|-----------|----------|
| **Ollama** | Запуск любых GGUF моделей локально |
| **vLLM** | Высокопроизводительный inference |
| **llama.cpp** | CPU/GPU inference |
| **LM Studio** | GUI + API сервер |
| **text-generation-webui** | Gradio-интерфейс |

### Специализированные провайдеры

| Провайдер | Применение |
|-----------|------------|
| **TogetherAI** | Fine-tuned open модели |
| **Anyscale** | Ray-based масштабирование |
| **Replicate** | Маркетплейс моделей |
| **Fireworks** | Низколатентный inference |
| **Groq** | Сверхбыстрый inference (LPU) |

## Использование

### Базовое использование

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
```

### С конфигурацией

```python
from rlm_toolkit import RLM
from rlm_toolkit.providers import OpenAIProvider

provider = OpenAIProvider(
    model="gpt-4o",
    temperature=0.7,
    max_tokens=4096,
    top_p=0.9,
    frequency_penalty=0.1,
    presence_penalty=0.1,
    api_key="your-key"  # Или используйте OPENAI_API_KEY env
)

rlm = RLM(provider=provider)
```

### Несколько провайдеров

```python
from rlm_toolkit.providers import (
    OpenAIProvider,
    AnthropicProvider,
    OllamaProvider
)

# Разные провайдеры для разных целей
main_provider = OpenAIProvider("gpt-4o")
backup_provider = AnthropicProvider("claude-3-sonnet")
local_provider = OllamaProvider("llama3")

rlm = RLM(
    provider=main_provider,
    fallback_providers=[backup_provider, local_provider]
)
```

## Функции провайдеров

### Streaming

```python
rlm = RLM.from_openai("gpt-4o")

for chunk in rlm.stream("Расскажи историю"):
    print(chunk, end="", flush=True)
```

### Function Calling

```python
from rlm_toolkit.tools import Tool

@Tool(name="get_weather")
def get_weather(city: str) -> str:
    return f"Погода в {city}: 22°C"

rlm = RLM.from_openai("gpt-4o", tools=[get_weather])
result = rlm.run("Какая погода в Токио?")
```

### JSON Mode

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(json_mode=True)
rlm = RLM.from_openai("gpt-4o", config=config)

result = rlm.run("Перечисли 3 фрукта как JSON массив")
# {"fruits": ["яблоко", "банан", "апельсин"]}
```

### Vision (Мультимодальность)

```python
rlm = RLM.from_openai("gpt-4o")

result = rlm.run(
    "Что на этом изображении?",
    images=["path/to/image.jpg"]
)
```

## Сравнение провайдеров

| Провайдер | Скорость | Цена | Контекст | Качество |
|-----------|----------|------|----------|----------|
| GPT-4o | ⭐⭐⭐ | $$ | 128K | ⭐⭐⭐⭐⭐ |
| Claude 3.5 | ⭐⭐⭐ | $$ | 200K | ⭐⭐⭐⭐⭐ |
| Gemini Pro | ⭐⭐⭐⭐ | $ | 1M | ⭐⭐⭐⭐ |
| Groq (Llama 3) | ⭐⭐⭐⭐⭐ | $ | 8K | ⭐⭐⭐ |
| Ollama (локальный) | ⭐⭐ | Бесплатно | Varies | ⭐⭐⭐ |

## Пользовательские провайдеры

Создание своего провайдера:

```python
from rlm_toolkit.providers import BaseProvider
from rlm_toolkit.types import Message, Response

class MyProvider(BaseProvider):
    name = "my_provider"
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
    
    def generate(self, messages: list[Message], **kwargs) -> Response:
        # Ваша реализация
        response = self._call_api(messages)
        return Response(content=response.text)
    
    def stream(self, messages: list[Message], **kwargs):
        # Реализация streaming
        for chunk in self._stream_api(messages):
            yield chunk.text

# Использование пользовательского провайдера
provider = MyProvider("https://api.example.com", "key")
rlm = RLM(provider=provider)
```

## Переменные окружения

| Переменная | Провайдер |
|------------|-----------|
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `GOOGLE_API_KEY` | Google AI |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI |
| `COHERE_API_KEY` | Cohere |
| `MISTRAL_API_KEY` | Mistral |
| `TOGETHER_API_KEY` | TogetherAI |
| `GROQ_API_KEY` | Groq |

## Лучшие практики

!!! tip "Выбор модели"
    - Используйте GPT-4o или Claude 3.5 для сложных рассуждений
    - Используйте GPT-4o-mini или Claude 3 Haiku для простых задач
    - Используйте локальные модели для конфиденциальных данных

!!! tip "Оптимизация стоимости"
    - Включите кэширование для повторных запросов
    - Используйте дешёвые модели для препроцессинга
    - Группируйте похожие запросы

!!! tip "Стратегия fallback"
    - Настройте резервные провайдеры для надёжности
    - Мониторьте rate limits и квоты

## Связанное

- [Туториал: Первое приложение](../tutorials/01-first-app.md)
- [How-to: Переключение провайдеров](../how-to/providers.md)
- [API Reference: Провайдеры](../api/providers.md)
