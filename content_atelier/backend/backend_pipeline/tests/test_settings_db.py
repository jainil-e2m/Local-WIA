"""0.B8 "done when" on the migrated database: changing a setting changes behaviour without a deploy or any environment
change, and the run's snapshot shows it; unsetting restores the default. Also: import-env, the command line, the routes,
the knowledge-base pin, and the live-mode model rule. Synthetic fixtures; no provider is called."""
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import gate_one, settings_store, startup
from backend_pipeline.angle_profiles import STRATEGIST_V5_PROFILE
from backend_pipeline.briefs import workflow as brief_workflow
from backend_pipeline.config import BACKEND_ROOT, Settings
from backend_pipeline.database import connect
from backend_pipeline.knowledge import assembly, compiler, items
from backend_pipeline.repository import ContentRepository
from backend_pipeline.settings_store import SettingError
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_brief_v2_db import v2  # noqa: F401 (fixture)
from backend_pipeline.tests.test_cards_sql import W1, W2

WRITER = "test/table-brief-writer"


@pytest.fixture
def database(platform_url, tmp_path, monkeypatch):  # noqa: F811
    """The migrated database, emptied, named by ATELIER_DATABASE_URL like a deployed process; no other variable set."""
    from backend_pipeline.tests.platform_db import empty
    empty(platform_url)
    for name in [d.env[0] for d in settings_store.DEFINITIONS if d.env and d.table]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ATELIER_DATABASE_URL", platform_url)
    monkeypatch.setenv("ATELIER_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ATELIER_SYNTHETIC_DATABASE", "true")
    settings_store.invalidate()
    return platform_url


def change(url, key, value, actor="tester"):
    with connect(url, vectors=False) as conn:
        result = settings_store.set_value(conn, key, value, actor)
        conn.commit()
    return result


def remove(url, key, actor="tester"):
    with connect(url, vectors=False) as conn:
        result = settings_store.unset_value(conn, key, actor)
        conn.commit()
    return result


def refs_of(repo, run_id):
    with repo.connection() as conn:
        return conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (run_id,)).fetchone()["input_refs"]


# The done-when: a row changes behaviour, the run's snapshot shows it, unsetting restores the default ----------------


def test_a_row_changes_the_model_the_profile_and_the_effort_without_any_environment_change(database, monkeypatch):
    before = Settings.from_env()
    assert before.angle_prompt_profile == "2026-10-19.reel-editorial.v2" and before.openrouter_angle_generation_model is None
    change(database, "prompts.profile.strategist", STRATEGIST_V5_PROFILE)
    change(database, "models.angle_generation", "table/strategist")
    change(database, "models.reasoning_effort.angle_generation", "low")
    after = Settings.from_env()  # the same process, the same environment
    assert after.angle_prompt_profile == STRATEGIST_V5_PROFILE
    assert after.model_for("angle_generation") == "table/strategist" and after.reasoning_effort_for("angle_generation") == "low"
    assert after.reasoning_effort_for("moment_extraction") == "high", "the default effort for every other stage"
    assert after.setting_sources["models.angle_generation"] == "table"
    for key in ("prompts.profile.strategist", "models.angle_generation", "models.reasoning_effort.angle_generation"):
        remove(database, key)
    restored = Settings.from_env()
    assert restored.angle_prompt_profile == before.angle_prompt_profile and restored.model_for("angle_generation") == before.model_for("angle_generation")
    assert restored.setting_sources["models.angle_generation"] == "default"


def test_a_row_beats_the_old_environment_variable_and_unsetting_returns_to_it(database, monkeypatch):
    monkeypatch.setenv("OPENROUTER_ANGLE_GENERATION_MODEL", "env/strategist")
    monkeypatch.setenv("CONTENT_ATELIER_ANGLE_PROMPT_PROFILE", STRATEGIST_V5_PROFILE)
    assert Settings.from_env().model_for("angle_generation") == "env/strategist", "a deployment with variables changes nothing on upgrade"
    change(database, "models.angle_generation", "table/strategist")
    now = Settings.from_env()
    assert now.model_for("angle_generation") == "table/strategist" and now.setting_sources["models.angle_generation"] == "table"
    assert settings_store.load(read_files=False).shadowed == {"models.angle_generation": "OPENROUTER_ANGLE_GENERATION_MODEL"}
    remove(database, "models.angle_generation")
    assert Settings.from_env().model_for("angle_generation") == "env/strategist"


