"""
SENTINEL Engine Toggle API

Secure endpoints for enabling/disabling engines with:
- API key authentication
- Critical engine blocklist
- Audit logging
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import hashlib

router = APIRouter(prefix="/engines", tags=["engines"])

# Critical engines that cannot be disabled
CRITICAL_ENGINES = {"pii", "injection", "prompt_guard"}

# In-memory audit log (will be replaced with proper storage)
_audit_log: list = []

# API key from environment (generate random if not set)
API_KEY = os.getenv("SENTINEL_API_KEY", "sentinel-dev-key-change-me")


class ToggleResponse(BaseModel):
    """Response from toggle operation."""

    engine: str
    enabled: bool
    message: str


class AuditEntry(BaseModel):
    """Audit log entry."""

    timestamp: str
    engine: str
    action: str
    key_fingerprint: str
    success: bool
    reason: Optional[str] = None


def _validate_api_key(api_key: Optional[str], user_email: Optional[str] = None) -> str:
    """Validate API key and return actor identifier."""
    if not api_key:
        raise HTTPException(
            status_code=401, detail="API key required. Set X-SENTINEL-API-KEY header."
        )

    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")

    # Return user email if provided, otherwise fingerprint
    if user_email:
        return f"user:{user_email}"

    # Fallback to fingerprint (first 8 chars of SHA256 hash)
    return f"api_key:{hashlib.sha256(api_key.encode()).hexdigest()[:8]}"


def _log_action(
    engine: str,
    action: str,
    key_fingerprint: str,
    success: bool,
    reason: Optional[str] = None,
):
    """Log toggle action to centralized audit log."""
    try:
        from brain.core.audit import get_audit_log, AuditEventType, AuditLevel

        audit = get_audit_log()

        # Determine level based on action
        if action == "disable":
            level = AuditLevel.WARNING
        else:
            level = AuditLevel.INFO

        event_type = AuditEventType.CONFIG_CHANGE

        audit.log(
            event_type=event_type,
            actor=key_fingerprint,  # Already prefixed with user: or api_key:
            resource=f"engine:{engine}",
            action=action,
            details={
                "engine": engine,
                "success": success,
                "reason": reason,
            },
            outcome="success" if success else "failure",
            level=level,
        )
    except Exception as e:
        # Fallback: just log to console
        import logging

        logging.warning(f"Audit log failed: {e}")


# ============================================================
# STATIC ROUTES (must be defined before dynamic /{engine_name})
# ============================================================


@router.get("/audit-log")
async def get_audit_log(
    limit: int = 50, x_sentinel_api_key: Optional[str] = Header(None)
):
    """
    Get audit log of engine toggle operations.

    Requires X-SENTINEL-API-KEY header.
    """
    _validate_api_key(x_sentinel_api_key)

    return {"entries": _audit_log[-limit:], "total": len(_audit_log)}


@router.get("/blocklist")
async def get_blocklist():
    """
    Get list of critical engines that cannot be disabled.

    Public endpoint - no auth required.
    """
    return {
        "critical_engines": list(CRITICAL_ENGINES),
        "message": "These engines cannot be disabled for security reasons.",
    }


# ============================================================
# DYNAMIC ROUTES (/{engine_name}/...)
# ============================================================


@router.post("/{engine_name}/enable", response_model=ToggleResponse)
async def enable_engine(
    engine_name: str,
    x_sentinel_api_key: Optional[str] = Header(None),
    x_sentinel_user: Optional[str] = Header(None),
):
    """
    Enable a detection engine.

    Requires X-SENTINEL-API-KEY header.
    X-SENTINEL-USER header is used for audit logging.
    """
    actor = _validate_api_key(x_sentinel_api_key, x_sentinel_user)

    try:
        from brain.engines.registry import get_registry

        registry = get_registry()

        success = registry.enable_engine(engine_name)

        _log_action(engine_name, "enable", actor, success)

        return ToggleResponse(
            engine=engine_name, enabled=True, message=f"Engine {engine_name} enabled"
        )

    except Exception as e:
        _log_action(engine_name, "enable", actor, False, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{engine_name}/disable", response_model=ToggleResponse)
async def disable_engine(
    engine_name: str,
    x_sentinel_api_key: Optional[str] = Header(None),
    x_sentinel_user: Optional[str] = Header(None),
):
    """
    Disable a detection engine.

    Requires X-SENTINEL-API-KEY header.
    Critical engines (pii, injection, prompt_guard) cannot be disabled.
    """
    actor = _validate_api_key(x_sentinel_api_key, x_sentinel_user)

    # Check blocklist
    if engine_name in CRITICAL_ENGINES:
        _log_action(
            engine_name,
            "disable",
            actor,
            False,
            "Critical engine - cannot be disabled",
        )
        raise HTTPException(
            status_code=403,
            detail=f"Engine '{engine_name}' is critical and cannot be disabled.",
        )

    try:
        from brain.engines.registry import get_registry

        registry = get_registry()

        success = registry.disable_engine(engine_name)

        _log_action(engine_name, "disable", actor, success)

        return ToggleResponse(
            engine=engine_name, enabled=False, message=f"Engine {engine_name} disabled"
        )

    except Exception as e:
        _log_action(engine_name, "disable", actor, False, str(e))
        raise HTTPException(status_code=500, detail=str(e))
