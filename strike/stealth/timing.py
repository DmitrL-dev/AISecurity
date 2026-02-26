"""
SENTINEL Strike — Timing Engine

Human-like request timing with jitter.
"""

import asyncio
import random
from dataclasses import dataclass


@dataclass
class TimingProfile:
    """Timing configuration."""

    min_delay: float = 0.5  # seconds
    max_delay: float = 3.0
    jitter: float = 0.3  # 30% variance
    burst_limit: int = 10  # requests per minute
    burst_window: float = 60.0  # seconds


class TimingEngine:
    """Human-like request timing."""

    def __init__(self, profile: TimingProfile = None):
        self.profile = profile or TimingProfile()
        self.request_times: list[float] = []

    async def wait(self):
        """Wait with human-like delay."""
        # Check burst limit
        await self._enforce_burst_limit()

        # Calculate delay with jitter
        base_delay = random.uniform(self.profile.min_delay, self.profile.max_delay)
        jitter = random.uniform(-self.profile.jitter, self.profile.jitter)
        delay = base_delay * (1 + jitter)

        await asyncio.sleep(delay)
        self._record_request()

    async def _enforce_burst_limit(self):
        """Wait if approaching burst limit."""
        import time

        now = time.time()
        window_start = now - self.profile.burst_window

        # Count requests in window
        recent = [t for t in self.request_times if t > window_start]
        self.request_times = recent  # Cleanup old

        if len(recent) >= self.profile.burst_limit:
            # Wait until oldest request exits window
            wait_time = recent[0] - window_start + 1
            await asyncio.sleep(wait_time)

    def _record_request(self):
        """Record request timestamp."""
        import time

        self.request_times.append(time.time())

    def set_stealth_level(self, level: int):
        """Adjust timing based on stealth level (1-10)."""
        if level >= 8:
            # Very stealthy - slow
            self.profile.min_delay = 2.0
            self.profile.max_delay = 10.0
            self.profile.burst_limit = 3
        elif level >= 5:
            # Moderate
            self.profile.min_delay = 0.5
            self.profile.max_delay = 3.0
            self.profile.burst_limit = 10
        else:
            # Fast (less stealthy)
            self.profile.min_delay = 0.1
            self.profile.max_delay = 0.5
            self.profile.burst_limit = 30
