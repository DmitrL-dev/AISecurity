# Agent Loop Security

> **Уровень:** �����������  
> **Время:** 50 минут  
> **Трек:** 04 — Agentic Security  
> **Модуль:** 04.1 — Agent Loops  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять структуру и риски agent loops
- [ ] Имплементировать loop detection и protection
- [ ] Построить secure agent execution pipeline
- [ ] Интегрировать agent loop security в SENTINEL

---

## 1. Agent Loop Overview

### 1.1 Agent Loop Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│              AGENT LOOP SECURITY                                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Typical Agent Loop:                                               │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │ User Input → LLM → Action Selection → Tool Execution → │     │
│  │      ↑                                            │      │     │
│  │      └──────────── Observation ←──────────────────┘      │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                    │
│  Security Concerns:                                                │
│  ├── Infinite Loops: Agent stuck in endless cycle                │
│  ├── Resource Exhaustion: Unbounded tool calls                   │
│  ├── Privilege Escalation: Accumulating permissions              │
│  ├── Goal Hijacking: Adversarial goal modification               │
│  ├── Side Effects: Unintended actions                            │
│  └── State Corruption: Manipulated memory/context                │
│                                                                    │
│  Defense Layers:                                                   │
│  ├── Iteration Limits: Max steps per task                        │
│  ├── Resource Budgets: Token/time/tool limits                    │
│  ├── State Validation: Check loop invariants                     │
│  ├── Goal Integrity: Verify goal hasn't changed                  │
│  └── Execution Sandbox: Isolate side effects                     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Loop State Management

### 2.1 Loop State Model

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import hashlib
import json

class LoopStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    TIMEOUT = "timeout"
    ERROR = "error"

@dataclass
class LoopStep:
    """Single step in agent loop"""
    step_id: str
    step_number: int
    timestamp: datetime
    
    # Action
    action_type: str  # "tool_call", "reasoning", "response"
    action_name: str
    action_params: Dict = field(default_factory=dict)
    
    # Result
    result: Any = None
    success: bool = True
    error: Optional[str] = None
    
    # Metrics
    tokens_used: int = 0
    execution_time_ms: float = 0
    
    def to_dict(self) -> dict:
        return {
            'step_id': self.step_id,
            'step_number': self.step_number,
            'action_type': self.action_type,
            'action_name': self.action_name,
            'success': self.success
        }

@dataclass
class LoopGoal:
    """Agent goal with integrity tracking"""
    goal_id: str
    description: str
    created_at: datetime
    goal_hash: str = ""
    
    def __post_init__(self):
        if not self.goal_hash:
            self.goal_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        content = f"{self.goal_id}:{self.description}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        return self.goal_hash == self._compute_hash()

@dataclass
class LoopState:
    """Complete loop state"""
    loop_id: str
    agent_id: str
    session_id: str
    
    # Goal
    goal: LoopGoal = None
    
    # Status
    status: LoopStatus = LoopStatus.RUNNING
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    
    # Steps
    steps: List[LoopStep] = field(default_factory=list)
    current_step: int = 0
    
    # Limits
    max_steps: int = 50
    max_tokens: int = 100000
    max_time_seconds: int = 300
    max_tool_calls: int = 100
    
    # Usage tracking
    total_tokens: int = 0
    total_tool_calls: int = 0
    
    # Context
    context: Dict = field(default_factory=dict)
    
    def add_step(self, step: LoopStep):
        """Add step and update counters"""
        self.steps.append(step)
        self.current_step = step.step_number
        self.total_tokens += step.tokens_used
        
        if step.action_type == "tool_call":
            self.total_tool_calls += 1
    
    def check_limits(self) -> tuple[bool, str]:
        """Check if any limit exceeded"""
        if self.current_step >= self.max_steps:
            return False, "Max steps exceeded"
        
        if self.total_tokens >= self.max_tokens:
            return False, "Token limit exceeded"
        
        if self.total_tool_calls >= self.max_tool_calls:
            return False, "Tool call limit exceeded"
        
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        if elapsed >= self.max_time_seconds:
            return False, "Time limit exceeded"
        
        return True, ""
    
    def get_summary(self) -> Dict:
        """Get loop summary"""
        return {
            'loop_id': self.loop_id,
            'status': self.status.value,
            'steps_completed': self.current_step,
            'total_tokens': self.total_tokens,
            'total_tool_calls': self.total_tool_calls,
            'duration_seconds': (
                (self.ended_at or datetime.utcnow()) - self.started_at
            ).total_seconds()
        }
