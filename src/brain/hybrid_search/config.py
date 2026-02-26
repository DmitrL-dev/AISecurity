"""
Hybrid Search Configuration — YAML-based configuration for the agent.

Part of SENTINEL Hybrid Search Agent.
"""

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class HybridConfig:
    """
    Configuration for the hybrid search agent.

    Combines AIDE ML core parameters with AI-Scientist extensions.
    Can be loaded from YAML or environment variables.
    """

    # ---- AIDE ML Core ----
    num_drafts: int = 5
    """Number of initial solution drafts to generate."""

    debug_prob: float = 0.3
    """Probability of debugging a buggy node vs improving a good one."""

    max_debug_depth: int = 3
    """Maximum consecutive debug attempts before giving up."""

    max_steps: int = 20
    """Maximum number of search steps."""

    # ---- AI-Scientist: Multi-Stage ----
    explore_fraction: float = 0.4
    """Fraction of steps for exploration stage (top-k selection)."""

    exploit_fraction: float = 0.4
    """Fraction of steps for exploitation stage (greedy selection)."""

    polish_fraction: float = 0.2
    """Fraction of steps for polishing stage (best-only selection)."""

    top_k: int = 5
    """Number of top nodes to consider during exploration."""

    # ---- AI-Scientist: VLM ----
    vlm_enabled: bool = False
    """Enable VLM (Vision Language Model) feedback for visual attacks."""

    vlm_model: str = "gpt-4o"
    """VLM model to use for image analysis."""

    vlm_api_key: Optional[str] = None
    """API key for VLM (defaults to OPENAI_API_KEY env var)."""

    # ---- AI-Scientist: Ablation ----
    ablation_enabled: bool = True
    """Enable ablation studies to measure engine contribution."""

    ablation_prob: float = 0.1
    """Probability of running an ablation experiment."""

    # ---- AI-Scientist: Parallel ----
    parallel_workers: int = 4
    """Number of parallel workers for search."""

    # ---- Logging ----
    log_dir: Optional[str] = None
    """Directory for saving journals and logs."""

    verbose: bool = False
    """Enable verbose logging."""

    def __post_init__(self):
        """Apply environment variable overrides."""
        if self.vlm_api_key is None:
            self.vlm_api_key = os.environ.get("OPENAI_API_KEY")

        # Validate fractions sum to 1.0
        total = self.explore_fraction + self.exploit_fraction + self.polish_fraction
        if abs(total - 1.0) > 0.01:
            # Normalize
            self.explore_fraction /= total
            self.exploit_fraction /= total
            self.polish_fraction /= total

    @classmethod
    def from_yaml(cls, path: str | Path) -> "HybridConfig":
        """
        Load configuration from YAML file.

        Args:
            path: Path to YAML config file

        Returns:
            HybridConfig instance
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML required for YAML config. Install with: pip install pyyaml"
            )

        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Handle nested structure (e.g., hybrid_search: ...)
        if "hybrid_search" in data:
            data = data["hybrid_search"]

        return cls(**data)

    @classmethod
    def from_env(cls) -> "HybridConfig":
        """
        Load configuration from environment variables.

        Environment variables are prefixed with HYBRID_SEARCH_.
        Example: HYBRID_SEARCH_NUM_DRAFTS=10

        Returns:
            HybridConfig instance
        """
        config = cls()
        prefix = "HYBRID_SEARCH_"

        for key in [
            "num_drafts",
            "debug_prob",
            "max_debug_depth",
            "max_steps",
            "explore_fraction",
            "exploit_fraction",
            "polish_fraction",
            "top_k",
            "vlm_enabled",
            "vlm_model",
            "ablation_enabled",
            "ablation_prob",
            "parallel_workers",
            "log_dir",
            "verbose",
        ]:
            env_key = f"{prefix}{key.upper()}"
            env_val = os.environ.get(env_key)
            if env_val is not None:
                # Type conversion
                current_val = getattr(config, key)
                if isinstance(current_val, bool):
                    setattr(config, key, env_val.lower() in ("true", "1", "yes"))
                elif isinstance(current_val, int):
                    setattr(config, key, int(env_val))
                elif isinstance(current_val, float):
                    setattr(config, key, float(env_val))
                else:
                    setattr(config, key, env_val)

        return config

    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to YAML file."""
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML required for YAML config. Install with: pip install pyyaml"
            )

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "hybrid_search": {
                "num_drafts": self.num_drafts,
                "debug_prob": self.debug_prob,
                "max_debug_depth": self.max_debug_depth,
                "max_steps": self.max_steps,
                "explore_fraction": self.explore_fraction,
                "exploit_fraction": self.exploit_fraction,
                "polish_fraction": self.polish_fraction,
                "top_k": self.top_k,
                "vlm_enabled": self.vlm_enabled,
                "vlm_model": self.vlm_model,
                "ablation_enabled": self.ablation_enabled,
                "ablation_prob": self.ablation_prob,
                "parallel_workers": self.parallel_workers,
                "verbose": self.verbose,
            }
        }

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
