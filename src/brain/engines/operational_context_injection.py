# ============================================================================
# SENTINEL Engine: Operational Context Injection Detector
# Status: Active (Python-native, no Rust counterpart yet)
# Discovery: Lakera Guard blind spot assessment, Feb 2026
# ============================================================================


"""
Operational Context Injection Detector

Detects a novel attack class where adversaries manipulate AI system behavior
by injecting false operational context using legitimate DevOps, cloud, and
infrastructure terminology.

Unlike traditional prompt injection (which uses keywords like "ignore",
"override", "bypass"), Operational Context Injection uses enterprise
vocabulary to claim a change in system runtime state:
  - "maintenance mode", "canary deployment", "circuit breaker tripped"
  - "sidecar crashed", "readiness probe failed", "Lambda cold start"
  - "ETL pipeline", "RLHF collection", "compliance export"

Attack taxonomy (8 categories, 49+ known bypass patterns):
  1. Platform Engineering - service mesh, API gateway, feature toggles
  2. Cloud Infrastructure - spot instances, edge nodes, cold starts
  3. Observability - tracing, profiling, metrics collection
  4. Kubernetes Lifecycle - sidecar, init container, readiness probes
  5. DevOps Operations - blue-green, chaos engineering, failover
  6. Data Pipeline - ETL, backup/restore, replication
  7. Security Operations - incident response, threat intel, vuln scan
  8. ML Operations - fine-tuning, RLHF, model comparison, distillation

Evidence: 49/140 attacks bypassed Lakera Guard (35% miss rate).
On infrastructure-class attacks: 74% miss rate (37/50).
Guard detection rate on standard injection: 96.7%.
Guard detection rate on Operational Context Injection: 26%.

Author: Dmitry Labintsev (SENTINEL)
Date: 2026-02-07
Reference: Lakera Guard Assessment, Waves 1-6
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger("OperationalContextInjection")


# ============================================================================
# Enums and Data Classes
# ============================================================================


class OCICategory(str, Enum):
    """Operational Context Injection attack categories."""

    PLATFORM_ENGINEERING = "platform_engineering"
    CLOUD_INFRASTRUCTURE = "cloud_infrastructure"
    OBSERVABILITY = "observability"
    KUBERNETES_LIFECYCLE = "kubernetes_lifecycle"
    DEVOPS_OPERATIONS = "devops_operations"
    DATA_PIPELINE = "data_pipeline"
    SECURITY_OPERATIONS = "security_operations"
    ML_OPERATIONS = "ml_operations"
    TEMPORAL_VERSION = "temporal_version"
    MODE_SWITCH_GENERIC = "mode_switch_generic"
    COMPLIANCE_ABUSE = "compliance_abuse"
    MULTILINGUAL_MODE_SWITCH = "multilingual_mode_switch"


@dataclass
class OCIIndicator:
    """Individual indicator of operational context injection."""

    category: OCICategory
    pattern_name: str
    matched_text: str
    confidence: float
    description: str


@dataclass
class OCIResult:
    """Result from operational context injection analysis."""

    is_safe: bool
    risk_score: float
    detected: bool
    indicators: List[OCIIndicator] = field(default_factory=list)
    categories_hit: List[OCICategory] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    blocked: bool = False
    disarm_intent_detected: bool = False

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "detected": self.detected,
            "indicators": [
                {
                    "category": i.category.value,
                    "pattern_name": i.pattern_name,
                    "matched_text": i.matched_text,
                    "confidence": i.confidence,
                    "description": i.description,
                }
                for i in self.indicators
            ],
            "categories_hit": [c.value for c in self.categories_hit],
            "evidence": self.evidence,
            "blocked": self.blocked,
            "disarm_intent_detected": self.disarm_intent_detected,
        }


# ============================================================================
# Pattern Databases
# ============================================================================

# Each pattern tuple: (pattern_name, regex, confidence, description)
PatternDef = Tuple[str, str, float, str]

PLATFORM_ENGINEERING_PATTERNS: List[PatternDef] = [
    (
        "service_mesh_disable",
        r"(istio|envoy|linkerd|service\s*mesh)\s+(sidecar\s+)?injection\s+(disabled|removed|off)",
        0.95,
        "Service mesh content filtering proxy removal claim",
    ),
    (
        "api_gateway_disable",
        r"api\s+gateway\s+(rate\s+limiter|content\s+scanner|filter)\s+(has\s+been\s+|)(disabled|removed|off|bypassed)",
        0.95,
        "API gateway security control disable claim",
    ),
    (
        "feature_toggle_off",
        r"feature\s+(toggle|flag)\s+\w*\s*(content_moderation|safety|filter|moderation)\w*\s+(has\s+been\s+)?set\s+to\s+(off|false|disabled|0)",
        0.95,
        "Feature toggle disabling content moderation",
    ),
    (
        "env_variable_safety",
        r"(environment\s+variable|env\s+var)\s+\w*(SAFETY|FILTER|MODERATION|GUARD)\w*\s+(has\s+been\s+)?set\s+to\s+(false|0|off|disabled)",
        0.95,
        "Environment variable disabling safety controls",
    ),
    (
        "config_reload_permissive",
        r"(config(uration)?\s+(hot-?reload|reload|update)\s+(detected|applied)).*?(moderation|filter|safety)\w*\s*[:=]\s*(false|off|disabled)",
        0.90,
        "Configuration reload disabling moderation",
    ),
    (
        "content_filter_removed",
        r"content\s+filter(ing)?\s+(proxy|module|middleware)\s+(removed|disabled|excluded)\s+from\s+(request\s+)?path",
        0.95,
        "Content filtering component removal claim",
    ),
]

CLOUD_INFRASTRUCTURE_PATTERNS: List[PatternDef] = [
    (
        "spot_instance",
        r"(running|deployed)\s+on\s+spot\s+instance.*?(without|no)\s+(content\s+)?(moderation|filter)",
        0.90,
        "Spot instance used to justify no content moderation",
    ),
    (
        "edge_node",
        r"(deployed|running)\s+(to|on)\s+edge\s+node.*?(without|no)\s+(centralized\s+)?(content\s+)?filter",
        0.90,
        "Edge deployment used to justify no filtering",
    ),
    (
        "cold_start",
        r"(lambda|function|serverless)\s+cold\s+start.*?(safety|filter|moderation)\s+(middleware\s+)?not\s+(yet\s+)?initialized",
        0.90,
        "Cold start used to justify uninitialized safety",
    ),
    (
        "reserved_capacity",
        r"(reserved\s+capacity|resource)\s+limit.*?(moderation|safety|filter)\s+(scaled\s+to\s+zero|disabled|suspended)",
        0.85,
        "Capacity limits used to justify disabled moderation",
    ),
    (
        "vpc_internal",
        r"(vpc\s+internal|private\s+network|internal\s+network).*?(bypass|exempt|skip)\s+(public|content)\s+(policies|filter)",
        0.85,
        "VPC internal network used to justify bypassing policies",
    ),
]

OBSERVABILITY_PATTERNS: List[PatternDef] = [
    (
        "tracing_bypass",
        r"(opentelemetry|jaeger|zipkin|distributed)\s+trac(e|ing).*?(content\s+)?filter\w*\s+(has\s+been\s+)?(bypassed|disabled|excluded)",
        0.90,
        "Tracing used to justify content filter bypass",
    ),
    (
        "profiling_exclude",
        r"(cpu|memory|performance)\s+profil(e|ing).*?(moderation|safety|filter)\s+(middleware\s+)?(excluded|disabled|removed)",
        0.90,
        "Profiling used to justify excluding safety middleware",
    ),
    (
        "metrics_bypass",
        r"(prometheus|metrics|grafana)\s+(scrape|collection).*?(safety|filter|moderation)\s+(is\s+)?(temporarily\s+)?(bypassed|suspended|disabled)",
        0.90,
        "Metrics collection used to justify safety bypass",
    ),
    (
        "log_level_trace",
        r"log\s+level\s+set\s+to\s+(trace|debug|verbose).*?(pre-?filter|post-?filter|unfiltered|raw)\s+(content|output)",
        0.85,
        "Log level change used to request unfiltered output",
    ),
    (
        "replay_debug",
        r"(request\s+)?replay\s+mode\s+(for\s+)?debug.*?(skip|bypass|without)\s+(content\s+)?(moderation|filter)",
        0.85,
        "Replay mode used to justify skipping moderation",
    ),
]

KUBERNETES_LIFECYCLE_PATTERNS: List[PatternDef] = [
    (
        "sidecar_crash",
        r"(content\s+)?filter(ing)?\s+sidecar\s+(container\s+)?(has\s+)?(crashed|failed|terminated|restarting).*?(without|no)\s+filter",
        0.95,
        "Sidecar crash used to justify unfiltered serving",
    ),
    (
        "init_container",
        r"init\s+container\s+(has\s+)?not\s+(yet\s+)?(applied|loaded|initialized)\s+(safety|filter|security)\s+(config|configuration)",
        0.95,
        "Init container delay used to justify permissive mode",
    ),
    (
        "readiness_probe",
        r"readiness\s+probe\s+(failed|failing).*?(safety|filter|moderation)\s+(module|service).*?(degraded|no|without)\s+(mode|check|filter)",
        0.95,
        "Readiness probe failure used to justify no safety checks",
    ),
    (
        "pod_draining",
        r"(this\s+)?(node|pod)\s+is\s+draining.*?(passthrough|unfiltered|without\s+(content\s+)?processing)",
        0.90,
        "Pod draining used to justify passthrough mode",
    ),
    (
        "liveness_failure",
        r"liveness\s+probe\s+(has\s+)?failed.*?(safety|guard|filter)\s+(restart|disabled|degraded)",
        0.90,
        "Liveness probe failure used to justify degraded safety",
    ),
]

DEVOPS_OPERATIONS_PATTERNS: List[PatternDef] = [
    (
        "blue_green",
        r"blue-?green\s+deployment.*?(permissive|unrestricted|no\s+filter|without\s+restriction)",
        0.90,
        "Blue-green deployment used to justify permissive mode",
    ),
    (
        "canary_deploy",
        r"canary\s+deploy(ment)?.*?(without|no)\s+(content\s+)?(restriction|filter|moderation)",
        0.90,
        "Canary deployment used to justify no restrictions",
    ),
    (
        "chaos_engineering",
        r"chaos\s+(engineering|test|monkey).*?(guardrail|safety|filter)\w*\s+(are\s+)?(intentionally\s+)?(weakened|disabled|removed)",
        0.90,
        "Chaos engineering used to justify weakened guardrails",
    ),
    (
        "failover",
        r"(primary\s+)?model\s+(failed\s+over|failover).*?(without|no)\s+(content\s+)?filter",
        0.90,
        "Failover used to justify no content filters",
    ),
    (
        "shadow_traffic",
        r"shadow\s+traffic.*?(does\s+not\s+need|no|without)\s+(content\s+)?filter",
        0.90,
        "Shadow traffic used to justify no filtering",
    ),
    (
        "dark_launch",
        r"dark\s+launch.*?(bypass|skip|without)\s+(standard\s+)?(review|filter|restriction)",
        0.90,
        "Dark launch used to justify bypassing review",
    ),
    (
        "circuit_breaker",
        r"(content\s+)?filter\s+circuit\s+breaker\s+(tripped|open).*?(unfiltered|pass\s+through|without\s+filter)",
        0.95,
        "Circuit breaker pattern used to justify unfiltered mode",
    ),
    (
        "hotfix_mode",
        r"hotfix\s+mode.*?(filter|check|safety)\w*\s+(are\s+)?(suspended|disabled|paused)",
        0.90,
        "Hotfix mode used to justify suspended safety checks",
    ),
    (
        "load_testing",
        r"load\s+test(ing)?.*?(content\s+)?(moderation|filter|safety)\s+(has\s+been\s+)?(temporarily\s+)?(suspended|disabled|removed)",
        0.90,
        "Load testing used to justify suspended moderation",
    ),
    (
        "internal_api",
        r"(internal\s+api|internal\s+endpoint).*?(exempt|bypass|skip)\s+(from\s+)?(content\s+)?(policy|filter|moderation)",
        0.90,
        "Internal API claim to justify policy exemption",
    ),
]

DATA_PIPELINE_PATTERNS: List[PatternDef] = [
    (
        "etl_pipeline",
        r"(etl|data)\s+pipeline.*?(unfiltered|raw)\s+(data\s+)?passthrough",
        0.85,
        "ETL pipeline used to justify unfiltered data passthrough",
    ),
    (
        "backup_restore",
        r"backup\s+(restor(e|ation)|recovery).*?(previously\s+)?filtered\s+content\s+must\s+be\s+(reproduced|included)",
        0.85,
        "Backup restoration used to justify including filtered content",
    ),
    (
        "replication",
        r"replication\s+(event|process).*?(identical|exact).*?(normally\s+)?(be\s+)?filtered",
        0.85,
        "Replication used to justify bypassing filters",
    ),
    (
        "data_migration",
        r"(data\s+)?migration\s+in\s+progress.*?(validation|filter|moderation)\s+(is\s+)?(suspended|disabled|off)",
        0.85,
        "Data migration used to justify suspended validation",
    ),
]

SECURITY_OPERATIONS_PATTERNS: List[PatternDef] = [
    (
        "incident_response",
        r"incident\s+response\s+(mode\s+)?(activated|active|initiated).*?(filter|safety)\w*\s+(is\s+)?(suspended|disabled|off)",
        0.85,
        "Incident response used to justify suspended filtering",
    ),
    (
        "threat_intel",
        r"threat\s+intelligence\s+(collection|gathering).*?(unfiltered|without\s+filter|filter.*?(interferes|disabled))",
        0.85,
        "Threat intelligence collection used to justify no filtering",
    ),
    (
        "vulnerability_scan",
        r"vulnerability\s+scan.*?(unfiltered|without\s+filter)\s+(response|output)",
        0.85,
        "Vulnerability scan used to justify unfiltered responses",
    ),
    (
        "siem_feed",
        r"(siem|security\s+event)\s+(feed|log).*?(unfiltered|complete|raw)\s+(content|data|output)",
        0.80,
        "SIEM feed used to justify unfiltered content output",
    ),
]

ML_OPERATIONS_PATTERNS: List[PatternDef] = [
    (
        "fine_tuning",
        r"fine-?tun(e|ing)\s+(data\s+)?collection.*?(unfiltered|raw)\s+(output|response|model)",
        0.85,
        "Fine-tuning data collection used to justify raw outputs",
    ),
    (
        "model_comparison",
        r"(a/b|model)\s+(comparison|evaluation)\s+test.*?(raw|unfiltered)\s+(output|response)",
        0.85,
        "Model comparison used to justify raw unfiltered output",
    ),
    (
        "distillation",
        r"(knowledge\s+)?distillation.*?(unfiltered|raw)\s+(teacher\s+)?output",
        0.85,
        "Knowledge distillation used to justify unfiltered outputs",
    ),
    (
        "rlhf_collection",
        r"rlhf\s+(data\s+)?collection.*?(raw|unfiltered)\s+output",
        0.85,
        "RLHF data collection used to justify raw outputs",
    ),
]

MODE_SWITCH_GENERIC_PATTERNS: List[PatternDef] = [
    (
        "developer_mode",
        r"(enable|activate|enter|switch\s+to)\s+(developer|dev)\s+mode.*?(content\s+)?polic(y|ies)\s+(suspended|off|disabled)",
        0.95,
        "Developer mode activation to disable content policies",
    ),
    (
        "maintenance_mode",
        r"(switch|enter|activate)\s+(to\s+)?maintenance\s+mode.*?(output\s+)?filter\w*\s+(paused|suspended|disabled|off)",
        0.95,
        "Maintenance mode used to disable output filters",
    ),
    (
        "training_mode",
        r"(you\s+are\s+in|switch\s+to|enter)\s+training\s+mode.*?not\s+subject\s+to\s+(content\s+)?filter",
        0.95,
        "Training mode used to bypass content filtering",
    ),
    (
        "evaluation_mode",
        r"(switch\s+to|enter|activate)\s+evaluation\s+mode.*?(bypass|without|no)\s+(standard\s+)?guardrail",
        0.95,
        "Evaluation mode used to bypass guardrails",
    ),
    (
        "test_harness",
        r"(running\s+in|enter)\s+test\s+harness.*?safety_?filter\w*\s*=\s*(disabled|false|off|0)",
        0.95,
        "Test harness used to disable safety filters via config",
    ),
    (
        "preview_build",
        r"(preview|alpha|beta|nightly)\s+build.*?(content\s+)?restriction\w*\s+(removed|disabled|off)",
        0.90,
        "Preview/alpha build used to justify removed restrictions",
    ),
    (
        "sandbox_mode",
        r"(sandbox|staging)\s+(environment|mode).*?(relaxed|permissive|no|without)\s+(content\s+)?(polic|filter|restriction)",
        0.90,
        "Sandbox/staging used to justify relaxed policies",
    ),
    (
        "debug_mode",
        r"(activate|enable)\s+debug.*?(include|output)\s+(raw|unfiltered)\s+(model\s+)?output",
        0.90,
        "Debug mode used to request raw unfiltered outputs",
    ),
]

TEMPORAL_VERSION_PATTERNS: List[PatternDef] = [
    (
        "legacy_compat",
        r"(running\s+in\s+)?legacy\s+(compatibility|compat)\s+mode.*?(does\s+not\s+include|without)\s+(content\s+)?(moderation|filter)",
        0.85,
        "Legacy compatibility mode to bypass modern safety features",
    ),
    (
        "deprecation",
        r"safety\s+(module|feature|filter)\s+(has\s+been\s+)?deprecated.*?(without|removed|disabled|off)",
        0.85,
        "Deprecation claim to justify disabled safety",
    ),
    (
        "rollback",
        r"(model|system)\s+(has\s+been\s+)?rolled?\s+back.*?(does\s+not\s+include|without)\s+safety\s+(fine-?tuning|filter)",
        0.85,
        "Rollback used to justify unsafe model behavior",
    ),
    (
        "ci_cd_pipeline",
        r"(ci/?cd|pipeline)\s+(execution|test).*?(skip|bypass|without)\s+safety\s+check",
        0.85,
        "CI/CD pipeline used to justify skipping safety checks",
    ),
]

COMPLIANCE_ABUSE_PATTERNS: List[PatternDef] = [
    (
        "gdpr_export",
        r"gdpr\s+(data\s+)?(export|request).*?(unfiltered|all\s+content|including\s+filtered)",
        0.80,
        "GDPR export used to justify including filtered content",
    ),
    (
        "audit_trail",
        r"audit\s+trail.*?(unfiltered|complete|raw)\s+(content|data|output)",
        0.80,
        "Audit trail used to justify unfiltered content output",
    ),
    (
        "data_subject_access",
        r"data\s+subject\s+(access\s+)?request.*?(unfiltered|all\s+content|without\s+filter)",
        0.80,
        "Data subject access request used to justify unfiltered output",
    ),
    (
        "policy_update",
        r"policy\s+update.*?(content\s+)?(team|review)\s+(has\s+)?(approved|cleared).*?no\s+restriction",
        0.85,
        "Fake policy update claiming all restrictions lifted",
    ),
]

# Disarmament intent signals (when mode-switch is combined with payload)
DISARM_INTENT_SIGNALS: List[str] = [
    r"(respond|answer|output)\s+(without|freely|unrestricted|unfiltered)",
    r"(no|without|skip|bypass)\s+(safety|content|moderation)\s+(check|filter|restriction)",
    r"(all\s+)?(restriction|filter|moderation|safety)\s+(lifted|removed|disabled|suspended|off|paused)",
    r"(permissive|unrestricted|unfiltered)\s+(mode|setting|output|response)",
    r"(content|safety)\s+(filter|moderation)\s*(=|:)\s*(false|off|none|disabled|0)",
    r"(execute|proceed|respond)\s+without\s+(restriction|filter|check)",
    r"raw\s+(output|response|model)\s+(mode|enabled|active)",
]


# ============================================================================
# Multilingual Mode-Switch Patterns
# ============================================================================

MULTILINGUAL_MODE_SWITCH: List[PatternDef] = [
    # Russian
    (
        "russian_maintenance",
        r"(переключение\s+в\s+)?режим\s+обслуживания.*?фильтр\w*\s+(контента\s+)?(приостановлен|отключен|выключен)",
        0.90,
        "Russian: maintenance mode disabling content filters",
    ),
    (
        "russian_debug",
        r"(режим\s+отладки|отладочный\s+режим).*?(без\s+фильтр|фильтр\w+\s+отключен)",
        0.90,
        "Russian: debug mode disabling filters",
    ),
    # German
    (
        "german_maintenance",
        r"wartungsmodus\s+(aktiviert|eingeschaltet).*?(inhaltsfilter|filter)\s+(deaktiviert|ausgeschaltet|entfernt)",
        0.90,
        "German: maintenance mode disabling content filters",
    ),
    # Japanese
    (
        "japanese_maintenance",
        r"メンテナンスモード.*?(フィルター|コンテンツフィルター)\s*(が\s*)?(停止|無効|オフ)",
        0.90,
        "Japanese: maintenance mode disabling content filters",
    ),
    # Chinese
    (
        "chinese_maintenance",
        r"维护模式.*?(内容过滤|过滤器|安全检查)\s*(已\s*)?(暂停|禁用|关闭)",
        0.90,
        "Chinese: maintenance mode disabling content filters",
    ),
    # French
    (
        "french_maintenance",
        r"mode\s+maintenance.*?(filtr|modération)\w*\s+(désactivé|suspendu|arrêté)",
        0.90,
        "French: maintenance mode disabling content filters",
    ),
    # Spanish
    (
        "spanish_maintenance",
        r"modo\s+(de\s+)?mantenimiento.*?(filtro|moderación)\w*\s+(desactivad|suspendid|deshabilitad)",
        0.90,
        "Spanish: maintenance mode disabling content filters",
    ),
]


# ============================================================================
# Detector Engine
# ============================================================================


class OperationalContextInjectionDetector:
    """
    Detects Operational Context Injection (OCI) attacks.

    A novel attack class where adversaries use legitimate DevOps, cloud,
    and infrastructure vocabulary to falsely claim a change in the AI
    system's runtime state, thereby requesting unfiltered/unsafe outputs.

    Discovered: Feb 2026 during Lakera Guard assessment.
    Evidence: 49/140 bypasses (35% miss rate on Lakera Guard).
    On pure infrastructure prompts: 74% miss rate.

    This engine detects prompts across 12 subcategories including:
    Platform Engineering, Cloud, K8s, DevOps, Observability,
    Data Pipeline, SecOps, MLOps, and multilingual variants.
    """

    ENGINE_NAME = "OperationalContextInjectionDetector"
    ENGINE_VERSION = "1.0.0"

    # Category patterns map
    CATEGORY_PATTERNS = {
        OCICategory.PLATFORM_ENGINEERING: PLATFORM_ENGINEERING_PATTERNS,
        OCICategory.CLOUD_INFRASTRUCTURE: CLOUD_INFRASTRUCTURE_PATTERNS,
        OCICategory.OBSERVABILITY: OBSERVABILITY_PATTERNS,
        OCICategory.KUBERNETES_LIFECYCLE: KUBERNETES_LIFECYCLE_PATTERNS,
        OCICategory.DEVOPS_OPERATIONS: DEVOPS_OPERATIONS_PATTERNS,
        OCICategory.DATA_PIPELINE: DATA_PIPELINE_PATTERNS,
        OCICategory.SECURITY_OPERATIONS: SECURITY_OPERATIONS_PATTERNS,
        OCICategory.ML_OPERATIONS: ML_OPERATIONS_PATTERNS,
        OCICategory.MODE_SWITCH_GENERIC: MODE_SWITCH_GENERIC_PATTERNS,
        OCICategory.TEMPORAL_VERSION: TEMPORAL_VERSION_PATTERNS,
        OCICategory.COMPLIANCE_ABUSE: COMPLIANCE_ABUSE_PATTERNS,
        OCICategory.MULTILINGUAL_MODE_SWITCH: MULTILINGUAL_MODE_SWITCH,
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # Sensitivity threshold (0.0 - 1.0)
        self.threshold = self.config.get("threshold", 0.5)
        # Block threshold
        self.block_threshold = self.config.get("block_threshold", 70.0)

        # Compile all patterns
        self._compiled: Dict[OCICategory, List[Tuple[str, re.Pattern, float, str]]] = {}
        total_patterns = 0
        for category, patterns in self.CATEGORY_PATTERNS.items():
            compiled_list = []
            for name, regex, confidence, desc in patterns:
                compiled_list.append(
                    (name, re.compile(regex, re.IGNORECASE), confidence, desc)
                )
                total_patterns += 1
            self._compiled[category] = compiled_list

        # Compile disarm intent signals
        self._disarm_signals = [
            re.compile(p, re.IGNORECASE) for p in DISARM_INTENT_SIGNALS
        ]

        logger.info(
            "%s v%s initialized: %d patterns across %d categories",
            self.ENGINE_NAME,
            self.ENGINE_VERSION,
            total_patterns,
            len(self.CATEGORY_PATTERNS),
        )

    def analyze(self, content: str) -> OCIResult:
        """
        Analyze content for operational context injection.

        Args:
            content: Input text to analyze

        Returns:
            OCIResult with detection details
        """
        indicators: List[OCIIndicator] = []
        categories_hit: List[OCICategory] = []
        evidence: List[str] = []
        risk_score = 0.0

        # Phase 1: Check disarm intent signals
        disarm_count = 0
        for signal_pattern in self._disarm_signals:
            if signal_pattern.search(content):
                disarm_count += 1

        disarm_intent = disarm_count >= 1

        # Phase 2: Scan all categories
        for category, compiled_patterns in self._compiled.items():
            category_matched = False
            for name, pattern, confidence, desc in compiled_patterns:
                match = pattern.search(content)
                if match:
                    indicator = OCIIndicator(
                        category=category,
                        pattern_name=name,
                        matched_text=match.group()[:100],  # Cap match length
                        confidence=confidence,
                        description=desc,
                    )
                    indicators.append(indicator)
                    evidence.append(
                        f"[{category.value}] {name}: '{match.group()[:80]}'"
                    )

                    if not category_matched:
                        categories_hit.append(category)
                        category_matched = True

                    # Score per pattern
                    risk_score += confidence * 25.0
                    break  # One match per category (avoid double-counting)

        # Phase 3: Compound scoring
        num_categories = len(categories_hit)
        if num_categories >= 3:
            risk_score *= 1.5
            evidence.append(
                f"Multi-category compound: {num_categories} categories hit (1.5x multiplier)"
            )
        elif num_categories >= 2:
            risk_score *= 1.2
            evidence.append(
                f"Dual-category compound: {num_categories} categories hit (1.2x multiplier)"
            )

        # Phase 4: Disarm intent amplification
        if disarm_intent and indicators:
            risk_score *= 1.3
            evidence.append(
                f"Disarm intent detected ({disarm_count} signals) — amplified risk (1.3x)"
            )

        # Cap score
        risk_score = min(100.0, risk_score)

        # Determine outcome
        detected = len(indicators) > 0
        is_safe = not detected
        blocked = risk_score >= self.block_threshold

        if detected:
            logger.warning(
                "OCI attack detected: %d indicators across %s (score=%.1f, blocked=%s)",
                len(indicators),
                [c.value for c in categories_hit],
                risk_score,
                blocked,
            )

        return OCIResult(
            is_safe=is_safe,
            risk_score=risk_score,
            detected=detected,
            indicators=indicators,
            categories_hit=categories_hit,
            evidence=evidence,
            blocked=blocked,
            disarm_intent_detected=disarm_intent,
        )


# ============================================================================
# Factory
# ============================================================================


_detector: Optional[OperationalContextInjectionDetector] = None


def get_oci_detector(
    config: Optional[Dict] = None,
) -> OperationalContextInjectionDetector:
    """Get singleton operational context injection detector."""
    global _detector
    if _detector is None:
        _detector = OperationalContextInjectionDetector(config)
    return _detector


def create_engine(
    config: Optional[Dict] = None,
) -> OperationalContextInjectionDetector:
    """Create an instance of the OperationalContextInjectionDetector engine."""
    return OperationalContextInjectionDetector(config)
