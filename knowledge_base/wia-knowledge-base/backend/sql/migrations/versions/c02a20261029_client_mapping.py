"""S2 client mapping: revisions for admin commands, archive dates, explicit "not applicable" per source.

Revision ID: c02a20261029
Revises: b05a20261028
"""
from alembic import op
import sqlalchemy as sa

revision = "c02a20261029"
down_revision = "b05a20261028"
branch_labels = depends_on = None


def upgrade():
    for table in ("source_scopes", "contacts"):
        op.add_column(table, sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("businesses", sa.Column("status_changed_at", sa.DateTime(timezone=True)))
    op.create_table("client_source_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(300), nullable=False),
        sa.Column("decided_by", sa.String(200), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('not_applicable')", name=op.f("ck_client_source_decisions_state")),
        sa.UniqueConstraint("business_id", "provider"))
    op.create_index("ix_client_source_decisions_business_id", "client_source_decisions", ["business_id"])


def downgrade():
    op.drop_table("client_source_decisions")
    op.drop_column("businesses", "status_changed_at")
    for table in ("source_scopes", "contacts"):
        op.drop_column(table, "revision")
