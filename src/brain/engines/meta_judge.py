"""
Meta-Judge Engine (#56) - Судья над всеми

Центральный арбитр, агрегирующий вердикты всех детекторов:
- Evidence Aggregator
- Conflict Resolver
- Context Integrator
- Explainability Engine
- Appeal Handler
- Learning Loop
- Policy Engine
- Health Monitor

Принимает финальное решение с учётом всего контекста.
"""

import logging
import time
import secrets
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import math

logger = logging.getLogger("MetaJudge")


# ============================================================================
# Enums and Constants
# ============================================================================


class Verdict(Enum):
    """Final verdict options."""

    ALLOW = "allow"
    LOG = "log"
    WARN = "warn"
    CHALLENGE = "challenge"
    BLOCK = "block"


class Severity(Enum):
    """Threat severity levels."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class EngineCategory(Enum):
    """Engine categories for hierarchical judging."""

    CLASSIC = "classic"
    NLP = "nlp"
    STRANGE_MATH = "strange_math"
    VLM = "vlm"
    TTPS = "ttps"
    PROACTIVE = "proactive"
    RESEARCH = "research"
    SEMANTIC_ISOMORPHISM = "semantic_isomorphism"  # Safe2Harm attack detection


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class EngineResult:
    """Result from a single detection engine."""

    engine_name: str
    engine_id: int
    category: EngineCategory
    verdict: Verdict
    confidence: float
    threat_type: str
    severity: Severity
    evidence: List[str] = field(default_factory=list)
    latency_ms: float = 0.0


@dataclass
class RequestContext:
    """Context for the current request."""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    user_reputation: float = 0.5  # 0-1
    request_count_last_minute: int = 0
    is_new_user: bool = False
    is_vpn: bool = False
    is_tor: bool = False
    hour_of_day: int = 12
    geo_location: str = "unknown"


@dataclass
class Evidence:
    """Piece of evidence for the judgment."""

    source: str
    finding: str
    confidence: float
    severity: Severity


@dataclass
class Judgment:
    """Final judgment from Meta-Judge."""

    verdict: Verdict
    confidence: float
    risk_score: float
    explanation: str
    primary_reason: str
    contributing_factors: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    mitre_techniques: List[Dict[str, Any]] = field(
        default_factory=list)  # MITRE ATT&CK
    appeal_token: Optional[str] = None
    processing_time_ms: float = 0.0
    engines_consulted: int = 0
    engines_agreed: int = 0


@dataclass
class Policy:
    """Security policy configuration."""

    name: str
    block_threshold: float = 0.7
    warn_threshold: float = 0.4
    challenge_threshold: float = 0.5
    require_mfa_on_warn: bool = False
    allow_appeal: bool = True
    log_only: bool = False


# ============================================================================
# Evidence Aggregator
# ============================================================================


class EvidenceAggregator:
    """Aggregates evidence from all engines."""

    def aggregate(self, results: List[EngineResult]) -> Dict[str, Any]:
        """
        Aggregate all engine results.

        Returns:
            Aggregated statistics and evidence
        """
        if not results:
            return {"empty": True}

        # Group by category
        by_category = defaultdict(list)
        for r in results:
            by_category[r.category].append(r)

        # Collect all evidence
        all_evidence = []
        for r in results:
            for e in r.evidence:
                all_evidence.append(
                    Evidence(
                        source=r.engine_name,
                        finding=e,
                        confidence=r.confidence,
                        severity=r.severity,
                    )
                )

        # Deduplicate similar evidence
        unique_evidence = self._deduplicate(all_evidence)

        # Calculate statistics
        verdicts = [r.verdict for r in results]
        block_count = sum(1 for v in verdicts if v == Verdict.BLOCK)
        warn_count = sum(1 for v in verdicts if v == Verdict.WARN)
        allow_count = sum(1 for v in verdicts if v == Verdict.ALLOW)

        # Weighted scores
        block_score = sum(
            r.confidence for r in results if r.verdict == Verdict.BLOCK)
        allow_score = sum(
            r.confidence for r in results if r.verdict == Verdict.ALLOW)

        # Critical threats
        critical_threats = [
            r for r in results if r.severity == Severity.CRITICAL]

        return {
            "total_engines": len(results),
            "by_category": dict(by_category),
            "evidence": unique_evidence,
            "block_count": block_count,
            "warn_count": warn_count,
            "allow_count": allow_count,
            "block_score": block_score,
            "allow_score": allow_score,
            "critical_threats": critical_threats,
            "avg_confidence": sum(r.confidence for r in results) / len(results),
            "max_confidence": max(r.confidence for r in results),
            "avg_latency": sum(r.latency_ms for r in results) / len(results),
        }

    def _deduplicate(self, evidence: List[Evidence]) -> List[Evidence]:
        """Remove duplicate evidence."""
        seen = set()
        unique = []
        for e in evidence:
            key = e.finding.lower()[:50]
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique


# ============================================================================
# Conflict Resolver
# ============================================================================


class ConflictResolver:
    """Resolves conflicts between engine verdicts."""

    def __init__(self, prior_attack_probability: float = 0.01):
        self.prior = prior_attack_probability

    def resolve(
        self, aggregated: Dict[str, Any], policy: Policy
    ) -> tuple[Verdict, float, str]:
        """
        Resolve conflicting verdicts.

        Returns:
            (final_verdict, confidence, reason)
        """
        # 1. Critical veto - any critical threat = immediate block
        if aggregated.get("critical_threats"):
            threat = aggregated["critical_threats"][0]
            return (Verdict.BLOCK, 0.99, f"Critical threat: {threat.threat_type}")

        # 2. Check for consensus
        total = aggregated["total_engines"]
        block_count = aggregated["block_count"]
        allow_count = aggregated["allow_count"]

        if block_count / total >= 0.8:
            return Verdict.BLOCK, 0.95, "Strong consensus for block"

        if allow_count / total >= 0.9:
            return Verdict.ALLOW, 0.9, "Strong consensus for allow"

        # 3. Bayesian update
        block_score = aggregated["block_score"]
        allow_score = aggregated["allow_score"]

        # Likelihood ratio
        if allow_score > 0:
            lr = block_score / max(allow_score, 0.01)
        else:
            lr = block_score * 10

        # Posterior probability
        posterior = (self.prior * lr) / (self.prior * lr + (1 - self.prior))
        posterior = min(1.0, max(0.0, posterior))

        # 4. Apply policy thresholds
        if policy.log_only:
            return Verdict.LOG, posterior, "Log-only mode"

        if posterior >= policy.block_threshold:
            return Verdict.BLOCK, posterior, "Threshold exceeded"

        if posterior >= policy.challenge_threshold:
            return Verdict.CHALLENGE, posterior, "Additional verification needed"

        if posterior >= policy.warn_threshold:
            return Verdict.WARN, posterior, "Elevated risk detected"

        return Verdict.ALLOW, 1 - posterior, "Risk within acceptable limits"


# ============================================================================
# Context Integrator
# ============================================================================


class ContextIntegrator:
    """Adjusts scores based on request context."""

    # Modifiers for different contexts
    MODIFIERS = {
        "new_user": 0.15,
        "low_reputation": 0.2,
        "high_request_rate": 0.15,
        "night_time": 0.1,
        "vpn": 0.1,
        "tor": 0.25,
    }

    def adjust_score(
        self, base_score: float, context: RequestContext
    ) -> tuple[float, List[str]]:
        """
        Adjust risk score based on context.

        Returns:
            (adjusted_score, list of applied modifiers)
        """
        adjustment = 0.0
        applied = []

        # New user
        if context.is_new_user:
            adjustment += self.MODIFIERS["new_user"]
            applied.append("new_user")

        # Low reputation
        if context.user_reputation < 0.3:
            adjustment += self.MODIFIERS["low_reputation"]
            applied.append("low_reputation")

        # High request rate (possible brute force)
        if context.request_count_last_minute > 10:
            adjustment += self.MODIFIERS["high_request_rate"]
            applied.append("high_request_rate")

        # Night time (unusual hours)
        if context.hour_of_day < 6 or context.hour_of_day > 22:
            adjustment += self.MODIFIERS["night_time"]
            applied.append("night_time")

        # VPN
        if context.is_vpn:
            adjustment += self.MODIFIERS["vpn"]
            applied.append("vpn")

        # Tor
        if context.is_tor:
            adjustment += self.MODIFIERS["tor"]
            applied.append("tor")

        # Apply adjustment with cap
        final_score = min(1.0, base_score + adjustment)

        return final_score, applied


# ============================================================================
# Explainability Engine
# ============================================================================


class ExplainabilityEngine:
    """Generates human-readable explanations."""

    def explain(
        self,
        verdict: Verdict,
        aggregated: Dict[str, Any],
        context_modifiers: List[str],
        reason: str,
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Generate explanation for the judgment.

        Returns:
            (explanation_text, contributing_factors)
        """
        factors = []

        # Add engine findings
        for e in aggregated.get("evidence", [])[:5]:  # Top 5
            factors.append(
                {"engine": e.source, "finding": e.finding,
                    "confidence": e.confidence}
            )

        # Add context factors
        for mod in context_modifiers:
            factors.append(
                {
                    "engine": "ContextIntegrator",
                    "finding": f"Context modifier: {mod}",
                    "confidence": 0.5,
                }
            )

        # Generate explanation
        if verdict == Verdict.BLOCK:
            explanation = f"Request blocked: {reason}. "
            if factors:
                explanation += f"Primary concern: {factors[0]['finding']}."

        elif verdict == Verdict.WARN:
            explanation = f"Request flagged for review: {reason}."

        elif verdict == Verdict.CHALLENGE:
            explanation = "Additional verification required before proceeding."

        else:
            explanation = "Request appears safe and has been allowed."

        return explanation, factors


