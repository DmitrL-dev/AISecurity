"""
Tests for Virtual Bandwidth Expander (C³ HPE Integration).

Verifies:
- Compression at all 3 levels (dense, semantic, ultra)
- Round-trip: expand(compress(facts)) preserves key primitives
- BandwidthReport calculations
- Crystal integration via compress_crystal
- Edge cases: empty facts, no content, single-char content
"""

import pytest

from rlm_toolkit.crystal.bandwidth import (
    BandwidthReport,
    CompressedFact,
    CompressionLevel,
    VirtualBandwidthExpander,
)
from rlm_toolkit.crystal.hierarchy import FileCrystal, Primitive


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vbe() -> VirtualBandwidthExpander:
    """Default VBE instance (semantic level)."""
    return VirtualBandwidthExpander()


@pytest.fixture
def sample_facts() -> list[dict[str, object]]:
    """Representative fact list."""
    return [
        {
            "content": (
                "The get_user function retrieves a User object "
                "from the database by primary key. It accepts an "
                "integer user_id and returns Optional[User]. "
                "Raises ValueError if user_id is negative."
            ),
            "level": 1,
            "domain": "auth",
            "confidence": 0.95,
        },
        {
            "content": (
                "class ModelRotator manages load balancing across "
                "multiple LLM providers using round-robin, weighted, "
                "priority, and adaptive strategies."
            ),
            "level": 1,
            "domain": "providers",
            "confidence": 1.0,
        },
        {
            "content": (
                "L0 fact: Project uses Python 3.11+ with strict "
                "mypy typing. All modules must pass mypy --strict."
            ),
            "level": 0,
            "domain": "infrastructure",
            "confidence": 1.0,
        },
    ]


@pytest.fixture
def sample_crystal() -> FileCrystal:
    """A small FileCrystal for integration testing."""
    crystal = FileCrystal(path="/src/auth.py", name="auth.py")
    crystal.token_count = 500
    crystal.add_primitive(
        Primitive(
            ptype="FUNCTION",
            name="get_user",
            value="def get_user(id: int) -> User",
            source_file="/src/auth.py",
            source_line=42,
        )
    )
    crystal.add_primitive(
        Primitive(
            ptype="CLASS",
            name="AuthManager",
            value="class AuthManager",
            source_file="/src/auth.py",
            source_line=1,
        )
    )
    return crystal


# ---------------------------------------------------------------------------
# Compression level tests
# ---------------------------------------------------------------------------


class TestCompressionLevels:
    """Each level must produce smaller output than the original."""

    def test_dense_compression(
        self,
        vbe: VirtualBandwidthExpander,
        sample_facts: list[dict[str, object]],
    ) -> None:
        results = vbe.compress_facts(sample_facts, level=CompressionLevel.DENSE)
        assert len(results) == len(sample_facts)
        for cf in results:
            assert cf.level == CompressionLevel.DENSE
            assert cf.compressed_tokens > 0
            assert cf.fact_id  # non-empty hash

    def test_semantic_compression(
        self,
        vbe: VirtualBandwidthExpander,
        sample_facts: list[dict[str, object]],
    ) -> None:
        results = vbe.compress_facts(sample_facts, level=CompressionLevel.SEMANTIC)
        assert len(results) == len(sample_facts)
        for cf in results:
            assert cf.level == CompressionLevel.SEMANTIC

    def test_ultra_compression(
        self,
        vbe: VirtualBandwidthExpander,
        sample_facts: list[dict[str, object]],
    ) -> None:
        results = vbe.compress_facts(sample_facts, level=CompressionLevel.ULTRA)
        assert len(results) == len(sample_facts)
        for cf in results:
            assert cf.level == CompressionLevel.ULTRA

    def test_ultra_is_most_compressed(
        self,
        vbe: VirtualBandwidthExpander,
        sample_facts: list[dict[str, object]],
    ) -> None:
        dense = vbe.compress_facts(sample_facts, level=CompressionLevel.DENSE)
        ultra = vbe.compress_facts(sample_facts, level=CompressionLevel.ULTRA)

        dense_tokens = sum(c.compressed_tokens for c in dense)
        ultra_tokens = sum(c.compressed_tokens for c in ultra)

        assert (
            ultra_tokens <= dense_tokens
        ), f"Ultra ({ultra_tokens}) should be ≤ Dense ({dense_tokens})"


# ---------------------------------------------------------------------------
# Round-trip (compress → expand) tests
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """expand_for_injection must produce readable output."""

    def test_expand_contains_domain(
        self,
        vbe: VirtualBandwidthExpander,
        sample_facts: list[dict[str, object]],
    ) -> None:
        compressed = vbe.compress_facts(sample_facts)
        text = vbe.expand_for_injection(compressed)
        assert "auth" in text
        assert "providers" in text

    def test_expand_header(
        self,
        vbe: VirtualBandwidthExpander,
        sample_facts: list[dict[str, object]],
    ) -> None:
        compressed = vbe.compress_facts(sample_facts)
        text = vbe.expand_for_injection(compressed, header="# Custom Header")
        assert text.startswith("# Custom Header")

    def test_expand_empty(self, vbe: VirtualBandwidthExpander) -> None:
        text = vbe.expand_for_injection([])
        assert text == ""

    def test_expand_shows_stats(
        self,
        vbe: VirtualBandwidthExpander,
        sample_facts: list[dict[str, object]],
    ) -> None:
        compressed = vbe.compress_facts(sample_facts)
        text = vbe.expand_for_injection(compressed)
        assert "3 facts" in text
        assert "compression" in text


