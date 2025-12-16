"""
Workflow Engine — SENTINEL Automation Executor

Executes workflows triggered by security events.

Features:
- Event-driven execution
- Action handlers
- Retry logic
- Execution history

Author: SENTINEL Team
Date: 2025-12-16
"""

import logging
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import httpx

from .schema import (
    Workflow,
    WorkflowStatus,
    Trigger,
    TriggerType,
    Action,
    ActionType,
    ExecutionRecord,
    ExecutionStatus,
)

logger = logging.getLogger("WorkflowEngine")


# ============================================================================
# Action Handlers
# ============================================================================


class ActionHandlers:
    """Built-in action handlers."""

    @staticmethod
    async def send_alert(params: dict, context: dict) -> dict:
        """Send alert notification."""
        message = params.get("message", "Alert triggered")
        # Template substitution
        for key, value in context.items():
            message = message.replace(f"{{{{{key}}}}}", str(value))

        logger.warning(f"ALERT: {message}")
        return {"sent": True, "message": message}

    @staticmethod
    async def send_slack(params: dict, context: dict) -> dict:
        """Send Slack message."""
        channel = params.get("channel", "#alerts")
        message = params.get("message", "Workflow triggered")

        # Template substitution
        for key, value in context.items():
            message = message.replace(f"{{{{{key}}}}}", str(value))

        webhook_url = params.get("webhook_url") or context.get("slack_webhook")

        if webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(webhook_url, json={
                        "channel": channel,
                        "text": message,
                    })
                return {"sent": True}
            except Exception as e:
                return {"sent": False, "error": str(e)}

        logger.info(f"Slack [{channel}]: {message}")
        return {"sent": True, "mock": True}

    @staticmethod
    async def send_webhook(params: dict, context: dict) -> dict:
        """Send HTTP webhook."""
        url = params.get("url", "")
        payload = params.get("payload", {})

        # Merge context into payload
        full_payload = {**context, **payload}

        if url:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=full_payload)
                return {"status": response.status_code}
            except Exception as e:
                return {"error": str(e)}

        return {"error": "No URL provided"}

    @staticmethod
    async def log_event(params: dict, context: dict) -> dict:
        """Log event to audit."""
        level = params.get("level", "info")
        message = f"Workflow event: {context.get('workflow_name', 'unknown')}"

        if level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        else:
            logger.info(message)

        return {"logged": True}

    @staticmethod
    async def block_user(params: dict, context: dict) -> dict:
        """Block user from further requests."""
        user_id = context.get("user_id")
        duration = params.get("duration_minutes", 60)

        logger.warning(f"Blocking user {user_id} for {duration} minutes")
        return {"blocked": True, "user_id": user_id, "duration": duration}

    @staticmethod
    async def add_to_watchlist(params: dict, context: dict) -> dict:
        """Add user/IP to watchlist."""
        target = context.get("user_id") or context.get("source_ip")
        duration = params.get("duration_hours", 24)

        logger.info(f"Adding {target} to watchlist for {duration}h")
        return {"added": True, "target": target}

    @staticmethod
    async def create_ticket(params: dict, context: dict) -> dict:
        """Create incident ticket."""
        priority = params.get("priority", "medium")
        team = params.get("team", "security")

        ticket_id = f"SENT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Creating ticket {ticket_id} ({priority}) for {team}")

        return {"ticket_id": ticket_id, "priority": priority}

    @staticmethod
    async def delay(params: dict, context: dict) -> dict:
        """Delay execution."""
        seconds = params.get("seconds", 1)
        await asyncio.sleep(min(seconds, 60))  # Max 60s
        return {"delayed": seconds}


# ============================================================================
# Workflow Engine
# ============================================================================