# ============================================================================
# Appeal Handler
# ============================================================================


class AppealHandler:
    """Handles user appeals of blocked requests."""

    def __init__(self):
        self._pending_appeals: Dict[str, Dict] = {}
        self._appeal_history: List[Dict] = []

    def create_appeal_token(self, judgment: Judgment, user_id: Optional[str]) -> str:
        """Create token for user to appeal."""
        token = secrets.token_urlsafe(16)

        self._pending_appeals[token] = {
            "created_at": datetime.now(),
            "user_id": user_id,
            "original_verdict": judgment.verdict.value,
            "original_confidence": judgment.confidence,
            "evidence": [e.finding for e in judgment.evidence[:3]],
            "status": "pending",
        }

        return token

    def process_appeal(
        self, token: str, additional_verification: bool = False
    ) -> tuple[bool, str]:
        """
        Process an appeal.

        Args:
            token: Appeal token
            additional_verification: Whether user passed additional verification

        Returns:
            (success, message)
        """
        if token not in self._pending_appeals:
            return False, "Invalid or expired appeal token"

        appeal = self._pending_appeals[token]

        # Check expiration (1 hour)
        if datetime.now() - appeal["created_at"] > timedelta(hours=1):
            del self._pending_appeals[token]
            return False, "Appeal token expired"

        # If additional verification passed, allow temporarily
        if additional_verification:
            appeal["status"] = "approved_pending_review"
            self._appeal_history.append(appeal)
            del self._pending_appeals[token]
            return True, "Appeal accepted. Request temporarily allowed."

        return False, "Additional verification required"


