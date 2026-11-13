"""Checks on a brief before anything is stored or shown. A failing line is dropped and logged; if the core
(goal and standing) fails, the runner asks once for a repair and otherwise rejects the brief, and the call keeps
showing the facts and the previous good version.

- refs: every item cites refs the pack showed; an item with none left is dropped.
- no new numbers: every figure in the model's text must appear in the pack (the idea of Content Atelier's
  cycle/verification.py digits_in / figures_in, copied here: the two projects don't share code).
- length: the skill's caps.
- leave out: a line containing one of the skill's leave_out_terms is dropped.
"""
import re

REF_LABEL = re.compile(r"\[?\b[AQWHDESLPFXCT]\d+\b\]?")
SOURCE_NUMBER = re.compile(r"\$?\d[\d,]*(?:\.\d+)?")
# Money, percentages, counts with a unit and bare numbers of two or more digits. Single digits ("one call", "3
# things") are too common in plain writing to check.
QUANTITY = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?[kKmM]?|\d[\d,]*(?:\.\d+)?\s?%|\d[\d,]*(?:\.\d+)?(?=\s?(?:days?|weeks?|months?|"
                      r"leads?|inquir\w*|tours?|clicks?|calls?|emails?|tasks?|bookings?|x\b))|\b\d{2,}[\d,]*(?:\.\d+)?\b")


def _digits(text: str) -> str:
    d = re.sub(r"[^\d.]", "", text).rstrip(".")
    return d[:-2] if d.endswith(".0") else d.rstrip("0").rstrip(".") if "." in d else d


def digits_in(texts) -> set[str]:
    out = set()
    for text in texts:
        for m in SOURCE_NUMBER.finditer(REF_LABEL.sub(" ", text or "")):
            out.add(_digits(m.group(0)))
    return out


def figures_in(text: str) -> list[tuple[str, str]]:
    clean = REF_LABEL.sub(" ", text or "")
    return [(m.group(0).strip(), d) for m in QUANTITY.finditer(clean) if (d := _digits(m.group(0)))]


class BriefChecks:
    def __init__(self, skill, refs, source_texts):
        self.skill, self.refs = skill, set(refs)
        self.allowed = digits_in(source_texts)
        self.dropped: list[dict] = []

    def _new_figure(self, text: str) -> str | None:
        return next((words for words, d in figures_in(text) if d not in self.allowed), None)

    def _left_out(self, text: str) -> str | None:
        low = (text or "").lower()
        return next((t for t in self.skill.leave_out_terms if re.search(rf"\b{re.escape(t)}\b", low)), None)

    def line_ok(self, where: str, *texts: str) -> bool:
        for text in texts:
            if not text:
                continue
            fig = self._new_figure(text)
            if fig:
                self.dropped.append({"where": where, "why": f"figure not in the sources: {fig}", "text": text[:200]})
                return False
            term = self._left_out(text)
            if term:
                self.dropped.append({"where": where, "why": f"leave-out topic: {term}", "text": text[:200]})
                return False
        return True

    def items(self, where: str, items: list[dict], fields: tuple[str, ...], cap: int, *, need_refs=True) -> list[dict]:
        out = []
        for item in items:
            if "refs" in item:
                item["refs"] = [r for r in item["refs"] if r in self.refs][:3]
                if need_refs and not item["refs"]:
                    self.dropped.append({"where": where, "why": "no ref from the sources", "text": item.get("text", "")[:200]})
                    continue
            if self.line_ok(where, *(item.get(f) or "" for f in fields)):
                out.append(item)
        if len(out) > cap:
            self.dropped.append({"where": where, "why": f"over the cap of {cap}", "text": f"{len(out) - cap} items"})
        return out[:cap]

    def run(self, output: dict) -> tuple[dict, list[str]]:
        """(checked output, core failures). Core failures: goal or standing failing a check."""
        o, L = dict(output), self.skill.length
        core = []
        for name in ("goal", "standing"):
            if not self.line_ok(name, o.get(name) or "") or not (o.get(name) or "").strip():
                core.append(name)
        if o.get("risk") and not self.line_ok("risk", o["risk"]):
            o["risk"] = None
        o["talking_points"] = self.items("talking_points", o.get("talking_points", []), ("text", "why"), L["points"])
        o["questions"] = self.items("questions", o.get("questions", []), ("text",), L["questions"], need_refs=False)
        o["watch_outs"] = self.items("watch_outs", o.get("watch_outs", []), ("text",), L["watch"])
        opp = o.get("opportunity")
        if opp and not self.items("opportunity", [opp], ("text", "why"), 1):
            o["opportunity"] = None
        facts = []
        for t in o.get("type_block", []):
            if t.get("ref") is not None and t["ref"] not in self.refs:
                t["ref"] = None
            if self.line_ok("type_block", t["label"], t["value"]):
                facts.append(t)
        o["type_block"] = facts
        o["changed_highlights"] = [r for r in o.get("changed_highlights", []) if r in self.refs and r.startswith("H")][:L["highlights"]]
        return o, core
