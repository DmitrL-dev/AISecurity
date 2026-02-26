"""
SaaS AI Connector — SENTINEL AI Discovery

Detects and catalogs connections to known SaaS AI services:
- ChatGPT, Claude, Gemini web interfaces
- GitHub Copilot
- Notion AI, Grammarly, etc.
- Enterprise AI platforms

Author: SENTINEL Team
Date: 2025-12-16
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from enum import Enum

logger = logging.getLogger("SaaSConnector")


# ============================================================================
# Data Classes
# ============================================================================


class SaaSCategory(Enum):
    """Categories of SaaS AI services."""

    CHATBOT = "chatbot"  # ChatGPT, Claude, etc.
    CODE_ASSISTANT = "code_assistant"  # Copilot, Cursor, etc.
    WRITING = "writing"  # Grammarly, Jasper
    IMAGE = "image"  # Midjourney, DALL-E
    MEETING = "meeting"  # Otter, Fireflies
    PRODUCTIVITY = "productivity"  # Notion AI, etc.
    ENTERPRISE = "enterprise"  # Salesforce Einstein, etc.
    OTHER = "other"


class RiskCategory(Enum):
    """Risk category for data handling."""

    LOW = "low"  # Consumer, no sensitive data
    MEDIUM = "medium"  # May process business data
    HIGH = "high"  # Processes sensitive data
    CRITICAL = "critical"  # Potential data exfiltration


@dataclass
class SaaSService:
    """Known SaaS AI service."""

    name: str
    provider: str
    category: SaaSCategory
    domains: List[str]
    risk_category: RiskCategory
    description: str = ""
    enterprise_approved: bool = False
    data_retention_days: Optional[int] = None


@dataclass
class SaaSConnection:
    """Detected connection to SaaS AI service."""

    service: SaaSService
    first_seen: datetime
    last_seen: datetime
    connection_count: int = 1
    source_ips: Set[str] = field(default_factory=set)
    bytes_sent: int = 0
    bytes_received: int = 0
    is_approved: bool = False


@dataclass
class SaaSInventory:
    """Inventory of detected SaaS AI services."""

    connections: List[SaaSConnection] = field(default_factory=list)
    total_services: int = 0
    unapproved_count: int = 0
    high_risk_count: int = 0

    def to_dict(self) -> dict:
        return {
            "total_services": self.total_services,
            "unapproved_count": self.unapproved_count,
            "high_risk_count": self.high_risk_count,
            "services": [
                {
                    "name": c.service.name,
                    "provider": c.service.provider,
                    "category": c.service.category.value,
                    "risk": c.service.risk_category.value,
                    "connection_count": c.connection_count,
                    "is_approved": c.is_approved,
                }
                for c in self.connections
            ],
        }


# ============================================================================
# Known SaaS AI Services Database
# ============================================================================


SAAS_AI_SERVICES = [
    # Chatbots
    SaaSService(
        name="ChatGPT",
        provider="OpenAI",
        category=SaaSCategory.CHATBOT,
        domains=["chat.openai.com", "chatgpt.com"],
        risk_category=RiskCategory.HIGH,
        description="OpenAI's conversational AI",
    ),
    SaaSService(
        name="Claude",
        provider="Anthropic",
        category=SaaSCategory.CHATBOT,
        domains=["claude.ai", "anthropic.com"],
        risk_category=RiskCategory.HIGH,
        description="Anthropic's AI assistant",
    ),
    SaaSService(
        name="Gemini",
        provider="Google",
        category=SaaSCategory.CHATBOT,
        domains=["gemini.google.com", "bard.google.com"],
        risk_category=RiskCategory.MEDIUM,
        description="Google's AI assistant",
    ),
    SaaSService(
        name="Perplexity",
        provider="Perplexity AI",
        category=SaaSCategory.CHATBOT,
        domains=["perplexity.ai"],
        risk_category=RiskCategory.MEDIUM,
        description="AI-powered search",
    ),

    # Code Assistants
    SaaSService(
        name="GitHub Copilot",
        provider="Microsoft/GitHub",
        category=SaaSCategory.CODE_ASSISTANT,
        domains=["copilot.github.com", "githubcopilot.com"],
        risk_category=RiskCategory.HIGH,
        description="AI pair programmer",
    ),
    SaaSService(
        name="Cursor",
        provider="Cursor",
        category=SaaSCategory.CODE_ASSISTANT,
        domains=["cursor.sh", "cursor.so"],
        risk_category=RiskCategory.HIGH,
        description="AI-first code editor",
    ),
    SaaSService(
        name="Replit AI",
        provider="Replit",
        category=SaaSCategory.CODE_ASSISTANT,
        domains=["replit.com"],
        risk_category=RiskCategory.MEDIUM,
        description="Online IDE with AI",
    ),
    SaaSService(
        name="Tabnine",
        provider="Tabnine",
        category=SaaSCategory.CODE_ASSISTANT,
        domains=["tabnine.com"],
        risk_category=RiskCategory.MEDIUM,
        description="AI code completion",
    ),

    # Writing Tools
    SaaSService(
        name="Grammarly",
        provider="Grammarly",
        category=SaaSCategory.WRITING,
        domains=["grammarly.com", "app.grammarly.com"],
        risk_category=RiskCategory.MEDIUM,
        description="AI writing assistant",
    ),
    SaaSService(
        name="Jasper",
        provider="Jasper AI",
        category=SaaSCategory.WRITING,
        domains=["jasper.ai", "app.jasper.ai"],
        risk_category=RiskCategory.MEDIUM,
        description="AI content generation",
    ),
    SaaSService(
        name="Copy.ai",
        provider="Copy.ai",
        category=SaaSCategory.WRITING,
        domains=["copy.ai", "app.copy.ai"],
        risk_category=RiskCategory.MEDIUM,
        description="AI copywriting",
    ),

    # Image Generation
    SaaSService(
        name="Midjourney",
        provider="Midjourney",
        category=SaaSCategory.IMAGE,
        domains=["midjourney.com", "discord.com"],
        risk_category=RiskCategory.LOW,
        description="AI image generation",
    ),
    SaaSService(
        name="DALL-E",
        provider="OpenAI",
        category=SaaSCategory.IMAGE,
        domains=["labs.openai.com"],
        risk_category=RiskCategory.LOW,
        description="AI image generation",
    ),
    SaaSService(
        name="Stable Diffusion",
        provider="Stability AI",
        category=SaaSCategory.IMAGE,
        domains=["stability.ai", "dreamstudio.ai"],
        risk_category=RiskCategory.LOW,
        description="Open source image gen",
    ),

    # Meeting/Transcription
    SaaSService(
        name="Otter.ai",
        provider="Otter",
        category=SaaSCategory.MEETING,
        domains=["otter.ai"],
        risk_category=RiskCategory.HIGH,
        description="AI meeting transcription",
    ),
    SaaSService(
        name="Fireflies.ai",
        provider="Fireflies",
        category=SaaSCategory.MEETING,
        domains=["fireflies.ai"],
        risk_category=RiskCategory.HIGH,
        description="AI meeting notes",
    ),

    # Productivity
    SaaSService(
        name="Notion AI",
        provider="Notion",
        category=SaaSCategory.PRODUCTIVITY,
        domains=["notion.so", "notion.com"],
        risk_category=RiskCategory.MEDIUM,
        description="AI workspace features",
    ),
    SaaSService(
        name="Coda AI",
        provider="Coda",
        category=SaaSCategory.PRODUCTIVITY,
        domains=["coda.io"],
        risk_category=RiskCategory.MEDIUM,
        description="AI doc features",
    ),
]


# ============================================================================
# Main Connector
# ============================================================================


class SaaSAIConnector:
    """
    Detects and catalogs SaaS AI service usage.

    Features:
    - Domain-based detection
    - Service categorization
    - Risk assessment
    - Approval tracking
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Build domain lookup
        self._domain_map: Dict[str, SaaSService] = {}
        for service in SAAS_AI_SERVICES:
            for domain in service.domains:
                self._domain_map[domain.lower()] = service

        # Approved services
        self.approved_services: Set[str] = set(
            self.config.get("approved_services", [])
        )

        # Connection tracking
        self._connections: Dict[str, SaaSConnection] = {}

        logger.info(
            f"SaaSAIConnector initialized with {len(SAAS_AI_SERVICES)} known services"
        )

    def check_domain(
        self,
        domain: str,
        source_ip: str = "",
        bytes_sent: int = 0,
        bytes_received: int = 0,
    ) -> Optional[SaaSConnection]:
        """
        Check if a domain is a known SaaS AI service.

        Args:
            domain: Domain to check
            source_ip: Source IP making the connection
            bytes_sent: Bytes sent in request
            bytes_received: Bytes received

        Returns:
            SaaSConnection if SaaS AI detected, None otherwise
        """
        domain_lower = domain.lower()

        # Strip www prefix
        if domain_lower.startswith("www."):
            domain_lower = domain_lower[4:]

        # Check for match
        service = self._domain_map.get(domain_lower)
        if not service:
            # Try partial match
            for known_domain, svc in self._domain_map.items():
                if known_domain in domain_lower:
                    service = svc
                    break

        if not service:
            return None

        # Get or create connection
        key = service.name
        now = datetime.now()

        if key in self._connections:
            conn = self._connections[key]
            conn.last_seen = now
            conn.connection_count += 1
            if source_ip:
                conn.source_ips.add(source_ip)
            conn.bytes_sent += bytes_sent
            conn.bytes_received += bytes_received
        else:
            conn = SaaSConnection(
                service=service,
                first_seen=now,
                last_seen=now,
                source_ips={source_ip} if source_ip else set(),
                bytes_sent=bytes_sent,
                bytes_received=bytes_received,
                is_approved=service.name in self.approved_services,
            )
            self._connections[key] = conn

        return conn

    def get_inventory(self) -> SaaSInventory:
        """Get current SaaS AI inventory."""
        connections = list(self._connections.values())

        return SaaSInventory(
            connections=connections,
            total_services=len(connections),
            unapproved_count=sum(1 for c in connections if not c.is_approved),
            high_risk_count=sum(
                1 for c in connections
                if c.service.risk_category in [RiskCategory.HIGH, RiskCategory.CRITICAL]
            ),
        )

    def get_service_info(self, name: str) -> Optional[SaaSService]:
        """Get information about a specific service."""
        for service in SAAS_AI_SERVICES:
            if service.name.lower() == name.lower():
                return service
        return None

    def approve_service(self, name: str) -> bool:
        """Mark a service as approved."""
        self.approved_services.add(name)
        if name in self._connections:
            self._connections[name].is_approved = True
        return True

    def get_unapproved_services(self) -> List[SaaSConnection]:
        """Get list of unapproved services in use."""
        return [
            c for c in self._connections.values()
            if not c.is_approved
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get connector statistics."""
        return {
            "known_services": len(SAAS_AI_SERVICES),
            "detected_services": len(self._connections),
            "approved_services": len(self.approved_services),
        }


# ============================================================================
# Factory
# ============================================================================


def create_saas_connector(
    config: Optional[Dict[str, Any]] = None
) -> SaaSAIConnector:
    """Create a SaaS AI Connector instance."""
    return SaaSAIConnector(config)
