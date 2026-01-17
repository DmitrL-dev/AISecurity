# How-to: Configure LLM Providers

Learn how to configure and switch between LLM providers in RLM-Toolkit.

## Quick Reference

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

# Azure OpenAI
rlm = RLM.from_azure_openai(
    deployment_name="gpt-4",
    api_version="2024-02-15-preview"
)
```

## Configure Temperature and Parameters

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

## Use Environment Variables

```bash
# .env file
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

```python
from dotenv import load_dotenv
from rlm_toolkit import RLM

load_dotenv()
rlm = RLM.from_openai("gpt-4o")  # Uses OPENAI_API_KEY
```

## Configure Fallback Providers

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

## Switch Providers at Runtime

```python
rlm = RLM.from_openai("gpt-4o")
response = rlm.run("Hello")

# Switch to Anthropic
rlm.set_provider(RLM.from_anthropic("claude-3-sonnet").provider)
response = rlm.run("Hello again")
```

## Use Streaming

```python
rlm = RLM.from_openai("gpt-4o")

for chunk in rlm.stream("Tell me a story"):
    print(chunk, end="", flush=True)
```

## JSON Mode

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(json_mode=True)
rlm = RLM.from_openai("gpt-4o", config=config)

result = rlm.run("List 3 fruits as JSON")
# {"fruits": ["apple", "banana", "orange"]}
```

## Vision (Multimodal)

```python
rlm = RLM.from_openai("gpt-4o")

result = rlm.run(
    "What's in this image?",
    images=["path/to/image.jpg"]
)
```

## Custom Timeout and Retries

```python
from rlm_toolkit.providers import OpenAIProvider

provider = OpenAIProvider(
    model="gpt-4o",
    timeout=60,
    max_retries=3,
    retry_delay=1.0
)
```

## Related

- [Concept: Providers](../concepts/providers.md)
- [Tutorial: First App](../tutorials/01-first-app.md)
