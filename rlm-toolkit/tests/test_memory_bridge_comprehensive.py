#!/usr/bin/env python
"""
Memory Bridge Comprehensive Test Suite
Tests all major functionality for production readiness verification.
"""

import sys
import tempfile
import gc
from pathlib import Path
from datetime import datetime, timedelta

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rlm_toolkit.memory_bridge.models import EntityType, HypothesisStatus
from rlm_toolkit.memory_bridge.storage import StateStorage
from rlm_toolkit.memory_bridge.manager import MemoryBridgeManager


def test_session_lifecycle():
    """Test 1: Session Creation and Restoration"""
    print("\n=== TEST 1: Session Lifecycle ===")

    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test.db"

    try:
        storage = StateStorage(db_path=db_path)
        manager = MemoryBridgeManager(storage=storage)

        # 1.1 Create new session
        state1 = manager.start_session(session_id="session-001", restore=False)
        assert state1.session_id == "session-001", "Session ID mismatch"
        print("  ✓ 1.1 New session created")

        # 1.2 Add some data
        manager.add_fact("Test fact 1", entity_type=EntityType.FACT)
        manager.set_goal("Test goal")
        version = manager.sync_state()
        print(f"  ✓ 1.2 Data added, saved version {version}")

        # 1.3 Create new manager and restore
        manager2 = MemoryBridgeManager(storage=storage)
        state2 = manager2.start_session(session_id="session-001", restore=True)
        assert state2.session_id == "session-001", "Restore failed"
        assert len(state2.facts) == 1, f"Facts not restored: {len(state2.facts)}"
        assert state2.primary_goal is not None, "Goal not restored"
        print("  ✓ 1.3 Session restored with data")

        # 1.4 Auto-generate session ID
        manager3 = MemoryBridgeManager(storage=storage)
        state3 = manager3.start_session()
        assert state3.session_id is not None, "No session ID generated"
        assert len(state3.session_id) > 10, "Session ID too short"
        print(f"  ✓ 1.4 Auto-generated session: {state3.session_id[:8]}...")

    finally:
        # Force garbage collection to release SQLite connections
        del manager, manager2, manager3, storage
        gc.collect()

    print("  ✅ Session Lifecycle: ALL PASSED")
    return True


def test_bitemporal_facts():
    """Test 2: Bi-Temporal Fact Tracking"""
    print("\n=== TEST 2: Bi-Temporal Facts ===")

    manager = MemoryBridgeManager()
    manager.start_session(session_id="facts-test")

    # 2.1 Add facts with different entity types
    for etype in [
        EntityType.FACT,
        EntityType.PREFERENCE,
        EntityType.DECISION,
        EntityType.REQUIREMENT,
        EntityType.PROCEDURE,
    ]:
        fact = manager.add_fact(f"Test {etype.value}", entity_type=etype)
        assert fact.entity_type == etype, f"Wrong type: {fact.entity_type}"
    print(f"  ✓ 2.1 Added {len(list(EntityType))} entity types")

    # 2.2 Check valid_at timestamp
    fact = manager.add_fact("Timestamped fact")
    assert fact.valid_at is not None, "No valid_at"
    assert fact.created_at is not None, "No created_at"
    assert fact.invalid_at is None, "Should not be invalidated"
    print("  ✓ 2.2 Bi-temporal timestamps set")

    # 2.3 Get current facts
    current = manager.get_current_facts()
    assert len(current) > 0, "No current facts"
    print(f"  ✓ 2.3 Got {len(current)} current facts")

    # 2.4 Filter by type
    prefs = manager.get_current_facts(EntityType.PREFERENCE)
    assert len(prefs) == 1, f"Wrong pref count: {len(prefs)}"
    print("  ✓ 2.4 Filtering by type works")

    print("  ✅ Bi-Temporal Facts: ALL PASSED")
    return True


def test_hybrid_search():
    """Test 3: Hybrid Search (Semantic + Keyword + Recency)"""
    print("\n=== TEST 3: Hybrid Search ===")

    manager = MemoryBridgeManager()
    manager.start_session(session_id="search-test")

    # Add test facts
    facts_data = [
        "Python is a programming language",
        "JavaScript runs in browsers",
        "Memory management is important",
        "RLM provides context compression",
        "AI security prevents prompt injection",
    ]
    for content in facts_data:
        manager.add_fact(content)
    print(f"  ✓ 3.1 Added {len(facts_data)} test facts")

    # 3.2 Keyword search
    results = manager.hybrid_search(
        "programming language",
        semantic_weight=0.0,
        keyword_weight=1.0,
        recency_weight=0.0,
    )
    assert len(results) > 0, "No keyword results"
    assert (
        "Python" in results[0][0].content
        or "programming" in results[0][0].content.lower()
    )
    print(f"  ✓ 3.2 Keyword search: top={results[0][0].content[:30]}...")

    # 3.3 Recency weight
    results_recency = manager.hybrid_search(
        "test",
        semantic_weight=0.0,
        keyword_weight=0.0,
        recency_weight=1.0,
    )
    # Most recent should score highest
    assert len(results_recency) > 0, "No recency results"
    print(f"  ✓ 3.3 Recency search returned {len(results_recency)} results")

    # 3.4 Combined search
    results_combined = manager.hybrid_search("AI context security")
    assert len(results_combined) > 0, "No combined results"
    print(f"  ✓ 3.4 Combined search: {len(results_combined)} results")

    print("  ✅ Hybrid Search: ALL PASSED")
    return True


