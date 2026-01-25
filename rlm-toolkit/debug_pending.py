"""Debug script for pending_store issue."""

import sys
import os
import asyncio
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(r"C:\AISecurity\sentinel-community\rlm-toolkit")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

print("=== STEP 1: Test pending_store import ===")
try:
    from rlm_mcp_server.pending_store import PendingCandidatesStore, PendingCandidate

    print("SUCCESS: pending_store imported")
except Exception as e:
    print(f"FAIL: {e}")
    import traceback

    traceback.print_exc()

print()
print("=== STEP 2: Test orchestrator import ===")
try:
    from rlm_mcp_server.extractors import ExtractionOrchestrator

    print("SUCCESS: ExtractionOrchestrator imported")
except Exception as e:
    print(f"FAIL: {e}")
    import traceback

    traceback.print_exc()

print()
print("=== STEP 3: Test discovery ===")


async def test_discovery():
    try:
        from rlm_mcp_server.extractors import ExtractionOrchestrator

        orch = ExtractionOrchestrator(PROJECT_ROOT)
        result = await orch.discover_deep(max_facts=10)
        print(f"Facts extracted: {result.get('facts_extracted', 0)}")
        print(f"Candidates count: {len(result.get('candidates', []))}")
        if result.get("candidates"):
            c = result["candidates"][0]
            print(f"First candidate confidence: {c.get('confidence')}")
            print(f"First candidate content: {c.get('content', '')[:100]}")
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback

        traceback.print_exc()


asyncio.run(test_discovery())

print()
print("=== STEP 4: Test pending_store creation ===")
try:
    pending_db = PROJECT_ROOT / ".rlm" / "pending_candidates.db"
    pending_db.parent.mkdir(parents=True, exist_ok=True)
    store = PendingCandidatesStore(pending_db)

    # Add test candidate
    test_candidate = PendingCandidate(
        id="test-123",
        content="Test fact content",
        source="test",
        confidence=0.7,
        domain="test-domain",
        level=1,
    )
    store.add(test_candidate)
    print(f"SUCCESS: Added test candidate")

    # Get pending
    pending = store.get_pending(limit=10)
    print(f"Pending count: {len(pending)}")

    # Stats
    stats = store.get_stats()
    print(f"Stats: {stats}")

    print(f"DB file exists: {pending_db.exists()}")
except Exception as e:
    print(f"FAIL: {e}")
    import traceback

    traceback.print_exc()
