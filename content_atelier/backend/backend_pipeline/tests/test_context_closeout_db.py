"""The close-out of Phase L on a migrated database: the committed delegated review empties the seed's queue and is
idempotent (L.F1, D12); an exported version reproduces its hashes (L.B4); a draft compiled from an older active
version cannot be approved (S.B2 review); an approver's entry is idempotent by key; the scheduler runs a job once
however many replicas claim it."""
from __future__ import annotations

import json
import re
import threading
from datetime import date

import pytest

from backend_pipeline import storage_cli
from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.database import connect
from backend_pipeline.knowledge import compiler, delegated, items, review, scheduler, seed
from backend_pipeline.knowledge_base import load_knowledge_base, load_published
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401

# Version 4, the committed default these tests were written against, archived on 19 October when version 5 replaced it.
ROOT = BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-18.c-0cb353e4"
ON = date(2026, 10, 20)
OWNER = "owner@example.invalid"
SETTINGS = StorageSettings(brief_approvers=(OWNER,))
seeded = pytest.mark.skipif(not (seed.REPOSITORY_ROOT / seed.DRAFTS).is_dir() or not (seed.REPOSITORY_ROOT / delegated.RECORD).is_file(),
                            reason="The export analysis drafts are not checked out")


@pytest.fixture
def conn(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url) as c:
        seed.run(c, actor="seed", approver=OWNER)
        yield c


def run_cli(capsys, *args):
    storage_cli.main(list(args))
    return json.loads(capsys.readouterr().out)


