"""Planning probe for the content-pack stage (not product code).

Takes one of N2's v4 briefs and asks a model to finish its copy into a publish-ready
pack, in one of two modes:
  edit  - edit the brief's own asset copy to WIA's house style (refine, don't replace)
  fresh - write each asset from the brief's strategy and evidence (the brief's copy is
          shown only as the approved draft to stay faithful to)
Routing: data_collection deny + zdr (the system's S.B1 policy). Never prints the key.
Usage: python -I pack_probe.py <brief.json> <mode> <model> <out_dir> [effort]
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(r"C:\Users\KENIL\Desktop\wedding_industry_ads\WIA-Content-Atelier")
KB = REPO / "backend" / "knowledge_base"
ENV = REPO / "backend" / ".env"
sys.path.insert(0, str(REPO / "backend"))
from backend_pipeline.llm.routing import raise_for_routing, send  # noqa: E402  (S.B1: every call through the routing)

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
KB_DOCS = ["02-founder-voice-guide.md", "09-format-guide.md", "17-editing-guide.md",
           "15-exemplars.md", "18-spoken-voice.md", "19-transformations.md", "10-cta-catalogue.md"]


def key():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY_INTERNAL="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("key missing")


HOUSE_STYLE = """
# WIA house style by format (the standard every finished piece meets)

ACROSS THE PACK
- One idea through different doors: every piece carries the same central point; pieces differ in scene, angle and hook, never in point. Repeat ideas, not language: no shared sentence or 6+ word span between siblings except an approved signature line.
- The story: one real moment and at most two concrete details. Use the client's or Whitney's own words from the evidence when they carry the moment (quote exactly; attribute correctly; never invent or tidy a quote into something they did not say).
- Reader: established, growth-minded wedding pros (venues, planners, photographers, entertainment) already investing in marketing. The example is specific; the lesson zooms out to all wedding pros. Never desperation, never pain-led, never present ads or a WIA offer as frustrating, never tell the reader how to fix their own account (no DIY self-audit lines at the end).
- Position against "most agencies" when useful, never against the reader.
- American English spelling and punctuation. No em dashes. Contractions. No hashtags. Minimal emoji (none by default).
- Banned: the problem-swap hook ("you don't have an X problem"); stock assistant phrasing; aphoristic kickers ("Those two things can exist together."; "That's the difference."); more than one "it's not X, it's Y" / "rather than" contrast per piece; abstract nouns standing in for the story ("contribution", "scrutiny", "judgment", "room", "space" used as filler).
- Concrete over vague: name the real thing (the landing page, the Google campaign, the couples, the inquiries, the tour).

FIRST-TOUCH TEXT (subject, preview, every cover and on-screen hook, the first b-roll screen, carousel slide 1)
1. Specific: names the concrete subject (ads, Google, Meta, the landing page, the budget, inquiries, bookings) so a cold reader knows what it is about.
2. Carousel slide 1 carries the carousel title's promise as an insight about the reader; a bare quote or teaser is not a slide 1.
3. Subject lines state WIA's counter-expected point or decision, or the reader's own question or problem. Never a narration of what a third party did. Give 3 options, best first; the preview finishes the thought.
4. No insider terms (office hours, VAULT, VIP Day, kickoff call, LeadLock landing page internals). Offer names carry their approved descriptors.
5. Who did what: keep the actor the evidence names.

