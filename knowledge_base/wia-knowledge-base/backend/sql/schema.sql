-- WIA Client Knowledge Base: production schema, final state at migration c09a20261106.
--
-- Generated 2026-11-06 by building an empty PostgreSQL 16 database from every Alembic migration
-- (backend/sql/migrations/versions) and dumping its schema. Same result as running the migrations, in one step.
--
-- Use ONLY on an empty production database:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/sql/schema.sql
-- It also records the Alembic revision, so later schema changes are applied as normal migrations
-- (alembic upgrade head) once production holds data. Never re-run this file on a database with data.
--
-- Regenerate after any new migration:  python -m backend.scripts.schema_export

BEGIN;
--
-- PostgreSQL database dump
--

-- Dumped from database version 16.15 (Debian 16.15-1.pgdg13+2)
-- Dumped by pg_dump version 16.15 (Debian 16.15-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account_team_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.account_team_members (
    id uuid NOT NULL,
    business_id uuid NOT NULL,
    person_id uuid NOT NULL,
    role character varying(30) NOT NULL,
    status character varying(20) NOT NULL,
    source character varying(30) NOT NULL,
    evidence jsonb NOT NULL,
    started_on date,
    ended_on date,
    confirmed_by character varying(200),
    confirmed_at timestamp with time zone,
    revision integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_account_team_members_date_order CHECK (((started_on IS NULL) OR (ended_on IS NULL) OR (started_on <= ended_on))),
    CONSTRAINT ck_account_team_members_role CHECK (((role)::text = ANY ((ARRAY['owner'::character varying, 'ads_google'::character varying, 'ads_meta'::character varying, 'copy'::character varying, 'technical'::character varying, 'creative'::character varying, 'operations'::character varying])::text[]))),
    CONSTRAINT ck_account_team_members_source CHECK (((source)::text = ANY ((ARRAY['clickup_assignments'::character varying, 'admin'::character varying, 'roster_file'::character varying])::text[]))),
    CONSTRAINT ck_account_team_members_status CHECK (((status)::text = ANY ((ARRAY['suggested'::character varying, 'confirmed'::character varying, 'ended'::character varying])::text[])))
);

--
-- Name: action_candidates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_candidates (
    id uuid NOT NULL,
    run_id uuid NOT NULL,
    business_id uuid,
    kind character varying(10) NOT NULL,
    title text NOT NULL,
    owner_side character varying(10),
    owner_name character varying(200),
    due_date date,
    due_phrase character varying(200),
    signal character varying(20),
    target_action_ref character varying(120),
    quote text NOT NULL,
    source_record_id uuid,
    unit_id uuid,
    verified boolean NOT NULL,
    status character varying(20) NOT NULL,
    decided_by character varying(200),
    decided_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_action_candidates_kind CHECK (((kind)::text = ANY ((ARRAY['new'::character varying, 'update'::character varying])::text[]))),
    CONSTRAINT ck_action_candidates_owner_side CHECK (((owner_side IS NULL) OR ((owner_side)::text = ANY ((ARRAY['WIA'::character varying, 'Client'::character varying])::text[])))),
    CONSTRAINT ck_action_candidates_signal CHECK (((signal IS NULL) OR ((signal)::text = ANY ((ARRAY['done'::character varying, 'progressed'::character varying, 'blocked'::character varying, 'date_changed'::character varying])::text[])))),
    CONSTRAINT ck_action_candidates_status CHECK (((status)::text = ANY ((ARRAY['proposed'::character varying, 'approved'::character varying, 'rejected'::character varying, 'superseded'::character varying])::text[])))
);

--
-- Name: ai_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_runs (
    id uuid NOT NULL,
    skill character varying(40) NOT NULL,
    skill_version character varying(20) NOT NULL,
    model character varying(100) NOT NULL,
    subject_kind character varying(20) NOT NULL,
    subject_id character varying(300) NOT NULL,
    business_id uuid,
    input_hash character varying(64) NOT NULL,
    state character varying(20) NOT NULL,
    prompt_tokens integer NOT NULL,
    completion_tokens integer NOT NULL,
    cost_usd numeric(12,6) NOT NULL,
    latency_ms integer,
    error_class character varying(60),
    refs jsonb NOT NULL,
    output jsonb,
    checks jsonb NOT NULL,
    is_current boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_ai_runs_state CHECK (((state)::text = ANY ((ARRAY['succeeded'::character varying, 'failed'::character varying, 'refused'::character varying])::text[]))),
    CONSTRAINT ck_ai_runs_subject_kind CHECK (((subject_kind)::text = ANY ((ARRAY['meeting'::character varying, 'call'::character varying, 'email_batch'::character varying, 'client'::character varying])::text[])))
);

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);

--
-- Name: association_reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.association_reviews (
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    record_id uuid NOT NULL,
    version_id uuid NOT NULL,
    existing_business_ids jsonb NOT NULL,
    proposed_business_ids jsonb NOT NULL,
    reason character varying(60) NOT NULL,
    state character varying(20) NOT NULL
);

--
-- Name: audit_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_events (
    actor character varying(200) NOT NULL,
    action character varying(100) NOT NULL,
    target_type character varying(50) NOT NULL,
    target_id character varying(100) NOT NULL,
    details jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    id uuid NOT NULL
);

--
-- Name: business_aliases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.business_aliases (
    business_id uuid NOT NULL,
    alias character varying(200) NOT NULL,
    id uuid NOT NULL
);

--
-- Name: businesses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.businesses (
    name character varying(200) NOT NULL,
    slug character varying(100) NOT NULL,
    status character varying(20) NOT NULL,
    lifecycle_stage character varying(30),
    revision integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    status_changed_at timestamp with time zone,
    CONSTRAINT ck_businesses_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'inactive'::character varying])::text[])))
);

--
-- Name: clickup_connections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clickup_connections (
    id uuid NOT NULL,
    person_id uuid NOT NULL,
    clickup_user_id character varying(40) NOT NULL,
    clickup_username character varying(200),
    workspace_ids jsonb NOT NULL,
    token_encrypted text NOT NULL,
    connected_by character varying(200) NOT NULL,
    connected_at timestamp with time zone NOT NULL,
    last_verified_at timestamp with time zone,
    revoked_at timestamp with time zone,
    revoked_reason character varying(200)
);

--
-- Name: client_source_decisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.client_source_decisions (
    id uuid NOT NULL,
    business_id uuid NOT NULL,
    provider character varying(20) NOT NULL,
    state character varying(20) NOT NULL,
    reason character varying(300) NOT NULL,
    decided_by character varying(200) NOT NULL,
    decided_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_client_source_decisions_state CHECK (((state)::text = 'not_applicable'::text))
);

