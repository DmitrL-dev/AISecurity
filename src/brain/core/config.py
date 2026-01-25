"""
Configuration Validator for Sentinel

Validates environment variables and configuration files at startup.
Prevents runtime errors from missing or invalid configuration.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

logger = logging.getLogger("ConfigValidator")


@dataclass
class ValidationError:
    """Single validation error."""
    key: str
    message: str
    severity: str = "error"  # error, warning


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    def add_error(self, key: str, message: str):
        self.errors.append(ValidationError(key, message, "error"))
        self.valid = False

    def add_warning(self, key: str, message: str):
        self.warnings.append(ValidationError(key, message, "warning"))


class ConfigValidator:
    """
    Validates Sentinel configuration from environment variables.

    Usage:
        validator = ConfigValidator()
        result = validator.validate()
        if not result.valid:
            for error in result.errors:
                print(f"ERROR: {error.key}: {error.message}")
    """

    # Required environment variables
    REQUIRED_VARS = [
        ("REDIS_URL", "Redis connection URL"),
    ]

    # Optional with defaults
    OPTIONAL_VARS = {
        "QWEN_GUARD_ENABLED": "true",
        "TLS_ENABLED": "false",
        "VAULT_ENABLED": "false",
        "LANGUAGE_MODE": "WHITELIST",
        "GPU_AUTO_DETECT": "true",
    }

    # Boolean vars that should be true/false
    BOOLEAN_VARS = [
        "QWEN_GUARD_ENABLED",
        "TLS_ENABLED",
        "VAULT_ENABLED",
        "GPU_AUTO_DETECT",
    ]

    def validate(self) -> ValidationResult:
        """Run all validation checks."""
        result = ValidationResult(valid=True)

        self._validate_required(result)
        self._validate_booleans(result)
        self._validate_tls(result)
        self._validate_vault(result)
        self._validate_redis(result)

        # Log results
        if result.valid:
            logger.info("Configuration validation passed")
        else:
            for error in result.errors:
                logger.error(f"Config error: {error.key}: {error.message}")

        for warning in result.warnings:
            logger.warning(f"Config warning: {warning.key}: {warning.message}")

        return result

    def _validate_required(self, result: ValidationResult):
        """Check required environment variables."""
        for var, description in self.REQUIRED_VARS:
            if not os.getenv(var):
                result.add_error(var, f"Required: {description}")

    def _validate_booleans(self, result: ValidationResult):
        """Check boolean vars have valid values."""
        valid_values = {"true", "false", "1", "0", "yes", "no"}
        for var in self.BOOLEAN_VARS:
            value = os.getenv(var, "").lower()
            if value and value not in valid_values:
                result.add_error(var, f"Invalid boolean: '{value}'")

    def _validate_tls(self, result: ValidationResult):
        """Check TLS configuration consistency."""
        if os.getenv("TLS_ENABLED", "false").lower() == "true":
            required = ["TLS_CERT_PATH", "TLS_KEY_PATH", "TLS_CA_PATH"]
            for var in required:
                path = os.getenv(var)
                if not path:
                    result.add_error(var, "Required when TLS_ENABLED=true")
                elif not os.path.exists(path):
                    result.add_warning(var, f"File not found: {path}")

    def _validate_vault(self, result: ValidationResult):
        """Check Vault configuration."""
        if os.getenv("VAULT_ENABLED", "false").lower() == "true":
            if not os.getenv("VAULT_ADDR"):
                result.add_error(
                    "VAULT_ADDR", "Required when VAULT_ENABLED=true")
            if not os.getenv("VAULT_TOKEN"):
                result.add_warning(
                    "VAULT_TOKEN", "Not set, will try AppRole auth")

    def _validate_redis(self, result: ValidationResult):
        """Validate Redis URL format."""
        redis_url = os.getenv("REDIS_URL", "")
        if redis_url and not redis_url.startswith("redis://"):
            result.add_error("REDIS_URL", "Must start with redis://")

    def get_config_summary(self) -> Dict[str, Any]:
        """Return current configuration summary (safe, no secrets)."""
        return {
            "qwen_guard_enabled": os.getenv("QWEN_GUARD_ENABLED", "true"),
            "tls_enabled": os.getenv("TLS_ENABLED", "false"),
            "vault_enabled": os.getenv("VAULT_ENABLED", "false"),
            "language_mode": os.getenv("LANGUAGE_MODE", "WHITELIST"),
            "gpu_auto_detect": os.getenv("GPU_AUTO_DETECT", "true"),
            "redis_configured": bool(os.getenv("REDIS_URL")),
        }


def validate_config() -> ValidationResult:
    """Convenience function to validate configuration."""
    return ConfigValidator().validate()


if __name__ == "__main__":
    # Run validation as script
    logging.basicConfig(level=logging.INFO)
    result = validate_config()

    print("\n=== Configuration Validation ===")
    print(f"Valid: {result.valid}")

    if result.errors:
        print("\nErrors:")
        for e in result.errors:
            print(f"  ❌ {e.key}: {e.message}")

    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"  ⚠️ {w.key}: {w.message}")

    print("\nCurrent Config:")
    for key, value in ConfigValidator().get_config_summary().items():
        print(f"  {key}: {value}")
