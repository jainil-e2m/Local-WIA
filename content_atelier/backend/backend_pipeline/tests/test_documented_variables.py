"""S.B8: every variable a deployment document or example names is read by the code, and every relative link resolves."""
from __future__ import annotations

import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
DOCUMENTS = [PROJECT / "DEPLOYMENT.md", PROJECT / "backend/docs/Calendar-Deployment.md", PROJECT / "backend/.env.example",
             PROJECT / "backend/storage.env.example", PROJECT / "backend/intake.env.example", PROJECT / "frontend/.env.example",
             PROJECT / "backend/compose.yml", PROJECT / "frontend/docker-compose.yml"]
CODE = [p for root in ("backend/backend_pipeline", "frontend/server", "frontend/src")
        for p in (PROJECT / root).rglob("*") if p.suffix in {".py", ".mjs", ".ts", ".tsx"} and "tests" not in p.parts
        and not p.name.endswith((".test.mjs", ".test.ts", ".test.tsx"))] + [PROJECT / "frontend/vite.config.ts"] + sorted((PROJECT / "frontend/tests").glob("*.mjs"))  # the browser acceptance runner
VARIABLE = re.compile(r"\b((?:ATELIER|CONTENT_ATELIER|OPENROUTER|EMBEDDING|OPENAI|COMMAND_CENTER|VITE)_[A-Z0-9_]*[A-Z0-9])\b")
# Set by the platform or read by another service, not by this repository's code.
ELSEWHERE = {"VITE_CONTENT_ATELIER_URL",  # Command Center's build variable
             "ATELIER_ARTIFACTS_DIR"}  # read by Docker Compose (backend/compose.yml), not by the code
WILDCARD_PREFIXES = ("CONTENT_ATELIER_LLM_",)


def settings_read_by_the_code():
    """0.B8: the registered keys some code reads, by name (a literal, or an f-string over its last segment) or through the
    typed object's field. The registry's definitions and the typed objects' field defaults are not reads."""
    from backend_pipeline.settings_store import DEFINITIONS
    texts = []
    for p in (PROJECT / "backend/backend_pipeline").rglob("*.py"):
        if "tests" in p.parts:
            continue
        text = p.read_text(encoding="utf-8")
        if p.name == "settings_store.py":
            text = text.split("\n_search_and_topics()\n", 1)[1]
        texts.append(re.sub(r"^\s*\w+: [^=\n]+= default\(\"[^\"]+\"\)$", "", text, flags=re.M))
    code = "\n".join(texts)
    read = set()
    for d in DEFINITIONS:
        prefix = re.escape(d.key.rsplit(".", 1)[0])
        if (re.search(rf"['\"]{re.escape(d.key)}['\"]|\bf['\"]{prefix}\.\{{", code)
                or d.field and re.search(rf"\.{d.field}\b|['\"]{d.field}['\"]", code)):
            read.add(d.key)
    return read


def test_every_registered_setting_is_read_by_some_code():
    from backend_pipeline.settings_store import DEFINITIONS
    read = settings_read_by_the_code()
    assert [d.key for d in DEFINITIONS if d.key not in read] == []


def test_the_read_check_sees_an_unread_setting(monkeypatch):
    from backend_pipeline import settings_store
    monkeypatch.setattr(settings_store, "DEFINITIONS", [*settings_store.DEFINITIONS, settings_store.Definition(
        "matching.never_read", "float", 0.5, "test", env=("CONTENT_ATELIER_NEVER_READ",), field="never_read_field")])
    assert "matching.never_read" not in settings_read_by_the_code()
    assert "matching.related" in settings_read_by_the_code()


def test_every_documented_variable_is_read_by_the_code():
    code = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in CODE)
    # A setting's legacy variables are read by the one loader from the registry (some names are built per item kind);
    # test_settings.py proves each of them changes the loaded value. A variable counts only when its setting is read
    # by some code (S.B8: a variable absorbed by an unread setting is not read).
    from backend_pipeline.settings_store import DEFINITIONS
    read = settings_read_by_the_code()
    absorbed = {v for d in DEFINITIONS if d.key in read for v in d.env}
    unread = {}
    for doc in DOCUMENTS:
        for name in set(VARIABLE.findall(doc.read_text(encoding="utf-8"))):
            if name in ELSEWHERE or name in WILDCARD_PREFIXES or name in absorbed:
                continue
            if not re.search(rf"\b{re.escape(name)}\b", code):
                unread.setdefault(doc.relative_to(PROJECT).as_posix(), []).append(name)
    assert unread == {}, f"Documented but never read: {unread}"


def test_the_removed_variables_are_not_documented():
    text = (PROJECT / "DEPLOYMENT.md").read_text(encoding="utf-8")
    for stale in ("ATELIER_API_TOKEN", "ATELIER_WHITNEY_EMAIL", "FATHOM_WEBHOOK_SECRET"):
        assert stale not in text