--
-- Name: connector_accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.connector_accounts (
    provider character varying(30) NOT NULL,
    provider_account_id character varying(200) NOT NULL,
    display_identity character varying(320),
    expected_identity character varying(320) NOT NULL,
    credential_ref character varying(100) NOT NULL,
    credential_owner character varying(200),
    granted_scopes jsonb NOT NULL,
    state character varying(20) NOT NULL,
    blocked_reason character varying(200),
    last_verified_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    lease_token uuid,
    lease_work_id uuid,
    lease_until timestamp with time zone,
    next_request_at timestamp with time zone,
    heavy_request_at timestamp with time zone,
    CONSTRAINT ck_connector_accounts_provider CHECK (((provider)::text = ANY ((ARRAY['slack'::character varying, 'clickup'::character varying, 'gmail'::character varying, 'drive'::character varying, 'calendar'::character varying, 'fathom'::character varying, 'zoom'::character varying, 'leadlock'::character varying, 'ghl_billing'::character varying])::text[]))),
    CONSTRAINT ck_connector_accounts_state CHECK (((state)::text = ANY ((ARRAY['active'::character varying, 'blocked'::character varying])::text[])))
);

--
-- Name: contacts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contacts (
    business_id uuid NOT NULL,
    email character varying(320),
    domain character varying(253),
    display_name character varying(200),
    status character varying(20) NOT NULL,
    origin character varying(20) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_contacts_email_xor_domain CHECK (((email IS NULL) <> (domain IS NULL))),
    CONSTRAINT ck_contacts_status CHECK (((status)::text = ANY ((ARRAY['candidate'::character varying, 'approved'::character varying, 'rejected'::character varying])::text[])))
);

--
-- Name: content_units; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.content_units (
    version_id uuid NOT NULL,
    ordinal integer NOT NULL,
    unit_kind character varying(40) NOT NULL,
    locator jsonb NOT NULL,
    author_identity_id uuid,
    occurred_at timestamp with time zone,
    text text NOT NULL,
    text_sha256 character varying(64) NOT NULL,
    is_quoted boolean NOT NULL,
    provider_generated boolean NOT NULL,
    domain character varying(30) NOT NULL,
    retention_category character varying(40) NOT NULL,
    retention_state character varying(20) NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_content_units_domain CHECK (((domain)::text = ANY ((ARRAY['registry'::character varying, 'actions'::character varying, 'communications'::character varying, 'meetings'::character varying, 'profile'::character varying, 'support'::character varying, 'programme'::character varying, 'leads'::character varying, 'health'::character varying, 'finance'::character varying])::text[]))),
    CONSTRAINT ck_content_units_retention_state CHECK (((retention_state)::text = ANY ((ARRAY['retained'::character varying, 'expired'::character varying])::text[])))
);

--
-- Name: coverage_windows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coverage_windows (
    scope_id uuid NOT NULL,
    run_id uuid NOT NULL,
    window_start timestamp with time zone,
    window_end timestamp with time zone NOT NULL,
    contract_version character varying(40) NOT NULL,
    counts jsonb NOT NULL,
    gaps jsonb NOT NULL,
    state character varying(20) NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_coverage_windows_state CHECK (((state)::text = ANY ((ARRAY['open'::character varying, 'complete'::character varying, 'partial'::character varying, 'failed'::character varying])::text[])))
);

--
-- Name: drive_nodes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.drive_nodes (
    id uuid NOT NULL,
    connector_account_id uuid NOT NULL,
    external_id character varying(300) NOT NULL,
    parents jsonb NOT NULL,
    is_folder boolean NOT NULL,
    name character varying(500) NOT NULL
);

--
-- Name: leadlock_app_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leadlock_app_events (
    id uuid NOT NULL,
    delivery_key character varying(200) NOT NULL,
    event_type character varying(40) NOT NULL,
    company_id character varying(64),
    location_id character varying(64),
    outcome character varying(60) NOT NULL,
    received_at timestamp with time zone NOT NULL
);

--
-- Name: leadlock_installations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leadlock_installations (
    id uuid NOT NULL,
    company_id character varying(64) NOT NULL,
    app_id character varying(64),
    installed_by_user_id character varying(64),
    access_token_encrypted text NOT NULL,
    refresh_token_encrypted text NOT NULL,
    access_expires_at timestamp with time zone NOT NULL,
    scopes jsonb NOT NULL,
    is_bulk_installation boolean,
    install_to_future_locations boolean,
    approve_all_locations boolean,
    approved_location_ids jsonb NOT NULL,
    installed_at timestamp with time zone NOT NULL,
    refreshed_at timestamp with time zone,
    revision integer NOT NULL,
    revoked_at timestamp with time zone,
    revoked_reason character varying(200),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);

--
-- Name: leadlock_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leadlock_locations (
    id uuid NOT NULL,
    installation_id uuid,
    location_id character varying(64) NOT NULL,
    name character varying(300),
    state character varying(20) NOT NULL,
    access_token_encrypted text,
    access_expires_at timestamp with time zone,
    scopes jsonb NOT NULL,
    installed_at timestamp with time zone,
    uninstalled_at timestamp with time zone,
    last_token_at timestamp with time zone,
    last_error character varying(300),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_leadlock_locations_ck_leadlock_locations_state CHECK (((state)::text = ANY ((ARRAY['pending'::character varying, 'active'::character varying, 'uninstalled'::character varying, 'failed'::character varying])::text[])))
);

--
-- Name: mailbox_holders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mailbox_holders (
    id uuid NOT NULL,
    mailbox_person_id uuid NOT NULL,
    holder_person_id uuid NOT NULL,
    valid_from date,
    valid_to date,
    note character varying(500),
    CONSTRAINT ck_mailbox_holders_date_order CHECK (((valid_from IS NULL) OR (valid_to IS NULL) OR (valid_from <= valid_to)))
);

