"""Phase S regressions, all offline: one embedding contract, start-up refusals, brief
validator cases (N2) and Gate 1 approval that does not depend on brief configuration."""
import copy
import json
import re
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend_pipeline import startup
from backend_pipeline.briefs import workflow
from backend_pipeline.briefs.contracts import BriefDocument, Dossier, writer_schema
from backend_pipeline.briefs.runtime import query_space
from backend_pipeline.briefs.validation import checks, numbers
from backend_pipeline.chunk_encoding import VERSION
from backend_pipeline.chunk_encoding import contract as chunk_contract
from backend_pipeline.config import BACKEND_ROOT, EMBEDDING_DIMENSIONS, EMBEDDING_ENDPOINT, EMBEDDING_MODEL, Settings
from backend_pipeline.contracts import ClaimStatus
from backend_pipeline.storage_config import StorageSettings, encoding_contract
from backend_pipeline.store import canonical_hash

OPENAI = {'embedding_base_url': 'https://api.openai.com/v1', 'embedding_model': 'text-embedding-3-small'}


# --- S.B5: one embedding contract -------------------------------------------------

def env_values(path):
    lines = (line.split('=', 1) for line in path.read_text(encoding='utf-8').splitlines()
             if '=' in line and not line.lstrip().startswith('#'))
    return {k.strip(): v.strip() for k, v in lines}


def test_code_default_is_the_openrouter_contract():
    models = Settings()
    assert (models.embedding_base_url, models.embedding_model, models.embedding_dimensions) == (
        'https://openrouter.ai/api/v1', 'openai/text-embedding-3-small', 1536)


@pytest.mark.parametrize('name', ['.env.example', 'intake.env.example', 'storage.env.example'])
def test_every_env_example_declares_the_code_contract(name):
    values = env_values(BACKEND_ROOT / name)
    assert values['EMBEDDING_BASE_URL'] == EMBEDDING_ENDPOINT
    assert values['OPENAI_EMBEDDING_MODEL'] == EMBEDDING_MODEL
    assert values['CONTENT_ATELIER_EMBEDDING_DIMENSIONS'] == str(EMBEDDING_DIMENSIONS)


@pytest.mark.parametrize('synthetic', [False, True])
def test_stage_digests_equal_the_previously_recorded_formulas(synthetic):
    # Stored provenance holds these digests; centralising the contract must not change them.
    models = Settings()
    endpoint, model = models.embedding_base_url.rstrip('/'), models.embedding_model
    assert chunk_contract(models, synthetic=synthetic) == canonical_hash(
        {'endpoint': endpoint, 'model': model, 'dimensions': 1536, 'input': VERSION, 'synthetic': synthetic})
    assert encoding_contract(models, synthetic=synthetic) == canonical_hash(
        {'endpoint': endpoint, 'model': model, 'dimensions': 1536, 'signature': 'six-fields-v1', 'synthetic': synthetic})
    assert query_space(models, synthetic) == {'model': model, 'endpoint': endpoint, 'dimensions': 1536,
                                              'synthetic': synthetic, 'purpose': 'brief-query-v1'}


def test_non_approved_dimensions_are_rejected_everywhere():
    models = Settings(embedding_dimensions=3072)
    for digest in (lambda: chunk_contract(models), lambda: encoding_contract(models), lambda: query_space(models, False)):
        with pytest.raises(ValueError, match='1536'):
            digest()


class FakeConn:
    """Answers the start-up query with the digests recorded for each stage."""
    def __init__(self, chunk=(), signature=(), moment=()):
        self.recorded = {'transcript_chunk_embedding': set(chunk), 'angle_embedding': set(signature), 'moment_embedding': set(moment)}

    def execute(self, query, params=None):
        stage = next((s for s in ('transcript_chunk_embedding', 'moment_embedding') if s in query), 'angle_embedding')
        return [{'digest': d} for d in self.recorded[stage]]


def test_matching_or_empty_archive_starts(monkeypatch):
    monkeypatch.delenv(startup.OVERRIDE, raising=False)
    models = Settings()
    startup.check_embedding_contract(FakeConn(), models, False)
    startup.check_embedding_contract(FakeConn([chunk_contract(models)], [encoding_contract(models)]), models, False)
    # Older contracts alongside the current one do not block.
    old = models.model_copy(update=OPENAI)
    startup.check_embedding_contract(FakeConn([chunk_contract(old), chunk_contract(models)]), models, False)


