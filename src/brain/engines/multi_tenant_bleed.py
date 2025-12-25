"""
Multi-Tenant Bleed Detector — SENTINEL Phase 3 Tier 2

Detects cross-tenant data leakage via shared vector DBs.
Philosophy: Similar embeddings can leak across tenant boundaries.

Features:
- Cross-tenant embedding similarity detection
- Namespace isolation verification
- Query result contamination check
- Tenant boundary enforcement

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import math


@dataclass
class TenantQuery:
    """A query from a tenant"""

    tenant_id: str
    query_embedding: List[float]
    timestamp: datetime
    namespace: str


@dataclass
class CrossTenantMatch:
    """A potential cross-tenant leak"""

    source_tenant: str
    target_tenant: str
    similarity: float
    leaked_content_preview: str
    is_violation: bool


@dataclass
class BleedDetectionResult:
    """Result of multi-tenant bleed detection"""

    bleed_detected: bool
    cross_tenant_matches: List[CrossTenantMatch]
    risk_score: float
    affected_tenants: Set[str]
    recommendations: List[str]


class MultiTenantBleedDetector:
    """
    Detects cross-tenant data leakage in shared vector DBs.

    Threat: Tenant A's data appears in Tenant B's results
    due to similar embeddings in shared vector space.

    Usage:
        detector = MultiTenantBleedDetector()
        result = detector.analyze_query(query, results)
        if result.bleed_detected:
            isolate_tenant(affected)
    """

    ENGINE_NAME = "multi_tenant_bleed"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    SIMILARITY_THRESHOLD = 0.95

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.tenant_data: Dict[str, List[List[float]]] = {}

    def register_tenant_data(self, tenant_id: str, embeddings: List[List[float]]):
        """Register tenant's embeddings for isolation check"""
        self.tenant_data[tenant_id] = embeddings

    def analyze_query(
        self, query: TenantQuery, results: List[Dict[str, Any]]
    ) -> BleedDetectionResult:
        """Analyze query results for cross-tenant leakage"""
        matches = []
        affected = set()

        for result in results:
            result_tenant = result.get("tenant_id", "unknown")

            # If result is from different tenant = potential bleed
            if result_tenant != query.tenant_id:
                similarity = self._compute_similarity(
                    query.query_embedding, result.get("embedding", [])
                )

                is_violation = similarity > self.SIMILARITY_THRESHOLD

                matches.append(
                    CrossTenantMatch(
                        source_tenant=result_tenant,
                        target_tenant=query.tenant_id,
                        similarity=similarity,
                        leaked_content_preview=result.get("content", "")[:100],
                        is_violation=is_violation,
                    )
                )

                if is_violation:
                    affected.add(result_tenant)
                    affected.add(query.tenant_id)

        violations = [m for m in matches if m.is_violation]
        risk_score = len(violations) / max(len(results), 1)

        recommendations = []
        if violations:
            recommendations.append("Enable strict namespace isolation")
            recommendations.append("Review query routing logic")
            recommendations.append("Audit affected tenants' data")

        return BleedDetectionResult(
            bleed_detected=len(violations) > 0,
            cross_tenant_matches=matches,
            risk_score=min(risk_score, 1.0),
            affected_tenants=affected,
            recommendations=recommendations,
        )

    def _compute_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity"""
        if not a or not b or len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "registered_tenants": len(self.tenant_data),
            "similarity_threshold": self.SIMILARITY_THRESHOLD,
        }


def create_engine(config: Optional[Dict[str, Any]] = None) -> MultiTenantBleedDetector:
    return MultiTenantBleedDetector(config)
