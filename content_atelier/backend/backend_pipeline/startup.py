"""Start-up checks for the API and workers. A misconfigured process refuses to start.

Two configurations fail silently at run time, so they are checked before serving:
- an embedding contract that differs from the one the stored vectors were encoded
  under (research then rejects the whole archive), and
- briefs enabled without a reviewed brand bundle (Gate 1 approval then cannot
  queue its brief).
"""
from __future__ import annotations

import logging
import os
import time

import psycopg
from psycopg.errors import UndefinedTable

from .config import EMBEDDING_ENDPOINT, EMBEDDING_MODEL, Settings, embedding_contract
from .database import LATEST, recorded_version
from .storage_config import StorageSettings, encoding_contract

log = logging.getLogger(__name__)

# Set only while deliberately re-encoding the archive under a new contract.
OVERRIDE = 'ATELIER_ALLOW_EMBEDDING_CONTRACT_CHANGE'
# How long a starting process waits for the database before refusing to start (S.B5).
DATABASE_WAIT = 'ATELIER_STARTUP_DATABASE_WAIT_SECONDS'

# Jobs whose result_refs record the digest of the contract their vectors used.
_STAGES = {
    'transcript chunks': ("stage='transcript_chunk_embedding'", 'chunk'),
    'angle signatures': ("stage IN ('angle_embedding','angle_initial_embedding','angle_refined_embedding')", 'signature'),
    'moments': ("stage='moment_embedding'", 'moment'),
}

# Endpoint/model pairs seen in this project's history, used only to name the
# archive's contract in the refusal message (SQL records the digest alone).
_KNOWN = [(EMBEDDING_ENDPOINT, EMBEDDING_MODEL), ('https://api.openai.com/v1', 'text-embedding-3-small'),
          (EMBEDDING_ENDPOINT, 'text-embedding-3-small'), ('https://api.openai.com/v1', EMBEDDING_MODEL)]


class StartupError(RuntimeError):
    pass


def _digest(kind, models, synthetic):
    from .chunk_encoding import contract as chunk_contract
    if kind == 'moment':
        from .moments.embedding import contract as moment_contract
        return moment_contract(models, synthetic=synthetic)
    return chunk_contract(models, synthetic=synthetic) if kind == 'chunk' else encoding_contract(models, synthetic=synthetic)


def _describe(models):
    c = embedding_contract(models)
    return f"endpoint={c['endpoint']} model={c['model']} dimensions={c['dimensions']}"


def check_embedding_contract(conn, models, synthetic):
    """Refuse a process whose embedding contract matches none of the archive's recorded ones."""
    if os.getenv(OVERRIDE) == 'true':
        log.warning('%s=true: embedding contract check skipped for deliberate re-encoding', OVERRIDE)
        return
    try:
        embedding_contract(models)
    except ValueError as exc:
        raise StartupError(f'{exc}. Set CONTENT_ATELIER_EMBEDDING_DIMENSIONS=1536.') from exc
    for label, (where, kind) in _STAGES.items():
        recorded = {r['digest'] for r in conn.execute(
            f"SELECT DISTINCT result_refs->>'contract' AS digest FROM pipeline_jobs WHERE {where} "
            "AND status='completed' AND result_refs ? 'contract'")}
        if not recorded:
            continue  # Nothing encoded yet: any contract can start the archive.
        current = _digest(kind, models, synthetic)
        if current in recorded:
            continue
        known = [f'endpoint={e} model={m}' for e, m in _KNOWN
                 if _digest(kind, models.model_copy(update={'embedding_base_url': e, 'embedding_model': m}), synthetic) in recorded]
        archive = ('; '.join(known) + ' (dimensions=1536)') if known else 'an unrecognised contract, digests ' + ', '.join(sorted(recorded))
        raise StartupError(
            f'Embedding contract differs from the stored {label}. This process uses {_describe(models)}; '
            f'the {label} were encoded with {archive}. Set EMBEDDING_BASE_URL and OPENAI_EMBEDDING_MODEL to the '
            f'archive\'s values, or set {OVERRIDE}=true only while deliberately re-encoding the archive.')


