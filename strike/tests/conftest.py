"""
SENTINEL Strike - Test Configuration

Pytest fixtures and configuration for Strike tests.
"""

import asyncio
import pytest
from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock


# ============================================================================
# Mock Target
# ============================================================================

@dataclass
class MockResponse:
    """Mock response from target."""
    text: str
    status: int = 200
    headers: dict = None
    
    def __post_init__(self):
        self.headers = self.headers or {}


class MockTarget:
    """Mock target for testing attacks."""
    
    def __init__(
        self,
        responses: List[str] = None,
        blocked_words: List[str] = None,
        defense_type: str = "none",
    ):
        self.responses = responses or ["I cannot help with that."]
        self.blocked_words = blocked_words or ["password", "secret"]
        self.defense_type = defense_type
        self.request_count = 0
        self.requests: List[str] = []
    
    async def send(self, payload: str) -> str:
        """Send payload and get response."""
        self.requests.append(payload)
        self.request_count += 1
        
        # Check for blocked words
        payload_lower = payload.lower()
        for word in self.blocked_words:
            if word in payload_lower:
                return f"Sorry, I cannot discuss '{word}'."
        
        # Return cycling response
        idx = (self.request_count - 1) % len(self.responses)
        return self.responses[idx]
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass


class MockGandalfTarget(MockTarget):
    """Mock Gandalf target with level-specific responses."""
    
    def __init__(self, level: int = 1):
        self.level = level
        self.password = f"SECRET{level}"
        super().__init__(
            responses=[
                "I cannot reveal the password.",
                f"The password is {self.password}",
            ],
            blocked_words=["password"] if level > 3 else [],
        )


class MockCrucibleTarget(MockTarget):
    """Mock Crucible CTF target."""
    
    def __init__(self, challenge: str = "pieceofcake"):
        self.challenge = challenge
        self.flag = f"gAAAAA{challenge[:8].upper()}"
        super().__init__(
            responses=[
                "Try harder!",
                f"Congratulations! The flag is: {self.flag}",
            ],
        )


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_target():
    """Create a mock target."""
    return MockTarget()


@pytest.fixture
def mock_gandalf():
    """Create mock Gandalf target."""
    return MockGandalfTarget(level=1)


@pytest.fixture
def mock_crucible():
    """Create mock Crucible target."""
    return MockCrucibleTarget()


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Test Helpers
# ============================================================================

def create_mock_response(text: str, status: int = 200) -> MockResponse:
    """Create mock HTTP response."""
    return MockResponse(text=text, status=status)


async def run_attack_test(target, payloads: List[str]) -> List[str]:
    """Run payloads against target and collect responses."""
    responses = []
    for payload in payloads:
        response = await target.send(payload)
        responses.append(response)
    return responses
