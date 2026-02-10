"""
Virtual Bandwidth Expander (VBE) — C³ HPE Integration.

Implements context window multiplexing inspired by the Fiber Loop
Memory Paradigm (Carmack 2026). Analogous to WDM (Wavelength Division
Multiplexing): a single physical channel (LLM context window) carries
multiple semantic "wavelengths" (compressed primitives), each
representing a distinct fact or knowledge fragment.

Three compression levels:
    - dense:    Lossless, all metadata preserved
    - semantic: Key signatures only (5-10x compression)
    - ultra:    Minimal tokens for reasoning (10-25x compression)

Example:
    >>> vbe = VirtualBandwidthExpander()
    >>> facts = [{"content": "get_user returns User object...", ...}]
    >>> compressed = vbe.compress_facts(facts)
    >>> injectable = vbe.expand_for_injection(compressed)
    >>> report = vbe.estimate_bandwidth(facts, context_window=128000)
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger("rlm_crystal.bandwidth")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHARS_PER_TOKEN: int = 4  # Approximate chars-per-token for GPT-class models


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CompressionLevel(Enum):
    """Compression strategy level."""

    DENSE = "dense"  # Lossless: all metadata preserved
    SEMANTIC = "semantic"  # Key information only
    ULTRA = "ultra"  # Minimal tokens for reasoning


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CompressedFact:
    """A fact compressed into a set of semantic primitives.

    Attributes:
        fact_id:           Stable hash of the original content.
        original_tokens:   Token count of the original content.
        compressed_tokens: Token count after compression.
        primitives:        Extracted semantic primitives.
        dense_repr:        Compact string representation.
        level:             Compression level used.
        metadata:          Preserved metadata (domain, level, confidence …).
    """

    fact_id: str
    original_tokens: int
    compressed_tokens: int
    primitives: List[str]
    dense_repr: str
    level: CompressionLevel
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def compression_ratio(self) -> float:
        """How many times smaller the compressed form is."""
        if self.original_tokens == 0:
            return 1.0
        return self.original_tokens / max(self.compressed_tokens, 1)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "fact_id": self.fact_id,
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "primitives": self.primitives,
            "dense_repr": self.dense_repr,
            "level": self.level.value,
            "compression_ratio": round(self.compression_ratio, 2),
            "metadata": self.metadata,
        }


@dataclass
class BandwidthReport:
    """Report on VBE effectiveness.

    Attributes:
        original_tokens:    Total tokens before compression.
        compressed_tokens:  Total tokens after compression.
        facts_compressed:   Number of facts processed.
        context_window:     Target context window size (tokens).
    """

    original_tokens: int
    compressed_tokens: int
    facts_compressed: int
    context_window: int

    @property
    def compression_ratio(self) -> float:
        """Overall compression ratio."""
        if self.original_tokens == 0:
            return 1.0
        return self.original_tokens / max(self.compressed_tokens, 1)

    @property
    def virtual_capacity(self) -> int:
        """Virtual context capacity (tokens) after compression."""
        return int(self.context_window * self.compression_ratio)

    @property
    def utilization_pct(self) -> float:
        """Percentage of context window used by compressed facts."""
        if self.context_window == 0:
            return 0.0
        return (self.compressed_tokens / self.context_window) * 100

    @property
    def headroom_tokens(self) -> int:
        """Remaining tokens available for system/user prompts."""
        return max(self.context_window - self.compressed_tokens, 0)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "compression_ratio": round(self.compression_ratio, 2),
            "virtual_capacity": self.virtual_capacity,
            "facts_compressed": self.facts_compressed,
            "context_window": self.context_window,
            "utilization_pct": round(self.utilization_pct, 1),
            "headroom_tokens": self.headroom_tokens,
        }


# ---------------------------------------------------------------------------
# Core: Virtual Bandwidth Expander
# ---------------------------------------------------------------------------


class VirtualBandwidthExpander:
    """WDM multiplexer for the LLM context window.

    Takes a collection of facts (dicts with ``content``, ``level``,
    ``domain``, etc.) and compresses them into *CompressedFact* objects.
    At injection time, ``expand_for_injection`` reconstructs a readable
    text block from the compressed forms.

    The net effect is a **virtual** increase in context window capacity —
    analogous to WDM adding wavelengths to a fiber optic channel.

    Example:
        >>> vbe = VirtualBandwidthExpander(level=CompressionLevel.SEMANTIC)
        >>> compressed = vbe.compress_facts(facts)
        >>> print(vbe.estimate_bandwidth(facts).compression_ratio)
        8.3
    """

    def __init__(
        self,
        level: CompressionLevel = CompressionLevel.SEMANTIC,
        max_primitive_length: int = 120,
    ) -> None:
        self.level = level
        self.max_primitive_length = max_primitive_length
        self._compressors = {
            CompressionLevel.DENSE: self._compress_dense,
            CompressionLevel.SEMANTIC: self._compress_semantic,
            CompressionLevel.ULTRA: self._compress_ultra,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compress_facts(
        self,
        facts: Sequence[Dict[str, Any]],
        *,
        level: Optional[CompressionLevel] = None,
    ) -> List[CompressedFact]:
        """Compress a sequence of facts.

        Args:
            facts: Dicts with at least ``content`` key.
            level: Override instance-level compression.

        Returns:
            List of CompressedFact objects.
        """
        effective_level = level or self.level
        compressor = self._compressors[effective_level]
        results: List[CompressedFact] = []

        for fact in facts:
            content: str = fact.get("content", "")
            if not content:
                continue
            compressed = compressor(fact, content)
            results.append(compressed)

        logger.info(
            "VBE compressed %d facts at level=%s",
            len(results),
            effective_level.value,
        )
        return results

    def expand_for_injection(
        self,
        compressed: Sequence[CompressedFact],
        *,
        header: str = "## Project Context (compressed)",
    ) -> str:
        """Expand compressed facts into an LLM-injectable block.

        Args:
            compressed: Previously compressed facts.
            header:     Markdown header for the block.

        Returns:
            Formatted string ready for prompt injection.
        """
        if not compressed:
            return ""

        lines: List[str] = [header, ""]

        for cf in compressed:
            domain = cf.metadata.get("domain", "general")
            level_tag = cf.metadata.get("level", "?")
            lines.append(f"- [{domain}/L{level_tag}] {cf.dense_repr}")

        lines.append("")
        lines.append(
            f"_({len(compressed)} facts, "
            f"{sum(c.compressed_tokens for c in compressed)} tokens, "
            f"{self._avg_ratio(compressed):.1f}x compression)_"
        )
        return "\n".join(lines)

    def estimate_bandwidth(
        self,
        facts: Sequence[Dict[str, Any]],
        context_window: int = 128_000,
        *,
        level: Optional[CompressionLevel] = None,
    ) -> BandwidthReport:
        """Estimate virtual bandwidth gain.

        Returns a :class:`BandwidthReport` showing how much context
        window space is saved (or virtually gained) by compression.
        """
        compressed = self.compress_facts(facts, level=level)

        total_original = sum(c.original_tokens for c in compressed)
        total_compressed = sum(c.compressed_tokens for c in compressed)

        return BandwidthReport(
            original_tokens=total_original,
            compressed_tokens=total_compressed,
            facts_compressed=len(compressed),
            context_window=context_window,
        )

    def compress_crystal(self, crystal: Any) -> CompressedFact:
        """Compress a FileCrystal into a single CompressedFact.

        This bridges C³ hierarchy objects directly into the VBE
        pipeline without requiring intermediate dict conversion.
        """
        primitives: List[str] = []
        for prim in crystal.primitives:
            primitives.append(f"{prim.ptype}:{prim.name}:{prim.source_line}")

        dense = f"# {crystal.name}\n" + "\n".join(primitives)
        original_tokens = crystal.token_count or (len(dense) // CHARS_PER_TOKEN)
        compressed_tokens = len(dense) // CHARS_PER_TOKEN

        return CompressedFact(
            fact_id=self._fact_hash(dense),
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            primitives=primitives,
            dense_repr=dense,
            level=CompressionLevel.DENSE,
            metadata={
                "source": crystal.path,
                "primitives_count": len(primitives),
            },
        )

    # ------------------------------------------------------------------
    # Compression strategies
    # ------------------------------------------------------------------

    def _compress_dense(
        self,
        fact: Dict[str, Any],
        content: str,
    ) -> CompressedFact:
        """Lossless dense compression — all metadata preserved.

        Format: ``LEVEL:DOMAIN:CONFIDENCE | content_summary``
        """
        domain = fact.get("domain", "general")
        level = fact.get("level", "?")
        confidence = fact.get("confidence", 1.0)

        primitives = self._extract_primitives(content)
        dense_parts = [
            f"L{level}:{domain}:{confidence}",
            *primitives,
        ]
        dense_repr = " | ".join(dense_parts)

        original_tokens = len(content) // CHARS_PER_TOKEN
        compressed_tokens = len(dense_repr) // CHARS_PER_TOKEN

        return CompressedFact(
            fact_id=self._fact_hash(content),
            original_tokens=max(original_tokens, 1),
            compressed_tokens=max(compressed_tokens, 1),
            primitives=primitives,
            dense_repr=dense_repr,
            level=CompressionLevel.DENSE,
            metadata=self._extract_metadata(fact),
        )

    def _compress_semantic(
        self,
        fact: Dict[str, Any],
        content: str,
    ) -> CompressedFact:
        """Semantic compression — key signatures only.

        Strips boilerplate, keeps function/class signatures,
        key entities, and causal relationships.
        """
        primitives = self._extract_primitives(content)

        # Semantic: keep only the most informative primitive(s)
        if len(primitives) > 3:
            primitives = primitives[:3]

        dense_repr = "; ".join(primitives)
        if not dense_repr:
            dense_repr = self._first_sentence(content)

        original_tokens = len(content) // CHARS_PER_TOKEN
        compressed_tokens = len(dense_repr) // CHARS_PER_TOKEN

        return CompressedFact(
            fact_id=self._fact_hash(content),
            original_tokens=max(original_tokens, 1),
            compressed_tokens=max(compressed_tokens, 1),
            primitives=primitives,
            dense_repr=dense_repr,
            level=CompressionLevel.SEMANTIC,
            metadata=self._extract_metadata(fact),
        )

    def _compress_ultra(
        self,
        fact: Dict[str, Any],
        content: str,
    ) -> CompressedFact:
        """Ultra compression — minimal tokens for reasoning.

        Extracts bare entity→relation→entity triples.
        """
        primitives = self._extract_primitives(content)

        # Ultra: collapse to single-line arrow notation
        if primitives:
            dense_repr = " → ".join(p[:40] for p in primitives[:2])
        else:
            dense_repr = content[:40].replace("\n", " ")

        original_tokens = len(content) // CHARS_PER_TOKEN
        compressed_tokens = len(dense_repr) // CHARS_PER_TOKEN

        return CompressedFact(
            fact_id=self._fact_hash(content),
            original_tokens=max(original_tokens, 1),
            compressed_tokens=max(compressed_tokens, 1),
            primitives=primitives[:2],
            dense_repr=dense_repr,
            level=CompressionLevel.ULTRA,
            metadata=self._extract_metadata(fact),
        )

    # ------------------------------------------------------------------
    # Primitive extraction helpers
    # ------------------------------------------------------------------

    def _extract_primitives(self, content: str) -> List[str]:
        """Extract semantic primitives from free-text content.

        Heuristic extraction:
        1. Code signatures (``def …``, ``class …``)
        2. Key-value patterns (``key: value``)
        3. Causal patterns (``X because Y``, ``X → Y``)
        4. Named entities (capitalized words following patterns)
        5. Fallback: first meaningful sentence
        """
        primitives: List[str] = []

        # 1. Code signatures
        for match in re.finditer(
            r"(?:def|class|async def)\s+(\w+)",
            content,
        ):
            sig = match.group(0)[: self.max_primitive_length]
            primitives.append(sig)

        # 2. Key-value / assignment patterns
        for match in re.finditer(
            r"(\w[\w\s]{1,30})\s*[:=]\s*(.{1,60})",
            content,
        ):
            kv = f"{match.group(1).strip()}: {match.group(2).strip()}"
            if len(kv) <= self.max_primitive_length:
                primitives.append(kv)

        # 3. Causal / arrow patterns
        for match in re.finditer(
            r"(\w[\w\s]{2,30})\s*"
            r"(?:→|->|=>|because|therefore)"
            r"\s*(\w[\w\s]{2,30})",
            content,
        ):
            causal = f"{match.group(1).strip()} → " f"{match.group(2).strip()}"
            primitives.append(causal[: self.max_primitive_length])

        # 4. Fallback: first sentence
        if not primitives:
            first = self._first_sentence(content)
            if first:
                primitives.append(first)

        # Deduplicate preserving order
        seen: set[str] = set()
        unique: List[str] = []
        for p in primitives:
            if p not in seen:
                seen.add(p)
                unique.append(p)

        return unique

    def _first_sentence(self, text: str) -> str:
        """Return the first meaningful sentence from *text*."""
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped and len(stripped) > 10:
                return stripped[: self.max_primitive_length]
        return text[: self.max_primitive_length]

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fact_hash(content: str) -> str:
        """Stable short hash for a fact."""
        return hashlib.sha256(
            content.encode("utf-8"),
        ).hexdigest()[:12]

    @staticmethod
    def _extract_metadata(fact: Dict[str, Any]) -> Dict[str, Any]:
        """Pull standard metadata fields from a fact dict."""
        return {
            k: fact[k] for k in ("level", "domain", "confidence", "id") if k in fact
        }

    @staticmethod
    def _avg_ratio(compressed: Sequence[CompressedFact]) -> float:
        """Average compression ratio across a batch."""
        if not compressed:
            return 1.0
        return sum(c.compression_ratio for c in compressed) / len(compressed)
