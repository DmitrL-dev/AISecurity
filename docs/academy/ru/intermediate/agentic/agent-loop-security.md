# Безопасность циклов агентов

> **Уровень:** Продвинутый  
> **Время:** 50 минут  
> **Трек:** 04 — Агентная безопасность  
> **Модуль:** 04.1 — Циклы агентов  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять структуру и риски циклов агента
- [ ] Реализовать детекцию и защиту циклов
- [ ] Построить безопасный пайплайн выполнения агента
- [ ] Интегрировать безопасность циклов в SENTINEL

---

## 1. Обзор циклов агента

```
┌────────────────────────────────────────────────────────────────────┐
│              БЕЗОПАСНОСТЬ ЦИКЛОВ АГЕНТА                            │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Типичный цикл агента:                                             │
│  Ввод → LLM → Действие → Инструмент → Наблюдение → LLM → ...     │
│                                                                    │
│  Проблемы безопасности:                                            │
│  ├── Бесконечные циклы: Бесконечные повторения                    │
│  ├── Исчерпание ресурсов: Неограниченные вызовы                   │
│  ├── Эскалация привилегий: Накопление разрешений                 │
│  ├── Захват цели: Модифицированные цели                           │
│  └── Повреждение состояния: Манипулированный контекст             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Модель состояния цикла

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import hashlib

class LoopStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    TIMEOUT = "timeout"
    ERROR = "error"

@dataclass
class LoopStep:
    """Один шаг цикла"""
    step_id: str
    step_number: int
    timestamp: datetime
    action_type: str
    action_name: str
    action_params: Dict = field(default_factory=dict)
    result: Any = None
    success: bool = True
    error: Optional[str] = None
    tokens_used: int = 0
    execution_time_ms: float = 0

@dataclass
class LoopGoal:
    """Цель с отслеживанием целостности"""
    goal_id: str
    description: str
    created_at: datetime
    goal_hash: str = ""
    
    def __post_init__(self):
        if not self.goal_hash:
            content = f"{self.goal_id}:{self.description}"
            self.goal_hash = hashlib.sha256(content.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        content = f"{self.goal_id}:{self.description}"
        return self.goal_hash == hashlib.sha256(content.encode()).hexdigest()

@dataclass
class LoopState:
    """Полное состояние цикла"""
    loop_id: str
    agent_id: str
    session_id: str
    goal: LoopGoal = None
    status: LoopStatus = LoopStatus.RUNNING
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    steps: List[LoopStep] = field(default_factory=list)
    current_step: int = 0
    
    # Лимиты
    max_steps: int = 50
    max_tokens: int = 100000
    max_time_seconds: int = 300
    max_tool_calls: int = 100
    
    # Счётчики
    total_tokens: int = 0
    total_tool_calls: int = 0
    
    def add_step(self, step: LoopStep):
        self.steps.append(step)
        self.current_step = step.step_number
        self.total_tokens += step.tokens_used
        if step.action_type == "tool_call":
            self.total_tool_calls += 1
    
    def check_limits(self) -> tuple[bool, str]:
        if self.current_step >= self.max_steps:
            return False, "Превышен лимит шагов"
        if self.total_tokens >= self.max_tokens:
            return False, "Превышен лимит токенов"
        if self.total_tool_calls >= self.max_tool_calls:
            return False, "Превышен лимит вызовов инструментов"
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        if elapsed >= self.max_time_seconds:
            return False, "Превышен лимит времени"
        return True, ""
```

---

## 3. Детекция паттернов циклов

```python
from collections import Counter

class LoopPatternDetector:
    """Детекция подозрительных паттернов"""
    
    def __init__(self):
        self.repetition_threshold = 3
    
    def detect_repetition(self, steps: List[LoopStep]) -> Dict:
        """Детекция повторяющихся последовательностей."""
        if len(steps) < 4:
            return {'detected': False}
        
        signatures = [f"{s.action_type}:{s.action_name}" for s in steps[-20:]]
        
        for size in [2, 3, 4, 5]:
            if len(signatures) >= size * 2:
                last = signatures[-size:]
                prev = signatures[-size*2:-size]
                if last == prev:
                    count = self._count_reps(signatures, last)
                    if count >= self.repetition_threshold:
                        return {'detected': True, 'type': 'repetition', 'count': count}
        
        return {'detected': False}
    
    def _count_reps(self, sigs: List[str], pattern: List[str]) -> int:
        count = 0
        i = len(sigs) - len(pattern)
        while i >= 0:
            if sigs[i:i+len(pattern)] == pattern:
                count += 1
                i -= len(pattern)
            else:
                break
        return count
    
    def detect_oscillation(self, steps: List[LoopStep]) -> Dict:
        """Детекция осцилляции между действиями."""
        if len(steps) < 6:
            return {'detected': False}
        
        sigs = [f"{s.action_type}:{s.action_name}" for s in steps[-10:]]
        
        for i in range(len(sigs) - 3):
            if sigs[i] == sigs[i+2] and sigs[i+1] == sigs[i+3] and sigs[i] != sigs[i+1]:
                count = 1
                j = i + 2
                while j + 1 < len(sigs):
                    if sigs[j] == sigs[i] and sigs[j+1] == sigs[i+1]:
                        count += 1
                        j += 2
                    else:
                        break
                if count >= 3:
                    return {'detected': True, 'type': 'oscillation', 'count': count}
        
        return {'detected': False}
    
    def detect_no_progress(self, state: LoopState) -> Dict:
        """Детекция застревания."""
        if len(state.steps) < 10:
            return {'detected': False}
        
        recent = state.steps[-10:]
        if all(not s.success for s in recent):
            return {'detected': True, 'type': 'all_failures'}
        
        actions = [s.action_name for s in recent]
        most = Counter(actions).most_common(1)[0]
        if most[1] >= 8:
            return {'detected': True, 'type': 'stuck', 'action': most[0]}
        
        return {'detected': False}

class GoalIntegrityChecker:
    """Проверка целостности цели."""
    
    def __init__(self):
        self.goals: Dict[str, LoopGoal] = {}
    
    def register(self, loop_id: str, goal: LoopGoal):
        self.goals[loop_id] = goal
    
    def check(self, loop_id: str, current: LoopGoal) -> Dict:
        original = self.goals.get(loop_id)
        if not original:
            return {'valid': True}
        if not current.verify_integrity():
            return {'valid': False, 'reason': 'Несоответствие хеша'}
        if current.goal_hash != original.goal_hash:
            return {'valid': False, 'reason': 'Цель изменена'}
        return {'valid': True}
```

