"""A hand-built pack document (the layout of the v2 packs WIA reviewed on 20 October) read into v4 brief bodies, so the
first-touch and asset checks run on it exactly as on a written brief (E.B34, E.B24; `scripts/pack_checks.py`).

Only the copy is read: each pack's email (send header, subject, preview, body), its Reels (format, cover, on-screen hook,
script or screens, caption) and its carousel (title, slides, caption). Lines offered as a variant for another week ("For a
CONVERT week, add: ...") are not the pack's copy and are left out. Everything the checks do not read is filled with
placeholders. The pack files themselves live under `research/` (R48) and are never copied into the repository's tests.
"""
from __future__ import annotations

import re

_PACK = re.compile(r"^# Pack (\d+) · (ATTRACT|WARM|CONVERT)\s*$", re.M)
_SECTION = re.compile(r"^## (.+)$", re.M)
_FIELD = re.compile(r"^\*\*([A-Z][A-Za-z -]+?)(?: \([^)]*\))?:\*\*\s*(.*)$")
_VARIANT = re.compile(r"^\*For (?:a|an) [A-Z]+ week[^*]*\*")


def _clean(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text).strip()


def _paragraphs(block: str) -> list[str]:
    out = []
    for p in re.split(r"\n\s*\n", block.strip()):
        p = p.strip()
        if not p or p == "---" or _VARIANT.match(p):
            continue
        out.append(_clean(p))
    return out


def _caption(paragraphs: list[str]) -> dict | None:
    if not paragraphs:
        return None
    if len(paragraphs) == 1:
        return {"hook": paragraphs[0], "body": paragraphs[0], "ending": paragraphs[0]}
    return {"hook": paragraphs[0], "body": "\n\n".join(paragraphs[1:-1]) or paragraphs[0], "ending": paragraphs[-1]}


def _split_caption(block: str) -> tuple[str, dict | None]:
    head, _, tail = block.partition("**Caption:**")
    return head, _caption(_paragraphs(tail))


def _reel(title: str, block: str) -> dict:
    head, caption = _split_caption(block)
    fields, script_lines, screens, mode = {}, [], [], None
    for line in head.splitlines():
        if m := _FIELD.match(line.strip()):
            name = m.group(1).lower()
            mode = name
            if m.group(2):
                fields[name] = _clean(m.group(2))
            continue
        if mode == "script":
            script_lines.append(line)
        elif mode == "on-screen text" and (m := re.match(r"^\s*\d+\.\s+(.*)$", line)):
            screens.append(_clean(m.group(1)))
    form = fields.get("format", "")
    kind = "broll_text" if "b-roll" in form else "stance" if "stance" in form else "story"
    script = "\n\n".join(_paragraphs("\n".join(script_lines))) or None
    return {"kind": kind, "job": title, "register": "on_screen" if kind == "broll_text" else "spoken",
            "cover_text": fields.get("cover", ""), "on_screen_hook": fields.get("on-screen hook") or (screens[0] if screens else ""),
            "spoken_opening": (script or "").split("\n")[0] or None if kind != "broll_text" else None,
            "script": script if kind != "broll_text" else None, "screens": screens or None,
            "beats": [title], "personal_lines": [], "read_time_seconds": 60, "source": "new_script", "caption": caption}


def _carousel(title: str, block: str) -> dict:
    head, caption = _split_caption(block)
    slides = []
    for m in re.finditer(r"^\*\*Slide (\d+)\*\*\s*\n(.*?)(?=^\*\*Slide \d+\*\*|\Z)", head, re.M | re.S):
        lines = [ln for ln in m.group(2).strip().splitlines() if ln.strip() and not _VARIANT.match(ln.strip()) and ln.strip() != "---"]
        slides.append({"number": int(m.group(1)), "job": f"Slide {m.group(1)}", "text": _clean("\n".join(lines))})
    return {"job": title, "register": "written", "title": title, "slides": slides, "caption": caption}