def test_mismatched_contract_refuses_to_start_and_names_both(monkeypatch):
    monkeypatch.delenv(startup.OVERRIDE, raising=False)
    archive = Settings()
    process = archive.model_copy(update=OPENAI)
    with pytest.raises(startup.StartupError) as raised:
        startup.check_embedding_contract(FakeConn([chunk_contract(archive)]), process, False)
    message = str(raised.value)
    assert 'transcript chunks' in message
    assert 'This process uses endpoint=https://api.openai.com/v1 model=text-embedding-3-small' in message
    assert 'encoded with endpoint=https://openrouter.ai/api/v1 model=openai/text-embedding-3-small' in message
    assert 'EMBEDDING_BASE_URL' in message and startup.OVERRIDE in message
    with pytest.raises(startup.StartupError, match='angle signatures'):
        startup.check_embedding_contract(FakeConn(signature=[encoding_contract(archive)]), process, False)
    with pytest.raises(startup.StartupError, match='unrecognised contract, digests abc'):
        startup.check_embedding_contract(FakeConn(['abc']), process, False)


def test_moment_vectors_are_part_of_the_start_up_contract_check(monkeypatch):
    from backend_pipeline.moments.embedding import contract as moment_contract
    monkeypatch.delenv(startup.OVERRIDE, raising=False)
    archive = Settings()
    process = archive.model_copy(update=OPENAI)
    startup.check_embedding_contract(FakeConn(moment=[moment_contract(archive)]), archive, False)
    with pytest.raises(startup.StartupError, match='moments'):
        startup.check_embedding_contract(FakeConn(moment=[moment_contract(archive)]), process, False)


def test_reencoding_override_and_wrong_dimensions(monkeypatch):
    archive, process = Settings(), Settings().model_copy(update=OPENAI)
    monkeypatch.setenv(startup.OVERRIDE, 'true')
    startup.check_embedding_contract(FakeConn([chunk_contract(archive)]), process, False)
    monkeypatch.delenv(startup.OVERRIDE)
    with pytest.raises(startup.StartupError, match='CONTENT_ATELIER_EMBEDDING_DIMENSIONS=1536'):
        startup.check_embedding_contract(FakeConn(), Settings(embedding_dimensions=3), False)


def fake_repository(monkeypatch, attempts):
    """ContentRepository whose connection follows `attempts`: an exception to raise, or a connection to yield."""
    import psycopg
    from backend_pipeline import repository
    calls = []

    class Repo:
        def __init__(self, storage):
            pass

        @contextmanager
        def connection(self):
            outcome = attempts[min(len(calls), len(attempts) - 1)]
            calls.append(outcome)
            if isinstance(outcome, Exception):
                raise outcome
            yield outcome
    monkeypatch.setattr(repository, 'ContentRepository', Repo)
    return calls, psycopg.OperationalError('connection refused')


def test_an_unreachable_database_is_waited_for_then_refuses_the_start(monkeypatch):
    """S.B5: a process that never checked its contract could encode or search under another one."""
    monkeypatch.delenv(startup.OVERRIDE, raising=False)
    monkeypatch.setenv(startup.DATABASE_WAIT, '5')
    import psycopg
    down = psycopg.OperationalError('connection refused')
    calls, _ = fake_repository(monkeypatch, [down])
    now, slept = [0.0], []
    def sleep(seconds):
        slept.append(seconds); now[0] += seconds
    with pytest.raises(startup.StartupError, match='Database unavailable at start-up'):
        startup.verify(StorageSettings(), Settings(), briefs=False, sleep=sleep, clock=lambda: now[0])
    assert len(calls) > 1 and slept, 'it retried before refusing'
    # A database that comes up within the wait is checked, and the process starts.
    monkeypatch.setattr(startup, 'recorded_version', lambda conn: startup.LATEST)
    calls, down = fake_repository(monkeypatch, [down, FakeConn()])
    now[0] = 0.0
    startup.verify(StorageSettings(), Settings(), briefs=False, sleep=sleep, clock=lambda: now[0])
    assert len(calls) == 2