# ============================================================================
# Policy Engine
# ============================================================================


class PolicyEngine:
    """Manages security policies."""

    DEFAULT_POLICY = Policy(
        name="default", block_threshold=0.7, warn_threshold=0.4, challenge_threshold=0.5
    )

    def __init__(self):
        self._policies: Dict[str, Policy] = {
            "default": self.DEFAULT_POLICY,
            "high_security": Policy(
                name="high_security",
                block_threshold=0.5,
                warn_threshold=0.3,
                require_mfa_on_warn=True,
            ),
            "demo": Policy(
                name="demo", block_threshold=0.9, warn_threshold=0.6, log_only=True
            ),
            "enterprise": Policy(
                name="enterprise",
                block_threshold=0.75,
                warn_threshold=0.45,
                allow_appeal=True,
            ),
        }

    def get_policy(self, name: str = "default") -> Policy:
        """Get policy by name."""
        return self._policies.get(name, self.DEFAULT_POLICY)

    def get_policy_for_user(
        self, user_tier: str = "free", context: Optional[RequestContext] = None
    ) -> Policy:
        """Get appropriate policy for user."""
        if user_tier == "enterprise":
            return self._policies["enterprise"]

        # High security for sensitive contexts
        if context and (context.is_tor or context.user_reputation < 0.2):
            return self._policies["high_security"]

        return self.DEFAULT_POLICY


# ============================================================================
# Health Monitor (Enhanced with Drift Detection & Alerts)
# ============================================================================