--
-- Name: outbound_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.outbound_requests (
    id uuid NOT NULL,
    kind character varying(30) NOT NULL,
    target character varying(100) NOT NULL,
    payload jsonb NOT NULL,
    payload_hash character varying(64) NOT NULL,
    preview jsonb NOT NULL,
    as_person_id uuid,
    state character varying(20) NOT NULL,
    drafted_by character varying(200) NOT NULL,
    drafted_at timestamp with time zone NOT NULL,
    approved_by character varying(200),
    approved_at timestamp with time zone,
    approved_hash character varying(64),
    sent_at timestamp with time zone,
    result jsonb NOT NULL,
    error character varying(500),
    CONSTRAINT ck_outbound_requests_kind CHECK (((kind)::text = ANY ((ARRAY['slack_post'::character varying, 'slack_dm'::character varying, 'clickup_task_update'::character varying])::text[]))),
    CONSTRAINT ck_outbound_requests_state CHECK (((state)::text = ANY ((ARRAY['draft'::character varying, 'approved'::character varying, 'sent'::character varying, 'failed'::character varying, 'refused'::character varying, 'rejected'::character varying, 'expired'::character varying])::text[])))
);

--
-- Name: people; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.people (
    id uuid NOT NULL,
    name character varying(200) NOT NULL,
    kind character varying(20) NOT NULL,
    business_id uuid,
    functions jsonb NOT NULL,
    status character varying(20) NOT NULL,
    merged_into_id uuid,
    notes character varying(500),
    revision integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_people_kind CHECK (((kind)::text = ANY ((ARRAY['staff'::character varying, 'contractor'::character varying, 'former'::character varying, 'shared_mailbox'::character varying, 'service_account'::character varying, 'client_contact'::character varying, 'partner'::character varying, 'prospect'::character varying, 'programme_member'::character varying, 'unknown'::character varying])::text[]))),
    CONSTRAINT ck_people_not_self_merged CHECK (((merged_into_id IS NULL) OR (merged_into_id <> id))),
    CONSTRAINT ck_people_status CHECK (((status)::text = ANY ((ARRAY['confirmed'::character varying, 'pending'::character varying])::text[])))
);

--
-- Name: person_addresses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.person_addresses (
    id uuid NOT NULL,
    person_id uuid NOT NULL,
    kind character varying(20) NOT NULL,
    value character varying(320) NOT NULL,
    source character varying(30) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_person_addresses_kind CHECK (((kind)::text = ANY ((ARRAY['email'::character varying, 'slack_user'::character varying, 'clickup_user'::character varying, 'fathom_email'::character varying, 'display_name'::character varying])::text[]))),
    CONSTRAINT ck_person_addresses_source CHECK (((source)::text = ANY ((ARRAY['roster'::character varying, 'admin'::character varying, 'client_contact'::character varying])::text[])))
);

--
-- Name: provider_identities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.provider_identities (
    connector_account_id uuid NOT NULL,
    external_key character varying(320) NOT NULL,
    display_name character varying(200),
    email character varying(320),
    is_internal boolean,
    person_id uuid,
    id uuid NOT NULL,
    party character varying(20),
    party_business_id uuid,
    resolution_basis character varying(30),
    resolved_at timestamp with time zone,
    CONSTRAINT ck_provider_identities_party CHECK (((party IS NULL) OR ((party)::text = ANY ((ARRAY['internal'::character varying, 'shared_mailbox'::character varying, 'client'::character varying, 'partner'::character varying, 'automated'::character varying, 'bot'::character varying, 'unknown'::character varying])::text[])))),
    CONSTRAINT ck_provider_identities_resolution_basis CHECK (((resolution_basis IS NULL) OR ((resolution_basis)::text = ANY ((ARRAY['provider_id'::character varying, 'email'::character varying, 'client_contact'::character varying, 'client_domain'::character varying, 'partner_rule'::character varying, 'automated'::character varying, 'display_name'::character varying, 'admin'::character varying])::text[]))))
);

--
-- Name: read_model_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.read_model_snapshots (
    name character varying(50) NOT NULL,
    built_at timestamp with time zone NOT NULL,
    payload jsonb NOT NULL
);

--
-- Name: record_associations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.record_associations (
    record_id uuid NOT NULL,
    business_id uuid NOT NULL,
    basis character varying(30) NOT NULL,
    status character varying(20) NOT NULL,
    multi_client boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_record_associations_basis CHECK (((basis)::text = ANY ((ARRAY['scope_mapping'::character varying, 'verified_contact'::character varying, 'series_mapping'::character varying, 'manual_review'::character varying])::text[]))),
    CONSTRAINT ck_record_associations_status CHECK (((status)::text = ANY ((ARRAY['associated'::character varying, 'unresolved'::character varying, 'rejected'::character varying])::text[])))
);

--
-- Name: record_changes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.record_changes (
    id uuid NOT NULL,
    record_id uuid NOT NULL,
    revision integer NOT NULL,
    version_id uuid,
    availability character varying(30) NOT NULL,
    created_at timestamp with time zone NOT NULL
);

--
-- Name: scope_memberships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scope_memberships (
    id uuid NOT NULL,
    record_id uuid NOT NULL,
    scope_id uuid NOT NULL,
    state character varying(20) NOT NULL,
    seen_run_id uuid
);

--
-- Name: sender_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sender_rules (
    id uuid NOT NULL,
    kind character varying(20) NOT NULL,
    email character varying(320),
    domain character varying(253),
    reason character varying(300) NOT NULL,
    created_by character varying(200) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_sender_rules_email_xor_domain CHECK (((email IS NULL) <> (domain IS NULL))),
    CONSTRAINT ck_sender_rules_kind CHECK (((kind)::text = ANY ((ARRAY['team'::character varying, 'partner'::character varying, 'blocked'::character varying])::text[])))
);

--
-- Name: service_engagements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.service_engagements (
    business_id uuid NOT NULL,
    service character varying(100) NOT NULL,
    status character varying(20) NOT NULL,
    started_on date,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);

--
-- Name: source_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_records (
    connector_account_id uuid NOT NULL,
    scope_id uuid,
    record_kind character varying(40) NOT NULL,
    external_id character varying(300) NOT NULL,
    availability character varying(30) NOT NULL,
    qualification character varying(20) NOT NULL,
    current_version_id uuid,
    source_url text,
    occurred_at timestamp with time zone,
    first_seen_at timestamp with time zone NOT NULL,
    last_seen_at timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    admitted_at timestamp with time zone,
    revision integer DEFAULT 0 NOT NULL,
    provider_state jsonb DEFAULT '{}'::jsonb NOT NULL,
    parent_external_id character varying(300),
    last_observed_at timestamp with time zone,
    CONSTRAINT ck_source_records_availability CHECK (((availability)::text = ANY ((ARRAY['available'::character varying, 'deleted_upstream'::character varying, 'access_lost'::character varying, 'out_of_scope'::character varying])::text[]))),
    CONSTRAINT ck_source_records_qualification CHECK (((qualification)::text = ANY ((ARRAY['content'::character varying, 'metadata_only'::character varying])::text[])))
);

