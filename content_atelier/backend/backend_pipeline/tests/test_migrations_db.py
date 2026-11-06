"""0.B3 step 1: migration 005 through `storage_cli migrate`, on isolated throwaway databases.

Each test creates its own database next to atelier_test (named atelier_test_*), so the shared
baseline database the other suites use is never migrated. Synthetic data only.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from psycopg import sql

from backend_pipeline import database
from backend_pipeline import schema_catalog
from backend_pipeline.database import LATEST, check, connect, migrate

URL = os.getenv('ATELIER_TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='Set isolated ATELIER_TEST_DATABASE_URL to run PostgreSQL integration tests')
PHASE_E_TABLES = {'schema_migrations', 'settings', 'users', 'decisions', 'calibration_labels', 'run_plans', 'llm_runs',
                  'external_calls', 'brand_kit_docs', 'seeds'}
PHASE_L_TABLES = {'brand_kit_items', 'published_content'}
ALL = ('001', '002', '003', '004', '005', '006', '007', '008', '009', '010', '011', '012')


def database_url(name):
    parts = urlsplit(URL)
    return urlunsplit(parts._replace(path='/' + name))


def recreate(name):
    """Drop and create a throwaway database beside atelier_test; refuses any other name."""
    assert urlsplit(URL).path == '/atelier_test', 'Tests refuse any database except atelier_test'
    assert name.startswith('atelier_test_')
    with psycopg.connect(URL, autocommit=True) as admin:
        admin.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    return database_url(name)


@pytest.fixture
def fresh():
    return recreate('atelier_test_migrate')


def legacy(url, through):
    """A database as the bespoke commands left it before the runner: files 001 to `through` applied, nothing recorded."""
    with connect(url, vectors=False) as conn:
        for number in ('001', '002', '003', '004'):
            if number <= through:
                conn.execute((database.MIGRATIONS / database.MIGRATION_FILES[number]).read_text(encoding='utf-8'))


def tables(url):
    with connect(url, vectors=False) as conn:
        return {r['tablename'] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}


def versions(url):
    with connect(url, vectors=False) as conn:
        return {r['version']: r['source'] for r in conn.execute('SELECT version,source FROM schema_migrations')}


def test_a_fresh_database_reaches_the_latest_version_with_one_command(fresh):
    result = migrate(fresh)
    assert result['status'] == 'migrated' and result['version'] == LATEST == '012'
    assert result['applied'] == list(ALL)
    assert PHASE_E_TABLES | PHASE_L_TABLES <= tables(fresh)
    assert versions(fresh) == dict.fromkeys(ALL, 'applied')
    assert migrate(fresh)['status'] == 'already_current'
    with connect(fresh, vectors=False) as conn:
        columns = {r['column_name'] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='pipeline_jobs'")}
        assert {'queue', 'rq_job_id', 'priority'} <= columns


def test_an_existing_001_to_004_database_upgrades_in_place(fresh):
    legacy(fresh, '004')
    with connect(fresh, vectors=False) as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_2026-06-01','2026-06-01','2026-06-07')")
    result = migrate(fresh)
    assert result['applied'] == ['005', '006', '007', '008', '009', '010', '011', '012']
    assert versions(fresh) == {**dict.fromkeys(('001', '002', '003', '004'), 'detected'), '005': 'applied', '006': 'applied', '007': 'applied', '008': 'applied', '009': 'applied', '010': 'applied', '011': 'applied', '012': 'applied'}
    with connect(fresh, vectors=False) as conn:
        assert conn.execute("SELECT count(*) n FROM weeks").fetchone()['n'] == 1, 'existing rows keep their data'
        assert conn.execute("SELECT queue FROM pipeline_jobs LIMIT 1").fetchone() is None


def test_a_baseline_only_database_gets_the_missing_files_in_order(fresh):
    legacy(fresh, '001')
    result = migrate(fresh)
    assert result['applied'] == ['002', '003', '004', '005', '006', '007', '008', '009', '010', '011', '012']
    assert versions(fresh)['001'] == 'detected'


def test_an_altered_column_fails_check(fresh):
    migrate(fresh)
    with connect(fresh, vectors=False) as conn:
        check(conn)
        conn.execute('ALTER TABLE run_plans ADD COLUMN surprise text')
        with pytest.raises(RuntimeError, match='differs from approved baseline'):
            check(conn)
        conn.rollback()


def test_a_legacy_database_with_foreign_objects_is_refused_and_rolled_back(fresh):
    legacy(fresh, '003')
    with connect(fresh, vectors=False) as conn:
        conn.execute('ALTER TABLE weeks ADD COLUMN unexpected text')
    with pytest.raises(RuntimeError, match='catalogue differs'):
        migrate(fresh)
    assert 'schema_migrations' not in tables(fresh), 'nothing is recorded or repaired after a refusal'
    with connect(fresh, vectors=False) as conn:
        assert conn.execute("SELECT count(*) n FROM information_schema.columns WHERE table_name='weeks' AND column_name='unexpected'").fetchone()['n'] == 1
        assert conn.execute("SELECT to_regclass('public.mutation_receipts') t").fetchone()['t'] is None, '004 was not applied'


def test_check_on_a_database_with_no_recorded_version_says_to_migrate(fresh):
    legacy(fresh, '004')
    with connect(fresh, vectors=False) as conn:
        with pytest.raises(RuntimeError, match='run `storage_cli migrate`'):
            check(conn)


def test_migrate_can_stop_at_a_version_and_never_goes_backwards(fresh):
    result = migrate(fresh, target='005')
    assert result['version'] == '005' and result['applied'] == ['001', '002', '003', '004', '005']
    assert 'brand_kit_items' not in tables(fresh)
    assert migrate(fresh)['applied'] == ['006', '007', '008', '009', '010', '011', '012']
    with pytest.raises(RuntimeError, match='never moves backwards'):
        migrate(fresh, target='005')
    with pytest.raises(ValueError, match='Cannot migrate to 004'):
        migrate(fresh, target='004')


def test_every_catalogue_equals_a_database_migrated_from_nothing():
    """CI fails on drift (0.B3): a migration file and its catalogue cannot change apart, and no catalogue is unused."""
    for version in sorted(v for v in database.MIGRATION_FILES if v >= database.FIRST_RECORDED):
        assert schema_catalog.build(URL, version) == database.expected_catalog(version), f'schema-catalog-{version}.json has drifted'
    assert schema_catalog.main(['--check']) == 0
    assert sorted(p.name for p in database.MIGRATIONS.glob('schema-catalog*.json')) == [
        f'schema-catalog-{v}.json' for v in sorted(v for v in database.MIGRATION_FILES if v >= database.FIRST_RECORDED)]


def test_the_bespoke_apply_functions_and_combination_catalogues_are_gone():
    assert not any(hasattr(database, name) for name in ('initialize', 'apply_brief_indexes', 'apply_intake', 'apply_calendar'))


def test_a_partial_or_foreign_database_is_refused(fresh):
    with connect(fresh, vectors=False) as conn:
        conn.execute('CREATE TABLE weeks(week_id text PRIMARY KEY)')
    with pytest.raises(RuntimeError, match='without the approved baseline'):
        migrate(fresh)
    assert tables(fresh) == {'weeks'}, 'nothing is repaired or partly applied'


def test_the_catalogue_file_describes_the_migrated_schema(fresh):
    migrate(fresh)
    with connect(fresh, vectors=False) as conn:
        assert database.catalog(conn) == database.expected_catalog(LATEST)


def apply_through_005(url):
    """A database left at 005 by the Phase E runner: 001 to 005 applied and recorded, nothing later."""
    with connect(url, vectors=False) as conn:
        for number in ('001', '002', '003', '004', '005'):
            conn.execute((database.MIGRATIONS / database.MIGRATION_FILES[number]).read_text(encoding='utf-8'))
        for number in ('001', '002', '003', '004', '005'):
            conn.execute('INSERT INTO schema_migrations(version,name,checksum,source) VALUES (%s,%s,%s,%s)',
                         (number, database.MIGRATION_FILES[number], database._checksum(database.MIGRATION_FILES[number]), 'applied'))
        assert database.catalog(conn) == database.expected_catalog('005')


def test_a_database_at_005_gets_006_through_the_runner(fresh):
    """L.B1: the context store applies through the runner on a database already at 005 (as staging and production are)."""
    apply_through_005(fresh)
    with connect(fresh, vectors=False) as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_2026-06-01','2026-06-01','2026-06-07')")
        conn.execute("INSERT INTO decisions(decision_id,item_kind,item_id,action,actor,author) VALUES ('d1','seed','s1','x','a','a')")
    result = migrate(fresh)
    assert result['applied'] == ['006', '007', '008', '009', '010', '011', '012'] and result['version'] == '012'
    assert versions(fresh)['006'] == 'applied'
    assert PHASE_L_TABLES <= tables(fresh)
    with connect(fresh, vectors=False) as conn:
        assert conn.execute("SELECT count(*) n FROM decisions").fetchone()['n'] == 1, 'existing rows keep their data'
        columns = {r['column_name'] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='brand_kit_docs'")}
        assert {'compiled_from', 'benchmark_state'} <= columns
        # Version decisions are now an audited item kind.
        conn.execute("INSERT INTO decisions(decision_id,item_kind,item_id,action,actor,author) VALUES ('d2','brand_kit_version','v','x','a','a')")
    assert migrate(fresh)['status'] == 'already_current'


def test_a_changed_applied_migration_is_refused(fresh):
    apply_through_005(fresh)
    with connect(fresh, vectors=False) as conn:
        conn.execute("UPDATE schema_migrations SET checksum='0' WHERE version='005'")
    with pytest.raises(RuntimeError, match='changed after it was applied'):
        migrate(fresh)
    assert 'brand_kit_items' not in tables(fresh), 'nothing is applied after a refusal'


def apply_through_006(url):
    """A database left at 006 by Phase L: 001 to 006 applied and recorded, nothing later."""
    apply_through_005(url)
    with connect(url, vectors=False) as conn:
        conn.execute((database.MIGRATIONS / database.MIGRATION_FILES['006']).read_text(encoding='utf-8'))
        conn.execute('INSERT INTO schema_migrations(version,name,checksum,source) VALUES (%s,%s,%s,%s)',
                     ('006', database.MIGRATION_FILES['006'], database._checksum(database.MIGRATION_FILES['006']), 'applied'))


def test_a_database_at_006_gets_the_evidence_model_and_keeps_every_row(fresh):
    """1.B1: migration 007 applies through the runner; documents and chunks keep their data and gain what is known."""
    apply_through_006(fresh)
    with connect(fresh, vectors=False) as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_2026-06-01','2026-06-01','2026-06-07')")
        conn.execute("""INSERT INTO transcripts(transcript_id,week_id,source_type,title,occurred_at,original_text,passage_map,content_hash)
            VALUES ('t_dated','week_2026-06-01','fathom','Dated call','2026-06-02T15:00:00Z','Hello there','[]','h1'),
                   ('t_undated','week_2026-06-01','zoom','Undated call',NULL,'Hello again','[]','h2')""")
        conn.execute("""INSERT INTO transcript_chunks(chunk_id,transcript_id,chunk_text,passage_refs,content_hash)
            VALUES ('c1','t_dated','Source: Dated call
Hello there','[]','ch1')""")
        conn.execute("""INSERT INTO pipeline_runs(run_id,week_id,run_scope,status,trigger_type,input_refs)
            VALUES ('r1','week_2026-06-01','weekly_angles','completed','manual','{"transcripts":[{"id":"t_dated","hash":"h1"}]}')""")
        conn.execute("""INSERT INTO pipeline_jobs(job_id,run_id,week_id,stage,status,idempotency_key,input_hash)
            VALUES ('j1','r1','week_2026-06-01','moment_extraction','completed','k1','x')""")
    result = migrate(fresh, target='007')
    assert result['applied'] == ['007'] and result['version'] == '007'
    assert {'clients', 'people', 'glossary_terms', 'slack_channels'} <= tables(fresh)
    with connect(fresh, vectors=False) as conn:
        dated = conn.execute("SELECT * FROM transcripts WHERE transcript_id='t_dated'").fetchone()
        undated = conn.execute("SELECT * FROM transcripts WHERE transcript_id='t_undated'").fetchone()
        assert dated['original_text'] == 'Hello there' and dated['week_id'] == 'week_2026-06-01', 'existing rows keep their data'
        assert dated['occurred_at_source'] == 'provider' and undated['occurred_at_source'] is None, 'a date has a source; none is invented'
        assert dated['raw_object_key'] == 'source-originals/h1.original' and dated['included'] is True and dated['call_type'] is None
        assert (dated['extraction_status'], undated['extraction_status']) == ('completed', 'pending')
        chunk = conn.execute("SELECT * FROM transcript_chunks WHERE chunk_id='c1'").fetchone()
        assert chunk['segmentation_version'] == 'v1' and chunk['is_current'] is True and chunk['occurred_at'] == dated['occurred_at']
        assert conn.execute("SELECT count(*) n FROM transcript_chunks WHERE tsv @@ websearch_to_tsquery('english','hello')").fetchone()['n'] == 1
        with pytest.raises(Exception, match='transcripts_exclusion_has_reason'):
            conn.execute("UPDATE transcripts SET included=false WHERE transcript_id='t_dated'")
    with connect(fresh, vectors=False) as conn:
        assert database.catalog(conn) == database.expected_catalog('007')


PASSAGES = [{"passage_id": "src1:span:0", "ordinal": 0, "start": 0, "end": 40, "speaker": "Jacqueline", "start_ms": 0, "end_ms": 1000, "kind": "cue"},
            {"passage_id": "src1:span:1", "ordinal": 1, "start": 41, "end": 80, "speaker": "Dana Client", "start_ms": 1000, "end_ms": 2000, "kind": "cue"}]


def test_a_database_at_007_gets_the_moments_ledger_and_every_moment_is_readable_through_the_new_columns(fresh):
    """2.B1: existing moments are promoted from moment_body and evidence_refs, never regenerated; the unverified moments
    that lived only in a job's result_refs become rows with quote_verified=false."""
    import json
    migrate(fresh, target='007')
    body = {"quote": "We tripled the leads", "context_summary": "A budget review", "moment_type": "result", "proposition": "p",
            "audience_relevance": "a", "qualifications": [], "claim_status": "reported", "sensitivity": "public_candidate",
            "strength": 3.0, "reasons": ["r"]}

    def refs(pid, tid):
        return [{"transcript_id": tid, "passage_id": pid, "start": 41, "end": 80, "roles": ["anchor", "context"]}]

    with connect(fresh, vectors=False) as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_2026-06-01','2026-06-01','2026-06-07')")
        conn.execute("INSERT INTO clients(client_id,name,consent) VALUES ('c1','Dana Weddings','may_name'),('c2','Quiet Venue','no_use')")
        conn.execute("INSERT INTO people(person_id,name,role,source) VALUES ('p_dana','Dana Client','client','call'),('p_jac','Jacqueline','staff','roster')")
        mapping = {"Jacqueline": {"person_id": "p_jac", "role": "staff"}, "Dana Client": {"person_id": "p_dana", "role": "client"}}
        for tid, client, speakers in [("t1", "c1", mapping), ("t2", "c2", None)]:
            conn.execute("""INSERT INTO transcripts(transcript_id,week_id,source_type,title,occurred_at,original_text,passage_map,content_hash,client_id,speaker_map)
                VALUES (%s,'week_2026-06-01','fathom','Call','2026-06-02T15:00:00Z','x',%s::jsonb,%s,%s,%s::jsonb)""",
                         (tid, json.dumps(PASSAGES), "h" + tid, client, None if speakers is None else json.dumps(speakers)))
        conn.execute("""INSERT INTO pipeline_runs(run_id,week_id,run_scope,status,trigger_type,input_refs)
            VALUES ('r1','week_2026-06-01','weekly_angles','completed','manual','{"transcripts":[{"id":"t1","hash":"ht1"}]}')""")
        unverified_record = {"local_key": "u1", "reason": "Moment quote must match an existing anchor span", "usable_as_proof": False,
                             "draft": {**body, "local_key": "u1", "quote": "not in the source", "anchor_span_ids": ["src1:span:1"]}}
        conn.execute("""INSERT INTO pipeline_jobs(job_id,run_id,week_id,stage,status,idempotency_key,input_hash,result_refs)
            VALUES ('j1','r1','week_2026-06-01','moment_extraction','completed','k1','x',%s::jsonb)""",
                     (json.dumps({"extraction_profile": "2026-10-18.scenes.v1", "unverified_moments": [unverified_record]}),))
        for mid, tid, pid in [("m_client", "t1", "src1:span:1"), ("m_staff", "t1", "src1:span:0"), ("m_blocked", "t2", "src1:span:1")]:
            conn.execute("INSERT INTO key_moments(moment_id,week_id,run_id,moment_body,evidence_refs) VALUES (%s,'week_2026-06-01','r1',%s::jsonb,%s::jsonb)",
                         (mid, json.dumps(body), json.dumps(refs(pid, tid))))
    result = migrate(fresh, target='008')
    assert result['applied'] == ['008'] and result['version'] == '008'
    with connect(fresh, vectors=False) as conn:
        rows = {r['moment_id']: r for r in conn.execute("SELECT * FROM key_moments")}
        client, staff, blocked = rows['m_client'], rows['m_staff'], rows['m_blocked']
        assert client['document_id'] == 't1' and client['moment_type'] == 'result' and client['sensitivity'] == 'public_candidate'
        assert (client['speaker_label'], client['speaker_id'], client['speaker_role']) == ('Dana Client', 'p_dana', 'client')
        assert client['evidence_kind'] == 'direct_quote' and client['consent_status'] == 'cleared' and client['client_id'] == 'c1'
        assert client['quote_verified'] is True and client['extractor_version'] == '2026-10-18.scenes.v1', 'the profile the job recorded'
        assert client['occurred_at'] is not None
        assert staff['speaker_role'] == 'staff' and staff['evidence_kind'] == 'team_report', 'a staff-spoken result is a team report'
        assert staff['consent_status'] == 'anonymise', 'a relayed result is never cleared for naming'
        assert blocked['consent_status'] == 'do_not_use' and blocked['speaker_role'] == 'unknown', 'a no_use client carries do_not_use'
        assert blocked['evidence_kind'] == 'team_report', 'an unplaced speaker of a result is treated as a relay'
        assert conn.execute("SELECT count(*) n FROM key_moments WHERE tsv @@ websearch_to_tsquery('english','tripled')").fetchone()['n'] == 3
        unverified = [r for r in rows.values() if not r['quote_verified']]
        assert len(unverified) == 1, 'the E.B12a record becomes a row'
        assert unverified[0]['document_id'] == 't1' and unverified[0]['extractor_version'] == '2026-10-18.scenes.v1'
        assert unverified[0]['unverified_reason'].startswith('Moment quote must match') and unverified[0]['evidence_refs'] == []
        assert unverified[0]['moment_body']['quote'] == 'not in the source'
        with pytest.raises(Exception, match='key_moments_unverified_has_no_vector'):
            conn.execute("UPDATE key_moments SET embedding=array_fill(0.1::real, ARRAY[1536])::vector, embedding_model='m', embedding_input_hash='h' WHERE moment_id=%s",
                         (unverified[0]['moment_id'],))
        conn.rollback()
        conn.execute("INSERT INTO topics(topic_id,name) VALUES ('tp1','Lead flow without posting')")
        with pytest.raises(Exception):
            conn.execute("INSERT INTO topics(topic_id,name) VALUES ('tp2','lead flow without posting')")
        conn.rollback()
        # week_id and run_id are optional: a document extracted on its own belongs to no week.
        conn.execute("INSERT INTO key_moments(moment_id,moment_body,evidence_refs,document_id) VALUES ('m_own',%s::jsonb,'[]','t1')", (json.dumps(body),))
        conn.rollback()
    with connect(fresh, vectors=False) as conn:
        assert database.catalog(conn) == database.expected_catalog('008')
    assert migrate(fresh, target='008')['status'] == 'already_current'


def test_a_database_at_008_gets_the_pack_contract_v2_columns_and_the_pack_decision_kind(fresh):
    """NP.B1, migration 009: a database at 008 with a v1 pack rolls forward; the pack keeps its data with no body, a v2 pack's
    body needs its hash, and a decision on a pack is an audited item kind."""
    migrate(fresh, target='008')
    with connect(fresh, vectors=False) as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_2026-06-01','2026-06-01','2026-06-07')")
        conn.execute("INSERT INTO content_packs(pack_id,week_id,title,contract_version) VALUES ('p1','week_2026-06-01','Old','production_pack_v1')")
        conn.commit()
        with pytest.raises(Exception, match='decisions_item_kind_check'):
            conn.execute("INSERT INTO decisions(decision_id,item_kind,item_id,action,actor,author) VALUES ('d1','pack','p1','x','a','a')")
        conn.rollback()
    result = migrate(fresh, target='009')
    assert result['applied'] == ['009'] and result['version'] == '009'
    with connect(fresh, vectors=False) as conn:
        old = conn.execute("SELECT * FROM content_packs WHERE pack_id='p1'").fetchone()
        assert old['title'] == 'Old' and old['content_body'] is None and old['content_hash'] is None, 'a v1 pack keeps its data'
        conn.execute("INSERT INTO decisions(decision_id,item_kind,item_id,action,actor,author) VALUES ('d1','pack','p1','pack_ready','a','a')")
        with pytest.raises(Exception, match='pack_content_has_hash'):
            conn.execute("UPDATE content_packs SET content_body='{}'::jsonb WHERE pack_id='p1'")
        conn.rollback()
        assert database.catalog(conn) == database.expected_catalog('009')
    assert migrate(fresh, target='009')['status'] == 'already_current'


def test_a_database_at_009_gets_identities_team_practice_founder_notes_and_date_evidence(fresh):
    """N8, migration 010: a database at 009 rolls forward with its data; an internal meeting's existing scenes become team
    practice, a client's stay call evidence; a founder note needs its call; a decision on a person is an audited item kind."""
    migrate(fresh, target='009')
    with connect(fresh, vectors=False) as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_2026-06-01','2026-06-01','2026-06-07')")
        for tid, call_type in (('t_team', 'internal'), ('t_call', 'client_1to1')):
            conn.execute("""INSERT INTO transcripts(transcript_id,week_id,source_type,upstream_id,title,original_text,passage_map,content_hash,
                source_metadata,use_restrictions,processing_status,call_type,included,exclusion_reason)
                VALUES (%s,'week_2026-06-01','zoom',%s,%s,'x','[]','h','{}','{}','pending',%s,%s,%s)""",
                         (tid, tid, tid, call_type, call_type != 'internal', 'Internal call' if call_type == 'internal' else None))
            conn.execute("""INSERT INTO key_moments(moment_id,week_id,moment_body,evidence_refs,document_id)
                VALUES (%s,'week_2026-06-01','{}','[]',%s)""", ('m_' + tid, tid))
        conn.execute("INSERT INTO clients(client_id,name) VALUES ('c1','Fernbrook Estate')")
        conn.commit()
    result = migrate(fresh, target='010')
    assert result['applied'] == ['010'] and result['version'] == '010'
    with connect(fresh, vectors=False) as conn:
        classes = {r['moment_id']: r['evidence_class'] for r in conn.execute('SELECT moment_id,evidence_class FROM key_moments')}
        assert classes == {'m_t_team': 'team_practice', 'm_t_call': 'call'}
        client = conn.execute("SELECT do_not_name,do_not_link,status FROM clients WHERE client_id='c1'").fetchone()
        assert client == {'do_not_name': False, 'do_not_link': [], 'status': 'active'}, 'an existing client keeps its data'
        conn.execute("INSERT INTO decisions(decision_id,item_kind,item_id,action,actor,author) VALUES ('d1','person','p1','x','a','a')")
        with pytest.raises(Exception, match='seeds_founder_note_has_call'):
            conn.execute("INSERT INTO seeds(seed_id,kind,text,author,created_by) VALUES ('s1','founder_note','x','a','a')")
        conn.rollback()
        assert database.catalog(conn) == database.expected_catalog('010')
    assert migrate(fresh, target='010')['status'] == 'already_current'


def test_a_database_at_010_gets_the_alerts_table(fresh):
    """N6, migration 011: a database at 010 rolls forward; one open alert per kind and subject, a resolution needs its time."""
    migrate(fresh, target='010')
    result = migrate(fresh, target='011')
    assert result['applied'] == ['011'] and result['version'] == '011'
    with connect(fresh, vectors=False) as conn:
        conn.execute("INSERT INTO alerts(alert_id,kind,subject,severity,message) VALUES ('a1','job_failed','j1','error','x')")
        with pytest.raises(Exception, match='alerts_one_open'):
            conn.execute("INSERT INTO alerts(alert_id,kind,subject,severity,message) VALUES ('a2','job_failed','j1','error','x')")
        conn.rollback()
        with pytest.raises(Exception, match='alerts_resolution_pair'):
            conn.execute("INSERT INTO alerts(alert_id,kind,subject,severity,message,resolution) VALUES ('a3','job_failed','j2','error','x','cleared')")
        conn.rollback()
        assert database.catalog(conn) == database.expected_catalog('011')
    assert migrate(fresh, target='011')['status'] == 'already_current'


def test_011_upgrades_to_slack_delivery_ledger_without_changing_audit_history(fresh):
    from psycopg.errors import UniqueViolation
    migrate(fresh, target='011')
    with connect(fresh, vectors=False) as conn:
        conn.execute("""INSERT INTO pipeline_runs(run_id,run_scope,trigger_type,input_refs)
            VALUES ('audit_run','scheduling','manual','{}')""")
        conn.execute("""INSERT INTO pipeline_events(event_id,run_id,event_type,message)
            VALUES ('existing_event','audit_run','schedule_saved','saved')""")
    upgraded = migrate(fresh)
    assert upgraded['applied'] == ['012'] and upgraded['version'] == '012'
    with connect(fresh, vectors=False) as conn:
        assert conn.execute("SELECT event_id FROM pipeline_events").fetchone()['event_id'] == 'existing_event'
        conn.execute("""INSERT INTO slack_schedule_notifications
            (notification_id,source_event_id,destination,channel_id,status)
            VALUES ('n1','existing_event','email','C0BQ6RW7C84','pending')""")
        with pytest.raises(UniqueViolation):
            with conn.transaction():
                conn.execute("""INSERT INTO slack_schedule_notifications
                    (notification_id,source_event_id,destination,channel_id,status)
                    VALUES ('n2','existing_event','email','C0BQ6RW7C84','pending')""")
        assert database.catalog(conn) == database.expected_catalog('012')
    assert migrate(fresh)['status'] == 'already_current'
