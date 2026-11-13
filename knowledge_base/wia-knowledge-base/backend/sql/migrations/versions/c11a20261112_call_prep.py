"""Call preparation: corrections to a call, brief versions, editable call-type skills, and ad-platform figures.

Revision ID: c11a20261112
Revises: c10a20261112
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "c11a20261112"
down_revision = "c10a20261112"
branch_labels = depends_on = None


def upgrade():
    op.create_table("call_overrides",
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("source_records.id", name="fk_call_overrides_record_id_source_records"),
                  primary_key=True),
        sa.Column("call_type", sa.String(40)),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", name="fk_call_overrides_business_id_businesses")),
        sa.Column("host", sa.String(200)),
        sa.Column("excluded", sa.Boolean()),
        sa.Column("note", sa.Text()),
        sa.Column("set_by", sa.String(200), nullable=False),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("call_briefs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("source_records.id", name="fk_call_briefs_record_id_source_records"),
                  nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("skill_key", sa.String(40), nullable=False),
        sa.Column("skill_ref", sa.String(80), nullable=False),
        sa.Column("instructions", sa.Text()),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("inputs", pg.JSONB(), nullable=False),
        sa.Column("facts", pg.JSONB(), nullable=False),
        sa.Column("output", pg.JSONB()),
        sa.Column("refs", pg.JSONB(), nullable=False),
        sa.Column("checks", pg.JSONB(), nullable=False),
        sa.Column("ai_run_id", sa.Uuid(), sa.ForeignKey("ai_runs.id", name="fk_call_briefs_ai_run_id_ai_runs")),
        sa.Column("trigger", sa.String(20), nullable=False),
        sa.Column("built_by", sa.String(200), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("record_id", "version", name="uq_call_briefs_record_id"),
        sa.CheckConstraint("outcome IN ('ready','rejected')", name="outcome"))
    op.create_index("uq_call_briefs_current", "call_briefs", ["record_id"], unique=True,
                    postgresql_where=sa.text("is_current"))
    op.create_table("call_skills",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("seed_sha", sa.String(64)),
        sa.Column("edited_by", sa.String(200), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("key", "version", name="uq_call_skills_key"),
        sa.CheckConstraint("source IN ('seed','edit')", name="source"))
    op.create_index("uq_call_skills_current", "call_skills", ["key"], unique=True, postgresql_where=sa.text("is_current"))
    op.create_table("ad_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("account_id", sa.String(40), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("currency", sa.String(3)),
        sa.Column("status", sa.String(40)),
        sa.Column("via", sa.String(120)),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", name="fk_ad_accounts_business_id_businesses")),
        sa.Column("mapped_by", sa.String(200)),
        sa.Column("mapped_at", sa.DateTime(timezone=True)),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_pulled_at", sa.DateTime(timezone=True)),
        sa.Column("pulled_from", sa.Date()),
        sa.Column("last_error", sa.Text()),
        sa.UniqueConstraint("provider", "account_id", name="uq_ad_accounts_provider"),
        sa.CheckConstraint("provider IN ('google_ads','meta')", name="provider"))
    op.create_index("ix_ad_accounts_business_id", "ad_accounts", ["business_id"])
    op.create_table("ad_daily",
        sa.Column("ad_account_id", sa.Uuid(), sa.ForeignKey("ad_accounts.id", name="fk_ad_daily_ad_account_id_ad_accounts",
                                                           ondelete="CASCADE"), primary_key=True),
        sa.Column("campaign_id", sa.String(40), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("campaign_name", sa.String(300), nullable=False),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("spend", sa.Numeric(12, 2), nullable=False),
        sa.Column("impressions", sa.BigInteger(), nullable=False),
        sa.Column("clicks", sa.BigInteger(), nullable=False),
        sa.Column("conversions", sa.Numeric(12, 2), nullable=False),
        sa.Column("extra", pg.JSONB(), nullable=False),
        sa.Column("pulled_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ad_daily_day", "ad_daily", ["day"])


def downgrade():
    op.drop_table("ad_daily")
    op.drop_table("ad_accounts")
    op.drop_table("call_skills")
    op.drop_table("call_briefs")
    op.drop_table("call_overrides")
