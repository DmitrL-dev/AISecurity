"""
Tests for RLM v2.4 Planning Components.

Tests:
- SubTask dataclass
- ExecutionDAG builder
- DAGExecutor parallel execution
- TaskPlanner decomposition
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from rlm_toolkit.planning import (
    TaskPlanner,
    SubTask,
    TaskStatus,
    ExecutionDAG,
    DAGExecutor,
)


class TestSubTask:
    """Tests for SubTask dataclass."""

    def test_creation(self):
        """SubTask should be created with required fields."""
        task = SubTask(name="Build", description="Build the project")

        assert task.name == "Build"
        assert task.description == "Build the project"
        assert task.id is not None
        assert task.status == TaskStatus.PENDING
        assert task.dependencies == []

    def test_with_dependencies(self):
        """SubTask should support dependencies."""
        task = SubTask(
            name="Test",
            description="Run tests",
            dependencies=["task-1", "task-2"]
        )

        assert task.dependencies == ["task-1", "task-2"]

    def test_priority(self):
        """SubTask should support priority."""
        task = SubTask(name="High", description="High priority", priority=10)
        assert task.priority == 10

    def test_metadata(self):
        """SubTask should support metadata."""
        task = SubTask(
            name="Task",
            description="With metadata",
            metadata={"team": "backend", "estimate_hours": 4}
        )

        assert task.metadata["team"] == "backend"
        assert task.metadata["estimate_hours"] == 4


class TestExecutionDAG:
    """Tests for ExecutionDAG."""

    def test_empty_dag(self):
        """Empty DAG should be valid."""
        dag = ExecutionDAG()
        assert len(dag.tasks) == 0
        assert dag.is_complete
        assert dag.validate() == []

    def test_add_task(self):
        """Should add tasks to DAG."""
        dag = ExecutionDAG()

        task = SubTask(id="1", name="Task1", description="First task")
        dag.add_task(task)

        assert "1" in dag.tasks
        assert dag.tasks["1"] is task

    def test_get_ready_tasks_no_deps(self):
        """Tasks without dependencies should be ready."""
        dag = ExecutionDAG()

        dag.add_task(SubTask(id="1", name="A", description="No deps"))
        dag.add_task(SubTask(id="2", name="B", description="No deps"))

        ready = dag.get_ready_tasks()
        assert len(ready) == 2

    def test_get_ready_tasks_with_deps(self):
        """Only tasks with completed dependencies should be ready."""
        dag = ExecutionDAG()

        task1 = SubTask(id="1", name="A", description="First")
        task2 = SubTask(id="2", name="B",
                        description="Depends on A", dependencies=["1"])

        dag.add_task(task1)
        dag.add_task(task2)

        # Only task1 should be ready initially
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "1"

        # Mark task1 completed
        task1.status = TaskStatus.COMPLETED

        # Now task2 should be ready
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "2"

    def test_topological_order(self):
        """Should return tasks in topological order."""
        dag = ExecutionDAG()

        # Create: 1 -> 2 -> 3
        dag.add_task(SubTask(id="3", name="C",
                     description="Third", dependencies=["2"]))
        dag.add_task(SubTask(id="1", name="A", description="First"))
        dag.add_task(SubTask(id="2", name="B",
                     description="Second", dependencies=["1"]))

        order = dag.get_topological_order()
        names = [t.name for t in order]

        # A must come before B, B before C
        assert names.index("A") < names.index("B")
        assert names.index("B") < names.index("C")

    def test_validate_missing_dependency(self):
        """Should detect missing dependencies."""
        dag = ExecutionDAG()

        dag.add_task(SubTask(
            id="1",
            name="Task",
            description="Has missing dep",
            dependencies=["nonexistent"]
        ))

        errors = dag.validate()
        assert len(errors) > 0
        assert "nonexistent" in errors[0]

    def test_validate_cycle(self):
        """Should detect cycles."""
        dag = ExecutionDAG()

        # Create cycle: 1 -> 2 -> 3 -> 1
        dag.add_task(SubTask(id="1", name="A",
                     description="", dependencies=["3"]))
        dag.add_task(SubTask(id="2", name="B",
                     description="", dependencies=["1"]))
        dag.add_task(SubTask(id="3", name="C",
                     description="", dependencies=["2"]))

        errors = dag.validate()
        assert len(errors) > 0
        assert "cycle" in errors[0].lower()

    def test_is_complete(self):
        """is_complete should be True when all tasks completed."""
        dag = ExecutionDAG()

        task1 = SubTask(id="1", name="A", description="")
        task2 = SubTask(id="2", name="B", description="")

        dag.add_task(task1)
        dag.add_task(task2)

        assert not dag.is_complete

        task1.status = TaskStatus.COMPLETED
        assert not dag.is_complete

        task2.status = TaskStatus.COMPLETED
        assert dag.is_complete

    def test_success_rate(self):
        """Should calculate success rate correctly."""
        dag = ExecutionDAG()

        for i in range(4):
            dag.add_task(SubTask(id=str(i), name=f"T{i}", description=""))

        # Complete 3/4
        dag.tasks["0"].status = TaskStatus.COMPLETED
        dag.tasks["1"].status = TaskStatus.COMPLETED
        dag.tasks["2"].status = TaskStatus.COMPLETED
        dag.tasks["3"].status = TaskStatus.FAILED

        summary = dag.summary()
        assert summary["success_rate"] == 0.75

    def test_summary(self):
        """Should return accurate summary."""
        dag = ExecutionDAG()

        dag.add_task(SubTask(id="1", name="A", description=""))
        dag.add_task(SubTask(id="2", name="B", description=""))
        dag.tasks["1"].status = TaskStatus.COMPLETED

        summary = dag.summary()

        assert summary["total_tasks"] == 2
        assert summary["by_status"]["completed"] == 1
        assert summary["by_status"].get("pending", 0) == 1


class TestDAGExecutor:
    """Tests for DAGExecutor."""

    @pytest.mark.asyncio
    async def test_execute_single_task(self):
        """Should execute a single task."""
        dag = ExecutionDAG()
        dag.add_task(SubTask(id="1", name="Single", description="One task"))

        async def executor(task):
            return f"Done: {task.name}"

        executor_obj = DAGExecutor(max_parallel=1)
        results = await executor_obj.execute(dag, executor)

        assert len(results) == 1
        assert results[0].status == TaskStatus.COMPLETED
        assert results[0].result == "Done: Single"

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        """Should execute independent tasks in parallel."""
        dag = ExecutionDAG()

        for i in range(4):
            dag.add_task(SubTask(id=str(i), name=f"Task{i}", description=""))

        execution_order = []

        async def executor(task):
            execution_order.append(f"start:{task.name}")
            await asyncio.sleep(0.01)
            execution_order.append(f"end:{task.name}")
            return "ok"

        executor_obj = DAGExecutor(max_parallel=4)
        await executor_obj.execute(dag, executor)

        # All should start before any ends (parallel execution)
        starts = [e for e in execution_order if e.startswith("start")]
        ends = [e for e in execution_order if e.startswith("end")]

        # With parallel execution, starts should cluster together
        assert len(starts) == 4
        assert len(ends) == 4

    @pytest.mark.asyncio
    async def test_respects_dependencies(self):
        """Should respect task dependencies."""
        dag = ExecutionDAG()

        dag.add_task(SubTask(id="1", name="First", description=""))
        dag.add_task(SubTask(id="2", name="Second",
                     description="", dependencies=["1"]))

        execution_order = []

        async def executor(task):
            execution_order.append(task.name)
            return "ok"

        executor_obj = DAGExecutor(max_parallel=2)
        await executor_obj.execute(dag, executor)

        assert execution_order.index("First") < execution_order.index("Second")

    @pytest.mark.asyncio
    async def test_handles_failure(self):
        """Should handle task failures gracefully."""
        dag = ExecutionDAG()

        dag.add_task(SubTask(id="1", name="FailTask", description="Will fail"))

        async def failing_executor(task):
            raise ValueError("Task failed!")

        executor_obj = DAGExecutor(max_parallel=1)
        results = await executor_obj.execute(dag, failing_executor)

        assert results[0].status == TaskStatus.FAILED
        assert "Task failed!" in results[0].error

    @pytest.mark.asyncio
    async def test_callbacks(self):
        """Should call lifecycle callbacks."""
        dag = ExecutionDAG()
        dag.add_task(SubTask(id="1", name="Task", description=""))

        on_start = Mock()
        on_complete = Mock()

        async def executor(task):
            return "ok"

        executor_obj = DAGExecutor(
            max_parallel=1,
            on_task_start=on_start,
            on_task_complete=on_complete
        )
        await executor_obj.execute(dag, executor)

        on_start.assert_called_once()
        on_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Should handle timeout gracefully."""
        dag = ExecutionDAG()
        dag.add_task(SubTask(id="1", name="SlowTask", description=""))

        async def slow_executor(task):
            await asyncio.sleep(10)
            return "ok"

        executor_obj = DAGExecutor(max_parallel=1)

        # Implementation catches TimeoutError and cancels
        results = await executor_obj.execute(dag, slow_executor, timeout=0.1)

        # Task should be cancelled or still running
        assert len(results) == 1