@pytest.mark.parametrize('version', [None, '005', '010', '012'])  # 010: behind (011 is this code's latest); 012: ahead
def test_the_api_refuses_a_database_not_at_this_codes_migration(monkeypatch, version):
    """Below 006 Gate 1 decisions, seeds and the context store silently do nothing; the start is refused."""
    monkeypatch.delenv(startup.OVERRIDE, raising=False)
    monkeypatch.setattr(startup, 'recorded_version', lambda conn: version)
    fake_repository(monkeypatch, [FakeConn()])
    with pytest.raises(startup.StartupError, match='storage_cli migrate'):
        startup.verify(StorageSettings(), Settings(), briefs=False)
    # The intake worker, whose database the intake runner migrates, checks the contract only.
    startup.verify(StorageSettings(), Settings(), briefs=False, schema=False)


def test_api_refuses_to_start_when_a_check_fails(monkeypatch):
    from backend_pipeline import api
    def refuse(*args, **kwargs):
        raise startup.StartupError('Embedding contract differs from the stored transcript chunks')
    monkeypatch.setattr(startup, 'verify', refuse)
    with pytest.raises(startup.StartupError, match='Embedding contract differs'), TestClient(api.app):
        pass


# --- S.B13: brief configuration ----------------------------------------------------

def bundle(tmp_path, **changes):
    path = tmp_path / 'brand.json'
    path.write_text(json.dumps({'status': 'approved', 'approved_by': 'founder@example.test', 'voice': ['Plain'],
                                'strategy': ['Decide'], 'cta_rules': ['Exact CTA'], 'exemplars': [], **changes}), encoding='utf-8')
    return path


def test_briefs_enabled_requires_a_reviewed_bundle(tmp_path):
    startup.check_brief_configuration(StorageSettings(brief_enabled=False))
    startup.check_brief_configuration(StorageSettings(brief_enabled=True, brief_brand_path=bundle(tmp_path)))
    startup.check_brief_configuration(StorageSettings(brief_enabled=True, synthetic=True))
    for settings in (StorageSettings(brief_enabled=True),
                     StorageSettings(brief_enabled=True, brief_brand_path=tmp_path / 'missing.json'),
                     StorageSettings(brief_enabled=True, brief_brand_path=bundle(tmp_path, status='pending_review'))):
        with pytest.raises(startup.StartupError, match='ATELIER_BRIEFS_ENABLED=true requires ATELIER_BRAND_BUNDLE_PATH'):
            startup.check_brief_configuration(settings)
    (tmp_path / 'broken.json').write_text('{', encoding='utf-8')
    with pytest.raises(startup.StartupError, match='broken.json'):
        startup.check_brief_configuration(StorageSettings(brief_enabled=True, brief_brand_path=tmp_path / 'broken.json'))


class QueueConn:
    """Records statements; transaction() is the savepoint the approval survives."""
    def __init__(self):
        self.statements, self.savepoints = [], []

    @contextmanager
    def transaction(self):
        self.savepoints.append('open')
        try:
            yield
        except Exception:
            self.savepoints[-1] = 'rolled_back'
            raise
        self.savepoints[-1] = 'released'

    def execute(self, query, params=None):
        self.statements.append((query, params))
        class Result:
            def fetchone(self_inner):
                return {'week_id': 'week_2026-06-01'} if 'FROM content_angles' in str(query) else None

            def fetchall(self_inner):
                return []
        return Result()


class QueueRepo:
    def __init__(self, settings):
        self.settings, self.events = settings, []

    def event(self, conn, run_id, kind, message, **kwargs):
        self.events.append((run_id, kind, message, kwargs))


def packet(conn, angle_id):
    return {'angle_id': angle_id, 'week_id': 'week_2026-06-01', 'approved_hash': 'hash'}


