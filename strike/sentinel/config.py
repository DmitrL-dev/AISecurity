"""
SENTINEL Defense Configuration

Usage:
    from sentinel import guard, scan
    
    @guard
    def call_llm(prompt):
        return your_llm_call(prompt)
"""

from sentinel import SENTINEL

sentinel = SENTINEL(
    level="standard",
    targets=["api", "langchain", "rag"],
    model={"filter": "qwen3guard", "deep": "aprielguard", "math": "deepseek-v3"},
)

guard = sentinel.guard
scan = sentinel.scan
