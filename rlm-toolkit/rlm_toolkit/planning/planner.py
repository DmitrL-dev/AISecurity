"""
Task Planner with DAG Execution.

Implements goal decomposition and dependency-aware parallel execution.

Example:
    >>> planner = TaskPlanner(llm_func=llm.generate)
    >>> subtasks = planner.decompose("Build a web app with login")
    >>> dag = planner.create_dag(subtasks)
    >>> results = await planner.execute(dag, executor)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Awaitable

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class CleanupPolicy(Enum):
    """Task cleanup policy after completion.

    Inspired by OpenClaw's subagent-registry cleanup patterns.
    """
    DELETE = "delete"      # Remove immediately after completion
    KEEP = "keep"          # Keep permanently
    ARCHIVE = "archive"    # Move to archive after TTL expires


@dataclass
class SubTask:
    """A subtask in the execution plan.

    Attributes:
        id: Unique task identifier
        name: Human-readable name
        description: What this task does
        dependencies: IDs of tasks that must complete first
        priority: Execution priority (higher = first)
        metadata: Additional task data
    """
    name: str
    description: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Cleanup policies (OpenClaw-inspired)
    cleanup: CleanupPolicy = CleanupPolicy.ARCHIVE
    archive_after_seconds: int = 3600  # 1 hour TTL
    created_at: float = field(
        default_factory=lambda: datetime.now().timestamp())

    @property
    def duration_ms(self) -> Optional[float]:
        """Get task duration in milliseconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": str(self.result)[:100] if self.result else None,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ExecutionDAG:
    """Directed Acyclic Graph for task execution.

    Manages task dependencies and determines execution order.
    """
    tasks: Dict[str, SubTask] = field(default_factory=dict)

    def add_task(self, task: SubTask) -> None:
        """Add task to DAG."""
        self.tasks[task.id] = task

    def get_ready_tasks(self) -> List[SubTask]:
        """Get tasks ready to execute (all dependencies completed)."""
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue

            # Check all dependencies are completed
            deps_complete = all(
                self.tasks.get(dep_id, SubTask("", "")
                               ).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )

            if deps_complete:
                ready.append(task)

        # Sort by priority (higher first)
        return sorted(ready, key=lambda t: -t.priority)

    def get_topological_order(self) -> List[SubTask]:
        """Get tasks in topological order (respecting dependencies)."""
        visited = set()
        order = []

        def visit(task_id: str):
            if task_id in visited:
                return
            visited.add(task_id)

            task = self.tasks.get(task_id)
            if not task:
                return

            for dep_id in task.dependencies:
                visit(dep_id)

            order.append(task)

        for task_id in self.tasks:
            visit(task_id)

        return order

    def validate(self) -> List[str]:
        """Validate DAG for cycles and missing dependencies."""
        errors = []

        # Check for missing dependencies
        for task in self.tasks.values():
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    errors.append(
                        f"Task '{task.name}' has missing dependency: {dep_id}")

        # Check for cycles using DFS
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {t_id: WHITE for t_id in self.tasks}

        def has_cycle(task_id: str) -> bool:
            color[task_id] = GRAY
            task = self.tasks[task_id]
            for dep_id in task.dependencies:
                if dep_id in color:
                    if color[dep_id] == GRAY:
                        return True
                    if color[dep_id] == WHITE and has_cycle(dep_id):
                        return True
            color[task_id] = BLACK
            return False

        for task_id in self.tasks:
            if color[task_id] == WHITE and has_cycle(task_id):
                errors.append(
                    f"Cycle detected involving task: {self.tasks[task_id].name}")
                break

        return errors

    @property
    def is_complete(self) -> bool:
        """Check if all tasks are completed or failed."""
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED,
                         TaskStatus.SKIPPED, TaskStatus.CANCELLED)
            for t in self.tasks.values()
        )

    @property
    def success_rate(self) -> float:
        """Get success rate of completed tasks."""
        completed = [t for t in self.tasks.values() if t.status ==
                     TaskStatus.COMPLETED]
        total = [t for t in self.tasks.values() if t.status !=
                 TaskStatus.PENDING]
        if not total:
            return 0.0
        return len(completed) / len(total)

    def summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        by_status = {}
        for task in self.tasks.values():
            by_status[task.status.value] = by_status.get(
                task.status.value, 0) + 1

        return {
            "total_tasks": len(self.tasks),
            "by_status": by_status,
            "success_rate": self.success_rate,
            "is_complete": self.is_complete,
        }


