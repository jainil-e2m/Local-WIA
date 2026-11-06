"""The week's pack document (NP.B12; the content-packs plan, sections 4.4 and 5.6): Markdown in the layout WIA reviewed.

It extends the week's review document (`briefs/review_document.py`, the "# Pack N" layout of the 13 and 20 October
documents) with what a content pack adds. On top, the week's plan (the proposed slots, the bank and the week's findings,
`week.plan`). Then, per pack in rank order: the angle card, the brief's strategy, every piece in its final form and
unabbreviated in the export order (the email with its DATE, SEND TIME, RECIPIENTS, every subject option, the preview and the
whole email; each Reel with its title, cover and alternates, on-screen hook, whole script or screens and whole caption; the
carousel slide by slide with its caption), then "Before you publish" with every note (a client's permission as a note for
whoever posts) and the client quotes to clear.

Output is labelled by its maker (R58): "System output: finished by the content-pack step from the approved brief", and
"Approved by the team under delegation; Whitney has not reviewed it" where that is true (R55). No model call; read only.
`document_docx.py` renders this Markdown as the .docx (`GET /weeks/{id}/packs.docx`).
"""
from __future__ import annotations

from datetime import UTC, datetime

from ..briefs import review_document as rd
from ..briefs.contracts_v4 import format_words, premise_lines
from ..production_common import ProductionError
from . import checks, model, views, week
from . import contracts_v2 as c2

MADE_BY = "System output: finished by the content-pack step from the approved brief"
DELEGATED = "Approved by the team under delegation; Whitney has not reviewed it"
STATES = {"finishing": "still finishing", "waiting": "waiting", "in_review": "generated", "ready_to_publish": "generated"}
CTA_WORDS = {"reply": "a reply", "link": "a link", "none": "no ask", "soft": "a soft invitation", "offer": "the offer ask",
             "no_offer": "no offer ask"}


def _date(value) -> str:
    return value.strftime("%d %B %Y") if hasattr(value, "strftime") else str(value or "")[:10]


def week_plan(w: rd.Writer, plan: dict):
    w.add("## The week's plan")
    w.gap()
    w.add(f"*Proposed for the publishing week of {plan['publishing_week_start']} to {plan['publishing_week_end']}: suggestions, "
          "computed when this document was made. Nothing is scheduled or published by the system.*")
    w.gap()
    for slot in plan["slots"]:
        what = (f"{slot['piece_label']} of \"{slot['title']}\"" if slot.get("piece") else "nothing proposed")
        cta = f" · {CTA_WORDS.get(slot.get('cta'), slot.get('cta'))}" if slot.get("cta") else ""
        w.add(f"- **{slot['label']}** ({slot['weekday']} {slot['date']}): {what}{cta}" + (f". {slot['note']}" if slot.get("note") else ""))
    w.gap()
    if plan["bank"]:
        w.add("### The bank")
        w.gap()
        w.add(*[f"- {b['piece_label']} of \"{b['title']}\": suggested for week {b['suggested_week']} after this one ({b['reason']})"
                for b in plan["bank"]])
        w.gap()
    if plan["findings"]:
        w.add("### The week's checks")
        w.gap()
        w.add(*[f"- {f['severity']}: {f['message']}" + (f" ({'; '.join(f['pieces'])})" if f.get("pieces") else "") for f in plan["findings"]])
        w.gap()


def email(w: rd.Writer, content: dict):
    w.add("## Email")
    w.gap()
    header = content.get("send_header") or {}
    w.add(f"**DATE:** {header.get('date') or ''}", f"**SEND TIME:** {header.get('send_time') or ''}",
          f"**RECIPIENTS:** {header.get('recipients') or ''}")
    w.gap()
    w.add("**SUBJECT OPTIONS (best first):**")
    w.gap()
    w.add(*[f"{i}. {s}" for i, s in enumerate(content.get("subject_options") or [], 1)])
    w.gap()
    w.field("PREVIEW TEXT", content.get("preview"))
    for part in ("opening", "body", "ending"):
        if rd.present(content.get(part)):
            w.add(str(content[part]).strip())
            w.gap()
    w.field("CTA", CTA_WORDS.get(content.get("cta"), content.get("cta")))
    w.field("Offer descriptor", content.get("offer_descriptor"))