def test_a_submitted_run_snapshots_the_settings_it_used_and_where_each_came_from(database, platform_setup, monkeypatch):  # noqa: F811
    repo, _, _ = platform_setup
    baseline = Settings.from_env()
    first = repo.submit(W1, "synthetic", models=baseline)
    snap = refs_of(repo, first["run_id"])["settings_snapshot"]
    assert snap["scope"] == "weekly" and snap["values"]["models.angle_generation"] == {"value": None, "source": "default"}
    assert snap["values"]["prompts.profile.strategist"] == {"value": "2026-10-19.reel-editorial.v2", "source": "default"}
    assert snap["knowledge_base_version"] is None, "the legacy profile uses no knowledge base"

    change(database, "prompts.profile.strategist", STRATEGIST_V5_PROFILE)
    change(database, "models.angle_generation", "table/strategist")
    change(database, "models.reasoning_effort.angle_generation", "low")
    change(database, "matching.duplicate", 0.85)
    monkeypatch.setenv("CONTENT_ATELIER_REQUEST_TIMEOUT_SECONDS", "321")
    storage = StorageSettings.from_env()
    second_repo = ContentRepository(storage)
    configured = Settings.from_env()
    second = second_repo.submit(W2, "synthetic", models=configured)
    refs = refs_of(second_repo, second["run_id"])
    assert refs["angle_prompt_profile"] == STRATEGIST_V5_PROFILE and refs["models"]["angle_generation"] == "table/strategist"
    values = refs["settings_snapshot"]["values"]
    assert values["prompts.profile.strategist"] == {"value": STRATEGIST_V5_PROFILE, "source": "table"}
    assert values["models.angle_generation"] == {"value": "table/strategist", "source": "table"}
    assert values["models.reasoning_effort.angle_generation"] == {"value": "low", "source": "table"}
    assert values["matching.duplicate"] == {"value": 0.85, "source": "table"}
    assert values["models.request_timeout_seconds"] == {"value": 321.0, "source": "env"}, "a legacy variable is recorded as env"
    assert values["models.moment_extraction"]["source"] == "default"
    assert refs["settings_snapshot"]["knowledge_base_version"], "the strategist profile records the knowledge-base version it will use"
    assert set(values) == set(settings_store.keys_for("weekly"))
    # Read-only in the week's API answer (GET /storage/weeks/{id}): the run rows carry input_refs.settings_snapshot.
    shown = next(r for r in second_repo.review(W2, APPROVER)["runs"] if r["run_id"] == second["run_id"])
    assert shown["input_refs"]["settings_snapshot"] == refs["settings_snapshot"]
    # The first run's snapshot is unchanged: a run keeps the settings it started under.
    assert refs_of(repo, first["run_id"])["settings_snapshot"] == snap


def test_unsetting_a_row_restores_the_default_in_the_next_runs_snapshot(database, platform_setup):  # noqa: F811
    repo, _, _ = platform_setup
    change(database, "prompts.profile.extraction", "2026-10-18.scenes.v1")
    changed = repo.submit(W1, "synthetic", models=Settings.from_env())
    assert refs_of(repo, changed["run_id"])["extraction_profile"] == "2026-10-18.scenes.v1"
    assert refs_of(repo, changed["run_id"])["settings_snapshot"]["values"]["prompts.profile.extraction"]["source"] == "table"
    remove(database, "prompts.profile.extraction")
    restored = repo.submit(W2, "synthetic", models=Settings.from_env())
    refs = refs_of(repo, restored["run_id"])
    # The default is the ledger's scene profile v2 (E.B12), frozen with the run like any profile but weekly v3 (which a run
    # without the key has always meant).
    assert refs["extraction_profile"] == "2026-10-19.scenes.v2"
    assert refs["settings_snapshot"]["values"]["prompts.profile.extraction"] == {"value": "2026-10-19.scenes.v2", "source": "default"}


