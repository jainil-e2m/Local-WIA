"""Portfolio read model: the built snapshot the production frontend loads (replaces the local JSON file).

Revision ID: c08a20261106
Revises: c07a20261104
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "c08a20261106"
down_revision = "c07a20261104"
branch_labels = depends_on = None


def upgrade():
    op.create_table("read_model_snapshots",
        sa.Column("name", sa.String(50), primary_key=True),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", pg.JSONB(), nullable=False))


def downgrade():
    op.drop_table("read_model_snapshots")
