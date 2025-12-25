"""
GPU Acceleration Module

Provides CUDA detection and GPU-accelerated kernels using:
- NVIDIA cuTILE for tensor core operations
- CuPy for general GPU arrays
- Automatic CPU fallback when CUDA not available

Hardware target: RTX 4070 (8GB VRAM)
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional, Callable
from functools import wraps

logger = logging.getLogger("GPU")


@dataclass
class GPUInfo:
    """GPU hardware information."""
    available: bool
    device_name: str = "CPU"
    cuda_version: str = "N/A"
    vram_gb: float = 0.0
    compute_capability: str = "N/A"
    cutile_available: bool = False


# Global GPU state
_gpu_info: Optional[GPUInfo] = None


def detect_gpu() -> GPUInfo:
    """
    Detect CUDA GPU and capabilities.
    Returns GPUInfo with hardware details.
    """
    global _gpu_info

    if _gpu_info is not None:
        return _gpu_info

    info = GPUInfo(available=False)

    # Try CuPy first (more reliable detection)
    try:
        import cupy as cp

        device = cp.cuda.Device(0)
        props = cp.cuda.runtime.getDeviceProperties(0)

        info.available = True
        info.device_name = props['name'].decode() if isinstance(
            props['name'], bytes) else props['name']
        info.cuda_version = f"{cp.cuda.runtime.runtimeGetVersion() // 1000}.{(cp.cuda.runtime.runtimeGetVersion() % 1000) // 10}"
        info.vram_gb = props['totalGlobalMem'] / (1024**3)
        info.compute_capability = f"{props['major']}.{props['minor']}"

        logger.info(f"CUDA GPU detected: {info.device_name}")
        logger.info(
            f"VRAM: {info.vram_gb:.1f}GB, CUDA: {info.cuda_version}, Compute: {info.compute_capability}")

    except ImportError:
        logger.warning("CuPy not installed - no GPU acceleration")
    except Exception as e:
        logger.warning(f"CUDA detection failed: {e}")

    # Try cuTILE
    try:
        import cuda.tile as ct
        info.cutile_available = True
        logger.info("cuTILE available - tensor core acceleration enabled")
    except ImportError:
        logger.info("cuTILE not installed - using CuPy fallback")
    except Exception as e:
        logger.warning(f"cuTILE detection failed: {e}")

    _gpu_info = info
    return info


def get_gpu_info() -> GPUInfo:
    """Get cached GPU info."""
    global _gpu_info
    if _gpu_info is None:
        _gpu_info = detect_gpu()
    return _gpu_info


def gpu_available() -> bool:
    """Check if GPU is available."""
    return get_gpu_info().available


def cutile_available() -> bool:
    """Check if cuTILE is available."""
    return get_gpu_info().cutile_available


def gpu_fallback(cpu_func: Callable):
    """
    Decorator that provides CPU fallback for GPU functions.

    Usage:
        @gpu_fallback(cpu_implementation)
        def gpu_function(data):
            # GPU implementation
            ...
    """
    def decorator(gpu_func: Callable):
        @wraps(gpu_func)
        def wrapper(*args, **kwargs):
            if gpu_available():
                try:
                    return gpu_func(*args, **kwargs)
                except Exception as e:
                    logger.warning(
                        f"GPU execution failed, falling back to CPU: {e}")
                    return cpu_func(*args, **kwargs)
            else:
                return cpu_func(*args, **kwargs)
        return wrapper
    return decorator


# Auto-detect on import if enabled
if os.getenv("GPU_AUTO_DETECT", "true").lower() == "true":
    detect_gpu()