def caption(w: rd.Writer, value: dict | None):
    if not value:
        return
    w.add("**Caption:**")
    w.gap()
    for part in ("hook", "body", "ending"):
        if rd.present(value.get(part)):
            w.add(str(value[part]).strip())
            w.gap()


def reel(w: rd.Writer, key: str, piece: dict):
    content = piece.get("content")
    kind = (content or {}).get("kind") or c2.KEY_KIND[key]
    heading = f"## {c2.LABELS[key]} · {format_words(content or {'kind': kind}) or kind}"
    if not content:
        w.add(heading)
        w.gap()
        w.add(f"Not written: {piece.get('not_written_reason') or 'no reason was recorded'}.")
        w.gap()
        return
    w.add(f"{heading}: {content.get('title') or content.get('cover_text')}")
    w.gap()
    w.field("Title", content.get("title"))
    # Round 2: the Reel's own premise and why it differs, and where its material is in the calls, apart from the copy.
    for label, text in premise_lines(content):
        w.field(label, text)
    w.field("Material in the calls", content.get("timestamps"))
    w.field("Cover", content.get("cover_text"))
    w.field("Cover alternates", content.get("cover_alternates"))
    w.field("On-screen hook", content.get("on_screen_hook"))
    w.field("Spoken opening", content.get("spoken_opening"))
    if content.get("screens"):
        w.block("On-screen text", content["screens"])
    w.block("Script", content.get("script"))
    caption(w, content.get("caption"))
    w.field("Personal lines for Whitney to keep or cut", content.get("personal_lines"))
    w.field("Without the offer ask, it ends", content.get("no_offer_ending"))
    w.field("Read time", f"about {content['read_time_seconds']} seconds" if content.get("read_time_seconds") else None)
    w.field("CTA", CTA_WORDS.get(content.get("cta"), content.get("cta")))
    w.field("Offer descriptor", content.get("offer_descriptor"))


def carousel(w: rd.Writer, content: dict):
    w.add(f"## Carousel: {content.get('title')}")
    w.gap()
    w.field("Title", content.get("title"))
    for slide in content.get("slides") or []:
        w.add(f"**Slide {slide['number']}**")
        w.add(*str(slide.get("text") or "").strip().splitlines())
        w.gap()
    caption(w, content.get("caption"))
    w.field("Without the offer ask, it ends", content.get("no_offer_ending"))
    w.field("CTA", CTA_WORDS.get(content.get("cta"), content.get("cta")))
    w.field("Offer descriptor", content.get("offer_descriptor"))


def _done(mark: dict | None, word: str) -> str:
    if not mark:
        return ""
    said = f" {word} by {mark['by']} on {str(mark['at'])[:10]}" + (" under delegation" if mark.get("delegated") else "")
    return said + (f" (reference: {mark['reference']})" if mark.get("reference") else "") + (f" ({mark['note']})" if mark.get("note") else "") + "."


def before_publishing(w: rd.Writer, body: dict, number: int, blockers: list[str]):
    w.add(f"## Before you publish Pack {number}")
    w.gap()
    for note in body.get("before_publishing") or []:
        who = "For whoever posts: the client's okay. " if note.get("client_permission") else ""
        answer = f" Answer: {note['answer']}" if note.get("answer") else " Unanswered."
        w.add(f"- {note['id']}{' (required)' if note.get('required') else ''}: {who}{note['text']}{answer}" + _done(note.get("done"), "Done"))
    if not body.get("before_publishing"):
        w.add("- Nothing to settle from the brief.")
    w.gap()
    quotes = body.get("client_quotes") or []
    w.add("### Client quotes to clear before posting")
    w.gap()
    w.add(*([f"- {q['quote_id']} ({c2.LABELS.get(q['piece'], q['piece'])}): \"{q['quote']}\"" + (f", {q['speaker']}" if q.get("speaker") else "")
             + (_done(q.get("cleared"), " Cleared") or ". Not cleared yet.") for q in quotes] or ["- No client quotes in this pack."]))
    w.gap()
    if body.get("stronger_with_permission"):
        w.field("Stronger with permission", body["stronger_with_permission"])
    if body.get("pack_notes"):
        w.field("Notes from the content-pack step", body["pack_notes"])
    if blockers:
        w.field("Not ready yet", blockers)


