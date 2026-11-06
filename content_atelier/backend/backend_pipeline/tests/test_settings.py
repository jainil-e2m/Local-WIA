"""0.B8 offline: the settings registry, its precedence, typing, the single environment reader, the example files
equal to the code defaults, per-stage models and reasoning effort, run snapshots and the live-mode model rule."""
from __future__ import annotations

import ast
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend_pipeline import config, settings_store
from backend_pipeline.config import Settings, frozen_models
from backend_pipeline.intake.config import IntakeSettings
from backend_pipeline.settings_store import DEFINITIONS, Definition, SettingError, coerce, definition, load
from backend_pipeline.storage_config import StorageSettings

BACKEND = Path(__file__).resolve().parents[2]
EXAMPLES = [BACKEND / ".env.example", BACKEND / "storage.env.example", BACKEND / "intake.env.example"]


def row(value):
    return {"value": value, "updated_by": "tester", "updated_at": datetime(2026, 10, 18, tzinfo=UTC)}


def parse_example(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip()
    return values


# Precedence ------------------------------------------------------------------------------------------------------


def test_default_then_legacy_environment_then_table_row():
    key, var = "models.angle_generation", "OPENROUTER_ANGLE_GENERATION_MODEL"
    assert load(environ={}, read_files=False).sources[key] == "default"
    env = load(environ={var: "env/model"}, read_files=False)
    assert env[key] == "env/model" and env.sources[key] == "env"
    # A row beats the old environment variable: the point is to change behaviour without a deploy.
    both = load(environ={var: "env/model"}, read_files=False, rows={key: row("table/model")})
    assert both[key] == "table/model" and both.sources[key] == "table"
    assert both.shadowed == {key: var}, "the ignored environment variable is reported"
    # Removing the row (unset) restores the environment value, then the default.
    assert load(environ={var: "env/model"}, read_files=False, rows={})[key] == "env/model"
    assert load(environ={}, read_files=False, rows={})[key] is None


def test_an_environment_override_beats_a_row_only_where_a_key_is_marked():
    plain = Definition("t.plain", "str", "default", "x", env=("T_PLAIN",), table=True)
    override = Definition("t.override", "str", "default", "x", env=("T_OVERRIDE",), env_override=True)
    rows = {"t.plain": row("table"), "t.override": row("table")}
    eff = load(environ={"T_PLAIN": "env", "T_OVERRIDE": "env"}, read_files=False, rows=rows, definitions=[plain, override])
    assert (eff["t.plain"], eff.sources["t.plain"]) == ("table", "table")
    assert (eff["t.override"], eff.sources["t.override"]) == ("env", "env")
    only_row = load(environ={}, read_files=False, rows=rows, definitions=[override])
    assert only_row["t.override"] == "table", "an override key still reads its row when the variable is unset"


def test_the_knowledge_base_directory_is_a_development_override_that_the_table_cannot_set():
    d = definition("knowledge_base.directory")
    assert d.env == ("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR",) and d.env_override and not d.table
    with pytest.raises(SettingError, match="environment-only"):
        settings_store._writable("knowledge_base.directory")
    eff = load(environ={"CONTENT_ATELIER_KNOWLEDGE_BASE_DIR": "/dev/kb"}, read_files=False, rows={})
    assert eff["knowledge_base.directory"] == "/dev/kb" and eff.sources["knowledge_base.directory"] == "env"
    assert Settings.from_effective(eff).knowledge_base_root == Path("/dev/kb")
    # A stray row for an environment-only key is ignored and reported, never obeyed.
    stray = load(environ={}, read_files=False, rows={"embedding.model": row("evil/model")})
    assert stray["embedding.model"] == config.EMBEDDING_MODEL and any("embedding.model" in p for p in stray.problems)


def test_legacy_aliases_keep_their_order():
    eff = load(environ={"OPENROUTER_MODEL": "alias/model"}, read_files=False)
    assert eff["models.default"] == "alias/model"
    eff = load(environ={"OPENROUTER_MODEL": "alias/model", "OPENROUTER_ANGLES_MODEL": "primary/model"}, read_files=False)
    assert eff["models.default"] == "primary/model"
    v2 = load(environ={"ATELIER_BRIEF_SCHEMA": "v2"}, read_files=False)
    assert v2["prompts.profile.brief"] == "brief_document_v2"


# Typing ----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("key,bad", [
    ("matching.duplicate", 1.5), ("matching.duplicate", "high"), ("matching.related", -0.1), ("cycle.hour", 24),
    ("cycle.weekday", 2.5), ("cycle.weekday", True), ("cycle.timezone", "Mars/Olympus"), ("display.timezone", 5),
    ("prompts.profile.strategist", "2026-10-18.made-up.v9"), ("models.reasoning_effort.default", "extreme"),
    ("features.briefs", "yes"), ("features.briefs", 1), ("briefs.channels", []), ("briefs.channels", ",,"),
    ("models.completion_tokens", 0), ("models.default", None), ("models.default", 7), ("context.exemplars.k", -1),
])
def test_values_are_validated_by_type_and_range(key, bad):
    with pytest.raises(SettingError):
        coerce(definition(key), bad)


