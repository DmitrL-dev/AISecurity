"""
Workflow Schema — SENTINEL Automation

Defines the schema for security automation workflows.

Features:
- Trigger conditions
- Action sequences
- Flow control (if/else, loops)
- Integration with rules and audit

Author: SENTINEL Team
Date: 2025-12-16
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger("Workflow")


# ============================================================================
# Enums
# ============================================================================


class TriggerType(Enum):
    """Types of workflow triggers."""

    ON_DETECTION = "on_detection"  # When threat detected
    ON_BLOCK = "on_block"  # When prompt blocked
    ON_HIGH_RISK = "on_high_risk"  # Risk score threshold
    ON_SCHEDULE = "on_schedule"  # Cron schedule
    ON_WEBHOOK = "on_webhook"  # External webhook
    ON_EVENT = "on_event"  # Custom event
    MANUAL = "manual"  # Manual trigger


class ActionType(Enum):
    """Types of workflow actions."""

    # Notifications
    SEND_ALERT = "send_alert"
    SEND_EMAIL = "send_email"
    SEND_SLACK = "send_slack"
    SEND_WEBHOOK = "send_webhook"

    # Security actions
    BLOCK_USER = "block_user"
    QUARANTINE_PROMPT = "quarantine_prompt"
    ESCALATE = "escalate"
    ADD_TO_WATCHLIST = "add_to_watchlist"

    # Data actions
    LOG_EVENT = "log_event"
    CREATE_TICKET = "create_ticket"
    UPDATE_RISK = "update_risk"

    # Flow control
    CONDITION = "condition"
    DELAY = "delay"
    LOOP = "loop"

    # Integrations
    RUN_SCRIPT = "run_script"
    CALL_API = "call_api"


class WorkflowStatus(Enum):
    """Status of workflow."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class ExecutionStatus(Enum):
    """Status of workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Trigger
# ============================================================================


@dataclass
class Trigger:
    """Workflow trigger definition."""

    type: TriggerType
    conditions: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "conditions": self.conditions,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Trigger":
        return cls(
            type=TriggerType(data["type"]),
            conditions=data.get("conditions", {}),
            config=data.get("config", {}),
        )

    def matches(self, event: Dict[str, Any]) -> bool:
        """Check if event matches trigger conditions."""
        if self.type == TriggerType.ON_DETECTION:
            return event.get("threats_detected", []) != []

        elif self.type == TriggerType.ON_BLOCK:
            return event.get("blocked", False)

        elif self.type == TriggerType.ON_HIGH_RISK:
            threshold = self.conditions.get("threshold", 70)
            return event.get("risk_score", 0) >= threshold

        elif self.type == TriggerType.ON_EVENT:
            event_type = self.conditions.get("event_type")
            return event.get("type") == event_type

        elif self.type == TriggerType.MANUAL:
            return event.get("manual_trigger", False)

        return False


# ============================================================================
# Action
# ============================================================================


@dataclass
class Action:
    """Workflow action definition."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: ActionType = ActionType.LOG_EVENT
    params: Dict[str, Any] = field(default_factory=dict)
    on_failure: str = "continue"  # continue, stop, retry
    timeout_seconds: int = 30

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "params": self.params,
            "on_failure": self.on_failure,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            type=ActionType(data["type"]),
            params=data.get("params", {}),
            on_failure=data.get("on_failure", "continue"),
            timeout_seconds=data.get("timeout_seconds", 30),
        )


# ============================================================================
# Workflow
# ============================================================================


@dataclass
class Workflow:
    """
    Complete workflow definition.

    A workflow contains:
    - Trigger: When to run
    - Actions: What to do (in order)
    - Metadata: Name, description, status
    """

    # Identifiers
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Configuration
    trigger: Optional[Trigger] = None
    actions: List[Action] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT

    # Metadata
    author: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1

    # Statistics
    run_count: int = 0
    last_run: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger.to_dict() if self.trigger else None,
            "actions": [a.to_dict() for a in self.actions],
            "status": self.status.value,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Workflow":
        trigger = None
        if data.get("trigger"):
            trigger = Trigger.from_dict(data["trigger"])

        actions = [Action.from_dict(a) for a in data.get("actions", [])]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            trigger=trigger,
            actions=actions,
            status=WorkflowStatus(data.get("status", "draft")),
            author=data.get("author", "system"),
            version=data.get("version", 1),
        )

    def validate(self) -> List[str]:
        """Validate workflow configuration."""
        errors = []

        if not self.name:
            errors.append("Workflow name is required")

        if not self.trigger:
            errors.append("Workflow trigger is required")

        if not self.actions:
            errors.append("At least one action is required")

        return errors


# ============================================================================
# Execution Record
# ============================================================================


@dataclass
class ExecutionRecord:
    """Record of workflow execution."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    trigger_event: Dict[str, Any] = field(default_factory=dict)
    action_results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "action_results": self.action_results,
            "error": self.error,
        }


# ============================================================================
# Workflow Templates
# ============================================================================


def create_alert_on_block_workflow() -> Workflow:
    """Template: Alert security team when prompt blocked."""
    return Workflow(
        name="Alert on Block",
        description="Send Slack alert when a prompt is blocked",
        trigger=Trigger(
            type=TriggerType.ON_BLOCK,
        ),
        actions=[
            Action(
                type=ActionType.SEND_SLACK,
                params={
                    "channel": "#security-alerts",
                    "message": "🚨 Prompt blocked: {{threat_type}}",
                }
            ),
            Action(
                type=ActionType.LOG_EVENT,
                params={"level": "warning"},
            ),
        ],
        status=WorkflowStatus.ACTIVE,
    )


def create_escalation_workflow(threshold: float = 85) -> Workflow:
    """Template: Escalate high-risk detections."""
    return Workflow(
        name=f"Escalate High Risk (>{threshold})",
        description="Create ticket and notify on-call for critical threats",
        trigger=Trigger(
            type=TriggerType.ON_HIGH_RISK,
            conditions={"threshold": threshold},
        ),
        actions=[
            Action(
                type=ActionType.CREATE_TICKET,
                params={
                    "priority": "critical",
                    "team": "security",
                }
            ),
            Action(
                type=ActionType.SEND_WEBHOOK,
                params={
                    "url": "{{pagerduty_webhook}}",
                    "payload": {"severity": "critical"},
                }
            ),
            Action(
                type=ActionType.ADD_TO_WATCHLIST,
                params={"duration_hours": 24},
            ),
        ],
        status=WorkflowStatus.ACTIVE,
    )
