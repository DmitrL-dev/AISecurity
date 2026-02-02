"""
Engine Registry — Auto-discovery and Profile Management

Provides:
- Auto-discovery of all BaseEngine subclasses
- Profile system (lite/standard/enterprise)
- Hardware auto-detection for profile selection

Usage:
    registry = EngineRegistry()
    engines = registry.get_engines_for_profile()
"""

import os
import logging
import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Type, Any
from enum import Enum

logger = logging.getLogger("EngineRegistry")


class Profile(Enum):
    """Engine profiles for different hardware/latency requirements."""

    LITE = "lite"  # 10 engines, <50ms, minimal hardware
    STANDARD = "standard"  # 30 engines, <200ms, CPU only
    ENTERPRISE = "enterprise"  # 100+ engines, <500ms, GPU optional


@dataclass
class EngineMetadata:
    """Metadata for a registered engine."""

    name: str
    module_path: str
    class_name: str
    tier: int = 1  # 0=instant, 1=fast, 2=heavy, 3=optional
    profiles: Set[Profile] = field(default_factory=lambda: {Profile.ENTERPRISE})
    requires_gpu: bool = False
    requires_model: bool = False  # Heavy ML model needed
    estimated_latency_ms: float = 50.0

    def __hash__(self):
        return hash(self.name)


# ============================================================================
# Profile Definitions
# ============================================================================

# Core engines that ALWAYS run (Tier 0)
TIER0_ENGINES = {
    "injection",
    "yara_engine",
}

# Fast engines for lite profile (< 50ms total)
LITE_ENGINES = TIER0_ENGINES | {
    "language",
    "query",
    "behavioral",
    "learning",
    "inverted",
}

# Standard profile engines (< 200ms total)
STANDARD_ENGINES = LITE_ENGINES | {
    "pii",
    "canary_tokens",
    "info_theory",
    "chaos_theory",
    "knowledge",
    "rule_dsl",
    "semantic_detector",
    "prompt_guard",
}

# Enterprise profile adds ML-heavy engines
ENTERPRISE_ENGINES = STANDARD_ENGINES | {
    "qwen_guard",
    "geometric",
    "tda_enhanced",
    "hyperbolic_geometry",
    "sheaf_coherence",
    "adversarial_resistance",
    "rag_poisoning_detector",
    "tool_hijacker_detector",
    "agent_anomaly",
    "mcp_a2a_security",
    # ... all other engines
}

PROFILE_ENGINES = {
    Profile.LITE: LITE_ENGINES,
    Profile.STANDARD: STANDARD_ENGINES,
    Profile.ENTERPRISE: ENTERPRISE_ENGINES,
}