@seeded
def test_the_delegated_review_decides_every_candidate_once(platform_url, monkeypatch, capsys):  # noqa: F811
    empty(platform_url)
    monkeypatch.setenv("ATELIER_DATABASE_URL", platform_url)
    monkeypatch.setenv("ATELIER_BRIEF_APPROVERS", OWNER)
    monkeypatch.delenv("ATELIER_IDENTITY_APPROVERS", raising=False)
    run_cli(capsys, "context-seed", "--approver", OWNER, "--actor", "seed@example.invalid")
    record = delegated.load()
    first = run_cli(capsys, "context-review-apply", "--actor", OWNER)
    assert first["candidates_left"] == 0 and not first["stale"] and not first["missing"]
    assert sum(first["applied"].values()) == len(record["decisions"])
    assert first["published_confirmed"] == len(record["published_confirm"])
    second = run_cli(capsys, "context-review-apply", "--actor", OWNER)
    assert second["applied"] == {"accept": 0, "edit": 0, "reject": 0} and second["published_confirmed"] == 0
    assert second["already_decided"] == len(record["decisions"])
    with connect(platform_url) as c:
        # One decision per candidate, with the owner who ran it as reviewer, the delegated reviewer as author, a reason.
        rows = c.execute("""SELECT actor,note FROM decisions WHERE author=%s AND item_kind<>'published_content'
            AND action<>'context_enter'""", (delegated.AUTHOR,)).fetchall()
        # The record's edits to confirmed entries are approver entries, one decision each, with their reason.
        entered = c.execute("SELECT note FROM decisions WHERE author=%s AND action='context_enter'", (delegated.AUTHOR,)).fetchall()
        assert len(entered) == len(record.get("confirmed_edits") or []) and all(r["note"] for r in entered)
        assert len(rows) == len(record["decisions"]) and all(r["actor"] == OWNER and r["note"] for r in rows)
        assert c.execute("SELECT count(*) n FROM brand_kit_items WHERE model_written AND status='confirmed' AND reviewed_by IS NULL").fetchone()["n"] == 0
        # Every entry the review accepted is still confirmed: no accepted entry retired another one by sharing its key
        # (L.B2, L.B3), so everything accepted reaches the next compiled version. The record's own edits (E.B11, valid
        # from 20 October) replace the entries they edit: from that day on, entering one retires its predecessor.
        lost = c.execute("""SELECT i.source_ref FROM brand_kit_items i JOIN decisions d ON d.item_id=i.item_id
            WHERE d.author=%s AND d.action IN ('context_accept','context_edit') AND i.status<>'confirmed'
            AND NOT EXISTS (SELECT 1 FROM brand_kit_items n JOIN decisions e ON e.item_id=n.item_id AND e.action='context_enter'
                            WHERE n.key=i.key AND n.status='confirmed' AND e.author=%s)
            ORDER BY 1""", (delegated.AUTHOR, delegated.AUTHOR)).fetchall()
        assert not lost, [r["source_ref"] for r in lost]
        # Every exemplar that reaches the knowledge base had its em dashes normalised (V01).
        texts = [r["text"] for r in c.execute("SELECT text FROM brand_kit_items WHERE kind='exemplar' AND status='confirmed'")]
        assert texts and not any("—" in t for t in texts)
        # Every environment's store compiles a version that holds the held-out Week 6 out (E.B17): its result and the
        # pieces built on it are withheld, and the rules that used it as their example keep the rule without it.
        from backend_pipeline.knowledge import held_out
        version = compiler.compile_version(c, on=ON, actor=OWNER, root=ROOT)["version"]
        kb = load_published(c, version)
        assert not {d.entry.key for d in kb.documents if held_out.text_weeks(d.text)}
        assert "Give exact periods and a fair comparison" in kb.document("rejection_rules").text
        withheld = [w for r in c.execute("SELECT compiled_from FROM brand_kit_docs WHERE version=%s AND compiled_from IS NOT NULL",
                                         (version,)) for w in r["compiled_from"].get("withheld", [])]
        assert {"result", "exemplar"} <= {w["key"].split(":")[0] for w in withheld if w["key"]}

        # E.B11: every compiled rule shows its level, scope, category, date, author and origin; the table's legend and a
        # section's citation line are not rules; the rules the drafts give a code all arrive (none lost to a shared key).
        assert c.execute("SELECT count(*) n FROM brand_kit_items WHERE kind='rule' AND status='confirmed' AND NOT body ? 'category'"
                         ).fetchone()["n"] == 0
        rules = kb.document("rejection_rules").text
        lines = [line for line in rules.splitlines() if line.startswith("- ")]
        categories = "|".join(c.replace("_", " ") for c in items.RULE_CATEGORIES)
        shape = re.compile(rf"\((?:ban|flag); scope (?:angle|brief|all); (?:{categories}); (?:since|stated) .+; by .+; origin: .+\)$")
        assert len(lines) > 90 and all(shape.search(line) for line in lines), [x for x in lines if not shape.search(x)][:3]
        assert not any("reject or rewrite" in line or line.startswith("- Source:") for line in lines)
        assert all(f"- {code}:" in rules for code in ("A04", "A09", "A18", "P16", "P17", "V08", "V15", "V16", "R02", "R08", "R10"))
        assert "by the team" in rules and "by Whitney;" in rules, "authorship is shown (K49)"
        # Compiled documents list each entry once, never repeat their heading on each entry, and a compiled content
        # plan no longer calls itself a draft.
        for key in ("team_roster", "content_workflow", "process_catalogue", "audience_language"):
            text = kb.document(key).text
            entries = [line for line in text.splitlines() if line.startswith("- ")]
            assert len(entries) == len(set(entries)), key
            heading = None
            for line in text.splitlines():
                heading = line[3:] if line.startswith("## ") else heading
                assert not (heading and line.startswith(f"- {heading}:")), (key, line[:80])
        plan = kb.document("content_plan").entry
        assert plan.status == "confirmed" and "draft" not in plan.heading.lower()
        # The exemplar document leads with WIA's own copy and keeps contrastive pairs.
        exemplars = kb.document("exemplars").text
        assert "## Contrastive pairs" in exemplars and "Draft she replaced:" in exemplars