@pytest.mark.parametrize("key,raw,typed", [
    ("matching.duplicate", "0.85", 0.85), ("matching.duplicate", 1, 1.0), ("cycle.hour", "6", 6), ("features.briefs", "True", True),
    ("features.packs", False, False), ("briefs.channels", "reel, email", ("reel", "email")), ("briefs.channels", ["caption"], ("caption",)),
    ("models.angle_generation", None, None), ("models.angle_generation", "  ", None), ("models.reasoning_effort.brief", "low", "low"),
    ("cycle.timezone", "America/New_York", "America/New_York"), ("matching.approval_cutoff", "0.9", 0.9),
])
def test_values_are_coerced_to_their_type(key, raw, typed):
    assert coerce(definition(key), raw) == typed


def test_an_invalid_environment_value_names_the_variable_and_the_setting():
    with pytest.raises(SettingError, match=r"ATELIER_DUPLICATE_COSINE \(setting matching.duplicate\).*between 0.5 and 1.0"):
        load(environ={"ATELIER_DUPLICATE_COSINE": "1.5"}, read_files=False)
    with pytest.raises(SettingError, match="CONTENT_ATELIER_LLM_RESPONSE_FORMAT"):
        load(environ={"CONTENT_ATELIER_LLM_RESPONSE_FORMAT": "xml"}, read_files=False)


def test_an_invalid_stored_row_is_reported_and_ignored_not_obeyed():
    eff = load(environ={}, read_files=False, rows={"matching.duplicate": row(7), "cycle.hour": row(5), "other.system.row": row({"x": 1})})
    assert eff["matching.duplicate"] == 0.86 and eff.sources["matching.duplicate"] == "default"
    assert eff["cycle.hour"] == 5 and eff.sources["cycle.hour"] == "table"
    assert len(eff.problems) == 1 and "matching.duplicate" in eff.problems[0], "other features' rows in the table are not problems"


def test_unknown_keys_and_secrets_are_refused():
    with pytest.raises(SettingError, match="Unknown setting models.nonexistent"):
        definition("models.nonexistent")
    for key in ("ATELIER_API_SECRET", "openrouter.api_key", "database_url", "slack.token", "x.password"):
        with pytest.raises(SettingError, match="secret or an endpoint"):
            definition(key)
    assert not [d.key for d in DEFINITIONS if settings_store.looks_secret(d.key)], "no secret is a setting"


