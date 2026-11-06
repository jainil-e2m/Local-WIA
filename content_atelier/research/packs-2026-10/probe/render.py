"""Render a probe pack JSON to Markdown in the v2 pack layout. Usage: render.py <pack.json>..."""
import json
import sys
from pathlib import Path


def render(p):
    e = p["email"]
    out = ["## Email", "", f"**DATE:** {e.get('date','')}", f"**SEND TIME:** {e.get('send_time','')}",
           f"**RECIPIENTS:** {e.get('recipients','')}", f"**SUBJECT:** {e['subject_options'][0]}",
           f"**OTHER SUBJECTS:** {' | '.join(e['subject_options'][1:])}", f"**PREVIEW TEXT:** {e['preview']}", "", e["body"], ""]
    for i, r in enumerate(p["reels"], 1):
        out += ["---", "", f"## Reel {i}: {r.get('title','')}", "", f"**Format:** {r['kind']}", f"**Cover:** {r['cover']}",
                f"**On-screen hook:** {r.get('on_screen_hook','')}", f"**Seconds:** {r.get('seconds','')}", ""]
        if r.get("script"):
            out += ["**Script:**", "", r["script"], ""]
        if r.get("screens"):
            out += ["**On-screen text:**"] + [f"{j}. {s}" for j, s in enumerate(r["screens"], 1)] + [""]
        if r.get("personal_lines"):
            out += ["*Personal lines to keep or cut:* " + " | ".join(r["personal_lines"]), ""]
        out += ["**Caption:**", "", r["caption"], ""]
    c = p["carousel"]
    out += ["---", "", f"## Carousel: {c['title']}", ""]
    for j, s in enumerate(c["slides"], 1):
        out += [f"**Slide {j}**", s, ""]
    out += ["**Caption:**", "", c["caption"], "", "---", "", "## Before you publish"]
    out += [f"{j}. {b}" for j, b in enumerate(p.get("before_publishing", []), 1)]
    out += ["", "## Stronger with permission"] + [f"- {s}" for s in p.get("stronger_with_permission", [])]
    out += ["", "## Change notes"] + [f"- {s}" for s in p.get("change_notes", [])]
    return "\n".join(out) + "\n"


for path in sys.argv[1:]:
    p = Path(path)
    md = p.with_suffix("").with_suffix(".md")
    md.write_text(render(json.loads(p.read_text(encoding="utf-8"))), encoding="utf-8")
    words = len(md.read_text(encoding="utf-8").split())
    print(md, words, "words")