@seeded
def test_the_lint_patterns_derive_from_the_compiled_rules(platform_url, tmp_path):  # noqa: F811
    """E.B11 (2): the E.B10 lint reads the patterns of the version in force, compiled from its rules, never a hand-kept
    file: the store built from committed inputs reproduces the committed patterns, an exported version carries its own
    bound by hash, and a rule an approver adds later reaches the lint through the next version alone."""
    from backend_pipeline.cycle import verification
    empty(platform_url)
    with connect(platform_url) as c:
        seed.run(c, actor="seed", approver=OWNER)
        applied = delegated.apply(c, SETTINGS, OWNER)
        edits = delegated.load()["confirmed_edits"]
        assert applied["confirmed_edits"] == [f"{e['key']}: new version from {e['valid_from']}" for e in edits]
        assert applied["confirmed_edits"][0] == "rule:rr-09: new version from 2026-10-19"
        assert delegated.apply(c, SETTINGS, OWNER)["confirmed_edits"] == [f"{e['key']}: already applied" for e in edits]
        first = compiler.compile_version(c, on=ON, actor=OWNER, root=ROOT)
        patterns = compiler.version_patterns(c, first["version"])
        committed = json.loads((ROOT / compiler.PATTERNS_FILE).read_text(encoding="utf-8"))["rules"]
        assert compiler.lint_content(patterns) == compiler.lint_content(committed), "the rules reproduce the hand-kept list"
        assert next(p for p in patterns if p["id"] == "RR-09")["applies_to"] == "email"
        kb = compiler.export(c, first["version"], tmp_path / "kb")
        files = load_knowledge_base(tmp_path / "kb")
        assert files.rule_patterns == patterns and files.refs()["rule_patterns_sha256"] == files.rule_patterns_sha256
        assert kb["sha256"] == files.sha256
        # A hand edit beside the version is refused.
        hand = tmp_path / "kb" / compiler.PATTERNS_FILE
        hand.write_text(hand.read_text(encoding="utf-8").replace("RR-01", "RR-99", 1), encoding="utf-8")
        with pytest.raises(ValueError, match="does not match the hash"):
            load_knowledge_base(tmp_path / "kb")
        compiler.approve(c, SETTINGS, first["version"], OWNER, note="Reviewed the diff")
        compiler.record_benchmark(c, SETTINGS, first["version"], OWNER, passed=True, result_ref="smoke", note="")
        # A rule an approver confirms with a pattern: the next version's lint carries it, and the verifier uses it.
        review.enter(c, SETTINGS, OWNER, kind="rule", name="no guarantee words", body={
            "statement": "Never write 'guaranteed bookings'", "level": "ban", "scope": "all", "category": "factual",
            "patterns": [{"pattern": r"\bguaranteed\s+bookings\b", "kind": "ban", "scope": "all", "message": "A guarantee"}]},
            reason="Whitney's correction at Gate 2", valid_from=ON)
        second = compiler.compile_version(c, on=ON, actor=OWNER, root=ROOT)
        assert second["status"] == "compiled"
        assert any(p["message"] == "A guarantee" for p in compiler.version_patterns(c, second["version"]))
        assert not any(r["message"] == "A guarantee" for r in verification.store_rules(c, ROOT)), "not before approval"
        compiler.approve(c, SETTINGS, second["version"], OWNER, note="New rule")
        compiler.record_benchmark(c, SETTINGS, second["version"], OWNER, passed=True, result_ref="smoke", note="")
        assert any(r["message"] == "A guarantee" for r in verification.store_rules(c, ROOT))
        assert any(r["message"] == "A guarantee" for r in verification.rules_for(load_published(c, second["version"]), ROOT))


@seeded
def test_version_5_reproduces_from_the_committed_inputs(platform_url, monkeypatch):  # noqa: F811
    """L.B4, E.B11: the store built from the committed seed and review on 19 October, compiled on that day from the
    committed version 4, gives version 5 byte for byte: its name, every document and its lint patterns. Built on a later
    day, the review's edits of 20 October retire the entries they replace as they are entered, so the store gives
    version 6 (the next test) and no longer version 5."""
    from backend_pipeline.tests.test_held_out import V5
    supersede = items._supersede
    # The store as built on 19 October: an entry replacing another is judged against that day.
    monkeypatch.setattr(items, "_supersede", lambda conn, item_id, today=None: supersede(conn, item_id, today or date(2026, 10, 19)))
    empty(platform_url)
    with connect(platform_url) as c:
        seed.run(c, actor="seed", approver=OWNER)
        delegated.apply(c, SETTINGS, OWNER)
        compiled = compiler.compile_version(c, on=date(2026, 10, 19), actor=OWNER, root=ROOT)
        files = load_knowledge_base(V5)
        assert compiled["version"] == files.version
        assert compiled["documents"] == {d.entry.key: d.sha256 for d in files.documents}
        published = load_published(c, compiled["version"])
        assert published.rule_patterns_sha256 == files.rule_patterns_sha256 and published.text == files.text
        # Compiled on that date against version 5 itself, its store changes nothing; compiled on a later day, only
        # operating documents change, apart from the rule edits of 20 October (version 6). The archived folder carries no
        # supersessions list, so the superseded lines of 01 to 03 (E.B25 (c)) come only from the committed one.
        assert compiler.compile_version(c, on=date(2026, 10, 19), actor=OWNER, root=V5)["status"] == "unchanged"
        later = compiler.compile_version(c, on=date(2026, 11, 2), actor=OWNER, root=V5)
        assert later["status"] == "compiled" and {k for k, v in later["changes"].items() if v == "identity"} == {"rejection_rules"}