def test_the_safety_catches_and_secrets_are_not_settings(monkeypatch):
    absorbed = {v for d in DEFINITIONS for v in d.env}
    catches = {"ATELIER_ALLOW_GENERATION", "ATELIER_ALLOW_ENCODING", "ATELIER_ALLOW_REFINEMENT", "ATELIER_ALLOW_BRIEF_GENERATION",
               "ATELIER_ALLOW_BRIEF_WEB", "ATELIER_ALLOW_PACK_GENERATION", "ATELIER_ALLOW_INTAKE_ENCODING", "CONTENT_ATELIER_LIVE",
               "CONTENT_ATELIER_EMBEDDINGS_ENABLED", "ATELIER_ALLOW_EMBEDDING_CONTRACT_CHANGE", "ATELIER_SYNTHETIC_DATABASE"}
    secrets = {"ATELIER_API_SECRET", "ATELIER_DATABASE_URL", "OPENROUTER_API_KEY", "OPENROUTER_MOMENTS_KEY", "OPENROUTER_ANGLES_KEY",
               "EMBEDDING_API_KEY", "ATELIER_SLACK_INTAKE_TOKEN", "ATELIER_FATHOM_API_KEY", "ATELIER_ARTIFACT_ROOT",
               "ATELIER_BRAND_BUNDLE_PATH", "OPENROUTER_BASE_URL", "ATELIER_BRIEF_APPROVERS", "ATELIER_BRIEF_EDITORS"}
    assert not (absorbed & (catches | secrets))
    # The catches still work from the environment alone, and a settings row cannot turn one on.
    monkeypatch.setenv("ATELIER_ALLOW_GENERATION", "true")
    monkeypatch.setenv("ATELIER_ALLOW_BRIEF_GENERATION", "true")
    storage = StorageSettings.from_effective(load(environ={}, read_files=False, rows={"generation_enabled": row(True)}))
    assert storage.generation_enabled and storage.brief_live_enabled and not storage.encoding_enabled
    monkeypatch.delenv("ATELIER_ALLOW_GENERATION")
    assert not StorageSettings.from_env().generation_enabled
    with pytest.raises(SettingError):
        settings_store._writable("generation_enabled")


def test_every_absorbed_variable_changes_the_loaded_value():
    """Each variable a definition absorbs is wired: setting it (to a value other than the default) changes the key."""
    sample = {"str": "x/model", "float": 0.6, "int": 7, "bool": None, "list": "a,b", "zone": "Europe/London"}
    for d in DEFINITIONS:
        if not d.env:
            continue
        if d.type == "enum":
            alternatives = [c for c in d.choices if c != d.default] or [d.choices[0]]
            raw = alternatives[0] if d.env_aliases == () else d.env_aliases[-1][0]
        elif d.type == "bool":
            raw = "true" if d.default is False else "false"
        else:
            raw = str(sample[d.type])
        if d.lo is not None and d.type in {"int", "float"}:
            raw = str(max(float(raw), d.lo) if d.type == "float" else max(int(raw), int(d.lo)))
        if d.hi is not None and d.type in {"int", "float"}:
            raw = str(min(float(raw), d.hi) if d.type == "float" else min(int(raw), int(d.hi)))
        if d.default is not None and str(d.default) == raw:
            raw = str(coerce(d, raw) + (1 if d.type == "int" and (d.hi is None or d.default < d.hi) else -1)) if d.type == "int" else raw
        eff = load(environ={d.env[0]: raw}, read_files=False)
        assert eff.sources[d.key] == "env", d.key
        assert eff[d.key] == coerce(d, raw, source=d.env[0]), d.key


# Defaults equal the documented defaults ---------------------------------------------------------------------------


def test_code_defaults_equal_the_example_environment_files():
    """4.10: a fresh deployment behaves like the examples (V12). Every setting variable an example names has the
    code default as its value, or is blank."""
    by_var = {v: d for d in DEFINITIONS for v in d.env}
    checked = {}
    for path in EXAMPLES:
        for name, text in parse_example(path).items():
            d = by_var.get(name)
            if d is None:
                continue
            typed = d.default if not text else coerce(d, text, source=name)
            assert typed == d.default, f"{path.name}: {name}={text!r} differs from the code default {d.default!r} ({d.key})"
            checked[name] = d.key
    for must in ("OPENROUTER_MOMENTS_MODEL", "OPENROUTER_ANGLES_MODEL", "ATELIER_BRIEF_MODEL", "ATELIER_BRIEF_REVIEW_MODEL",
                 "CONTENT_ATELIER_LLM_REASONING_EFFORT", "CONTENT_ATELIER_LLM_RESPONSE_FORMAT", "CONTENT_ATELIER_LLM_PAYLOAD_FORMAT",
                 "CONTENT_ATELIER_REQUEST_TIMEOUT_SECONDS", "CONTENT_ATELIER_ANGLE_PROMPT_PROFILE", "ATELIER_CALENDAR_TIMEZONE",
                 "CONTENT_ATELIER_SIMILARITY_THRESHOLD", "ATELIER_BRIEF_MAX_CHARACTERS"):
        assert must in checked, f"{must} is documented in an example file"