def test_a_brief_run_snapshots_the_brief_settings(database, v2, monkeypatch):  # noqa: F811
    repo, _, top, row, original_refs, _, _ = v2
    initial = original_refs["settings_snapshot"]
    assert initial["scope"] == "brief" and initial["values"]["models.brief"] == {"value": "openai/gpt-6.1-sol", "source": "default"}
    assert initial["knowledge_base_version"] == original_refs["execution_contract"]["knowledge_base"]["version"], \
        "the snapshot names the knowledge-base version the writer used"
    # A brief revision queued after the writer model is set in the table carries that value and its source.
    change(database, "models.brief", WRITER)
    change(database, "briefs.channels", ["reel", "email"])
    monkeypatch.setenv("ATELIER_BRIEFS_ENABLED", "true")
    monkeypatch.setenv("ATELIER_BRIEF_APPROVERS", APPROVER)
    live = ContentRepository(StorageSettings.from_env())
    queued = brief_workflow.queue(live, top["angle_id"], APPROVER, "synthetic", revision=row["brief_id"], instructions="Tighten the opening.")
    refs = refs_of(live, queued["run_id"])
    values = refs["settings_snapshot"]["values"]
    assert values["models.brief"] == {"value": WRITER, "source": "table"}
    assert values["briefs.channels"] == {"value": ["reel", "email"], "source": "table"}
    assert values["models.brief_review"]["source"] == "default" and values["prompts.profile.brief"]["source"] == "default"
    assert set(values) == set(settings_store.keys_for("brief"))


# The process notices a changed row without a restart --------------------------------------------------------------


def test_the_repository_and_the_worker_pick_up_a_changed_row_with_no_restart(database, tmp_path):
    storage, models = StorageSettings.from_env(), Settings.from_env()
    repo = ContentRepository(storage)
    worker = SQLWorker(storage, models)
    assert repo.settings.angle_approval_cutoff is None and repo.settings.brief_enabled is False
    change(database, "matching.approval_cutoff", 0.85)
    change(database, "features.briefs", True)
    change(database, "prompts.profile.strategist", STRATEGIST_V5_PROFILE)
    assert repo.settings.angle_approval_cutoff == 0.85 and repo.settings.brief_enabled is True, "the repository sees the rows"
    assert worker.models.angle_prompt_profile == "2026-10-19.reel-editorial.v2"
    assert worker.once() is None, "no job to run"
    assert worker.models.angle_prompt_profile == STRATEGIST_V5_PROFILE and worker.storage.brief_enabled is True, "each job starts under the current settings"
    remove(database, "matching.approval_cutoff")
    assert repo.settings.angle_approval_cutoff is None
    # A settings object a script changed by hand is never overwritten by the table.
    pinned = Settings.from_env().model_copy(update={"angle_prompt_profile": "2026-10-16.reel-editorial.v1"})
    assert SQLWorker(storage, pinned).models.refreshed().angle_prompt_profile == "2026-10-16.reel-editorial.v1"


def test_the_duplicate_cutoff_and_the_cycle_schedule_read_the_table(database):
    from backend_pipeline.matching import duplicate_cosine
    with connect(database, vectors=False) as conn:
        assert duplicate_cosine(conn) == 0.86 and settings_store.cycle_schedule_text(conn) == "Sunday 04:00 America/Chicago"
        settings_store.set_value(conn, "matching.duplicate", 0.85, "tester")
        settings_store.set_value(conn, "cycle.weekday", 4, "tester")
        settings_store.set_value(conn, "cycle.timezone", "Asia/Kolkata", "tester")
        assert duplicate_cosine(conn) == 0.85 and settings_store.cycle_schedule_text(conn) == "Friday 04:00 Asia/Kolkata"
        with pytest.raises(SettingError, match="between 0.5 and 1.0"):
            settings_store.set_value(conn, "matching.duplicate", 1.5, "tester")
        conn.rollback()
        assert duplicate_cosine(conn) == 0.86, "the rolled-back writes left nothing"


def test_the_knowledge_base_version_can_be_pinned(database, platform_setup):  # noqa: F811
    repo, _, _ = platform_setup
    root = BACKEND_ROOT / "knowledge_base"
    unpinned = assembly.assemble("strategist", root=root, connection=repo.connection).refs()["version"]
    with repo.connection() as conn:
        # A confirmed team member changes the compiled roster, so the compiled version differs from the files' version.
        items.add_item(conn, kind="roster_member", key="roster:new-hire", body={"name": "Robin Vale", "role": "Ads coordinator", "state": "current"},
                       status="confirmed", source_kind="approver_entry", source_ref="r1", author="Whitney", created_by=APPROVER,
                       reviewed_by=APPROVER)
        pinned_version = compiler.compile_version(conn, on=date.today(), actor=APPROVER, root=root)["version"]
    assert pinned_version != unpinned
    change(database, "knowledge_base.version", pinned_version)
    assert assembly.assemble("strategist", root=root, connection=repo.connection).refs()["version"] == pinned_version
    change(database, "knowledge_base.version", "wia-kb-0000-00-00.missing")
    with pytest.raises(ValueError, match="not published"):
        assembly.assemble("strategist", root=root, connection=repo.connection)
    remove(database, "knowledge_base.version")
    assert assembly.assemble("strategist", root=root, connection=repo.connection).refs()["version"] == unpinned