---

## 4. Безопасный исполнитель

```python
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError

@dataclass
class LoopConfig:
    max_steps: int = 50
    max_tokens: int = 100000
    max_time_seconds: int = 300
    max_tool_calls: int = 100
    enable_detection: bool = True
    enable_goal_integrity: bool = True

class SecureLoopExecutor:
    """Безопасное выполнение циклов агента."""
    
    def __init__(self, config: LoopConfig):
        self.config = config
        self.detector = LoopPatternDetector()
        self.goal_checker = GoalIntegrityChecker()
        self.loops: Dict[str, LoopState] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def start(self, agent_id: str, session_id: str, goal: str) -> LoopState:
        loop_id = str(uuid.uuid4())
        goal_obj = LoopGoal(str(uuid.uuid4()), goal, datetime.utcnow())
        
        state = LoopState(
            loop_id=loop_id,
            agent_id=agent_id,
            session_id=session_id,
            goal=goal_obj,
            max_steps=self.config.max_steps,
            max_tokens=self.config.max_tokens,
            max_time_seconds=self.config.max_time_seconds,
            max_tool_calls=self.config.max_tool_calls
        )
        
        self.loops[loop_id] = state
        if self.config.enable_goal_integrity:
            self.goal_checker.register(loop_id, goal_obj)
        
        return state
    
    def step(self, loop_id: str, action_type: str, action_name: str,
             params: Dict, handler: callable) -> Dict:
        state = self.loops.get(loop_id)
        if not state or state.status != LoopStatus.RUNNING:
            return {'success': False, 'error': 'Недействительный цикл'}
        
        # Проверка лимитов
        ok, err = state.check_limits()
        if not ok:
            state.status = LoopStatus.TERMINATED
            return {'success': False, 'error': err}
        
        # Детекция паттернов
        if self.config.enable_detection:
            for check in [self.detector.detect_repetition,
                         self.detector.detect_oscillation]:
                result = check(state.steps)
                if result['detected']:
                    state.status = LoopStatus.TERMINATED
                    return {'success': False, 'error': f"Паттерн: {result['type']}"}
        
        # Целостность цели
        if self.config.enable_goal_integrity:
            check = self.goal_checker.check(loop_id, state.goal)
            if not check['valid']:
                state.status = LoopStatus.TERMINATED
                return {'success': False, 'error': check['reason']}
        
        # Выполнение
        start = datetime.utcnow()
        step = LoopStep(
            step_id=str(uuid.uuid4()),
            step_number=state.current_step + 1,
            timestamp=start,
            action_type=action_type,
            action_name=action_name,
            action_params=params
        )
        
        try:
            future = self.executor.submit(handler, params)
            remaining = self.config.max_time_seconds - (
                datetime.utcnow() - state.started_at
            ).total_seconds()
            
            step.result = future.result(timeout=max(1, remaining))
            step.success = True
        except TimeoutError:
            step.success = False
            step.error = "Таймаут"
            state.status = LoopStatus.TIMEOUT
        except Exception as e:
            step.success = False
            step.error = str(e)
        
        step.execution_time_ms = (datetime.utcnow() - start).total_seconds() * 1000
        state.add_step(step)
        
        return {
            'success': step.success,
            'result': step.result,
            'error': step.error
        }
    
    def complete(self, loop_id: str, success: bool = True):
        state = self.loops.get(loop_id)
        if state:
            state.status = LoopStatus.COMPLETED if success else LoopStatus.ERROR
            state.ended_at = datetime.utcnow()
```

---

## 5. Интеграция с SENTINEL

```python
class SENTINELAgentLoopEngine:
    """Движок безопасности циклов для SENTINEL."""
    
    def __init__(self, config):
        self.executor = SecureLoopExecutor(LoopConfig(
            max_steps=config.max_steps,
            max_time_seconds=config.max_time_seconds,
            enable_detection=config.enable_detection
        ))
    
    def start(self, agent_id: str, session_id: str, goal: str) -> str:
        state = self.executor.start(agent_id, session_id, goal)
        return state.loop_id
    
    def step(self, loop_id: str, action_type: str, action_name: str,
             params: Dict, handler: callable) -> Dict:
        return self.executor.step(loop_id, action_type, action_name, params, handler)
    
    def complete(self, loop_id: str, success: bool = True):
        self.executor.complete(loop_id, success)
```

---

## 6. Итоги

| Компонент | Описание |
|-----------|----------|
| **LoopState** | Полное состояние выполнения |
| **LoopStep** | Один шаг с метриками |
| **PatternDetector** | Детекция повторений, осцилляций |
| **GoalChecker** | Верификация целостности цели |
| **SecureExecutor** | Выполнение с проверками |

---

## Следующий урок

→ [02. Tool Security](../02-tool-security/README.md)

---

*AI Security Academy | Трек 04: Агентная безопасность | Модуль 04.1: Циклы агентов*
