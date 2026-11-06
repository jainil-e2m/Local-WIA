"""Deterministic checks on a validated answer, before anything is stored or shown.

- A quote must be the source's own words: the same words in order in its ref's text (whitespace, punctuation and
  the first word's case may differ; the stored quote is then the exact source text). Ported from Content
  Atelier's moment_validation.repair_quote.
- Failed quote: a digest or brief item is dropped; a commitment is kept but marked unverified (a person reviews
  every proposed action anyway).
- A ref the prompt never showed: the item is dropped.
- `due_date` survives only with its timing words inside the quote, and within 180 days after the meeting.
- `owner_name` must be a name the input showed (a first name maps to the full name); `matches_action`,
  `action_ref` and `client` must be ones the input listed.
"""
import re
from datetime import date, timedelta

WORD = re.compile(r"\w+")
MIN_WORDS = 3


def exact_quote(quote: str, text: str) -> str | None:
    words = WORD.findall(quote or "")
    if len(words) < MIN_WORDS or not text:
        return None  # a two-word fragment proves nothing
    if quote in text:
        return quote
    tokens = list(WORD.finditer(text))
    found = [t.group(0) for t in tokens]
    for start in range(len(found) - len(words) + 1):
        window = found[start:start + len(words)]
        if window[1:] == words[1:] and window[0].lower() == words[0].lower():
            return text[tokens[start].start():tokens[start + len(words) - 1].end()]
    return None


class Checker:
    def __init__(self, refs, *, names: set[str], meeting_date: date | None, clients: set[str] = frozenset()):
        self.refs, self.meeting_date, self.clients = refs, meeting_date, clients
        self.names = {n for n in names if n}
        self.action_refs = {r for r in refs.items if r.startswith("A")}
        self.dropped: dict[str, int] = {}
        self.unverified = 0

    def _drop(self, what):
        self.dropped[what] = self.dropped.get(what, 0) + 1

    def quoted(self, item: dict) -> bool:
        """Point the item's quote at the exact source text; False when the ref or the words don't check out."""
        ref = item.get("ref")
        exact = exact_quote(item.get("quote", ""), self.refs.texts.get(ref, "")) if ref in self.refs.texts else None
        if exact is None:
            return False
        item["quote"] = exact
        return True

    def owner(self, name: str | None) -> str | None:
        if not name:
            return None
        low = name.strip().lower()
        for full in self.names:
            if full.lower() == low or full.lower().split()[0] == low:
                return full
        return None

    def due(self, item: dict) -> None:
        phrase, value = item.get("due_phrase"), item.get("due_date")
        if not value:
            return
        ok = bool(phrase) and phrase.lower() in item.get("quote", "").lower()
        try:
            when = date.fromisoformat(value)
            if self.meeting_date and not (self.meeting_date <= when <= self.meeting_date + timedelta(days=180)):
                ok = False
        except ValueError:
            ok = False
        if not ok:
            item["due_date"] = None

    def commitments(self, items: list[dict]) -> list[dict]:
        out = []
        for c in items:
            if c.get("ref") not in self.refs.items:
                self._drop("commitments")
                continue
            c["verified"] = self.quoted(c)
            self.unverified += not c["verified"]
            c["owner_name"] = self.owner(c.get("owner_name"))
            if c.get("matches_action") not in self.action_refs:
                c["matches_action"] = None
            if "client" in c and c["client"] not in self.clients:
                c["client"] = None
            self.due(c)
            out.append(c)
        return out

    def quoted_list(self, items: list[dict], what: str) -> list[dict]:
        out = []
        for item in items:
            if self.quoted(item):
                if "client" in item and item["client"] not in self.clients:
                    item["client"] = None
                out.append(item)
            else:
                self._drop(what)
        return out

    def updates(self, items: list[dict]) -> list[dict]:
        return [u for u in self.quoted_list(items, "action_updates") if u.get("action_ref") in self.action_refs]

    def ref_list(self, items: list[dict], what: str, *, optional=False) -> list[dict]:
        out = []
        for item in items:
            if item.get("ref") in self.refs.items or (optional and item.get("ref") is None):
                out.append(item)
            else:
                self._drop(what)
        return out


def check(skill_name: str, output: dict, checker: Checker) -> dict:
    o = dict(output)
    if "commitments" in o:
        o["commitments"] = checker.commitments(o["commitments"])
    if "decisions" in o:
        o["decisions"] = checker.quoted_list(o["decisions"], "decisions")
    if "action_updates" in o:
        o["action_updates"] = checker.updates(o["action_updates"])
    if skill_name in ("meeting_digest", "email_actions"):
        o["open_asks"] = checker.quoted_list(o.get("open_asks", []), "open_asks")
    if skill_name == "meeting_digest":
        o["answered"] = checker.ref_list(o["answered"], "answered")
    if skill_name == "history_moments":
        kept = []
        for m in o["moments"]:
            m["refs"] = [r for r in m["refs"] if r in checker.refs.items][:3]
            if m["refs"]:
                kept.append(m)
            else:
                checker._drop("moments")
        o["moments"] = kept[:15]
    if skill_name == "call_brief":
        o["asks"] = checker.quoted_list(o["asks"], "asks")
        o["since"] = checker.ref_list(o["since"], "since")
        o["type_block"] = checker.ref_list(o["type_block"], "type_block", optional=True)
        if o.get("opportunity") and o["opportunity"].get("ref") not in checker.refs.items:
            o["opportunity"] = None
            checker._drop("opportunity")
    return o