class EngineRegistry:
    """
    Central registry for all detection engines.

    Supports:
    - Auto-discovery of engines from engines/ directory
    - Profile-based engine selection
    - Hardware auto-detection
    """

    def __init__(self, engines_package: str = "engines"):
        self._engines_package = engines_package
        self._registry: Dict[str, EngineMetadata] = {}
        self._instances: Dict[str, Any] = {}  # Lazy-loaded instances
        self._disabled_engines: Set[str] = set()  # Manually disabled engines
        self._enabled_engines: Set[str] = set()  # Manually enabled (outside profile)
        self._profile = self._detect_profile()

        logger.info(f"EngineRegistry initialized (profile={self._profile.value})")

    @property
    def profile(self) -> Profile:
        """Current active profile."""
        return self._profile

    @profile.setter
    def profile(self, value: Profile):
        """Set profile and clear cached instances."""
        if value != self._profile:
            self._profile = value
            self._instances.clear()
            logger.info(f"Profile changed to: {value.value}")

    def _detect_profile(self) -> Profile:
        """
        Auto-detect profile based on environment and hardware.

        Priority:
        1. SENTINEL_PROFILE env var
        2. Hardware detection (GPU, CPU cores)
        3. Default to STANDARD
        """
        # 1. Check environment variable
        env_profile = os.getenv("SENTINEL_PROFILE", "").lower()
        if env_profile:
            try:
                return Profile(env_profile)
            except ValueError:
                logger.warning(f"Unknown profile '{env_profile}', using auto-detect")

        # 2. Hardware detection
        try:
            import torch

            if torch.cuda.is_available():
                logger.info("GPU detected → enterprise profile")
                return Profile.ENTERPRISE
        except ImportError:
            pass

        try:
            import psutil

            cpu_count = psutil.cpu_count(logical=False)
            if cpu_count and cpu_count >= 8:
                logger.info(f"{cpu_count} CPU cores → standard profile")
                return Profile.STANDARD
            elif cpu_count and cpu_count < 4:
                logger.info(f"{cpu_count} CPU cores → lite profile")
                return Profile.LITE
        except ImportError:
            pass

        # 3. Default
        return Profile.STANDARD

    def discover_engines(self) -> int:
        """
        Auto-discover all engine modules.

        Scans engines/ directory for Python files and registers
        any classes that inherit from BaseEngine.

        Returns:
            Number of engines discovered
        """
        try:
            engines_module = importlib.import_module(self._engines_package)
            engines_path = engines_module.__path__
        except ImportError:
            logger.error(f"Cannot import {self._engines_package}")
            return 0

        discovered = 0

        for _, module_name, is_pkg in pkgutil.iter_modules(engines_path):
            if is_pkg or module_name.startswith("_"):
                continue

            # Determine profile based on engine name
            profiles = {Profile.ENTERPRISE}  # Default
            if module_name in LITE_ENGINES:
                profiles = {Profile.LITE, Profile.STANDARD, Profile.ENTERPRISE}
            elif module_name in STANDARD_ENGINES:
                profiles = {Profile.STANDARD, Profile.ENTERPRISE}

            # Determine tier
            tier = 2  # Default to heavy
            if module_name in TIER0_ENGINES:
                tier = 0
            elif module_name in LITE_ENGINES:
                tier = 1

            metadata = EngineMetadata(
                name=module_name,
                module_path=f"{self._engines_package}.{module_name}",
                class_name=self._infer_class_name(module_name),
                tier=tier,
                profiles=profiles,
            )

            self._registry[module_name] = metadata
            discovered += 1

        logger.info(f"Discovered {discovered} engines")
        return discovered

    def _infer_class_name(self, module_name: str) -> str:
        """Infer class name from module name (snake_case → PascalCase)."""
        parts = module_name.split("_")
        return "".join(part.capitalize() for part in parts)

    def get_engines_for_profile(self, profile: Optional[Profile] = None) -> List[str]:
        """
        Get list of engine names for the specified profile.

        Args:
            profile: Profile to use (default: current profile)

        Returns:
            List of engine names
        """
        profile = profile or self._profile
        profile_set = PROFILE_ENGINES.get(profile, STANDARD_ENGINES)

        return [
            name
            for name, meta in self._registry.items()
            if (
                (name in profile_set or profile in meta.profiles)
                or name in self._enabled_engines  # Manually enabled
            )
            and name not in self._disabled_engines
        ]

    def get_engine_instance(self, name: str) -> Optional[Any]:
        """
        Get or create an engine instance.

        Args:
            name: Engine name

        Returns:
            Engine instance or None if not found/failed
        """
        if name in self._instances:
            return self._instances[name]

        if name not in self._registry:
            logger.warning(f"Engine '{name}' not in registry")
            return None

        meta = self._registry[name]

        try:
            module = importlib.import_module(meta.module_path)
            engine_class = getattr(module, meta.class_name, None)

            if engine_class is None:
                # Try common alternatives
                for cls_name in [
                    meta.class_name,
                    f"{meta.class_name}Engine",
                    f"{meta.class_name}Detector",
                ]:
                    engine_class = getattr(module, cls_name, None)
                    if engine_class:
                        break

            if engine_class:
                instance = engine_class()
                self._instances[name] = instance
                return instance
            else:
                logger.warning(f"Cannot find class in {meta.module_path}")
                return None

        except Exception as e:
            logger.error(f"Failed to load engine '{name}': {e}")
            return None

    def get_tiered_engines(
        self, profile: Optional[Profile] = None
    ) -> Dict[int, List[str]]:
        """
        Get engines grouped by tier for parallel execution.

        Returns:
            Dict mapping tier number to list of engine names
        """
        profile = profile or self._profile
        engines = self.get_engines_for_profile(profile)

        tiered: Dict[int, List[str]] = {0: [], 1: [], 2: [], 3: []}

        for name in engines:
            if name in self._registry:
                tier = self._registry[name].tier
                tiered[tier].append(name)

        return tiered

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_registered": len(self._registry),
            "loaded_instances": len(self._instances),
            "current_profile": self._profile.value,
            "profile_engines": len(self.get_engines_for_profile()),
            "disabled_engines": list(self._disabled_engines),
            "by_tier": {
                tier: len(engines)
                for tier, engines in self.get_tiered_engines().items()
            },
        }

    def enable_engine(self, name: str) -> bool:
        """
        Enable an engine (adds to active list even if not in profile).

        Args:
            name: Engine name

        Returns:
            True if engine was enabled
        """
        if name not in self._registry:
            logger.warning(f"Cannot enable unknown engine: {name}")
            return False

        # Remove from disabled if present
        self._disabled_engines.discard(name)
        # Add to manually enabled
        self._enabled_engines.add(name)
        logger.info(f"Engine enabled: {name}")
        return True

    def disable_engine(self, name: str) -> bool:
        """
        Disable an engine (removes from active list).

        Args:
            name: Engine name

        Returns:
            True if engine was disabled
        """
        if name not in self._registry:
            logger.warning(f"Cannot disable unknown engine: {name}")
            return False

        self._disabled_engines.add(name)
        self._enabled_engines.discard(name)  # Remove from manual enable
        # Clear cached instance
        self._instances.pop(name, None)
        logger.info(f"Engine disabled: {name}")
        return True

    def get_disabled_engines(self) -> List[str]:
        """Get list of manually disabled engines."""
        return list(self._disabled_engines)

    def is_engine_enabled(self, name: str) -> bool:
        """Check if engine is enabled."""
        return name not in self._disabled_engines


# ============================================================================
# Global Registry Instance
# ============================================================================

_default_registry: Optional[EngineRegistry] = None


def get_registry() -> EngineRegistry:
    """Get or create the global engine registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = EngineRegistry()
        _default_registry.discover_engines()
    return _default_registry


def get_profile() -> Profile:
    """Get current profile."""
    return get_registry().profile


def set_profile(profile: Profile):
    """Set current profile."""
    get_registry().profile = profile
