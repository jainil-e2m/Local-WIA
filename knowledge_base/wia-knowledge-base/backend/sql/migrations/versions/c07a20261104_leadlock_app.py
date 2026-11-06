"""LeadLock Marketplace app: the agency grant, one row per installed sub-account, and the webhook event log.

Revision ID: c07a20261104
Revises: c06a20261102
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "c07a20261104"
down_revision = "c06a20261102"
branch_labels = depends_on = None


def upgrade():
    op.create_table("leadlock_installations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.String(64), nullable=False),
        sa.Column("app_id", sa.String(64)),
        sa.Column("installed_by_user_id", sa.String(64)),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scopes", pg.JSONB(), nullable=False),
        sa.Column("is_bulk_installation", sa.Boolean()),
        sa.Column("install_to_future_locations", sa.Boolean()),
        sa.Column("approve_all_locations", sa.Boolean()),
        sa.Column("approved_location_ids", pg.JSONB(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True)),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_reason", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("uq_leadlock_installations_active_company", "leadlock_installations", ["company_id"],
                    unique=True, postgresql_where=sa.text("revoked_at IS NULL"))
    op.create_table("leadlock_locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("installation_id", sa.Uuid(), sa.ForeignKey("leadlock_installations.id")),
        sa.Column("location_id", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(300)),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("access_token_encrypted", sa.Text()),
        sa.Column("access_expires_at", sa.DateTime(timezone=True)),
        sa.Column("scopes", pg.JSONB(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True)),
        sa.Column("uninstalled_at", sa.DateTime(timezone=True)),
        sa.Column("last_token_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('pending','active','uninstalled','failed')", name="ck_leadlock_locations_state"))
    op.create_index("ix_leadlock_locations_installation_id", "leadlock_locations", ["installation_id"])
    op.create_table("leadlock_app_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("delivery_key", sa.String(200), nullable=False, unique=True),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("company_id", sa.String(64)),
        sa.Column("location_id", sa.String(64)),
        sa.Column("outcome", sa.String(60), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table("leadlock_app_events")
    op.drop_table("leadlock_locations")
    op.drop_table("leadlock_installations")
