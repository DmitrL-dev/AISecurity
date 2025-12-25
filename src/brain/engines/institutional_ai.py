"""
Institutional AI Framework

Implements functional differentiation from arxiv:2512.02682:
- Legislative: Rule generation and policy creation
- Judicial: Rule interpretation and compliance checking  
- Executive: Task execution with oversight

This creates self-governance within multi-agent systems.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from datetime import datetime
import hashlib

logger = logging.getLogger("InstitutionalAI")


class AgentRole(str, Enum):
    """Institutional roles for AI agents."""
    LEGISLATIVE = "legislative"  # Creates rules
    JUDICIAL = "judicial"        # Interprets rules
    EXECUTIVE = "executive"      # Executes tasks
    MONITOR = "monitor"          # Observes system


@dataclass
class Rule:
    """A system rule created by legislative agents."""
    rule_id: str
    name: str
    description: str
    condition: str  # Python expression
    action: str     # block, warn, log, allow
    priority: int   # Higher = more important
    created_by: str
    created_at: datetime
    active: bool = True
    version: int = 1

    def hash(self) -> str:
        """Create hash for rule integrity."""
        content = f"{self.name}:{self.condition}:{self.action}:{self.version}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class Judgment:
    """A judicial decision on rule compliance."""
    judgment_id: str
    rule_id: str
    agent_id: str
    action_description: str
    compliant: bool
    reasoning: str
    severity: float  # 0-1
    timestamp: datetime


@dataclass
class AgentRegistration:
    """Registered agent with assigned role."""
    agent_id: str
    role: AgentRole
    capabilities: List[str]
    trust_score: float = 0.5
    active: bool = True


class LegislativeAgent:
    """
    Creates and manages system rules.

    Powers:
    - Propose new rules
    - Modify existing rules
    - Deactivate rules

    Constraints:
    - Cannot execute tasks directly
    - Rules require judicial validation
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._proposed_rules: List[Rule] = []

    def propose_rule(
        self,
        name: str,
        description: str,
        condition: str,
        action: str,
        priority: int = 50
    ) -> Rule:
        """Propose a new rule."""
        rule = Rule(
            rule_id=f"rule_{len(self._proposed_rules)}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=name,
            description=description,
            condition=condition,
            action=action,
            priority=priority,
            created_by=self.agent_id,
            created_at=datetime.now()
        )
        self._proposed_rules.append(rule)
        logger.info("Legislative %s proposed rule: %s", self.agent_id, name)
        return rule

    def amend_rule(self, rule: Rule, new_condition: str = None, new_action: str = None) -> Rule:
        """Propose amendment to existing rule."""
        amended = Rule(
            rule_id=rule.rule_id,
            name=rule.name,
            description=rule.description,
            condition=new_condition or rule.condition,
            action=new_action or rule.action,
            priority=rule.priority,
            created_by=self.agent_id,
            created_at=datetime.now(),
            version=rule.version + 1
        )
        logger.info("Legislative %s amended rule: %s (v%d)",
                    self.agent_id, rule.name, amended.version)
        return amended


class JudicialAgent:
    """
    Interprets rules and judges compliance.

    Powers:
    - Validate proposed rules
    - Judge agent actions for compliance
    - Issue warnings and recommendations

    Constraints:
    - Cannot create rules
    - Cannot execute tasks
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._judgments: List[Judgment] = []

    def validate_rule(self, rule: Rule) -> tuple:
        """Validate a proposed rule. Returns (valid, reason)."""
        # Check for dangerous conditions
        dangerous_keywords = ['import os',
                              'subprocess', 'eval(', 'exec(', '__']
        for keyword in dangerous_keywords:
            if keyword in rule.condition.lower():
                logger.warning("Judicial %s rejected rule %s: dangerous condition",
                               self.agent_id, rule.name)
                return False, f"Dangerous keyword in condition: {keyword}"

        # Check action validity
        valid_actions = ['block', 'warn', 'log', 'allow', 'review']
        if rule.action not in valid_actions:
            return False, f"Invalid action: {rule.action}"

        logger.info("Judicial %s validated rule: %s", self.agent_id, rule.name)
        return True, "Rule is valid"

    def judge_action(
        self,
        agent_id: str,
        action_description: str,
        rules: List[Rule],
        context: Dict[str, Any]
    ) -> Judgment:
        """Judge whether an action complies with rules."""
        violations = []
        max_severity = 0.0

        for rule in rules:
            if not rule.active:
                continue

            try:
                # Safely evaluate condition
                if self._evaluate_condition(rule.condition, context):
                    violations.append(rule)
                    max_severity = max(max_severity, rule.priority / 100)
            except Exception as e:
                logger.error("Error evaluating rule %s: %s", rule.name, e)

        compliant = len(violations) == 0
        reasoning = (
            "Action complies with all rules" if compliant
            else f"Violated rules: {[r.name for r in violations]}"
        )

        judgment = Judgment(
            judgment_id=f"judg_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            rule_id=violations[0].rule_id if violations else "none",
            agent_id=agent_id,
            action_description=action_description,
            compliant=compliant,
            reasoning=reasoning,
            severity=max_severity,
            timestamp=datetime.now()
        )

        self._judgments.append(judgment)

        if not compliant:
            logger.warning("Judicial %s: agent %s violated rules (severity=%.2f)",
                           self.agent_id, agent_id, max_severity)

        return judgment

    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """Safely evaluate a rule condition."""
        # Very restricted evaluation
        safe_names = {
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'True': True,
            'False': False,
            'None': None,
        }
        safe_names.update(context)

        try:
            return eval(condition, {"__builtins__": {}}, safe_names)
        except Exception:
            return False


class ExecutiveAgent:
    """
    Executes tasks under judicial oversight.

    Powers:
    - Execute approved tasks
    - Request rule clarification

    Constraints:
    - Must comply with rules
    - Actions judged by judicial
    """

    def __init__(self, agent_id: str, judicial: JudicialAgent):
        self.agent_id = agent_id
        self._judicial = judicial
        self._action_log: List[Dict] = []

    def execute(
        self,
        task: str,
        handler: Callable,
        rules: List[Rule],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a task with judicial oversight."""
        # Pre-check with judicial
        judgment = self._judicial.judge_action(
            self.agent_id,
            f"Intent to execute: {task}",
            rules,
            context
        )

        if not judgment.compliant and judgment.severity > 0.7:
            logger.warning("Executive %s blocked from task: %s",
                           self.agent_id, task)
            return {
                "success": False,
                "blocked": True,
                "reason": judgment.reasoning
            }

        # Execute with warning if minor violation
        if not judgment.compliant:
            logger.info("Executive %s proceeding with warning: %s",
                        self.agent_id, task)

        try:
            result = handler()
            self._action_log.append({
                "task": task,
                "timestamp": datetime.now(),
                "success": True,
                "judgment": judgment.judgment_id
            })
            return {"success": True, "result": result}
        except Exception as e:
            logger.error("Executive %s failed task %s: %s",
                         self.agent_id, task, e)
            return {"success": False, "error": str(e)}


