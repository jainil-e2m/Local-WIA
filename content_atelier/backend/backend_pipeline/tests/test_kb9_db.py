"""Knowledge-base version 9 in the database suite (E.B25 (i), (j); L.B12): the store built from the committed inputs (the seed,
the delegated review, the published central points with the giveaway's pieces, the reviewed entries) and compiled on 22
October from the archived version 8 with the committed lists beside it gives the committed version 9 byte for byte, with
no model call; its new documents wait for a benchmark (R44); the reviewed entries enter once; and compiling never
activates it (its reading in phase N2, D40, did)."""
from __future__ import annotations

import shutil
from datetime import date

import pytest

from backend_pipeline import storage_cli
from backend_pipeline.database import connect
from backend_pipeline.knowledge import compiler, delegated, entries, published_points, seed
from backend_pipeline.knowledge_base import load_knowledge_base, load_published
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401
from backend_pipeline.tests.test_held_out import V8
from backend_pipeline.tests.test_kb9 import V9

OWNER = "owner@example.invalid"
SETTINGS = StorageSettings(brief_approvers=(OWNER,))
ON = date(2026, 10, 22)
seeded = pytest.mark.skipif(not (seed.REPOSITORY_ROOT / seed.DRAFTS).is_dir() or not (seed.REPOSITORY_ROOT / delegated.RECORD).is_file(),
                            reason="The export analysis drafts are not checked out")


def committed_inputs(tmp_path):
    """The archived version 8 with the committed lists and the two documents they add beside it: the base version 9
    compiles from."""
    root = tmp_path / "v8"
    shutil.copytree(V8, root)
    for name in ("supersessions.json", "additions.json", "18-spoken-voice.md", "19-transformations.md"):
        shutil.copy(V9 / name, root / name)
    return root


@seeded
def test_version_9_reproduces_from_the_committed_inputs_without_activating(platform_url, tmp_path, monkeypatch, capsys):  # noqa: F811
    root = committed_inputs(tmp_path)
    empty(platform_url)
    with connect(platform_url) as c:
        seed.run(c, actor="seed", approver=OWNER)
        delegated.apply(c, SETTINGS, OWNER)
        published_points.apply(c, SETTINGS, OWNER)
        c.commit()
    monkeypatch.setenv("ATELIER_DATABASE_URL", platform_url)
    monkeypatch.setenv("ATELIER_BRIEF_APPROVERS", OWNER)
    storage_cli.main(["context-entries-apply", "--actor", OWNER])
    import json
    first = json.loads(capsys.readouterr().out)
    assert first["entered"] == first["entries"] and not first["missing"]
    storage_cli.main(["context-entries-apply", "--actor", OWNER])
    again = json.loads(capsys.readouterr().out)
    assert again["entered"] == 0 and again["already_entered"] == first["entries"], "idempotent"
    with connect(platform_url) as c:
        # Before the lists' date the new documents are not added.
        assert "spoken_voice" not in compiler.compile_version(c, on=date(2026, 10, 21), actor=OWNER, root=root)["changes"]
        c.rollback()
        compiled = compiler.compile_version(c, on=ON, actor=OWNER, root=root)
        files = load_knowledge_base(V9)
        assert compiled["version"] == files.version and compiled["documents"] == {d.entry.key: d.sha256 for d in files.documents}
        assert {k: v for k, v in compiled["changes"].items() if v != "unchanged"} == {
            "offer_sheet": "operating", "format_guide": "identity", "recent_published": "operating",
            "spoken_voice": "identity", "transformations": "identity"}
        assert load_published(c, compiled["version"]).text == files.text
        assert c.execute("SELECT count(*) n FROM brand_kit_docs WHERE version=%s AND benchmark_state='pending'",
                         (compiled["version"],)).fetchone()["n"] == 3, "an identity change waits for its benchmark (R44)"
        assert compiler.active_version(c) is None, "compiling never activates a version"
        # Compiled from the committed folder itself (what a new environment checks, DEPLOYMENT.md production step 5),
        # nothing is added twice.
        assert compiler.compile_version(c, on=ON, actor=OWNER, root=V9)["status"] in ("unchanged", "exists")


@seeded
def test_a_reviewed_edit_without_its_confirmed_line_is_reported_not_invented(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url) as c:
        seed.run(c, actor="seed", approver=OWNER)  # the delegated review has not confirmed the format guide's lines
        result = entries.apply(c, SETTINGS, OWNER)
        assert result["missing"] == ["format:format-guide.carousel.bullet01"]
        with pytest.raises(PermissionError):
            entries.apply(c, SETTINGS, "viewer@example.invalid")
