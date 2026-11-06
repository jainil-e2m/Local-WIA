import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import runner
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).parent
P = lambda n: (ROOT / "prompts" / n).read_text(encoding="utf-8")
SCHEMA = {"type": "object", "additionalProperties": False,
  "required": ["criteria", "overall_preference", "overall_reason", "would_whitney_approve", "factual_problems"],
  "properties": {
    "criteria": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["criterion", "better", "reason"],
        "properties": {"criterion": {"type": "string", "enum": ["clear_what_we_will_say", "wia_perspective", "audience_reason_to_care", "usable_plan_for_reels_carousel_email", "sounds_like_whitney", "accuracy_without_caution_in_public_copy", "easy_to_review_and_approve"]},
                       "better": {"type": "string", "enum": ["X", "Y", "tie"]}, "reason": {"type": "string"}}}},
    "overall_preference": {"type": "string", "enum": ["X", "Y", "tie"]},
    "overall_reason": {"type": "string"},
    "would_whitney_approve": {"type": "object", "additionalProperties": False, "required": ["X", "Y"],
        "properties": {"X": {"type": "string", "enum": ["approve", "approve_with_edits", "reject"]}, "Y": {"type": "string", "enum": ["approve", "approve_with_edits", "reject"]}}},
    "factual_problems": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["brief", "problem"],
        "properties": {"brief": {"type": "string", "enum": ["X", "Y"]}, "problem": {"type": "string"}}}}}}
SYSTEM = """You are an independent editorial reviewer for Wedding Industry Ads (WIA), a Google and Meta ads agency for wedding businesses founded by Whitney Hodges. Two systems wrote an editorial content brief for the same approved content angle, from the same call excerpt. After approval, a writer turns the brief into three Instagram Reels, one carousel and one marketing email for WIA's own marketing. Judge which brief Whitney would rather approve. You do not know which system wrote which. Do not reward length, field count or caution for its own sake.

Whitney's standard (from her feedback): content should demonstrate what WIA knows, how it thinks, how it works with clients and why its approach matters; zoom out from the call to the bigger idea; support WIA's marketing strategy (Savannah's ATTRACT / WARM / CONVERT pillars and the framework Hook, Problems/Desires/Symptoms, Main Point, Transformation, CTA); sound like Whitney (plain, warm, confident, specific to weddings, principles before tactics, never academic); never invent results. A brief should make it easy to see what we are going to say, why WIA's audience would care, how we will make the point and what the piece does for WIA. Evidence and claim limits matter, but they belong in supporting material, not in the voice of the public content.

Voice guide summary: Whitney is a strategic marketing thinker; readers should think "I've never thought about it that way before"; she reframes rather than attacks; a client story should become evidence of a broader principle; earn the CTA.

For each criterion say which brief is better (X, Y or tie) and why. Then give an overall preference, whether Whitney would approve each brief, and any factual problems (claims not supported by the excerpt, wrong attribution). Return only JSON."""
def ex():
    m = next(x for x in json.loads((ROOT / "sources" / "week2.json").read_text(encoding="utf-8")) if x["moment_id"] == "w2_m2_tour_followup")
    return "\n".join(f"[{t['t']}] {t['speaker']}: {t['text']}" for t in m["turns"])
if __name__ == "__main__":
    a, b, judge = sys.argv[1:4]
    da = json.loads((ROOT / "runs" / f"{a}.json").read_text(encoding="utf-8"))["output"]
    db = json.loads((ROOT / "runs" / f"{b}.json").read_text(encoding="utf-8"))["output"]
    user = ("Call excerpt (WIA team: Whitney Hodges, founder; Fallon Looney. 'aliepler' is the venue owner, a client):\n" + ex()
            + "\n\nApproved angle: Tour follow-up has to fit both the couple's timeline and the venue's capacity (WARM, behind the scenes). CTA: DM us ADS.\n\n# Brief X\n"
            + json.dumps(da, ensure_ascii=False, indent=1) + "\n\n# Brief Y\n" + json.dumps(db, ensure_ascii=False, indent=1))
    run_id = f"JB-{judge.split('/')[-1]}-X_{a}-Y_{b}"
    runner.call(run_id, judge, SYSTEM, user, SCHEMA, "BriefJudgment", effort="medium", max_tokens=16000, estimate_usd=0.12)