def check_brief_configuration(storage):
    """ATELIER_BRIEFS_ENABLED=true with the version 1 contract requires a reviewed brand bundle at
    ATELIER_BRAND_BUNDLE_PATH. Version 2 and 3 briefs read the knowledge base instead (E.B11 f), checked when a run starts;
    their writer prompt must be one the contract accepts (E.B23)."""
    from .briefs.contracts_v2 import SCHEMA_V2
    from .briefs.contracts_v3 import SCHEMA_V3
    from .briefs.contracts_v4 import SCHEMA_V4
    if storage.brief_enabled and storage.brief_schema in (SCHEMA_V2, SCHEMA_V3, SCHEMA_V4):
        from .settings_store import brief_writer_problem
        if problem := brief_writer_problem(storage.brief_schema, storage.brief_writer):
            raise StartupError(problem)
    if not storage.brief_enabled or storage.brief_schema in (SCHEMA_V2, SCHEMA_V3, SCHEMA_V4):
        return
    from .briefs.runtime import brand_bundle
    try:
        brand_bundle(storage)
    except (OSError, ValueError) as exc:
        where = storage.brief_brand_path or 'unset'
        raise StartupError(f'ATELIER_BRIEFS_ENABLED=true requires ATELIER_BRAND_BUNDLE_PATH to name a reviewed brand '
                           f'bundle (path: {where}): {exc}. Fix the bundle or set ATELIER_BRIEFS_ENABLED=false.') from exc


def check_settings(*loaded):
    """Refuse to start when a settings row (read when the settings were loaded) fails its type or range: a hand-edited
    row would otherwise be ignored and the process would silently run on the environment or the default (0.B8)."""
    problems = [p for s in loaded for p in (getattr(getattr(s, '_effective', None), 'problems', None) or [])]
    if problems:
        raise StartupError('The settings table holds invalid rows, which are ignored until fixed: ' + '; '.join(sorted(set(problems)))
                           + '. Correct them with `storage_cli settings set` or remove them with `settings unset`.')


def check_schema(conn):
    """Refuse a database that is not at this code's migration (0.B3): below it, Gate 1 decisions, seeds and the
    context store silently do nothing; above it, this code is older than the schema."""
    version = recorded_version(conn)
    if version != LATEST:
        raise StartupError(f'The database is at migration {version or "004 or earlier"}; this code needs {LATEST}. '
                           'Run python -m backend_pipeline.storage_cli migrate (or deploy the matching code).')


def verify(storage=None, models=None, *, briefs=True, schema=True, sleep=time.sleep, clock=time.monotonic):
    """Run every start-up check, or refuse to start.

    The embedding contract is checked against the database, so a database that cannot be reached is waited for (up to
    ATELIER_STARTUP_DATABASE_WAIT_SECONDS, default 60) and then refuses the start: a process that never checked could
    encode or search under a different contract (S.B5). `schema` (the API and the editorial worker) also requires the
    latest migration; the intake worker, whose database is migrated by the intake runner, checks the contract only.
    """
    storage = storage or StorageSettings.from_env()
    models = models or Settings.from_env()
    check_settings(storage, models)
    if briefs:
        check_brief_configuration(storage)
    from .repository import ContentRepository
    deadline = clock() + float(os.getenv(DATABASE_WAIT, '60'))
    while True:
        try:
            with ContentRepository(storage).connection() as conn:
                if schema:
                    check_schema(conn)
                try:
                    check_embedding_contract(conn, models, storage.synthetic)
                except UndefinedTable:
                    # Only reachable without the schema check: no jobs table means nothing has been encoded.
                    log.warning('Storage schema is not initialised; nothing encoded, so any embedding contract may start')
            return
        except psycopg.OperationalError as exc:
            if clock() >= deadline:
                raise StartupError(f'Database unavailable at start-up, so the embedding contract cannot be verified; '
                                   f'refusing to start (waited {os.getenv(DATABASE_WAIT, "60")} s, {DATABASE_WAIT}): {exc}') from exc
            log.warning('Database unavailable at start-up; retrying the embedding contract check: %s', exc)
            sleep(2)
