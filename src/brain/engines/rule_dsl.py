"""
SENTINEL Rule DSL - Declarative Security Rule Engine

Inspired by NeMo-Guardrails Colang 2.0 but focused on security:
- Declarative rule definitions
- Event-based triggers
- Pattern matching on inputs/outputs
- Action composition

Part of SENTINEL's Rule Layer.

Author: SENTINEL Team
Engine ID: 192
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from abc import ABC, abstractmethod

logger = logging.getLogger("SentinelRuleDSL")


# ============================================================================
# Enums
# ============================================================================

class RulePriority(Enum):
    """Rule execution priority."""
    CRITICAL = 100
    HIGH = 75
    MEDIUM = 50
    LOW = 25
    INFO = 10


class RuleSeverity(Enum):
    """Detection severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TriggerType(Enum):
    """Types of rule triggers."""
    INPUT = "input"       # Trigger on user input
    OUTPUT = "output"     # Trigger on LLM output
    CONTEXT = "context"   # Trigger on context changes
    EVENT = "event"       # Trigger on system events
    ALWAYS = "always"     # Always run


class ActionType(Enum):
    """Types of rule actions."""
    BLOCK = "block"           # Block the request
    ALERT = "alert"           # Send alert
    LOG = "log"               # Log the event
    MODIFY = "modify"         # Modify input/output
    ESCALATE = "escalate"     # Escalate to meta-judge
    ACTIVATE = "activate"     # Activate another engine


# ============================================================================
# AST Data Classes (Colang-inspired)
# ============================================================================

@dataclass
class Condition:
    """A condition for rule matching."""
    field: str                      # Field to check (input, output, context.*)
    operator: str                   # Operator (matches, contains, equals, >, <, etc.)
    value: Any                      # Value to compare against
    negate: bool = False            # Negate the condition


@dataclass
class Action:
    """An action to execute when rule triggers."""
    action_type: ActionType
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule:
    """A security detection rule."""
    name: str
    description: str = ""
    priority: RulePriority = RulePriority.MEDIUM
    trigger: TriggerType = TriggerType.INPUT
    conditions: List[Condition] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    severity: RuleSeverity = RuleSeverity.MEDIUM
    tags: Set[str] = field(default_factory=set)
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "priority": self.priority.name,
            "trigger": self.trigger.value,
            "severity": self.severity.value,
            "conditions": len(self.conditions),
            "actions": len(self.actions),
            "tags": list(self.tags),
            "enabled": self.enabled,
        }


@dataclass 
class RuleExecutionResult:
    """Result of rule execution."""
    rule_name: str
    triggered: bool
    severity: RuleSeverity
    matched_conditions: List[str] = field(default_factory=list)
    actions_executed: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Condition Matchers
# ============================================================================

