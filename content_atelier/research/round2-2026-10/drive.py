"""Round 2's re-test on a scratch copy (not product code): save a pack, finish it again, refresh a brief, wait for a run,
and print a pack as text for reading. `python -I drive.py <command> [args]`; STACK_API, STACK_SECRET and STACK_ACTOR as for
research/packs-2026-10/np5/api.py.

    save <pack_id> <label>         the pack's JSON to proof/<label>.json and its text to proof/<label>.md
    finish <pack_id>               Finish again (a new run under the profiles the copy's settings name)
    latest <brief_id>              the brief's current pack: id, state, whether its run is active
    wait <brief_id>                until the brief's current pack is out of its run (prints the state)
    revise <brief_id> <file>       a refresh with the instructions in <file>, live
    brief <angle_id>               the angle's latest brief run status and brief id
"""
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packs-2026-10" / "np5"))
from api import call  # noqa: E402

PROOF = Path(__file__).resolve().parent / "proof"
ORDER = ("email", "carousel", "reel_1", "reel_2", "reel_3")


def ok(status, value):
    assert status in (200, 201, 202), (status, value)
    return value


def pack(pack_id):
    return ok(*call("GET", f"/packs/{pack_id}"))


def text(p):
    out = [f"# {p['title']} ({p['state']})", ""]
    for piece in p["pieces"]:
        c = piece.get("content") or {}
        out += [f"## {piece['label']} · {c.get('kind') or ''} {c.get('production') or ''}".rstrip(), ""]
        for k in ("premise", "takeaway", "distinct_because"):
            if c.get(k):
                out.append(f"*{k}:* {c[k]}")
        if c.get("timestamps"):
            out.append(f"*timestamps:* {' | '.join(c['timestamps'])}")
        for k in ("subject_options", "preview", "opening", "body", "ending", "title", "cover_text", "on_screen_hook", "script"):
            v = c.get(k)
            if v:
                out += [f"**{k}:** " + (" | ".join(v) if isinstance(v, list) else v), ""]
        for s in c.get("screens") or []:
            out.append(f"- screen: {s}")
        for s in c.get("slides") or []:
            out.append(f"[{s['number']}] {s['text']}")
        if c.get("caption"):
            out += ["", "**caption:** " + " / ".join(c["caption"].get(k) or "" for k in ("hook", "body", "ending"))]
        for f in piece.get("findings") or []:
            out.append(f"> finding ({f.get('source')}, {f.get('severity')}, {f.get('status')}): {f.get('message')}")
        out.append("")
    out += ["## Creative choices", *[f"- {c['piece']}: chose \"{c['chosen']}\" over {c['considered']} because {c['why']}"
                                     for c in p.get("creative_choices") or []], ""]
    out += ["## Ready blockers", *[f"- {b}" for b in p.get("ready_blockers") or []], ""]
    out += ["## Before publishing", *[f"- {n['id']}: {n['text']}" for n in p.get("before_publishing") or []],
            *[f"- note: {n}" for n in p.get("pack_notes") or []], ""]
    readings = (p.get("fidelity") or {}).get("readings") or []
    out += ["## Piece readings (check v4)", *[f"- {r['piece']}: {r['strength']} ({r['why']})" for r in readings]]
    return "\n".join(out)


def latest(brief_id):
    items = ok(*call("GET", "/packs", brief_id=brief_id))["items"]
    p = pack(items[0]["pack_id"])
    return p


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "save":
        p = pack(args[0])
        PROOF.mkdir(exist_ok=True)
        (PROOF / f"{args[1]}.json").write_text(json.dumps(p, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        (PROOF / f"{args[1]}.md").write_text(text(p), encoding="utf-8")
        print("saved", args[1], p["state"])
    elif cmd == "finish":
        p = pack(args[0])
        print(json.dumps(ok(*call("POST", f"/packs/{args[0]}/finish", {"request_id": f"r2-{uuid.uuid4().hex[:12]}",
                                                                          "expected_manifest_hash": p["manifest_hash"]})), default=str)[:600])
    elif cmd == "latest":
        p = latest(args[0])
        print(p["pack_id"], p["state"], p.get("run_active"))
    elif cmd == "wait":
        for _ in range(240):
            p = latest(args[0])
            if not p.get("run_active") and p["state"] != "finishing":
                print(p["pack_id"], p["state"])
                break
            time.sleep(15)
    elif cmd == "revise":
        status, row = call("GET", f"/briefs/{args[0]}")
        body = {"expected_hash": ok(status, row)["content_hash"], "instructions": Path(args[1]).read_text(encoding="utf-8"),
                "mode": "live"}
        print(json.dumps(ok(*call("POST", f"/briefs/{args[0]}/revise", body)), default=str)[:600])
    elif cmd == "brief":
        print(json.dumps(ok(*call("GET", f"/angles/{args[0]}/research")), default=str)[:1500])