@seeded
def test_version_6_reproduces_and_refiles_rules_with_their_provenance(platform_url):  # noqa: F811
    """E.B11 (1), (4): the committed review's edits of 20 October, compiled on that day from the committed version 5, give
    version 6, the committed default, byte for byte. A refiled rule keeps its words, author, date and origin and changes only its
    category; the proof rule no longer quotes the figure a venue client vetoed."""
    from backend_pipeline.tests.test_held_out import V5, V6
    empty(platform_url)
    with connect(platform_url) as c:
        seed.run(c, actor="seed", approver=OWNER)
        delegated.apply(c, SETTINGS, OWNER)
        # Version 6 is the review's edits alone: without the superseded lines of 01 to 03 (E.B25 (c), version 7).
        compiled = compiler.compile_version(c, on=date(2026, 10, 20), actor=OWNER, root=V5, supersessions=False)
        files = load_knowledge_base(V6)
        assert compiler.compile_version(c, on=date(2026, 10, 20), actor=OWNER, root=V6, supersessions=False)["status"] == "unchanged"
        assert compiled["version"] == files.version and compiled["documents"] == {d.entry.key: d.sha256 for d in files.documents}
        assert {k for k, v in compiled["changes"].items() if v != "unchanged"} == {"rejection_rules"}
        published = load_published(c, compiled["version"])
        assert published.rule_patterns_sha256 == files.rule_patterns_sha256 and published.text == files.text
        before = load_knowledge_base(V5).document("rejection_rules").text.splitlines()
        after = files.document("rejection_rules").text.splitlines()
        changed = [(b, a) for b, a in zip(before, after) if b != a]
        assert len(before) == len(after) and len(changed) == 12
        meta = re.compile(r"\((ban|flag); scope (\w+); ([a-z ]+); (.+)\)$")
        refiled = [(b, a) for b, a in changed if "1,200" not in b]
        for b, a in refiled:
            old, new = meta.search(b), meta.search(a)
            assert b[:old.start()] == a[:new.start()] and old.group(4) == new.group(4) and old.group(3) != new.group(3), (b, a)
        assert not any("1,200" in line for line in after) and "the count of weddings it had hosted" in "\n".join(after)


@seeded
def test_version_7_reproduces_with_the_superseded_lines_and_applies_them_once(platform_url, tmp_path):  # noqa: F811
    """E.B25 (c): the committed review and the committed supersessions, compiled on 20 October from version 6, give the
    archived version 7 byte for byte; compiled from version 7 itself with the list beside it, nothing is applied again;
    a supplied document whose superseded line has changed stops the compile, naming the entry."""
    import shutil

    from backend_pipeline.knowledge import supersessions
    from backend_pipeline.tests.test_held_out import V6, V7
    from backend_pipeline.tests.test_kb9 import V9
    # Version 6 with the committed list beside it: the base version 7 was compiled from.
    committed = tmp_path / "v6"
    shutil.copytree(V6, committed)
    shutil.copy(V9 / supersessions.FILE, committed / supersessions.FILE)
    empty(platform_url)
    with connect(platform_url) as c:
        seed.run(c, actor="seed", approver=OWNER)
        delegated.apply(c, SETTINGS, OWNER)
        compiled = compiler.compile_version(c, on=date(2026, 10, 20), actor=OWNER, root=committed)
        files = load_knowledge_base(V7)
        assert compiled["version"] == files.version and compiled["documents"] == {d.entry.key: d.sha256 for d in files.documents}
        assert {k for k, v in compiled["changes"].items() if v != "unchanged"} == set(supersessions.DOCUMENTS)
        assert all(compiled["changes"][k] == "identity" for k in supersessions.DOCUMENTS), "a benchmark first (R44)"
        published = load_published(c, compiled["version"])
        assert published.text == files.text
        stored = c.execute("SELECT value FROM settings WHERE key=%s", (compiler.MANIFEST_PREFIX + compiled["version"],)).fetchone()["value"]
        assert stored["compiled"]["supersessions"]["remove_lines"] == 14 and len(stored["compiled"]["supersessions"]["applied"]) == 26
        # Compiled from version 7 with the list beside it, nothing is applied twice: the store already gives version 7.
        v7 = tmp_path / "v7"
        shutil.copytree(V7, v7)
        shutil.copy(V9 / supersessions.FILE, v7 / supersessions.FILE)
        assert compiler.compile_version(c, on=date(2026, 10, 20), actor=OWNER, root=v7)["status"] == "unchanged"
        c.rollback()
        # A supplied document that no longer holds a line the list names stops the compile and names it.
        changed = tmp_path / "changed"
        shutil.copytree(committed, changed)
        path = changed / "01-content-strategy.md"
        path.write_text(path.read_text(encoding="utf-8").replace("- Feast or famine inquiries.", "- Feast-or-famine inquiries."),
                        encoding="utf-8", newline="\n")
        with pytest.raises(ValueError, match=r"Supersession S09 \(content_strategy, R-8\).*found 0"):
            compiler.compile_version(c, on=date(2026, 10, 20), actor=OWNER, root=changed)


