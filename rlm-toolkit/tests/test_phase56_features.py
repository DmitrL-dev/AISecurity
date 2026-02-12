"""
Unit tests for Phase 5-6 features:
1. Semantic deduplication (extractor.py)
2. InfiniRetri ↔ RLM fallback (infiniretri.py)
3. Async arun() (engine.py)
4. CLI eval/trace commands (commands.py)
"""

import asyncio
import json
import math
import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rlm_toolkit.core.engine import RLM, RLMConfig, RLMResult
from rlm_toolkit.testing.mocks import MockProvider
from rlm_toolkit.memory_bridge.v2.hierarchical import (
    MemoryLevel,
    HierarchicalFact,
)
from rlm_toolkit.memory_bridge.v2.extractor import (
    AutoExtractionEngine,
    CandidateFact,
)
from rlm_toolkit.cli.commands import (
    eval_command,
    trace_command,
)


# ============================================================
# 1. Semantic Deduplication Tests
# ============================================================


class TestCosineSimlarity:
    """Tests for _cosine_similarity static method."""

    def test_identical_vectors(self):
        """Identical vectors → similarity 1.0."""
        sim = AutoExtractionEngine._cosine_similarity(
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
        )
        assert abs(sim - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        """Orthogonal vectors → similarity 0.0."""
        sim = AutoExtractionEngine._cosine_similarity(
            [1.0, 0.0],
            [0.0, 1.0],
        )
        assert abs(sim) < 1e-6

    def test_opposite_vectors(self):
        """Opposite vectors → similarity -1.0."""
        sim = AutoExtractionEngine._cosine_similarity(
            [1.0, 0.0],
            [-1.0, 0.0],
        )
        assert abs(sim - (-1.0)) < 1e-6

    def test_zero_vector(self):
        """Zero vector → similarity 0.0."""
        sim = AutoExtractionEngine._cosine_similarity(
            [0.0, 0.0],
            [1.0, 1.0],
        )
        assert sim == 0.0

    def test_similar_vectors(self):
        """Similar vectors → high similarity."""
        sim = AutoExtractionEngine._cosine_similarity(
            [1.0, 1.0, 0.0],
            [1.0, 0.9, 0.1],
        )
        assert sim > 0.9


class TestSemanticDeduplication:
    """Tests for semantic dedup in AutoExtractionEngine."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock EmbeddingService."""
        svc = MagicMock()

        def make_embed(text):
            """Deterministic embedding with wide spread."""
            words = text.lower().split()
            # Use distinct dimensions per word hash
            vec = [0.0] * 16
            for w in words:
                idx = hash(w) % 16
                vec[idx] += 1.0
            # Normalize
            norm = sum(x * x for x in vec) ** 0.5
            if norm > 0:
                vec = [x / norm for x in vec]
            return vec

        svc.embed = make_embed
        svc.embed_batch = lambda texts: [make_embed(t) for t in texts]
        return svc

    @pytest.fixture
    def extractor_with_embeddings(self, tmp_path, mock_embedding_service):
        """Extractor with mock EmbeddingService."""
        return AutoExtractionEngine(
            project_root=tmp_path,
            embedding_service=mock_embedding_service,
        )

    @pytest.fixture
    def extractor_plain(self, tmp_path):
        """Extractor without EmbeddingService (Jaccard)."""
        return AutoExtractionEngine(project_root=tmp_path)

    def test_semantic_dedupe_identical_content(self, extractor_with_embeddings):
        """Identical content detected as duplicate."""
        candidates = [
            CandidateFact(
                content="Auth uses JWT tokens",
                confidence=0.9,
                source="git_diff",
                suggested_level=MemoryLevel.L1_DOMAIN,
            )
        ]
        existing = [
            HierarchicalFact(
                id="e1",
                content="Auth uses JWT tokens",
                level=MemoryLevel.L1_DOMAIN,
            )
        ]
        result = extractor_with_embeddings.deduplicate(candidates, existing)
        assert len(result) == 0

    def test_jaccard_fallback_when_no_service(self, extractor_plain):
        """Without EmbeddingService, falls back to Jaccard."""
        candidates = [
            CandidateFact(
                content="Auth uses JWT tokens",
                confidence=0.9,
                source="git_diff",
                suggested_level=MemoryLevel.L1_DOMAIN,
            )
        ]
        existing = [
            HierarchicalFact(
                id="e1",
                content="Auth uses JWT tokens",
                level=MemoryLevel.L1_DOMAIN,
            )
        ]
        result = extractor_plain.deduplicate(candidates, existing)
        assert len(result) == 0

    def test_unique_content_passes_through(self, extractor_with_embeddings):
        """Unique content is not deduplicated."""
        candidates = [
            CandidateFact(
                content="Completely new feature added",
                confidence=0.9,
                source="git_diff",
                suggested_level=MemoryLevel.L1_DOMAIN,
            )
        ]
        existing = [
            HierarchicalFact(
                id="e1",
                content="Auth uses JWT tokens",
                level=MemoryLevel.L1_DOMAIN,
            )
        ]
        result = extractor_with_embeddings.deduplicate(candidates, existing)
        assert len(result) >= 1

    def test_embedding_error_falls_back(self, tmp_path):
        """Embedding service error falls back to Jaccard."""
        bad_svc = MagicMock()
        bad_svc.embed_batch = MagicMock(side_effect=RuntimeError("GPU OOM"))

        extractor = AutoExtractionEngine(
            project_root=tmp_path,
            embedding_service=bad_svc,
        )
        candidates = [
            CandidateFact(
                content="Some new fact",
                confidence=0.9,
                source="git_diff",
                suggested_level=MemoryLevel.L1_DOMAIN,
            )
        ]
        # Should not raise, falls back to Jaccard
        result = extractor.deduplicate(candidates, [])
        assert len(result) == 1


# ============================================================
# 2. InfiniRetri Fallback Tests
# ============================================================


class TestInfiniRetriRLMFallback:
    """Tests for InfiniRetriRLM RLM engine fallback."""

    def test_import(self):
        """InfiniRetriRLM can be imported."""
        from rlm_toolkit.retrieval.infiniretri import (
            InfiniRetriRLM,
        )

        assert InfiniRetriRLM is not None

    @patch("rlm_toolkit.retrieval.infiniretri" ".InfiniRetriever")
    def test_init_with_rlm_engine(self, mock_retriever):
        """InfiniRetriRLM accepts rlm_engine parameter."""
        from rlm_toolkit.retrieval.infiniretri import (
            InfiniRetriRLM,
        )

        mock_engine = MagicMock()
        iri = InfiniRetriRLM(
            model_name_or_path="test-model",
            rlm_engine=mock_engine,
        )
        assert iri._rlm_engine is mock_engine

    @patch("rlm_toolkit.retrieval.infiniretri" ".InfiniRetriever")
    def test_init_default_no_engine(self, mock_retriever):
        """InfiniRetriRLM defaults to no engine."""
        from rlm_toolkit.retrieval.infiniretri import (
            InfiniRetriRLM,
        )

        iri = InfiniRetriRLM(
            model_name_or_path="test-model",
        )
        assert iri._rlm_engine is None

    @patch("rlm_toolkit.retrieval.infiniretri" ".InfiniRetriever")
    def test_small_context_uses_engine(self, mock_retriever):
        """Small context delegates to RLM engine."""
        from rlm_toolkit.retrieval.infiniretri import (
            InfiniRetriRLM,
        )

        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.answer = "Engine answer"
        mock_engine.run.return_value = mock_result

        iri = InfiniRetriRLM(
            model_name_or_path="test-model",
            rlm_engine=mock_engine,
            infiniretri_threshold=100_000,
        )

        result = iri.run(
            context="Short context",
            query="What?",
        )

        assert result["metadata"]["method"] == "rlm"
        assert result["answer"] == "Engine answer"
        mock_engine.run.assert_called_once()

    @patch("rlm_toolkit.retrieval.infiniretri" ".InfiniRetriever")
    def test_passthrough_when_no_engine(self, mock_retriever):
        """No engine → passthrough fallback."""
        from rlm_toolkit.retrieval.infiniretri import (
            InfiniRetriRLM,
        )

        iri = InfiniRetriRLM(
            model_name_or_path="test-model",
            rlm_engine=None,
        )

        # Patch lazy init to also fail
        with patch.dict(
            "sys.modules",
            {
                "rlm_toolkit.core.engine": None,
            },
        ):
            result = iri.run(
                context="Short",
                query="What?",
            )

        assert result["metadata"]["method"] == "passthrough"


# ============================================================
# 3. Async arun() Tests
# ============================================================


class TestAsyncArun:
    """Tests for RLM.arun() async method."""

    def test_arun_returns_result(self):
        """arun() returns RLMResult via asyncio."""
        provider = MockProvider(responses=["FINAL(42)"])
        rlm = RLM(root=provider)

        result = asyncio.run(rlm.arun(context="test", query="What?"))

        assert isinstance(result, RLMResult)
        assert result.status == "success"
        assert "42" in result.answer

    def test_arun_passes_kwargs(self):
        """arun() passes kwargs to run()."""
        provider = MockProvider(responses=["FINAL(ok)"])
        config = RLMConfig(max_iterations=5)
        rlm = RLM(root=provider, config=config)

        result = asyncio.run(rlm.arun(context="ctx", query="q"))

        assert isinstance(result, RLMResult)

    def test_arun_handles_error(self):
        """arun() propagates errors gracefully."""
        provider = MockProvider(responses=["error!"])
        config = RLMConfig(max_iterations=1)
        rlm = RLM(root=provider, config=config)

        result = asyncio.run(rlm.arun(context="", query="test"))

        assert isinstance(result, RLMResult)
        # Should still return a result, not raise


# ============================================================
# 4. CLI Commands Tests
# ============================================================


class TestEvalCommandReal:
    """Tests for eval_command with real benchmark files."""

    def test_missing_benchmark_file(self, tmp_path, capsys):
        """Non-existent benchmark returns 1."""
        args = argparse.Namespace(
            model="ollama:llama3",
            benchmark=str(tmp_path / "nonexistent.json"),
        )

        result = eval_command(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_invalid_benchmark_format(self, tmp_path, capsys):
        """Non-array benchmark returns 1."""
        bench = tmp_path / "bad.json"
        bench.write_text('{"not": "array"}')

        args = argparse.Namespace(
            model="ollama:llama3",
            benchmark=str(bench),
        )

        result = eval_command(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "JSON array" in captured.err

    def test_valid_benchmark(self, tmp_path, capsys):
        """Valid benchmark runs and returns 0."""
        bench = tmp_path / "bench.json"
        bench.write_text(
            json.dumps(
                [
                    {
                        "context": "2+2=4",
                        "query": "What is 2+2?",
                    },
                ]
            )
        )

        args = argparse.Namespace(
            model="ollama:llama3",
            benchmark=str(bench),
        )

        # Mock to avoid actual LLM call
        with patch("rlm_toolkit.cli.commands.get_provider") as mock_prov:
            mock_prov.return_value = MockProvider(responses=["FINAL(4)"])
            result = eval_command(args)

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["total"] == 1

    def test_empty_benchmark(self, tmp_path, capsys):
        """Empty array benchmark returns 0."""
        bench = tmp_path / "empty.json"
        bench.write_text("[]")

        args = argparse.Namespace(
            model="ollama:llama3",
            benchmark=str(bench),
        )

        with patch("rlm_toolkit.cli.commands.get_provider") as mock_prov:
            mock_prov.return_value = MockProvider()
            result = eval_command(args)

        assert result == 0


class TestTraceCommandReal:
    """Tests for trace_command with real files."""

    def test_missing_trace(self, tmp_path, capsys):
        """Non-existent trace returns 1."""
        args = argparse.Namespace(
            run_id="nonexistent-id",
            format="text",
        )

        with patch(
            "rlm_toolkit.cli.commands.Path",
        ) as mock_path_cls:
            # Make .rlm/traces/ point to tmp
            mock_path_cls.side_effect = Path
            result = trace_command(args)

        assert result == 1

    def test_valid_trace_text(self, tmp_path, capsys):
        """Valid trace displayed as text."""
        traces_dir = tmp_path / ".rlm" / "traces"
        traces_dir.mkdir(parents=True)
        trace_file = traces_dir / "run-123.json"
        trace_file.write_text(
            json.dumps(
                {
                    "status": "success",
                    "iterations": 3,
                    "history": [
                        ["action1", "output1"],
                        ["action2", "output2"],
                    ],
                }
            )
        )

        args = argparse.Namespace(
            run_id="run-123",
            format="text",
        )

        # Patch Path so .rlm resolves to tmp
        original_path = Path

        class PatchedPath(type(Path())):
            def __new__(cls, *args):
                p = original_path(*args)
                if str(p) == ".rlm":
                    return original_path(tmp_path / ".rlm")
                return p

        with patch(
            "rlm_toolkit.cli.commands.Path",
            side_effect=lambda *a: (
                Path(tmp_path / ".rlm") if a == (".rlm",) else Path(*a)
            ),
        ):
            result = trace_command(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "run-123" in captured.out

    def test_valid_trace_json(self, tmp_path, capsys):
        """Valid trace displayed as JSON."""
        traces_dir = tmp_path / ".rlm" / "traces"
        traces_dir.mkdir(parents=True)
        trace_file = traces_dir / "run-456.json"
        trace_data = {
            "status": "success",
            "iterations": 2,
            "history": [],
        }
        trace_file.write_text(json.dumps(trace_data))

        args = argparse.Namespace(
            run_id="run-456",
            format="json",
        )

        with patch(
            "rlm_toolkit.cli.commands.Path",
            side_effect=lambda *a: (
                Path(tmp_path / ".rlm") if a == (".rlm",) else Path(*a)
            ),
        ):
            result = trace_command(args)

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "success"