def test_the_typed_objects_default_to_the_registry_defaults():
    models, storage, intake = Settings(), StorageSettings(), IntakeSettings()
    holders = {"models": models, "storage": storage, "intake": intake}
    for d in DEFINITIONS:
        if not d.target or not d.field or d.key == "knowledge_base.directory":
            continue
        for target in d.target.split("+"):
            value = getattr(holders[target], d.field)
            if d.field_key:
                value = value.get(d.field_key)
            assert settings_store.plain(value) == settings_store.plain(d.default), (d.key, target)
    assert models.knowledge_base_root == config.BACKEND_ROOT / "knowledge_base"


def test_the_documented_defaults_the_plan_names():
    """V12: Sol writes, Sonnet reviews, reasoning effort is high and the response format is json_schema in code too."""
    storage, models = StorageSettings(), Settings()
    assert storage.brief_model == "openai/gpt-6.1-sol" and storage.brief_review_model == "anthropic/claude-sonnet-5.5"
    assert models.llm_reasoning_effort == "high" and models.llm_response_format == "json_schema"
    assert models.model_for("brief_write") == "openai/gpt-6.1-sol" and models.model_for("brief_review") == "anthropic/claude-sonnet-5.5"
    from backend_pipeline.prompts import ANGLE_PROMPT_VERSION
    from backend_pipeline.angle_profiles import ANGLE_PROFILES
    assert settings_store.LEGACY_ANGLE_PROFILE == ANGLE_PROMPT_VERSION and settings_store.ANGLE_PROFILES == ANGLE_PROFILES
    assert definition("prompts.profile.strategist").choices == ANGLE_PROFILES


# One environment reader ------------------------------------------------------------------------------------------


@pytest.fixture
def folders(tmp_path, monkeypatch):
    project = tmp_path / "project"
    backend = project / "backend"
    backend.mkdir(parents=True)
    monkeypatch.setattr(config, "PROJECT_ROOT", project)
    monkeypatch.setattr(config, "BACKEND_ROOT", backend)
    return project, backend


def test_the_four_legacy_files_are_read_in_one_place_with_the_process_environment_winning(folders, monkeypatch):
    project, backend = folders
    for name in ("OPENROUTER_ANGLES_MODEL", "OPENROUTER_MOMENTS_MODEL", "ATELIER_BRIEF_MODEL", "ATELIER_SLACK_WORKSPACE",
                 "ATELIER_INTAKE_AUDIO_MODEL", "CONTENT_ATELIER_REQUEST_TIMEOUT_SECONDS", "CONTENT_ATELIER_DATA_ROOT"):
        monkeypatch.delenv(name, raising=False)
    (project / ".env").write_text('OPENROUTER_ANGLES_MODEL="root/angles"\nOPENROUTER_MOMENTS_MODEL=root/moments\n', encoding="utf-8")
    (backend / ".env").write_text("OPENROUTER_ANGLES_MODEL=backend/angles\nCONTENT_ATELIER_DATA_ROOT=\n", encoding="utf-8")
    (backend / ".env.storage.local").write_text("ATELIER_BRIEF_MODEL=storage/brief\nOPENROUTER_MOMENTS_MODEL=ignored/non-atelier\n",
                                                 encoding="utf-8")
    (backend / ".env.intake.local").write_text("ATELIER_SLACK_WORKSPACE=T-from-intake-file\nATELIER_INTAKE_AUDIO_MODEL=base.en\n",
                                               encoding="utf-8")
    monkeypatch.setenv("CONTENT_ATELIER_REQUEST_TIMEOUT_SECONDS", "321")
    models, storage, intake = Settings.from_env(), StorageSettings.from_env(), IntakeSettings.from_env()
    assert models.openrouter_angles_model == "backend/angles", "backend/.env before the project root .env"
    assert models.openrouter_moments_model == "root/moments", ".env.storage.local only supplies ATELIER_* keys"
    assert models.request_timeout_seconds == 321, "the process environment wins over every file"
    assert storage.brief_model == "storage/brief"
    assert intake.workspace == "T-from-intake-file" and intake.audio_model == "base.en", ".env.intake.local reaches the intake settings"


def test_every_loader_calls_the_same_single_reader(monkeypatch):
    calls = []
    real = settings_store.load_env_files
    monkeypatch.setattr(settings_store, "load_env_files", lambda environ=None: (calls.append(1), real(environ))[1])
    Settings.from_env()
    StorageSettings.from_env()
    IntakeSettings.from_env()
    assert len(calls) == 3


