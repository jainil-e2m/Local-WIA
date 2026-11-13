"""Shared edits: Action Hub changes and client details saved for everyone, not in one browser.

Revision ID: c12a20261113
Revises: c11a20261112
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "c12a20261113"
down_revision = "c11a20261112"
branch_labels = depends_on = None


def upgrade():
    op.create_table("shared_edits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("data", pg.JSONB(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kind", "key", name="uq_shared_edits_kind_key"),
        sa.CheckConstraint("kind IN ('action','client')", name="kind"))


def downgrade():
    op.drop_table("shared_edits")
