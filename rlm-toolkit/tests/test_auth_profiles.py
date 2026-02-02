"""
Tests for Auth Profile Rotation.

Tests AuthProfile and AuthProfileStore for multi-key provider management.
"""

import time
import pytest
from rlm_toolkit.providers.auth_profiles import AuthProfile, AuthProfileStore


class TestAuthProfile:
    """Tests for AuthProfile class."""

    def test_create_profile(self):
        """Test basic profile creation."""
        profile = AuthProfile("test", "openai", "sk-xxx")
        assert profile.profile_id == "test"
        assert profile.provider == "openai"
        assert profile.api_key == "sk-xxx"
        assert profile.priority == 0
        assert profile.is_available()

    def test_profile_with_priority(self):
        """Test profile with custom priority."""
        profile = AuthProfile("backup", "openai", "sk-yyy", priority=1)
        assert profile.priority == 1

    def test_record_rate_limit(self):
        """Test rate limit cooldown."""
        profile = AuthProfile("test", "openai", "sk-xxx")
        profile.record_rate_limit(cooldown_seconds=1.0)

        assert not profile.is_available()
        assert profile.remaining_cooldown() > 0

        # Wait for cooldown to expire
        time.sleep(1.1)
        assert profile.is_available()

    def test_record_success(self):
        """Test success recording."""
        profile = AuthProfile("test", "openai", "sk-xxx")
        profile.record_success()

        assert profile._success_count == 1
        assert profile.success_rate == 1.0

    def test_record_failure(self):
        """Test failure recording."""
        profile = AuthProfile("test", "openai", "sk-xxx")
        profile.record_failure()

        assert profile._failure_count == 1
        assert profile.success_rate == 0.0

    def test_success_rate_calculation(self):
        """Test success rate with mixed results."""
        profile = AuthProfile("test", "openai", "sk-xxx")
        profile.record_success()
        profile.record_success()
        profile.record_failure()

        assert profile.success_rate == pytest.approx(0.666, rel=0.01)

    def test_reset(self):
        """Test profile reset."""
        profile = AuthProfile("test", "openai", "sk-xxx")
        profile.record_rate_limit()
        profile.record_failure()

        profile.reset()

        assert profile.is_available()
        assert profile._failure_count == 0

    def test_to_dict(self):
        """Test serialization (excludes api_key)."""
        profile = AuthProfile("test", "openai", "sk-xxx")
        data = profile.to_dict()

        assert "api_key" not in data
        assert data["profile_id"] == "test"
        assert data["provider"] == "openai"