--
-- Name: source_scopes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_scopes (
    connector_account_id uuid NOT NULL,
    kind character varying(30) NOT NULL,
    external_id character varying(300) NOT NULL,
    name character varying(500) NOT NULL,
    parent_name character varying(500),
    state character varying(20) NOT NULL,
    default_domain character varying(30) NOT NULL,
    business_id uuid,
    association_mode character varying(20) NOT NULL,
    suggested_business_id uuid,
    suggestion_reason character varying(300),
    discovery_stats jsonb NOT NULL,
    approved_at timestamp with time zone,
    approved_by character varying(200),
    last_successful_sync_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_source_scopes_association_mode CHECK (((association_mode)::text = ANY ((ARRAY['dedicated'::character varying, 'per_record'::character varying])::text[]))),
    CONSTRAINT ck_source_scopes_dedicated_has_business CHECK ((((association_mode)::text <> 'dedicated'::text) OR ((state)::text <> 'approved'::text) OR (business_id IS NOT NULL))),
    CONSTRAINT ck_source_scopes_default_domain CHECK (((default_domain)::text = ANY ((ARRAY['registry'::character varying, 'actions'::character varying, 'communications'::character varying, 'meetings'::character varying, 'profile'::character varying, 'support'::character varying, 'programme'::character varying, 'leads'::character varying, 'health'::character varying, 'finance'::character varying])::text[]))),
    CONSTRAINT ck_source_scopes_state CHECK (((state)::text = ANY ((ARRAY['candidate'::character varying, 'approved'::character varying, 'excluded'::character varying, 'retired'::character varying])::text[])))
);

--
-- Name: source_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_versions (
    record_id uuid NOT NULL,
    version_key character varying(200) NOT NULL,
    content_sha256 character varying(64) NOT NULL,
    provider_updated_at timestamp with time zone,
    observed_at timestamp with time zone NOT NULL,
    parser_version character varying(40) NOT NULL,
    content_state character varying(20) NOT NULL,
    coverage_notes jsonb NOT NULL,
    attributes jsonb NOT NULL,
    unit_count integer NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_source_versions_content_state CHECK (((content_state)::text = ANY ((ARRAY['metadata_only'::character varying, 'content'::character varying, 'content_pending'::character varying, 'unsupported'::character varying, 'partial'::character varying])::text[])))
);

--
-- Name: sync_cursors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sync_cursors (
    scope_id uuid NOT NULL,
    mode character varying(20) NOT NULL,
    cursor text,
    generation integer NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    id uuid NOT NULL
);

--
-- Name: sync_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sync_runs (
    connector_account_id uuid NOT NULL,
    scope_id uuid,
    mode character varying(20) NOT NULL,
    window_start timestamp with time zone,
    window_end timestamp with time zone NOT NULL,
    state character varying(20) NOT NULL,
    started_at timestamp with time zone NOT NULL,
    finished_at timestamp with time zone,
    pages integer NOT NULL,
    error_class character varying(30),
    id uuid NOT NULL,
    stream_id uuid,
    generation integer DEFAULT 1 NOT NULL,
    checkpoint jsonb DEFAULT '{}'::jsonb NOT NULL,
    target_external_id character varying(300),
    CONSTRAINT ck_sync_runs_mode CHECK (((mode)::text = ANY ((ARRAY['discovery'::character varying, 'backfill'::character varying, 'incremental'::character varying, 'reconcile'::character varying, 'refresh'::character varying])::text[]))),
    CONSTRAINT ck_sync_runs_state CHECK (((state)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying, 'succeeded'::character varying, 'partial'::character varying, 'failed'::character varying])::text[])))
);

--
-- Name: sync_streams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sync_streams (
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    connector_account_id uuid NOT NULL,
    stream_key character varying(320) NOT NULL,
    scope_id uuid NOT NULL,
    cursor jsonb NOT NULL,
    generation integer NOT NULL,
    enabled boolean NOT NULL,
    next_sync_at timestamp with time zone NOT NULL,
    next_reconcile_at timestamp with time zone NOT NULL,
    last_incremental_at timestamp with time zone,
    last_reconciled_at timestamp with time zone
);

--
-- Name: webhook_receipts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_receipts (
    id uuid NOT NULL,
    connector_account_id uuid NOT NULL,
    delivery_id character varying(200) NOT NULL,
    content_hash character varying(64) NOT NULL,
    received_at timestamp with time zone NOT NULL,
    run_id uuid
);

--
-- Name: work_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.work_items (
    kind character varying(50) NOT NULL,
    lane character varying(20) NOT NULL,
    input_signature character varying(300) NOT NULL,
    payload jsonb NOT NULL,
    state character varying(20) NOT NULL,
    attempt integer NOT NULL,
    next_run_at timestamp with time zone NOT NULL,
    lease_token uuid,
    lease_until timestamp with time zone,
    last_error_class character varying(30),
    last_error text,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_work_items_state CHECK (((state)::text = ANY ((ARRAY['pending'::character varying, 'claimed'::character varying, 'retry_wait'::character varying, 'succeeded'::character varying, 'blocked'::character varying, 'failed'::character varying, 'cancelled'::character varying])::text[])))
);

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);

--
-- Name: account_team_members pk_account_team_members; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_team_members
    ADD CONSTRAINT pk_account_team_members PRIMARY KEY (id);

--
-- Name: action_candidates pk_action_candidates; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_candidates
    ADD CONSTRAINT pk_action_candidates PRIMARY KEY (id);

--
-- Name: ai_runs pk_ai_runs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_runs
    ADD CONSTRAINT pk_ai_runs PRIMARY KEY (id);

--
-- Name: association_reviews pk_association_reviews; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.association_reviews
    ADD CONSTRAINT pk_association_reviews PRIMARY KEY (id);

--
-- Name: audit_events pk_audit_events; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT pk_audit_events PRIMARY KEY (id);

--
-- Name: business_aliases pk_business_aliases; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.business_aliases
    ADD CONSTRAINT pk_business_aliases PRIMARY KEY (id);

--
-- Name: businesses pk_businesses; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.businesses
    ADD CONSTRAINT pk_businesses PRIMARY KEY (id);

--
-- Name: clickup_connections pk_clickup_connections; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clickup_connections
    ADD CONSTRAINT pk_clickup_connections PRIMARY KEY (id);

--
-- Name: client_source_decisions pk_client_source_decisions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_source_decisions
    ADD CONSTRAINT pk_client_source_decisions PRIMARY KEY (id);