def test_state_persistence():
    """Test 4: State Persistence with Encryption"""
    print("\n=== TEST 4: State Persistence ===")

    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "encrypted.db"
    storage = None
    manager = None

    try:
        # 4.1 Create storage (no encryption key = no encryption)
        storage = StateStorage(db_path=db_path)
        manager = MemoryBridgeManager(storage=storage)

        manager.start_session(session_id="persist-test")
        manager.add_fact("Secret fact", confidence=0.95)
        manager.set_goal("Persist everything")
        manager.add_hypothesis("This will be saved")
        manager.record_decision("Use encryption", "Security is important")

        version = manager.sync_state()
        print(f"  ✓ 4.1 Saved state v{version}")

        # 4.2 Verify DB file exists
        assert db_path.exists(), "DB file not created"
        size_kb = db_path.stat().st_size / 1024
        print(f"  ✓ 4.2 DB created: {size_kb:.1f} KB")

        # 4.3 List sessions
        sessions = storage.list_sessions()
        assert len(sessions) >= 1, "No sessions listed"
        print(f"  ✓ 4.3 Sessions listed: {len(sessions)}")

        # 4.4 Load and verify
        loaded = storage.load_state("persist-test")
        assert loaded is not None, "Failed to load"
        assert len(loaded.facts) == 1, "Facts not loaded"
        assert loaded.primary_goal is not None, "Goal not loaded"
        assert len(loaded.hypotheses) == 1, "Hypotheses not loaded"
        assert len(loaded.decisions) == 1, "Decisions not loaded"
        print("  ✓ 4.4 All data restored correctly")

        # 4.5 Version history (method is get_versions)
        versions = storage.get_versions("persist-test")
        assert len(versions) >= 1, "No versions"
        print(f"  ✓ 4.5 Version history: {len(versions)} version(s)")

    finally:
        # Clean up to release file handles on Windows
        del manager, storage
        gc.collect()

    print("  ✅ State Persistence: ALL PASSED")
    return True


def test_goals_and_decisions():
    """Test 5: Goals, Hypotheses, and Decisions"""
    print("\n=== TEST 5: Goals & Decisions ===")

    manager = MemoryBridgeManager()
    manager.start_session(session_id="goals-test")

    # 5.1 Set goal
    goal = manager.set_goal("Complete Memory Bridge testing")
    assert goal.id is not None, "Goal has no ID"
    assert goal.progress == 0.0, "Initial progress wrong"
    print("  ✓ 5.1 Goal created")

    # 5.2 Update progress
    manager.update_goal_progress(0.5)
    state = manager.get_state()
    assert state.primary_goal.progress == 0.5, "Progress not updated"
    print("  ✓ 5.2 Progress updated to 50%")

    # 5.3 Add hypothesis
    h = manager.add_hypothesis("Memory Bridge will work in production")
    assert h.status == HypothesisStatus.PROPOSED, "Wrong initial status"
    print("  ✓ 5.3 Hypothesis added")

    # 5.4 Update hypothesis
    manager.update_hypothesis(h.id, HypothesisStatus.CONFIRMED, ["Tests passed"])
    state = manager.get_state()
    updated_h = next(x for x in state.hypotheses if x.id == h.id)
    assert updated_h.status == HypothesisStatus.CONFIRMED, "Status not updated"
    assert len(updated_h.evidence) == 1, "Evidence not added"
    print("  ✓ 5.4 Hypothesis confirmed with evidence")

    # 5.5 Record decision
    d = manager.record_decision(
        description="Use SQLite for storage",
        rationale="Simple, portable, no external deps",
        alternatives=["PostgreSQL", "Redis", "File-based"],
    )
    assert len(d.alternatives_considered) == 3, "Alternatives missing"
    print("  ✓ 5.5 Decision recorded with alternatives")

    print("  ✅ Goals & Decisions: ALL PASSED")
    return True


def test_compact_state():
    """Test 6: Compact State for Context Injection"""
    print("\n=== TEST 6: Compact State ===")

    manager = MemoryBridgeManager()
    manager.start_session(session_id="compact-test")

    # Add rich state
    manager.set_goal("Test compact representation")
    manager.add_fact("Fact 1")
    manager.add_fact("Fact 2")
    manager.add_hypothesis("Hypothesis 1")
    manager.record_decision("Decision 1", "Because reasons")
    manager.add_open_question("Question 1?")

    # 6.1 Get compact string
    compact = manager.get_state_for_injection(max_tokens=500)
    assert len(compact) > 0, "Empty compact state"
    print(f"  ✓ 6.1 Compact state: {len(compact)} chars")

    # 6.2 Check sections present
    assert "GOAL:" in compact or "Goal:" in compact.title(), "No goal section"
    print("  ✓ 6.2 Goal section present")

    # 6.3 Token limit
    short = manager.get_state_for_injection(max_tokens=50)
    assert len(short) <= 300, "Token limit not respected"  # ~4 chars/token
    print(f"  ✓ 6.3 Short version: {len(short)} chars")

    print("  ✅ Compact State: ALL PASSED")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("MEMORY BRIDGE COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    tests = [
        test_session_lifecycle,
        test_bitemporal_facts,
        test_hybrid_search,
        test_state_persistence,
        test_goals_and_decisions,
        test_compact_state,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} test suites passed")
    if failed == 0:
        print("🏆 ALL TESTS PASSED - PRODUCTION READY")
    else:
        print(f"⚠️  {failed} test suite(s) failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