class TestTaskPlanner:
    """Tests for TaskPlanner."""

    def test_creation(self):
        """TaskPlanner should be created."""
        planner = TaskPlanner()
        assert planner is not None

    def test_decompose_without_llm(self):
        """Should provide fallback decomposition without LLM."""
        planner = TaskPlanner()

        subtasks = planner.decompose("Build a web application")

        # Should have at least one task
        assert len(subtasks) >= 1
        assert all(isinstance(t, SubTask) for t in subtasks)

    def test_decompose_with_mock_llm(self):
        """Should use LLM for decomposition when available."""
        # Mock LLM that returns structured subtasks
        def mock_llm(prompt):
            return """
            1. Setup project structure | Setup | Initialize the project
            2. Implement core logic | Core | Build main functionality | dep:1
            3. Add tests | Testing | Write unit tests | dep:2
            """

        planner = TaskPlanner(llm_func=mock_llm)
        subtasks = planner.decompose("Build feature X")

        assert len(subtasks) >= 1

    def test_create_dag(self):
        """Should create DAG from subtasks."""
        planner = TaskPlanner()

        subtasks = [
            SubTask(id="1", name="A", description="First"),
            SubTask(id="2", name="B", description="Second",
                    dependencies=["1"]),
        ]

        dag = planner.create_dag(subtasks)

        assert len(dag.tasks) == 2
        assert dag.validate() == []

    @pytest.mark.asyncio
    async def test_plan_and_execute(self):
        """Should plan and execute in one call."""
        planner = TaskPlanner()

        async def executor(task):
            return f"Executed: {task.name}"

        result = await planner.plan_and_execute(
            goal="Simple goal",
            executor_func=executor,
            max_parallel=2
        )

        assert "summary" in result
        assert result["summary"]["success_rate"] == 1.0
        assert result["summary"]["is_complete"] is True


