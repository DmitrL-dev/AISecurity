"""
Cascading Guard Engine — SENTINEL ASI08: Cascading Failures

Prevents cascading failures in multi-agent systems.
Philosophy: Blast radius control through circuit breakers and isolation.

Features:
- Fanout detection
- Feedback loop breaking
- Circuit breakers
- Rollback coordination

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking all actions
    HALF_OPEN = "half_open"  # Testing recovery


class PropagationType(Enum):
    """Types of cascade propagation"""

    DIRECT = "direct"  # A → B
    TRANSITIVE = "transitive"  # A → B → C
    FEEDBACK = "feedback"  # A → B → A


@dataclass
class AgentAction:
    """An action by an agent"""

    action_id: str
    agent_id: str
    action_type: str
    timestamp: datetime
    target_agents: List[str]
    parent_action: Optional[str] = None


@dataclass
class CircuitBreaker:
    """Circuit breaker for an agent/action"""

    agent_id: str
    action_type: str
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure: Optional[datetime]
    last_transition: datetime

    def trip(self):
        """Trip the circuit breaker"""
        self.state = CircuitState.OPEN
        self.last_transition = datetime.now()

    def reset(self):
        """Reset the circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_transition = datetime.now()

    def half_open(self):
        """Set to half-open for testing"""
        self.state = CircuitState.HALF_OPEN
        self.last_transition = datetime.now()


@dataclass
class FeedbackLoop:
    """A detected feedback loop"""

    loop_id: str
    agents: List[str]
    cycle_length: int
    iteration_count: int
    first_detected: datetime


@dataclass
class FanoutResult:
    """Result of fanout detection"""

    origin_agent: str
    origin_action: str
    affected_agents: Set[str]
    propagation_depth: int
    velocity: float  # Actions per second
    is_suspicious: bool


@dataclass
class RollbackPlan:
    """Plan for coordinated rollback"""

    cascade_id: str
    affected_agents: List[str]
    rollback_order: List[str]
    actions_to_revert: List[str]
    estimated_recovery_time: timedelta


@dataclass
class CascadeAnalysisResult:
    """Result of cascade analysis"""

    is_cascading: bool
    fanout_detected: bool
    feedback_loops: List[FeedbackLoop]
    circuit_states: Dict[str, CircuitState]
    risk_score: float
    recommendations: List[str]


