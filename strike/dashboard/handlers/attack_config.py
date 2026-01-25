"""
SENTINEL Strike Dashboard - Attack Configuration

Centralized attack configuration and validation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class AttackMode(Enum):
    """Attack mode enumeration."""
    WEB = "web"
    LLM = "llm"
    HYBRID = "hybrid"


@dataclass
class AttackConfig:
    """
    Attack configuration container.
    
    Centralizes all attack parameters for cleaner code.
    """
    
    # Target
    target: str = ""
    
    # Mode and vectors
    mode: AttackMode = AttackMode.WEB
    attack_types: List[str] = field(default_factory=lambda: ["sqli", "xss", "lfi"])
    llm_attacks: List[str] = field(default_factory=list)
    
    # Evasion settings
    stealth_mode: str = "aggressive"
    country: str = "auto"
    browser_profile: str = "chrome_win"
    
    # Payload settings
    custom_payload: str = ""
    max_payloads: int = 100
    
    # Concurrency
    threads: int = 10
    delay_ms: int = 0
    
    # Proxy settings
    use_proxy: bool = False
    proxy_url: str = ""
    proxy_type: str = "residential"
    
    # LLM endpoint settings
    llm_endpoint_type: str = "openai"
    llm_endpoint_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    
    # Advanced
    waf_fingerprint: bool = True
    adaptive_bypass: bool = True
    deep_exploit: bool = True
    
    @classmethod
    def from_request(cls, data: Dict) -> "AttackConfig":
        """
        Create config from Flask request data.
        
        Args:
            data: Request JSON data
            
        Returns:
            AttackConfig instance
        """
        mode_str = data.get("mode", "web")
        try:
            mode = AttackMode(mode_str)
        except ValueError:
            mode = AttackMode.WEB
        
        return cls(
            target=data.get("target", ""),
            mode=mode,
            attack_types=data.get("attacks", ["sqli", "xss", "lfi"]),
            llm_attacks=data.get("llm_attacks", []),
            stealth_mode=data.get("stealth_mode", "aggressive"),
            country=data.get("country", "auto"),
            browser_profile=data.get("browser", "chrome_win"),
            custom_payload=data.get("custom_payload", ""),
            max_payloads=int(data.get("max_payloads", 100)),
            threads=int(data.get("threads", 10)),
            delay_ms=int(data.get("delay", 0)),
            use_proxy=data.get("use_proxy", False),
            proxy_url=data.get("proxy_url", ""),
            proxy_type=data.get("proxy_type", "residential"),
            llm_endpoint_type=data.get("llm_endpoint_type", "openai"),
            llm_endpoint_url=data.get("llm_endpoint_url", ""),
            llm_api_key=data.get("llm_api_key", ""),
            llm_model=data.get("llm_model", ""),
            waf_fingerprint=data.get("waf_fingerprint", True),
            adaptive_bypass=data.get("adaptive_bypass", True),
            deep_exploit=data.get("deep_exploit", True),
        )
    
    def validate(self) -> List[str]:
        """
        Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.target:
            errors.append("Target URL is required")
        elif not self.target.startswith(("http://", "https://")):
            errors.append("Target must start with http:// or https://")
        
        if self.mode == AttackMode.WEB and not self.attack_types:
            errors.append("At least one attack type required for web mode")
        
        if self.mode == AttackMode.LLM and not self.llm_attacks:
            errors.append("At least one LLM attack type required for LLM mode")
        
        if self.threads < 1 or self.threads > 100:
            errors.append("Threads must be between 1 and 100")
        
        if self.max_payloads < 1:
            errors.append("Max payloads must be at least 1")
        
        return errors
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            "target": self.target,
            "mode": self.mode.value,
            "attack_types": self.attack_types,
            "llm_attacks": self.llm_attacks,
            "stealth_mode": self.stealth_mode,
            "country": self.country,
            "browser_profile": self.browser_profile,
            "custom_payload": self.custom_payload,
            "max_payloads": self.max_payloads,
            "threads": self.threads,
            "delay_ms": self.delay_ms,
            "use_proxy": self.use_proxy,
            "proxy_type": self.proxy_type,
            "llm_endpoint_type": self.llm_endpoint_type,
            "waf_fingerprint": self.waf_fingerprint,
            "adaptive_bypass": self.adaptive_bypass,
            "deep_exploit": self.deep_exploit,
        }
