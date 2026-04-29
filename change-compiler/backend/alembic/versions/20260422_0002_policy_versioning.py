"""policy versioning

Revision ID: 20260422_0002
Revises: 20260414_0001
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260422_0002"
down_revision = "20260414_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("policies", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column(
        "policies",
        sa.Column("supersedes_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.alter_column("policies", "version", server_default=None)


def downgrade() -> None:
    op.drop_column("policies", "supersedes_policy_id")
    op.drop_column("policies", "version")