# Live mode names its models ---------------------------------------------------------------------------------------


def test_a_live_submit_is_refused_until_the_models_are_set_explicitly(database, platform_setup, monkeypatch):  # noqa: F811
    repo, _, _ = platform_setup
    with pytest.raises(SettingError, match=r"models\.moment_extraction, models\.default"):
        repo.submit(W1, "live", models=Settings.from_env())
    change(database, "models.moment_extraction", "table/moments")
    change(database, "models.default", "openai/gpt-6-luna")  # choosing the default model counts as choosing
    # The models are chosen but the strategist profile is still the rated code default (E.X4): refused, with the remedy.
    with pytest.raises(SettingError, match=r"prompts\.profile\.strategist is still the code default"):
        repo.submit(W1, "live", models=Settings.from_env())
    change(database, "prompts.profile.strategist", "2026-10-20.wia-strategist.v6")
    # The model and profile rules are satisfied; the next refusal is the environment-only generation catch.
    with pytest.raises(ValueError, match="SQL generation permission is disabled"):
        ContentRepository(StorageSettings.from_env()).submit(W1, "live", models=Settings.from_env())


# import-env ------------------------------------------------------------------------------------------------------


def test_import_env_records_the_deployments_values_with_who_and_leaves_secrets_out(database):
    env = {"OPENROUTER_ANGLE_GENERATION_MODEL": "env/strategist", "ATELIER_BRIEF_MODEL": "env/writer",
           "CONTENT_ATELIER_LLM_REASONING_EFFORT": "low", "ATELIER_DUPLICATE_COSINE": "0.85", "ATELIER_BRIEF_CHANNELS": "reel,email",
           "OPENROUTER_API_KEY": "sk-secret", "ATELIER_API_SECRET": "s3cret", "EMBEDDING_API_KEY": "k", "OPENAI_EMBEDDING_MODEL": "x/embed",
           "CONTENT_ATELIER_LLM_RESPONSE_FORMAT": "xml", "ATELIER_ALLOW_GENERATION": "true", "CONTENT_ATELIER_KNOWLEDGE_BASE_DIR": "/dev/kb"}
    with connect(database, vectors=False) as conn:
        result = settings_store.import_env(conn, "jainil@example.invalid", environ=env)
        conn.commit()
        rows = {r["key"]: r for r in conn.execute("SELECT * FROM settings").fetchall()}
    imported = {i["key"]: i["value"] for i in result["imported"]}
    assert imported == {"models.angle_generation": "env/strategist", "models.brief": "env/writer",
                        "models.reasoning_effort.default": "low", "matching.duplicate": 0.85, "briefs.channels": ["reel", "email"]}
    assert all(r["updated_by"] == "jainil@example.invalid" for r in rows.values()) and set(rows) == set(imported)
    assert len(result["invalid"]) == 1 and "CONTENT_ATELIER_LLM_RESPONSE_FORMAT" in result["invalid"][0]
    assert not any(secret in json.dumps(result) + json.dumps({k: r["value"] for k, r in rows.items()})
                   for secret in ("sk-secret", "s3cret", "x/embed", "/dev/kb")), "secrets, the embedding contract and the catches stay in the environment"
    # The values are now the table's: the variable can go, and a later import keeps what is there.
    with connect(database, vectors=False) as conn:
        again = settings_store.import_env(conn, "someone-else", environ={"ATELIER_BRIEF_MODEL": "env/other"})
        conn.commit()
        listing = {r["key"]: r for r in settings_store.listing(conn, environ={"ATELIER_BRIEF_MODEL": "env/other"})}
    assert again["imported"] == [] and again["skipped"] == [{"key": "models.brief", "reason": "a row exists"}]
    assert listing["models.brief"]["value"] == "env/writer" and listing["models.brief"]["source"] == "table"
    assert listing["models.brief"]["env_ignored"] == "ATELIER_BRIEF_MODEL", "the ignored variable is shown"
    assert listing["models.brief"]["updated_by"] == "jainil@example.invalid"
    assert StorageSettings.from_env().brief_model == "env/writer"


