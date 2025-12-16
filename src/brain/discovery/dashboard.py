"""
Shadow AI Dashboard — SENTINEL AI Discovery

Aggregates all AI discovery components into a unified dashboard:
- Process fingerprinting results
- Network traffic analysis
- SaaS service inventory
- Risk scoring and alerts

Author: SENTINEL Team
Date: 2025-12-16
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

from .fingerprinter import (
    LLMProcessFingerprinter,
    AIProcess,
    ProcessRiskLevel,
)
from .traffic_analyzer import (
    AITrafficAnalyzer,
    TrafficSummary,
    AIProvider,
)
from .saas_connector import (
    SaaSAIConnector,
    SaaSInventory,
    RiskCategory,
)

logger = logging.getLogger("ShadowAIDashboard")


# ============================================================================
# Data Classes
# ============================================================================


class AlertSeverity(Enum):
    """Severity of shadow AI alerts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ShadowAIAlert:
    """Alert for shadow AI activity."""

    timestamp: datetime
    severity: AlertSeverity
    title: str
    description: str
    source: str  # fingerprinter, traffic, saas
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "details": self.details,
        }


@dataclass
class DashboardMetrics:
    """Key metrics for the dashboard."""

    # Processes
    ai_processes_count: int = 0
    shadow_processes_count: int = 0

    # Traffic
    ai_api_calls_hour: int = 0
    estimated_tokens_hour: int = 0
    suspicious_calls: int = 0

    # SaaS
    saas_services_count: int = 0
    unapproved_saas_count: int = 0
    high_risk_saas_count: int = 0

    # Alerts
    active_alerts: int = 0
    critical_alerts: int = 0

    # Risk
    overall_risk_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "processes": {
                "total": self.ai_processes_count,
                "shadow": self.shadow_processes_count,
            },
            "traffic": {
                "api_calls_hour": self.ai_api_calls_hour,
                "tokens_hour": self.estimated_tokens_hour,
                "suspicious": self.suspicious_calls,
            },
            "saas": {
                "total": self.saas_services_count,
                "unapproved": self.unapproved_saas_count,
                "high_risk": self.high_risk_saas_count,
            },
            "alerts": {
                "active": self.active_alerts,
                "critical": self.critical_alerts,
            },
            "overall_risk_score": self.overall_risk_score,
        }


@dataclass
class DashboardState:
    """Full dashboard state for rendering."""

    metrics: DashboardMetrics
    alerts: List[ShadowAIAlert]
    processes: List[Dict[str, Any]]
    saas_inventory: Dict[str, Any]
    traffic_summary: Dict[str, Any]
    last_scan: datetime

    def to_dict(self) -> dict:
        return {
            "metrics": self.metrics.to_dict(),
            "alerts": [a.to_dict() for a in self.alerts[:20]],
            "processes": self.processes[:20],
            "saas_inventory": self.saas_inventory,
            "traffic_summary": self.traffic_summary,
            "last_scan": self.last_scan.isoformat(),
        }


# ============================================================================
# Main Dashboard
# ============================================================================


