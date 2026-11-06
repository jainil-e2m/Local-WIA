"""1.F1: the OpenAPI document the frontend's types are generated from is current, stable and describes what the app reads."""
import json
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from backend_pipeline import api_models, openapi
from backend_pipeline.knowledge import items

# Every route whose answer the Atelier app reads. Each must publish a schema, so its generated type is not `unknown`.
APP_READS = [
    ('get', '/storage/flags'), ('get', '/storage/me'), ('get', '/storage/weeks'), ('get', '/storage/weeks/{week_id}'),
    ('get', '/storage/moments/{moment_id}'), ('get', '/storage/transcripts/{transcript_id}'), ('get', '/storage/seeds'),
    ('get', '/storage/briefs'), ('get', '/storage/briefs/{brief_id}'), ('get', '/storage/briefs/{brief_id}/versions'),
    ('get', '/storage/angles/{angle_id}/research'), ('get', '/storage/calendar/config'), ('get', '/storage/calendar'),
    ('get', '/storage/packs'), ('get', '/storage/packs/{pack_id}'), ('get', '/storage/packs/{pack_id}/production'),
    ('get', '/storage/context/summary'), ('get', '/storage/context/kinds'), ('get', '/storage/context/queue'),
    ('get', '/storage/context/items'), ('get', '/storage/context/items/{item_id}/history'), ('get', '/storage/context/published'),
    ('get', '/storage/context/versions'), ('get', '/storage/context/versions/{version}/diff'), ('get', '/storage/context/warnings'),
    ('get', '/storage/intake/overview'), ('get', '/storage/intake/sources/{source_id}'), ('get', '/storage/intake/buckets/{bucket_id}'),
    ('get', '/storage/intake/revisions/{revision_id}/original'), ('post', '/storage/intake/search'),
    ('post', '/storage/context/items'), ('post', '/storage/context/items/{item_id}/decision'), ('post', '/storage/context/versions'),
    ('post', '/storage/context/versions/{version}/discard'),
    ('post', '/storage/briefs/{brief_id}/pack'), ('patch', '/storage/briefs/{brief_id}'), ('post', '/storage/briefs/{brief_id}/decision'),
    # Home's cycle summary, the schedule, the alerts and the cost summary on Sources, the week's monitoring (6.F2, 3.B11, 6.F5, 6.B13).
    ('get', '/storage/summary'), ('get', '/storage/schedule'), ('get', '/storage/alerts'), ('post', '/storage/alerts/{alert_id}/dismiss'),
    ('get', '/storage/costs'), ('get', '/storage/weeks/{week_id}/measures'),
]


def spec():
    from backend_pipeline.api import app
    return app.openapi()


def test_the_committed_document_is_the_applications(capsys):
    assert openapi.main(['--check']) == 0, 'backend/openapi.json is stale: run python -m backend_pipeline.openapi --write'


def test_the_document_renders_the_same_bytes_every_time():
    first, second = openapi.current(), openapi.current()
    assert first == second
    assert '\r' not in first and first.endswith('}\n')
    assert json.loads(first) == json.loads(openapi.DOCUMENT.read_bytes())
    assert json.dumps(json.loads(first), indent=2, sort_keys=True) + '\n' == first, 'keys are sorted and indentation is two spaces'


def test_the_committed_file_uses_lf_line_endings():
    assert b'\r' not in openapi.DOCUMENT.read_bytes()


def success_schema(operation):
    codes = [code for code in operation['responses'] if code.startswith('2')]
    assert codes, operation
    return operation['responses'][codes[0]].get('content', {}).get('application/json', {}).get('schema')


def test_every_route_the_app_reads_publishes_a_schema():
    paths = spec()['paths']
    for method, path in APP_READS:
        schema = success_schema(paths[path][method])
        assert schema, f'{method.upper()} {path} publishes no schema; the generated type would be unknown'
        assert schema.get('$ref') or schema.get('anyOf') or schema.get('items'), f'{method.upper()} {path}: {schema}'


def test_the_models_use_the_backends_own_enumerations():
    schemas = spec()['components']['schemas']
    assert schemas['ContextItem']['properties']['kind']['enum'] == list(items.KINDS)
    assert schemas['ContextItem']['properties']['status']['enum'] == list(items.STATUSES)
    assert set(schemas['Capabilities']['properties']) == set(api_models.Capabilities.model_fields)


def test_a_documented_response_is_published_without_being_validated():
    """`returns()` documents the answer; it never filters or fails it (a stored row may lack a field or carry a datetime)."""
    class Strict(api_models.Loose):
        needed: str
        when: str

    documented, plain = FastAPI(), FastAPI()

    def read():
        return {'when': datetime(2026, 10, 18, tzinfo=UTC), 'extra': 1}

    documented.get('/x', responses=api_models.returns(Strict))(read)
    plain.get('/x')(read)
    answer = TestClient(documented).get('/x')
    assert answer.status_code == 200 and answer.json() == TestClient(plain).get('/x').json()
    assert answer.json()['extra'] == 1 and 'needed' not in answer.json()
    published = documented.openapi()['paths']['/x']['get']['responses']['200']['content']['application/json']['schema']
    assert published == {'$ref': '#/components/schemas/Strict'}
    assert issubclass(Strict, BaseModel)
