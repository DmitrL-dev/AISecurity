# Memory Bridge E2E Verification Script
"""
Tests the complete Memory Bridge workflow end-to-end.
Run from project root: python -m rlm_toolkit.memory_bridge.tests.e2e_verification
"""

from rlm_toolkit.memory_bridge import (
    MemoryBridgeManager,
    StateStorage,
    EntityType,
    HypothesisStatus,
)
import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

# Ensure we can import from project
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class E2EVerification:
    """End-to-end verification of Memory Bridge workflow."""

    def __init__(self):
        self.results = []
        self.temp_dir = None

    def log(self, test_name: str, passed: bool, details: str = ""):
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append((test_name, passed, details))
        print(f"{status} | {test_name}")
        if details and not passed:
            print(f"       └─ {details}")

    def run_all(self):
        """Run all E2E tests."""
        print("\n" + "=" * 60)
        print("🔬 Memory Bridge E2E Verification")
        print("=" * 60 + "\n")

        # Create temp directory for test database
        self.temp_dir = tempfile.mkdtemp(prefix="memory_bridge_e2e_")
        db_path = Path(self.temp_dir) / "test.db"

        try:
            # Test 1: Full Session Lifecycle
            self._test_session_lifecycle(db_path)

            # Test 2: State Persistence Across Sessions
            self._test_cross_session_persistence(db_path)

            # Test 3: Bi-Temporal Fact Model
            self._test_bitemporal_facts(db_path)

            # Test 4: Hybrid Search
            self._test_hybrid_search(db_path)

            # Test 5: Encryption
            self._test_encryption(db_path)

            # Test 6: MCP Tools Integration
            self._test_mcp_tools(db_path)

            # Test 7: Context Injection
            self._test_context_injection(db_path)

            # Test 8: Performance Baseline
            self._test_performance(db_path)

        finally:
            # Cleanup
            import shutil
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass

        # Summary
        self._print_summary()

    def _test_session_lifecycle(self, db_path: Path):
        """Test complete session lifecycle."""
        storage = StateStorage(db_path=db_path)
        manager = MemoryBridgeManager(storage=storage)

        try:
            # Start session
            state = manager.start_session(session_id="e2e-lifecycle")
            assert state.session_id == "e2e-lifecycle"

            # Set goal
            goal = manager.set_goal("Complete E2E verification")
            assert goal.description == "Complete E2E verification"

            # Add hypothesis
            h = manager.add_hypothesis("Memory Bridge works correctly")
            assert h.status == HypothesisStatus.PROPOSED

            # Update hypothesis
            manager.update_hypothesis(
                h.id, HypothesisStatus.CONFIRMED, ["E2E tests pass"])

            # Record decision
            d = manager.record_decision(
                "Use SQLite for storage",
                "Local-first, no external dependencies",
                ["PostgreSQL", "Redis"],
            )
            assert len(d.alternatives_considered) == 2

            # Sync state
            version = manager.sync_state()
            assert version == 1

            self.log("Session Lifecycle", True)

        except Exception as e:
            self.log("Session Lifecycle", False, str(e))

    def _test_cross_session_persistence(self, db_path: Path):
        """Test that state persists across manager instances."""
        try:
            # First session
            storage1 = StateStorage(db_path=db_path)
            manager1 = MemoryBridgeManager(storage=storage1)
            state1 = manager1.start_session(session_id="persist-test")
            manager1.set_goal("Cross-session persistence test")
            manager1.add_fact("User preference: dark mode",
                              EntityType.PREFERENCE)
            manager1.sync_state()

            # Second session (new manager instance)
            storage2 = StateStorage(db_path=db_path)
            manager2 = MemoryBridgeManager(storage=storage2)
            state2 = manager2.start_session(
                session_id="persist-test", restore=True)

            # Verify persistence
            assert state2.primary_goal is not None
            assert state2.primary_goal.description == "Cross-session persistence test"
            assert len(state2.facts) == 1
            assert state2.facts[0].content == "User preference: dark mode"

            self.log("Cross-Session Persistence", True)

        except Exception as e:
            self.log("Cross-Session Persistence", False, str(e))

    def _test_bitemporal_facts(self, db_path: Path):
        """Test bi-temporal fact model with valid_at/invalid_at."""
        try:
            storage = StateStorage(db_path=db_path)
            manager = MemoryBridgeManager(storage=storage)
            manager.start_session(session_id="bitemporal-test")

            # Add facts with different entity types
            f1 = manager.add_fact("Python 3.12 is used",
                                  EntityType.REQUIREMENT)
            f2 = manager.add_fact("User prefers VS Code",
                                  EntityType.PREFERENCE)
            f3 = manager.add_fact("Deploy to AWS", EntityType.DECISION)

            # All facts should be current
            current = manager.get_current_facts()
            assert len(current) == 3

            # Filter by entity type
            prefs = manager.get_current_facts(EntityType.PREFERENCE)
            assert len(prefs) == 1
            assert prefs[0].content == "User prefers VS Code"

            # Check is_current
            assert f1.is_current()
            assert f2.is_current()

            self.log("Bi-Temporal Facts", True)

        except Exception as e:
            self.log("Bi-Temporal Facts", False, str(e))

    def _test_hybrid_search(self, db_path: Path):
        """Test hybrid search functionality."""
        try:
            storage = StateStorage(db_path=db_path)
            manager = MemoryBridgeManager(storage=storage)
            manager.start_session(session_id="search-test")

            # Add searchable facts
            manager.add_fact(
                "SQLite is a lightweight database", EntityType.FACT)
            manager.add_fact("PostgreSQL is a powerful RDBMS", EntityType.FACT)
            manager.add_fact("Redis is an in-memory cache", EntityType.FACT)

            # Search (keyword-based without embeddings)
            results = manager.hybrid_search("SQLite database", top_k=3)

            # Should find results
            assert len(results) > 0
            # First result should be SQLite-related
            assert "SQLite" in results[0][0].content

            self.log("Hybrid Search", True)

        except Exception as e:
            self.log("Hybrid Search", False, str(e))

    def _test_encryption(self, db_path: Path):
        """Test encryption of stored data."""
        import sqlite3

        try:
            encrypted_db = Path(self.temp_dir) / "encrypted.db"

            # Create storage with encryption
            storage = StateStorage(
                db_path=encrypted_db,
                encryption_key="test_secret_key_123",
            )
            manager = MemoryBridgeManager(storage=storage)
            manager.start_session(session_id="encrypted-session")
            manager.add_fact("SENSITIVE_DATA_12345", EntityType.FACT)
            manager.sync_state()

            # Read raw database directly
            with sqlite3.connect(encrypted_db) as conn:
                cursor = conn.execute("SELECT data FROM states")
                raw_data = cursor.fetchone()[0]

            # Plaintext should NOT be visible in raw data
            assert b"SENSITIVE_DATA_12345" not in raw_data

            self.log("Encryption", True)

        except Exception as e:
            self.log("Encryption", False, str(e))

    def _test_mcp_tools(self, db_path: Path):
        """Test MCP tool registration and execution."""
        try:
            from rlm_toolkit.memory_bridge import register_memory_bridge_tools

            # Create mock server
            class MockServer:
                def __init__(self):
                    self.tools = {}

                def tool(self, name, description):
                    def decorator(func):
                        self.tools[name] = func
                        return func
                    return decorator

            mock_server = MockServer()
            storage = StateStorage(db_path=db_path)
            manager = MemoryBridgeManager(storage=storage)
            manager.start_session(session_id="mcp-test")

            register_memory_bridge_tools(mock_server, manager)

            # Verify tools registered
            expected_tools = [
                "rlm_sync_state",
                "rlm_restore_state",
                "rlm_get_state",
                "rlm_update_goals",
                "rlm_record_decision",
                "rlm_add_hypothesis",
                "rlm_add_fact",
                "rlm_search_facts",
                "rlm_build_communities",
                "rlm_list_sessions",
            ]

            for tool_name in expected_tools:
                assert tool_name in mock_server.tools, f"Missing: {tool_name}"

            self.log("MCP Tools Registration", True,
                     f"{len(expected_tools)} tools")

        except Exception as e:
            self.log("MCP Tools Registration", False, str(e))

    def _test_context_injection(self, db_path: Path):
        """Test context injection output."""
        try:
            storage = StateStorage(db_path=db_path)
            manager = MemoryBridgeManager(storage=storage)
            manager.start_session(session_id="injection-test")

            manager.set_goal("Build Memory Bridge")
            manager.add_fact("Using SQLite for storage", EntityType.DECISION)
            manager.add_hypothesis("Performance will be acceptable")
            manager.add_open_question("Should we add Redis caching?")

            # Get compact injection
            injection = manager.get_state_for_injection(max_tokens=500)

            # Should contain key elements
            assert "Memory Bridge" in injection or "Goal:" in injection
            assert len(injection) > 50  # Non-trivial output

            self.log("Context Injection", True, f"{len(injection)} chars")

        except Exception as e:
            self.log("Context Injection", False, str(e))

    def _test_performance(self, db_path: Path):
        """Test baseline performance."""
        try:
            storage = StateStorage(db_path=db_path)
            manager = MemoryBridgeManager(storage=storage)
            manager.start_session(session_id="perf-test")

            # Measure fact addition
            start = time.perf_counter()
            for i in range(100):
                manager.add_fact(f"Performance test fact {i}", EntityType.FACT)
            fact_time = time.perf_counter() - start

            # Measure sync
            start = time.perf_counter()
            manager.sync_state()
            sync_time = time.perf_counter() - start

            # Measure search
            start = time.perf_counter()
            manager.hybrid_search("test fact", top_k=10)
            search_time = time.perf_counter() - start

            # Performance thresholds (relaxed for Windows I/O)
            assert fact_time < 2.0, f"Facts too slow: {fact_time:.2f}s"
            assert sync_time < 2.0, f"Sync too slow: {sync_time:.2f}s"
            assert search_time < 0.5, f"Search too slow: {search_time:.2f}s"

            self.log("Performance", True,
                     f"facts={fact_time*1000:.0f}ms, sync={sync_time*1000:.0f}ms, search={search_time*1000:.0f}ms")

        except Exception as e:
            self.log("Performance", False, str(e))

    def _print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        passed = sum(1 for _, p, _ in self.results if p)
        total = len(self.results)

        if passed == total:
            print(f"🎉 E2E VERIFICATION PASSED: {passed}/{total} tests")
        else:
            print(f"⚠️ E2E VERIFICATION: {passed}/{total} tests passed")
            print("\nFailed tests:")
            for name, p, details in self.results:
                if not p:
                    print(f"  - {name}: {details}")

        print("=" * 60 + "\n")


if __name__ == "__main__":
    verifier = E2EVerification()
    verifier.run_all()
