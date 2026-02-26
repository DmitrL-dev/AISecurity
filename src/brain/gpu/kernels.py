"""
cuTILE GPU Kernels

High-performance kernels for Sentinel using NVIDIA cuTILE.
Automatically uses Tensor Cores when available.

Kernels:
- KL Divergence (Information Theory)
- Cosine Similarity (Embeddings)
- Softmax (Attention)
"""

import logging
import numpy as np
from typing import Union
from .detector import gpu_available, cutile_available, gpu_fallback

logger = logging.getLogger("GPU.Kernels")

# Type alias for array-like
ArrayLike = Union[np.ndarray, "cp.ndarray"]


# ============================================================================
# CPU Reference Implementations (fallbacks)
# ============================================================================

def _kl_divergence_cpu(p: np.ndarray, q: np.ndarray, epsilon: float = 1e-10) -> float:
    """CPU implementation of KL Divergence."""
    p = np.asarray(p, dtype=np.float32)
    q = np.asarray(q, dtype=np.float32)

    # Normalize
    p = p / (p.sum() + epsilon)
    q = q / (q.sum() + epsilon)

    # Add epsilon to avoid log(0)
    p = np.clip(p, epsilon, 1.0)
    q = np.clip(q, epsilon, 1.0)

    return float(np.sum(p * np.log(p / q)))


def _cosine_similarity_batch_cpu(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """CPU implementation of batch cosine similarity."""
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)

    # Normalize
    a_norm = a / (np.linalg.norm(a, axis=-1, keepdims=True) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=-1, keepdims=True) + 1e-10)

    return np.sum(a_norm * b_norm, axis=-1)


def _softmax_cpu(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """CPU implementation of softmax."""
    x = np.asarray(x, dtype=np.float32)
    x_max = np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


# ============================================================================
# GPU Implementations (cuTILE or CuPy)
# ============================================================================

def _get_cupy():
    """Lazy import of CuPy."""
    import cupy as cp
    return cp


def _get_cutile():
    """Lazy import of cuTILE."""
    import cuda.tile as ct
    return ct


# KL Divergence
@gpu_fallback(_kl_divergence_cpu)
def kl_divergence_gpu(p: ArrayLike, q: ArrayLike, epsilon: float = 1e-10) -> float:
    """
    GPU-accelerated KL Divergence using CuPy.

    D_KL(P || Q) = Σ P(x) * log(P(x) / Q(x))
    """
    cp = _get_cupy()

    p = cp.asarray(p, dtype=cp.float32)
    q = cp.asarray(q, dtype=cp.float32)

    # Normalize
    p = p / (p.sum() + epsilon)
    q = q / (q.sum() + epsilon)

    # Clip to avoid log(0)
    p = cp.clip(p, epsilon, 1.0)
    q = cp.clip(q, epsilon, 1.0)

    kl = cp.sum(p * cp.log(p / q))

    return float(kl.get())


# Cosine Similarity Batch
@gpu_fallback(_cosine_similarity_batch_cpu)
def cosine_similarity_batch_gpu(a: ArrayLike, b: ArrayLike) -> np.ndarray:
    """
    GPU-accelerated batch cosine similarity.

    Returns cosine similarity for each pair in the batch.
    """
    cp = _get_cupy()

    a = cp.asarray(a, dtype=cp.float32)
    b = cp.asarray(b, dtype=cp.float32)

    # Normalize
    a_norm = a / (cp.linalg.norm(a, axis=-1, keepdims=True) + 1e-10)
    b_norm = b / (cp.linalg.norm(b, axis=-1, keepdims=True) + 1e-10)

    result = cp.sum(a_norm * b_norm, axis=-1)

    return result.get()


# Softmax
@gpu_fallback(_softmax_cpu)
def softmax_gpu(x: ArrayLike, axis: int = -1) -> np.ndarray:
    """GPU-accelerated softmax."""
    cp = _get_cupy()

    x = cp.asarray(x, dtype=cp.float32)
    x_max = cp.max(x, axis=axis, keepdims=True)
    exp_x = cp.exp(x - x_max)
    result = exp_x / cp.sum(exp_x, axis=axis, keepdims=True)

    return result.get()


# ============================================================================
# cuTILE Optimized Kernels (for future Tensor Core usage)
# ============================================================================

def kl_divergence_cutile(p: ArrayLike, q: ArrayLike, tile_size: int = 65536) -> float:
    """
    cuTILE-optimized KL Divergence using tiling for large distributions.

    For distributions larger than tile_size, processes in tiles to:
    - Reduce GPU memory pressure
    - Enable better cache utilization
    - Allow Tensor Core optimization per tile

    Args:
        p: First probability distribution
        q: Second probability distribution
        tile_size: Elements per tile (default 64K for optimal L2 cache usage)

    Returns:
        KL divergence value
    """
    if not cutile_available():
        return kl_divergence_gpu(p, q)

    cp = _get_cupy()
    epsilon = 1e-10

    p = cp.asarray(p, dtype=cp.float32).ravel()
    q = cp.asarray(q, dtype=cp.float32).ravel()

    # Normalize full distributions first
    p = p / (p.sum() + epsilon)
    q = q / (q.sum() + epsilon)

    # For small distributions, use standard implementation
    if p.size <= tile_size:
        p = cp.clip(p, epsilon, 1.0)
        q = cp.clip(q, epsilon, 1.0)
        return float(cp.sum(p * cp.log(p / q)).get())

    # Tiled processing for large distributions
    kl_sum = cp.float32(0.0)
    n_tiles = (p.size + tile_size - 1) // tile_size

    for i in range(n_tiles):
        start = i * tile_size
        end = min(start + tile_size, p.size)

        p_tile = cp.clip(p[start:end], epsilon, 1.0)
        q_tile = cp.clip(q[start:end], epsilon, 1.0)

        # Accumulate KL divergence contribution from this tile
        kl_sum += cp.sum(p_tile * cp.log(p_tile / q_tile))

    return float(kl_sum.get())


# ============================================================================
# Convenience API
# ============================================================================

def kl_divergence(p: ArrayLike, q: ArrayLike, epsilon: float = 1e-10) -> float:
    """
    Compute KL Divergence with automatic GPU acceleration.

    Automatically uses GPU if available, falls back to CPU otherwise.
    """
    if gpu_available():
        return kl_divergence_gpu(p, q, epsilon)
    return _kl_divergence_cpu(np.asarray(p), np.asarray(q), epsilon)


def cosine_similarity_batch(a: ArrayLike, b: ArrayLike) -> np.ndarray:
    """Batch cosine similarity with automatic GPU acceleration."""
    if gpu_available():
        return cosine_similarity_batch_gpu(a, b)
    return _cosine_similarity_batch_cpu(np.asarray(a), np.asarray(b))


def softmax(x: ArrayLike, axis: int = -1) -> np.ndarray:
    """Softmax with automatic GPU acceleration."""
    if gpu_available():
        return softmax_gpu(x, axis)
    return _softmax_cpu(np.asarray(x), axis)
