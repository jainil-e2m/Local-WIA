"""S.B12 and R48: no transcript text is committed outside research/ and backend/knowledge_base/.

A transcript takes several shapes in this project: caption files and caption-timed lines (Zoom VTT, Fathom exports
flattened to cues), timestamped speaker lines ("00:01:51 Whitney Hodges: ..."), JSON turns (a speaker, the words and
a time, as Fathom and the research sources store them), quoted passages with their time and speaker (the old
fixtures' passage(...) calls), and client documents and reviews as office files or PDFs. Any of them outside the two
roots fails CI. The files below predate 18 October and are kept by the owner's decision (D7, V11); nothing is added
to that list, and a file leaves it when it is removed.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[3]
ALLOWED_ROOTS = ("research/", "backend/knowledge_base/")
KEPT_BEFORE_18_OCTOBER = frozenset({
    "client_documents/WIA - Content Angle Review.docx",
    "client_documents/content_guides/Strategy from Savannah.docx",
    "client_documents/content_guides/Wedding Industry Ads _ Tier 1 Accelerator Strategy Doc.docx",
    "client_documents/content_guides/Whitney _ Founder Voice Guide.docx",
    "client_review/week1_content_angles_feedback_tables.docx",
    "client_review/week1_content_angles_for_review.docx",
    "client_review/week1_content_angles_for_review_ui_fields.docx",
    "testing/document_qa/feedback_tables/render/word_review.pdf",
    "testing/document_qa/render/word_review.pdf",
    "testing/document_qa/ui_fields/render/word_review.pdf",
    "frontend/src/components/MomentsLedgerView.tsx",
    "frontend/src/data/mockData.ts",
    "mock-data/weekly-studio-2026-10-05.json",
})
# This file's own examples are invented dialogue.
THIS_FILE = "backend/backend_pipeline/tests/test_client_material_guard.py"
CAPTION_FILE = re.compile(r"\.(vtt|srt)$", re.IGNORECASE)
DOCUMENT_FILE = re.compile(r"\.(docx?|pdf|pptx?|xlsx?|rtf|odt)$", re.IGNORECASE)
CAPTION_LINE = re.compile(r"^\s*\d{2}:\d{2}:\d{2}[.,]\d{3} --> \d{2}:\d{2}:\d{2}[.,]\d{3}", re.MULTILINE)
NAME = r"[A-Z][\w.'’-]+(?: [A-Z][\w.'’-]+){0,3}"
TIMED_LINE = re.compile(r"^\s*\[?\(?\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?\)?\]?\s*[-–]?\s*" + NAME + r"\s*:", re.MULTILINE)
QUOTED_PASSAGE = re.compile(r"['\"]\d{1,2}:\d{2}(?::\d{2})?['\"]\s*,\s*['\"]" + NAME + r"['\"]\s*,\s*[\"'][^\"'\n]{12,}")
JSON_SPEAKER = re.compile(r"[\"']?speaker(?:_name)?[\"']?\s*:\s*[\"'][A-Z]")
JSON_WORDS = re.compile(r"[\"']?(?:text|excerpt|transcript|quote|utterance)[\"']?\s*:\s*[\"']")
JSON_TIME = re.compile(r"[\"']?(?:start(?:_seconds|_ms|_time)?|timestamp|time)[\"']?\s*:\s*[\"']?\d")


def transcript_shape(rel: str, text: str | None) -> str | None:
    """Why a tracked file looks like transcript or client material, or None."""
    if CAPTION_FILE.search(rel):
        return "caption file"
    if DOCUMENT_FILE.search(rel):
        return "office file or PDF"
    if text is None:
        return None
    if CAPTION_LINE.search(text):
        return "caption-timed lines"
    if len(TIMED_LINE.findall(text)) >= 3:
        return "timestamped speaker lines"
    if len(QUOTED_PASSAGE.findall(text)) >= 3:
        return "quoted passages with time and speaker"
    if min(len(JSON_SPEAKER.findall(text)), len(JSON_WORDS.findall(text)), len(JSON_TIME.findall(text))) >= 3:
        return "JSON transcript turns"
    return None


def tracked_files():
    if not shutil.which("git") or not (PROJECT / ".git").exists():
        pytest.skip("Needs a git checkout to list tracked files")
    out = subprocess.run(["git", "-c", "core.commitGraph=false", "ls-files", "-z"], cwd=PROJECT,
                         capture_output=True, check=True)
    return [p for p in out.stdout.decode("utf-8").split("\0") if p]


def test_no_transcript_text_outside_the_permitted_roots():
    offenders = []
    for rel in tracked_files():
        if rel.startswith(ALLOWED_ROOTS) or rel in KEPT_BEFORE_18_OCTOBER or rel == THIS_FILE:
            continue
        path = PROJECT / rel
        if not path.is_file():
            continue
        text = None
        if path.stat().st_size <= 5_000_000:
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                text = None
        if why := transcript_shape(rel, text):
            offenders.append(f"{rel} ({why})")
    assert offenders == [], ("Transcript text belongs under research/ or backend/knowledge_base/ (R48): "
                             + ", ".join(offenders))


@pytest.mark.parametrize("rel,text", [
    ("notes/call.vtt", ""),
    ("docs/client brief.docx", None),
    ("docs/call.md", "00:01:51 Whitney Hodges: The forms are the same.\n00:02:10 Carmen Cruickshank: Right.\n"
                     "00:02:30 Whitney Hodges: So we wait.\n"),
    ("frontend/src/data/week.ts", "passage('1', '00:01:51', 'Whitney Hodges', 'The forms are exactly the same.'),\n"
                                  "passage('1', '00:00:28', 'Carmen Cruickshank', 'Victor was saying we got seven leads'),\n"
                                  "passage('1', '00:09:30', 'Whitney Hodges', 'Give it a full eight days before we decide.'),"),
    ("backend/fixtures/turns.json", '[{"speaker": "Whitney", "text": "a", "start": 1}, {"speaker": "Carmen", "text": "b", '
                                    '"start": 2}, {"speaker": "Ivy", "text": "c", "start": 3}]'),
])
def test_each_transcript_shape_is_recognised(rel, text):
    assert transcript_shape(rel, text)


def test_the_kept_files_are_still_the_only_exceptions():
    """The exception list only shrinks: every entry is tracked and still looks like client material."""
    tracked = set(tracked_files())
    for rel in KEPT_BEFORE_18_OCTOBER:
        if rel not in tracked:
            continue
        path = PROJECT / rel
        text = path.read_text(encoding="utf-8") if not DOCUMENT_FILE.search(rel) else None
        assert transcript_shape(rel, text), f"{rel} no longer needs its exception; remove it from the list"