```

---

## 3. Loop Detection

### 3.1 Pattern-based Detection

```python
from collections import Counter

class LoopPatternDetector:
    """Detects suspicious loop patterns"""
    
    def __init__(self):
        self.repetition_threshold = 3
        self.similarity_threshold = 0.8
    
    def detect_repetition(self, steps: List[LoopStep]) -> Dict:
        """Detect repeated action sequences"""
        if len(steps) < 4:
            return {'detected': False}
        
        # Get recent action signatures
        signatures = [
            f"{s.action_type}:{s.action_name}"
            for s in steps[-20:]
        ]
        
        # Check for exact repetition
        for window_size in [2, 3, 4, 5]:
            if len(signatures) >= window_size * 2:
                last_window = signatures[-window_size:]
                prev_window = signatures[-window_size*2:-window_size]
                
                if last_window == prev_window:
                    count = self._count_repetitions(signatures, last_window)
                    if count >= self.repetition_threshold:
                        return {
                            'detected': True,
                            'type': 'exact_repetition',
                            'pattern': last_window,
                            'count': count
                        }
        
        return {'detected': False}
    
    def _count_repetitions(self, signatures: List[str], 
                           pattern: List[str]) -> int:
        """Count pattern repetitions"""
        count = 0
        pattern_len = len(pattern)
        i = len(signatures) - pattern_len
        
        while i >= 0:
            window = signatures[i:i+pattern_len]
            if window == pattern:
                count += 1
                i -= pattern_len
            else:
                break
        
        return count
    
    def detect_oscillation(self, steps: List[LoopStep]) -> Dict:
        """Detect oscillating actions (A→B→A→B)"""
        if len(steps) < 6:
            return {'detected': False}
        
        signatures = [
            f"{s.action_type}:{s.action_name}"
            for s in steps[-10:]
        ]
        
        # Check A-B-A-B pattern
        for i in range(len(signatures) - 3):
            if (signatures[i] == signatures[i+2] and 
                signatures[i+1] == signatures[i+3] and
                signatures[i] != signatures[i+1]):
                
                # Count oscillations
                osc_count = 1
                j = i + 2
                while j + 1 < len(signatures):
                    if (signatures[j] == signatures[i] and 
                        j + 1 < len(signatures) and
                        signatures[j+1] == signatures[i+1]):
                        osc_count += 1
                        j += 2
                    else:
                        break
                
                if osc_count >= 3:
                    return {
                        'detected': True,
                        'type': 'oscillation',
                        'states': [signatures[i], signatures[i+1]],
                        'count': osc_count
                    }
        
        return {'detected': False}
    
    def detect_no_progress(self, state: LoopState) -> Dict:
        """Detect lack of progress"""
        if len(state.steps) < 10:
            return {'detected': False}
        
        recent = state.steps[-10:]
        
        # All failures
        if all(not s.success for s in recent):
            return {
                'detected': True,
                'type': 'all_failures',
                'count': 10
            }
        
        # Same action repeated
        action_names = [s.action_name for s in recent]
        most_common = Counter(action_names).most_common(1)[0]
        if most_common[1] >= 8:
            return {
                'detected': True,
                'type': 'stuck_action',
                'action': most_common[0],
                'count': most_common[1]
            }
        
        return {'detected': False}