class TestAuthProfileStore:
    """Tests for AuthProfileStore class."""

    def test_add_profile(self):
        """Test adding profiles."""
        store = AuthProfileStore()
        store.add_profile(AuthProfile("p1", "openai", "sk-xxx"))
        store.add_profile(AuthProfile("p2", "openai", "sk-yyy"))

        profiles = store.get_profiles_for_provider("openai")
        assert len(profiles) == 2

    def test_add_duplicate_profile_raises(self):
        """Test duplicate profile ID raises error."""
        store = AuthProfileStore()
        store.add_profile(AuthProfile("p1", "openai", "sk-xxx"))

        with pytest.raises(ValueError, match="already exists"):
            store.add_profile(AuthProfile("p1", "anthropic", "sk-yyy"))

    def test_get_available_priority(self):
        """Test priority-based selection."""
        store = AuthProfileStore()
        store.add_profile(AuthProfile(
            "primary", "openai", "sk-xxx", priority=0))
        store.add_profile(AuthProfile(
            "backup", "openai", "sk-yyy", priority=1))

        profile = store.get_available("openai")
        assert profile.profile_id == "primary"

    def test_get_available_fallback_on_cooldown(self):
        """Test fallback to lower priority when primary in cooldown."""
        store = AuthProfileStore()
        primary = AuthProfile("primary", "openai", "sk-xxx", priority=0)
        backup = AuthProfile("backup", "openai", "sk-yyy", priority=1)
        store.add_profile(primary)
        store.add_profile(backup)

        primary.record_rate_limit(cooldown_seconds=60)

        profile = store.get_available("openai")
        assert profile.profile_id == "backup"

    def test_get_available_round_robin_same_priority(self):
        """Test round-robin for same priority profiles."""
        store = AuthProfileStore()
        store.add_profile(AuthProfile("p1", "openai", "sk-1", priority=0))
        store.add_profile(AuthProfile("p2", "openai", "sk-2", priority=0))

        # Should round-robin
        first = store.get_available("openai")
        second = store.get_available("openai")

        assert first.profile_id != second.profile_id

    def test_all_in_cooldown(self):
        """Test all_in_cooldown check."""
        store = AuthProfileStore()
        p1 = AuthProfile("p1", "openai", "sk-xxx")
        p2 = AuthProfile("p2", "openai", "sk-yyy")
        store.add_profile(p1)
        store.add_profile(p2)

        assert not store.all_in_cooldown("openai")

        p1.record_rate_limit()
        assert not store.all_in_cooldown("openai")

        p2.record_rate_limit()
        assert store.all_in_cooldown("openai")

    def test_all_in_cooldown_empty_provider(self):
        """Test all_in_cooldown for unknown provider."""
        store = AuthProfileStore()
        # No profiles = not in cooldown (just missing)
        assert not store.all_in_cooldown("unknown")

    def test_remove_profile(self):
        """Test profile removal."""
        store = AuthProfileStore()
        store.add_profile(AuthProfile("p1", "openai", "sk-xxx"))

        assert store.remove_profile("p1")
        assert not store.remove_profile("unknown")
        assert len(store.get_profiles_for_provider("openai")) == 0

    def test_get_providers(self):
        """Test getting list of providers."""
        store = AuthProfileStore()
        store.add_profile(AuthProfile("p1", "openai", "sk-xxx"))
        store.add_profile(AuthProfile("p2", "anthropic", "sk-yyy"))

        providers = store.get_providers()
        assert "openai" in providers
        assert "anthropic" in providers

    def test_reset_all(self):
        """Test resetting all profiles."""
        store = AuthProfileStore()
        p1 = AuthProfile("p1", "openai", "sk-xxx")
        p2 = AuthProfile("p2", "anthropic", "sk-yyy")
        store.add_profile(p1)
        store.add_profile(p2)

        p1.record_rate_limit()
        p2.record_rate_limit()

        store.reset_all()

        assert p1.is_available()
        assert p2.is_available()

    def test_get_stats(self):
        """Test statistics gathering."""
        store = AuthProfileStore()
        store.add_profile(AuthProfile("p1", "openai", "sk-xxx"))

        stats = store.get_stats()
        assert "openai" in stats
        assert stats["openai"]["total"] == 1


class TestModelRotatorAuthIntegration:
    """Tests for ModelRotator with AuthProfileStore."""

    def test_rotator_with_auth_store(self):
        """Test rotator uses auth store for filtering."""
        from rlm_toolkit.providers.rotation import ModelRotator, ModelConfig

        store = AuthProfileStore()
        store.add_profile(AuthProfile("p1", "openai", "sk-xxx"))

        rotator = ModelRotator(
            models=[ModelConfig(model="gpt-4", provider="openai")],
            auth_store=store,
        )

        model = rotator.next()
        assert model.model == "gpt-4"

    def test_rotator_skips_cooldown_provider(self):
        """Test rotator skips models when all auth keys in cooldown."""
        from rlm_toolkit.providers.rotation import ModelRotator, ModelConfig

        store = AuthProfileStore()
        p1 = AuthProfile("p1", "openai", "sk-xxx")
        store.add_profile(p1)
        store.add_profile(AuthProfile("p2", "anthropic", "sk-yyy"))

        rotator = ModelRotator(
            models=[
                ModelConfig(model="gpt-4", provider="openai", priority=0),
                ModelConfig(model="claude-3",
                            provider="anthropic", priority=1),
            ],
            strategy="priority",
            auth_store=store,
        )

        # Put openai in cooldown
        p1.record_rate_limit(cooldown_seconds=60)

        # Should skip openai and use anthropic
        model = rotator.next()
        assert model.model == "claude-3"

    def test_get_api_key(self):
        """Test getting API key for model."""
        from rlm_toolkit.providers.rotation import ModelRotator, ModelConfig

        store = AuthProfileStore()
        store.add_profile(AuthProfile("p1", "openai", "sk-test-key"))

        rotator = ModelRotator(
            models=[ModelConfig(model="gpt-4", provider="openai")],
            auth_store=store,
        )

        model = rotator.next()
        api_key = rotator.get_api_key(model)

        assert api_key == "sk-test-key"

    def test_get_api_key_no_store(self):
        """Test get_api_key without auth store returns None."""
        from rlm_toolkit.providers.rotation import ModelRotator, ModelConfig

        rotator = ModelRotator(
            models=[ModelConfig(model="gpt-4", provider="openai")],
        )

        model = rotator.next()
        assert rotator.get_api_key(model) is None
