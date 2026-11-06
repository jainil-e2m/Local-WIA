"""Admin sender rules: team, partner and blocked addresses or domains that never become client contacts.

Revision ID: c03a20261030
Revises: c02a20261029
"""
from alembic import op
import sqlalchemy as sa

revision = "c03a20261030"
down_revision = "c02a20261029"
branch_labels = depends_on = None


def upgrade():
    op.create_table("sender_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("domain", sa.String(253)),
        sa.Column("reason", sa.String(300), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('team','partner','blocked')", name=op.f("ck_sender_rules_kind")),
        sa.CheckConstraint("(email IS NULL) <> (domain IS NULL)", name=op.f("ck_sender_rules_email_xor_domain")),
        sa.UniqueConstraint("email"), sa.UniqueConstraint("domain"))


def downgrade():
    op.drop_table("sender_rules")
