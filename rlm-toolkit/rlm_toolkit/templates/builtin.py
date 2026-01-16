"""
Builtin Templates
=================

Standard templates for common RLM use cases.
"""

from rlm_toolkit.templates.base import PromptTemplate, get_registry


# =============================================================================
# System Prompts
# =============================================================================

DEFAULT_SYSTEM_PROMPT = """You are an advanced AI assistant with access to a Python REPL.
You can execute code to analyze the provided context and answer questions.

IMPORTANT RULES:
1. Use the REPL to break down complex tasks into smaller steps
2. Store intermediate results in variables
3. When you have the final answer, respond with: FINAL(your answer)
4. Do NOT use dangerous operations (os, subprocess, network access)

Available in your environment:
- `context`: The full document/context to analyze
- `context.slice(start, end)`: Get a portion of the context
- `context.search(query)`: Search for relevant parts
- `llm_query(prompt)`: Query a sub-LLM for semantic analysis

Example workflow:
```python
# Step 1: Analyze structure
parts = context.slice(0, 1000).split('\\n')
print(f"Document has {len(parts)} lines in first 1000 chars")

# Step 2: Search for relevant info
relevant = context.search("important keyword")
print(relevant)

# Step 3: Use sub-LLM for understanding
summary = llm_query(f"Summarize: {relevant}")
print(summary)
```

Then when ready: FINAL(your complete answer)
"""


# =============================================================================
# Task Templates
# =============================================================================

ANALYSIS_TEMPLATE = PromptTemplate(
    name="analysis",
    template="""Analyze the following context and answer the question.

CONTEXT:
{context}

QUESTION:
{query}

Use the Python REPL to break down the analysis into steps.
When you have the answer, respond with FINAL(your answer).
""",
    description="General analysis template for document understanding",
)


SUMMARY_TEMPLATE = PromptTemplate(
    name="summary",
    template="""Summarize the following context in {style} style.

CONTEXT:
{context}

Requirements:
- Maximum {max_length} words
- Focus on key points
- Maintain accuracy

Use the REPL to analyze the document structure, then FINAL(your summary).
""",
    variables=["context", "style", "max_length"],
    description="Document summarization template",
)


QA_TEMPLATE = PromptTemplate(
    name="qa",
    template="""Answer the question based ONLY on the provided context.

CONTEXT:
{context}

QUESTION:
{question}

Instructions:
1. Search the context for relevant information
2. Quote specific passages that support your answer
3. If the answer is not in the context, say "Not found in context"

FINAL(your answer with citations)
""",
    description="Question-answering with citations",
)


CODE_ANALYSIS_TEMPLATE = PromptTemplate(
    name="code_analysis",
    template="""Analyze the following code and {task}.

CODE:
```{language}
{code}
```

Use the REPL to parse and analyze the code structure.
Provide findings in FINAL(your analysis).
""",
    variables=["code", "language", "task"],
    description="Source code analysis template",
)


COMPARISON_TEMPLATE = PromptTemplate(
    name="comparison",
    template="""Compare the following items and provide analysis.

ITEM A:
{item_a}

ITEM B:
{item_b}

Comparison criteria:
{criteria}

Use the REPL to analyze each item, then FINAL(your comparison).
""",
    description="Comparison analysis template",
)


# =============================================================================
# Register builtin templates
# =============================================================================

def _register_builtins():
    """Register all builtin templates."""
    registry = get_registry()
    
    for template in [
        ANALYSIS_TEMPLATE,
        SUMMARY_TEMPLATE,
        QA_TEMPLATE,
        CODE_ANALYSIS_TEMPLATE,
        COMPARISON_TEMPLATE,
    ]:
        registry.register(template)


# Auto-register on import
_register_builtins()
