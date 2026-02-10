"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-01-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(100)),
        sa.Column("user_id", sa.String(100)),
        sa.Column("session_id", sa.String(100)),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("request_id", sa.String(50)),
        sa.Column("text_hash", sa.String(64)),
        sa.Column("text_length", sa.Integer()),
        sa.Column("verdict", sa.String(20)),
        sa.Column("risk_score", sa.Float()),
        sa.Column("threats", postgresql.JSON()),
        sa.Column("latency_ms", sa.Float()),
        sa.Column("metadata", postgresql.JSON()),
    )
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_verdict", "audit_logs", ["verdict"])
    op.create_index("ix_audit_logs_session_id", "audit_logs", ["session_id"])

    # Create detection_events table
    op.create_table(
        "detection_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("audit_log_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audit_logs.id")),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("engine_name", sa.String(50), nullable=False),
        sa.Column("engine_version", sa.String(20)),
        sa.Column("threat_name", sa.String(100), nullable=False),
        sa.Column("threat_category", sa.String(50)),
        sa.Column("confidence", sa.Float()),
        sa.Column("severity", sa.String(20)),
        sa.Column("matched_pattern", sa.Text()),
        sa.Column("context_snippet", sa.Text()),
    )
    op.create_index("ix_detection_events_engine", "detection_events", ["engine_name"])
    op.create_index("ix_detection_events_threat", "detection_events", ["threat_name"])
    op.create_index("ix_detection_events_severity", "detection_events", ["severity"])

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("scopes", postgresql.JSON()),
        sa.Column("rate_limit", sa.Integer(), default=1000),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("expires_at", sa.DateTime()),
        sa.Column("last_used_at", sa.DateTime()),
        sa.Column("owner_id", sa.String(100)),
        sa.Column("owner_email", sa.String(255)),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])
    op.create_index("ix_api_keys_owner", "api_keys", ["owner_id"])

    # Create engine_configs table
    op.create_table(
        "engine_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("engine_name", sa.String(50), unique=True, nullable=False),
        sa.Column("version", sa.String(20)),
        sa.Column("config", postgresql.JSON()),
        sa.Column("enabled", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table("engine_configs")
    op.drop_table("api_keys")
    op.drop_table("detection_events")
    op.drop_table("audit_logs")