--
-- Name: connector_accounts pk_connector_accounts; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_accounts
    ADD CONSTRAINT pk_connector_accounts PRIMARY KEY (id);

--
-- Name: contacts pk_contacts; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contacts
    ADD CONSTRAINT pk_contacts PRIMARY KEY (id);

--
-- Name: content_units pk_content_units; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_units
    ADD CONSTRAINT pk_content_units PRIMARY KEY (id);

--
-- Name: coverage_windows pk_coverage_windows; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_windows
    ADD CONSTRAINT pk_coverage_windows PRIMARY KEY (id);

--
-- Name: drive_nodes pk_drive_nodes; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drive_nodes
    ADD CONSTRAINT pk_drive_nodes PRIMARY KEY (id);

--
-- Name: leadlock_app_events pk_leadlock_app_events; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leadlock_app_events
    ADD CONSTRAINT pk_leadlock_app_events PRIMARY KEY (id);

--
-- Name: leadlock_installations pk_leadlock_installations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leadlock_installations
    ADD CONSTRAINT pk_leadlock_installations PRIMARY KEY (id);

--
-- Name: leadlock_locations pk_leadlock_locations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leadlock_locations
    ADD CONSTRAINT pk_leadlock_locations PRIMARY KEY (id);

--
-- Name: mailbox_holders pk_mailbox_holders; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mailbox_holders
    ADD CONSTRAINT pk_mailbox_holders PRIMARY KEY (id);

--
-- Name: outbound_requests pk_outbound_requests; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outbound_requests
    ADD CONSTRAINT pk_outbound_requests PRIMARY KEY (id);

--
-- Name: people pk_people; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT pk_people PRIMARY KEY (id);

--
-- Name: person_addresses pk_person_addresses; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_addresses
    ADD CONSTRAINT pk_person_addresses PRIMARY KEY (id);

--
-- Name: provider_identities pk_provider_identities; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_identities
    ADD CONSTRAINT pk_provider_identities PRIMARY KEY (id);

--
-- Name: read_model_snapshots pk_read_model_snapshots; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.read_model_snapshots
    ADD CONSTRAINT pk_read_model_snapshots PRIMARY KEY (name);

--
-- Name: record_associations pk_record_associations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.record_associations
    ADD CONSTRAINT pk_record_associations PRIMARY KEY (id);

--
-- Name: record_changes pk_record_changes; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.record_changes
    ADD CONSTRAINT pk_record_changes PRIMARY KEY (id);

--
-- Name: scope_memberships pk_scope_memberships; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scope_memberships
    ADD CONSTRAINT pk_scope_memberships PRIMARY KEY (id);

--
-- Name: sender_rules pk_sender_rules; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sender_rules
    ADD CONSTRAINT pk_sender_rules PRIMARY KEY (id);

--
-- Name: service_engagements pk_service_engagements; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service_engagements
    ADD CONSTRAINT pk_service_engagements PRIMARY KEY (id);

--
-- Name: source_records pk_source_records; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_records
    ADD CONSTRAINT pk_source_records PRIMARY KEY (id);

--
-- Name: source_scopes pk_source_scopes; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_scopes
    ADD CONSTRAINT pk_source_scopes PRIMARY KEY (id);

--
-- Name: source_versions pk_source_versions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_versions
    ADD CONSTRAINT pk_source_versions PRIMARY KEY (id);

--
-- Name: sync_cursors pk_sync_cursors; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_cursors
    ADD CONSTRAINT pk_sync_cursors PRIMARY KEY (id);

--
-- Name: sync_runs pk_sync_runs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_runs
    ADD CONSTRAINT pk_sync_runs PRIMARY KEY (id);

--
-- Name: sync_streams pk_sync_streams; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_streams
    ADD CONSTRAINT pk_sync_streams PRIMARY KEY (id);

--
-- Name: webhook_receipts pk_webhook_receipts; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_receipts
    ADD CONSTRAINT pk_webhook_receipts PRIMARY KEY (id);

--
-- Name: work_items pk_work_items; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_items
    ADD CONSTRAINT pk_work_items PRIMARY KEY (id);

--
-- Name: business_aliases uq_business_aliases_business_id_alias; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.business_aliases
    ADD CONSTRAINT uq_business_aliases_business_id_alias UNIQUE (business_id, alias);

--
-- Name: businesses uq_businesses_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.businesses
    ADD CONSTRAINT uq_businesses_slug UNIQUE (slug);

--
-- Name: client_source_decisions uq_client_source_decisions_business_id_provider; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_source_decisions
    ADD CONSTRAINT uq_client_source_decisions_business_id_provider UNIQUE (business_id, provider);

--
-- Name: connector_accounts uq_connector_accounts_provider_provider_account_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_accounts
    ADD CONSTRAINT uq_connector_accounts_provider_provider_account_id UNIQUE (provider, provider_account_id);

--
-- Name: contacts uq_contacts_business_id_domain; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contacts
    ADD CONSTRAINT uq_contacts_business_id_domain UNIQUE (business_id, domain);

--
-- Name: contacts uq_contacts_business_id_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contacts
    ADD CONSTRAINT uq_contacts_business_id_email UNIQUE (business_id, email);

--
-- Name: content_units uq_content_units_version_id_ordinal; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_units
    ADD CONSTRAINT uq_content_units_version_id_ordinal UNIQUE (version_id, ordinal);

--
-- Name: coverage_windows uq_coverage_windows_scope_id_run_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_windows
    ADD CONSTRAINT uq_coverage_windows_scope_id_run_id UNIQUE (scope_id, run_id);

--
-- Name: drive_nodes uq_drive_nodes_connector_account_id_external_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drive_nodes
    ADD CONSTRAINT uq_drive_nodes_connector_account_id_external_id UNIQUE (connector_account_id, external_id);

--
-- Name: leadlock_app_events uq_leadlock_app_events_delivery_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leadlock_app_events
    ADD CONSTRAINT uq_leadlock_app_events_delivery_key UNIQUE (delivery_key);

--
-- Name: leadlock_locations uq_leadlock_locations_location_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leadlock_locations
    ADD CONSTRAINT uq_leadlock_locations_location_id UNIQUE (location_id);

--
-- Name: person_addresses uq_person_addresses_kind_value; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_addresses
    ADD CONSTRAINT uq_person_addresses_kind_value UNIQUE (kind, value);

--
-- Name: provider_identities uq_provider_identities_connector_account_id_external_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_identities
    ADD CONSTRAINT uq_provider_identities_connector_account_id_external_key UNIQUE (connector_account_id, external_key);

