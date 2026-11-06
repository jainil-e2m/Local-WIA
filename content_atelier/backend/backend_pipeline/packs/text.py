"""The copy of a pack's pieces as text: which leaves are copy, their sentences, and where a statement sits (Phase NP).

The fidelity loop reads and patches copy leaf by leaf, by the same dotted paths the editor writes (relative to a piece's
`content`). Direction (a Reel's kind, job, beats, read time, source), the CTA kinds and the working title are not copy.
"""
from __future__ import annotations

import difflib
import re

from ..briefs import paths

COPY_LEAF = {
    "email": re.compile(r"^(subject_options\[\d+\]|preview|opening|body|ending)$"),
    "reel": re.compile(r"^(cover_text|cover_alternates\[\d+\]|on_screen_hook|spoken_opening|script|screens\[\d+\]|"
                       r"caption\.(hook|body|ending)|no_offer_ending)$"),
    "carousel": re.compile(r"^(title|slides\[\d+\]\.text|caption\.(hook|body|ending)|no_offer_ending)$"),
}
FILLERS = re.compile(r"\b(um+|uh+|like|you know|kind of|sort of|i mean)\b[,]?\s*", re.I)
_SENTENCE = re.compile(r"(?<=[.!?])[\"')\]]*\s+|\n+")


def leaves(channel: str, content: dict | None) -> dict[str, str]:
    """The copy leaves of a piece, {path: text}, in document order; empty and null leaves left out."""
    if not content:
        return {}
    return {p: v for p, v in paths.leaves(content) if isinstance(v, str) and v.strip() and COPY_LEAF[channel].match(p)}


def norm(text: str) -> str:
    """Text compared loosely: curly quotes straightened, dashes and whitespace collapsed, lower case."""
    text = (text or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("—", "-").replace("–", "-").replace("**", "")
    return " ".join(text.lower().split())


def norm_quote(text: str) -> str:
    """A quote compared with its filler words dropped (fillers may be dropped from an exact quote)."""
    return " ".join(re.sub(r"[^\w\s']", " ", FILLERS.sub("", norm(text))).split())


def sentences(text: str) -> list[str]:
    return [s for s in (x.strip() for x in _SENTENCE.split(text or "")) if s]


def locate(piece_leaves: dict[str, str], statement: str) -> str | None:
    """The path of the leaf a statement sits in: an exact match after loose normalisation, else the leaf holding the most
    similar sentence when it is close enough (the check copies text, but a model may tidy punctuation)."""
    target = norm(statement)
    if not target:
        return None
    for path, text in piece_leaves.items():
        if target in norm(text):
            return path
    best, score = None, 0.0
    for path, text in piece_leaves.items():
        for s in sentences(text) or [text]:
            ratio = difflib.SequenceMatcher(None, target, norm(s)).ratio()
            if ratio > score:
                best, score = path, ratio
    return best if score >= 0.72 else None


def sentence_in(text: str, statement: str) -> str | None:
    """The sentence of a leaf that carries a statement (exact, or the most similar one when close enough)."""
    target = norm(statement)
    candidates = sentences(text) or [text]
    for s in candidates:
        if target and (target in norm(s) or norm(s) in target):
            return s
    scored = sorted(((difflib.SequenceMatcher(None, target, norm(s)).ratio(), s) for s in candidates), reverse=True)
    return scored[0][1] if scored and scored[0][0] >= 0.5 else None


def most_similar(sentence: str, text: str) -> tuple[str | None, float]:
    """The sentence of `text` most similar to `sentence`, with its similarity."""
    scored = sorted(((difflib.SequenceMatcher(None, norm(sentence), norm(s)).ratio(), s) for s in sentences(text) or [text]),
                    reverse=True)
    return (scored[0][1], scored[0][0]) if scored else (None, 0.0)


_STOP = frozenset("that this with what when where which while your their they them then than there these those have"
                  " from into about would could should been were will just more most other another every both through"
                  " also only some such very each".split())


def _content_words(sentence: str) -> set[str]:
    return {w.rstrip("s") for w in re.findall(r"[a-z']+", norm(sentence)) if len(w) >= 4 and w not in _STOP}


def repeats(sentence: str, others: list[str]) -> bool:
    """Whether `sentence` says again what one of `others` says: at least four content words in common, and at least 40%
    of the shorter one's (a brief sentence the finisher split in two, put back beside the half that was not flagged)."""
    mine = _content_words(sentence)
    for other in others:
        theirs = _content_words(other)
        shared = len(mine & theirs)
        if shared >= 4 and shared >= 0.4 * min(len(mine), len(theirs)):
            return True
    return False


def paragraph_of(text: str, sentence: str) -> str | None:
    """The paragraph (a run of text between blank lines) of `text` holding `sentence`."""
    for paragraph in re.split(r"\n\s*\n", text or ""):
        if sentence and norm(sentence) in norm(paragraph):
            return paragraph.strip()
    return None


def replace_once(text: str, old: str, new: str) -> str | None:
    """`text` with the first occurrence of `old` replaced; None when `old` is not in it (exact, then ignoring curly quotes
    and runs of whitespace)."""
    if old and old in text:
        return text.replace(old, new, 1)
    pattern = re.escape(old.strip()).replace(r"\ ", r"\s+")
    for a, b in (("'", "['’]"), ('"', "[\"“”]")):
        pattern = pattern.replace(re.escape(a), b)
    m = re.search(pattern, text) if old.strip() else None
    if not m:
        return None
    return text[:m.start()] + new + text[m.end():]


def tidy(text: str) -> str:
    """A leaf after a sentence was removed: no doubled spaces or empty lines left behind."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return re.sub(r" +\n", "\n", text).strip()