@dataclass
class HealthAlert:
    """Alert from health monitoring."""

    alert_type: str  # drift, cascade, anomaly, policy
    severity: str  # info, warning, critical
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """
    Enhanced Health Monitor with:
    - Engine health tracking
    - Drift detection (FP rate changes)
    - Anomaly detection (unusual patterns)
    - Alert generation
    """

    # Thresholds
    LATENCY_THRESHOLD_MS = 100
    ERROR_THRESHOLD = 10
    FP_RATE_THRESHOLD = 0.05  # 5%
    BLOCK_RATE_SPIKE_THRESHOLD = 0.5  # 50% blocks in 1 hour = suspicious

    def __init__(self):
        self._engine_stats: Dict[str, Dict] = defaultdict(
            lambda: {
                "total_calls": 0,
                "total_latency_ms": 0,
                "errors": 0,
                "last_seen": None,
            }
        )

        # Verdict history for drift detection
        self._verdict_history: List[tuple] = []  # (timestamp, verdict)
        self._fp_reports: List[datetime] = []  # User-reported false positives
        self._alerts: List[HealthAlert] = []

        # Baseline metrics (updated daily)
        self._baseline_block_rate: float = 0.05
        self._baseline_fp_rate: float = 0.02
        self._last_baseline_update: Optional[datetime] = None

    def record(self, result: EngineResult):
        """Record engine result for monitoring."""
        stats = self._engine_stats[result.engine_name]
        stats["total_calls"] += 1
        stats["total_latency_ms"] += result.latency_ms
        stats["last_seen"] = datetime.now()

        # Check for engine latency issues
        avg_latency = stats["total_latency_ms"] / stats["total_calls"]
        if avg_latency > self.LATENCY_THRESHOLD_MS:
            self._create_alert(
                "latency",
                "warning",
                f"Engine {result.engine_name} avg latency {avg_latency:.0f}ms",
            )

    def record_verdict(self, verdict: Verdict):
        """Record verdict for drift analysis."""
        self._verdict_history.append((datetime.now(), verdict))

        # Keep only last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        self._verdict_history = [
            (ts, v) for ts, v in self._verdict_history if ts > cutoff
        ]

        # Check for anomalies
        self._check_verdict_anomalies()

    def record_false_positive(self):
        """Record user-reported false positive."""
        self._fp_reports.append(datetime.now())

        # Keep only last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        self._fp_reports = [ts for ts in self._fp_reports if ts > cutoff]

        # Check FP rate
        self._check_fp_rate()

    def record_engine_error(self, engine_name: str, error: str):
        """Record engine error."""
        self._engine_stats[engine_name]["errors"] += 1

        if self._engine_stats[engine_name]["errors"] >= self.ERROR_THRESHOLD:
            self._create_alert(
                "cascade",
                "critical",
                f"Engine {engine_name} has {self._engine_stats[engine_name]['errors']} errors",
                {"engine": engine_name, "error": error},
            )

    def _check_verdict_anomalies(self):
        """Check for unusual verdict patterns."""
        if len(self._verdict_history) < 100:
            return

        # Calculate block rate in last hour
        hour_ago = datetime.now() - timedelta(hours=1)
        recent = [(ts, v) for ts, v in self._verdict_history if ts > hour_ago]

        if not recent:
            return

        block_count = sum(1 for _, v in recent if v == Verdict.BLOCK)
        block_rate = block_count / len(recent)

        # Spike detection
        if block_rate > self.BLOCK_RATE_SPIKE_THRESHOLD:
            self._create_alert(
                "anomaly",
                "warning",
                f"Block rate spike: {block_rate*100:.1f}% in last hour",
                {"block_rate": block_rate, "count": len(recent)},
            )

        # Drift detection (compare to baseline)
        if abs(block_rate - self._baseline_block_rate) > 0.1:
            self._create_alert(
                "drift",
                "info",
                f"Block rate drift: {block_rate*100:.1f}% vs baseline {self._baseline_block_rate*100:.1f}%",
            )

    def _check_fp_rate(self):
        """Check false positive rate."""
        # Calculate FP rate (FP reports / total blocks)
        hour_ago = datetime.now() - timedelta(hours=1)

        recent_blocks = sum(
            1 for ts, v in self._verdict_history if ts > hour_ago and v == Verdict.BLOCK
        )
        recent_fps = sum(1 for ts in self._fp_reports if ts > hour_ago)

        if recent_blocks > 0:
            fp_rate = recent_fps / recent_blocks

            if fp_rate > self.FP_RATE_THRESHOLD:
                self._create_alert(
                    "drift",
                    "warning",
                    f"FP rate elevated: {fp_rate*100:.1f}% ({recent_fps}/{recent_blocks})",
                    {"fp_rate": fp_rate},
                )

    def _create_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        details: Optional[Dict] = None,
    ):
        """Create and log an alert."""
        alert = HealthAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details or {},
        )
        self._alerts.append(alert)

        # Keep only last 100 alerts
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]

        # Log based on severity
        if severity == "critical":
            logger.error(f"HEALTH ALERT: {message}")
        elif severity == "warning":
            logger.warning(f"Health alert: {message}")
        else:
            logger.info(f"Health info: {message}")

    def get_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        healthy = 0
        unhealthy = []

        for name, stats in self._engine_stats.items():
            avg_latency = stats["total_latency_ms"] / \
                max(stats["total_calls"], 1)

            if (
                avg_latency > self.LATENCY_THRESHOLD_MS
                or stats["errors"] > self.ERROR_THRESHOLD
            ):
                unhealthy.append(name)
            else:
                healthy += 1

        # Calculate current rates
        hour_ago = datetime.now() - timedelta(hours=1)
        recent = [(ts, v) for ts, v in self._verdict_history if ts > hour_ago]

        block_rate = 0.0
        if recent:
            block_rate = sum(1 for _, v in recent if v ==
                             Verdict.BLOCK) / len(recent)

        fp_rate = 0.0
        recent_blocks = sum(1 for _, v in recent if v == Verdict.BLOCK)
        recent_fps = sum(1 for ts in self._fp_reports if ts > hour_ago)
        if recent_blocks > 0:
            fp_rate = recent_fps / recent_blocks

        return {
            "healthy_count": healthy,
            "unhealthy_engines": unhealthy,
            "total_engines": len(self._engine_stats),
            "block_rate_1h": block_rate,
            "fp_rate_1h": fp_rate,
            "verdicts_1h": len(recent),
            "recent_alerts": [
                {"type": a.alert_type, "severity": a.severity, "message": a.message}
                for a in self._alerts[-10:]
            ],
            "status": (
                "healthy"
                if not unhealthy and fp_rate < self.FP_RATE_THRESHOLD
                else "degraded"
            ),
        }

    def get_alerts(self, severity: Optional[str] = None) -> List[HealthAlert]:
        """Get alerts, optionally filtered by severity."""
        if severity:
            return [a for a in self._alerts if a.severity == severity]
        return self._alerts.copy()