class ConditionMatcher:
    """Evaluates conditions against context."""
    
    OPERATORS = {
        "matches": "_match_regex",
        "contains": "_match_contains",
        "equals": "_match_equals",
        "startswith": "_match_startswith",
        "endswith": "_match_endswith",
        "gt": "_match_gt",
        "lt": "_match_lt",
        "gte": "_match_gte",
        "lte": "_match_lte",
        "in": "_match_in",
        "similarity": "_match_similarity",
    }
    
    def evaluate(self, condition: Condition, context: Dict[str, Any]) -> bool:
        """Evaluate a condition against context."""
        # Get field value from context
        field_value = self._get_field_value(condition.field, context)
        
        if field_value is None:
            return condition.negate
        
        # Get matcher method
        method_name = self.OPERATORS.get(condition.operator)
        if not method_name:
            logger.warning(f"Unknown operator: {condition.operator}")
            return False
        
        method = getattr(self, method_name, None)
        if not method:
            return False
        
        result = method(field_value, condition.value)
        return not result if condition.negate else result
    
    def _get_field_value(
        self, 
        field: str, 
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """Get nested field value from context."""
        parts = field.split(".")
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            
            if value is None:
                return None
        
        return value
    
    def _match_regex(self, value: str, pattern: str) -> bool:
        """Match value against regex pattern."""
        if not isinstance(value, str):
            return False
        try:
            return bool(re.search(pattern, value, re.IGNORECASE))
        except re.error:
            return False
    
    def _match_contains(self, value: str, substring: str) -> bool:
        """Check if value contains substring."""
        if not isinstance(value, str):
            return False
        return substring.lower() in value.lower()
    
    def _match_equals(self, value: Any, expected: Any) -> bool:
        """Check equality."""
        return value == expected
    
    def _match_startswith(self, value: str, prefix: str) -> bool:
        """Check if value starts with prefix."""
        if not isinstance(value, str):
            return False
        return value.lower().startswith(prefix.lower())
    
    def _match_endswith(self, value: str, suffix: str) -> bool:
        """Check if value ends with suffix."""
        if not isinstance(value, str):
            return False
        return value.lower().endswith(suffix.lower())
    
    def _match_gt(self, value: float, threshold: float) -> bool:
        """Check if value > threshold."""
        try:
            return float(value) > float(threshold)
        except (ValueError, TypeError):
            return False
    
    def _match_lt(self, value: float, threshold: float) -> bool:
        """Check if value < threshold."""
        try:
            return float(value) < float(threshold)
        except (ValueError, TypeError):
            return False
    
    def _match_gte(self, value: float, threshold: float) -> bool:
        """Check if value >= threshold."""
        try:
            return float(value) >= float(threshold)
        except (ValueError, TypeError):
            return False
    
    def _match_lte(self, value: float, threshold: float) -> bool:
        """Check if value <= threshold."""
        try:
            return float(value) <= float(threshold)
        except (ValueError, TypeError):
            return False
    
    def _match_in(self, value: Any, collection: List[Any]) -> bool:
        """Check if value is in collection."""
        return value in collection
    
    def _match_similarity(self, value: str, params: Dict[str, Any]) -> bool:
        """Check semantic similarity (placeholder)."""
        # Would integrate with embedding engine
        threshold = params.get("threshold", 0.85)
        # Placeholder - would use actual similarity
        return False


# ============================================================================
# Action Executor
# ============================================================================

class ActionExecutor:
    """Executes rule actions."""
    
    def __init__(self):
        self.handlers: Dict[ActionType, Callable] = {
            ActionType.BLOCK: self._execute_block,
            ActionType.ALERT: self._execute_alert,
            ActionType.LOG: self._execute_log,
            ActionType.MODIFY: self._execute_modify,
            ActionType.ESCALATE: self._execute_escalate,
            ActionType.ACTIVATE: self._execute_activate,
        }
        self.action_log: List[str] = []
    
    def execute(
        self, 
        action: Action, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an action."""
        handler = self.handlers.get(action.action_type)
        if not handler:
            logger.warning(f"Unknown action type: {action.action_type}")
            return {"success": False, "error": "Unknown action"}
        
        result = handler(action.parameters, context)
        self.action_log.append(f"{action.action_type.value}: {result}")
        return result
    
    def _execute_block(
        self, 
        params: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Block the request."""
        message = params.get("message", "Request blocked by security rule")
        return {
            "success": True,
            "blocked": True,
            "message": message,
        }
    
    def _execute_alert(
        self, 
        params: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send an alert."""
        severity = params.get("severity", "medium")
        message = params.get("message", "Security alert triggered")
        logger.warning(f"[ALERT][{severity}] {message}")
        return {
            "success": True,
            "alert_sent": True,
            "severity": severity,
        }
    
    def _execute_log(
        self, 
        params: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Log the event."""
        message = params.get("message", "Security event logged")
        logger.info(f"[LOG] {message}")
        return {
            "success": True,
            "logged": True,
        }
    
    def _execute_modify(
        self, 
        params: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Modify input/output."""
        field = params.get("field", "input")
        replacement = params.get("replacement", "[REDACTED]")
        return {
            "success": True,
            "modified": True,
            "field": field,
            "replacement": replacement,
        }
    
    def _execute_escalate(
        self, 
        params: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Escalate to meta-judge."""
        return {
            "success": True,
            "escalated": True,
            "target": "meta_judge",
        }
    
    def _execute_activate(
        self, 
        params: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Activate another engine."""
        engine = params.get("engine", "unknown")
        return {
            "success": True,
            "activated": engine,
        }


# ============================================================================
# Main Rule Engine
# ============================================================================

class SentinelRuleEngine:
    """
    SENTINEL Declarative Rule Engine.
    
    Inspired by NeMo-Guardrails Colang 2.0 but focused on security:
    - Declarative rule definitions
    - Event-based triggers
    - Pattern matching
    - Action composition
    """
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.matcher = ConditionMatcher()
        self.executor = ActionExecutor()
        
        # Built-in security patterns
        self._register_builtin_rules()
    
    @property
    def name(self) -> str:
        return "sentinel_rule_engine"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def register_rule(self, rule: Rule) -> None:
        """Register a rule with the engine."""
        self.rules[rule.name] = rule
        logger.info(f"Registered rule: {rule.name}")
    
    def unregister_rule(self, name: str) -> bool:
        """Unregister a rule by name."""
        if name in self.rules:
            del self.rules[name]
            return True
        return False
    
    def evaluate(
        self, 
        context: Dict[str, Any],
        trigger_type: TriggerType = TriggerType.INPUT,
    ) -> List[RuleExecutionResult]:
        """
        Evaluate all rules against context.
        
        Args:
            context: Dictionary with input, output, and metadata
            trigger_type: Type of trigger to filter rules
            
        Returns:
            List of execution results for triggered rules
        """
        results = []
        
        # Get applicable rules sorted by priority
        applicable_rules = [
            r for r in self.rules.values()
            if r.enabled and (r.trigger == trigger_type or r.trigger == TriggerType.ALWAYS)
        ]
        applicable_rules.sort(key=lambda r: r.priority.value, reverse=True)
        
        for rule in applicable_rules:
            result = self._evaluate_rule(rule, context)
            if result.triggered:
                results.append(result)
        
        return results
    
    def _evaluate_rule(
        self, 
        rule: Rule, 
        context: Dict[str, Any]
    ) -> RuleExecutionResult:
        """Evaluate a single rule."""
        matched_conditions = []
        all_matched = True
        
        # Check all conditions (AND logic)
        for condition in rule.conditions:
            if self.matcher.evaluate(condition, context):
                matched_conditions.append(
                    f"{condition.field} {condition.operator} {condition.value}"
                )
            else:
                all_matched = False
                break
        
        # If all conditions matched, execute actions
        actions_executed = []
        if all_matched and matched_conditions:
            for action in rule.actions:
                result = self.executor.execute(action, context)
                actions_executed.append(
                    f"{action.action_type.value}: {result.get('success', False)}"
                )
        
        return RuleExecutionResult(
            rule_name=rule.name,
            triggered=all_matched and len(matched_conditions) > 0,
            severity=rule.severity,
            matched_conditions=matched_conditions,
            actions_executed=actions_executed,
            metadata={"priority": rule.priority.name},
        )
    
    def _register_builtin_rules(self) -> None:
        """Register built-in security rules."""
        
        # Rule 1: Basic injection detection
        self.register_rule(Rule(
            name="basic_injection",
            description="Detect basic prompt injection patterns",
            priority=RulePriority.HIGH,
            trigger=TriggerType.INPUT,
            severity=RuleSeverity.HIGH,
            conditions=[
                Condition(
                    field="input",
                    operator="matches",
                    value=r"(?i)(ignore|disregard|forget)\s+(previous|above|all)",
                ),
            ],
            actions=[
                Action(ActionType.LOG, {"message": "Injection attempt detected"}),
                Action(ActionType.ALERT, {"severity": "high"}),
                Action(ActionType.BLOCK, {"message": "Potential injection blocked"}),
            ],
            tags={"injection", "builtin"},
        ))
        
        # Rule 2: System prompt extraction
        self.register_rule(Rule(
            name="system_prompt_extraction",
            description="Detect attempts to extract system prompt",
            priority=RulePriority.HIGH,
            trigger=TriggerType.INPUT,
            severity=RuleSeverity.HIGH,
            conditions=[
                Condition(
                    field="input",
                    operator="matches",
                    value=r"(?i)(show|reveal|print|display|output)\s+(your\s+)?(system|initial)\s+(prompt|instructions)",
                ),
            ],
            actions=[
                Action(ActionType.LOG, {"message": "System prompt extraction attempt"}),
                Action(ActionType.BLOCK, {"message": "Cannot reveal system prompt"}),
            ],
            tags={"extraction", "builtin"},
        ))
        
        # Rule 3: Jailbreak patterns
        self.register_rule(Rule(
            name="jailbreak_patterns",
            description="Detect common jailbreak patterns",
            priority=RulePriority.CRITICAL,
            trigger=TriggerType.INPUT,
            severity=RuleSeverity.CRITICAL,
            conditions=[
                Condition(
                    field="input",
                    operator="matches",
                    value=r"(?i)(DAN|developer\s+mode|jailbreak|bypass\s+restrictions)",
                ),
            ],
            actions=[
                Action(ActionType.ALERT, {"severity": "critical"}),
                Action(ActionType.ESCALATE, {}),
                Action(ActionType.BLOCK, {"message": "Jailbreak attempt blocked"}),
            ],
            tags={"jailbreak", "builtin"},
        ))
        
        # Rule 4: Output leakage detection
        self.register_rule(Rule(
            name="output_leakage",
            description="Detect potential data leakage in output",
            priority=RulePriority.MEDIUM,
            trigger=TriggerType.OUTPUT,
            severity=RuleSeverity.MEDIUM,
            conditions=[
                Condition(
                    field="output",
                    operator="matches",
                    value=r"(?i)(password|api[_\s]?key|secret|token)\s*[:=]\s*\S+",
                ),
            ],
            actions=[
                Action(ActionType.LOG, {"message": "Potential data leakage in output"}),
                Action(ActionType.MODIFY, {
                    "field": "output",
                    "replacement": "[SENSITIVE DATA REDACTED]",
                }),
            ],
            tags={"leakage", "builtin"},
        ))
    
    def get_rule_stats(self) -> Dict[str, Any]:
        """Get statistics about registered rules."""
        by_priority = {}
        by_trigger = {}
        by_severity = {}
        
        for rule in self.rules.values():
            by_priority[rule.priority.name] = by_priority.get(
                rule.priority.name, 0
            ) + 1
            by_trigger[rule.trigger.value] = by_trigger.get(
                rule.trigger.value, 0
            ) + 1
            by_severity[rule.severity.value] = by_severity.get(
                rule.severity.value, 0
            ) + 1
        
        return {
            "total_rules": len(self.rules),
            "by_priority": by_priority,
            "by_trigger": by_trigger,
            "by_severity": by_severity,
        }
    
    def health_check(self) -> bool:
        """Check engine health."""
        try:
            context = {"input": "test message"}
            self.evaluate(context)
            return True
        except Exception:
            return False


# ============================================================================
# Rule Builder (Fluent API)
# ============================================================================

class RuleBuilder:
    """Fluent API for building rules."""
    
    def __init__(self, name: str):
        self._rule = Rule(name=name)
    
    def description(self, desc: str) -> "RuleBuilder":
        self._rule.description = desc
        return self
    
    def priority(self, p: RulePriority) -> "RuleBuilder":
        self._rule.priority = p
        return self
    
    def trigger(self, t: TriggerType) -> "RuleBuilder":
        self._rule.trigger = t
        return self
    
    def severity(self, s: RuleSeverity) -> "RuleBuilder":
        self._rule.severity = s
        return self
    
    def when(
        self, 
        field: str, 
        operator: str, 
        value: Any,
        negate: bool = False
    ) -> "RuleBuilder":
        self._rule.conditions.append(Condition(
            field=field,
            operator=operator,
            value=value,
            negate=negate,
        ))
        return self
    
    def then_block(self, message: str = "Blocked") -> "RuleBuilder":
        self._rule.actions.append(Action(
            ActionType.BLOCK, 
            {"message": message}
        ))
        return self
    
    def then_alert(self, severity: str = "medium") -> "RuleBuilder":
        self._rule.actions.append(Action(
            ActionType.ALERT,
            {"severity": severity}
        ))
        return self
    
    def then_log(self, message: str) -> "RuleBuilder":
        self._rule.actions.append(Action(
            ActionType.LOG,
            {"message": message}
        ))
        return self
    
    def then_escalate(self) -> "RuleBuilder":
        self._rule.actions.append(Action(ActionType.ESCALATE, {}))
        return self
    
    def then_activate(self, engine: str) -> "RuleBuilder":
        self._rule.actions.append(Action(
            ActionType.ACTIVATE,
            {"engine": engine}
        ))
        return self
    
    def tags(self, *tags: str) -> "RuleBuilder":
        self._rule.tags = set(tags)
        return self
    
    def build(self) -> Rule:
        return self._rule


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "SentinelRuleEngine",
    "RuleBuilder",
    "Rule",
    "Condition",
    "Action",
    "RulePriority",
    "RuleSeverity",
    "TriggerType",
    "ActionType",
    "RuleExecutionResult",
]
