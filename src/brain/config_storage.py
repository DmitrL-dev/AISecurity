"""
Engine Configuration Storage

Persists engine configuration to Redis for durability across restarts.
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Redis connection
_redis = None
CONFIG_KEY_PREFIX = "sentinel:engine:config:"


def get_redis():
    """Get or create Redis connection."""
    global _redis
    if _redis is None:
        try:
            import redis

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            _redis = redis.from_url(redis_url, decode_responses=True)
            _redis.ping()
            logger.info("Engine config storage connected to Redis")
        except Exception as e:
            logger.warning(f"Redis not available for config storage: {e}")
            _redis = None
    return _redis


def save_config(engine_name: str, config: dict) -> bool:
    """
    Save engine configuration to Redis.

    Args:
        engine_name: Name of the engine
        config: Configuration dict with threshold, priority, parameters

    Returns:
        True if saved successfully
    """
    r = get_redis()
    if not r:
        logger.warning(f"Cannot save config for {engine_name} - Redis unavailable")
        return False

    try:
        key = f"{CONFIG_KEY_PREFIX}{engine_name}"
        r.set(key, json.dumps(config))
        logger.info(f"Saved config for engine '{engine_name}': {config}")
        return True
    except Exception as e:
        logger.error(f"Failed to save config for {engine_name}: {e}")
        return False


def load_config(engine_name: str) -> Optional[dict]:
    """
    Load engine configuration from Redis.

    Args:
        engine_name: Name of the engine

    Returns:
        Configuration dict or None if not found
    """
    r = get_redis()
    if not r:
        return None

    try:
        key = f"{CONFIG_KEY_PREFIX}{engine_name}"
        data = r.get(key)
        if data:
            config = json.loads(data)
            logger.debug(f"Loaded config for {engine_name}: {config}")
            return config
        return None
    except Exception as e:
        logger.error(f"Failed to load config for {engine_name}: {e}")
        return None


def load_all_configs() -> dict:
    """
    Load all engine configurations from Redis.

    Returns:
        Dict mapping engine names to config dicts
    """
    r = get_redis()
    if not r:
        return {}

    try:
        pattern = f"{CONFIG_KEY_PREFIX}*"
        keys = r.keys(pattern)
        configs = {}
        for key in keys:
            engine_name = key.replace(CONFIG_KEY_PREFIX, "")
            data = r.get(key)
            if data:
                configs[engine_name] = json.loads(data)
        logger.info(f"Loaded {len(configs)} engine configs from Redis")
        return configs
    except Exception as e:
        logger.error(f"Failed to load configs: {e}")
        return {}


def delete_config(engine_name: str) -> bool:
    """Delete engine configuration from Redis."""
    r = get_redis()
    if not r:
        return False

    try:
        key = f"{CONFIG_KEY_PREFIX}{engine_name}"
        r.delete(key)
        logger.info(f"Deleted config for engine '{engine_name}'")
        return True
    except Exception as e:
        logger.error(f"Failed to delete config for {engine_name}: {e}")
        return False
