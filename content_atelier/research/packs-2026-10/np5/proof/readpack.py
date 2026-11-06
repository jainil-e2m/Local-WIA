import json, sys
label = sys.argv[1]
brief = sys.argv[2] if len(sys.argv) > 2 else label
p = json.load(open(f"{label}.pack.json", encoding="utf-8"))
b = json.load(open(f"{brief}.brief.json", encoding="utf-8"))
body = b["content_body"]["document"]["body"]
out = []
out.append(f"# {p['title']}\nCENTRAL: {body['central_point']}\nSCENE: {body['supporting_example']['scene']}\nWIA MOVE: {body['supporting_example']['wia_move']}\nCLIENT: {body['supporting_example']['client_contribution']}")
out.append("BEFORE PUBLISHING: " + " | ".join(f"{n['id']} {n['text'][:200]} => {n.get('answer')}" for n in p["before_publishing"]))
out.append("EVIDENCE:\n" + "\n".join(f"- {e['speaker']} {e['start_ms']//60000}:{(e['start_ms']//1000)%60:02d}: {e['quote']}" for e in body["evidence"]))
for x in p["pieces"]:
    c = x["content"]
    out.append(f"\n## {x['key']} ({x.get('kind')}, {x['origin']}) locks={[l['path'] for l in x['locks']]}")
    if x["channel"] == "email":
        out.append("SUBJECTS: " + " || ".join(c["subject_options"]) + f"\nPREVIEW: {c['preview']}\n{c['opening']}\n\n{c['body']}\n\n{c['ending']}")
    elif x["channel"] == "carousel":
        out.append(f"TITLE: {c['title']}\n" + "\n".join(f"[{s['number']}] {s['text']}" for s in c["slides"]))
        out.append(f"CAPTION: {c['caption']['hook']}\n{c['caption']['body']}\n{c['caption']['ending']}\nCTA {c['cta']} NO-OFFER: {c.get('no_offer_ending')}")
    else:
        out.append(f"TITLE: {c['title']}\nCOVER: {c['cover_text']} | ALTS: {c.get('cover_alternates')}\nHOOK: {c['on_screen_hook']}")
        if c.get("script"): out.append("SCRIPT: " + c["script"])
        if c.get("screens"): out.append("SCREENS: " + " / ".join(c["screens"]))
        out.append(f"PERSONAL: {c.get('personal_lines')}\nCAPTION: {c['caption']['hook']}\n{c['caption']['body']}\n{c['caption']['ending']}\nCTA {c['cta']} NO-OFFER: {c.get('no_offer_ending')}")
    out.append("CHANGES: " + "; ".join(f"{ch['kind']}:{ch['path']}" for ch in x["changes"][:12]))
out.append("\nQUOTES: " + json.dumps(p["client_quotes"], ensure_ascii=False))
out.append("STRONGER: " + json.dumps(p["stronger_with_permission"], ensure_ascii=False))
out.append("NOTES: " + json.dumps(p["pack_notes"], ensure_ascii=False))
out.append("FIDELITY: " + json.dumps({k: v for k, v in p["fidelity"].items() if k in ("checked","flags","repairs","survivors","settled")}, ensure_ascii=False)[:3000])
open(f"{label}.read.txt", "w", encoding="utf-8").write("\n".join(out))
print(len("\n".join(out)))
