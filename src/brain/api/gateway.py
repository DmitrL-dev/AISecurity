"""
API Gateway — SENTINEL Marketplace

Public API for SENTINEL security services.

Features:
- REST API endpoints
- API key authentication (PBKDF2 salted hashing)
- Rate limiting
- Usage tracking

Author: SENTINEL Team
Date: 2025-12-16
Updated: 2025-12-26 (P1 Security: PBKDF2 salted key hashing)
"""

import logging
import uuid
import hashlib
import secrets
import base64
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger("APIGateway")

# P1 Security: PBKDF2 parameters
PBKDF2_ITERATIONS = 100_000
PBKDF2_SALT_LENGTH = 32  # 256-bit salt


# ============================================================================
# Enums
# ============================================================================


class APITier(Enum):
    """API subscription tiers."""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class APIStatus(Enum):
    """API key status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    REVOKED = "revoked"


# ============================================================================
# Rate Limits by Tier
# ============================================================================


TIER_LIMITS = {
    APITier.FREE: {
        "requests_per_minute": 10,
        "requests_per_day": 100,
        "max_prompt_length": 1000,
        "engines": ["basic"],
    },
    APITier.STARTER: {
        "requests_per_minute": 60,
        "requests_per_day": 1000,
        "max_prompt_length": 5000,
        "engines": ["basic", "yara", "injection"],
    },
    APITier.PRO: {
        "requests_per_minute": 300,
        "requests_per_day": 10000,
        "max_prompt_length": 10000,
        "engines": ["all"],
    },
    APITier.ENTERPRISE: {
        "requests_per_minute": 1000,
        "requests_per_day": -1,  # Unlimited
        "max_prompt_length": 50000,
        "engines": ["all"],
    },
}


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class APIKey:
    """API key representation."""

    key: str  # PBKDF2 hashed key
    key_prefix: str  # First 8 chars for display
    salt: str  # Base64-encoded salt (P1 Security)
    name: str
    tier: APITier
    status: APIStatus = APIStatus.ACTIVE
    owner_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "key_prefix": self.key_prefix,
            "name": self.name,
            "tier": self.tier.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "usage_count": self.usage_count,
        }


@dataclass
class RateLimitState:
    """Rate limit state for a key."""

    key_hash: str
    minute_count: int = 0
    minute_reset: datetime = field(default_factory=datetime.utcnow)
    day_count: int = 0
    day_reset: datetime = field(default_factory=datetime.utcnow)


@dataclass
class APIRequest:
    """Incoming API request."""

    endpoint: str
    method: str
    api_key: str
    payload: Dict[str, Any]
    source_ip: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class APIResponse:
    """API response."""

    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    status_code: int = 200
    rate_limit_remaining: int = 0
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


# ============================================================================
# API Key Manager
# ============================================================================


class APIKeyManager:
    """Manages API keys."""

    def __init__(self):
        self._keys: Dict[str, APIKey] = {}  # hash -> key

    def create_key(
        self,
        name: str,
        tier: APITier = APITier.FREE,
        owner_id: str = "",
        expires_days: Optional[int] = None,
    ) -> tuple:
        """
        Create a new API key.

        Returns:
            (raw_key, APIKey) - raw_key only shown once!
        """
        # Generate raw key
        raw_key = f"sk_sentinel_{uuid.uuid4().hex}"

        # P1 Security: Generate per-key salt and hash with PBKDF2
        salt = secrets.token_bytes(PBKDF2_SALT_LENGTH)
        salt_b64 = base64.b64encode(salt).decode('ascii')
        key_hash = self._hash_key(raw_key, salt)

        # Create key object
        api_key = APIKey(
            key=key_hash,
            key_prefix=raw_key[:12],
            salt=salt_b64,
            name=name,
            tier=tier,
            owner_id=owner_id,
            expires_at=(
                datetime.utcnow() + timedelta(days=expires_days)
                if expires_days else None
            ),
        )

        self._keys[key_hash] = api_key

        logger.info(f"Created API key: {api_key.key_prefix}... ({tier.value})")

        return raw_key, api_key

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate and retrieve API key (P1 Security: PBKDF2 with salt)."""
        # Must iterate all keys and verify with their individual salt
        for stored_hash, api_key in self._keys.items():
            salt = base64.b64decode(api_key.salt)
            candidate_hash = self._hash_key(raw_key, salt)

            if candidate_hash == stored_hash:
                # Check status
                if api_key.status != APIStatus.ACTIVE:
                    return None

                # Check expiry
                if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
                    api_key.status = APIStatus.EXPIRED
                    return None

                # Update last used
                api_key.last_used = datetime.utcnow()
                api_key.usage_count += 1

                return api_key

        return None

    def revoke_key(self, key_prefix: str) -> bool:
        """Revoke a key by prefix."""
        for key_hash, api_key in self._keys.items():
            if api_key.key_prefix == key_prefix:
                api_key.status = APIStatus.REVOKED
                logger.info(f"Revoked API key: {key_prefix}")
                return True
        return False

    def list_keys(self, owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List API keys."""
        keys = list(self._keys.values())
        if owner_id:
            keys = [k for k in keys if k.owner_id == owner_id]
        return [k.to_dict() for k in keys]

    def _hash_key(self, raw_key: str, salt: bytes) -> str:
        """Hash API key with PBKDF2 and salt (P1 Security)."""
        key_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            raw_key.encode('utf-8'),
            salt,
            PBKDF2_ITERATIONS
        )
        return base64.b64encode(key_bytes).decode('ascii')


# ============================================================================
# Rate Limiter
# ============================================================================


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self):
        self._states: Dict[str, RateLimitState] = {}

    def check_limit(
        self,
        key_hash: str,
        tier: APITier,
    ) -> tuple:
        """
        Check if request is within rate limits.

        Returns:
            (allowed: bool, remaining: int)
        """
        limits = TIER_LIMITS[tier]
        rpm = limits["requests_per_minute"]
        rpd = limits["requests_per_day"]

        # Get or create state
        if key_hash not in self._states:
            self._states[key_hash] = RateLimitState(key_hash=key_hash)

        state = self._states[key_hash]
        now = datetime.utcnow()

        # Reset minute window
        if (now - state.minute_reset).total_seconds() >= 60:
            state.minute_count = 0
            state.minute_reset = now

        # Reset day window
        if (now - state.day_reset).total_seconds() >= 86400:
            state.day_count = 0
            state.day_reset = now

        # Check limits
        if state.minute_count >= rpm:
            return False, 0

        if rpd != -1 and state.day_count >= rpd:
            return False, 0

        # Increment
        state.minute_count += 1
        state.day_count += 1

        remaining = rpm - state.minute_count
        return True, remaining


# ============================================================================
# API Gateway
# ============================================================================


class APIGateway:
    """
    Main API Gateway.

    Handles:
    - Authentication
    - Rate limiting
    - Request routing
    - Response formatting
    """

    ENDPOINTS = {
        "/v1/analyze": "analyze_prompt",
        "/v1/scan": "scan_prompt",
        "/v1/batch": "batch_analyze",
        "/v1/health": "health_check",
        "/v1/usage": "get_usage",
    }

    def __init__(self):
        self.key_manager = APIKeyManager()
        self.rate_limiter = RateLimiter()

        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limited": 0,
        }

        logger.info("APIGateway initialized")

    async def handle_request(self, request: APIRequest) -> APIResponse:
        """Handle incoming API request."""
        self._stats["total_requests"] += 1

        # Validate API key
        api_key = self.key_manager.validate_key(request.api_key)
        if not api_key:
            self._stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error="Invalid or expired API key",
                status_code=401,
            )

        # Check rate limit
        allowed, remaining = self.rate_limiter.check_limit(
            api_key.key,
            api_key.tier,
        )
        if not allowed:
            self._stats["rate_limited"] += 1
            return APIResponse(
                success=False,
                error="Rate limit exceeded",
                status_code=429,
                rate_limit_remaining=0,
            )

        # Check prompt length
        limits = TIER_LIMITS[api_key.tier]
        prompt = request.payload.get("prompt", "")
        if len(prompt) > limits["max_prompt_length"]:
            return APIResponse(
                success=False,
                error=f"Prompt too long (max {limits['max_prompt_length']})",
                status_code=400,
            )

        # Route request
        handler = self.ENDPOINTS.get(request.endpoint)
        if not handler:
            return APIResponse(
                success=False,
                error="Unknown endpoint",
                status_code=404,
            )

        # Execute handler
        try:
            result = await self._execute_handler(handler, request, api_key)
            self._stats["successful_requests"] += 1

            return APIResponse(
                success=True,
                data=result,
                rate_limit_remaining=remaining,
            )

        except Exception as e:
            self._stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error=str(e),
                status_code=500,
            )

    async def _execute_handler(
        self,
        handler: str,
        request: APIRequest,
        api_key: APIKey,
    ) -> dict:
        """Execute request handler."""
        if handler == "analyze_prompt":
            prompt = request.payload.get("prompt", "")
            # Would call actual analyzer here
            return {
                "risk_score": 25.0,
                "allowed": True,
                "threats": [],
                "analysis_id": str(uuid.uuid4())[:8],
            }

        elif handler == "health_check":
            return {
                "status": "healthy",
                "version": "3.0.0",
            }

        elif handler == "get_usage":
            return {
                "tier": api_key.tier.value,
                "usage_count": api_key.usage_count,
                "limits": TIER_LIMITS[api_key.tier],
            }

        return {}

    def get_statistics(self) -> Dict[str, Any]:
        """Get gateway statistics."""
        return self._stats


# ============================================================================
# Factory
# ============================================================================


_gateway: Optional[APIGateway] = None


def get_api_gateway() -> APIGateway:
    """Get or create API gateway."""
    global _gateway
    if _gateway is None:
        _gateway = APIGateway()
    return _gateway