--
-- Name: record_associations uq_record_associations_record_id_business_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.record_associations
    ADD CONSTRAINT uq_record_associations_record_id_business_id UNIQUE (record_id, business_id);

--
-- Name: record_changes uq_record_changes_record_id_revision; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.record_changes
    ADD CONSTRAINT uq_record_changes_record_id_revision UNIQUE (record_id, revision);

--
-- Name: scope_memberships uq_scope_memberships_record_id_scope_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scope_memberships
    ADD CONSTRAINT uq_scope_memberships_record_id_scope_id UNIQUE (record_id, scope_id);

--
-- Name: sender_rules uq_sender_rules_domain; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sender_rules
    ADD CONSTRAINT uq_sender_rules_domain UNIQUE (domain);

--
-- Name: sender_rules uq_sender_rules_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sender_rules
    ADD CONSTRAINT uq_sender_rules_email UNIQUE (email);

--
-- Name: source_records uq_source_records_connector_account_id_record_kind_external_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_records
    ADD CONSTRAINT uq_source_records_connector_account_id_record_kind_external_id UNIQUE (connector_account_id, record_kind, external_id);

--
-- Name: source_scopes uq_source_scopes_connector_account_id_kind_external_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_scopes
    ADD CONSTRAINT uq_source_scopes_connector_account_id_kind_external_id UNIQUE (connector_account_id, kind, external_id);

--
-- Name: source_versions uq_source_versions_record_id_version_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_versions
    ADD CONSTRAINT uq_source_versions_record_id_version_key UNIQUE (record_id, version_key);

--
-- Name: sync_cursors uq_sync_cursors_scope_id_mode; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_cursors
    ADD CONSTRAINT uq_sync_cursors_scope_id_mode UNIQUE (scope_id, mode);

--
-- Name: sync_streams uq_sync_streams_connector_account_id_stream_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_streams
    ADD CONSTRAINT uq_sync_streams_connector_account_id_stream_key UNIQUE (connector_account_id, stream_key);

--
-- Name: webhook_receipts uq_webhook_receipts_connector_account_id_delivery_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_receipts
    ADD CONSTRAINT uq_webhook_receipts_connector_account_id_delivery_id UNIQUE (connector_account_id, delivery_id);

--
-- Name: work_items uq_work_items_kind_input_signature; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_items
    ADD CONSTRAINT uq_work_items_kind_input_signature UNIQUE (kind, input_signature);

--
-- Name: ix_account_team_members_business_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_account_team_members_business_id ON public.account_team_members USING btree (business_id);

--
-- Name: ix_action_candidates_business_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_action_candidates_business_id ON public.action_candidates USING btree (business_id);

--
-- Name: ix_action_candidates_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_action_candidates_run_id ON public.action_candidates USING btree (run_id);

--
-- Name: ix_ai_runs_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_runs_created ON public.ai_runs USING btree (created_at);

--
-- Name: ix_association_reviews_record_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_association_reviews_record_id ON public.association_reviews USING btree (record_id);

--
-- Name: ix_business_aliases_business_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_business_aliases_business_id ON public.business_aliases USING btree (business_id);

--
-- Name: ix_clickup_connections_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_clickup_connections_person_id ON public.clickup_connections USING btree (person_id);

--
-- Name: ix_client_source_decisions_business_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_client_source_decisions_business_id ON public.client_source_decisions USING btree (business_id);

--
-- Name: ix_contacts_business_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contacts_business_id ON public.contacts USING btree (business_id);

--
-- Name: ix_content_units_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_content_units_version ON public.content_units USING btree (version_id);

--
-- Name: ix_leadlock_locations_installation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leadlock_locations_installation_id ON public.leadlock_locations USING btree (installation_id);

--
-- Name: ix_mailbox_holders_mailbox_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mailbox_holders_mailbox_person_id ON public.mailbox_holders USING btree (mailbox_person_id);

--
-- Name: ix_outbound_requests_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_outbound_requests_state ON public.outbound_requests USING btree (state);

--
-- Name: ix_person_addresses_person_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_person_addresses_person_id ON public.person_addresses USING btree (person_id);

--
-- Name: ix_record_associations_business_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_record_associations_business_id ON public.record_associations USING btree (business_id);

--
-- Name: ix_record_associations_record_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_record_associations_record_id ON public.record_associations USING btree (record_id);

--
-- Name: ix_record_changes_record_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_record_changes_record_id ON public.record_changes USING btree (record_id);

--
-- Name: ix_scope_memberships_record_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scope_memberships_record_id ON public.scope_memberships USING btree (record_id);

--
-- Name: ix_scope_memberships_scope_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scope_memberships_scope_id ON public.scope_memberships USING btree (scope_id);

--
-- Name: ix_service_engagements_business_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_service_engagements_business_id ON public.service_engagements USING btree (business_id);

--
-- Name: ix_source_records_occurred_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_records_occurred_at ON public.source_records USING btree (occurred_at);

--
-- Name: ix_source_records_parent_external_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_records_parent_external_id ON public.source_records USING btree (parent_external_id);

--
-- Name: ix_source_records_scope_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_records_scope_id ON public.source_records USING btree (scope_id);

--
-- Name: ix_source_scopes_connector_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_scopes_connector_account_id ON public.source_scopes USING btree (connector_account_id);

--
-- Name: ix_source_versions_record_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_versions_record_id ON public.source_versions USING btree (record_id);

--
-- Name: ix_sync_runs_scope_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sync_runs_scope_id ON public.sync_runs USING btree (scope_id);

--
-- Name: ix_sync_runs_stream_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sync_runs_stream_id ON public.sync_runs USING btree (stream_id);

--
-- Name: ix_sync_streams_connector_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sync_streams_connector_account_id ON public.sync_streams USING btree (connector_account_id);

--
-- Name: ix_work_items_due; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_work_items_due ON public.work_items USING btree (lane, next_run_at) WHERE ((state)::text = ANY ((ARRAY['pending'::character varying, 'retry_wait'::character varying])::text[]));

--
-- Name: uq_account_team_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_account_team_active ON public.account_team_members USING btree (business_id, role, person_id) WHERE ((status)::text <> 'ended'::text);

--
-- Name: uq_account_team_confirmed_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_account_team_confirmed_owner ON public.account_team_members USING btree (business_id) WHERE (((role)::text = 'owner'::text) AND ((status)::text = 'confirmed'::text));

--
-- Name: uq_ai_runs_current; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_ai_runs_current ON public.ai_runs USING btree (skill, subject_id) WHERE is_current;

