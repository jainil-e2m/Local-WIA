"""Per-person ClickUp OAuth connections (encrypted tokens) for write-back under each person's name.

Revision ID: c05a20261102
Revises: c04a20261030
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "c05a20261102"
down_revision = "c04a20261030"
branch_labels = depends_on = None


def upgrade():
    op.create_table("clickup_connections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("person_id", sa.Uuid(), sa.ForeignKey("people.id"), nullable=False),
        sa.Column("clickup_user_id", sa.String(40), nullable=False),
        sa.Column("clickup_username", sa.String(200)),
        sa.Column("workspace_ids", pg.JSONB(), nullable=False),
        sa.Column("token_encrypted", sa.Text(), nullable=False),
        sa.Column("connected_by", sa.String(200), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_reason", sa.String(200)))
    op.create_index("ix_clickup_connections_person_id", "clickup_connections", ["person_id"])
    op.create_index("uq_clickup_connections_active_person", "clickup_connections", ["person_id"], unique=True,
                    postgresql_where=sa.text("revoked_at IS NULL"))


def downgrade():
    op.drop_table("clickup_connections")
