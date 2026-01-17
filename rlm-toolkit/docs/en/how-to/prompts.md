# How-to: Prompt Engineering

Recipes for effective prompt design.

## System Prompts

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

rlm.set_system_prompt("""
You are a helpful Python programming assistant.
Always provide working code examples.
Format code with proper indentation.
""")

response = rlm.run("How do I read a JSON file?")
```

## Prompt Templates

```python
from rlm_toolkit.prompts import PromptTemplate

template = PromptTemplate("""
Analyze the following {document_type}:

{content}

Provide:
1. Summary
2. Key points
3. Recommendations
""")

prompt = template.format(
    document_type="contract",
    content="..."
)
```

## Chat Prompt Templates

```python
from rlm_toolkit.prompts import ChatPromptTemplate

template = ChatPromptTemplate.from_messages([
    ("system", "You are a {role}"),
    ("human", "{question}")
])

messages = template.format(
    role="Python expert",
    question="What is a decorator?"
)
```

## Few-Shot Prompting

```python
from rlm_toolkit.prompts import FewShotPromptTemplate

examples = [
    {"input": "happy", "output": "sad"},
    {"input": "big", "output": "small"},
    {"input": "fast", "output": "slow"}
]

template = FewShotPromptTemplate(
    examples=examples,
    prefix="Give the opposite of each word:",
    suffix="Input: {input}\nOutput:",
    example_prompt="Input: {input}\nOutput: {output}"
)

prompt = template.format(input="hot")
```

## Chain-of-Thought

```python
rlm = RLM.from_openai("gpt-4o")

response = rlm.run("""
Solve this step by step:

A store has 25 apples. They sell 12 and receive 8 more.
How many apples are there now?

Think through each step:
""")
```

## Output Formatting

```python
from rlm_toolkit import RLM, RLMConfig

# JSON mode
config = RLMConfig(json_mode=True)
rlm = RLM.from_openai("gpt-4o", config=config)

response = rlm.run("""
Extract person info as JSON:
"John Smith is 30 years old"

Format: {"name": str, "age": int}
""")
```

## Structured Output

```python
from pydantic import BaseModel
from rlm_toolkit import RLM

class Person(BaseModel):
    name: str
    age: int
    city: str

rlm = RLM.from_openai("gpt-4o")
person = rlm.run_structured(
    "Extract: John, 30, lives in Tokyo",
    output_schema=Person
)
print(person.name)  # "John"
```

## Role-Based Prompts

```python
roles = {
    "expert": "You are a senior Python developer with 20 years experience.",
    "teacher": "You are a patient teacher explaining to beginners.",
    "critic": "You are a code reviewer looking for bugs and improvements."
}

rlm.set_system_prompt(roles["expert"])
```

## Context Injection

```python
from rlm_toolkit.prompts import PromptTemplate

template = PromptTemplate("""
Context: {context}

Based on the above context, answer: {question}

If the context doesn't contain the answer, say "I don't know".
""")
```

## Related

- [How-to: Providers](./providers.md)
- [Tutorial: First App](../tutorials/01-first-app.md)
