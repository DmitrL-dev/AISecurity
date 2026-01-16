"""
Test Fixtures
=============

Common fixtures and utilities for RLM testing.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from rlm_toolkit.testing.mocks import MockProvider


# Sample contexts for testing
SAMPLE_CONTEXTS = {
    'short': "Hello, world!",
    
    'medium': """
    Document Title: Introduction to RLM
    
    Recursive Language Models (RLM) are a new paradigm for processing 
    extremely long contexts. Unlike traditional approaches that are limited 
    by context windows, RLM uses recursive summarization and code execution
    to process documents of arbitrary length.
    
    Key features:
    1. O(1) memory complexity
    2. Sub-linear token usage
    3. 10x cost reduction
    
    The approach was introduced by Zhang, Kraska, and Khattab in 2024.
    """,
    
    'code': """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Calculate factorial of 5
result = factorial(5)
print(f"Factorial of 5 is {result}")
""",
    
    'json': """
{
    "users": [
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": 25},
        {"id": 3, "name": "Charlie", "age": 35}
    ],
    "total": 3,
    "active": true
}
""",
}


def sample_contexts() -> Dict[str, str]:
    """Get sample contexts for testing."""
    return SAMPLE_CONTEXTS.copy()


def create_test_rlm(
    responses: Optional[List[str]] = None,
    max_iterations: int = 10,
    sandbox: bool = True,
):
    """Create RLM instance with mock provider for testing.
    
    Args:
        responses: Mock responses (default: returns FINAL immediately)
        max_iterations: Max REPL iterations
        sandbox: Enable sandbox
    
    Returns:
        Configured RLM instance
    """
    from rlm_toolkit.core.engine import RLM, RLMConfig
    
    responses = responses or ["FINAL(test answer)"]
    mock = MockProvider(responses=responses)
    
    config = RLMConfig(
        max_iterations=max_iterations,
        sandbox=sandbox,
    )
    
    return RLM(root=mock, config=config)


def create_failing_rlm(error_on_call: int = 1):
    """Create RLM that fails on specified call.
    
    Useful for testing error recovery.
    """
    from rlm_toolkit.core.engine import RLM, RLMConfig
    
    mock = MockProvider(
        responses="FINAL(success)",
        raise_on_call=error_on_call,
    )
    
    return RLM(root=mock, config=RLMConfig())


def create_multi_iteration_rlm(iterations: int = 3):
    """Create RLM that requires multiple iterations.
    
    Useful for testing REPL loop behavior.
    """
    from rlm_toolkit.core.engine import RLM, RLMConfig
    
    # Build response sequence that does work then finishes
    responses = []
    for i in range(iterations - 1):
        responses.append(f"```python\nx = {i}\nprint(x)\n```")
    responses.append("FINAL(completed after iterations)")
    
    mock = MockProvider(responses=responses)
    
    return RLM(root=mock, config=RLMConfig(max_iterations=iterations + 5))


class RLMTestCase:
    """Base class for RLM test cases.
    
    Provides common setup and assertions.
    """
    
    def setup_method(self):
        """Called before each test."""
        self.rlm = create_test_rlm()
    
    def assert_result_success(self, result):
        """Assert RLM result is successful."""
        assert result.status == "success", f"Expected success, got {result.status}"
        assert result.answer is not None, "Expected answer"
    
    def assert_result_has_answer(self, result, expected: str):
        """Assert result contains expected answer."""
        assert result.answer is not None
        assert expected.lower() in result.answer.lower(), \
            f"Expected '{expected}' in '{result.answer}'"
