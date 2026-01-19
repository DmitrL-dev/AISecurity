"""
Crystal Compression Metrics.

Measures actual compression ratio achieved by crystallization.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger("rlm_crystal.compression")


@dataclass
class CompressionMetrics:
    """Compression metrics for a crystal."""

    original_bytes: int
    crystal_bytes: int
    primitives_count: int
    token_count_original: int
    token_count_crystal: int

    @property
    def compression_ratio(self) -> float:
        """Bytes compression ratio."""
        if self.original_bytes == 0:
            return 1.0
        return self.original_bytes / max(self.crystal_bytes, 1)

    @property
    def token_compression_ratio(self) -> float:
        """Token compression ratio (most important for LLMs)."""
        if self.token_count_original == 0:
            return 1.0
        return self.token_count_original / max(self.token_count_crystal, 1)

    @property
    def density(self) -> float:
        """Information density (primitives per KB)."""
        return self.primitives_count / max(self.original_bytes / 1024, 0.001)

    def __str__(self):
        return (
            f"Compression: {self.compression_ratio:.1f}x bytes, "
            f"{self.token_compression_ratio:.1f}x tokens, "
            f"{self.density:.1f} primitives/KB"
        )


class CompressionAnalyzer:
    """
    Analyze compression achieved by crystallization.

    Measures:
    - Bytes compression ratio
    - Token compression ratio (most important)
    - Information density

    Example:
        >>> analyzer = CompressionAnalyzer()
        >>> metrics = analyzer.analyze_crystal(crystal, original_content)
        >>> print(f"Compression: {metrics.compression_ratio:.1f}x")
    """

    # Average chars per token (GPT-like tokenizers)
    CHARS_PER_TOKEN = 4

    def analyze_crystal(
        self,
        crystal,
        original_content: str,
    ) -> CompressionMetrics:
        """Analyze compression for a single crystal."""
        # Original metrics
        original_bytes = len(original_content.encode("utf-8"))
        original_tokens = len(original_content) // self.CHARS_PER_TOKEN

        # Crystal metrics
        crystal_repr = self._crystal_to_string(crystal)
        crystal_bytes = len(crystal_repr.encode("utf-8"))
        crystal_tokens = len(crystal_repr) // self.CHARS_PER_TOKEN

        return CompressionMetrics(
            original_bytes=original_bytes,
            crystal_bytes=crystal_bytes,
            primitives_count=len(crystal.primitives),
            token_count_original=original_tokens,
            token_count_crystal=crystal_tokens,
        )

    def analyze_project(
        self,
        crystals: Dict[str, Any],
        original_contents: Dict[str, str],
    ) -> Dict[str, Any]:
        """Analyze compression for entire project."""
        total_original = 0
        total_crystal = 0
        total_primitives = 0

        file_metrics = []

        for path, crystal in crystals.items():
            if path in original_contents:
                metrics = self.analyze_crystal(crystal, original_contents[path])
                file_metrics.append(metrics)

                total_original += metrics.original_bytes
                total_crystal += metrics.crystal_bytes
                total_primitives += metrics.primitives_count

        # Aggregate metrics
        return {
            "files_analyzed": len(file_metrics),
            "total_original_bytes": total_original,
            "total_crystal_bytes": total_crystal,
            "total_primitives": total_primitives,
            "overall_compression_ratio": total_original / max(total_crystal, 1),
            "average_density": total_primitives / max(total_original / 1024, 0.001),
            "best_compression": max(
                (m.compression_ratio for m in file_metrics), default=0
            ),
            "worst_compression": min(
                (m.compression_ratio for m in file_metrics), default=0
            ),
        }

    def _crystal_to_string(self, crystal) -> str:
        """Convert crystal to compact string representation."""
        lines = []

        # Header
        lines.append(f"# {crystal.name}")

        # Primitives (compact format)
        for prim in crystal.primitives:
            lines.append(f"{prim.ptype}:{prim.name}:{prim.source_line}")

        return "\n".join(lines)

    def estimate_context_savings(
        self,
        crystals: Dict[str, Any],
        original_contents: Dict[str, str],
        context_window: int = 128000,
    ) -> Dict[str, Any]:
        """Estimate how many more files fit in context with compression."""
        total_original_tokens = 0
        total_crystal_tokens = 0

        for path, crystal in crystals.items():
            if path in original_contents:
                content = original_contents[path]
                total_original_tokens += len(content) // self.CHARS_PER_TOKEN

                crystal_repr = self._crystal_to_string(crystal)
                total_crystal_tokens += len(crystal_repr) // self.CHARS_PER_TOKEN

        files_count = len(crystals)
        avg_original = total_original_tokens / max(files_count, 1)
        avg_crystal = total_crystal_tokens / max(files_count, 1)

        return {
            "files_count": files_count,
            "total_original_tokens": total_original_tokens,
            "total_crystal_tokens": total_crystal_tokens,
            "compression_ratio": total_original_tokens / max(total_crystal_tokens, 1),
            "files_fit_original": int(context_window / max(avg_original, 1)),
            "files_fit_crystal": int(context_window / max(avg_crystal, 1)),
            "capacity_increase": f"{total_original_tokens / max(total_crystal_tokens, 1):.1f}x",
        }


def measure_compression(crystal, content: str) -> CompressionMetrics:
    """Quick compression measurement."""
    analyzer = CompressionAnalyzer()
    return analyzer.analyze_crystal(crystal, content)
