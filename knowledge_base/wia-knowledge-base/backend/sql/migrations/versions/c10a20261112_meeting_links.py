"""Meeting links: a recording link a person added to a past meeting that has none.

Revision ID: c10a20261112
Revises: c09a20261106
"""
from alembic import op
import sqlalchemy as sa

revision = "c10a20261112"
down_revision = "c09a20261106"
branch_labels = depends_on = None


def upgrade():
    op.create_table("meeting_links",
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("source_records.id", name="fk_meeting_links_record_id_source_records"),
                  primary_key=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("added_by", sa.String(200), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table("meeting_links")
