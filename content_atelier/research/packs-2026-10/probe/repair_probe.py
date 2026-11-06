"""Planning probe: repair only the flagged statements of a finished pack, as patches, then apply them.
Usage: python -I repair_probe.py <brief.json> <pack.json> <claims.json> <model> <out_dir>
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pack_probe import ENDPOINT, key, raise_for_routing, send  # noqa: E402

PROMPT = """You repair a finished WIA content pack. A fidelity check flagged the statements below: each adds a detail, an actor, a sequence, words, a decision or a commitment the sources do not give, or hints at a kept-out detail.
Rewrite ONLY the flagged sentences so each says only what the sources support, in the same voice and register, keeping the piece's flow. Prefer cutting a detail over inventing a replacement. Reported speech may only restate what a claim or quote says; never invent dialogue. A quote stays attached to the moment it was said in.
Return JSON only: {"patches": [{"piece": str, "old": str /* exact text as it appears in the pack, a whole sentence or more */, "new": str}]}
"""


def walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                yield obj, k
            else:
                yield from walk(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                yield obj, i
            else:
                yield from walk(v)


def main():
    brief_path, pack_path, claims_path, model, out_dir = sys.argv[1:6]
    body = json.loads(Path(brief_path).read_text(encoding="utf-8"))["content_body"]["document"]["body"]
    sources = {
        "supported_claims": [c["text"] for c in body.get("claims", []) if c.get("status") in ("supported", "attested", "general")],
        "supporting_example": body.get("supporting_example"),
        "before_publishing": body.get("before_publishing"),
        "evidence": [{"speaker": e["speaker"], "quote": e["quote"]} for e in body.get("evidence", [])],
    }
    pack = json.loads(Path(pack_path).read_text(encoding="utf-8"))
    flags = [s for s in json.loads(Path(claims_path).read_text(encoding="utf-8"))["statements"] if s["verdict"] != "supported"]
    user = (PROMPT + "\n# Flagged statements\n" + json.dumps(flags, ensure_ascii=False, indent=1) + "\n# Sources\n"
            + json.dumps(sources, ensure_ascii=False, indent=1) + "\n# The pack\n" + json.dumps(pack, ensure_ascii=False, indent=1))
    req_body = {"model": model, "messages": [{"role": "user", "content": user}], "response_format": {"type": "json_object"},
                "max_tokens": 32000, "provider": {"data_collection": "deny", "zdr": True}, "usage": {"include": True},
                "reasoning": {"effort": "medium"}}
    t0 = time.time()
    response = send(ENDPOINT, req_body, {"Authorization": f"Bearer {key()}"}, timeout=900)
    raise_for_routing(response)
    resp = response.json()
    content = resp["choices"][0]["message"].get("content") or ""
    s, e = content.find("{"), content.rfind("}")
    patches = json.loads(content[s:e + 1])["patches"]
    applied = missed = 0
    for p in patches:
        hit = False
        for parent, k in walk(pack):
            if p["old"] in parent[k]:
                parent[k] = parent[k].replace(p["old"], p["new"])
                hit = True
        applied += hit
        missed += not hit
    out = Path(out_dir) / Path(pack_path).name.replace(".pack.json", "-repaired.pack.json")
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
    u = resp.get("usage", {})
    print(json.dumps({"out": str(out), "seconds": round(time.time() - t0), "cost": u.get("cost"), "patches": len(patches),
                      "applied": applied, "missed": missed, "flags": len(flags)}))


if __name__ == "__main__":
    main()
