# LLM Providers

RLM-Toolkit supports 75+ LLM providers with a unified interface.

## Supported Providers

### Cloud Providers

| Provider | Models | Features |
|----------|--------|----------|
| **OpenAI** | GPT-4o, GPT-4, GPT-3.5 | Function calling, streaming, JSON mode |
| **Anthropic** | Claude 3.5, Claude 3, Claude 2 | Long context, vision |
| **Google** | Gemini Pro, Gemini Ultra, PaLM 2 | Multimodal, grounding |
| **Azure OpenAI** | GPT-4, GPT-3.5 (Azure hosted) | Enterprise compliance |
| **AWS Bedrock** | Claude, Titan, Llama 2 | AWS integration |
| **Cohere** | Command, Command-R | RAG optimization |
| **Mistral AI** | Mistral-7B, Mixtral-8x7B | Open-weight models |

### Local Providers

| Provider | Description |
|----------|-------------|
| **Ollama** | Run any GGUF model locally |
| **vLLM** | High-throughput inference |
| **llama.cpp** | CPU/GPU inference |
| **LM Studio** | GUI + API server |
| **text-generation-webui** | Gradio-based interface |

### Specialized Providers

| Provider | Use Case |
|----------|----------|
| **TogetherAI** | Fine-tuned open models |
| **Anyscale** | Ray-based scaling |
| **Replicate** | Model marketplace |
| **Fireworks** | Low-latency inference |
| **Groq** | Ultra-fast inference (LPU) |

## Usage

### Basic Usage

```python
from rlm_toolkit import RLM

# OpenAI
rlm = RLM.from_openai("gpt-4o")

# Anthropic
rlm = RLM.from_anthropic("claude-3-5-sonnet-20241022")

# Google
rlm = RLM.from_google("gemini-pro")

# Local (Ollama)
rlm = RLM.from_ollama("llama3")
```

### With Configuration

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
    api_key="your-key"  # Or use OPENAI_API_KEY env
)

rlm = RLM(provider=provider)
```

### Multiple Providers

```python
from rlm_toolkit.providers import (
    OpenAIProvider,
    AnthropicProvider,
    OllamaProvider
)

# Use different providers for different purposes
main_provider = OpenAIProvider("gpt-4o")
backup_provider = AnthropicProvider("claude-3-sonnet")
local_provider = OllamaProvider("llama3")

rlm = RLM(
    provider=main_provider,
    fallback_providers=[backup_provider, local_provider]
)
```

## Provider Features

### Streaming

```python
rlm = RLM.from_openai("gpt-4o")

for chunk in rlm.stream("Tell me a story"):
    print(chunk, end="", flush=True)
```

### Function Calling

```python
from rlm_toolkit.tools import Tool

@Tool(name="get_weather")
def get_weather(city: str) -> str:
    return f"Weather in {city}: 22°C"

rlm = RLM.from_openai("gpt-4o", tools=[get_weather])
result = rlm.run("What's the weather in Tokyo?")
```

### JSON Mode

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(json_mode=True)
rlm = RLM.from_openai("gpt-4o", config=config)

result = rlm.run("List 3 fruits as JSON array")
# {"fruits": ["apple", "banana", "orange"]}
```

### Vision (Multimodal)

```python
rlm = RLM.from_openai("gpt-4o")

result = rlm.run(
    "What's in this image?",
    images=["path/to/image.jpg"]
)
```

## Provider Comparison

| Provider | Speed | Cost | Context | Quality |
|----------|-------|------|---------|---------|
| GPT-4o | ⭐⭐⭐ | $$ | 128K | ⭐⭐⭐⭐⭐ |
| Claude 3.5 | ⭐⭐⭐ | $$ | 200K | ⭐⭐⭐⭐⭐ |
| Gemini Pro | ⭐⭐⭐⭐ | $ | 1M | ⭐⭐⭐⭐ |
| Groq (Llama 3) | ⭐⭐⭐⭐⭐ | $ | 8K | ⭐⭐⭐ |
| Ollama (local) | ⭐⭐ | Free | Varies | ⭐⭐⭐ |

## Custom Providers

Create your own provider:

```python
from rlm_toolkit.providers import BaseProvider
from rlm_toolkit.types import Message, Response

class MyProvider(BaseProvider):
    name = "my_provider"
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
    
    def generate(self, messages: list[Message], **kwargs) -> Response:
        # Your implementation
        response = self._call_api(messages)
        return Response(content=response.text)
    
    def stream(self, messages: list[Message], **kwargs):
        # Streaming implementation
        for chunk in self._stream_api(messages):
            yield chunk.text

# Use custom provider
provider = MyProvider("https://api.example.com", "key")
rlm = RLM(provider=provider)
```

## Environment Variables

| Variable | Provider |
|----------|----------|
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `GOOGLE_API_KEY` | Google AI |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI |
| `COHERE_API_KEY` | Cohere |
| `MISTRAL_API_KEY` | Mistral |
| `TOGETHER_API_KEY` | TogetherAI |
| `GROQ_API_KEY` | Groq |

## Best Practices

!!! tip "Model Selection"
    - Use GPT-4o or Claude 3.5 for complex reasoning
    - Use GPT-4o-mini or Claude 3 Haiku for simple tasks
    - Use local models for privacy-sensitive data

!!! tip "Cost Optimization"
    - Enable caching for repeated queries
    - Use cheaper models for preprocessing
    - Batch similar requests

!!! tip "Fallback Strategy"
    - Configure backup providers for reliability
    - Monitor rate limits and quotas

## Related

- [Tutorial: First Application](../tutorials/01-first-app.md)
- [How-to: Switch Providers](../how-to/providers.md)
- [API Reference: Providers](../api/providers.md)
