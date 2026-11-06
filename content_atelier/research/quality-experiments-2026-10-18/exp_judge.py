import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import runner, render
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).parent
P = lambda n: (ROOT / "prompts" / n).read_text(encoding="utf-8")
SCHEMA = {"type": "object", "additionalProperties": False,
  "required": ["criteria", "overall_preference", "overall_reason", "estimated_whitney_rating", "factual_problems"],
  "properties": {
    "criteria": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["criterion", "better", "reason"],
        "properties": {"criterion": {"type": "string", "enum": ["shows_wia_expertise_zoomed_out", "strategic_fit", "worth_attention", "sounds_like_whitney", "accuracy_and_attribution", "public_vs_internal_judgment"]},
                       "better": {"type": "string", "enum": ["X", "Y", "tie"]}, "reason": {"type": "string"}}}},
    "overall_preference": {"type": "string", "enum": ["X", "Y", "tie"]},
    "overall_reason": {"type": "string"},
    "estimated_whitney_rating": {"type": "object", "additionalProperties": False, "required": ["X", "Y"],
        "properties": {"X": {"type": "number"}, "Y": {"type": "number"}}},
    "factual_problems": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["set", "angle", "problem"],
        "properties": {"set": {"type": "string", "enum": ["X", "Y"]}, "angle": {"type": "string"}, "problem": {"type": "string"}}}}}}
SYSTEM = """You are an independent editorial reviewer. You will compare two sets of content angles that two different systems produced from the same call excerpts for Wedding Industry Ads (WIA), a Google and Meta ads agency for wedding businesses founded by Whitney Hodges. Judge them the way Whitney would, using her own feedback and framework below. You do not know which system produced which set; do not reward length, field count or caution for its own sake, and do not reward style that is not supported by the excerpts.

## Whitney's feedback on an earlier batch (verbatim)
""" + P("founder_feedback.md") + """

## Whitney's angle-selection framework and guidance (verbatim from her document)
""" + P("whitney_framework.md") + """

## WIA's audience and voice, in brief
WIA's content markets WIA to established, growth-minded wedding business owners (venues, planners, photographers and other pros) who already invest in marketing. Offers: ELEVATE (full-service ads), Ads Accelerators (WIA builds campaigns, then teaches owners to run them), LeadLock (inquiry follow-up system). Whitney's voice: a strategic thinker, principles before tactics, calm confidence, plain conversational language, reframes rather than attacks, never hype. She dislikes academic, cautious or generic phrasing and content framed around wedding pros doing things wrong.

## How to judge
For each criterion say which set is better overall (X, Y or tie) and why, citing angle numbers:
1. shows_wia_expertise_zoomed_out: do the angles reveal what WIA knows, how it thinks, how it works and why its approach matters, rather than extracting a lesson for the client on the call?
2. strategic_fit: clear and sensible ATTRACT / WARM / CONVERT purpose and content type; connection to WIA's marketing strategy and offers where earned.
3. worth_attention: a perspective a prospective client would actually care about; distinctive, not generic.
4. sounds_like_whitney: plain, confident, non-academic working titles and perspectives.
5. accuracy_and_attribution: claims stay within the excerpts; nothing invented; credit goes to the right person (client vs WIA team member).
6. public_vs_internal_judgment: sensible decisions about what becomes public content versus internal intelligence.
Then give an overall preference, an estimated rating Whitney would give each set on her 1 to 5 scale, and list concrete factual problems (invented facts, wrong attribution, overclaims) in either set. Return only JSON."""
def excerpts(week):
    ms = json.loads((ROOT / "sources" / f"{week}.json").read_text(encoding="utf-8"))
    out = []
    for m in ms:
        out.append(f"## {m['moment_id']}")
        out += [f"[{t['t']}] {t['speaker']}: {t['text']}" for t in m["turns"]]
    return "\n".join(out)
if __name__ == "__main__":
    a, b, judge, week = sys.argv[1:5]
    est = float(next((x.split("=")[1] for x in sys.argv if x.startswith("--est=")), "0.15"))
    user = ("Call excerpts both systems worked from (WIA team: Whitney Hodges (founder), Carmen Cruickshank, Fallon Looney, Danielle McGinnis, Giselle; everyone else is a client, prospect or student):\n\n"
            + excerpts(week)
            + (("\n\n# Whitney's own alternative angles for these same excerpts (her reference for what good looks like)\n" + P("whitney_alternatives_w1.md")) if week == "week1" else "")
            + "\n\n# Set X\n\n" + render.as_text(a, "X") + "\n\n# Set Y\n\n" + render.as_text(b, "Y"))
    run_id = f"J{'W1R' if week=='week1' else ''}-{judge.split('/')[-1]}-X_{a}-Y_{b}"
    if "--dry" in sys.argv: print(run_id, len(SYSTEM), len(user)); print(user[-3000:]); sys.exit()
    runner.call(run_id, judge, SYSTEM, user, SCHEMA, "PairwiseJudgment", effort="medium", max_tokens=16000, estimate_usd=est)
