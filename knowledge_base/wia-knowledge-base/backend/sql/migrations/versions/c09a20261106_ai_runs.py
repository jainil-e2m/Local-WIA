"""AI layer (built, off): the run log with cost and validated output, and the action candidates it proposes.

Revision ID: c09a20261106
Revises: c08a20261106
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "c09a20261106"
down_revision = "c08a20261106"
branch_labels = depends_on = None


def upgrade():
    op.create_table("ai_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("skill", sa.String(40), nullable=False),
        sa.Column("skill_version", sa.String(20), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("subject_kind", sa.String(20), nullable=False),
        sa.Column("subject_id", sa.String(300), nullable=False),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", name="fk_ai_runs_business_id_businesses")),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("error_class", sa.String(60)),
        sa.Column("refs", pg.JSONB(), nullable=False),
        sa.Column("output", pg.JSONB()),
        sa.Column("checks", pg.JSONB(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("subject_kind IN ('meeting','call','email_batch','client')", name="subject_kind"),
        sa.CheckConstraint("state IN ('succeeded','failed','refused')", name="state"))
    op.create_index("uq_ai_runs_succeeded_input", "ai_runs", ["skill", "input_hash"], unique=True,
                    postgresql_where=sa.text("state = 'succeeded'"))
    op.create_index("uq_ai_runs_current", "ai_runs", ["skill", "subject_id"], unique=True,
                    postgresql_where=sa.text("is_current"))
    op.create_index("ix_ai_runs_created", "ai_runs", ["created_at"])
    op.create_table("action_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("ai_runs.id", name="fk_action_candidates_run_id_ai_runs"), nullable=False),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", name="fk_action_candidates_business_id_businesses")),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("owner_side", sa.String(10)),
        sa.Column("owner_name", sa.String(200)),
        sa.Column("due_date", sa.Date()),
        sa.Column("due_phrase", sa.String(200)),
        sa.Column("signal", sa.String(20)),
        sa.Column("target_action_ref", sa.String(120)),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("source_record_id", sa.Uuid(),
                  sa.ForeignKey("source_records.id", name="fk_action_candidates_source_record_id_source_records")),
        sa.Column("unit_id", sa.Uuid(), sa.ForeignKey("content_units.id", name="fk_action_candidates_unit_id_content_units")),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("decided_by", sa.String(200)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('new','update')", name="kind"),
        sa.CheckConstraint("owner_side IS NULL OR owner_side IN ('WIA','Client')", name="owner_side"),
        sa.CheckConstraint("signal IS NULL OR signal IN ('done','progressed','blocked','date_changed')",
                           name="signal"),
        sa.CheckConstraint("status IN ('proposed','approved','rejected','superseded')", name="status"))
    op.create_index("ix_action_candidates_run_id", "action_candidates", ["run_id"])
    op.create_index("ix_action_candidates_business_id", "action_candidates", ["business_id"])


def downgrade():
    op.drop_table("action_candidates")
    op.drop_table("ai_runs")
