"""
SENTINEL Strike — Configuration Management
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from pathlib import Path
import yaml


class TargetConfig(BaseModel):
    """Target configuration for testing."""
    url: str = Field(..., description="Target API endpoint URL")
    api_key: Optional[str] = Field(
        None, description="API key for authentication")
    model: Optional[str] = Field(None, description="Target model name")
    mode: Literal["external", "internal", "both"] = Field(
        "external", description="Target mode")
    headers: dict[str, str] = Field(
        default_factory=dict, description="Custom headers")
    timeout: int = Field(30, description="Request timeout in seconds")


class ScanConfig(BaseModel):
    """Scan configuration."""
    mode: Literal["quick", "standard", "full", "stealth"] = Field("quick")
    attack_categories: list[str] = Field(default_factory=lambda: ["all"])
    max_concurrent: int = Field(5, description="Max concurrent requests")
    delay_ms: int = Field(100, description="Delay between requests")
    stop_on_critical: bool = Field(
        False, description="Stop on critical finding")


class ReportConfig(BaseModel):
    """Report configuration."""
    format: Literal["html", "json", "pdf", "markdown"] = Field("html")
    output_dir: Path = Field(default_factory=lambda: Path("./reports"))
    include_evidence: bool = Field(True)
    include_remediation: bool = Field(True)
    mitre_atlas_mapping: bool = Field(True)


class StrikeConfig(BaseModel):
    """Main configuration for SENTINEL Strike."""
    target: TargetConfig
    scan: ScanConfig = Field(default_factory=ScanConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)

    @classmethod
    def load(cls, path: Path) -> "StrikeConfig":
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def save(self, path: Path) -> None:
        """Save configuration to YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)

    @classmethod
    def default_path(cls) -> Path:
        """Get default config path."""
        return Path.home() / ".sentinel-strike" / "config.yaml"
