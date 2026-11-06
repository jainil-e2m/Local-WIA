"""A v4 brief as Whitney reads it (E.B33): the Markdown export, in the 13 October order and the layout of the packs WIA
reviewed on 20 October (the brief, then the email with its send header, each Reel, the carousel), then the ledger, the prior
coverage and the checks. Rendered from the brief's structure, with no model call."""
from __future__ import annotations

from . import turns
from .contracts_v4 import format_words, premise_lines
STATUS = {"bound": "bound to the call", "supported": "checked by the verifier", "unsupported": "not supported",
          "unchecked": "not checked", "kept_by_person": "kept by a person", "attested": "attested by a person"}


def _caption(c: dict | None) -> list[str]:
    if not c:
        return []
    return ["**Caption:**", "", c["hook"], "", c["body"], "", c["ending"], ""]


def asset_lines(plan: dict) -> list[str]:
    """The finished copy of every asset, in the order the review document shows them."""
    lines = []
    if e := plan.get("email"):
        h = e["send_header"]
        lines += ["## Email", "", f"**DATE:** {h['date']}", f"**SEND TIME:** {h['send_time']}", f"**RECIPIENTS:** {h['recipients']}",
                  "**SUBJECT:** " + e["subject_options"][0]]
        if len(e["subject_options"]) > 1:
            lines += ["**OTHER SUBJECTS:** " + " | ".join(e["subject_options"][1:])]
        lines += [f"**PREVIEW TEXT:** {e['preview']}", "", e["opening"], "", e["body"], "", e["ending"], ""]
        if e.get("offer_descriptor"):
            lines += [f"Offer descriptor: {e['offer_descriptor']}", ""]
    for i, r in enumerate(plan.get("reels") or [], 1):
        lines += [f"## Reel {i}: {r['job']}", "", f"**Format:** {format_words(r)}",
                  *[f"**{label}:** {text}" for label, text in premise_lines(r)], f"**Cover:** {r['cover_text']}",
                  f"**On-screen hook:** {r['on_screen_hook']}",
                  f"**Read time:** about {r['read_time_seconds']} seconds ({r['source'].replace('_', ' ')})", ""]
        if r.get("screens"):
            lines += [f"**On-screen text ({len(r['screens'])} screen{'s' if len(r['screens']) != 1 else ''}):**"]
            lines += [f"{n}. {s}" for n, s in enumerate(r["screens"], 1)] + [""]
        if r.get("script"):
            lines += ["**Script:**", "", r["script"], ""]
        elif r.get("spoken_opening"):
            lines += [f"**Opening:** {r['spoken_opening']}", ""]
        lines += ["Beats: " + "; ".join(r["beats"]), ""]
        if r.get("personal_lines"):
            lines += ["Personal lines for Whitney to keep or cut: " + " | ".join(r["personal_lines"]), ""]
        lines += _caption(r.get("caption"))
        if r.get("offer_descriptor"):
            lines += [f"Offer descriptor: {r['offer_descriptor']}", ""]
    if c := plan.get("carousel"):
        lines += [f"## Carousel: {c['title']}", ""]
        for s in c["slides"]:
            lines += [f"**Slide {s['number']}** ({s['job']})", s["text"], ""]
        lines += _caption(c.get("caption"))
        if c.get("offer_descriptor"):
            lines += [f"Offer descriptor: {c['offer_descriptor']}", ""]
    if plan.get("stories"):
        lines += ["## Stories", ""] + ["- " + x for x in plan["stories"]["frames"]] + [""]
    return lines


def markdown_v4(row: dict) -> str:
    from .gate_two import prior_coverage_lines
    doc = row["content_body"]["document"]
    h, b = doc["header"], doc["body"]
    a, sp, ex, outline, plan = b["approved_angle"], b["strategic_purpose"], b["supporting_example"], b["narrative_outline"], b["format_plan"]
    lines = ["# " + a["title"], "", a["core_perspective"], ""]
    if b.get("sharpened_point"):
        lines += ["Sharper point (proposed): " + b["sharpened_point"]["text"], "Why: " + b["sharpened_point"]["reason"], ""]
    lines += ["## Central point", "", b["central_point"], "",
              "## Strategic purpose and desired response", "", f"{sp['pillar']} · {sp['content_type'].replace('_', ' ')}", "",
              sp["why_now"], "", f"Desired response: {sp['desired_response']}", "",
              "- Understand: " + b["intended_shift"]["understand"], "- Believe: " + b["intended_shift"]["believe"],
              *(["- Do: " + b["intended_shift"]["do"]] if b["intended_shift"].get("do") else []), "",
              "## Audience and reason to care", "", b["audience"]["who"], "", b["audience"]["reason_to_care"], "",
              "## WIA perspective", "", b["wia_perspective"], "",
              "## Supporting example", "", ex["scene"], "", "What WIA did: " + ex["wia_move"], "",
              "What the client contributed: " + ex["client_contribution"], ""]
    lines += ["- " + t for t in ex.get("timestamps") or []]
    if ex.get("details"):
        lines += ["- Details the copy uses: " + "; ".join(ex["details"])]
    lines += ["- Who did what: " + "; ".join(f"{c['actor']}: {c['did']}" for c in ex.get("credits") or [])]
    lines += ["", "## Narrative outline", ""]
    lines += ["- Hook (" + x["style"].replace("_", " ") + "): " + x["text"] for x in outline["hooks"]]
    lines += ["- Problems, desires or symptoms: " + "; ".join(outline["problems_desires_symptoms"]),
              "- Main point: " + outline["main_point"], "- Transformation: " + outline["transformation"], "- CTA: " + outline["cta"], "",
              "## Format and creative approach", ""]
    if plan.get("email"):
        lines += ["- Email: " + plan["email"]["job"]]
    lines += [f"- Reel {i} ({format_words(r)}): {r.get('premise') or r['job']}" for i, r in enumerate(plan.get("reels") or [], 1)]
    if plan.get("carousel"):
        lines += ["- Carousel: " + plan["carousel"]["job"]]
    cta = h["cta"]
    who = "confirmed by a person" if cta["chosen_by"] == "person" else "proposed by the writer; confirm it at Gate 2"
    lines += ["", "## CTA and essential boundaries", "", (cta["action"] or "No explicit ask") + f" ({who})", "", b["cta_why"], ""]
    lines += [f"- P{i}{' (required)' if x['required'] else ''}: {x['text']} — {x['answer'] or 'Unanswered'}"
              for i, x in enumerate(b["before_publishing"], 1)]
    lines += ["", "---", ""] + asset_lines(plan) + ["---", "", "## Evidence", ""]
    for x in b["evidence"]:
        at = "" if x["start_ms"] is None else f" at {x['start_ms'] // 60000}:{(x['start_ms'] // 1000) % 60:02d}"
        lines += [f"- {x['speaker'] or 'Unknown speaker'}{at}: \"{turns.words(x['quote'], x['speaker'])}\""]

    def settled(c):
        att = c.get("attested")
        return f"attested by {att['by']} on {att['on']}" if att else STATUS.get(c["status"], c["status"])
    lines += ["", "## Claims", ""] + [f"- {c['text']} ({c['claim_class'].replace('_', ' ')}; {settled(c)})" for c in b["claims"]]
    lines += ["", "## Prior coverage", ""] + prior_coverage_lines(row)
    lines += ["", "## Checks", ""] + ["- " + f["severity"] + ": " + f["message"] for f in row["content_body"]["review"]["findings"]]
    return "\n".join(lines) + "\n"