# The command line -------------------------------------------------------------------------------------------------


def run_cli(capsys, *args):
    from backend_pipeline import storage_cli
    storage_cli.main(["settings", *args])
    return json.loads(capsys.readouterr().out)


def test_the_command_line_lists_gets_sets_unsets_and_refuses(database, capsys, monkeypatch):
    listing = run_cli(capsys, "list")
    keys = {r["key"] for r in listing["settings"]}
    assert keys == {d.key for d in settings_store.DEFINITIONS} and listing["problems"] == []
    assert not [k for k in keys if settings_store.looks_secret(k)]
    result = run_cli(capsys, "set", "models.brief", "test/cli-writer", "--actor", "kenil@example.invalid")
    assert result["value"] == "test/cli-writer" and result["before"] == "openai/gpt-6.1-sol" and result["updated_by"] == "kenil@example.invalid"
    got = run_cli(capsys, "get", "models.brief")
    assert got["value"] == "test/cli-writer" and got["source"] == "table" and got["updated_by"] == "kenil@example.invalid"
    assert run_cli(capsys, "set", "cycle.hour", "6", "--actor", "kenil")["value"] == 6
    assert run_cli(capsys, "set", "briefs.channels", "reel, email", "--actor", "kenil")["value"] == ["reel", "email"]
    assert run_cli(capsys, "set", "models.angle_generation", "null", "--actor", "kenil")["value"] is None
    assert StorageSettings.from_env().brief_model == "test/cli-writer"
    undone = run_cli(capsys, "unset", "models.brief", "--actor", "kenil")
    assert undone["was_set"] and undone["value"] == "openai/gpt-6.1-sol" and undone["source"] == "default"
    for args, message in ((("set", "models.nonsense", "x"), "Unknown setting"), (("set", "ATELIER_API_SECRET", "x"), "secret or an endpoint"),
                          (("set", "openrouter.api_key", "x"), "secret or an endpoint"), (("set", "cycle.hour", "99"), "between 0 and 23"),
                          (("set", "embedding.model", "other/embed"), "environment-only"), (("set", "features.briefs", "maybe"), "true or false"),
                          (("unset", "models.nonsense"), "Unknown setting"), (("get", "models.nonsense"), "Unknown setting")):
        with pytest.raises(SystemExit) as stopped:
            run_cli(capsys, *args, "--actor", "kenil") if args[0] in {"set", "unset"} else run_cli(capsys, *args)
        assert message in str(stopped.value), args
    monkeypatch.setenv("ATELIER_BRIEF_REVIEW_MODEL", "env/reviewer")
    imported = run_cli(capsys, "import-env", "--actor", "kenil")
    assert [i["key"] for i in imported["imported"]] == ["models.brief_review"]


# The routes -------------------------------------------------------------------------------------------------------


@pytest.fixture
def api(database):
    storage = StorageSettings(database_url=database, synthetic=True, api_secret="test-secret", brief_approvers=(APPROVER,), brief_editors=(EDITOR,))
    app = FastAPI()
    app.include_router(router(storage))
    client = TestClient(app)
    as_ = lambda email: {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email}  # noqa: E731
    return client, as_


def test_settings_routes_read_for_editors_and_write_for_approvers(api, database):
    client, as_ = api
    assert client.get("/storage/settings").status_code == 401
    assert client.get("/storage/settings", headers=as_("stranger@example.invalid")).status_code == 403
    listing = client.get("/storage/settings", headers=as_(EDITOR))
    assert listing.status_code == 200 and {r["key"] for r in listing.json()["settings"]} == {d.key for d in settings_store.DEFINITIONS}
    put = lambda who, key, value: client.put(f"/storage/settings/{key}", json={"value": value}, headers=as_(who))  # noqa: E731
    assert put(EDITOR, "models.brief", "api/writer").status_code == 403, "an editor reads but cannot write"
    ok = put(APPROVER, "models.brief", "api/writer")
    assert ok.status_code == 200 and ok.json()["value"] == "api/writer" and ok.json()["updated_by"] == APPROVER
    changed = {r["key"]: r for r in client.get("/storage/settings", headers=as_(EDITOR)).json()["settings"]}["models.brief"]
    assert changed["value"] == "api/writer" and changed["source"] == "table" and changed["updated_by"] == APPROVER
    for key, value, code in (("models.nonsense", "x", 422), ("ATELIER_API_SECRET", "x", 422), ("cycle.hour", 99, 422),
                             ("embedding.model", "x", 422), ("features.briefs", "maybe", 422)):
        response = put(APPROVER, key, value)
        assert response.status_code == code, (key, response.text)
    assert client.put("/storage/settings/cycle.hour", json={"value": 5, "extra": 1}, headers=as_(APPROVER)).status_code == 422
    assert StorageSettings.from_env().brief_model == "api/writer"