def test_no_other_module_parses_environment_files():
    """The legacy files are opened in settings_store alone (4.10: one loader)."""
    offenders = []
    for path in (BACKEND / "backend_pipeline").rglob("*.py"):
        if "tests" in path.parts or path.name == "settings_store.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.search(r"\.env(\.storage\.local|\.intake\.local)?$", node.value):
                offenders.append(f"{path.name}: {node.value}")
    assert offenders == []


def test_the_intake_loader_is_built_on_the_settings_registry():
    source = (BACKEND / "backend_pipeline/intake/config.py").read_text(encoding="utf-8")
    assert "settings_store.load" in source and "read_text" not in source and "open(" not in source


# Per-stage models and reasoning effort -----------------------------------------------------------------------------


def test_model_for_and_reasoning_effort_for_read_per_stage_settings():
    rows = {"models.angle_generation": row("table/strategist"), "models.reasoning_effort.angle_generation": row("low"),
            "models.reasoning_effort.default": row("medium"), "models.reasoning_effort.brief": row("high"),
            "models.brief_review": row("table/reviewer"), "prompts.profile.strategist": row("2026-10-18.wia-strategist.v5")}
    s = Settings.from_effective(load(environ={}, read_files=False, rows=rows))
    assert s.model_for("angle_generation") == "table/strategist"
    assert s.reasoning_effort_for("angle_generation") == "low"
    assert s.reasoning_effort_for("moment_extraction") == "medium", "a stage without its own uses the default"
    assert s.reasoning_effort_for("brief_write") == "high" and s.reasoning_effort_for("brief_repair") == "high"
    assert s.model_for("brief_plan") == s.model_for("brief_review") == "table/reviewer"
    assert s.model_for("angle_refinement") == s.openrouter_angles_model
    # The strategist model applies to the card profiles only (unchanged rule).
    legacy = Settings.from_effective(load(environ={}, read_files=False, rows={"models.angle_generation": row("table/strategist")}))
    assert legacy.model_for("angle_generation") == legacy.openrouter_angles_model


def test_scene_extraction_has_its_own_output_cap_and_the_live_provider_sends_it():
    """N1 shakedown, from paid evidence: Luna's scene extractions used up to 20,607 output tokens (reasoning included), so
    the one cap every stage took (16,000) cut a third of them off, each a paid call lost."""
    import httpx

    from backend_pipeline.llm.providers import live_provider
    from backend_pipeline.tests.plans import OpenTestPlan
    rows = {"models.completion_tokens": row(16000), "models.completion_tokens.moment_extraction": row(32000)}
    s = Settings.from_effective(load(environ={}, read_files=False, rows=rows))
    assert s.completion_tokens_for("moment_extraction") == 32000
    assert s.completion_tokens_for("angle_generation") == s.completion_tokens_for("brief_write") == 16000
    assert Settings.from_effective(load(environ={}, read_files=False, rows={"models.completion_tokens": row(16000)})
                                   ).completion_tokens_for("moment_extraction") == 16000, "blank uses the global cap"
    sent = []

    def answer(request):
        sent.append(__import__("json").loads(request.content)["max_tokens"])
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]})
    provider = live_provider(s, plan=OpenTestPlan(), key="k")
    original = httpx.Client.__init__
    try:
        httpx.Client.__init__ = lambda self, *a, **kw: original(self, *a, **{**kw, "transport": httpx.MockTransport(answer)})
        for stage in ("moment_extraction", "angle_generation"):
            provider.json_call(stage=stage, system="s", user="u", schema={"type": "object"}, fingerprint=stage)
    finally:
        httpx.Client.__init__ = original
    assert sent == [32000, 16000]


def test_the_old_variables_still_feed_the_per_stage_settings():
    env = {"OPENROUTER_ANGLE_GENERATION_MODEL": "env/strategist", "CONTENT_ATELIER_ANGLE_PROMPT_PROFILE": "2026-10-18.wia-strategist.v4",
           "CONTENT_ATELIER_LLM_REASONING_EFFORT": "low", "OPENROUTER_VERIFICATION_MODEL": "env/verifier"}
    s = Settings.from_effective(load(environ=env, read_files=False))
    assert s.model_for("angle_generation") == "env/strategist" and s.model_for("card_verification") == "env/verifier"
    assert s.reasoning_effort_for("card_verification") == "low"
    assert frozen_models(s)["card_verification"] == "env/verifier"