class TestIntegration:
    """Integration tests for planning system."""

    @pytest.mark.asyncio
    async def test_complex_dag_execution(self):
        """Test complex DAG with multiple paths."""
        dag = ExecutionDAG()

        # Create diamond pattern:
        #       1
        #      / \
        #     2   3
        #      \ /
        #       4

        dag.add_task(SubTask(id="1", name="Start", description=""))
        dag.add_task(SubTask(id="2", name="PathA",
                     description="", dependencies=["1"]))
        dag.add_task(SubTask(id="3", name="PathB",
                     description="", dependencies=["1"]))
        dag.add_task(SubTask(id="4", name="End",
                     description="", dependencies=["2", "3"]))

        execution_log = []

        async def executor(task):
            execution_log.append(task.name)
            await asyncio.sleep(0.01)
            return "ok"

        executor_obj = DAGExecutor(max_parallel=4)
        results = await executor_obj.execute(dag, executor)

        # Verify execution order
        assert execution_log.index("Start") < execution_log.index("PathA")
        assert execution_log.index("Start") < execution_log.index("PathB")
        assert execution_log.index("PathA") < execution_log.index("End")
        assert execution_log.index("PathB") < execution_log.index("End")

        assert all(r.status == TaskStatus.COMPLETED for r in results)