--
-- Name: uq_ai_runs_succeeded_input; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_ai_runs_succeeded_input ON public.ai_runs USING btree (skill, input_hash) WHERE ((state)::text = 'succeeded'::text);

--
-- Name: uq_association_review_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_association_review_pending ON public.association_reviews USING btree (record_id) WHERE ((state)::text = 'pending'::text);

--
-- Name: uq_clickup_connections_active_person; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_clickup_connections_active_person ON public.clickup_connections USING btree (person_id) WHERE (revoked_at IS NULL);

--
-- Name: uq_leadlock_installations_active_company; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_leadlock_installations_active_company ON public.leadlock_installations USING btree (company_id) WHERE (revoked_at IS NULL);

--
-- Name: uq_sync_run_active_stream; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_sync_run_active_stream ON public.sync_runs USING btree (stream_id) WHERE ((state)::text = 'running'::text);

--
-- Name: account_team_members fk_account_team_members_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_team_members
    ADD CONSTRAINT fk_account_team_members_business_id_businesses FOREIGN KEY (business_id) REFERENCES public.businesses(id);

--
-- Name: account_team_members fk_account_team_members_person_id_people; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_team_members
    ADD CONSTRAINT fk_account_team_members_person_id_people FOREIGN KEY (person_id) REFERENCES public.people(id);

--
-- Name: action_candidates fk_action_candidates_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_candidates
    ADD CONSTRAINT fk_action_candidates_business_id_businesses FOREIGN KEY (business_id) REFERENCES public.businesses(id);

--
-- Name: action_candidates fk_action_candidates_run_id_ai_runs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_candidates
    ADD CONSTRAINT fk_action_candidates_run_id_ai_runs FOREIGN KEY (run_id) REFERENCES public.ai_runs(id);

--
-- Name: action_candidates fk_action_candidates_source_record_id_source_records; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_candidates
    ADD CONSTRAINT fk_action_candidates_source_record_id_source_records FOREIGN KEY (source_record_id) REFERENCES public.source_records(id);

--
-- Name: action_candidates fk_action_candidates_unit_id_content_units; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_candidates
    ADD CONSTRAINT fk_action_candidates_unit_id_content_units FOREIGN KEY (unit_id) REFERENCES public.content_units(id);

--
-- Name: ai_runs fk_ai_runs_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_runs
    ADD CONSTRAINT fk_ai_runs_business_id_businesses FOREIGN KEY (business_id) REFERENCES public.businesses(id);

--
-- Name: association_reviews fk_association_reviews_record_id_source_records; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.association_reviews
    ADD CONSTRAINT fk_association_reviews_record_id_source_records FOREIGN KEY (record_id) REFERENCES public.source_records(id);

--
-- Name: association_reviews fk_association_reviews_version_id_source_versions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.association_reviews
    ADD CONSTRAINT fk_association_reviews_version_id_source_versions FOREIGN KEY (version_id) REFERENCES public.source_versions(id);

--
-- Name: business_aliases fk_business_aliases_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.business_aliases
    ADD CONSTRAINT fk_business_aliases_business_id_businesses FOREIGN KEY (business_id) REFERENCES public.businesses(id);

--
-- Name: clickup_connections fk_clickup_connections_person_id_people; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clickup_connections
    ADD CONSTRAINT fk_clickup_connections_person_id_people FOREIGN KEY (person_id) REFERENCES public.people(id);

--
-- Name: client_source_decisions fk_client_source_decisions_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_source_decisions
    ADD CONSTRAINT fk_client_source_decisions_business_id_businesses FOREIGN KEY (business_id) REFERENCES public.businesses(id);

--
-- Name: contacts fk_contacts_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contacts
    ADD CONSTRAINT fk_contacts_business_id_businesses FOREIGN KEY (business_id) REFERENCES public.businesses(id);

--
-- Name: content_units fk_content_units_author_identity_id_provider_identities; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_units
    ADD CONSTRAINT fk_content_units_author_identity_id_provider_identities FOREIGN KEY (author_identity_id) REFERENCES public.provider_identities(id);

--
-- Name: content_units fk_content_units_version_id_source_versions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_units
    ADD CONSTRAINT fk_content_units_version_id_source_versions FOREIGN KEY (version_id) REFERENCES public.source_versions(id);

--
-- Name: coverage_windows fk_coverage_windows_run_id_sync_runs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_windows
    ADD CONSTRAINT fk_coverage_windows_run_id_sync_runs FOREIGN KEY (run_id) REFERENCES public.sync_runs(id);

--
-- Name: coverage_windows fk_coverage_windows_scope_id_source_scopes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coverage_windows
    ADD CONSTRAINT fk_coverage_windows_scope_id_source_scopes FOREIGN KEY (scope_id) REFERENCES public.source_scopes(id);

--
-- Name: drive_nodes fk_drive_nodes_connector_account_id_connector_accounts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drive_nodes
    ADD CONSTRAINT fk_drive_nodes_connector_account_id_connector_accounts FOREIGN KEY (connector_account_id) REFERENCES public.connector_accounts(id);

--
-- Name: leadlock_locations fk_leadlock_locations_installation_id_leadlock_installations; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leadlock_locations
    ADD CONSTRAINT fk_leadlock_locations_installation_id_leadlock_installations FOREIGN KEY (installation_id) REFERENCES public.leadlock_installations(id);

--
-- Name: mailbox_holders fk_mailbox_holders_holder_person_id_people; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mailbox_holders
    ADD CONSTRAINT fk_mailbox_holders_holder_person_id_people FOREIGN KEY (holder_person_id) REFERENCES public.people(id);

--
-- Name: mailbox_holders fk_mailbox_holders_mailbox_person_id_people; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mailbox_holders
    ADD CONSTRAINT fk_mailbox_holders_mailbox_person_id_people FOREIGN KEY (mailbox_person_id) REFERENCES public.people(id);

--
-- Name: outbound_requests fk_outbound_requests_as_person_id_people; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outbound_requests
    ADD CONSTRAINT fk_outbound_requests_as_person_id_people FOREIGN KEY (as_person_id) REFERENCES public.people(id);

--
-- Name: people fk_people_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT fk_people_business_id_businesses FOREIGN KEY (business_id) REFERENCES public.businesses(id);

--
-- Name: people fk_people_merged_into_id_people; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT fk_people_merged_into_id_people FOREIGN KEY (merged_into_id) REFERENCES public.people(id);

--
-- Name: person_addresses fk_person_addresses_person_id_people; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_addresses
    ADD CONSTRAINT fk_person_addresses_person_id_people FOREIGN KEY (person_id) REFERENCES public.people(id);

