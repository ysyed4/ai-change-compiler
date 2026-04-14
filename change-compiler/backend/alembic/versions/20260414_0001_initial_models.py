"""initial models

Revision ID: 20260414_0001
Revises:
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260414_0001"
down_revision = None
branch_labels = None
depends_on = None


change_status_enum = sa.Enum(
    "received",
    "evaluated",
    "executing",
    "paused",
    "halted",
    "completed",
    "blocked",
    name="changestatus",
)

decision_type_enum = sa.Enum(
    "allow",
    "allow_with_constraints",
    "block",
    name="decisiontype",
)

enforcement_type_enum = sa.Enum(
    "hard_stop",
    "manual_approval",
    "advisory",
    name="enforcementtype",
)


def upgrade() -> None:
    bind = op.get_bind()
    change_status_enum.create(bind, checkfirst=True)
    decision_type_enum.create(bind, checkfirst=True)
    enforcement_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "change_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("change_type", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", change_status_enum, nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("requested_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rollback_available", sa.Boolean(), nullable=False),
        sa.Column("decision", decision_type_enum, nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("explanations", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("condition_expr", sa.Text(), nullable=False),
        sa.Column("enforcement", enforcement_type_enum, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("scope_platform", sa.String(length=64), nullable=False),
        sa.Column("scope_change_type", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("change_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("change_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("telemetry_snapshot", sa.JSON(), nullable=False),
        sa.Column("rule_hits", sa.JSON(), nullable=False),
        sa.Column("policy_hits", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("policies")
    op.drop_table("change_requests")

    bind = op.get_bind()
    enforcement_type_enum.drop(bind, checkfirst=True)
    decision_type_enum.drop(bind, checkfirst=True)
    change_status_enum.drop(bind, checkfirst=True)