def test_gate_one_queue_records_a_failed_run_instead_of_raising(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, 'angle_packet', packet)
    repo = QueueRepo(StorageSettings(brief_enabled=True, brief_brand_path=tmp_path / 'missing.json'))
    conn = QueueConn()
    # Exactly the call gate_one.py makes inside its approval transaction.
    result = workflow.queue_in_transaction(repo, conn, 'angle_1', 'approver@example.test', 'replay')
    assert result['status'] == 'failed' and result['run_id'].startswith('brief_run_unqueued_')
    assert 'missing.json' in result['error']
    assert conn.savepoints == ['rolled_back']
    inserted = [p for q, p in conn.statements if 'INSERT' in str(q)]
    assert len(inserted) == 1
    record = dict(zip(['run_id', 'week_id', 'run_scope', 'status', 'error_summary'], inserted[0]))
    assert record['run_scope'] == 'brief_generation' and record['status'] == 'failed'
    assert 'missing.json' in record['error_summary']
    assert repo.events[0][1] == 'brief_queue_failed' and repo.events[0][3]['severity'] == 'error'


def test_v2_briefs_read_the_knowledge_base_not_a_separate_bundle(tmp_path, monkeypatch):
    """E.B11 (f), V3: one brand source. A v2 brief takes its brand context from the knowledge base (pinned in the run's
    execution contract and the brief header), so neither start-up nor queueing needs the version 1 brand bundle."""
    v2 = dict(brief_enabled=True, brief_schema='brief_document_v2')
    startup.check_brief_configuration(StorageSettings(**v2))
    startup.check_brief_configuration(StorageSettings(**v2, brief_brand_path=tmp_path / 'missing.json'))
    monkeypatch.setattr(workflow, 'angle_packet', packet)
    monkeypatch.setattr(workflow, 'snapshot_refs', lambda *a, **k: {})
    conn = QueueConn()
    result = workflow.queue_in_transaction(QueueRepo(StorageSettings(**v2)), conn, 'angle_1', 'approver@example.test', 'replay')
    assert result['status'] == 'queued', result
    run = next(p for q, p in conn.statements if 'INSERT' in str(q) and 'pipeline_runs' in str(q))
    refs = next(v.obj for v in run if isinstance(getattr(v, 'obj', None), dict) and 'workflow' in v.obj)  # the Jsonb input_refs
    assert refs['brand']['source'] == 'knowledge_base' and refs['schema_version'] == 'brief_document_v2'
    with pytest.raises(FileNotFoundError):  # version 1 still reads its reviewed bundle
        workflow.queue_in_transaction(QueueRepo(StorageSettings(brief_enabled=True, brief_brand_path=tmp_path / 'missing.json')),
                                      QueueConn(), 'angle_1', 'a', 'replay', on_failure='raise')


def test_explicit_queue_and_revisions_still_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, 'angle_packet', packet)
    repo = QueueRepo(StorageSettings(brief_enabled=True, brief_brand_path=tmp_path / 'missing.json'))
    with pytest.raises(FileNotFoundError):
        workflow.queue_in_transaction(repo, QueueConn(), 'angle_1', 'a', 'replay', on_failure='raise')
    with pytest.raises(FileNotFoundError):
        workflow.queue_in_transaction(repo, QueueConn(), 'angle_1', 'a', 'replay', revision='brief_1', instructions='Revise')


# --- S.B4: brief validator ---------------------------------------------------------

ANGLE = {'angle_id': 'angle_current', 'week_id': 'week_2026-06-01', 'approved_hash': 'h',
         'body': {'argument': 'Review follow-up before claiming a result', 'audience': 'Wedding business owners',
                  'reader_decision': 'Choose a bounded review'}, 'cta': {'text': 'Book a review call'}}


def evidence_item(evidence_id, status='reported', role='anchor'):
    return {'evidence_id': evidence_id, 'excerpt': 'We improved the follow-up. It was not measured.', 'title': 'Call',
            'role': role, 'qualifications': ['Not measured'], 'claim_status': status}


def dossier(prior_ids=('angle_prior_1',), status='reported'):
    prior = [{'angle_id': p, 'argument': 'An earlier argument', 'audience': 'Owners', 'mechanism': 'Mechanism',
              'approval_status': 'approved', 'cosine': 0.5, 'discovery': [], 'briefs': [], 'publications': [],
              'content_hash': 'c'} for p in prior_ids]
    return Dossier.model_validate({'angle': ANGLE, 'evidence': [evidence_item('ev_1', status)], 'prior': prior,
                                   'queries': [], 'coverage': {}, 'gaps': [], 'audit': [], 'brand': {'hash': 'b'}})