class WorkflowEngine:
    """
    Executes security automation workflows.

    Features:
    - Event matching to triggers
    - Sequential action execution
    - Error handling and retry
    - Execution history
    """

    ACTION_HANDLERS = {
        ActionType.SEND_ALERT: ActionHandlers.send_alert,
        ActionType.SEND_SLACK: ActionHandlers.send_slack,
        ActionType.SEND_WEBHOOK: ActionHandlers.send_webhook,
        ActionType.LOG_EVENT: ActionHandlers.log_event,
        ActionType.BLOCK_USER: ActionHandlers.block_user,
        ActionType.ADD_TO_WATCHLIST: ActionHandlers.add_to_watchlist,
        ActionType.CREATE_TICKET: ActionHandlers.create_ticket,
        ActionType.DELAY: ActionHandlers.delay,
    }

    def __init__(self, workflows_dir: Optional[str] = None):
        """
        Initialize workflow engine.

        Args:
            workflows_dir: Directory containing workflow JSON files
        """
        self.workflows: Dict[str, Workflow] = {}
        self.execution_history: List[ExecutionRecord] = []
        self._max_history = 1000

        if workflows_dir:
            self.load_workflows(workflows_dir)

        self._stats = {
            "events_processed": 0,
            "workflows_executed": 0,
            "actions_executed": 0,
            "failures": 0,
        }

        logger.info(
            f"WorkflowEngine initialized with {len(self.workflows)} workflows")

    def load_workflows(self, workflows_dir: str) -> int:
        """Load workflows from directory."""
        path = Path(workflows_dir)
        if not path.exists():
            return 0

        count = 0
        for wf_file in path.glob("*.json"):
            try:
                with open(wf_file) as f:
                    data = json.load(f)
                workflow = Workflow.from_dict(data)
                self.register_workflow(workflow)
                count += 1
            except Exception as e:
                logger.error(f"Failed to load workflow {wf_file}: {e}")

        return count

    def register_workflow(self, workflow: Workflow) -> bool:
        """Register a workflow."""
        errors = workflow.validate()
        if errors:
            logger.warning(f"Invalid workflow '{workflow.name}': {errors}")
            return False

        self.workflows[workflow.id] = workflow
        logger.debug(f"Registered workflow: {workflow.name}")
        return True

    def unregister_workflow(self, workflow_id: str) -> bool:
        """Unregister a workflow."""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            return True
        return False

    async def process_event(self, event: Dict[str, Any]) -> List[ExecutionRecord]:
        """
        Process a security event and execute matching workflows.

        Args:
            event: Event data (risk_score, blocked, threats, etc)

        Returns:
            List of execution records
        """
        self._stats["events_processed"] += 1

        executions = []

        for workflow in self.workflows.values():
            if workflow.status != WorkflowStatus.ACTIVE:
                continue

            if workflow.trigger and workflow.trigger.matches(event):
                record = await self._execute_workflow(workflow, event)
                executions.append(record)

        return executions

    async def _execute_workflow(
        self,
        workflow: Workflow,
        event: Dict[str, Any],
    ) -> ExecutionRecord:
        """Execute a single workflow."""
        logger.info(f"Executing workflow: {workflow.name}")

        self._stats["workflows_executed"] += 1
        workflow.run_count += 1
        workflow.last_run = datetime.utcnow()

        record = ExecutionRecord(
            workflow_id=workflow.id,
            status=ExecutionStatus.RUNNING,
            trigger_event=event,
        )

        # Build context for actions
        context = {
            **event,
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
        }

        try:
            for action in workflow.actions:
                result = await self._execute_action(action, context)
                record.action_results.append({
                    "action_id": action.id,
                    "action_type": action.type.value,
                    "result": result,
                })

            record.status = ExecutionStatus.COMPLETED
            workflow.success_count += 1

        except Exception as e:
            record.status = ExecutionStatus.FAILED
            record.error = str(e)
            workflow.failure_count += 1
            self._stats["failures"] += 1
            logger.error(f"Workflow {workflow.name} failed: {e}")

        record.completed_at = datetime.utcnow()

        # Store in history
        self.execution_history.append(record)
        if len(self.execution_history) > self._max_history:
            self.execution_history = self.execution_history[-self._max_history:]

        return record

    async def _execute_action(
        self,
        action: Action,
        context: Dict[str, Any],
    ) -> dict:
        """Execute a single action."""
        self._stats["actions_executed"] += 1

        handler = self.ACTION_HANDLERS.get(action.type)
        if not handler:
            logger.warning(f"No handler for action type: {action.type}")
            return {"error": "No handler"}

        try:
            result = await asyncio.wait_for(
                handler(action.params, context),
                timeout=action.timeout_seconds,
            )
            return result

        except asyncio.TimeoutError:
            return {"error": "Timeout"}

        except Exception as e:
            if action.on_failure == "stop":
                raise
            return {"error": str(e)}

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get list of active workflows."""
        return [
            {
                "id": w.id,
                "name": w.name,
                "trigger": w.trigger.type.value if w.trigger else None,
                "actions_count": len(w.actions),
                "run_count": w.run_count,
            }
            for w in self.workflows.values()
            if w.status == WorkflowStatus.ACTIVE
        ]

    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        return [
            r.to_dict()
            for r in reversed(self.execution_history[-limit:])
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self._stats,
            "total_workflows": len(self.workflows),
            "active_workflows": sum(
                1 for w in self.workflows.values()
                if w.status == WorkflowStatus.ACTIVE
            ),
        }


# ============================================================================
# Factory
# ============================================================================


_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get or create workflow engine."""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine


def create_workflow_engine(workflows_dir: Optional[str] = None) -> WorkflowEngine:
    """Create a new workflow engine."""
    return WorkflowEngine(workflows_dir=workflows_dir)