@seeded
def test_version_8_adds_the_editing_guide_once_and_its_strategist_prefix_fits_the_budget(platform_url, tmp_path, monkeypatch):  # noqa: F811
    """E.B25 (e): the committed review, the committed supersessions list and version 8's additions list (archived with it),
    compiled on 20 October from version 7, give the archived version 8 byte for byte: version 7 with the editing guide, an
    identity change (R44). Compiled from version 8 itself with the lists beside it, the guide is not added again; a
    guide whose text is not the reviewed one stops the compile. E.B25 (d): assembled from the store, version 8's
    strategist prefix is cut to the budget and the run records it."""
    import shutil
    from contextlib import nullcontext

    from backend_pipeline.knowledge import additions, assembly, supersessions
    from backend_pipeline.tests.test_held_out import V7, V8
    from backend_pipeline.tests.test_kb9 import V9
    monkeypatch.delenv("ATELIER_CONTEXT_PREFIX_TOKENS", raising=False)
    # Version 7 with the lists (and the guide they name) beside it: the base version 8 was compiled from. Version 8's
    # additions list is archived with it; the committed one also adds version 9's documents from 22 October.
    committed = tmp_path / "v7"
    shutil.copytree(V7, committed)
    shutil.copy(V9 / supersessions.FILE, committed / supersessions.FILE)
    for name in (additions.FILE, "17-editing-guide.md"):
        shutil.copy(V8 / name, committed / name)
    empty(platform_url)
    with connect(platform_url) as c:
        seed.run(c, actor="seed", approver=OWNER)
        delegated.apply(c, SETTINGS, OWNER)
        # Before the list's date the store still gives version 7.
        assert compiler.compile_version(c, on=date(2026, 10, 19), actor=OWNER, root=committed)["version"] != V8.name
        c.rollback()
        compiled = compiler.compile_version(c, on=date(2026, 10, 20), actor=OWNER, root=committed)
        files = load_knowledge_base(V8)
        assert compiled["version"] == files.version and compiled["documents"] == {d.entry.key: d.sha256 for d in files.documents}
        assert {k: v for k, v in compiled["changes"].items() if v != "unchanged"} == {"editing_guide": "identity"}
        published = load_published(c, compiled["version"])
        assert published.text == files.text
        stored = c.execute("SELECT value FROM settings WHERE key=%s", (compiler.MANIFEST_PREFIX + compiled["version"],)).fetchone()["value"]
        assert stored["compiled"]["additions"] == {"applied": ["A01"], "documents": ["editing_guide"]}
        assert stored["manifest"]["additions"]["applied"] == ["A01"]
        assert c.execute("SELECT benchmark_state FROM brand_kit_docs WHERE version=%s AND key='editing_guide'",
                         (compiled["version"],)).fetchone()["benchmark_state"] == "pending"
        kb = assembly.assemble("strategist", root=V8, connection=lambda: nullcontext(c), on=date(2026, 10, 20), version=files.version)
        record = kb.context["prefix_budget"]
        assert record["priority"] == "prefix-priority.v2" and record["tokens_before"] > 30000 >= record["tokens_after"]
        assert record["dropped"][:2] == ["content_workflow", "accelerator_strategy"] and "rejection_rules" not in record["dropped"]
        assert "editing_guide" in [d["key"] for d in kb.context["documents"]] and kb.context["over_budget"] is False
        # Compiled from version 8 with the lists beside it: nothing is applied or added twice.
        v8 = tmp_path / "v8"
        shutil.copytree(V8, v8)
        shutil.copy(V9 / supersessions.FILE, v8 / supersessions.FILE)
        assert compiler.compile_version(c, on=date(2026, 10, 20), actor=OWNER, root=v8)["status"] == "unchanged"
        c.rollback()
        (committed / "17-editing-guide.md").write_text("How Whitney edits: a line nobody reviewed.\n", encoding="utf-8")
        with pytest.raises(ValueError, match=r"Addition A01 \(editing_guide\)"):
            compiler.compile_version(c, on=date(2026, 10, 20), actor=OWNER, root=committed)


