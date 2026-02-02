"""Quick test for discover_deep performance."""
from pathlib import Path
from rlm_mcp_server.extractors import ExtractionOrchestrator
import asyncio
import time
import sys
sys.path.insert(0, "src")


async def test():
    print("Starting discover_deep test...")
    start = time.time()

    orchestrator = ExtractionOrchestrator(
        Path(r"C:/AISecurity/sentinel-community")
    )

    result = await orchestrator.discover_deep(max_facts=5)

    elapsed = time.time() - start
    candidates = result.get("candidates", [])

    print(f"Completed in {elapsed:.1f}s")
    print(f"Found {len(candidates)} candidates")

    # Show extractor timings
    for ext_result in result.get("extractor_results", []):
        print(f"  - {ext_result['source']}: {ext_result['duration_ms']:.0f}ms")


if __name__ == "__main__":
    asyncio.run(test())