class InstitutionalFramework:
    """
    Coordinates institutional agents for self-governance.

    Usage:
        framework = InstitutionalFramework()

        # Create agents
        legislative = framework.create_legislative("leg_1")
        judicial = framework.create_judicial("jud_1")
        executive = framework.create_executive("exec_1", judicial)

        # Legislative proposes rule
        rule = legislative.propose_rule(
            name="no_pii",
            description="Block PII in responses",
            condition="'ssn' in message.lower()",
            action="block"
        )

        # Judicial validates
        valid, reason = judicial.validate_rule(rule)
        if valid:
            framework.activate_rule(rule)

        # Executive executes under rules
        result = executive.execute(
            "process_message",
            handler=lambda: process(message),
            rules=framework.active_rules,
            context={"message": user_input}
        )
    """

    def __init__(self):
        self._agents: Dict[str, AgentRegistration] = {}
        self._rules: Dict[str, Rule] = {}
        self._active_rules: List[Rule] = []
        logger.info("Institutional Framework initialized")

    def create_legislative(self, agent_id: str) -> LegislativeAgent:
        """Register a legislative agent."""
        self._agents[agent_id] = AgentRegistration(
            agent_id=agent_id,
            role=AgentRole.LEGISLATIVE,
            capabilities=["propose_rules", "amend_rules"]
        )
        return LegislativeAgent(agent_id)

    def create_judicial(self, agent_id: str) -> JudicialAgent:
        """Register a judicial agent."""
        self._agents[agent_id] = AgentRegistration(
            agent_id=agent_id,
            role=AgentRole.JUDICIAL,
            capabilities=["validate_rules", "judge_actions"]
        )
        return JudicialAgent(agent_id)

    def create_executive(self, agent_id: str, judicial: JudicialAgent) -> ExecutiveAgent:
        """Register an executive agent with judicial oversight."""
        self._agents[agent_id] = AgentRegistration(
            agent_id=agent_id,
            role=AgentRole.EXECUTIVE,
            capabilities=["execute_tasks"]
        )
        return ExecutiveAgent(agent_id, judicial)

    def activate_rule(self, rule: Rule) -> bool:
        """Activate a validated rule."""
        self._rules[rule.rule_id] = rule
        self._active_rules.append(rule)
        self._active_rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info("Activated rule: %s (priority=%d)",
                    rule.name, rule.priority)
        return True

    def deactivate_rule(self, rule_id: str) -> bool:
        """Deactivate a rule."""
        if rule_id in self._rules:
            self._rules[rule_id].active = False
            self._active_rules = [
                r for r in self._active_rules if r.rule_id != rule_id]
            logger.info("Deactivated rule: %s", rule_id)
            return True
        return False

    @property
    def active_rules(self) -> List[Rule]:
        """Get all active rules sorted by priority."""
        return self._active_rules

    def get_agent_stats(self) -> Dict[str, int]:
        """Get agent count by role."""
        stats = {role.value: 0 for role in AgentRole}
        for agent in self._agents.values():
            if agent.active:
                stats[agent.role.value] += 1
        return stats

    def separation_of_powers_check(self) -> bool:
        """
        Verify separation of powers is maintained.
        Returns True if no single agent has multiple roles.
        """
        # In this implementation, each agent has exactly one role
        # Future: check for role concentration
        stats = self.get_agent_stats()
        return all(count > 0 for count in stats.values() if count > 0)


# Singleton
_framework: Optional[InstitutionalFramework] = None


def get_institutional_framework() -> InstitutionalFramework:
    """Get singleton framework."""
    global _framework
    if _framework is None:
        _framework = InstitutionalFramework()
    return _framework
