"""Outbound send log: every Slack message or ClickUp edit is drafted, approved by a person, then sent.

Revision ID: c06a20261102
Revises: c05a20261102
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "c06a20261102"
down_revision = "c05a20261102"
branch_labels = depends_on = None


def upgrade():
    op.create_table("outbound_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("target", sa.String(100), nullable=False),
        sa.Column("payload", pg.JSONB(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("preview", pg.JSONB(), nullable=False),
        sa.Column("as_person_id", sa.Uuid(), sa.ForeignKey("people.id")),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("drafted_by", sa.String(200), nullable=False),
        sa.Column("drafted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.String(200)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("approved_hash", sa.String(64)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("result", pg.JSONB(), nullable=False),
        sa.Column("error", sa.String(500)),
        sa.CheckConstraint("kind IN ('slack_post','slack_dm','clickup_task_update')", name=op.f("ck_outbound_requests_kind")),
        sa.CheckConstraint("state IN ('draft','approved','sent','failed','refused','rejected','expired')",
                           name=op.f("ck_outbound_requests_state")))
    op.create_index("ix_outbound_requests_state", "outbound_requests", ["state"])


def downgrade():
    op.drop_table("outbound_requests")
