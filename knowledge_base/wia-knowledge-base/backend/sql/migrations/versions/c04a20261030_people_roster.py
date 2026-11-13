"""People, roster addresses, shared inbox history and account teams.

Revision ID: c04a20261030
Revises: c03a20261030
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "c04a20261030"
down_revision = "c03a20261030"
branch_labels = depends_on = None


def upgrade():
    op.create_table("people",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id")),
        sa.Column("functions", pg.JSONB(), nullable=False), sa.Column("status", sa.String(20), nullable=False),
        sa.Column("merged_into_id", sa.Uuid(), sa.ForeignKey("people.id")), sa.Column("notes", sa.String(500)),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('staff','contractor','former','shared_mailbox','service_account','client_contact','partner','prospect','programme_member','unknown')", name=op.f("ck_people_kind")),
        sa.CheckConstraint("status IN ('confirmed','pending')", name=op.f("ck_people_status")),
        sa.CheckConstraint("merged_into_id IS NULL OR merged_into_id <> id", name=op.f("ck_people_not_self_merged")))
    op.create_table("person_addresses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("person_id", sa.Uuid(), sa.ForeignKey("people.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False), sa.Column("value", sa.String(320), nullable=False),
        sa.Column("source", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kind", "value"),
        sa.CheckConstraint("kind IN ('email','slack_user','clickup_user','fathom_email','display_name')", name=op.f("ck_person_addresses_kind")),
        sa.CheckConstraint("source IN ('roster','admin','client_contact')", name=op.f("ck_person_addresses_source")))
    op.create_index("ix_person_addresses_person_id", "person_addresses", ["person_id"])
    op.create_table("mailbox_holders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("mailbox_person_id", sa.Uuid(), sa.ForeignKey("people.id"), nullable=False),
        sa.Column("holder_person_id", sa.Uuid(), sa.ForeignKey("people.id"), nullable=False),
        sa.Column("valid_from", sa.Date()), sa.Column("valid_to", sa.Date()), sa.Column("note", sa.String(500)),
        sa.CheckConstraint("valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to", name=op.f("ck_mailbox_holders_date_order")))
    op.create_index("ix_mailbox_holders_mailbox_person_id", "mailbox_holders", ["mailbox_person_id"])
    # Preserve any pre-table identity links as explicit pending placeholders rather
    # than dropping their IDs or silently failing the new FK on legacy values.
    op.execute("""INSERT INTO people (id,name,kind,functions,status,notes,revision,created_at,updated_at)
        SELECT DISTINCT person_id,'Unresolved legacy person','unknown','[]'::jsonb,'pending',
        'Legacy identity link: roster review required',1,clock_timestamp(),clock_timestamp()
        FROM (SELECT DISTINCT person_id FROM provider_identities WHERE person_id IS NOT NULL) legacy""")
    op.create_foreign_key(op.f("fk_provider_identities_person_id_people"), "provider_identities", "people", ["person_id"], ["id"])
    op.add_column("provider_identities", sa.Column("party", sa.String(20)))
    op.add_column("provider_identities", sa.Column("party_business_id", sa.Uuid(), sa.ForeignKey("businesses.id")))
    op.add_column("provider_identities", sa.Column("resolution_basis", sa.String(30)))
    op.add_column("provider_identities", sa.Column("resolved_at", sa.DateTime(timezone=True)))
    op.create_check_constraint(op.f("ck_provider_identities_party"), "provider_identities",
        "party IS NULL OR party IN ('internal','shared_mailbox','client','partner','automated','bot','unknown')")
    op.create_check_constraint(op.f("ck_provider_identities_resolution_basis"), "provider_identities",
        "resolution_basis IS NULL OR resolution_basis IN ('provider_id','email','client_contact','client_domain','partner_rule','automated','display_name','admin')")
    op.execute("UPDATE provider_identities SET party='internal' WHERE is_internal IS TRUE")
    op.create_table("account_team_members",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("person_id", sa.Uuid(), sa.ForeignKey("people.id"), nullable=False),
        sa.Column("role", sa.String(30), nullable=False), sa.Column("status", sa.String(20), nullable=False),
        sa.Column("source", sa.String(30), nullable=False), sa.Column("evidence", pg.JSONB(), nullable=False),
        sa.Column("started_on", sa.Date()), sa.Column("ended_on", sa.Date()), sa.Column("confirmed_by", sa.String(200)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)), sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('owner','ads_google','ads_meta','copy','technical','creative','operations')", name=op.f("ck_account_team_members_role")),
        sa.CheckConstraint("status IN ('suggested','confirmed','ended')", name=op.f("ck_account_team_members_status")),
        sa.CheckConstraint("source IN ('clickup_assignments','admin','roster_file')", name=op.f("ck_account_team_members_source")),
        sa.CheckConstraint("started_on IS NULL OR ended_on IS NULL OR started_on <= ended_on", name=op.f("ck_account_team_members_date_order")))
    op.create_index("ix_account_team_members_business_id", "account_team_members", ["business_id"])
    op.create_index("uq_account_team_active", "account_team_members", ["business_id", "role", "person_id"], unique=True,
                    postgresql_where=sa.text("status <> 'ended'"))
    op.create_index("uq_account_team_confirmed_owner", "account_team_members", ["business_id"], unique=True,
                    postgresql_where=sa.text("role = 'owner' AND status = 'confirmed'"))


def downgrade():
    op.drop_table("account_team_members")
    op.drop_constraint(op.f("ck_provider_identities_resolution_basis"), "provider_identities", type_="check")
    op.drop_constraint(op.f("ck_provider_identities_party"), "provider_identities", type_="check")
    op.drop_column("provider_identities", "resolved_at")
    op.drop_column("provider_identities", "resolution_basis")
    op.drop_column("provider_identities", "party_business_id")
    op.drop_column("provider_identities", "party")
    op.drop_constraint(op.f("fk_provider_identities_person_id_people"), "provider_identities", type_="foreignkey")
    op.drop_table("mailbox_holders")
    op.drop_table("person_addresses")
    op.drop_table("people")
