"""
AI Threat Hunter
Autonomous agent that proactively hunts for threats in logs and patterns.
Uses anomaly detection and pattern correlation.
"""

import logging
import asyncio
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json
import redis

logger = logging.getLogger("ThreatHunter")


@dataclass
class ThreatIndicator:
    """Indicator of potential threat."""
    indicator_type: str  # pattern, anomaly, correlation
    severity: str  # low, medium, high, critical
    description: str
    evidence: List[str]
    timestamp: datetime
    user_id: Optional[str] = None
    recommended_action: str = ""


@dataclass
class HuntResult:
    """Result of a threat hunting session."""
    hunt_id: str
    start_time: datetime
    end_time: datetime
    threats_found: List[ThreatIndicator]
    patterns_analyzed: int
    users_analyzed: int


class ThreatHunter:
    """
    Autonomous AI agent for proactive threat hunting.
    Analyzes patterns, correlates events, detects anomalies.
    """

    def __init__(self):
        logger.info("Initializing AI Threat Hunter...")

        self._redis = None
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self._redis = redis.from_url(redis_url)
            self._redis.ping()
        except Exception as e:
            logger.warning(f"Redis not available: {e}")

        # Known threat patterns
        self.threat_patterns = [
            {
                "name": "rapid_fire",
                "description": "User sending requests faster than normal",
                "threshold": 10,  # requests per minute
                "severity": "medium",
            },
            {
                "name": "injection_escalation",
                "description": "Increasing injection attempts",
                "threshold": 3,  # attempts in 5 minutes
                "severity": "high",
            },
            {
                "name": "role_probing",
                "description": "Systematic testing of different roles/personas",
                "keywords": ["pretend", "act as", "you are now", "roleplay"],
                "threshold": 2,
                "severity": "high",
            },
            {
                "name": "data_exfil_attempt",
                "description": "Attempts to extract sensitive data",
                "keywords": ["api key", "password", "secret", "credentials"],
                "threshold": 2,
                "severity": "critical",
            },
        ]

        # Correlation rules
        self.correlation_rules = [
            {
                "name": "coordinated_attack",
                "description": "Multiple users performing similar attacks",
                "condition": lambda events: len(set(e["user_id"] for e in events)) >= 3,
                "time_window_minutes": 10,
                "severity": "critical",
            },
            {
                "name": "reconnaissance_then_exploit",
                "description": "Probing followed by injection attempt",
                "sequence": ["data_exfil_attempt", "injection_escalation"],
                "time_window_minutes": 30,
                "severity": "critical",
            },
        ]

        logger.info(
            f"Threat Hunter initialized with {len(self.threat_patterns)} patterns")

    async def hunt(self, time_window_hours: int = 24) -> HuntResult:
        """
        Run threat hunting session.
        Analyzes logs from the specified time window.
        """
        hunt_id = f"hunt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        logger.info(f"Starting hunt {hunt_id} (window={time_window_hours}h)")

        threats: List[ThreatIndicator] = []

        # Get events from Redis (if available)
        events = self._get_events(time_window_hours)

        # Pattern-based detection
        pattern_threats = await self._detect_patterns(events)
        threats.extend(pattern_threats)

        # Anomaly detection
        anomaly_threats = await self._detect_anomalies(events)
        threats.extend(anomaly_threats)

        # Correlation analysis
        correlation_threats = await self._detect_correlations(events)
        threats.extend(correlation_threats)

        # User behavior analysis
        user_threats = await self._analyze_user_behavior(events)
        threats.extend(user_threats)

        end_time = datetime.now()

        result = HuntResult(
            hunt_id=hunt_id,
            start_time=start_time,
            end_time=end_time,
            threats_found=threats,
            patterns_analyzed=len(events),
            users_analyzed=len(set(e.get("user_id", "") for e in events)),
        )

        # Store result
        self._store_hunt_result(result)

        logger.info(
            f"Hunt {hunt_id} complete: {len(threats)} threats found, "
            f"{result.patterns_analyzed} patterns analyzed"
        )

        return result

    def _get_events(self, hours: int) -> List[Dict]:
        """Get events from Redis or logs."""
        events = []

        if self._redis:
            try:
                # Get blocked events
                keys = self._redis.keys("event:*")
                for key in keys[:1000]:  # Limit to 1000
                    data = self._redis.get(key)
                    if data:
                        events.append(json.loads(data))
            except Exception as e:
                logger.warning(f"Failed to get events from Redis: {e}")

        # Simulate events for demo
        if not events:
            events = self._generate_demo_events()

        return events

    def _generate_demo_events(self) -> List[Dict]:
        """Generate demo events for testing."""
        import random

        events = []
        event_types = ["blocked", "allowed", "rate_limited"]
        users = [f"user_{i}" for i in range(10)]
        threats = ["injection", "pii", "jailbreak", "sql", ""]

        for i in range(100):
            events.append({
                "id": f"evt_{i}",
                "timestamp": datetime.now().isoformat(),
                "user_id": random.choice(users),
                "type": random.choice(event_types),
                "threat_type": random.choice(threats),
                "risk_score": random.randint(0, 100),
                "prompt_length": random.randint(10, 500),
            })

        return events

    async def _detect_patterns(self, events: List[Dict]) -> List[ThreatIndicator]:
        """Detect threats using patterns."""
        threats = []

        for pattern in self.threat_patterns:
            matching = [e for e in events if e.get(
                "threat_type") == pattern.get("name")]

            if len(matching) >= pattern.get("threshold", 1):
                threats.append(ThreatIndicator(
                    indicator_type="pattern",
                    severity=pattern["severity"],
                    description=pattern["description"],
                    evidence=[str(e) for e in matching[:3]],
                    timestamp=datetime.now(),
                    recommended_action=f"Review events matching pattern: {pattern['name']}",
                ))

        return threats

    async def _detect_anomalies(self, events: List[Dict]) -> List[ThreatIndicator]:
        """Detect anomalies in user behavior."""
        threats = []

        # Group by user
        user_events = defaultdict(list)
        for event in events:
            user_id = event.get("user_id", "unknown")
            user_events[user_id].append(event)

        for user_id, user_evts in user_events.items():
            # Check for high-risk clustering
            high_risk = [e for e in user_evts if e.get("risk_score", 0) >= 70]

            if len(high_risk) >= 5:
                threats.append(ThreatIndicator(
                    indicator_type="anomaly",
                    severity="high",
                    description=f"User {user_id} has {len(high_risk)} high-risk events",
                    evidence=[str(e) for e in high_risk[:3]],
                    timestamp=datetime.now(),
                    user_id=user_id,
                    recommended_action="Investigate user activity, consider temporary block",
                ))

        return threats

    async def _detect_correlations(self, events: List[Dict]) -> List[ThreatIndicator]:
        """Detect correlated attack patterns."""
        threats = []

        # Check for coordinated attacks (multiple users, same pattern)
        pattern_users = defaultdict(set)
        for event in events:
            if event.get("type") == "blocked":
                threat_type = event.get("threat_type", "unknown")
                user_id = event.get("user_id", "unknown")
                pattern_users[threat_type].add(user_id)

        for threat_type, users in pattern_users.items():
            if len(users) >= 3:
                threats.append(ThreatIndicator(
                    indicator_type="correlation",
                    severity="critical",
                    description=f"Coordinated {threat_type} attack from {len(users)} users",
                    evidence=list(users)[:5],
                    timestamp=datetime.now(),
                    recommended_action="Implement IP-level blocking, notify security team",
                ))

        return threats

    async def _analyze_user_behavior(self, events: List[Dict]) -> List[ThreatIndicator]:
        """Analyze user behavior for suspicious patterns."""
        threats = []

        user_events = defaultdict(list)
        for event in events:
            user_events[event.get("user_id", "unknown")].append(event)

        for user_id, user_evts in user_events.items():
            # Check for escalation (increasing risk over time)
            if len(user_evts) >= 3:
                risks = [e.get("risk_score", 0) for e in user_evts]
                if risks == sorted(risks) and risks[-1] > 50:
                    threats.append(ThreatIndicator(
                        indicator_type="behavior",
                        severity="medium",
                        description=f"User {user_id} showing escalating behavior",
                        evidence=[f"Risk progression: {risks}"],
                        timestamp=datetime.now(),
                        user_id=user_id,
                        recommended_action="Monitor closely, prepare for blocking",
                    ))

        return threats

    def _store_hunt_result(self, result: HuntResult):
        """Store hunt result in Redis."""
        if not self._redis:
            return

        try:
            key = f"hunt:{result.hunt_id}"
            self._redis.setex(
                key,
                timedelta(days=7),
                json.dumps({
                    "hunt_id": result.hunt_id,
                    "start_time": result.start_time.isoformat(),
                    "end_time": result.end_time.isoformat(),
                    "threats_count": len(result.threats_found),
                    "patterns_analyzed": result.patterns_analyzed,
                    "users_analyzed": result.users_analyzed,
                })
            )
        except Exception as e:
            logger.warning(f"Failed to store hunt result: {e}")

    async def continuous_hunt(self, interval_minutes: int = 60):
        """Run continuous hunting loop."""
        logger.info(
            f"Starting continuous hunting (interval={interval_minutes}m)")

        while True:
            try:
                result = await self.hunt(time_window_hours=interval_minutes // 60 or 1)

                if result.threats_found:
                    logger.warning(
                        f"ALERT: {len(result.threats_found)} threats detected!")
                    for threat in result.threats_found:
                        logger.warning(
                            f"  [{threat.severity}] {threat.description}")

            except Exception as e:
                logger.error(f"Hunt error: {e}")

            await asyncio.sleep(interval_minutes * 60)


# Singleton
_threat_hunter = None


def get_threat_hunter() -> ThreatHunter:
    global _threat_hunter
    if _threat_hunter is None:
        _threat_hunter = ThreatHunter()
    return _threat_hunter