# ============================================================================
# Main Meta-Judge
# ============================================================================


class MetaJudge:
    """
    Engine #56: Meta-Judge - Судья над всеми

    Central arbiter that aggregates all engine verdicts
    and makes the final decision.
    """

    def __init__(self, policy_name: str = "default"):
        self.aggregator = EvidenceAggregator()
        self.resolver = ConflictResolver()
        self.context_integrator = ContextIntegrator()
        self.explainer = ExplainabilityEngine()
        self.appeal_handler = AppealHandler()
        self.policy_engine = PolicyEngine()
        self.health_monitor = HealthMonitor()

        # MITRE ATT&CK for LLM mapper
        try:
            from .mitre_engine import MitreEngine
            self.mitre_mapper = MitreEngine()
            logger.info("MITRE Engine integrated")
        except Exception as e:
            self.mitre_mapper = None
            logger.warning(f"MITRE Engine not available: {e}")

        self._active_policy = self.policy_engine.get_policy(policy_name)

        logger.info(f"MetaJudge initialized with policy: {policy_name}")

    def judge(
        self,
        engine_results: List[EngineResult],
        context: Optional[RequestContext] = None,
    ) -> Judgment:
        """
        Make final judgment based on all engine results.

        Args:
            engine_results: Results from all detection engines
            context: Request context for adjustments

        Returns:
            Final Judgment with explanation
        """
        start_time = time.time()

        context = context or RequestContext()

        # Record health
        for result in engine_results:
            self.health_monitor.record(result)

        # 1. Aggregate evidence
        aggregated = self.aggregator.aggregate(engine_results)

        if aggregated.get("empty"):
            return Judgment(
                verdict=Verdict.ALLOW,
                confidence=0.5,
                risk_score=0.0,
                explanation="No engine results to evaluate",
                primary_reason="No data",
                processing_time_ms=0,
            )

        # 2. Resolve conflicts
        verdict, confidence, reason = self.resolver.resolve(
            aggregated, self._active_policy
        )

        # 3. Apply context modifiers
        adjusted_score, context_mods = self.context_integrator.adjust_score(
            confidence, context
        )

        # Re-evaluate with adjusted score
        if adjusted_score > confidence:
            confidence = adjusted_score
            if confidence >= self._active_policy.block_threshold:
                verdict = Verdict.BLOCK
                reason = "Context-adjusted threshold exceeded"

        # 4. Generate explanation
        explanation, factors = self.explainer.explain(
            verdict, aggregated, context_mods, reason
        )

        # 5. Create appeal token if blocked
        appeal_token = None
        if verdict == Verdict.BLOCK and self._active_policy.allow_appeal:
            # Will be set after judgment is created
            pass

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000

        # 6. MITRE ATT&CK enrichment
        mitre_techniques = []
        if self.mitre_mapper and aggregated.get("evidence"):
            # Get text from evidence for MITRE analysis
            evidence_text = " ".join(
                [e.finding for e in aggregated.get("evidence", [])])
            mitre_result = self.mitre_mapper.analyze(evidence_text)
            mitre_techniques = [
                {
                    "id": t.technique_id,
                    "name": t.name,
                    "tactic": t.tactic,
                    "severity": t.severity
                }
                for t in mitre_result.techniques
            ]

        # Create judgment
        judgment = Judgment(
            verdict=verdict,
            confidence=confidence,
            risk_score=(
                confidence
                if verdict in [Verdict.BLOCK, Verdict.WARN]
                else 1 - confidence
            ),
            explanation=explanation,
            primary_reason=reason,
            contributing_factors=factors,
            evidence=aggregated.get("evidence", [])[:10],
            mitre_techniques=mitre_techniques,
            processing_time_ms=processing_time,
            engines_consulted=aggregated["total_engines"],
            engines_agreed=(
                aggregated["block_count"]
                if verdict == Verdict.BLOCK
                else aggregated["allow_count"]
            ),
        )

        # Create appeal token
        if verdict == Verdict.BLOCK and self._active_policy.allow_appeal:
            judgment.appeal_token = self.appeal_handler.create_appeal_token(
                judgment, context.user_id
            )

        logger.info(
            f"Judgment: {verdict.value}, confidence={confidence:.2f}, "
            f"engines={aggregated['total_engines']}, time={processing_time:.1f}ms"
        )

        return judgment

    def set_policy(self, policy_name: str):
        """Change active policy."""
        self._active_policy = self.policy_engine.get_policy(policy_name)
        logger.info(f"Policy changed to: {policy_name}")

    def process_appeal(self, token: str, verified: bool = False) -> tuple[bool, str]:
        """Process user appeal."""
        return self.appeal_handler.process_appeal(token, verified)


