# Templates

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Prompt templates** for consistent, reusable prompts

## Quick Start

```python
from rlm_toolkit.templates import PromptTemplate

template = PromptTemplate(
    template="Answer the question: {question}\nContext: {context}",
    input_variables=["question", "context"]
)

prompt = template.format(
    question="What is the capital?",
    context="France is in Europe"
)
```

## Template Types

### PromptTemplate

```python
from rlm_toolkit.templates import PromptTemplate

# Simple template
template = PromptTemplate(
    template="Summarize: {text}",
    input_variables=["text"]
)

# With validation
template = PromptTemplate(
    template="Translate to {language}: {text}",
    input_variables=["language", "text"],
    validate_template=True
)
```

### ChatPromptTemplate

```python
from rlm_toolkit.templates import ChatPromptTemplate, SystemMessage, HumanMessage

template = ChatPromptTemplate.from_messages([
    SystemMessage("You are a helpful assistant"),
    HumanMessage("{user_input}")
])

messages = template.format_messages(user_input="Hello!")
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
    example_template="Input: {input}\nOutput: {output}",
    prefix="Solve math problems:",
    suffix="Input: {question}\nOutput:",
    input_variables=["question"]
)
```

## Built-in Templates

```python
from rlm_toolkit.templates import (
    QA_TEMPLATE,
    SUMMARIZE_TEMPLATE,
    TRANSLATE_TEMPLATE,
    CODE_REVIEW_TEMPLATE,
    EXTRACT_TEMPLATE
)

# Use pre-built templates
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
result = rlm.run(QA_TEMPLATE.format(
    question="What is AI?",
    context="AI is artificial intelligence..."
))
```

## Related

- [Optimize](optimize.md)
- [Agents](agents.md)
