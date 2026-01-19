"""
RLM-Toolkit Performance Benchmarks.

Measures:
- Crystal indexing speed
- Retrieval latency
- Memory usage
"""

import time
import sys
import os
import random
import string

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rlm_toolkit.crystal import HPEExtractor, CrystalIndexer
from rlm_toolkit.retrieval import EmbeddingRetriever


def generate_python_file(lines: int = 100) -> str:
    """Generate synthetic Python file."""
    content = []
    content.append('"""Auto-generated test module."""')
    content.append("import os")
    content.append("import sys")
    content.append("")

    # Add some classes
    for i in range(lines // 20):
        class_name = f"TestClass{i}"
        content.append(f"class {class_name}:")
        content.append(f'    """Class {i} docstring."""')
        content.append("    ")
        content.append(f"    def __init__(self):")
        content.append(f"        self.value = {i}")
        content.append("    ")
        content.append(f"    def method_{i}(self, arg):")
        content.append(f"        return self.value + arg")
        content.append("")

    # Add standalone functions
    for i in range(lines // 10):
        func_name = f"function_{i}"
        content.append(f"def {func_name}(x, y):")
        content.append(f'    """Function {i}."""')
        content.append(f"    return x + y + {i}")
        content.append("")

    return "\n".join(content[:lines])


def benchmark_indexing(n_files: int, lines_per_file: int = 100):
    """Benchmark crystal indexing."""
    print(f"\n📊 Benchmark: Indexing {n_files} files ({lines_per_file} lines each)")
    print("-" * 50)

    extractor = HPEExtractor()
    indexer = CrystalIndexer(use_embeddings=False)  # Disable embeddings for speed

    # Generate files
    files = []
    for i in range(n_files):
        content = generate_python_file(lines_per_file)
        files.append((f"/test/file_{i}.py", content))

    # Benchmark extraction
    start = time.perf_counter()
    crystals = []
    for path, content in files:
        crystal = extractor.extract_from_file(path, content)
        crystals.append(crystal)
    extract_time = time.perf_counter() - start

    # Benchmark indexing
    start = time.perf_counter()
    for crystal in crystals:
        indexer.index_file(crystal)
    index_time = time.perf_counter() - start

    total_time = extract_time + index_time
    total_primitives = sum(len(c.primitives) for c in crystals)

    print(f"✅ Extraction: {extract_time:.3f}s ({n_files/extract_time:.1f} files/s)")
    print(f"✅ Indexing:   {index_time:.3f}s ({n_files/index_time:.1f} files/s)")
    print(f"✅ Total:      {total_time:.3f}s")
    print(f"✅ Primitives: {total_primitives}")
    print(f"✅ Stats:      {indexer.get_stats()}")

    return {
        "files": n_files,
        "lines_per_file": lines_per_file,
        "extract_time": extract_time,
        "index_time": index_time,
        "total_time": total_time,
        "primitives": total_primitives,
        "files_per_sec": n_files / total_time,
    }


def benchmark_retrieval(n_docs: int):
    """Benchmark embedding retrieval."""
    print(f"\n📊 Benchmark: Retrieval from {n_docs} documents")
    print("-" * 50)

    retriever = EmbeddingRetriever(use_embeddings=False)  # Keyword fallback

    # Generate corpus
    corpus = [
        f"Document {i} about topic {i % 10} with content {i * 2}" for i in range(n_docs)
    ]

    # Benchmark indexing
    start = time.perf_counter()
    retriever.index(corpus)
    index_time = time.perf_counter() - start

    # Benchmark queries
    queries = ["topic 5", "Document 100", "content 42"]
    query_times = []

    for query in queries:
        start = time.perf_counter()
        results = retriever.search(query, top_k=10)
        query_time = time.perf_counter() - start
        query_times.append(query_time)

    avg_query_time = sum(query_times) / len(query_times)

    print(f"✅ Index time:     {index_time:.3f}s")
    print(f"✅ Avg query time: {avg_query_time*1000:.2f}ms")
    print(f"✅ Stats:          {retriever.get_stats()}")

    return {
        "docs": n_docs,
        "index_time": index_time,
        "avg_query_ms": avg_query_time * 1000,
    }


def run_all_benchmarks():
    """Run all benchmarks."""
    print("=" * 60)
    print("🚀 RLM-Toolkit Performance Benchmarks")
    print("=" * 60)

    results = {}

    # Indexing benchmarks
    for n_files in [100, 1000]:
        result = benchmark_indexing(n_files)
        results[f"index_{n_files}"] = result

    # Retrieval benchmarks
    for n_docs in [1000, 10000]:
        result = benchmark_retrieval(n_docs)
        results[f"retrieve_{n_docs}"] = result

    # Summary
    print("\n" + "=" * 60)
    print("📈 BENCHMARK SUMMARY")
    print("=" * 60)

    print("\n### Indexing Performance")
    for key, val in results.items():
        if key.startswith("index_"):
            print(f"  {val['files']} files: {val['files_per_sec']:.1f} files/sec")

    print("\n### Retrieval Latency")
    for key, val in results.items():
        if key.startswith("retrieve_"):
            print(f"  {val['docs']} docs: {val['avg_query_ms']:.2f}ms avg query")

    # Targets
    print("\n### Target Metrics")
    print("  ✅ 10K files indexing < 60s: ", end="")
    idx_1k = results.get("index_1000", {})
    if idx_1k and idx_1k.get("total_time", 999) * 10 < 60:
        print("PASS")
    else:
        print("NEEDS OPTIMIZATION")

    print("  ✅ Query latency < 100ms: ", end="")
    ret_10k = results.get("retrieve_10000", {})
    if ret_10k and ret_10k.get("avg_query_ms", 999) < 100:
        print("PASS")
    else:
        print("NEEDS OPTIMIZATION")

    return results


if __name__ == "__main__":
    run_all_benchmarks()