--
-- Name: provider_identities fk_provider_identities_connector_account_id_connector_accounts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_identities
    ADD CONSTRAINT fk_provider_identities_connector_account_id_connector_accounts FOREIGN KEY (connector_account_id) REFERENCES public.connector_accounts(id);

--
-- Name: provider_identities fk_provider_identities_party_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_identities
    ADD CONSTRAINT fk_provider_identities_party_business_id_businesses FOREIGN KEY (party_business_id) REFERENCES public.businesses(id);

--
-- Name: provider_identities fk_provider_identities_person_id_people; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_identities
    ADD CONSTRAINT fk_provider_identities_person_id_people FOREIGN KEY (person_id) REFERENCES public.people(id);

--
-- Name: record_associations fk_record_associations_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.record_associations
    ADD CONSTRAINT fk_record_associations_business_id_businesses FOREIGN KEY (business_id) REFERENCES public.businesses(id);

--
-- Name: record_associations fk_record_associations_record_id_source_records; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.record_associations
    ADD CONSTRAINT fk_record_associations_record_id_source_records FOREIGN KEY (record_id) REFERENCES public.source_records(id);

--
-- Name: record_changes fk_record_changes_record_id_source_records; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.record_changes
    ADD CONSTRAINT fk_record_changes_record_id_source_records FOREIGN KEY (record_id) REFERENCES public.source_records(id);

--
-- Name: record_changes fk_record_changes_version_id_source_versions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.record_changes
    ADD CONSTRAINT fk_record_changes_version_id_source_versions FOREIGN KEY (version_id) REFERENCES public.source_versions(id);

--
-- Name: scope_memberships fk_scope_memberships_record_id_source_records; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scope_memberships
    ADD CONSTRAINT fk_scope_memberships_record_id_source_records FOREIGN KEY (record_id) REFERENCES public.source_records(id);

--
-- Name: scope_memberships fk_scope_memberships_scope_id_source_scopes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scope_memberships
    ADD CONSTRAINT fk_scope_memberships_scope_id_source_scopes FOREIGN KEY (scope_id) REFERENCES public.source_scopes(id);

--
-- Name: scope_memberships fk_scope_memberships_seen_run_id_sync_runs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scope_memberships
    ADD CONSTRAINT fk_scope_memberships_seen_run_id_sync_runs FOREIGN KEY (seen_run_id) REFERENCES public.sync_runs(id);

--
-- Name: service_engagements fk_service_engagements_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service_engagements
    ADD CONSTRAINT fk_service_engagements_business_id_businesses FOREIGN KEY (business_id) REFERENCES public.businesses(id);

--
-- Name: source_records fk_source_records_connector_account_id_connector_accounts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_records
    ADD CONSTRAINT fk_source_records_connector_account_id_connector_accounts FOREIGN KEY (connector_account_id) REFERENCES public.connector_accounts(id);

--
-- Name: source_records fk_source_records_current_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_records
    ADD CONSTRAINT fk_source_records_current_version FOREIGN KEY (current_version_id) REFERENCES public.source_versions(id);

--
-- Name: source_records fk_source_records_scope_id_source_scopes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_records
    ADD CONSTRAINT fk_source_records_scope_id_source_scopes FOREIGN KEY (scope_id) REFERENCES public.source_scopes(id);

--
-- Name: source_scopes fk_source_scopes_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_scopes
    ADD CONSTRAINT fk_source_scopes_business_id_businesses FOREIGN KEY (business_id) REFERENCES public.businesses(id);

--
-- Name: source_scopes fk_source_scopes_connector_account_id_connector_accounts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_scopes
    ADD CONSTRAINT fk_source_scopes_connector_account_id_connector_accounts FOREIGN KEY (connector_account_id) REFERENCES public.connector_accounts(id);

--
-- Name: source_scopes fk_source_scopes_suggested_business_id_businesses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_scopes
    ADD CONSTRAINT fk_source_scopes_suggested_business_id_businesses FOREIGN KEY (suggested_business_id) REFERENCES public.businesses(id);

--
-- Name: source_versions fk_source_versions_record_id_source_records; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_versions
    ADD CONSTRAINT fk_source_versions_record_id_source_records FOREIGN KEY (record_id) REFERENCES public.source_records(id);

--
-- Name: sync_cursors fk_sync_cursors_scope_id_source_scopes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_cursors
    ADD CONSTRAINT fk_sync_cursors_scope_id_source_scopes FOREIGN KEY (scope_id) REFERENCES public.source_scopes(id);

--
-- Name: sync_runs fk_sync_runs_connector_account_id_connector_accounts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_runs
    ADD CONSTRAINT fk_sync_runs_connector_account_id_connector_accounts FOREIGN KEY (connector_account_id) REFERENCES public.connector_accounts(id);

--
-- Name: sync_runs fk_sync_runs_scope_id_source_scopes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_runs
    ADD CONSTRAINT fk_sync_runs_scope_id_source_scopes FOREIGN KEY (scope_id) REFERENCES public.source_scopes(id);

--
-- Name: sync_runs fk_sync_runs_stream_id_sync_streams; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_runs
    ADD CONSTRAINT fk_sync_runs_stream_id_sync_streams FOREIGN KEY (stream_id) REFERENCES public.sync_streams(id);

--
-- Name: sync_streams fk_sync_streams_connector_account_id_connector_accounts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_streams
    ADD CONSTRAINT fk_sync_streams_connector_account_id_connector_accounts FOREIGN KEY (connector_account_id) REFERENCES public.connector_accounts(id);

--
-- Name: sync_streams fk_sync_streams_scope_id_source_scopes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_streams
    ADD CONSTRAINT fk_sync_streams_scope_id_source_scopes FOREIGN KEY (scope_id) REFERENCES public.source_scopes(id);

--
-- Name: webhook_receipts fk_webhook_receipts_connector_account_id_connector_accounts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_receipts
    ADD CONSTRAINT fk_webhook_receipts_connector_account_id_connector_accounts FOREIGN KEY (connector_account_id) REFERENCES public.connector_accounts(id);

--
-- Name: webhook_receipts fk_webhook_receipts_run_id_sync_runs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_receipts
    ADD CONSTRAINT fk_webhook_receipts_run_id_sync_runs FOREIGN KEY (run_id) REFERENCES public.sync_runs(id);

--
-- PostgreSQL database dump complete
--

-- Mark the database as being at the latest migration, so future migrations start from here.
INSERT INTO public.alembic_version (version_num) VALUES ('c09a20261106');

COMMIT;
