"""Test fixtures and utilities for RLM-Toolkit test suite."""

import pytest
from typing import Generator

from rlm_toolkit.testing.mocks import MockProvider, SequenceProvider
from rlm_toolkit.testing.fixtures import sample_contexts


@pytest.fixture
def mock_provider() -> MockProvider:
    """Basic mock provider returning FINAL immediately."""
    return MockProvider(responses="FINAL(test answer)")


@pytest.fixture
def sequence_provider() -> SequenceProvider:
    """Provider that goes through iteration before FINAL."""
    return SequenceProvider(
        "```python\nx = 1 + 1\nprint(x)\n```",
        "```python\ny = x * 2\nprint(y)\n```",
        "FINAL(completed)",
    )


@pytest.fixture
def failing_provider() -> MockProvider:
    """Provider that fails on first call."""
    return MockProvider(
        responses="FINAL(success)",
        raise_on_call=1,
    )


@pytest.fixture
def sample_context_short() -> str:
    """Short sample context."""
    return sample_contexts()["short"]


@pytest.fixture
def sample_context_medium() -> str:
    """Medium sample context."""
    return sample_contexts()["medium"]


@pytest.fixture
def sample_context_code() -> str:
    """Code sample context."""
    return sample_contexts()["code"]


@pytest.fixture
def sample_context_json() -> str:
    """JSON sample context."""
    return sample_contexts()["json"]
