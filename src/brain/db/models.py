"""
SENTINEL Brain - Database Models

SQLAlchemy models for persistence layer.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class AuditLog(Base):
    """Audit log for all security events."""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(String(50), nullable=False)  # analyze, block, alert
    source = Column(String(100))  # API, Shield, etc.
    user_id = Column(String(100))
    session_id = Column(String(100))
    ip_address = Column(String(45))
    
    # Request details
    request_id = Column(String(50))
    text_hash = Column(String(64))  # SHA256 of input
    text_length = Column(Integer)
    
    # Result
    verdict = Column(String(20))  # ALLOW, WARN, BLOCK
    risk_score = Column(Float)
    threats = Column(JSON)  # List of detected threats
    
    # Timing
    latency_ms = Column(Float)
    
    # Metadata
    metadata = Column(JSON)
    
    __table_args__ = (
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_verdict", "verdict"),
        Index("ix_audit_logs_session_id", "session_id"),
    )


class DetectionEvent(Base):
    """Individual detection events from engines."""
    
    __tablename__ = "detection_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_log_id = Column(UUID(as_uuid=True), ForeignKey("audit_logs.id"))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Engine info
    engine_name = Column(String(50), nullable=False)
    engine_version = Column(String(20))
    
    # Detection details
    threat_name = Column(String(100), nullable=False)
    threat_category = Column(String(50))
    confidence = Column(Float)
    severity = Column(String(20))  # low, medium, high, critical
    
    # Context
    matched_pattern = Column(Text)
    context_snippet = Column(Text)
    
    # Relationships
    audit_log = relationship("AuditLog", backref="detections")
    
    __table_args__ = (
        Index("ix_detection_events_engine", "engine_name"),
        Index("ix_detection_events_threat", "threat_name"),
        Index("ix_detection_events_severity", "severity"),
    )


class APIKey(Base):
    """API keys for authentication."""
    
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(64), unique=True, nullable=False)  # SHA256
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Permissions
    scopes = Column(JSON)  # List of allowed scopes
    rate_limit = Column(Integer, default=1000)  # Requests per minute
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)
    
    # Owner
    owner_id = Column(String(100))
    owner_email = Column(String(255))
    
    __table_args__ = (
        Index("ix_api_keys_key_hash", "key_hash"),
        Index("ix_api_keys_owner", "owner_id"),
    )


class EngineConfig(Base):
    """Engine configuration storage."""
    
    __tablename__ = "engine_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_name = Column(String(50), unique=True, nullable=False)
    version = Column(String(20))
    
    # Configuration
    config = Column(JSON)
    enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