def test_relative_links_in_deployment_documents_resolve():
    link = re.compile(r"\]\(<?([^)>\s]+)>?\)")
    broken = []
    for doc in [PROJECT / "DEPLOYMENT.md", PROJECT / "backend/README.md", PROJECT / "frontend/README.md",
                PROJECT / "backend/docs/Calendar-Deployment.md", PROJECT / "backend/docs/Angle-Prompt-Profiles.md",
                PROJECT / "backend/docs/Privacy-Routing-Addendum.md"]:
        for target in link.findall(doc.read_text(encoding="utf-8")):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            path = (doc.parent / target.split("#", 1)[0]).resolve()
            if not path.exists():
                broken.append(f"{doc.relative_to(PROJECT).as_posix()} -> {target}")
    assert broken == []


def test_older_plans_carry_the_governing_plan_note():
    """S.B9: one governing plan. Every older plan or specification says so at its top."""
    marked = ["BUILD_HANDOFF.md", "content_atelier_vectordb.md", "implementation-plan-content-briefs.md",
              "implementation-plan-historical-comparison.md", "implementation-plan-weekly-angles-postgres.md",
              "implementation-status-content-briefs.md", "project_agenda.md", "transcript_to_content-angle.md",
              "backend/docs/Content-Atelier-Feasibility-Study.md", "backend/docs/Content-Atelier-Status-Audit.md",
              "backend/docs/Content-Atelier-Implementation-Roadmap-Brief-Generation.md",
              "backend/docs/Content-Atelier-Solution-Architecture.md"]
    for rel in marked:
        head = (PROJECT / rel).read_text(encoding="utf-8")[:1200]
        assert "<!-- governing-plan-note -->" in head and "Content-Atelier-Implementation-Plan-Brief-Generation.md" in head, rel
    analysis = (PROJECT / "backend/docs/Content-Atelier-Content-Quality-Analysis.md").read_text(encoding="utf-8")
    for section in ("## 10.", "## 11."):
        assert "Superseded (18 October 2026, plan item S.B9)" in analysis.split(section, 1)[1][:600]


# 0.B8: a behavioural variable in an example file is a setting (registered in settings_store, with a code default the file
# must equal: test_settings.py). Only these stay environment-only: secrets, endpoints, paths, allow-lists and the safety catches.
ENVIRONMENT_ONLY = {
    "ATELIER_SLACK_BOT_TOKEN",  # Outbound Slack credential: never stored as a behavioural setting.
    "CONTENT_ATELIER_LIVE", "CONTENT_ATELIER_EMBEDDINGS_ENABLED", "CONTENT_ATELIER_TRANSCRIPT_ROOT", "CONTENT_ATELIER_DATA_ROOT",
    "OPENROUTER_BASE_URL", "OPENROUTER_API_KEY", "OPENROUTER_MOMENTS_KEY", "OPENROUTER_ANGLES_KEY", "EMBEDDING_API_KEY",
    "ATELIER_DATABASE_URL", "ATELIER_REDIS_URL", "ATELIER_API_SECRET", "ATELIER_BACKEND_ORIGIN", "ATELIER_SYNTHETIC_DATABASE", "ATELIER_BRAND_BUNDLE_PATH",
    "ATELIER_ALLOW_GENERATION", "ATELIER_ALLOW_ENCODING", "ATELIER_ALLOW_REFINEMENT", "ATELIER_ALLOW_BRIEF_GENERATION",
    "ATELIER_ALLOW_BRIEF_WEB", "ATELIER_ALLOW_PACK_GENERATION", "ATELIER_ALLOW_INTAKE_ENCODING",
    "ATELIER_BRIEF_APPROVERS", "ATELIER_BRIEF_EDITORS", "ATELIER_PACK_EDITORS", "ATELIER_PACK_APPROVERS", "ATELIER_CALENDAR_SCHEDULERS",
    "ATELIER_IDENTITY_APPROVERS", "ATELIER_INTAKE_ADMINS", "ATELIER_SLACK_INTAKE_TOKEN", "ATELIER_FATHOM_API_KEY",
    "ATELIER_WIA_REVIEWERS",  # a people list like the approver lists: whose gate decisions are WIA's own labels
}


def test_every_variable_in_the_backend_examples_is_a_setting_or_deliberately_environment_only():
    from backend_pipeline.settings_store import DEFINITIONS
    absorbed = {v for d in DEFINITIONS for v in d.env}
    unclassified = {}
    for name in ("backend/.env.example", "backend/storage.env.example", "backend/intake.env.example"):
        for line in (PROJECT / name).read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                variable = line.split("=", 1)[0].strip()
                if variable not in absorbed and variable not in ENVIRONMENT_ONLY:
                    unclassified.setdefault(name, []).append(variable)
    assert unclassified == {}, f"Register these as settings in settings_store, or add them to ENVIRONMENT_ONLY with a reason: {unclassified}"
    assert not (absorbed & ENVIRONMENT_ONLY), "a variable is a setting or environment-only, not both"


def test_every_setting_is_listed_in_the_deployment_guide():
    from backend_pipeline.settings_store import DEFINITIONS
    text = (PROJECT / "DEPLOYMENT.md").read_text(encoding="utf-8")
    missing = [d.key for d in DEFINITIONS if f"`{d.key}`" not in text]
    assert missing == [], f"List these settings in DEPLOYMENT.md's Settings section: {missing}"