def test_a_confirmed_rule_without_a_category_fails_the_compile(conn):
    """E.B11 (1): a rule stored without a category (written before the field was required) stops the compile."""
    key = conn.execute("SELECT key FROM brand_kit_items WHERE kind='rule' AND status='confirmed' ORDER BY key LIMIT 1").fetchone()["key"]
    conn.execute("UPDATE brand_kit_items SET body=body-'category' WHERE key=%s", (key,))
    with pytest.raises(ValueError, match=f"no known category.*{re.escape(key)}"):
        compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)


def test_an_exported_version_reproduces_its_hashes(conn, tmp_path, platform_url, monkeypatch, capsys):  # noqa: F811
    version = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    conn.commit()
    monkeypatch.setenv("ATELIER_DATABASE_URL", platform_url)
    exported = run_cli(capsys, "kb-export", "--version", version, "--dir", str(tmp_path / "kb"))
    files = load_knowledge_base(tmp_path / "kb")
    published = load_published(conn, version)
    assert exported["documents"] == len(published.documents) and exported["sha256"] == files.sha256
    assert {d.entry.key: d.sha256 for d in files.documents} == {d.entry.key: d.sha256 for d in published.documents}
    assert files.version == version
    with pytest.raises(LookupError):
        compiler.export(conn, "wia-kb-missing", tmp_path / "none")


def test_a_draft_compiled_from_an_older_active_version_is_refused(conn):
    first = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    compiler.approve(conn, SETTINGS, first, OWNER, note="first")
    compiler.record_benchmark(conn, SETTINGS, first, OWNER, passed=True, result_ref="smoke", note="")
    review.enter(conn, SETTINGS, OWNER, kind="roster_member", name="First Hire", body={"name": "First Hire", "role": "Ads coordinator",
                                                                                     "state": "current"}, reason="Joined")
    second = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    review.enter(conn, SETTINGS, OWNER, kind="roster_member", name="Second Hire", body={"name": "Second Hire", "role": "Designer",
                                                                                      "state": "current"}, reason="Joined")
    third = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    assert compiler.approve(conn, SETTINGS, third, OWNER, note="both hires")["state"] == "active"
    with pytest.raises(ValueError, match="compile again"):
        compiler.approve(conn, SETTINGS, second, OWNER, note="would roll back the second hire")
    assert compiler.active_version(conn) == third
    assert "Second Hire" in load_published(conn, third).document("team_roster").text


def test_an_entry_with_an_idempotency_key_is_recorded_once(conn):
    body = {"name": "Robin Vale", "role": "Ads coordinator", "state": "current"}
    first = review.enter(conn, SETTINGS, OWNER, kind="roster_member", name="Robin Vale", body=body, reason="Joined",
                         idempotency_key="form-17")
    again = review.enter(conn, SETTINGS, OWNER, kind="roster_member", name="Robin Vale", body=body, reason="Joined",
                         idempotency_key="form-17")
    assert again["repeated"] is True and again["item_id"] == first["item_id"] and again["decision_id"] is None
    count = conn.execute("SELECT count(*) n FROM decisions WHERE action='context_enter' AND item_id=%s", (first["item_id"],)).fetchone()
    assert count["n"] == 1
    other = review.enter(conn, SETTINGS, OWNER, kind="roster_member", name="Robin Vale", body={**body, "role": "Designer"},
                         reason="Changed role", idempotency_key="form-18")
    assert other["item_id"] != first["item_id"] and other["supersedes_id"] == first["item_id"]