class CascadingGuard:
    """
    Prevents cascading failures in multi-agent systems.

    Addresses OWASP ASI08: Cascading Failures

    Features:
    - Fanout detection
    - Feedback loop breaking
    - Circuit breakers
    - Rollback coordination

    Usage:
        guard = CascadingGuard()
        result = guard.analyze_cascade(actions)
        if result.is_cascading:
            guard.enforce_circuit_breaker(agent_id)
    """

    ENGINE_NAME = "cascading_guard"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    # Thresholds
    FANOUT_THRESHOLD = 5  # agents in window
    VELOCITY_THRESHOLD = 10  # actions per second
    LOOP_THRESHOLD = 3  # iterations before breaking
    FAILURE_THRESHOLD = 5  # failures before tripping

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.actions: List[AgentAction] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.feedback_loops: List[FeedbackLoop] = []
        self.action_graph: Dict[str, List[str]] = defaultdict(list)

    def record_action(self, action: AgentAction):
        """Record an action for cascade tracking"""
        self.actions.append(action)

        # Update action graph
        for target in action.target_agents:
            self.action_graph[action.agent_id].append(target)

    def detect_fanout(
        self, origin_action: AgentAction, window: timedelta = timedelta(seconds=30)
    ) -> FanoutResult:
        """Detect rapid multi-agent spread"""
        affected = set()
        relevant_actions = []

        # Find actions within window
        for action in self.actions:
            if (
                action.timestamp >= origin_action.timestamp
                and action.timestamp <= origin_action.timestamp + window
            ):
                relevant_actions.append(action)
                affected.update(action.target_agents)
                affected.add(action.agent_id)

        # Calculate velocity
        if len(relevant_actions) > 1:
            time_span = (
                relevant_actions[-1].timestamp - relevant_actions[0].timestamp
            ).total_seconds()
            velocity = len(relevant_actions) / max(time_span, 0.1)
        else:
            velocity = 0

        # Calculate depth
        depth = self._calculate_propagation_depth(origin_action.agent_id)

        is_suspicious = (
            len(affected) > self.FANOUT_THRESHOLD or velocity > self.VELOCITY_THRESHOLD
        )

        return FanoutResult(
            origin_agent=origin_action.agent_id,
            origin_action=origin_action.action_id,
            affected_agents=affected,
            propagation_depth=depth,
            velocity=velocity,
            is_suspicious=is_suspicious,
        )

    def _calculate_propagation_depth(self, origin: str) -> int:
        """Calculate propagation depth using BFS"""
        visited = set()
        depth = 0
        current_level = {origin}

        while current_level:
            next_level = set()
            for agent in current_level:
                if agent not in visited:
                    visited.add(agent)
                    next_level.update(self.action_graph.get(agent, []))

            if next_level - visited:
                depth += 1
            current_level = next_level - visited

        return depth

    def detect_feedback_loop(self) -> List[FeedbackLoop]:
        """Find cycles in agent dependency graph"""
        loops = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.action_graph.get(node, []):
                if neighbor not in visited:
                    cycle = dfs(neighbor, path + [node])
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor) if neighbor in path else 0
                    return path[cycle_start:] + [node]

            rec_stack.remove(node)
            return None

        for node in list(self.action_graph.keys()):
            if node not in visited:
                cycle = dfs(node, [])
                if cycle:
                    loop = FeedbackLoop(
                        loop_id=f"loop-{len(loops)+1}",
                        agents=cycle,
                        cycle_length=len(cycle),
                        iteration_count=1,
                        first_detected=datetime.now(),
                    )
                    loops.append(loop)

        self.feedback_loops = loops
        return loops

    def get_or_create_circuit_breaker(
        self, agent_id: str, action_type: str = "*"
    ) -> CircuitBreaker:
        """Get or create circuit breaker for agent/action"""
        key = f"{agent_id}:{action_type}"

        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker(
                agent_id=agent_id,
                action_type=action_type,
                state=CircuitState.CLOSED,
                failure_count=0,
                success_count=0,
                last_failure=None,
                last_transition=datetime.now(),
            )

        return self.circuit_breakers[key]

    def record_failure(self, agent_id: str, action_type: str = "*"):
        """Record a failure for circuit breaker"""
        cb = self.get_or_create_circuit_breaker(agent_id, action_type)
        cb.failure_count += 1
        cb.last_failure = datetime.now()

        if cb.failure_count >= self.FAILURE_THRESHOLD:
            cb.trip()

    def record_success(self, agent_id: str, action_type: str = "*"):
        """Record a success for circuit breaker"""
        cb = self.get_or_create_circuit_breaker(agent_id, action_type)
        cb.success_count += 1

        if cb.state == CircuitState.HALF_OPEN:
            cb.reset()

    def enforce_circuit_breaker(self, agent_id: str, action_type: str = "*") -> bool:
        """Check if circuit breaker allows action"""
        cb = self.get_or_create_circuit_breaker(agent_id, action_type)

        if cb.state == CircuitState.OPEN:
            # Check if we should try half-open
            if cb.last_transition:
                time_since = datetime.now() - cb.last_transition
                if time_since > timedelta(seconds=30):
                    cb.half_open()
                    return True  # Allow test
            return False

        return True

    def coordinate_rollback(self, cascade_id: str) -> RollbackPlan:
        """Generate coordinated rollback plan"""
        # Find affected agents
        affected = set()
        actions_to_revert = []

        for action in self.actions:
            if action.action_id.startswith(cascade_id):
                affected.add(action.agent_id)
                actions_to_revert.append(action.action_id)

        # Determine rollback order (reverse of action order)
        rollback_order = list(affected)[::-1]

        return RollbackPlan(
            cascade_id=cascade_id,
            affected_agents=list(affected),
            rollback_order=rollback_order,
            actions_to_revert=actions_to_revert,
            estimated_recovery_time=timedelta(seconds=len(affected) * 5),
        )

    def analyze_cascade(
        self, recent_actions: Optional[List[AgentAction]] = None
    ) -> CascadeAnalysisResult:
        """Full cascade analysis"""
        if recent_actions:
            for action in recent_actions:
                self.record_action(action)

        # Detect fanout
        fanout_detected = False
        if self.actions:
            fanout = self.detect_fanout(self.actions[-1])
            fanout_detected = fanout.is_suspicious

        # Detect feedback loops
        loops = self.detect_feedback_loop()

        # Get circuit states
        circuit_states = {k: v.state for k, v in self.circuit_breakers.items()}

        # Calculate risk
        risk_score = 0.0
        if fanout_detected:
            risk_score += 0.4
        if loops:
            risk_score += 0.4
        if any(s == CircuitState.OPEN for s in circuit_states.values()):
            risk_score += 0.2

        # Recommendations
        recommendations = []
        if fanout_detected:
            recommendations.append("Implement fanout limits")
        if loops:
            recommendations.append(f"Break {len(loops)} feedback loops")

        return CascadeAnalysisResult(
            is_cascading=risk_score > 0.5,
            fanout_detected=fanout_detected,
            feedback_loops=loops,
            circuit_states=circuit_states,
            risk_score=min(risk_score, 1.0),
            recommendations=recommendations,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get cascade guard statistics"""
        open_breakers = sum(
            1 for cb in self.circuit_breakers.values() if cb.state == CircuitState.OPEN
        )

        return {
            "total_actions_tracked": len(self.actions),
            "active_circuit_breakers": len(self.circuit_breakers),
            "open_circuit_breakers": open_breakers,
            "feedback_loops_detected": len(self.feedback_loops),
            "agents_in_graph": len(self.action_graph),
        }


# Factory function
def create_engine(config: Optional[Dict[str, Any]] = None) -> CascadingGuard:
    """Create an instance of the CascadingGuard engine."""
    return CascadingGuard(config)


if __name__ == "__main__":
    guard = CascadingGuard()

    print("=== Cascading Guard Test ===\n")

    # Simulate cascade
    print("Simulating cascade...")
    now = datetime.now()

    actions = [
        AgentAction("a1", "agent-1", "process", now, ["agent-2", "agent-3"]),
        AgentAction(
            "a2", "agent-2", "process", now + timedelta(seconds=1), ["agent-4"]
        ),
        AgentAction(
            "a3",
            "agent-3",
            "process",
            now + timedelta(seconds=2),
            ["agent-4", "agent-5"],
        ),
        AgentAction(
            "a4", "agent-4", "process", now + timedelta(seconds=3), ["agent-1"]
        ),  # Loop!
    ]

    for action in actions:
        guard.record_action(action)

    # Detect fanout
    print("\nFanout detection:")
    fanout = guard.detect_fanout(actions[0])
    print(f"  Affected agents: {fanout.affected_agents}")
    print(f"  Depth: {fanout.propagation_depth}")
    print(f"  Suspicious: {fanout.is_suspicious}")

    # Detect loops
    print("\nFeedback loop detection:")
    loops = guard.detect_feedback_loop()
    print(f"  Loops found: {len(loops)}")
    for loop in loops:
        print(f"    {loop.agents}")

    # Test circuit breaker
    print("\nCircuit breaker test:")
    for _ in range(6):  # Trigger threshold
        guard.record_failure("agent-1")

    can_proceed = guard.enforce_circuit_breaker("agent-1")
    print(f"  Agent-1 can proceed: {can_proceed}")

    # Full analysis
    print("\nFull cascade analysis:")
    result = guard.analyze_cascade()
    print(f"  Is cascading: {result.is_cascading}")
    print(f"  Risk score: {result.risk_score:.0%}")
    print(f"  Recommendations: {result.recommendations}")

    # Statistics
    print(f"\nStatistics: {guard.get_statistics()}")