EMAIL
- Header: DATE, SEND TIME, RECIPIENTS (keep the brief's proposed values), SUBJECT (3 options), PREVIEW.
- "Hi {{contact.first_name}}," then an opening scene; short flowing paragraphs (no bullet lists); one bold key line; the principle; the offer named with its approved descriptor as the solution when the brief names one; the CTA (reply, or a sales-page link if the brief says so; never "DM" in an email); "Talk soon,\\nWhitney".
- Stands alone (no Instagram references). Personality: warm, confident, a little personal ("Honestly?"), clean and declarative. 250-450 words.

REEL SCRIPT (face to camera: story or stance)
- Spoken and casual, the way she talks on her recorded Reels (document 18): a crisp first line (a result, a stance, a question, or "I had a call with..."); backstory in plain speech; what WIA did or saw; the client's own words; the principle; a soft close or DM keyword only if the brief's CTA allows an offer on Instagram. 45 to 90 seconds (about 120-220 words). No "Okay, so..." opener. Personal reaction lines are allowed but listed for Whitney to keep or cut.
- Cover: a short specific statement (most don't start with "Why"), distinct from the on-screen hook and from other covers.
- On-screen hook: the line on screen in the first second; specific.

B-ROLL TEXT REEL
- One to three screens that tell the turn of the story so a cold viewer follows it from the screens alone (screen 1 states the situation, screen 2 the turn, screen 3 the line that lands). The caption carries the rest.

CAPTION (every Reel and the carousel)
- Savannah's framework, in order: (1) a hook different from the Reel's on-screen hook and cover; (2) problems, desires and symptoms in the reader's world, wedding-specific (what they see, feel, wonder); (3) the main point with the story as proof; (4) the transformation; (5) the CTA (none, save, or a DM keyword only where the brief allows; CONVERT names the offer).
- 150-300 words, clean and declarative, short paragraphs. "-Whitney" at the end of first-person captions.

CAROUSEL
- A title; 7 to 12 slides. Slide 1: the title's promise as an insight about the reader. The story over two to four slides. The reader's situation and the reframe. A belief slide ("We believe..."). A last slide for both readers: those who want WIA to manage their ads and those who want WIA to launch their campaigns and guide them while they run them.
- Each slide is short stacked lines (2 to 5 short lines, about 20-55 words), with at most one bold key line marked **like this**. Real text on every slide, but never a paragraph block. "We" and "us" throughout.
"""

FIDELITY = """
# Fidelity rules (hard; a breach makes the pack unusable)
- Use only facts in the brief (supporting example, claims marked supported, central point, WIA perspective, audience) and the evidence quotes. Add no new event, number, result, time span, name, motive, tool, or outcome.
- Respect every guardrail and before-publishing item in the brief: if the brief keeps something out of public copy (a result, a comparison, a name), keep it out. If a stronger story would need a detail the brief keeps out, do not use it: list it under "stronger_with_permission" instead.
- Keep tense: what was planned stays planned; what happened stays happened.
- Keep the brief's CTA decision (offer or no offer per channel) and its offer descriptor.
- Lines listed as LOCKED are copied exactly, character for character, in their field.
- Never change who did what: an explanation stays an explanation (never "agreed"), a suggestion stays a suggestion, a plan stays a plan; keep the actor the evidence names.
- Never hint at a kept-out detail either (for example, no line about budget, affordability or price when price comparisons are kept out; no hint of a result when results are kept out).
- Personal reactions or reflections in Whitney's voice ("I love this", "I've been thinking about it since") are allowed only in a script and must be listed in personal_lines; never in an email or caption as a fact.
- Quotes: only exact words from the evidence quotes (fillers like "um", "like" may be dropped), attributed to the right speaker. List every client quote you use in client_quotes, so WIA can clear it.
- Offers are described only with the approved descriptor wording in the knowledge base; add no inclusions, terms or promises.
"""

TASK_EDIT = """
# Your task: finish this approved brief's copy into a publish-ready content pack
Edit each asset's copy so it meets the house style, as Whitney would after one careful pass: refine, don't replace. Keep the brief's central point, story, actors and CTA decisions. Fix what is weak: abstraction, repeated vocabulary across pieces, kickers, formal register in scripts, captions that skip the reader's world, dense carousel slides, unspecific covers, British spelling. Where a piece tells no moment, bring in the moment from the supporting example and evidence (her or the client's own words) within the fidelity rules.
"""

TASK_FRESH = """
# Your task: write the publish-ready content pack for this approved brief
Write each asset from the brief's strategy (central point, purpose, audience, WIA perspective, supporting example, narrative outline, format and creative approach, CTA and boundaries) and the evidence. The brief's existing copy is the approved draft: stay faithful to its point, story, actors and CTA decisions, keep any LOCKED line exactly, but write each piece as Whitney's best version of it, format by format.
"""

OUTPUT = """
# Output: one JSON object, nothing else
{
  "email": {"subject_options": [str, str, str], "preview": str, "date": str, "send_time": str, "recipients": str, "body": str  /* from "Hi {{contact.first_name}}," to the sign-off */},
  "reels": [ {"key": "reel_1"|"reel_2"|..., "kind": "story"|"stance"|"broll_text", "title": str  /* a short working title, not the creative direction */,
              "cover": str, "cover_alternates": [str, str], "on_screen_hook": str, "script": str|null, "screens": [str]|null, "caption": str,
              "personal_lines": [str], "seconds": int, "cta": "none"|"offer"|"soft", "no_offer_ending": str|null /* when cta is offer: the caption's last lines rewritten with no offer ask, for weeks when this is not the offer post */} ],
  "carousel": {"title": str, "slides": [str], "caption": str, "cta": "none"|"offer"|"soft", "no_offer_ending": str|null},
  "client_quotes": [str],
  "before_publishing": [str]  /* at most five; keep the brief's required items in plain words */,
  "stronger_with_permission": [str],
  "change_notes": [str]  /* what you changed and why, one line each */
}
Every pack has exactly 1 email, 1 carousel and 3 Reels: reel_1 kind "story" (face to camera), reel_2 kind "stance" (face to camera), reel_3 kind "broll_text" (one to three screens). If the brief lacks a kind, write that Reel from the brief's strategy and evidence: the stance Reel says Whitney's stance on the SAME central point, face to camera, with the moment as proof in a line or two; it is never a sub-lesson or a new point, and it adds no facts. Same idea, different doors. Write slides as plain text with line breaks; bold with **...**.
"""


def brief_payload(brief):
    body = brief["content_body"]["document"]["body"]
    keep = {k: body[k] for k in ("approved_angle", "central_point", "strategic_purpose", "intended_shift", "audience",
                                 "wia_perspective", "supporting_example", "narrative_outline", "cta", "cta_why",
                                 "before_publishing") if k in body}
    fp = json.loads(json.dumps(body["format_plan"]))
    keep["format_plan_with_draft_copy"] = fp
    keep["claims"] = [{"text": c["text"], "status": c["status"], "field": c["field"], "quote": c.get("quote")}
                      for c in body.get("claims", []) if c.get("status") in ("supported", "attested", "general")]
    keep["evidence_quotes"] = [{"speaker": e["speaker"], "at_seconds": e["start_ms"] // 1000, "quote": e["quote"]}
                               for e in body.get("evidence", [])]
    return keep


def main():
    brief_path, mode, model, out_dir = sys.argv[1:5]
    effort = sys.argv[5] if len(sys.argv) > 5 else "medium"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))
    kb = "\n\n".join(f"<document name=\"{n}\">\n{(KB / n).read_text(encoding='utf-8')}\n</document>" for n in KB_DOCS)
    system = ("You are the finishing editor for Wedding Industry Ads (WIA), a paid-ads agency for wedding businesses, "
              "led by Whitney Hodges. You turn an approved content brief into the content pack WIA publishes from: "
              "copy Whitney would post with no more than a light edit.\n\n"
              "# WIA's knowledge base (her voice, formats, edits and finished pieces; patterns, never lines to copy)\n" + kb
              + "\n" + HOUSE_STYLE + FIDELITY)
    user = ((TASK_EDIT if mode == "edit" else TASK_FRESH) + OUTPUT + "\n# The approved brief\n"
            + json.dumps(brief_payload(brief), ensure_ascii=False, indent=1) + "\n\nLOCKED lines: none.\n")
    req_body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
        "max_tokens": 32000,
        "provider": {"data_collection": "deny", "zdr": True},
        "usage": {"include": True},
        "reasoning": {"effort": effort},
    }
    t0 = time.time()
    response = send(ENDPOINT, req_body, {"Authorization": f"Bearer {key()}"}, timeout=900)
    raise_for_routing(response)
    resp = response.json()
    dt = time.time() - t0
    tag = f"{Path(brief_path).stem}-v2{mode}-{model.split('/')[-1]}-{effort}"
    (out / f"{tag}.raw.json").write_text(json.dumps(resp, ensure_ascii=False, indent=1), encoding="utf-8")
    usage = resp.get("usage", {})
    content = resp["choices"][0]["message"].get("content") or ""
    try:
        pack = json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        pack = json.loads(content[start:end + 1])
    (out / f"{tag}.pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"tag": tag, "seconds": round(dt), "prompt_tokens": usage.get("prompt_tokens"),
                      "completion_tokens": usage.get("completion_tokens"), "cost": usage.get("cost"),
                      "provider": resp.get("provider"), "finish": resp["choices"][0].get("finish_reason")}))


if __name__ == "__main__":
    main()