def test_the_scheduler_claims_a_job_once_across_replicas(platform_url):  # noqa: F811
    empty(platform_url)
    storage = StorageSettings(database_url=platform_url)
    results = []
    threads = [threading.Thread(target=lambda: results.append(scheduler._claim(storage, "context.staleness.ran.2026-10-20")))
               for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1 and len(results) == 6
    assert scheduler._claim(storage, "context.staleness.ran.2026-10-20") is False
    scheduler._finish(storage, "context.staleness.ran.2026-10-20", {"retired": 0})
    with connect(platform_url) as c:
        assert c.execute("SELECT value FROM settings WHERE key='context.staleness.ran.2026-10-20'").fetchone()["value"]["state"] == "done"


def test_a_diff_against_an_archived_file_version_uses_that_version(conn):
    """The seed's first compile is based on file version 2; once version 3 replaced it in backend/knowledge_base/, the
    diff still compares with version 2 (from archive/), not with the newer files."""
    version = compiler.compile_version(conn, on=ON, actor=OWNER, root=BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-18.v2")["version"]
    diff = compiler.diff(conn, version)
    assert diff["against"] == "wia-kb-2026-10-18.v2"
    roster = next(d for d in diff["documents"] if d["key"] == "team_roster")
    assert roster["diff"].startswith("--- wia-kb-2026-10-18.v2") and "+- Carmen Cruickshank:" in roster["diff"]


def test_whitneys_own_copy_leads_the_exemplars_and_approved_directions_stay_apart(conn):
    """The learning loop feeds the knowledge base without passing a model's draft off as WIA's voice: a brief section
    WIA approved in Content Atelier is listed apart, after every one of WIA's own finals, within its share; Whitney's
    finals come before finals a model drafted for her; contrastive pairs keep a share however many finals there are."""
    from datetime import date as day
    for i in range(6):
        items.add_item(conn, kind="exemplar", key=f"exemplar:final.{i}", body={"channel": "email", "text": f"Older approved final {i}. " * 40,
                       "label": "approved_final"}, status="confirmed", source_kind="approver_entry", source_ref=f"final-{i}",
                       author="Whitney", created_by=OWNER, reviewed_by=OWNER, statement_date=day(2026, 5, 1))
    items.add_item(conn, kind="exemplar", key="exemplar:final.polished", body={"channel": "email", "label": "approved_final",
                   "text": "A newer final ChatGPT drafted and Whitney approved."}, status="candidate", source_kind="export_seed",
                   source_ref="final-polished", author="ChatGPT draft approved by Whitney", created_by=OWNER, model_written=True,
                   statement_date=day(2026, 9, 1))
    polished = items.get_item(conn, conn.execute("SELECT item_id FROM brand_kit_items WHERE source_ref='final-polished'").fetchone()["item_id"])
    review.decide(conn, SETTINGS, polished["item_id"], polished["hash"], "accept", OWNER, reason="Her approved final")
    items.add_item(conn, kind="exemplar", key="exemplar:pair.1", body={"channel": "caption", "label": "preference_pair",
                   "text": "Her chosen caption line.", "ai_text": "The draft line she replaced."}, status="confirmed",
                   source_kind="approver_entry", source_ref="pair-1", author="Whitney", created_by=OWNER, reviewed_by=OWNER,
                   statement_date=day(2026, 3, 1))
    for i in range(8):
        items.add_item(conn, kind="exemplar", key=f"exemplar:brief.more.{i}", body={"channel": "brief", "text": f"Brief section {i}. " * 40,
                       "label": "approved_brief_supporting_example"}, status="candidate", source_kind="approved_brief",
                       source_ref=f"brief-more-{i}", author=f"model draft, approved by {OWNER}", created_by=OWNER, model_written=True,
                       statement_date=day(2026, 10, 18))
        row = items.get_item(conn, conn.execute("SELECT item_id FROM brand_kit_items WHERE source_ref=%s", (f"brief-more-{i}",)).fetchone()["item_id"])
        review.decide(conn, SETTINGS, row["item_id"], row["hash"], "accept", OWNER, reason="Approved direction")
    text = load_published(conn, compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]).document("exemplars").text
    voice, rest = text.split("## Contrastive pairs", 1)
    pairs, directions = rest.split("## Approved directions", 1)
    assert "Brief section" not in voice and "Brief section" in directions, "a model's draft is never a voice exemplar"
    assert voice.index("Older approved final") < voice.index("A newer final ChatGPT drafted"), "Whitney's own finals first"
    assert "The draft line she replaced." in pairs and "Her chosen caption line." in pairs
    assert len(directions) <= compiler.EXEMPLAR_DIRECTION_CHARACTERS + 200
    assert voice.count("Older approved final") >= 5
