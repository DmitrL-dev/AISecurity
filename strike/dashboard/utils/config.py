#!/usr/bin/env python3
"""
SENTINEL Strike — Configuration Loader

Extracted from strike_console.py for modularity.
"""

import json
from pathlib import Path
from typing import Dict


# Default config path
CONFIG_PATH = Path(__file__).parent.parent.parent / \
    "config" / "attack_config.json"


def load_default_config() -> Dict:
    """Load default config from attack_config.json."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load config: {e}")
    return {}


# Cache the config on module load
DEFAULT_CONFIG = load_default_config()
