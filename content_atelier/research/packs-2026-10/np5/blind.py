"""NP.X3's blind reading kit (the content-packs plan, section 7.3; not product code).

For each pack, every piece the brief also wrote (the email, the carousel, the story Reel and the b-roll text Reel) is
rendered twice, from the brief's approved copy and from the pack's copy, under neutral letters (A and B) in a seeded
random order; the extras only a pack has (a working title, cover alternates, a no-offer ending) are left out, so the
layout does not tell them apart. A written stance Reel has no brief copy and is rendered alone, for the standard reading.
The key goes to a folder the reader never sees.

Usage: python -I blind.py <proof.json> <out_dir> <key_file>
  proof.json: [{"label": "brief 1", "brief": <approved brief row JSON file>, "pack": <GET /packs/{id} JSON file>}, ...]
"""
import json
import random
import sys
from pathlib import Path

PAIRED = (("email", "email"), ("carousel", "carousel"), ("story", "reel_1"), ("broll_text", "reel_3"))


def caption(c):
    return [] if not c else ["CAPTION", c["hook"], "", c["body"], "", c["ending"]]


def email_text(e):
    return (["SUBJECT OPTIONS"] + [f"- {s}" for s in e["subject_options"]] + ["", "PREVIEW", e["preview"], "", "EMAIL",
            e["opening"], "", e["body"], "", e["ending"]])


def reel_text(r):
    lines = ["COVER", r["cover_text"], "", "ON-SCREEN HOOK", r["on_screen_hook"], ""]
    if r.get("script"):
        lines += ["SCRIPT", r["script"], ""]
    if r.get("screens"):
        lines += ["SCREENS"] + [f"{i}. {s}" for i, s in enumerate(r["screens"], 1)] + [""]
    return lines + caption(r.get("caption"))


def carousel_text(c):
    lines = ["TITLE", c["title"], ""]
    for s in c["slides"]:
        lines += [f"SLIDE {s['number']}", s["text"], ""]
    return lines + caption(c.get("caption"))


def render(kind, value):
    text = email_text(value) if kind == "email" else carousel_text(value) if kind == "carousel" else reel_text(value)
    return "\n".join(text).strip() + "\n"


def sources(brief_row):
    """What happened, the same for both versions: the supporting example, the call's words and what is kept out, so the
    reader can judge fidelity without telling the versions apart."""
    body = brief_row["content_body"]["document"]["body"]
    example = body["supporting_example"]
    lines = ["## What happened (the sources; the same for both versions)", "", f"Scene: {example['scene']}",
             f"WIA's part: {example['wia_move']}", f"The client's part: {example['client_contribution']}", "", "The call's words:"]
    lines += [f"- {e.get('speaker')} ({e['start_ms'] // 60000}:{(e['start_ms'] // 1000) % 60:02d}): {e['quote']}"
              for e in body["evidence"]]
    kept = [n for n in body["before_publishing"] if n.get("kind") in ("do_not_claim", "permission", "fact")]
    if kept:
        lines += ["", "Before publishing (what must stay out or be confirmed):"] + [f"- {n['text']}" for n in kept]
    return lines + [""]


def brief_piece(brief_row, kind):
    plan = brief_row["content_body"]["document"]["body"]["format_plan"]
    if kind in ("email", "carousel"):
        return plan.get(kind)
    return next((r for r in plan.get("reels") or [] if r["kind"] == kind), None)


def main():
    proof, out, key_file = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), Path(sys.argv[2]), Path(sys.argv[3])
    (out / "pairs").mkdir(parents=True, exist_ok=True)
    (out / "stance").mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261024)
    key = {}
    n = 0
    for entry in proof:
        brief = json.loads(Path(entry["brief"]).read_text(encoding="utf-8"))
        pack = json.loads(Path(entry["pack"]).read_text(encoding="utf-8"))
        pieces = {p["key"]: p for p in pack["pieces"]}
        for kind, key_name in PAIRED:
            original, finished = brief_piece(brief, kind), (pieces.get(key_name) or {}).get("content")
            if not original or not finished:
                continue
            n += 1
            name = f"pair-{n:02d}"
            versions = [("brief", original), ("pack", finished)]
            rng.shuffle(versions)
            body = [f"# {name}: {'Email' if kind == 'email' else 'Carousel' if kind == 'carousel' else 'Reel'}", ""] + sources(brief)
            for letter, (_, value) in zip("AB", versions):
                body += [f"## Version {letter}", "", render(kind, value)]
            (out / "pairs" / f"{name}.md").write_text("\n".join(body), encoding="utf-8")
            key[name] = {"label": entry["label"], "piece": key_name, "A": versions[0][0], "B": versions[1][0]}
        stance = pieces.get("reel_2") or {}
        if stance.get("origin") == "written" and stance.get("content"):
            name = f"stance-{entry['label'].replace(' ', '-')}"
            (out / "stance" / f"{name}.md").write_text(f"# {name}: Reel (stance, face to camera)\n\n" + "\n".join(sources(brief)) +
                                                       "\n## The Reel\n\n" + render("stance", stance["content"]), encoding="utf-8")
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(f"{n} pairs written to {out / 'pairs'}; key at {key_file}")


if __name__ == "__main__":
    main()