# Snapshots -------------------------------------------------------------------------------------------------------


def test_a_snapshot_records_each_value_and_where_it_came_from():
    rows = {"models.moment_extraction": row("table/moments"), "prompts.profile.extraction": row("2026-10-18.scenes.v1")}
    eff = load(environ={"OPENROUTER_ANGLES_MODEL": "env/angles"}, read_files=False, rows=rows)
    models, storage = Settings.from_effective(eff), StorageSettings.from_effective(eff)
    snap = settings_store.snapshot("weekly", models=models, storage=storage)
    assert snap["scope"] == "weekly" and snap["version"] == 1
    values = snap["values"]
    assert values["models.moment_extraction"] == {"value": "table/moments", "source": "table"}
    assert values["models.default"] == {"value": "env/angles", "source": "env"}
    assert values["prompts.profile.extraction"] == {"value": "2026-10-18.scenes.v1", "source": "table"}
    assert values["models.response_format"] == {"value": "json_schema", "source": "default"}
    assert values["embedding.dimensions"]["value"] == 1536 and values["matching.duplicate"]["source"] == "default"
    assert set(values) == set(settings_store.keys_for("weekly"))
    # Nothing secret and no environment-only catch is in a snapshot.
    assert not [k for k in values if settings_store.looks_secret(k)]
    # An object built or changed by hand says so instead of claiming the table.
    changed = models.model_copy(update={"openrouter_moments_model": "hand/model"})
    assert settings_store.snapshot("weekly", models=changed)["values"]["models.moment_extraction"] == {"value": "hand/model", "source": "explicit"}
    assert settings_store.snapshot("weekly", models=Settings())["values"]["models.default"]["source"] == "default"
    brief = settings_store.snapshot("brief", storage=storage)["values"]
    assert {"models.brief", "models.brief_review", "briefs.channels", "prompts.profile.brief"} <= set(brief)
    assert brief["models.brief"] == {"value": "openai/gpt-6.1-sol", "source": "default"}


# Live mode names its models ---------------------------------------------------------------------------------------


def test_live_mode_refuses_a_paid_stage_whose_model_was_never_chosen():
    fresh = Settings.from_effective(load(environ={}, read_files=False))
    assert fresh.explicit_model_gaps() == ["models.moment_extraction", "models.default"]
    with pytest.raises(SettingError, match=r"models\.moment_extraction, models\.default"):
        fresh.require_explicit_models()
    chosen = Settings.from_effective(load(environ={"OPENROUTER_MOMENTS_MODEL": "a/b", "OPENROUTER_ANGLES_MODEL": "c/d",
                                                   "CONTENT_ATELIER_ANGLE_PROMPT_PROFILE": "2026-10-19.reel-editorial.v2"}, read_files=False))
    chosen.require_explicit_models()
    # A row counts as choosing, the code default does not.
    by_row = Settings.from_effective(load(environ={}, read_files=False,
                                          rows={"models.moment_extraction": row("a/b"), "models.default": row("openai/gpt-6-luna"),
                                                "prompts.profile.strategist": row("2026-10-20.wia-strategist.v6")}))
    by_row.require_explicit_models()
    # Under the strategist profile the strategist's own model satisfies the angle stage.
    cards = Settings.from_effective(load(environ={"OPENROUTER_MOMENTS_MODEL": "a/b", "OPENROUTER_ANGLE_GENERATION_MODEL": "s/s",
                                                  "CONTENT_ATELIER_ANGLE_PROMPT_PROFILE": "2026-10-18.wia-strategist.v5"}, read_files=False))
    cards.require_explicit_models()
    # Objects built by hand (tests, scripts) name their models in code.
    Settings().require_explicit_models()