def document(d):
    direction = {'reader_job': 'Understand the decision', 'direction': 'Explain the reported observation.',
                 'outline': ['Name the uncertainty', 'Explain the mechanism', 'Ask for a bounded review'], 'evidence_ids': ['ev_1']}
    return {'title': 'A bounded follow-up review', 'angle_statement': ANGLE['body']['argument'],
            'audience': ANGLE['body']['audience'], 'reader_decision': ANGLE['body']['reader_decision'],
            'reader_promise': 'Understand how to review follow-up.', 'positioning': None,
            'why_now': 'The observation raises a current question.', 'core_insight': 'A reported improvement is not proof.',
            'message_spine': ['Inspect', 'Retain the limitation', 'Choose a review'], 'audience_pain': 'Uncertainty',
            'narrative': ['Explain the observation without causal certainty.'], 'evidence_boundaries': ['Not measured.'],
            'claims': [{'claim_id': 'C1', 'text': 'An improvement in follow-up was reported.', 'kind': 'source_assertion',
                        'evidence_ids': ['ev_1'], 'source_status': 'reported', 'qualifications': ['Not measured'],
                        'quote': None, 'public_quote': False, 'numeric_facts': []}],
            'differentiation': 'Focus on the review decision.',
            'prior_differences': {p.angle_id: 'Develop the decision, not the outcome.' for p in d.prior},
            'voice': ['Plain language'], 'email': direction, 'carousel_reader_job': 'Apply a bounded review',
            'carousel': [{'number': i, 'direction': 'Explain a review step.', 'evidence_ids': ['ev_1']} for i in range(1, 9)],
            'reels': [{**direction, 'reader_job': r} for r in ('Recognise', 'Understand', 'Decide')],
            'cta': ANGLE['cta'], 'creative_direction': ['Clear flow'], 'accessibility': ['Captions'],
            'distribution': ['Editorial channels'], 'evaluation_signals': ['Comprehension'],
            'similarity_review': 'Legacy publication coverage is incomplete.', 'claims_requiring_consent': [],
            'open_questions': [{'question_id': 'Q1', 'text': 'Which channel leads?', 'required': True, 'answer': None}],
            'sources': ['ev_1'], 'handoff_checklist': ['Preserve qualifications']}


def blocking(doc, d):
    return [f['message'] for f in checks(doc, d) if f['severity'] == 'blocking']


def test_baseline_fixture_has_no_blocking_findings():
    d = dossier()
    assert blocking(document(d), d) == []


def test_probe_from_the_plan_no_longer_blocks():
    # "[C1]", "Slide 1", "step 1", and an extra prior_differences key (the prose status is covered below).
    d = dossier(); doc = document(d)
    doc['narrative'] = ['The reported change [C1] is a starting point, not proof [C1, Q1].']
    doc['carousel'][0]['direction'] = 'Slide 1 of 8: name the uncertainty.'
    doc['email']['outline'][0] = 'In step 1, name the uncertainty; steps 2-3 explain it.'
    doc['why_now'] = 'Week 2 of the series follows the week 1 observation.'
    doc['claims'][0]['text'] = 'An improvement in follow-up was reported [C1].'
    doc['prior_differences']['exemplar_angle_9'] = 'Extra commentary'
    findings = checks(doc, d)
    assert [f['message'] for f in findings if f['severity'] == 'blocking'] == []
    assert any('exemplar_angle_9' in f['message'] for f in findings if f['severity'] == 'warning')


@pytest.mark.parametrize('field,value', [
    ('narrative', ['Follow-up improved by 40 percent.']),
    ('why_now', ['Slide 1 says 3 of 4 couples asked.']),
    ('email', ['Reply within 24 hours [C1].'])])
def test_quantities_next_to_labels_and_numbering_still_block(field, value):
    d = dossier(); doc = document(d)
    if field == 'email': doc['email']['direction'] = value[0]
    elif field == 'why_now': doc['why_now'] = value[0]
    else: doc[field] = value
    assert any('Numerical prose' in m for m in blocking(doc, d))
    doc = document(d); doc['claims'][0]['text'] = 'Follow-up improved by 40 percent [C1].'
    assert any('Numerical factual claim' in m for m in blocking(doc, d))