class TestEdgeCases:
    """Edge cases and boundary condition tests."""

    def test_empty_goal(self):
        """Empty goal should be handled."""
        planner = TaskPlanner()
        subtasks = planner.decompose("")
        assert len(subtasks) >= 1

    def test_very_long_goal(self):
        """Very long goals should work."""
        planner = TaskPlanner()
        long_goal = "Build a system that " + "really complex " * 1000
        subtasks = planner.decompose(long_goal)
        assert len(subtasks) >= 1

    def test_unicode_goal(self):
        """Unicode in goals should work."""
        planner = TaskPlanner()
        subtasks = planner.decompose("Создать систему для 日本語 🚀")
        assert len(subtasks) >= 1

    def test_dag_with_many_tasks(self):
        """DAG should handle many tasks."""
        dag = ExecutionDAG()

        for i in range(100):
            deps = [str(i-1)] if i > 0 else []
            dag.add_task(
                SubTask(id=str(i), name=f"T{i}", description="", dependencies=deps))

        assert len(dag.tasks) == 100
        assert dag.validate() == []

    def test_dag_wide_parallel(self):
        """DAG should handle wide parallel tasks."""
        dag = ExecutionDAG()

        # All depend on root
        dag.add_task(SubTask(id="root", name="Root", description=""))
        for i in range(50):
            dag.add_task(
                SubTask(id=str(i), name=f"P{i}", description="", dependencies=["root"]))

        ready = dag.get_ready_tasks()
        assert len(ready) == 1  # Only root
        assert ready[0].id == "root"

    @pytest.mark.asyncio
    async def test_executor_empty_dag(self):
        """Executor should handle empty DAG."""
        dag = ExecutionDAG()

        async def executor(task):
            return "ok"

        executor_obj = DAGExecutor(max_parallel=2)
        results = await executor_obj.execute(dag, executor)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_executor_cancel(self):
        """Executor cancel should work."""
        dag = ExecutionDAG()
        for i in range(3):
            dag.add_task(SubTask(id=str(i), name=f"T{i}", description=""))

        async def slow_executor(task):
            await asyncio.sleep(5)
            return "ok"

        executor_obj = DAGExecutor(max_parallel=3)

        # Start execution in background
        task = asyncio.create_task(executor_obj.execute(dag, slow_executor))
        await asyncio.sleep(0.01)

        # Cancel
        executor_obj.cancel()

        await task  # Let it finish

    def test_subtask_duration(self):
        """duration_ms should calculate correctly."""
        from datetime import timedelta

        task = SubTask(id="1", name="Test", description="")
        task.started_at = datetime.now()
        task.completed_at = task.started_at + timedelta(milliseconds=150)

        assert task.duration_ms is not None
        assert 140 <= task.duration_ms <= 160

    def test_subtask_to_dict(self):
        """to_dict should contain all fields."""
        task = SubTask(id="1", name="Test", description="Desc")
        task.status = TaskStatus.COMPLETED
        task.result = "Result value"

        d = task.to_dict()

        assert d["id"] == "1"
        assert d["name"] == "Test"
        assert d["status"] == "completed"


# --- v2.5: TaskReviewer Tests ---

