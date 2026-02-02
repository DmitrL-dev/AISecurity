"""
SENTINEL Audit API

Endpoints for viewing and managing audit logs.
"""

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import hashlib

router = APIRouter(prefix="/audit", tags=["audit"])

# API key for protected endpoints
API_KEY = os.getenv("SENTINEL_API_KEY", "sentinel-dev-key-change-me")


class AuditConfigResponse(BaseModel):
    """Audit configuration."""

    level: str
    max_events: int
    current_count: int


class AuditLogResponse(BaseModel):
    """Audit log entries response."""

    entries: List[Dict[str, Any]]
    total: int
    filtered: int


def _validate_api_key(api_key: Optional[str]) -> str:
    """Validate API key and return fingerprint."""
    if not api_key:
        raise HTTPException(
            status_code=401, detail="API key required. Set X-SENTINEL-API-KEY header."
        )

    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")

    return hashlib.sha256(api_key.encode()).hexdigest()[:8]


@router.get("/logs", response_model=AuditLogResponse)
async def get_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(
        None, description="Min level: DEBUG/INFO/WARNING/CRITICAL"
    ),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    x_sentinel_api_key: Optional[str] = Header(None),
):
    """
    Get audit log entries with optional filtering.

    Requires X-SENTINEL-API-KEY header.
    """
    _validate_api_key(x_sentinel_api_key)

    try:
        from core.audit import get_audit_log, LEVEL_MAP

        audit = get_audit_log()
        entries = audit.get_entries(event_type=event_type, limit=limit)

        # Filter by level if specified
        if level:
            min_level = LEVEL_MAP.get(level.upper())
            if min_level:
                entries = [
                    e
                    for e in entries
                    if LEVEL_MAP.get(e.get("level", "INFO"), 0) >= min_level
                ]

        return AuditLogResponse(
            entries=entries, total=len(audit._entries), filtered=len(entries)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", response_model=AuditConfigResponse)
async def get_audit_config(
    x_sentinel_api_key: Optional[str] = Header(None),
):
    """
    Get current audit configuration.

    Requires X-SENTINEL-API-KEY header.
    """
    _validate_api_key(x_sentinel_api_key)

    try:
        from core.audit import get_audit_log

        audit = get_audit_log()

        return AuditConfigResponse(
            level=audit.level.name,
            max_events=(
                audit._entries.maxlen if hasattr(audit._entries, "maxlen") else 1000
            ),
            current_count=len(audit._entries),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def set_audit_config(
    level: Optional[str] = Query(
        None, description="New level: DEBUG/INFO/WARNING/CRITICAL"
    ),
    x_sentinel_api_key: Optional[str] = Header(None),
):
    """
    Update audit configuration.

    Requires X-SENTINEL-API-KEY header.
    """
    _validate_api_key(x_sentinel_api_key)

    try:
        from core.audit import get_audit_log, AuditEventType

        audit = get_audit_log()

        if level:
            if not audit.set_level_by_name(level):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid level: {level}. Use DEBUG/INFO/WARNING/CRITICAL",
                )

            # Log config change
            audit.log_warning(
                AuditEventType.CONFIG_CHANGE,
                "admin",
                "audit",
                "set_level",
                {"new_level": level},
            )

        return {"success": True, "level": audit.level.name}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify")
async def verify_audit_integrity(
    x_sentinel_api_key: Optional[str] = Header(None),
):
    """
    Verify audit log integrity (cryptographic chain + HMAC signatures).

    Requires X-SENTINEL-API-KEY header.
    Returns integrity status and tamper detection flag.
    """
    _validate_api_key(x_sentinel_api_key)

    try:
        from core.audit import get_audit_log

        audit = get_audit_log()
        is_valid = audit.verify_integrity()

        return {
            "valid": is_valid,
            "tamper_detected": audit.is_tampered,
            "entries_checked": len(audit._entries),
            "signatures_enabled": True,
            "message": (
                "Integrity verified - chain and signatures valid"
                if is_valid
                else "INTEGRITY COMPROMISED - TAMPERING DETECTED!"
            ),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SECURE EXPORT SYSTEM
# ============================================================

import secrets
import json
import time
from datetime import datetime

# In-memory token store (Redis in production)
_export_tokens: Dict[str, Dict[str, Any]] = {}
EXPORT_TOKEN_TTL = 300  # 5 minutes


class ExportRequest(BaseModel):
    """Export request parameters."""

    format: str = "json"  # json or csv
    limit: int = 1000
    level: Optional[str] = None


class ExportResponse(BaseModel):
    """Export response with download URL."""

    download_url: str
    token: str
    expires_at: str
    format: str
    entry_count: int


@router.post("/export", response_model=ExportResponse)
async def create_audit_export(
    request: ExportRequest,
    x_sentinel_api_key: Optional[str] = Header(None),
):
    """
    Create a secure, one-time audit log export.

    Returns a signed download URL valid for 5 minutes.
    Export event is logged to audit trail.

    Requires X-SENTINEL-API-KEY header.
    """
    key_fp = _validate_api_key(x_sentinel_api_key)

    try:
        from core.audit import get_audit_log, AuditEventType, AuditLevel

        audit = get_audit_log()

        # Get entries
        entries = audit.get_entries(limit=request.limit)

        # Filter by level if specified
        if request.level:
            from core.audit import LEVEL_MAP

            min_level = LEVEL_MAP.get(request.level.upper(), 0)
            entries = [
                e
                for e in entries
                if LEVEL_MAP.get(e.get("level", "INFO"), 0) >= min_level
            ]

        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + EXPORT_TOKEN_TTL

        # Store export data with token
        _export_tokens[token] = {
            "entries": entries,
            "format": request.format,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at,
            "used": False,
            "creator_fp": key_fp,
        }

        # Audit log the export request
        audit.log(
            event_type=AuditEventType.ADMIN_ACTION,
            actor=f"api_key:{key_fp}",
            resource="audit_log",
            action="export_created",
            details={
                "format": request.format,
                "entry_count": len(entries),
                "token_preview": token[:8] + "...",
            },
            outcome="success",
            level=AuditLevel.WARNING,
        )

        expires_iso = datetime.fromtimestamp(expires_at).isoformat()

        return ExportResponse(
            download_url=f"/v1/audit/download/{token}",
            token=token,
            expires_at=expires_iso,
            format=request.format,
            entry_count=len(entries),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from fastapi.responses import StreamingResponse
import io


@router.get("/download/{token}")
async def download_audit_export(token: str):
    """
    Download audit export (one-time use).

    Token is invalidated after download.
    No API key required - token IS the auth.
    """
    # Check token exists
    if token not in _export_tokens:
        raise HTTPException(status_code=404, detail="Export not found or expired")

    export_data = _export_tokens[token]

    # Check expiry
    if time.time() > export_data["expires_at"]:
        del _export_tokens[token]
        raise HTTPException(status_code=410, detail="Export expired")

    # Check already used
    if export_data["used"]:
        raise HTTPException(
            status_code=410, detail="Export already downloaded (one-time use)"
        )

    # Mark as used
    export_data["used"] = True

    entries = export_data["entries"]
    fmt = export_data["format"]

    # Log the download
    try:
        from core.audit import get_audit_log, AuditEventType, AuditLevel

        audit = get_audit_log()
        audit.log(
            event_type=AuditEventType.ADMIN_ACTION,
            actor=f"token:{token[:8]}...",
            resource="audit_log",
            action="export_downloaded",
            details={"entry_count": len(entries), "format": fmt},
            outcome="success",
            level=AuditLevel.INFO,
        )
    except Exception:
        pass

    # Generate file content
    if fmt == "csv":
        content = _generate_csv(entries)
        media_type = "text/csv"
        filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    else:
        content = json.dumps(entries, indent=2, default=str)
        media_type = "application/json"
        filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Clean up token after use
    del _export_tokens[token]

    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _generate_csv(entries: List[Dict]) -> str:
    """Generate CSV content from audit entries."""
    if not entries:
        return "timestamp,level,event_type,actor,resource,action,outcome\n"

    lines = ["timestamp,level,event_type,actor,resource,action,outcome"]
    for e in entries:
        line = ",".join(
            [
                str(e.get("timestamp", "")),
                str(e.get("level", "")),
                str(e.get("event_type", "")),
                str(e.get("actor", "")),
                str(e.get("resource", "")),
                str(e.get("action", "")),
                str(e.get("outcome", "")),
            ]
        )
        lines.append(line)
    return "\n".join(lines)