def markdown(repo, week_id: str, actor=None, *, exported: datetime | None = None) -> str:
    """GET /weeks/{id}/packs.md: the week's packs, every piece unabbreviated, the week's plan on top."""
    plan = week.plan(repo, week_id, actor)
    exported = exported or datetime.now(UTC)
    with repo.connection() as conn:
        row = conn.execute("SELECT * FROM weeks WHERE week_id=%s", (week_id,)).fetchone()
        if not row:
            raise ProductionError("Week not found", "not_found", 404)
        order = {p["pack_id"]: n for n, p in enumerate(plan["packs"])}
        packs = sorted(conn.execute("""SELECT * FROM content_packs p WHERE p.week_id=%s AND p.contract_version=%s
            AND NOT EXISTS (SELECT 1 FROM content_packs n WHERE n.supersedes_id=p.pack_id)""", (week_id, c2.VERSION)).fetchall(),
                       key=lambda p: order.get(p["pack_id"], len(order)))
        w = rd.Writer()
        w.add("# Content Atelier Packs", "", "The week's content packs", "", "Wedding Industry Ads", "")
        w.add(f"**Week:** {_date(row['week_start'])} to {_date(row['week_end'])}")
        w.add(f"**Made by:** {MADE_BY}. Lines a person wrote or edited are kept word for word and named in the pack's versions.")
        w.add(f"**Exported:** {exported:%d %B %Y, %H:%M} UTC")
        w.add(f"**In this document:** {len(packs)} {'pack' if len(packs) == 1 else 'packs'}, each with one email, three Reels and one carousel")
        w.gap()
        week_plan(w, plan)
        if not packs:
            w.add("No content packs for this week yet: a pack is made when Gate 2 approves a v4 brief.")
            w.gap()
        for number, pack in enumerate(packs, 1):
            state, reason = model.state_of(conn, pack)
            body = pack.get("content_body") or {}
            brief = views.brief_of(conn, pack)
            angle = conn.execute("SELECT * FROM content_angles WHERE angle_id=%s", (brief["angle_id"],)).fetchone() or {}
            card = (angle.get("content_body") or {}).get("card") or {}
            w.add("---", "", f"# Pack {number} · {body.get('pillar') or card.get('pillar') or 'IDEA'}: {pack['title']}", "")
            label = MADE_BY + ("; " + DELEGATED if views.approval_delegated(conn, pack) else "")
            w.add(f"*{label}.*")
            w.gap()
            status = STATES.get(state, state)
            w.field("State", status + (f": {reason}" if reason else ""))
            w.add("## Content angle")
            w.gap()
            w.add(f"### {card.get('title') or pack['title']}")
            w.gap()
            if card:
                rd.card_section(w, card, angle)
            w.add("## Content brief")
            w.gap()
            brief["version_number"] = conn.execute("""WITH RECURSIVE chain AS (SELECT brief_id,supersedes_id FROM content_briefs
                WHERE brief_id=%s UNION ALL SELECT b.brief_id,b.supersedes_id FROM content_briefs b JOIN chain c ON b.brief_id=c.supersedes_id)
                SELECT count(*) AS n FROM chain""", (brief["brief_id"],)).fetchone()["n"]
            w.add(f"*{rd.brief_maker(brief)}.*")
            w.gap()
            rd.brief_section(w, ((brief["content_body"] or {}).get("document") or {}).get("body") or {}, rd.BRIEF_SECTIONS)
            if not body:
                w.add(f"The pack is {status}; its pieces appear here once it is finished.")
                w.gap()
                continue
            rows = model.pieces(conn, pack["pack_id"])
            bodies = checks.bodies_of(rows)
            for key in c2.EXPORT_ORDER:
                piece = bodies.get(key) or {}
                if key.startswith("reel_"):
                    reel(w, key, piece)
                elif not piece.get("content"):
                    w.add(f"## {c2.LABELS[key]}", "", f"Not written: {piece.get('not_written_reason') or 'no reason was recorded'}.", "")
                elif key == "email":
                    email(w, piece["content"])
                else:
                    carousel(w, piece["content"])
            blockers = views.ready_blockers(bodies, checks.findings(conn, pack, bodies, brief))
            before_publishing(w, body, number, blockers)
    return w.text()