def test_live_mode_refuses_a_prompt_profile_left_at_the_rated_code_default():
    """E.X4: the code defaults stay the configuration WIA rated 1 of 5 (released runs replay under them), so a live run on
    a deployment where `settings apply` was missed stops and says how to apply it, instead of quietly running that."""
    models_only = Settings.from_effective(load(environ={"OPENROUTER_MOMENTS_MODEL": "a/b", "OPENROUTER_ANGLES_MODEL": "c/d"}, read_files=False))
    assert models_only.explicit_model_gaps() == [] and settings_store.explicit_profile_gaps(models_only) == ["prompts.profile.strategist"]
    with pytest.raises(SettingError, match=r"prompts\.profile\.strategist is still the code default[\s\S]*settings apply --file deploy/production-settings.json"):
        models_only.require_explicit_models()
    storage = StorageSettings.from_effective(load(environ={"ATELIER_BRIEF_MODEL": "w/w", "ATELIER_BRIEF_REVIEW_MODEL": "r/r"}, read_files=False))
    assert settings_store.explicit_profile_gaps(storage=storage, brief=True) == ["prompts.profile.brief", "prompts.profile.brief_writer"]
    with pytest.raises(SettingError, match="prompts.profile.brief, prompts.profile.brief_writer"):
        settings_store.require_explicit_models(storage=storage, brief=True)
    # The production configuration names all three, so applying it clears every gap.
    import json
    from backend_pipeline.config import BACKEND_ROOT
    applied = json.loads((BACKEND_ROOT / "deploy" / "production-settings.json").read_text(encoding="utf-8"))["settings"]
    rows = {k: row(v) for k, v in applied.items() if not isinstance(v, bool)}
    Settings.from_effective(load(environ={}, read_files=False, rows=rows)).require_explicit_models()
    settings_store.require_explicit_models(storage=StorageSettings.from_effective(load(environ={}, read_files=False, rows=rows)), brief=True)
    # Objects built by hand (tests, scripts) name their profiles in code, as they name their models.
    assert settings_store.explicit_profile_gaps(Settings()) == []


def test_a_model_a_script_sets_in_code_after_loading_counts_as_chosen():
    fresh = Settings.from_effective(load(environ={}, read_files=False))
    changed = fresh.model_copy(update={"openrouter_moments_model": "script/moments", "openrouter_angles_model": "script/angles"})
    assert changed.explicit_model_gaps() == [] and fresh.explicit_model_gaps() != []
    one = fresh.model_copy(update={"openrouter_moments_model": "script/moments"})
    assert one.explicit_model_gaps() == ["models.default"]


def test_a_live_brief_needs_its_models_set_not_defaulted():
    storage = StorageSettings.from_effective(load(environ={}, read_files=False))
    assert storage.explicit_model_gaps() == ["models.brief", "models.brief_review"]
    with pytest.raises(SettingError, match="models.brief, models.brief_review"):
        settings_store.require_explicit_models(storage=storage, brief=True)
    ok = StorageSettings.from_effective(load(environ={"ATELIER_BRIEF_MODEL": "w/w", "ATELIER_BRIEF_REVIEW_MODEL": "r/r",
                                                      "ATELIER_BRIEF_SCHEMA": "v3", "ATELIER_BRIEF_WRITER": "v4"}, read_files=False))
    settings_store.require_explicit_models(storage=ok, brief=True)
    from types import SimpleNamespace
    from backend_pipeline.briefs.runtime import require_live_models
    live = {"input_refs": {"mode": "live"}}
    with pytest.raises(SettingError, match="models.brief"):
        require_live_models(SimpleNamespace(storage=storage), live, "brief_write")
    require_live_models(SimpleNamespace(storage=ok), live, "brief_write")


# The cycle (R36) -------------------------------------------------------------------------------------------------


def test_the_cycle_cutoff_follows_the_cycle_settings():
    from backend_pipeline.intake.runtime import last_saturday
    now = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)  # Sunday
    assert last_saturday(now) == datetime(2026, 10, 18, 9, 0, tzinfo=UTC), "Sunday 04:00 America/Chicago (CDT; the owner, 25 October)"
    eff = load(environ={}, read_files=False, rows={"cycle.timezone": row("Asia/Kolkata"), "cycle.weekday": row(4), "cycle.hour": row(6)})
    schedule = {"timezone": eff["cycle.timezone"], "weekday": eff["cycle.weekday"], "hour": eff["cycle.hour"]}
    assert last_saturday(now, **schedule) == datetime(2026, 10, 16, 0, 30, tzinfo=UTC), "Friday 06:00 Asia/Kolkata"
    assert settings_store.cycle_schedule_text() == "Sunday 04:00 America/Chicago"