# ---------------------------------------------------------------------------
# BandwidthReport tests
# ---------------------------------------------------------------------------


class TestBandwidthReport:
    """Verify report calculations."""

    def test_report_structure(
        self,
        vbe: VirtualBandwidthExpander,
        sample_facts: list[dict[str, object]],
    ) -> None:
        report = vbe.estimate_bandwidth(sample_facts, context_window=128_000)
        assert report.facts_compressed == 3
        assert report.context_window == 128_000
        assert report.original_tokens > 0
        assert report.compressed_tokens > 0
        assert report.compression_ratio >= 1.0

    def test_virtual_capacity(self) -> None:
        report = BandwidthReport(
            original_tokens=1000,
            compressed_tokens=100,
            facts_compressed=5,
            context_window=128_000,
        )
        # 10x compression → 10x virtual capacity
        assert report.compression_ratio == 10.0
        assert report.virtual_capacity == 1_280_000

    def test_headroom(self) -> None:
        report = BandwidthReport(
            original_tokens=1000,
            compressed_tokens=28_000,
            facts_compressed=5,
            context_window=128_000,
        )
        assert report.headroom_tokens == 100_000

    def test_to_dict(self) -> None:
        report = BandwidthReport(
            original_tokens=1000,
            compressed_tokens=100,
            facts_compressed=5,
            context_window=128_000,
        )
        d = report.to_dict()
        assert "compression_ratio" in d
        assert "virtual_capacity" in d
        assert "headroom_tokens" in d


# ---------------------------------------------------------------------------
# CompressedFact tests
# ---------------------------------------------------------------------------


class TestCompressedFact:
    """Verify CompressedFact properties."""

    def test_compression_ratio(self) -> None:
        cf = CompressedFact(
            fact_id="abc",
            original_tokens=100,
            compressed_tokens=10,
            primitives=["test"],
            dense_repr="test",
            level=CompressionLevel.DENSE,
        )
        assert cf.compression_ratio == 10.0

    def test_compression_ratio_zero_original(self) -> None:
        cf = CompressedFact(
            fact_id="abc",
            original_tokens=0,
            compressed_tokens=10,
            primitives=[],
            dense_repr="",
            level=CompressionLevel.DENSE,
        )
        assert cf.compression_ratio == 1.0

    def test_to_dict(self) -> None:
        cf = CompressedFact(
            fact_id="abc123",
            original_tokens=100,
            compressed_tokens=10,
            primitives=["def foo", "class Bar"],
            dense_repr="foo; Bar",
            level=CompressionLevel.SEMANTIC,
            metadata={"domain": "test"},
        )
        d = cf.to_dict()
        assert d["fact_id"] == "abc123"
        assert d["level"] == "semantic"
        assert d["compression_ratio"] == 10.0


# ---------------------------------------------------------------------------
# Crystal integration
# ---------------------------------------------------------------------------


class TestCrystalIntegration:
    """VBE ↔ C³ Crystal hierarchy bridge."""

    def test_compress_crystal(
        self,
        vbe: VirtualBandwidthExpander,
        sample_crystal: FileCrystal,
    ) -> None:
        cf = vbe.compress_crystal(sample_crystal)
        assert cf.original_tokens == 500
        assert "FUNCTION:get_user:42" in cf.dense_repr
        assert "CLASS:AuthManager:1" in cf.dense_repr
        assert len(cf.primitives) == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions and error handling."""

    def test_empty_facts_list(self, vbe: VirtualBandwidthExpander) -> None:
        results = vbe.compress_facts([])
        assert results == []

    def test_fact_without_content(self, vbe: VirtualBandwidthExpander) -> None:
        results = vbe.compress_facts([{"level": 0}])
        assert results == []

    def test_fact_with_empty_content(self, vbe: VirtualBandwidthExpander) -> None:
        results = vbe.compress_facts([{"content": ""}])
        assert results == []

    def test_single_word_content(self, vbe: VirtualBandwidthExpander) -> None:
        results = vbe.compress_facts([{"content": "hello"}])
        assert len(results) == 1
        assert results[0].compressed_tokens >= 1

    def test_code_content_extracts_signatures(
        self,
        vbe: VirtualBandwidthExpander,
    ) -> None:
        results = vbe.compress_facts(
            [
                {
                    "content": (
                        "def calculate_score(user_id: int, weights: list) -> float:\n"
                        "    '''Calculate weighted score for user.'''\n"
                        "    return sum(w * v for w, v in zip(weights, values))"
                    ),
                    "level": 2,
                    "domain": "scoring",
                }
            ]
        )
        assert len(results) == 1
        # Should extract the function signature
        assert any("calculate_score" in p for p in results[0].primitives)
