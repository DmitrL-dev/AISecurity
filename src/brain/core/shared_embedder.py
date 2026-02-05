"""
SharedEmbedder - Singleton SentenceTransformer для всех engines.

Экономит ~2GB RAM за счёт разделения одной модели между engines.
Переключение через env: SENTINEL_SHARED_EMBEDDER=true|false

Usage:
    from brain.core.shared_embedder import get_embedder

    # Автоматически выберет shared или новую копию по настройке
    model = get_embedder()
    embeddings = model.encode(["text1", "text2"])
"""

import os
import logging
from functools import lru_cache
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Feature flag: включить/выключить shared embedder
SHARED_EMBEDDER_ENABLED = (
    os.getenv("SENTINEL_SHARED_EMBEDDER", "true").lower() == "true"
)

# Default model
DEFAULT_MODEL = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_shared_instance(model_name: str = DEFAULT_MODEL) -> Any:
    """
    Singleton instance - загружается один раз.

    Returns:
        SentenceTransformer instance (shared)
    """
    try:
        from sentence_transformers import SentenceTransformer

        logger.info(f"[SharedEmbedder] Loading shared model: {model_name}")
        model = SentenceTransformer(model_name)
        logger.info(f"[SharedEmbedder] Model loaded successfully (shared mode)")
        return model
    except ImportError:
        logger.warning("[SharedEmbedder] sentence-transformers not available")
        return None
    except Exception as e:
        logger.error(f"[SharedEmbedder] Failed to load model: {e}")
        return None


def _get_new_instance(model_name: str = DEFAULT_MODEL) -> Any:
    """
    Создаёт новую изолированную копию модели (legacy behavior).

    Returns:
        SentenceTransformer instance (new copy)
    """
    try:
        from sentence_transformers import SentenceTransformer

        logger.info(f"[Embedder] Loading isolated model: {model_name}")
        model = SentenceTransformer(model_name)
        logger.info(f"[Embedder] Model loaded (isolated mode)")
        return model
    except ImportError:
        logger.warning("[Embedder] sentence-transformers not available")
        return None
    except Exception as e:
        logger.error(f"[Embedder] Failed to load model: {e}")
        return None


def get_embedder(
    model_name: str = DEFAULT_MODEL, force_new: bool = False
) -> Optional[Any]:
    """
    Получить SentenceTransformer embedder.

    Стратегия определяется через:
    - env SENTINEL_SHARED_EMBEDDER=true (default) → shared singleton
    - env SENTINEL_SHARED_EMBEDDER=false → новая копия для каждого вызова
    - force_new=True → игнорирует настройку, создаёт новую копию

    Args:
        model_name: Имя модели sentence-transformers
        force_new: Принудительно создать новую копию (для особых случаев)

    Returns:
        SentenceTransformer instance или None если недоступен

    Example:
        # Стандартное использование (авто-выбор по настройке):
        model = get_embedder()

        # Принудительно изолированная копия:
        model = get_embedder(force_new=True)

        # Другая модель:
        model = get_embedder("all-mpnet-base-v2")
    """
    if force_new:
        return _get_new_instance(model_name)

    if SHARED_EMBEDDER_ENABLED:
        return _get_shared_instance(model_name)
    else:
        return _get_new_instance(model_name)


def is_shared_mode() -> bool:
    """Проверить текущий режим работы."""
    return SHARED_EMBEDDER_ENABLED


def get_embedder_stats() -> dict:
    """
    Получить статистику embedder для мониторинга.

    Returns:
        dict с информацией о режиме и состоянии
    """
    return {
        "shared_mode": SHARED_EMBEDDER_ENABLED,
        "default_model": DEFAULT_MODEL,
        "shared_instance_loaded": (
            _get_shared_instance.cache_info().hits > 0
            if SHARED_EMBEDDER_ENABLED
            else False
        ),
        "cache_info": (
            _get_shared_instance.cache_info()._asdict()
            if SHARED_EMBEDDER_ENABLED
            else None
        ),
    }


# Health check для использования при startup
def embedder_health_check() -> bool:
    """
    Проверка работоспособности embedder.
    Вызывать при startup для раннего обнаружения проблем.

    Returns:
        True если embedder работает корректно
    """
    try:
        model = get_embedder()
        if model is None:
            return False
        # Тестовый encode
        result = model.encode(["health check test"])
        return result is not None and len(result) > 0
    except Exception as e:
        logger.error(f"[SharedEmbedder] Health check failed: {e}")
        return False
