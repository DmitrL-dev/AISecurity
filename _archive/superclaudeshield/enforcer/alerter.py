# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Alerter - sends security alerts
"""

import logging
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityAlert:
    """Security alert data."""
    timestamp: str
    severity: AlertSeverity
    ide: str
    command: str
    threats: List[str]
    risk_score: float
    action_taken: str
    context: Dict[str, Any]


class Alerter:
    """
    Sends security alerts for detected threats.
    
    Supports:
    - Console logging
    - Webhook delivery
    - File logging
    - Custom callbacks
    """
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        log_file: Optional[str] = None,
        min_severity: AlertSeverity = AlertSeverity.WARNING,
        on_alert: Optional[Callable[[SecurityAlert], None]] = None
    ):
        """
        Initialize alerter.
        
        Args:
            webhook_url: URL for webhook delivery
            log_file: Path to log file
            min_severity: Minimum severity to alert on
            on_alert: Custom alert callback
        """
        self.webhook_url = webhook_url
        self.log_file = log_file
        self.min_severity = min_severity
        self.on_alert = on_alert
        
        self.alert_count = 0
    
    def alert(
        self,
        ide: str,
        command: str,
        threats: List[str],
        risk_score: float,
        action_taken: str = "blocked",
        context: Optional[Dict] = None
    ):
        """
        Send a security alert.
        
        Args:
            ide: IDE context
            command: Command that triggered alert
            threats: List of detected threats
            risk_score: Risk score
            action_taken: Action taken (blocked, warned, logged)
            context: Additional context
        """
        severity = self._calculate_severity(risk_score)
        
        # Check minimum severity
        severity_order = [AlertSeverity.INFO, AlertSeverity.WARNING, 
                         AlertSeverity.HIGH, AlertSeverity.CRITICAL]
        if severity_order.index(severity) < severity_order.index(self.min_severity):
            return
        
        alert = SecurityAlert(
            timestamp=datetime.now().isoformat(),
            severity=severity,
            ide=ide,
            command=command,
            threats=threats,
            risk_score=risk_score,
            action_taken=action_taken,
            context=context or {}
        )
        
        self.alert_count += 1
        
        # Log to console
        self._log_alert(alert)
        
        # Send to webhook
        if self.webhook_url:
            self._send_webhook(alert)
        
        # Write to file
        if self.log_file:
            self._write_file(alert)
        
        # Custom callback
        if self.on_alert:
            try:
                self.on_alert(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def _calculate_severity(self, risk_score: float) -> AlertSeverity:
        """Calculate severity from risk score."""
        if risk_score >= 0.9:
            return AlertSeverity.CRITICAL
        elif risk_score >= 0.7:
            return AlertSeverity.HIGH
        elif risk_score >= 0.4:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO
    
    def _log_alert(self, alert: SecurityAlert):
        """Log alert to console."""
        msg = (f"[{alert.severity.value.upper()}] {alert.ide}: "
               f"{alert.command} - {', '.join(alert.threats[:3])}")
        
        if alert.severity == AlertSeverity.CRITICAL:
            logger.critical(msg)
        elif alert.severity == AlertSeverity.HIGH:
            logger.error(msg)
        elif alert.severity == AlertSeverity.WARNING:
            logger.warning(msg)
        else:
            logger.info(msg)
    
    def _send_webhook(self, alert: SecurityAlert):
        """Send alert to webhook."""
        try:
            import urllib.request
            
            data = json.dumps({
                **asdict(alert),
                "severity": alert.severity.value
            }).encode("utf-8")
            
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status != 200:
                    logger.warning(f"Webhook returned {resp.status}")
                    
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")
    
    def _write_file(self, alert: SecurityAlert):
        """Write alert to file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps({
                    **asdict(alert),
                    "severity": alert.severity.value
                }) + "\n")
        except Exception as e:
            logger.error(f"File write failed: {e}")
