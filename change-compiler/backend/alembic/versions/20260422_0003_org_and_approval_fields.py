"""org and approval fields

Revision ID: 20260422_0003
Revises: 20260422_0002
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260422_0003"
down_revision = "20260422_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("change_requests", sa.Column("org_id", sa.String(length=128), nullable=False, server_default="default-org"))
    op.add_column(
        "change_requests",
        sa.Column("requires_manual_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("change_requests", sa.Column("approved_by", sa.String(length=128), nullable=True))
    op.add_column("change_requests", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("change_requests", "org_id", server_default=None)
    op.alter_column("change_requests", "requires_manual_approval", server_default=None)

    op.add_column("policies", sa.Column("org_id", sa.String(length=128), nullable=False, server_default="default-org"))
    op.alter_column("policies", "org_id", server_default=None)

    op.add_column("audit_logs", sa.Column("org_id", sa.String(length=128), nullable=False, server_default="default-org"))
    op.alter_column("audit_logs", "org_id", server_default=None)


def downgrade() -> None:
    op.drop_column("audit_logs", "org_id")
    op.drop_column("policies", "org_id")
    op.drop_column("change_requests", "approved_at")
    op.drop_column("change_requests", "approved_by")
    op.drop_column("change_requests", "requires_manual_approval")
    op.drop_column("change_requests", "org_id")