def test_the_node_server_relays_the_settings_read_and_only_the_settings_screens_four_changes():
    """The Settings screen (6.F7) reads every setting; an approver changes the duplicate cutoff and the cycle's schedule there.
    The Node server relays the read and a change to those four keys only (frontend/server/allowlist.mjs, with its own tests),
    so models, prompt profiles, the knowledge-base pin and budgets stay `storage_cli settings` changes."""
    import re
    allowlist = (Path(__file__).resolve().parents[3] / "frontend/server/allowlist.mjs").read_text(encoding="utf-8")
    settable = re.search(r"export const SETTABLE = \[([^\]]*)\]", allowlist)
    assert settable, "the allowlist names the settable keys"
    keys = re.findall(r"'([^']+)'", settable.group(1))
    assert keys == ["matching.duplicate", "cycle.timezone", "cycle.weekday", "cycle.hour"]
    assert all(settings_store.definition(key).table for key in keys), "each is a key the table may hold"


# Start-up and an unreachable database ------------------------------------------------------------------------------


def test_start_up_refuses_a_hand_edited_row_that_fails_its_type(database):
    with connect(database, vectors=False) as conn:
        conn.execute("INSERT INTO settings(key,value,updated_by) VALUES ('cycle.hour','99','sql'),('matching.duplicate','0.95','sql')")
        conn.commit()
    models, storage = Settings.from_env(), StorageSettings.from_env()
    assert models.setting_sources["matching.duplicate"] == "table"
    with pytest.raises(startup.StartupError, match=r"invalid rows.*cycle\.hour"):
        startup.check_settings(storage, models)
    with connect(database, vectors=False) as conn:
        conn.execute("DELETE FROM settings WHERE key='cycle.hour'")
        conn.commit()
    settings_store.invalidate()
    startup.check_settings(StorageSettings.from_env(), Settings.from_env())


def test_a_database_that_cannot_be_reached_falls_back_to_the_environment_and_defaults(monkeypatch):
    monkeypatch.setenv("OPENROUTER_ANGLE_GENERATION_MODEL", "env/strategist")
    started = time.monotonic()
    unreachable = "postgresql://atelier:x@127.0.0.1:1/none"
    models = Settings.from_env(database_url=unreachable)
    assert models.openrouter_angle_generation_model == "env/strategist" and models.setting_sources["models.angle_generation"] == "env"
    Settings.from_env(database_url=unreachable)  # cached as unreachable: no second wait
    assert time.monotonic() - started < 10
    assert settings_store.load(database_url=unreachable, read_files=False).state == "unreachable"


def test_a_database_below_migration_005_has_no_table_and_works_on_defaults(setup_baseline):
    eff = settings_store.load(database_url=setup_baseline, read_files=False)
    assert eff.state == "no_table" and eff["models.default"] == "openai/gpt-6-luna"


@pytest.fixture
def setup_baseline():
    """A database with no platform tables at all (the runner never produces one below 005, so it is empty)."""
    from backend_pipeline.tests.test_migrations_db import URL, recreate
    if not URL:
        pytest.skip("Requires isolated atelier_test")
    return recreate('atelier_test_settings_baseline')


def test_gate_one_reassessment_snapshots_the_matching_settings(database, platform_setup):  # noqa: F811
    repo, models, _ = platform_setup
    change(database, "matching.approval_cutoff", 0.85)
    storage = StorageSettings.from_env()
    live = ContentRepository(storage)
    from backend_pipeline.tests.test_sql_storage import NonemptyProvider, drain
    worker = SQLWorker(repo.settings, models, provider=NonemptyProvider())
    repo.submit(W1, "synthetic")
    drain(worker)
    storage.brief_approvers = (APPROVER,)
    storage.brief_editors = (EDITOR,)
    result = gate_one.reassess(live, W1, EDITOR)
    values = refs_of(live, result["run_id"])["settings_snapshot"]["values"]
    assert values["matching.approval_cutoff"] == {"value": 0.85, "source": "table"} and values["matching.duplicate"]["source"] == "default"