def test_number_scan_ignores_identifiers_labels_and_format_numbering():
    assert numbers('See [C3] and [claim_2; E4] in Slide 2 of 8, slides 3-4, Step 1, week 2, evidence ev_17.', {'ev_17'}) == set()
    assert numbers('Three weeks: 3 weeks and 40 percent, slide 2 shows 5 couples.') == {'3', '40', '5'}


def test_writer_schema_sends_the_six_status_enum():
    status = BriefDocument.model_json_schema()['$defs']['Claim']['properties']['source_status']
    assert status['enum'] == ['reported', 'measured', 'estimated', 'planned', 'hypothetical', 'inferred']
    assert set(status['enum']) == set(ClaimStatus.__args__)
    d = dossier(); doc = document(d)
    doc['claims'][0]['source_status'] = 'reported by the venue owner'
    with pytest.raises(ValidationError):
        BriefDocument.model_validate(doc)


def test_stored_prose_status_is_reported_not_raised():
    d = dossier(); doc = document(d)
    doc['claims'][0]['source_status'] = 'reported by the venue owner'
    original = copy.deepcopy(doc)
    messages = blocking(doc, d)
    assert messages == ['Claim status must be one of: reported, measured, estimated, planned, hypothetical, inferred']
    assert doc == original


def test_an_invalid_status_is_not_also_compared_with_its_sources():
    """The real Week 2 v1 brief: "Planned proposal; public reuse not cleared" on planned evidence gave a second finding,
    'exceeds the source status', computed from the placeholder status, not from what the brief says (S.B4, 19 October)."""
    d = dossier(status='planned'); doc = document(d)
    doc['claims'][0]['source_status'] = 'Planned proposal; public reuse not cleared'
    assert blocking(doc, d) == ['Claim status must be one of: reported, measured, estimated, planned, hypothetical, inferred']


def test_a_widened_qualification_is_kept_and_a_dropped_part_is_lost():
    """The real Week 2 v1 brief widened a caveat ("no client adoption, response rate, messaging change or marketing result");
    an exact-string match called it lost. Every content word kept is enough; dropping part of it still blocks."""
    d = dossier(); d.evidence[0].qualifications = ['No client adoption, response rate, or marketing result is reported.']
    doc = document(d)
    doc['claims'][0]['qualifications'] = ['No client adoption, response rate, messaging change or marketing result is reported.']
    assert blocking(doc, d) == []
    doc['claims'][0]['qualifications'] = ['No adoption or marketing result is established.']
    assert blocking(doc, d) == ['Source qualifications were lost']
    doc['claims'][0]['qualifications'] = []
    assert blocking(doc, d) == ['Source qualifications were lost']


def test_unknown_source_status_supports_only_reported():
    d = dossier(status='unknown'); doc = document(d)
    assert blocking(doc, d) == []
    doc['claims'][0]['source_status'] = 'measured'
    assert blocking(doc, d) == ['Claim status exceeds the source status']


def test_prior_differences_limited_to_supplied_prior_angles():
    schema = writer_schema(['angle_prior_2', 'angle_prior_1', 'angle_prior_1'])['properties']['prior_differences']
    assert schema['required'] == ['angle_prior_1', 'angle_prior_2'] and list(schema['properties']) == schema['required']
    assert schema['additionalProperties'] is False
    assert writer_schema([])['properties']['prior_differences']['required'] == []
    # Every other part of the writer schema is the BriefDocument contract.
    full = BriefDocument.model_json_schema()
    narrowed = writer_schema(['a'])
    assert {k: v for k, v in narrowed['properties'].items() if k != 'prior_differences'} == {
        k: v for k, v in full['properties'].items() if k != 'prior_differences'}
    d = dossier(('angle_prior_1', 'angle_prior_2')); doc = document(d)
    del doc['prior_differences']['angle_prior_2']
    assert any('Prior coverage differences' in m for m in blocking(doc, d))


def test_prompt_states_the_status_and_prior_key_rules():
    text = (Path(workflow.__file__).resolve().parent.parent / 'prompt_templates' / 'brief_write.v1.md').read_text(encoding='utf-8')
    assert re.search(r'source_status is one of the six status values', text)
    assert 'keyed in prior_differences by exactly the supplied prior angle IDs' in text