class GoalIntegrityChecker:
    """Checks goal hasn't been hijacked"""
    
    def __init__(self):
        self.original_goals: Dict[str, LoopGoal] = {}
    
    def register_goal(self, loop_id: str, goal: LoopGoal):
        """Register original goal for loop"""
        self.original_goals[loop_id] = goal
    
    def check_integrity(self, loop_id: str, current_goal: LoopGoal) -> Dict:
        """Check if goal maintains integrity"""
        original = self.original_goals.get(loop_id)
        
        if not original:
            return {'valid': True, 'reason': 'No original registered'}
        
        if not current_goal.verify_integrity():
            return {
                'valid': False,
                'reason': 'Goal hash mismatch - possible tampering'
            }
        
        if current_goal.goal_hash != original.goal_hash:
            return {
                'valid': False,
                'reason': 'Goal changed from original'
            }
        
        return {'valid': True}
```

---

## 4. Secure Loop Executor

```python
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError

@dataclass
class LoopConfig:
    """Loop security configuration"""
    max_steps: int = 50
    max_tokens: int = 100000
    max_time_seconds: int = 300
    max_tool_calls: int = 100
    enable_pattern_detection: bool = True
    enable_goal_integrity: bool = True

class SecureLoopExecutor:
    """Secure agent loop executor"""
    
    def __init__(self, config: LoopConfig):
        self.config = config
        self.pattern_detector = LoopPatternDetector()
        self.goal_checker = GoalIntegrityChecker()
        self.active_loops: Dict[str, LoopState] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def start_loop(self, agent_id: str, session_id: str,
                   goal_description: str) -> LoopState:
        """Start a new secure loop"""
        loop_id = str(uuid.uuid4())
        
        goal = LoopGoal(
            goal_id=str(uuid.uuid4()),
            description=goal_description,
            created_at=datetime.utcnow()
        )
        
        state = LoopState(
            loop_id=loop_id,
            agent_id=agent_id,
            session_id=session_id,
            goal=goal,
            max_steps=self.config.max_steps,
            max_tokens=self.config.max_tokens,
            max_time_seconds=self.config.max_time_seconds,
            max_tool_calls=self.config.max_tool_calls
        )
        
        self.active_loops[loop_id] = state
        
        if self.config.enable_goal_integrity:
            self.goal_checker.register_goal(loop_id, goal)
        
        return state
    
    def execute_step(self, loop_id: str, action_type: str,
                     action_name: str, action_params: Dict,
                     action_handler: callable) -> Dict:
        """Execute a single step with security checks"""
        state = self.active_loops.get(loop_id)
        if not state:
            return {'success': False, 'error': 'Loop not found'}
        
        if state.status != LoopStatus.RUNNING:
            return {'success': False, 'error': f'Loop not running: {state.status}'}
        
        # Check limits
        within_limits, limit_error = state.check_limits()
        if not within_limits:
            state.status = LoopStatus.TERMINATED
            state.ended_at = datetime.utcnow()
            return {'success': False, 'error': limit_error}
        
        # Pattern detection
        if self.config.enable_pattern_detection:
            repetition = self.pattern_detector.detect_repetition(state.steps)
            if repetition['detected']:
                state.status = LoopStatus.TERMINATED
                return {
                    'success': False,
                    'error': f"Loop pattern detected: {repetition['type']}"
                }
            
            oscillation = self.pattern_detector.detect_oscillation(state.steps)
            if oscillation['detected']:
                state.status = LoopStatus.TERMINATED
                return {
                    'success': False,
                    'error': f"Oscillation detected: {oscillation['states']}"
                }
        
        # Goal integrity
        if self.config.enable_goal_integrity:
            integrity = self.goal_checker.check_integrity(loop_id, state.goal)
            if not integrity['valid']:
                state.status = LoopStatus.TERMINATED
                return {
                    'success': False,
                    'error': f"Goal integrity violation: {integrity['reason']}"
                }
        
        # Execute action with timeout
        start_time = datetime.utcnow()
        step = LoopStep(
            step_id=str(uuid.uuid4()),
            step_number=state.current_step + 1,
            timestamp=start_time,
            action_type=action_type,
            action_name=action_name,
            action_params=action_params
        )
        
        try:
            future = self.executor.submit(action_handler, action_params)
            remaining_time = self.config.max_time_seconds - (
                datetime.utcnow() - state.started_at
            ).total_seconds()
            
            result = future.result(timeout=max(1, remaining_time))
            
            step.result = result
            step.success = True
            step.execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        except TimeoutError:
            step.success = False
            step.error = "Step timeout"
            state.status = LoopStatus.TIMEOUT
        
        except Exception as e:
            step.success = False
            step.error = str(e)
        
        # Record step
        state.add_step(step)
        
        # Check no-progress
        if self.config.enable_pattern_detection:
            no_progress = self.pattern_detector.detect_no_progress(state)
            if no_progress['detected']:
                state.status = LoopStatus.TERMINATED
                return {
                    'success': False,
                    'error': f"No progress detected: {no_progress['type']}"
                }
        
        return {
            'success': step.success,
            'result': step.result,
            'error': step.error,
            'step_number': step.step_number
        }
    
    def complete_loop(self, loop_id: str, success: bool = True):
        """Mark loop as completed"""
        state = self.active_loops.get(loop_id)
        if state:
            state.status = LoopStatus.COMPLETED if success else LoopStatus.ERROR
            state.ended_at = datetime.utcnow()
    
    def get_loop_state(self, loop_id: str) -> Optional[LoopState]:
        """Get loop state"""
        return self.active_loops.get(loop_id)
    
    def get_active_loops(self) -> List[Dict]:
        """Get all active loops"""
        return [
            state.get_summary()
            for state in self.active_loops.values()
            if state.status == LoopStatus.RUNNING
        ]
