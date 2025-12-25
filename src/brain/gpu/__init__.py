# GPU Acceleration Module
from .detector import detect_gpu, get_gpu_info, gpu_available, cutile_available, GPUInfo
from .kernels import kl_divergence, cosine_similarity_batch, softmax

__all__ = [
    "detect_gpu",
    "get_gpu_info",
    "gpu_available",
    "cutile_available",
    "GPUInfo",
    "kl_divergence",
    "cosine_similarity_batch",
    "softmax",
]