# Type for executor function
Executor = Callable[[SubTask], Awaitable[Any]]


class DAGExecutor:
    """Executes tasks in a DAG with parallelism.

    Args:
        max_parallel: Maximum concurrent tasks
        on_task_start: Callback when task starts
        on_task_complete: Callback when task completes
        on_task_error: Callback when task fails
    """

    def __init__(
        self,
        max_parallel: int = 4,
        on_task_start: Optional[Callable[[SubTask], None]] = None,
        on_task_complete: Optional[Callable[[SubTask], None]] = None,
        on_task_error: Optional[Callable[[SubTask, Exception], None]] = None,
    ):
        self.max_parallel = max_parallel
        self.on_task_start = on_task_start
        self.on_task_complete = on_task_complete
        self.on_task_error = on_task_error
        self._cancelled = False

    async def execute(
        self,
        dag: ExecutionDAG,
        executor_func: Executor,
        timeout: Optional[float] = None
    ) -> List[SubTask]:
        """Execute all tasks in DAG.

        Args:
            dag: The DAG to execute
            executor_func: Async function to execute each task
            timeout: Total timeout in seconds

        Returns:
            List of completed/failed tasks
        """
        errors = dag.validate()
        if errors:
            raise ValueError(f"Invalid DAG: {errors}")

        self._cancelled = False
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def run_task(task: SubTask):
            async with semaphore:
                if self._cancelled:
                    task.status = TaskStatus.CANCELLED
                    return

                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()

                if self.on_task_start:
                    self.on_task_start(task)

                try:
                    task.result = await executor_func(task)
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now()

                    if self.on_task_complete:
                        self.on_task_complete(task)

                    logger.debug(f"Task completed: {task.name}")

                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = datetime.now()

                    if self.on_task_error:
                        self.on_task_error(task, e)

                    logger.error(f"Task failed: {task.name} - {e}")

        async def execution_loop():
            completed_ids: Set[str] = set()

            while not dag.is_complete and not self._cancelled:
                ready = dag.get_ready_tasks()

                if not ready:
                    # No ready tasks, wait a bit
                    await asyncio.sleep(0.01)
                    continue

                # Start all ready tasks
                tasks = [run_task(task) for task in ready]
                await asyncio.gather(*tasks, return_exceptions=True)

        try:
            if timeout:
                await asyncio.wait_for(execution_loop(), timeout=timeout)
            else:
                await execution_loop()
        except asyncio.TimeoutError:
            logger.warning("DAG execution timed out")
            self.cancel()

        return list(dag.tasks.values())

    def cancel(self) -> None:
        """Cancel execution."""
        self._cancelled = True