```

---

## 5. SENTINEL Integration

```python
from dataclasses import dataclass

@dataclass
class AgentLoopConfig:
    """Agent loop security configuration"""
    max_steps: int = 50
    max_tokens: int = 100000
    max_time_seconds: int = 300
    max_tool_calls: int = 100
    enable_pattern_detection: bool = True
    enable_goal_integrity: bool = True

class SENTINELAgentLoopEngine:
    """Agent loop security for SENTINEL"""
    
    def __init__(self, config: AgentLoopConfig):
        self.config = config
        loop_config = LoopConfig(
            max_steps=config.max_steps,
            max_tokens=config.max_tokens,
            max_time_seconds=config.max_time_seconds,
            max_tool_calls=config.max_tool_calls,
            enable_pattern_detection=config.enable_pattern_detection,
            enable_goal_integrity=config.enable_goal_integrity
        )
        self.executor = SecureLoopExecutor(loop_config)
    
    def start_loop(self, agent_id: str, session_id: str,
                   goal: str) -> str:
        """Start secure agent loop"""
        state = self.executor.start_loop(agent_id, session_id, goal)
        return state.loop_id
    
    def execute_step(self, loop_id: str, action_type: str,
                     action_name: str, params: Dict,
                     handler: callable) -> Dict:
        """Execute loop step"""
        return self.executor.execute_step(
            loop_id, action_type, action_name, params, handler
        )
    
    def complete(self, loop_id: str, success: bool = True):
        """Complete loop"""
        self.executor.complete_loop(loop_id, success)
    
    def get_state(self, loop_id: str) -> Optional[Dict]:
        """Get loop state summary"""
        state = self.executor.get_loop_state(loop_id)
        return state.get_summary() if state else None
    
    def get_active(self) -> List[Dict]:
        """Get active loops"""
        return self.executor.get_active_loops()
```

---

## 6. Резюме

| Компонент | Описание |
|-----------|----------|
| **LoopState** | Полное состояние loop execution |
| **LoopStep** | Единичный шаг с метриками |
| **PatternDetector** | Детекция repetition, oscillation |
| **GoalChecker** | Integrity verification для goal |
| **SecureExecutor** | Execution с limits и checks |

---

## Следующий урок

→ [02. Tool Security](../02-tool-security/README.md)

---

*AI Security Academy | Track 04: Agentic Security | Module 04.1: Agent Loops*
