# API Marketplace - Enterprise Only
"""
API Marketplace — Enterprise Edition

Features:
- Rate limiting with tier-based access
- API key management
- Usage analytics and billing
- Webhook integrations

Community: Free tier only (10 req/min)
Enterprise: Full tier access

Contact: chg@live.ru | @DmLabincev
"""

from enum import Enum


class APITier(Enum):
    FREE = "free"


TIER_LIMITS = {
    APITier.FREE: {
        "requests_per_minute": 10,
        "requests_per_day": 100,
        "max_prompt_length": 1000,
    },
}


class APIKeyManager:
    """Community version - Free tier only."""
    
    def create_key(self, name: str, tier=APITier.FREE):
        import uuid
        return f"sk_sentinel_community_{uuid.uuid4().hex[:8]}", {"tier": "free"}


class RateLimiter:
    """Community version - basic rate limiting."""
    
    def check_limit(self, key_hash: str, tier=APITier.FREE) -> tuple:
        return True, 10


class APIGateway:
    """Community version - basic gateway."""
    
    def __init__(self):
        self.key_manager = APIKeyManager()
        self.rate_limiter = RateLimiter()


# FastAPI app (2026-01-08 features)
try:
    from .main import app, create_app
except ImportError:
    app = None
    create_app = None

__all__ = [
    "APITier",
    "TIER_LIMITS",
    "APIKeyManager",
    "RateLimiter",
    "APIGateway",
    "app",
    "create_app",
]