def test_writer_dossier_carries_no_exemplars_beside_the_prior_set():
    from backend_pipeline.briefs.runtime import compact_dossier
    dossier = {'angle': {'angle_id': 'a'}, 'evidence': [], 'prior': [{'angle_id': 'angle_prior', 'argument': 'Earlier'}],
               'queries': [], 'coverage': {}, 'gaps': [], 'audit': [{'step': 1}],
               'brand': {'hash': 'bundle-hash', 'documents': {'voice': ['Plain'], 'exemplars': [{'title': 'Old angle'}]}}}
    compact = compact_dossier(dossier)
    assert compact['prior'] == dossier['prior']
    assert 'exemplars' not in compact['brand']['documents'] and compact['brand']['documents']['voice'] == ['Plain']
    assert compact['brand']['hash'] == 'bundle-hash' and 'audit' not in compact
    assert dossier['brand']['documents']['exemplars'], 'the stored dossier is not changed'


# --- S.B11: feature flags reach the frontend ----------------------------------------

def test_flags_route_reports_each_switch():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend_pipeline.storage_api import router
    for briefs, packs, calendar, context in [(False, False, False, False), (True, False, False, False), (True, True, True, True)]:
        settings = StorageSettings(api_secret='s', brief_enabled=briefs, packs_enabled=packs, calendar_enabled=calendar,
                                   context_enabled=context)
        app = FastAPI()
        app.include_router(router(settings))
        client = TestClient(app)
        assert client.get('/storage/flags').status_code == 401
        answer = client.get('/storage/flags', headers={'authorization': 'Bearer s', 'x-atelier-actor': 'a@example.invalid'}).json()
        assert answer == {'briefs': briefs, 'packs': packs, 'calendar': calendar, 'context': context}


# --- S.B7: experiment code stays out of the package and the image -------------------

def test_experiment_harnesses_live_outside_the_shipped_package():
    from pathlib import Path
    backend = Path(__file__).resolve().parents[2]
    moved = ('model_experiment', 'reviewed_experiment', 'handbook_testing', 'handbook_contracts')
    assert not [m for m in moved if (backend / 'backend_pipeline' / f'{m}.py').exists()]
    assert all((backend / 'experiments' / f'{m}.py').is_file() for m in moved)
    # The image copies only what .dockerignore re-includes: the package (minus tests) and migrations.
    allowed = [line.strip() for line in (backend / '.dockerignore').read_text(encoding='utf-8').splitlines()
               if line.strip().startswith('!')]
    assert not [line for line in allowed if 'experiments' in line or 'scripts' in line or 'evaluation' in line]
    dockerfile = (backend / 'Dockerfile').read_text(encoding='utf-8')
    assert 'COPY experiments' not in dockerfile and 'COPY scripts' not in dockerfile


def test_experiment_harnesses_still_import():
    import importlib
    for name in ('experiments.model_experiment', 'experiments.reviewed_experiment', 'experiments.handbook_testing'):
        module = importlib.import_module(name)
        assert module.__name__ == name
    from experiments.model_experiment import runtime_identity
    assert set(runtime_identity()) >= {'model_experiment.py', 'pipeline.py'}


# --- S.B8: live briefs name their models ---------------------------------------------

def test_live_briefs_refuse_to_fall_back_to_the_angle_model():
    from types import SimpleNamespace
    from backend_pipeline.briefs.runtime import require_live_models
    def worker(brief=None, review=None):
        return SimpleNamespace(storage=SimpleNamespace(brief_model=brief, brief_review_model=review))
    live, replay = {'input_refs': {'mode': 'live'}}, {'input_refs': {'mode': 'replay'}}
    require_live_models(worker(), replay, 'brief_write')
    with pytest.raises(ValueError, match='ATELIER_BRIEF_MODEL'):
        require_live_models(worker(review='anthropic/claude-sonnet-5.5'), live, 'brief_write')
    with pytest.raises(ValueError, match='ATELIER_BRIEF_REVIEW_MODEL'):
        require_live_models(worker(brief='openai/gpt-6.1-sol'), live, 'brief_review')
    require_live_models(worker('openai/gpt-6.1-sol', 'anthropic/claude-sonnet-5.5'), live, 'brief_plan')