def _email(block: str) -> dict:
    header, rest = {}, []
    for line in block.strip().splitlines():
        m = _FIELD.match(line.strip())
        if m and not rest:
            header[m.group(1).lower()] = _clean(m.group(2))
        else:
            rest.append(line)
    paragraphs = _paragraphs("\n".join(rest))
    greeting = next((i for i, p in enumerate(paragraphs) if p.lower().startswith(("hi ", "hello", "hey"))), 0)
    opening = "\n\n".join(paragraphs[greeting:greeting + 2])
    ending = "\n\n".join(paragraphs[-2:])
    body = "\n\n".join(paragraphs[greeting + 2:-2])
    return {"job": "The whole story", "register": "written",
            "send_header": {"date": header.get("date", ""), "send_time": header.get("send time", ""),
                            "recipients": header.get("recipients", "")},
            "subject_options": [header.get("subject", "")], "preview": header.get("preview text", ""),
            "opening": opening, "body": body, "ending": ending}


def parse_packs(text: str) -> list[dict]:
    """Each pack as {number, pillar, title, body}: `body` a v4 writer body with the pack's copy."""
    starts = list(_PACK.finditer(text))
    packs = []
    for i, m in enumerate(starts):
        chunk = text[m.end():starts[i + 1].start() if i + 1 < len(starts) else len(text)]
        chunk = chunk.split("\n## Before you publish")[0]
        title = (re.search(r"^### (.+)$", chunk, re.M) or [None, f"Pack {m.group(1)}"])[1].strip()
        sections = list(_SECTION.finditer(chunk))
        reels, carousel, email = [], None, None
        for j, s in enumerate(sections):
            block = chunk[s.end():sections[j + 1].start() if j + 1 < len(sections) else len(chunk)]
            name = s.group(1).strip()
            if name.startswith("Reel "):
                reels.append(_reel(name.split(":", 1)[-1].strip(), block))
            elif name.startswith("Carousel"):
                carousel = _carousel(name.split(":", 1)[-1].strip(), block)
            elif name == "Email":
                email = _email(block)
        body = {"approved_angle": {"title": title, "core_perspective": title}, "sharpened_point": None, "central_point": title,
                "strategic_purpose": {"pillar": m.group(2), "content_type": "pack", "why_now": "-", "desired_response": "-"},
                "intended_shift": {"understand": "-", "believe": "-", "do": None}, "audience": {"who": "-", "reason_to_care": "-"},
                "point_of_view": "we", "wia_perspective": "-",
                "supporting_example": {"scene": "-", "wia_move": "-", "client_contribution": "-", "timestamps": [], "details": [],
                                       "credits": [{"actor": "-", "did": "-"}]},
                "narrative_outline": {"hooks": [], "problems_desires_symptoms": ["-"], "main_point": "-", "transformation": "-", "cta": "-"},
                "cta": {"choice": "no_explicit_ask", "track": None, "action": None, "offer_connection": None, "chosen_by": "person"},
                "cta_why": "-", "before_publishing": [],
                "format_plan": {"reels": reels, "carousel": carousel, "email": email, "stories": None}}
        packs.append({"number": int(m.group(1)), "pillar": m.group(2), "title": title, "body": body})
    return packs


def check_packs(packs: list[dict], *, attested: dict | None = None, terms=None, offers=None) -> dict[int, list[dict]]:
    """The first-touch and asset checks on each pack, and the week checks across them. `attested` maps a pack number to the
    facts an approver attested for it (W8's fact is one)."""
    from .asset_checks import asset_findings, week_findings
    from .first_touch import first_touch_findings
    out = {}
    for p in packs:
        facts = (attested or {}).get(p["number"], [])
        found = first_touch_findings(p["body"], terms=terms, attested=facts)
        found += asset_findings(p["body"], pillar=p["pillar"], attested=facts, offers=offers)
        siblings = [{"brief_id": f"pack_{q['number']}", "title": q["title"], "body": q["body"]} for q in packs if q is not p]
        found += week_findings(p["body"], siblings)
        out[p["number"]] = found
    return out
