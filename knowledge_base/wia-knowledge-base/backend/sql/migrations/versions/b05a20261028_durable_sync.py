"""B-05 admission, stream checkpoints, memberships and lifecycle outbox.

Revision ID: b05a20261028
Revises: 18e642a0961c
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "b05a20261028"
down_revision = "18e642a0961c"
branch_labels = depends_on = None


def _id():
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _timestamps():
    return [sa.Column(n, sa.DateTime(timezone=True), nullable=False) for n in ("created_at", "updated_at")]


def upgrade():
    for name in ("lease_token", "lease_work_id"):
        op.add_column("connector_accounts", sa.Column(name, sa.Uuid()))
    for name in ("lease_until", "next_request_at", "heavy_request_at"):
        op.add_column("connector_accounts", sa.Column(name, sa.DateTime(timezone=True)))
    op.add_column("source_records", sa.Column("admitted_at", sa.DateTime(timezone=True)))
    op.add_column("source_records", sa.Column("revision", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("source_records", sa.Column("provider_state", pg.JSONB(), nullable=False, server_default="{}"))
    op.add_column("source_records", sa.Column("parent_external_id", sa.String(300)))
    op.add_column("source_records", sa.Column("last_observed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_source_records_parent_external_id", "source_records", ["parent_external_id"])
    op.execute("""UPDATE source_records r SET admitted_at = first_seen_at
        WHERE qualification = 'content' OR EXISTS
        (SELECT 1 FROM record_associations a WHERE a.record_id=r.id AND a.status='associated')""")
    op.execute("""UPDATE source_records r SET parent_external_id = v.attributes->>'calendar_id' || ':' ||
        (v.attributes->>'recurring_event_id') FROM source_versions v
        WHERE v.id=r.current_version_id AND v.attributes->>'recurring_event_id' IS NOT NULL""")
    op.drop_constraint(op.f("ck_record_associations_basis"), "record_associations", type_="check")
    op.create_check_constraint("basis", "record_associations",
                               "basis IN ('scope_mapping','verified_contact','series_mapping','manual_review')")
    op.create_table("sync_streams", _id(), *_timestamps(),
        sa.Column("connector_account_id", sa.Uuid(), sa.ForeignKey("connector_accounts.id"), nullable=False),
        sa.Column("stream_key", sa.String(320), nullable=False),
        sa.Column("scope_id", sa.Uuid(), sa.ForeignKey("source_scopes.id"), nullable=False),
        sa.Column("cursor", pg.JSONB(), nullable=False), sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        *[sa.Column(n, sa.DateTime(timezone=True), nullable=False) for n in ("next_sync_at", "next_reconcile_at")],
        *[sa.Column(n, sa.DateTime(timezone=True)) for n in ("last_incremental_at", "last_reconciled_at")],
        sa.UniqueConstraint("connector_account_id", "stream_key"))
    op.create_index("ix_sync_streams_connector_account_id", "sync_streams", ["connector_account_id"])
    op.add_column("sync_runs", sa.Column("stream_id", sa.Uuid(), sa.ForeignKey("sync_streams.id")))
    op.add_column("sync_runs", sa.Column("generation", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("sync_runs", sa.Column("checkpoint", pg.JSONB(), nullable=False, server_default="{}"))
    op.add_column("sync_runs", sa.Column("target_external_id", sa.String(300)))
    op.drop_constraint(op.f("ck_sync_runs_mode"), "sync_runs", type_="check")
    op.create_check_constraint("mode", "sync_runs", "mode IN ('discovery','backfill','incremental','reconcile','refresh')")
    op.drop_constraint(op.f("ck_sync_runs_state"), "sync_runs", type_="check")
    op.create_check_constraint("state", "sync_runs", "state IN ('queued','running','succeeded','partial','failed')")
    op.create_index("ix_sync_runs_stream_id", "sync_runs", ["stream_id"])
    op.create_index("uq_sync_run_active_stream", "sync_runs", ["stream_id"], unique=True,
                    postgresql_where=sa.text("state = 'running'"))
    op.create_table("scope_memberships", _id(),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("source_records.id"), nullable=False),
        sa.Column("scope_id", sa.Uuid(), sa.ForeignKey("source_scopes.id"), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("seen_run_id", sa.Uuid(), sa.ForeignKey("sync_runs.id")),
        sa.UniqueConstraint("record_id", "scope_id"))
    for name in ("record_id", "scope_id"):
        op.create_index("ix_scope_memberships_" + name, "scope_memberships", [name])
    op.execute("""INSERT INTO scope_memberships (id,record_id,scope_id,state)
        SELECT gen_random_uuid(),id,scope_id,'active' FROM source_records WHERE scope_id IS NOT NULL""")
    op.create_table("drive_nodes", _id(),
        sa.Column("connector_account_id", sa.Uuid(), sa.ForeignKey("connector_accounts.id"), nullable=False),
        sa.Column("external_id", sa.String(300), nullable=False),
        sa.Column("parents", pg.JSONB(), nullable=False), sa.Column("is_folder", sa.Boolean(), nullable=False),
        sa.Column("name", sa.String(500), nullable=False), sa.UniqueConstraint("connector_account_id", "external_id"))
    op.create_table("association_reviews", _id(), *_timestamps(),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("source_records.id"), nullable=False),
        sa.Column("version_id", sa.Uuid(), sa.ForeignKey("source_versions.id"), nullable=False),
        sa.Column("existing_business_ids", pg.JSONB(), nullable=False),
        sa.Column("proposed_business_ids", pg.JSONB(), nullable=False),
        sa.Column("reason", sa.String(60), nullable=False), sa.Column("state", sa.String(20), nullable=False))
    op.create_index("ix_association_reviews_record_id", "association_reviews", ["record_id"])
    op.create_index("uq_association_review_pending", "association_reviews", ["record_id"], unique=True,
                    postgresql_where=sa.text("state = 'pending'"))
    op.create_table("webhook_receipts", _id(),
        sa.Column("connector_account_id", sa.Uuid(), sa.ForeignKey("connector_accounts.id"), nullable=False),
        sa.Column("delivery_id", sa.String(200), nullable=False), sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("sync_runs.id")),
        sa.UniqueConstraint("connector_account_id", "delivery_id"))
    op.create_table("record_changes", _id(),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("source_records.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Uuid(), sa.ForeignKey("source_versions.id")),
        sa.Column("availability", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("record_id", "revision"))
    op.create_index("ix_record_changes_record_id", "record_changes", ["record_id"])


def downgrade():
    # Evidence, admission and lifecycle state must not be silently discarded.
    raise RuntimeError("B-05 is forward-only; restore a verified backup to roll back")