class TaskPlanner:
    """Decomposes goals into executable subtasks.

    Uses an LLM to break down complex goals into concrete steps
    with proper dependencies.

    Args:
        llm_func: Function that takes prompt and returns response
        prompt_template: Template for decomposition prompt

    Example:
        >>> planner = TaskPlanner(llm.generate)
        >>> subtasks = planner.decompose("Create a REST API")
        >>> dag = planner.create_dag(subtasks)
    """

    DEFAULT_PROMPT = """Decompose this goal into concrete subtasks:

GOAL: {goal}

Break down into 3-7 concrete, executable steps. For each step specify:
- name: Short task name
- description: What to do
- dependencies: Which steps must complete first (by number)

Respond in JSON format:
{{
    "subtasks": [
        {{"name": "Step 1 name", "description": "...", "dependencies": []}},
        {{"name": "Step 2 name", "description": "...", "dependencies": [0]}},
        ...
    ]
}}"""

    def __init__(
        self,
        llm_func: Optional[Callable[[str], str]] = None,
        prompt_template: Optional[str] = None
    ):
        self.llm_func = llm_func
        self.prompt_template = prompt_template or self.DEFAULT_PROMPT

    def decompose(self, goal: str) -> List[SubTask]:
        """Decompose goal into subtasks using LLM.

        Args:
            goal: The high-level goal to decompose

        Returns:
            List of SubTask objects
        """
        if not self.llm_func:
            # Fallback: create single task
            return [SubTask(name="Execute", description=goal)]

        prompt = self.prompt_template.format(goal=goal)

        try:
            response = self.llm_func(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.warning(f"Decomposition failed: {e}")
            return [SubTask(name="Execute", description=goal)]

    def _parse_response(self, response: str) -> List[SubTask]:
        """Parse LLM response to subtasks."""
        import json
        import re

        # Try to extract JSON
        json_match = re.search(
            r'\{[^{}]*"subtasks"[^{}]*\[.*?\]\s*\}', response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                subtasks_data = data.get("subtasks", [])
            except json.JSONDecodeError:
                subtasks_data = []
        else:
            subtasks_data = []

        # Convert to SubTask objects
        subtasks = []
        id_map = {}  # Map index to task ID

        for i, item in enumerate(subtasks_data):
            task = SubTask(
                name=item.get("name", f"Step {i+1}"),
                description=item.get("description", ""),
                priority=len(subtasks_data) - i,  # Earlier = higher priority
            )
            subtasks.append(task)
            id_map[i] = task.id

        # Resolve dependencies
        for i, item in enumerate(subtasks_data):
            deps = item.get("dependencies", [])
            subtasks[i].dependencies = [
                id_map[dep] for dep in deps if dep in id_map
            ]

        return subtasks if subtasks else [SubTask(name="Execute", description="")]

    def create_dag(self, subtasks: List[SubTask]) -> ExecutionDAG:
        """Create DAG from subtasks.

        Args:
            subtasks: List of subtasks with dependencies

        Returns:
            ExecutionDAG ready for execution
        """
        dag = ExecutionDAG()
        for task in subtasks:
            dag.add_task(task)
        return dag

    async def plan_and_execute(
        self,
        goal: str,
        executor_func: Executor,
        max_parallel: int = 4,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """One-call decompose and execute.

        Args:
            goal: Goal to accomplish
            executor_func: Function to execute each task
            max_parallel: Max concurrent tasks
            timeout: Total timeout

        Returns:
            Execution summary with results
        """
        # Decompose
        subtasks = self.decompose(goal)
        logger.info(f"Decomposed into {len(subtasks)} subtasks")

        # Create DAG
        dag = self.create_dag(subtasks)

        # Execute
        executor = DAGExecutor(max_parallel=max_parallel)
        results = await executor.execute(dag, executor_func, timeout=timeout)

        return {
            "goal": goal,
            "subtasks": [t.to_dict() for t in results],
            "summary": dag.summary(),
        }

    async def plan_execute_review(
        self,
        goal: str,
        executor_func: Executor,
        reviewer: Optional["TaskReviewer"] = None,
        max_parallel: int = 4,
        timeout: Optional[float] = None,
        retry_failed: bool = True,
    ) -> Dict[str, Any]:
        """Full Plan → Execute → Review cycle.

        Implements the complete agentic task-tree pattern:
        1. Plan: Decompose goal into subtasks
        2. Execute: Run tasks in parallel (respecting dependencies)
        3. Review: Evaluate results and optionally retry failed tasks

        Args:
            goal: Goal to accomplish
            executor_func: Function to execute each task
            reviewer: Optional TaskReviewer for evaluation
            max_parallel: Max concurrent tasks
            timeout: Total timeout
            retry_failed: Whether to retry failed tasks

        Returns:
            Execution summary with review insights
        """
        # 1. PLAN
        subtasks = self.decompose(goal)
        logger.info(f"[PLAN] Decomposed into {len(subtasks)} subtasks")

        # 2. EXECUTE
        dag = self.create_dag(subtasks)
        executor = DAGExecutor(max_parallel=max_parallel)
        results = await executor.execute(dag, executor_func, timeout=timeout)
        logger.info(
            f"[EXECUTE] Completed {sum(1 for t in results if t.status == TaskStatus.COMPLETED)}/{len(results)} tasks")

        # 3. REVIEW
        review_result = None
        if reviewer:
            review_result = reviewer.review(results)
            logger.info(f"[REVIEW] Score: {review_result.get('score', 'N/A')}")

            # Retry failed tasks if requested
            if retry_failed and review_result.get("retry_tasks"):
                retry_dag = ExecutionDAG()
                for task in results:
                    if task.id in review_result["retry_tasks"]:
                        task.status = TaskStatus.PENDING
                        task.error = None
                        retry_dag.add_task(task)

                if retry_dag.tasks:
                    logger.info(
                        f"[RETRY] Retrying {len(retry_dag.tasks)} failed tasks")
                    retry_results = await executor.execute(retry_dag, executor_func)
                    # Update original results
                    for task in retry_results:
                        for i, orig in enumerate(results):
                            if orig.id == task.id:
                                results[i] = task

        return {
            "goal": goal,
            "subtasks": [t.to_dict() for t in results],
            "summary": dag.summary(),
            "review": review_result,
            "phases": ["plan", "execute", "review"] if reviewer else ["plan", "execute"],
        }


class TaskReviewer:
    """Reviews task execution results.

    Evaluates success/failure rates, identifies issues,
    and suggests retries for failed tasks.

    Example:
        >>> reviewer = TaskReviewer()
        >>> report = reviewer.review(completed_tasks)
        >>> print(f"Score: {report['score']}")
    """

    def __init__(
        self,
        llm_func: Optional[Callable[[str], str]] = None,
        retry_threshold: float = 0.5,
        min_success_rate: float = 0.8,
    ):
        """Initialize reviewer.

        Args:
            llm_func: Optional LLM for intelligent review
            retry_threshold: Max failure rate before retry suggested
            min_success_rate: Minimum acceptable success rate
        """
        self.llm_func = llm_func
        self.retry_threshold = retry_threshold
        self.min_success_rate = min_success_rate

    def review(self, tasks: List[SubTask]) -> Dict[str, Any]:
        """Review completed tasks.

        Args:
            tasks: List of completed SubTask objects

        Returns:
            Review report with score, insights, and retry suggestions
        """
        if not tasks:
            return {"score": 1.0, "passed": True, "insights": [], "retry_tasks": []}

        completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        failed = [t for t in tasks if t.status == TaskStatus.FAILED]

        success_rate = len(completed) / len(tasks) if tasks else 0
        passed = success_rate >= self.min_success_rate

        # Identify tasks to retry
        retry_tasks = []
        if not passed and failed:
            # Retry failed tasks
            for task in failed:
                retry_tasks.append(task.id)

        # Generate insights
        insights = []
        if failed:
            insights.append(f"{len(failed)} task(s) failed")
            for task in failed:
                insights.append(
                    f"  - {task.name}: {task.error or 'Unknown error'}")

        if success_rate < 0.5:
            insights.append("Critical: Less than 50% success rate")
        elif success_rate < 0.8:
            insights.append("Warning: Below target success rate (80%)")

        # Calculate score
        score = self._calculate_score(tasks, completed, failed)

        return {
            "score": round(score, 3),
            "passed": passed,
            "success_rate": round(success_rate, 3),
            "completed_count": len(completed),
            "failed_count": len(failed),
            "insights": insights,
            "retry_tasks": retry_tasks,
        }

    def _calculate_score(
        self,
        all_tasks: List[SubTask],
        completed: List[SubTask],
        failed: List[SubTask]
    ) -> float:
        """Calculate overall execution score.

        Factors:
        - Success rate (50%)
        - Average duration efficiency (25%)
        - No critical failures (25%)
        """
        if not all_tasks:
            return 1.0

        # Success rate component
        success_component = len(completed) / len(all_tasks) * 0.5

        # Duration efficiency (penalize very long tasks)
        duration_score = 1.0
        durations = [t.duration_ms for t in completed if t.duration_ms]
        if durations:
            avg_duration = sum(durations) / len(durations)
            # Penalize if average > 5 seconds
            if avg_duration > 5000:
                duration_score = max(0.5, 5000 / avg_duration)
        duration_component = duration_score * 0.25

        # No critical failures component
        critical_component = 0.25 if not failed else 0.25 * \
            (1 - len(failed) / len(all_tasks))

        return success_component + duration_component + critical_component
