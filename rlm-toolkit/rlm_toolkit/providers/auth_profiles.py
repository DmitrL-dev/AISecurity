"""
Auth Profile Rotation for Multi-Key Provider Management.

Manage multiple API keys per provider with cooldown tracking.
Inspired by OpenClaw's auth-profiles.ts pattern.

Example:
    >>> store = AuthProfileStore()
    >>> store.add_profile(AuthProfile("key1", "openai", "sk-xxx", priority=0))
    >>> store.add_profile(AuthProfile("key2", "openai", "sk-yyy", priority=1))
    >>> profile = store.get_available("openai")
    >>> profile.record_rate_limit(cooldown_seconds=60)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import defaultdict


@dataclass
class AuthProfile:
    """Single API key profile with cooldown tracking.

    Attributes:
        profile_id: Unique identifier for this profile
        provider: Provider name (openai, anthropic, etc.)
        api_key: The actual API key
        priority: Lower value = higher priority (0 is highest)
        cooldown_seconds: Default cooldown duration when rate-limited
    """
    profile_id: str
    provider: str
    api_key: str
    priority: int = 0
    cooldown_seconds: float = 60.0

    # Runtime state (not serialized)
    _in_cooldown: bool = field(default=False, repr=False)
    _cooldown_until: Optional[float] = field(default=None, repr=False)
    _failure_count: int = field(default=0, repr=False)
    _success_count: int = field(default=0, repr=False)
    _last_used: Optional[float] = field(default=None, repr=False)

    def is_available(self) -> bool:
        """Check if profile is available (not in cooldown)."""
        if not self._in_cooldown:
            return True
        if self._cooldown_until and time.time() > self._cooldown_until:
            self._in_cooldown = False
            self._cooldown_until = None
            return True
        return False

    def remaining_cooldown(self) -> float:
        """Get remaining cooldown time in seconds."""
        if not self._in_cooldown or not self._cooldown_until:
            return 0.0
        remaining = self._cooldown_until - time.time()
        return max(0.0, remaining)

    def record_rate_limit(self, cooldown_seconds: Optional[float] = None) -> None:
        """Mark profile as rate-limited.

        Args:
            cooldown_seconds: Override default cooldown duration
        """
        self._in_cooldown = True
        duration = cooldown_seconds or self.cooldown_seconds
        self._cooldown_until = time.time() + duration
        self._failure_count += 1

    def record_success(self) -> None:
        """Record successful API call."""
        self._success_count += 1
        self._last_used = time.time()
        # Reset failure count on success
        self._failure_count = 0

    def record_failure(self) -> None:
        """Record failed API call (non-rate-limit)."""
        self._failure_count += 1
        self._last_used = time.time()

    def reset(self) -> None:
        """Reset all runtime state."""
        self._in_cooldown = False
        self._cooldown_until = None
        self._failure_count = 0
        self._success_count = 0
        self._last_used = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self._success_count + self._failure_count
        if total == 0:
            return 1.0
        return self._success_count / total

    def to_dict(self) -> Dict:
        """Serialize profile (excludes api_key for security)."""
        return {
            "profile_id": self.profile_id,
            "provider": self.provider,
            "priority": self.priority,
            "in_cooldown": self._in_cooldown,
            "remaining_cooldown": self.remaining_cooldown(),
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "success_rate": self.success_rate,
        }


class AuthProfileStore:
    """Manage multiple API keys per provider.

    Supports:
    - Multiple profiles per provider
    - Priority-based selection
    - Automatic cooldown tracking
    - Round-robin fallback within same priority

    Example:
        >>> store = AuthProfileStore()
        >>> store.add_profile(AuthProfile("primary", "openai", "sk-xxx"))
        >>> store.add_profile(AuthProfile("backup", "openai", "sk-yyy", priority=1))
        >>> 
        >>> # Get best available profile
        >>> profile = store.get_available("openai")
        >>> if profile:
        ...     response = call_api(profile.api_key)
        ...     if is_rate_limited(response):
        ...         profile.record_rate_limit()
        ...     else:
        ...         profile.record_success()
    """

    def __init__(self):
        self._profiles: Dict[str, List[AuthProfile]] = defaultdict(list)
        self._round_robin_index: Dict[str, int] = defaultdict(int)

    def add_profile(self, profile: AuthProfile) -> None:
        """Register an auth profile.

        Args:
            profile: AuthProfile to add
        """
        # Check for duplicate profile_id
        existing = self.get_profile(profile.profile_id)
        if existing:
            raise ValueError(f"Profile {profile.profile_id} already exists")

        self._profiles[profile.provider].append(profile)
        # Sort by priority (lower = higher priority)
        self._profiles[profile.provider].sort(key=lambda p: p.priority)

    def remove_profile(self, profile_id: str) -> bool:
        """Remove a profile by ID.

        Returns:
            True if removed, False if not found
        """
        for provider, profiles in self._profiles.items():
            for i, p in enumerate(profiles):
                if p.profile_id == profile_id:
                    del profiles[i]
                    return True
        return False

    def get_profile(self, profile_id: str) -> Optional[AuthProfile]:
        """Get profile by ID."""
        for profiles in self._profiles.values():
            for p in profiles:
                if p.profile_id == profile_id:
                    return p
        return None

    def get_available(self, provider: str) -> Optional[AuthProfile]:
        """Get next available profile for provider.

        Selection logic:
        1. Group by priority
        2. Within same priority, use round-robin
        3. Skip profiles in cooldown

        Args:
            provider: Provider name

        Returns:
            Best available AuthProfile, or None if all in cooldown
        """
        profiles = self._profiles.get(provider, [])
        if not profiles:
            return None

        available = [p for p in profiles if p.is_available()]
        if not available:
            return None

        # Get highest priority (lowest value) among available
        min_priority = min(p.priority for p in available)
        same_priority = [p for p in available if p.priority == min_priority]

        if len(same_priority) == 1:
            return same_priority[0]

        # Round-robin within same priority
        key = f"{provider}:{min_priority}"
        idx = self._round_robin_index[key] % len(same_priority)
        self._round_robin_index[key] = idx + 1

        return same_priority[idx]

    def all_in_cooldown(self, provider: str) -> bool:
        """Check if all profiles for provider are in cooldown.

        Args:
            provider: Provider name

        Returns:
            True if no profiles available
        """
        profiles = self._profiles.get(provider, [])
        if not profiles:
            return False  # No profiles = not in cooldown (just missing)
        return all(not p.is_available() for p in profiles)

    def get_providers(self) -> List[str]:
        """Get list of configured providers."""
        return list(self._profiles.keys())

    def get_profiles_for_provider(self, provider: str) -> List[AuthProfile]:
        """Get all profiles for a provider."""
        return list(self._profiles.get(provider, []))

    def reset_all(self) -> None:
        """Reset all profiles to available state."""
        for profiles in self._profiles.values():
            for p in profiles:
                p.reset()

    def get_stats(self) -> Dict:
        """Get statistics for all profiles."""
        stats = {}
        for provider, profiles in self._profiles.items():
            stats[provider] = {
                "total": len(profiles),
                "available": sum(1 for p in profiles if p.is_available()),
                "in_cooldown": sum(1 for p in profiles if not p.is_available()),
                "profiles": [p.to_dict() for p in profiles],
            }
        return stats
