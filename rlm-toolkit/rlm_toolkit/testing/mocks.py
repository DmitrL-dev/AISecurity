"""
Mock Providers
==============

Mock LLM providers for testing without API calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from rlm_toolkit.providers.base import LLMProvider, LLMResponse


@dataclass
class MockResponse:
    """Predefined mock response."""
    content: str
    tokens_in: int = 100
    tokens_out: int = 50
    cost: float = 0.001


class MockProvider(LLMProvider):
    """Mock provider for testing.
    
    Can be configured with:
    - Fixed responses
    - Sequence of responses
    - Dynamic response function
    
    Example:
        >>> mock = MockProvider(responses=["Answer 1", "FINAL(done)"])
        >>> response = mock.generate([{"role": "user", "content": "test"}])
        >>> print(response.content)
        Answer 1
    """
    
    def __init__(
        self,
        responses: Optional[Union[str, List[str], Callable]] = None,
        model: str = "mock-model",
        raise_on_call: Optional[int] = None,
        error_type: type = RuntimeError,
    ):
        """Initialize mock provider.
        
        Args:
            responses: Fixed response(s) or callable
            model: Mock model name
            raise_on_call: Raise error on Nth call (1-indexed)
            error_type: Type of error to raise
        """
        self._responses = responses or "FINAL(mock response)"
        self._model = model
        self._call_count = 0
        self._raise_on_call = raise_on_call
        self._error_type = error_type
        self._history: List[Dict] = []
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @property
    def max_context(self) -> int:
        return 128000
    
    @property
    def call_count(self) -> int:
        return self._call_count
    
    @property
    def history(self) -> List[Dict]:
        """All calls made to this provider."""
        return self._history
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        self._call_count += 1
        
        # Record call
        self._history.append({
            'call_number': self._call_count,
            'prompt': prompt,
            'system_prompt': system_prompt,
            'kwargs': kwargs,
        })
        
        # Raise error if configured
        if self._raise_on_call and self._call_count == self._raise_on_call:
            raise self._error_type(f"Mock error on call {self._call_count}")
        
        # Get response
        if callable(self._responses):
            content = self._responses(prompt, self._call_count)
        elif isinstance(self._responses, list):
            idx = min(self._call_count - 1, len(self._responses) - 1)
            content = self._responses[idx]
        else:
            content = self._responses
        
        return LLMResponse(
            content=content,
            tokens_in=100,
            tokens_out=len(content) // 4,
            model=self._model,
        )
    
    def reset(self) -> None:
        """Reset call count and history."""
        self._call_count = 0
        self._history.clear()


class RecordingProvider(LLMProvider):
    """Wrapper that records all calls to an underlying provider.
    
    Useful for debugging and test verification.
    
    Example:
        >>> real_provider = OllamaProvider("llama4")
        >>> recording = RecordingProvider(real_provider)
        >>> # ... use recording as provider ...
        >>> print(recording.calls)  # See all calls
    """
    
    def __init__(self, inner: LLMProvider):
        """Initialize.
        
        Args:
            inner: Provider to wrap
        """
        self._inner = inner
        self._calls: List[Dict] = []
    
    @property
    def model_name(self) -> str:
        return self._inner.model_name
    
    @property
    def max_context(self) -> int:
        return self._inner.max_context
    
    @property
    def calls(self) -> List[Dict]:
        """All recorded calls."""
        return self._calls
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        import time
        # Record input
        call_record = {
            'prompt': prompt,
            'system_prompt': system_prompt,
            'kwargs': kwargs.copy(),
            'timestamp': time.time(),
        }
        
        # Call inner provider
        start = time.time()
        try:
            response = self._inner.generate(prompt, system_prompt, max_tokens, temperature, **kwargs)
            call_record['response'] = response.content
            call_record['success'] = True
            call_record['duration'] = time.time() - start
            return response
        except Exception as e:
            call_record['error'] = str(e)
            call_record['success'] = False
            call_record['duration'] = time.time() - start
            raise
        finally:
            self._calls.append(call_record)
    
    def clear(self) -> None:
        """Clear recorded calls."""
        self._calls.clear()


class SequenceProvider(MockProvider):
    """Provider with predefined response sequence.
    
    Convenience wrapper around MockProvider for test scenarios.
    """
    
    def __init__(self, *responses: str, cycle: bool = False):
        """Initialize.
        
        Args:
            *responses: Sequence of responses
            cycle: If True, cycle through responses indefinitely
        """
        self._cycle = cycle
        super().__init__(responses=list(responses))
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        self._call_count += 1
        
        responses = self._responses
        if self._cycle:
            idx = (self._call_count - 1) % len(responses)
        else:
            idx = min(self._call_count - 1, len(responses) - 1)
        
        content = responses[idx]
        
        return LLMResponse(
            content=content,
            tokens_in=100,
            tokens_out=len(content) // 4,
            model="sequence-mock",
        )

