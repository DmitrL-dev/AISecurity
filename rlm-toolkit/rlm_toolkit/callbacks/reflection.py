"""
Reflection Callback.

Implements the Reflection Pattern for agent self-evaluation.
Agents automatically evaluate their actions and store insights for learning.

Example:
    >>> from rlm_toolkit.callbacks.reflection import ReflectionCallback
    >>> 
    >>> reflection = ReflectionCallback(
    ...     llm=my_llm,
    ...     memory=my_memory,
    ...     frequency=1  # Reflect on every action
    ... )
    >>> 
    >>> callbacks = CallbackManager([reflection])
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Represents an action and its outcome for reflection."""
    action_id: str
    action_type: str
    input: str
    output: str
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    tokens_used: int = 0
    latency_ms: float = 0


@dataclass
class Reflection:
    """A reflection on an action."""
    action_id: str
    analysis: str
    quality_score: float  # 0.0 to 1.0
    improvements: List[str] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "analysis": self.analysis,
            "quality_score": self.quality_score,
            "improvements": self.improvements,
            "learnings": self.learnings,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class ReflectorBase(ABC):
    """Base class for reflection generation."""

    @abstractmethod
    def reflect(self, action: ActionResult) -> Reflection:
        """Generate reflection for an action."""
        pass


class LLMReflector(ReflectorBase):
    """Uses an LLM to generate reflections.

    Args:
        llm_func: Function that takes a prompt and returns response
        prompt_template: Template for reflection prompt
    """

    DEFAULT_PROMPT = """Analyze this AI action and provide reflection:

Action Type: {action_type}
Input: {input}
Output: {output}
Success: {success}

Evaluate:
1. Was this action effective? (score 0-10)
2. What could be improved?
3. What lessons can be learned?

Respond in JSON format:
{{
    "quality_score": <0.0-1.0>,
    "analysis": "<brief analysis>",
    "improvements": ["<improvement1>", "<improvement2>"],
    "learnings": ["<learning1>", "<learning2>"]
}}"""

    def __init__(
        self,
        llm_func: Callable[[str], str],
        prompt_template: Optional[str] = None
    ):
        self.llm_func = llm_func
        self.prompt_template = prompt_template or self.DEFAULT_PROMPT

    def reflect(self, action: ActionResult) -> Reflection:
        """Generate reflection using LLM."""
        prompt = self.prompt_template.format(
            action_type=action.action_type,
            input=action.input[:500],  # Truncate for context
            output=action.output[:500],
            success=action.success,
        )

        try:
            response = self.llm_func(prompt)
            data = self._parse_response(response)

            return Reflection(
                action_id=action.action_id,
                analysis=data.get("analysis", "No analysis available"),
                quality_score=float(data.get("quality_score", 0.5)),
                improvements=data.get("improvements", []),
                learnings=data.get("learnings", []),
            )
        except Exception as e:
            logger.warning(f"Reflection generation failed: {e}")
            return Reflection(
                action_id=action.action_id,
                analysis=f"Reflection failed: {e}",
                quality_score=0.5,
            )

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to reflection data."""
        import json
        import re

        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: return minimal data
        return {"analysis": response, "quality_score": 0.5}


class SimpleReflector(ReflectorBase):
    """Simple rule-based reflector (no LLM required).

    Uses heuristics to evaluate action quality.
    """

    def reflect(self, action: ActionResult) -> Reflection:
        """Generate reflection using simple heuristics."""
        score = 0.5
        improvements = []
        learnings = []

        # Success contributes to score
        if action.success:
            score += 0.3
        else:
            score -= 0.2
            improvements.append("Action failed - investigate cause")

        # Latency analysis
        if action.latency_ms < 100:
            score += 0.1
            learnings.append("Fast response time achieved")
        elif action.latency_ms > 5000:
            score -= 0.1
            improvements.append("Consider optimizing for speed")

        # Token efficiency
        if action.tokens_used > 0:
            ratio = len(action.output) / action.tokens_used
            if ratio < 0.5:
                improvements.append("Low output/token ratio - optimize prompt")

        # Output length analysis
        if len(action.output) < 10 and action.success:
            improvements.append("Output very short - may need more detail")

        score = max(0.0, min(1.0, score))  # Clamp to 0-1

        analysis = f"Action {'succeeded' if action.success else 'failed'}"
        analysis += f" in {action.latency_ms:.0f}ms"
        if action.tokens_used:
            analysis += f" using {action.tokens_used} tokens"

        return Reflection(
            action_id=action.action_id,
            analysis=analysis,
            quality_score=score,
            improvements=improvements,
            learnings=learnings,
        )


class ReflectionCallback:
    """Callback for automatic action reflection.

    Integrates with RLM's callback system to reflect on LLM actions.

    Args:
        reflector: Reflector to use (LLMReflector or SimpleReflector)
        frequency: Reflect every N actions (1 = every action)
        store_func: Function to store reflections (e.g., to H-MEM)
        min_quality_threshold: Only store reflections above this score

    Example:
        >>> # With LLM-based reflection
        >>> reflector = LLMReflector(llm_func=llm.generate)
        >>> callback = ReflectionCallback(reflector, frequency=5)
        >>> 
        >>> # With simple reflection (no LLM)
        >>> callback = ReflectionCallback(SimpleReflector())
    """

    def __init__(
        self,
        reflector: Optional[ReflectorBase] = None,
        frequency: int = 1,
        store_func: Optional[Callable[[Reflection], None]] = None,
        min_quality_threshold: float = 0.0,
    ):
        self.reflector = reflector or SimpleReflector()
        self.frequency = max(1, frequency)
        self.store_func = store_func
        self.min_quality_threshold = min_quality_threshold

        self._action_count = 0
        self._pending_action: Optional[ActionResult] = None
        self._reflections: List[Reflection] = []

    @property
    def reflections(self) -> List[Reflection]:
        """Get all reflections."""
        return list(self._reflections)

    @property
    def average_quality(self) -> float:
        """Get average quality score."""
        if not self._reflections:
            return 0.0
        return sum(r.quality_score for r in self._reflections) / len(self._reflections)

    def on_llm_start(self, prompt: str, **kwargs) -> None:
        """Record action start."""
        import uuid
        self._pending_action = ActionResult(
            action_id=str(uuid.uuid4()),
            action_type=kwargs.get("action_type", "llm_call"),
            input=prompt,
            output="",
            success=False,
            metadata=kwargs,
        )

    def on_llm_end(self, response: str, **kwargs) -> None:
        """Record action end and potentially reflect."""
        if not self._pending_action:
            return

        self._pending_action.output = response
        self._pending_action.success = True
        self._pending_action.tokens_used = kwargs.get("tokens", 0)
        self._pending_action.latency_ms = kwargs.get("latency_ms", 0)

        self._action_count += 1

        # Check if we should reflect
        if self._action_count % self.frequency == 0:
            self._do_reflect(self._pending_action)

        self._pending_action = None

    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Record action error."""
        if not self._pending_action:
            return

        self._pending_action.output = str(error)
        self._pending_action.success = False
        self._pending_action.metadata["error"] = str(error)

        self._action_count += 1

        # Always reflect on errors
        self._do_reflect(self._pending_action)

        self._pending_action = None

    def _do_reflect(self, action: ActionResult) -> None:
        """Generate and store reflection."""
        try:
            reflection = self.reflector.reflect(action)

            # Check threshold
            if reflection.quality_score >= self.min_quality_threshold:
                self._reflections.append(reflection)

                # Store if provided
                if self.store_func:
                    try:
                        self.store_func(reflection)
                    except Exception as e:
                        logger.warning(f"Failed to store reflection: {e}")

                logger.debug(
                    f"Reflection [{action.action_id[:8]}]: "
                    f"score={reflection.quality_score:.2f}"
                )
        except Exception as e:
            logger.error(f"Reflection failed: {e}")

    def force_reflect(self) -> Optional[Reflection]:
        """Force reflection on pending action."""
        if self._pending_action:
            self._do_reflect(self._pending_action)
            return self._reflections[-1] if self._reflections else None
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Get reflection summary."""
        return {
            "total_actions": self._action_count,
            "total_reflections": len(self._reflections),
            "average_quality": round(self.average_quality, 3),
            "all_improvements": list(set(
                imp for r in self._reflections for imp in r.improvements
            )),
            "all_learnings": list(set(
                l for r in self._reflections for l in r.learnings
            )),
        }

    def clear(self) -> None:
        """Clear all reflections."""
        self._reflections.clear()
        self._action_count = 0


# Integration helper for H-MEM
def create_hmem_store_func(memory_bridge):
    """Create a store function for H-MEM integration.

    Args:
        memory_bridge: RLM Memory Bridge instance

    Returns:
        Function to store reflections in H-MEM

    Example:
        >>> from rlm_toolkit.memory_bridge import MemoryBridge
        >>> bridge = MemoryBridge()
        >>> store_func = create_hmem_store_func(bridge)
        >>> callback = ReflectionCallback(store_func=store_func)
    """
    def store(reflection: Reflection) -> None:
        content = (
            f"Reflection [{reflection.action_id[:8]}]: "
            f"score={reflection.quality_score:.2f}. "
            f"{reflection.analysis}"
        )
        if reflection.learnings:
            content += f" Learnings: {', '.join(reflection.learnings)}"

        memory_bridge.add_fact(
            content=content,
            level=3,  # L3 = episodic
            domain="reflection",
        )

    return store
