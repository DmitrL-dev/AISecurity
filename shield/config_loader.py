"""
SENTINEL Shield v2.0 — YAML Configuration Loader

Loads config from YAML file with env-var overrides.
Priority: env vars > YAML file > defaults.

Usage:
    cfg = ShieldConfig.load("config/shield_config.yaml")
    cfg.server.port  # 8080
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("shield.config")

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore
    logger.warning("PyYAML not installed — " "YAML config disabled, using defaults")


# ============================================================
# Config dataclasses
# ============================================================


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    workers: int = 1
    log_level: str = "info"
    request_timeout: float = 30.0


@dataclass
class EngineConfig:
    enabled: bool = True
    weight: float = 1.0
    max_matches_per_category: int = 3


@dataclass
class PipelineConfig:
    block_threshold: float = 0.85
    warn_threshold: float = 0.50
    engines: dict[str, EngineConfig] = field(
        default_factory=lambda: {
            "regex": EngineConfig(
                weight=1.0,
                max_matches_per_category=3,
            ),
            "entropy": EngineConfig(weight=0.7),
            "encoding": EngineConfig(weight=0.8),
            "structural": EngineConfig(weight=0.9),
            "redaction": EngineConfig(weight=0.9),
        }
    )


@dataclass
class GuardConfig:
    enabled: bool = True
    threshold: float = 0.70


@dataclass
class ZoneConfig:
    name: str = "default"
    trust_level: int = 1
    rate_limit: int = 100


@dataclass
class CDNConfigYAML:
    url: str = ""
    check_interval_hours: int = 24
    max_retries: int = 3
    timeout_seconds: int = 30
    max_cached_versions: int = 5


@dataclass
class RateLimitConfig:
    enabled: bool = False
    requests_per_minute: int = 100
    burst: int = 20


@dataclass
class BrainConfig:
    url: str = "http://sentinel-community:8000"
    mode: str = "proxy"
    max_tokens: int = 4096


@dataclass
class PluginConfig:
    enabled: bool = False
    directory: str = "./plugins"


@dataclass
class ShieldConfig:
    """Complete Shield configuration."""

    server: ServerConfig = field(default_factory=ServerConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    guards: dict[str, GuardConfig] = field(
        default_factory=lambda: {
            "llm": GuardConfig(),
            "rag": GuardConfig(),
            "agent": GuardConfig(),
            "tool": GuardConfig(),
            "mcp": GuardConfig(),
            "api": GuardConfig(),
        }
    )
    zones: list[ZoneConfig] = field(
        default_factory=lambda: [
            ZoneConfig("external", 1, 100),
            ZoneConfig("internal", 10, 1000),
            ZoneConfig("dmz", 5, 500),
        ]
    )
    cdn: CDNConfigYAML = field(default_factory=CDNConfigYAML)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    brain: BrainConfig = field(default_factory=BrainConfig)
    plugins: PluginConfig = field(default_factory=PluginConfig)
    api_keys: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "ShieldConfig":
        """
        Load config from YAML file with env overrides.

        Priority: env vars > YAML > defaults.
        """
        cfg = cls()

        # Load YAML if available
        if path and yaml:
            yaml_path = Path(path)
            if yaml_path.exists():
                try:
                    with open(yaml_path) as f:
                        data = yaml.safe_load(f) or {}
                    cfg = cls._from_dict(data)
                    logger.info(f"Config loaded from {yaml_path}")
                except Exception as e:
                    logger.error(f"Config load error: {e}, " f"using defaults")

        # Apply env overrides
        cfg._apply_env_overrides()
        return cfg

    @classmethod
    def _from_dict(cls, data: dict) -> "ShieldConfig":
        """Build config from parsed YAML dict."""
        cfg = cls()

        # Server
        if "server" in data:
            s = data["server"]
            cfg.server = ServerConfig(
                host=s.get("host", "0.0.0.0"),
                port=int(s.get("port", 8080)),
                workers=int(s.get("workers", 1)),
                log_level=s.get("log_level", "info"),
                request_timeout=float(
                    s.get(
                        "request_timeout",
                        30.0,
                    )
                ),
            )

        # Pipeline
        if "pipeline" in data:
            p = data["pipeline"]
            cfg.pipeline.block_threshold = float(p.get("block_threshold", 0.85))
            cfg.pipeline.warn_threshold = float(p.get("warn_threshold", 0.50))
            if "engines" in p:
                for name, ec in p["engines"].items():
                    if isinstance(ec, dict):
                        cfg.pipeline.engines[name] = EngineConfig(
                            enabled=ec.get("enabled", True),
                            weight=float(ec.get("weight", 1.0)),
                            max_matches_per_category=(
                                int(ec.get("max_matches_per_" "category", 3))
                            ),
                        )

        # Guards
        if "guards" in data:
            for gid, gc in data["guards"].items():
                if isinstance(gc, dict):
                    cfg.guards[gid] = GuardConfig(
                        enabled=gc.get("enabled", True),
                        threshold=float(gc.get("threshold", 0.70)),
                    )

        # Zones
        if "zones" in data:
            cfg.zones = [
                ZoneConfig(
                    name=z.get("name", "default"),
                    trust_level=int(z.get("trust_level", 1)),
                    rate_limit=int(z.get("rate_limit", 100)),
                )
                for z in data["zones"]
                if isinstance(z, dict)
            ]

        # CDN
        if "cdn" in data:
            c = data["cdn"]
            cfg.cdn = CDNConfigYAML(
                url=c.get("url", ""),
                check_interval_hours=int(c.get("check_interval_hours", 24)),
                max_retries=int(c.get("max_retries", 3)),
                timeout_seconds=int(c.get("timeout_seconds", 30)),
                max_cached_versions=int(c.get("max_cached_versions", 5)),
            )

        # Rate limit
        if "rate_limit" in data:
            r = data["rate_limit"]
            cfg.rate_limit = RateLimitConfig(
                enabled=bool(r.get("enabled", False)),
                requests_per_minute=int(r.get("requests_per_minute", 100)),
                burst=int(r.get("burst", 20)),
            )

        # Brain
        if "brain" in data:
            b = data["brain"]
            cfg.brain = BrainConfig(
                url=b.get(
                    "url",
                    "http://sentinel-community:8000",
                ),
                mode=b.get("mode", "proxy"),
                max_tokens=int(b.get("max_tokens", 4096)),
            )

        # Plugins
        if "plugins" in data:
            pl = data["plugins"]
            cfg.plugins = PluginConfig(
                enabled=bool(pl.get("enabled", False)),
                directory=pl.get("directory", "./plugins"),
            )

        # API keys
        if "api_keys" in data:
            cfg.api_keys = list(data["api_keys"])

        return cfg

    def _apply_env_overrides(self):
        """Override config from environment."""
        env = os.environ.get

        # Server
        if env("SHIELD_HOST"):
            self.server.host = env("SHIELD_HOST")
        if env("SHIELD_PORT"):
            self.server.port = int(env("SHIELD_PORT"))
        if env("SHIELD_WORKERS"):
            self.server.workers = int(env("SHIELD_WORKERS"))
        if env("SHIELD_LOG_LEVEL"):
            self.server.log_level = env("SHIELD_LOG_LEVEL")

        # Pipeline thresholds
        if env("SHIELD_BLOCK_THRESHOLD"):
            self.pipeline.block_threshold = float(env("SHIELD_BLOCK_THRESHOLD"))
        if env("SHIELD_WARN_THRESHOLD"):
            self.pipeline.warn_threshold = float(env("SHIELD_WARN_THRESHOLD"))

        # CDN
        if env("SHIELD_CDN_URL"):
            self.cdn.url = env("SHIELD_CDN_URL")
        if env("SHIELD_UPDATE_HOURS"):
            self.cdn.check_interval_hours = int(env("SHIELD_UPDATE_HOURS"))

        # Brain
        if env("BRAIN_URL"):
            self.brain.url = env("BRAIN_URL")

        # API keys
        if env("SHIELD_API_KEYS"):
            self.api_keys = [
                k.strip() for k in env("SHIELD_API_KEYS").split(",") if k.strip()
            ]

    def to_dict(self) -> dict:
        """Serialize config to dict."""
        return {
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "workers": self.server.workers,
                "log_level": self.server.log_level,
            },
            "pipeline": {
                "block_threshold": (self.pipeline.block_threshold),
                "warn_threshold": (self.pipeline.warn_threshold),
                "engines": {
                    name: {
                        "enabled": ec.enabled,
                        "weight": ec.weight,
                    }
                    for name, ec in self.pipeline.engines.items()
                },
            },
            "guards": {
                gid: {
                    "enabled": g.enabled,
                    "threshold": g.threshold,
                }
                for gid, g in self.guards.items()
            },
            "cdn": {
                "url": self.cdn.url,
                "interval_h": (self.cdn.check_interval_hours),
            },
            "rate_limit": {
                "enabled": self.rate_limit.enabled,
                "rpm": (self.rate_limit.requests_per_minute),
            },
            "brain": {
                "url": self.brain.url,
                "mode": self.brain.mode,
            },
            "plugins": {
                "enabled": self.plugins.enabled,
                "directory": self.plugins.directory,
            },
        }
