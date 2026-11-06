"""NP.X1's canned finisher answers (not product code): the planning probe's round-2 packs as `pack_finish` answers.

The free-model shakedown runs the pack path on free models. A free finisher fails its contract, as expected (K70), so each
pack's finisher answer is replaced, inside the shakedown only, by the probe's Opus 5.5 answer for the same brief converted
to contracts_v2.FinishOutput. The stages after the finisher then run on real data; these runs are recorded as "pipeline
path, not model quality". Usage (from backend/): python -I ../research/packs-2026-10/np5/canned.py <probe pack.json> <out.json>
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3] / "backend"
sys.path.insert(0, str(BACKEND))

from backend_pipeline.packs import contracts_v2 as c2  # noqa: E402


def split_caption(text):
    parts = [p.strip() for p in (text or "").split("\n\n") if p.strip()]
    if len(parts) < 3:
        parts = (parts + ["", "", ""])[:3]
        parts = [p or "-Whitney" for p in parts]
    return {"hook": parts[0], "body": "\n\n".join(parts[1:-1]), "ending": parts[-1]}


def split_email(body):
    parts = [p.strip() for p in body.split("\n\n") if p.strip()]
    sign = next((i for i, p in enumerate(parts) if p.lower().startswith("talk soon")), len(parts))
    opening = "\n\n".join(parts[:2])
    ending = "\n\n".join(parts[max(2, sign - 1):])
    middle = "\n\n".join(parts[2:max(2, sign - 1)]) or parts[min(2, len(parts) - 1)]
    return opening, middle, ending


def convert(pack):
    e = pack["email"]
    opening, body, ending = split_email(e["body"])
    reels = []
    for kind in c2.REEL_KINDS:
        r = next(x for x in pack["reels"] if x["kind"] == kind)
        broll = kind == "broll_text"
        script = None if broll else (r.get("script") or "")
        reels.append({"kind": kind, "title": r.get("title") or r["cover"], "job": f"The {kind.replace('_', ' ')} Reel",
                      "cover_text": r["cover"], "cover_alternates": (r.get("cover_alternates") or [])[:2],
                      "on_screen_hook": r["on_screen_hook"],
                      "spoken_opening": None if broll else (script.split("\n")[0].split(". ")[0] + "."),
                      "script": script, "screens": (r.get("screens") or [])[:3] if broll else None,
                      "beats": ["The moment", "The point"], "caption": split_caption(r["caption"]),
                      "personal_lines": (r.get("personal_lines") or [])[:6],
                      "read_time_seconds": max(5, min(180, int(r.get("seconds") or 45))),
                      "cta": r.get("cta") or "none", "no_offer_ending": r.get("no_offer_ending") if r.get("cta") == "offer" else None,
                      "offer_descriptor": None})
    c = pack["carousel"]
    answer = {"email": {"subject_options": e["subject_options"][:4], "preview": e["preview"], "opening": opening, "body": body,
                        "ending": ending, "offer_descriptor": None, "cta": "reply"},
              "reels": reels,
              "carousel": {"title": c["title"], "slides": [{"number": i, "text": t} for i, t in enumerate(c["slides"][:12], 1)],
                           "caption": split_caption(c["caption"]), "cta": c.get("cta") or "none",
                           "no_offer_ending": c.get("no_offer_ending") if c.get("cta") == "offer" else None, "offer_descriptor": None},
              "client_quotes": [], "stronger_with_permission": pack.get("stronger_with_permission") or [],
              "pack_notes": ["Canned answer from the planning probe (NP.X1, pipeline path, not model quality)"],
              "change_notes": pack.get("change_notes") or []}
    c2.FinishOutput.model_validate(answer)
    return answer


if __name__ == "__main__":
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    target.write_text(json.dumps(convert(json.loads(source.read_text(encoding="utf-8"))), ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print("wrote", target)