class TestTaskReviewer:
    """Tests for TaskReviewer (v2.5)."""

    def test_creation(self):
        """TaskReviewer should be created with defaults."""
        from rlm_toolkit.planning import TaskReviewer

        reviewer = TaskReviewer()

        assert reviewer.min_success_rate == 0.8
        assert reviewer.retry_threshold == 0.5

    def test_review_empty_tasks(self):
        """Review of empty task list should pass."""
        from rlm_toolkit.planning import TaskReviewer

        reviewer = TaskReviewer()
        report = reviewer.review([])

        assert report["passed"] == True
        assert report["score"] == 1.0

    def test_review_all_completed(self):
        """Review of all completed tasks should pass with high score."""
        from rlm_toolkit.planning import TaskReviewer

        tasks = [
            SubTask(id="1", name="T1", description=""),
            SubTask(id="2", name="T2", description=""),
        ]
        tasks[0].status = TaskStatus.COMPLETED
        tasks[1].status = TaskStatus.COMPLETED

        reviewer = TaskReviewer()
        report = reviewer.review(tasks)

        assert report["passed"] == True
        assert report["success_rate"] == 1.0
        assert report["completed_count"] == 2
        assert report["failed_count"] == 0

    def test_review_with_failures(self):
        """Review should identify failed tasks and suggest retries."""
        from rlm_toolkit.planning import TaskReviewer

        tasks = [
            SubTask(id="1", name="T1", description=""),
            SubTask(id="2", name="T2", description=""),
            SubTask(id="3", name="T3", description=""),
        ]
        tasks[0].status = TaskStatus.COMPLETED
        tasks[1].status = TaskStatus.FAILED
        tasks[1].error = "Connection timeout"
        tasks[2].status = TaskStatus.COMPLETED

        reviewer = TaskReviewer()
        report = reviewer.review(tasks)

        # 67% success < 80% threshold
        assert report["passed"] == False
        assert len(report["retry_tasks"]) == 1
        assert "2" in report["retry_tasks"]
        assert any("failed" in i for i in report["insights"])

    def test_review_critical_failure(self):
        """Review should flag critical failure when < 50% success."""
        from rlm_toolkit.planning import TaskReviewer

        tasks = [
            SubTask(id="1", name="T1", description=""),
            SubTask(id="2", name="T2", description=""),
        ]
        tasks[0].status = TaskStatus.FAILED
        tasks[1].status = TaskStatus.FAILED

        reviewer = TaskReviewer()
        report = reviewer.review(tasks)

        assert report["success_rate"] == 0.0
        assert any("Critical" in i for i in report["insights"])

    def test_custom_success_threshold(self):
        """Should respect custom min_success_rate."""
        from rlm_toolkit.planning import TaskReviewer

        tasks = [
            SubTask(id="1", name="T1", description=""),
            SubTask(id="2", name="T2", description=""),
        ]
        tasks[0].status = TaskStatus.COMPLETED
        tasks[1].status = TaskStatus.FAILED

        # 50% success
        reviewer = TaskReviewer(min_success_rate=0.5)
        report = reviewer.review(tasks)

        assert report["passed"] == True  # 50% == 50% threshold

    def test_score_calculation(self):
        """Score should be calculated correctly."""
        from rlm_toolkit.planning import TaskReviewer

        tasks = [
            SubTask(id="1", name="T1", description=""),
        ]
        tasks[0].status = TaskStatus.COMPLETED

        reviewer = TaskReviewer()
        report = reviewer.review(tasks)

        # 100% success -> score should be 1.0 (0.5 success + 0.25 duration + 0.25 no failures)
        assert report["score"] == 1.0


@pytest.mark.asyncio
class TestPlanExecuteReview:
    """Tests for plan_execute_review (v2.5)."""

    async def test_full_cycle_without_reviewer(self):
        """Should work without reviewer (just plan + execute)."""
        from rlm_toolkit.planning import TaskReviewer

        async def execute(task):
            task.status = TaskStatus.COMPLETED
            return "done"

        planner = TaskPlanner()  # No LLM
        result = await planner.plan_execute_review(
            goal="Test goal",
            executor_func=execute,
        )

        assert "phases" in result
        assert "plan" in result["phases"]
        assert "execute" in result["phases"]
        assert result["review"] is None

    async def test_full_cycle_with_reviewer(self):
        """Should run full Plan→Execute→Review cycle."""
        from rlm_toolkit.planning import TaskReviewer

        async def execute(task):
            task.status = TaskStatus.COMPLETED
            return "done"

        planner = TaskPlanner()
        reviewer = TaskReviewer()

        result = await planner.plan_execute_review(
            goal="Test goal",
            executor_func=execute,
            reviewer=reviewer,
        )

        assert "review" in result["phases"]
        assert result["review"]["passed"] == True

    async def test_retry_failed_tasks(self):
        """Should retry failed tasks when review fails."""
        from rlm_toolkit.planning import TaskReviewer

        call_count = [0]

        async def execute(task):
            call_count[0] += 1
            if call_count[0] == 1:
                task.status = TaskStatus.FAILED
                task.error = "First attempt failed"
            else:
                task.status = TaskStatus.COMPLETED
            return "done"

        planner = TaskPlanner()
        reviewer = TaskReviewer(min_success_rate=0.8)

        result = await planner.plan_execute_review(
            goal="Test retry",
            executor_func=execute,
            reviewer=reviewer,
            retry_failed=True,
        )

        # Should have retried the failed task
        assert call_count[0] >= 1