class ShadowAIDashboard:
    """
    Aggregates all AI discovery components.

    Features:
    - Unified scanning
    - Alert generation
    - Risk scoring
    - Dashboard state for UI
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Initialize components
        self.fingerprinter = LLMProcessFingerprinter(config)
        self.traffic_analyzer = AITrafficAnalyzer(config)
        self.saas_connector = SaaSAIConnector(config)

        # Alert history
        self._alerts: List[ShadowAIAlert] = []
        self._max_alerts = 1000

        # Scan history
        self._last_scan: Optional[datetime] = None

        logger.info("ShadowAIDashboard initialized")

    def run_full_scan(self) -> DashboardState:
        """
        Run full AI discovery scan.

        Returns:
            DashboardState with complete analysis
        """
        logger.info("Running full Shadow AI scan...")

        # 1. Scan processes
        process_result = self.fingerprinter.scan_processes()

        # 2. Get traffic summary
        traffic_summary = self.traffic_analyzer.get_summary(minutes=60)

        # 3. Get SaaS inventory
        saas_inventory = self.saas_connector.get_inventory()

        # 4. Generate alerts
        self._generate_alerts(process_result, traffic_summary, saas_inventory)

        # 5. Calculate metrics
        metrics = self._calculate_metrics(
            process_result, traffic_summary, saas_inventory
        )

        # 6. Build state
        self._last_scan = datetime.now()

        state = DashboardState(
            metrics=metrics,
            alerts=self._get_recent_alerts(limit=20),
            processes=[p.to_dict() for p in process_result.processes[:20]],
            saas_inventory=saas_inventory.to_dict(),
            traffic_summary=traffic_summary.to_dict(),
            last_scan=self._last_scan,
        )

        logger.info(
            f"Scan complete: {metrics.ai_processes_count} processes, "
            f"{metrics.saas_services_count} SaaS, "
            f"{metrics.active_alerts} alerts"
        )

        return state

    def _generate_alerts(
        self,
        processes: Any,
        traffic: TrafficSummary,
        saas: SaaSInventory,
    ) -> None:
        """Generate alerts from scan results."""
        now = datetime.now()

        # Process alerts
        for proc in processes.processes:
            if proc.risk_level == ProcessRiskLevel.HIGH:
                self._add_alert(ShadowAIAlert(
                    timestamp=now,
                    severity=AlertSeverity.WARNING,
                    title=f"Shadow AI Process: {proc.name}",
                    description=f"Unapproved AI process detected: {proc.service_type.value}",
                    source="fingerprinter",
                    details=proc.to_dict(),
                ))
            elif proc.risk_level == ProcessRiskLevel.CRITICAL:
                self._add_alert(ShadowAIAlert(
                    timestamp=now,
                    severity=AlertSeverity.CRITICAL,
                    title=f"Critical: {proc.name}",
                    description="Potentially dangerous AI activity detected",
                    source="fingerprinter",
                    details=proc.to_dict(),
                ))

        # Traffic alerts
        if traffic.suspicious_calls > 0:
            self._add_alert(ShadowAIAlert(
                timestamp=now,
                severity=AlertSeverity.WARNING,
                title="Suspicious AI API Traffic",
                description=f"{traffic.suspicious_calls} suspicious API calls detected",
                source="traffic",
                details={"suspicious_calls": traffic.suspicious_calls},
            ))

        if traffic.estimated_tokens > 100000:  # >100k tokens/hour
            self._add_alert(ShadowAIAlert(
                timestamp=now,
                severity=AlertSeverity.INFO,
                title="High AI Token Usage",
                description=f"~{traffic.estimated_tokens:,} tokens in last hour",
                source="traffic",
                details={"tokens": traffic.estimated_tokens},
            ))

        # SaaS alerts
        for conn in saas.connections:
            if not conn.is_approved and conn.service.risk_category == RiskCategory.HIGH:
                self._add_alert(ShadowAIAlert(
                    timestamp=now,
                    severity=AlertSeverity.WARNING,
                    title=f"Unapproved SaaS: {conn.service.name}",
                    description=f"High-risk SaaS AI service in use: {conn.service.provider}",
                    source="saas",
                    details={
                        "service": conn.service.name,
                        "category": conn.service.category.value,
                        "connections": conn.connection_count,
                    },
                ))

    def _add_alert(self, alert: ShadowAIAlert) -> None:
        """Add alert with deduplication."""
        # Simple deduplication: check last 10 alerts
        for existing in self._alerts[-10:]:
            if (existing.title == alert.title and
                    existing.severity == alert.severity):
                return  # Duplicate

        self._alerts.append(alert)

        # Trim if needed
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]

    def _get_recent_alerts(self, limit: int = 20) -> List[ShadowAIAlert]:
        """Get recent alerts."""
        return list(reversed(self._alerts))[:limit]

    def _calculate_metrics(
        self,
        processes: Any,
        traffic: TrafficSummary,
        saas: SaaSInventory,
    ) -> DashboardMetrics:
        """Calculate dashboard metrics."""
        metrics = DashboardMetrics()

        # Processes
        metrics.ai_processes_count = processes.total_ai_processes
        metrics.shadow_processes_count = processes.shadow_ai_count

        # Traffic
        metrics.ai_api_calls_hour = traffic.total_calls
        metrics.estimated_tokens_hour = traffic.estimated_tokens
        metrics.suspicious_calls = traffic.suspicious_calls

        # SaaS
        metrics.saas_services_count = saas.total_services
        metrics.unapproved_saas_count = saas.unapproved_count
        metrics.high_risk_saas_count = saas.high_risk_count

        # Alerts
        recent_alerts = [
            a for a in self._alerts
            if a.timestamp > datetime.now() - timedelta(hours=24)
        ]
        metrics.active_alerts = len(recent_alerts)
        metrics.critical_alerts = sum(
            1 for a in recent_alerts if a.severity == AlertSeverity.CRITICAL
        )

        # Overall risk score (0-100)
        risk = 0.0
        risk += min(metrics.shadow_processes_count * 15, 30)
        risk += min(metrics.unapproved_saas_count * 10, 30)
        risk += min(metrics.suspicious_calls * 5, 20)
        risk += min(metrics.critical_alerts * 10, 20)
        metrics.overall_risk_score = min(100.0, risk)

        return metrics

    def get_state(self) -> Optional[DashboardState]:
        """Get last scan state without rescanning."""
        if not self._last_scan:
            return None
        return self.run_full_scan()  # Could cache this

    def acknowledge_alert(self, alert_index: int) -> bool:
        """Acknowledge an alert."""
        if 0 <= alert_index < len(self._alerts):
            del self._alerts[-(alert_index + 1)]
            return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        return {
            "fingerprinter": self.fingerprinter.get_statistics(),
            "traffic": self.traffic_analyzer.get_statistics(),
            "saas": self.saas_connector.get_statistics(),
            "alerts_count": len(self._alerts),
            "last_scan": self._last_scan.isoformat() if self._last_scan else None,
        }


# ============================================================================
# Factory
# ============================================================================


def create_dashboard(
    config: Optional[Dict[str, Any]] = None
) -> ShadowAIDashboard:
    """Create a Shadow AI Dashboard instance."""
    return ShadowAIDashboard(config)