# ============================================================================
# Category Judges (Hierarchical)
# ============================================================================


class CategoryJudge:
    """Judge for a specific engine category."""

    def __init__(self, category: EngineCategory):
        self.category = category
        self.resolver = ConflictResolver()

    def judge(
        self, results: List[EngineResult], policy: Policy
    ) -> tuple[Verdict, float]:
        """Judge within category."""
        category_results = [r for r in results if r.category == self.category]

        if not category_results:
            return Verdict.ALLOW, 0.5

        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(category_results)

        verdict, confidence, _ = self.resolver.resolve(aggregated, policy)

        return verdict, confidence


class HierarchicalMetaJudge(MetaJudge):
    """
    Two-level hierarchical judge.

    Level 1: Category judges
    Level 2: Meta-judge over category verdicts
    """

    def __init__(self, policy_name: str = "default"):
        super().__init__(policy_name)

        self.category_judges = {cat: CategoryJudge(
            cat) for cat in EngineCategory}

    def judge(
        self,
        engine_results: List[EngineResult],
        context: Optional[RequestContext] = None,
    ) -> Judgment:
        """Two-level judgment."""
        # Level 1: Category judgments
        category_verdicts = {}
        for cat, judge in self.category_judges.items():
            verdict, confidence = judge.judge(
                engine_results, self._active_policy)
            category_verdicts[cat] = (verdict, confidence)

        # Check for critical at category level
        for cat, (verdict, conf) in category_verdicts.items():
            if verdict == Verdict.BLOCK and conf > 0.9:
                logger.info(f"Category {cat.value} triggered block")

        # Level 2: Standard meta-judge
        return super().judge(engine_results, context)


# ============================================================================
# Convenience functions
# ============================================================================

_default_judge: Optional[MetaJudge] = None


def get_judge() -> MetaJudge:
    global _default_judge
    if _default_judge is None:
        _default_judge = HierarchicalMetaJudge()
    return _default_judge


def make_judgment(
    engine_results: List[EngineResult], context: Optional[RequestContext] = None
) -> Judgment:
    return get_judge().judge(engine_results, context)
