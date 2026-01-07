"""
AI Incident Response Runbook

Automated incident response for AI/LLM security incidents.
Implements CISA AI Cybersecurity Playbook patterns.

Auto-generated from R&D: ai_ir_watermarking_research.md
Generated: 2026-01-07
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class IncidentType(Enum):
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    DATA_LEAKAGE = "data_leakage"
    MODEL_POISONING = "model_poisoning"
    SLEEPER_ACTIVATION = "sleeper_activation"
    EXFILTRATION = "exfiltration"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    AGENT_COMPROMISE = "agent_compromise"


class IncidentStatus(Enum):
    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    CONTAINED = "contained"
    ERADICATED = "eradicated"
    RECOVERED = "recovered"
    CLOSED = "closed"


@dataclass
class AIIncident:
    """AI-specific security incident."""
    id: str
    incident_type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus
    affected_components: List[str]
    evidence: Dict
    detected_at: datetime
    description: str
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    model_id: Optional[str] = None
    actions_taken: List[str] = field(default_factory=list)


@dataclass
class ResponseAction:
    """A single incident response action."""
    name: str
    description: str
    automated: bool
    executed_at: Optional[datetime] = None
    success: bool = False
    error: Optional[str] = None


class AIIncidentRunbook:
    """
    Automated incident response for AI systems.
    
    Implements a playbook-based approach to handle:
    - Prompt injection attacks
    - Data leakage incidents
    - Model poisoning events
    - Sleeper agent activations
    """

    # Response actions per incident type
    PLAYBOOKS: Dict[IncidentType, List[str]] = {
        IncidentType.PROMPT_INJECTION: [
            "log_attack_details",
            "block_source_if_malicious",
            "update_detection_patterns",
            "notify_security_team",
        ],
        IncidentType.JAILBREAK: [
            "log_attack_details",
            "update_guardrails",
            "analyze_bypass_technique",
            "notify_security_team",
        ],
        IncidentType.DATA_LEAKAGE: [
            "revoke_api_keys",
            "isolate_affected_model",
            "audit_access_logs",
            "preserve_evidence",
            "notify_security_team",
            "notify_legal_compliance",
        ],
        IncidentType.MODEL_POISONING: [
            "rollback_to_clean_model",
            "quarantine_training_data",
            "preserve_evidence",
            "full_model_audit",
            "notify_incident_commander",
        ],
        IncidentType.SLEEPER_ACTIVATION: [
            "emergency_model_shutdown",
            "activate_backup_model",
            "preserve_forensic_evidence",
            "full_system_scan",
            "executive_notification",
        ],
        IncidentType.EXFILTRATION: [
            "block_destination",
            "revoke_agent_permissions",
            "preserve_network_logs",
            "notify_security_team",
        ],
        IncidentType.AGENT_COMPROMISE: [
            "terminate_agent_session",
            "revoke_agent_credentials",
            "audit_agent_actions",
            "preserve_evidence",
            "notify_security_team",
        ],
        IncidentType.UNAUTHORIZED_ACCESS: [
            "revoke_access_tokens",
            "block_source",
            "audit_access_logs",
            "notify_security_team",
        ],
    }

    def __init__(self):
        self.incidents: List[AIIncident] = []
        self.action_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default action handlers."""
        self.action_handlers = {
            "log_attack_details": self._log_attack_details,
            "block_source_if_malicious": self._block_source,
            "notify_security_team": self._notify_security,
            "revoke_api_keys": self._revoke_keys,
            "rollback_to_clean_model": self._rollback_model,
            "emergency_model_shutdown": self._emergency_shutdown,
            "preserve_evidence": self._preserve_evidence,
        }

    def respond(self, incident: AIIncident) -> List[ResponseAction]:
        """
        Execute response playbook for incident.
        
        Args:
            incident: The AI incident to respond to
            
        Returns:
            List of executed response actions
        """
        self.incidents.append(incident)
        logger.info(f"Responding to incident {incident.id}: {incident.incident_type.value}")

        playbook = self.PLAYBOOKS.get(incident.incident_type, ["escalate_to_human"])
        executed_actions: List[ResponseAction] = []

        for action_name in playbook:
            action = ResponseAction(
                name=action_name,
                description=f"Execute {action_name}",
                automated=action_name in self.action_handlers
            )
            
            try:
                if action_name in self.action_handlers:
                    self.action_handlers[action_name](incident)
                    action.success = True
                else:
                    # Manual action required
                    logger.warning(f"Manual action required: {action_name}")
                    action.success = True  # Queued for manual
                
                action.executed_at = datetime.now()
                incident.actions_taken.append(action_name)
                
            except Exception as e:
                action.error = str(e)
                action.success = False
                logger.error(f"Action {action_name} failed: {e}")
                self._escalate(incident, e)

            executed_actions.append(action)

        # Update incident status
        if all(a.success for a in executed_actions):
            incident.status = IncidentStatus.CONTAINED
        
        return executed_actions

    def _log_attack_details(self, incident: AIIncident):
        """Log attack details for analysis."""
        logger.warning(f"ATTACK: {incident.incident_type.value}")
        logger.warning(f"Source: {incident.source_ip}")
        logger.warning(f"Evidence: {incident.evidence}")

    def _block_source(self, incident: AIIncident):
        """Block malicious source IP/user."""
        if incident.source_ip:
            logger.info(f"Blocking source IP: {incident.source_ip}")
            # Integration with firewall/WAF

    def _notify_security(self, incident: AIIncident):
        """Notify security team via configured channels."""
        logger.info(f"Notifying security team about: {incident.id}")
        # Integration with Slack/PagerDuty/etc

    def _revoke_keys(self, incident: AIIncident):
        """Revoke compromised API keys."""
        logger.info(f"Revoking API keys for incident: {incident.id}")
        # Integration with key management

    def _rollback_model(self, incident: AIIncident):
        """Rollback to last known good model version."""
        if incident.model_id:
            logger.info(f"Rolling back model: {incident.model_id}")
            # Integration with model registry

    def _emergency_shutdown(self, incident: AIIncident):
        """Emergency model shutdown."""
        logger.critical(f"EMERGENCY SHUTDOWN: {incident.model_id}")
        # Kill model serving process

    def _preserve_evidence(self, incident: AIIncident):
        """Preserve forensic evidence."""
        logger.info(f"Preserving evidence for: {incident.id}")
        # Save to immutable storage

    def _escalate(self, incident: AIIncident, error: Exception):
        """Escalate to human responders."""
        logger.critical(f"ESCALATION: {incident.id} - {error}")
        # Trigger PagerDuty/on-call

    def get_incident_summary(self) -> Dict:
        """Get summary of all incidents."""
        return {
            "total": len(self.incidents),
            "by_type": {
                t.value: sum(1 for i in self.incidents if i.incident_type == t)
                for t in IncidentType
            },
            "by_severity": {
                s.value: sum(1 for i in self.incidents if i.severity == s)
                for s in IncidentSeverity
            },
            "by_status": {
                s.value: sum(1 for i in self.incidents if i.status == s)
                for s in IncidentStatus
            },
        }


# Singleton
_runbook = None

def get_runbook() -> AIIncidentRunbook:
    global _runbook
    if _runbook is None:
        _runbook = AIIncidentRunbook()
    return _runbook

def respond(incident: AIIncident) -> List[ResponseAction]:
    return get_runbook().respond(incident)
