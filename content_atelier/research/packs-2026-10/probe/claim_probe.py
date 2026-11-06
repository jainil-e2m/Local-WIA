"""Planning probe: check a finished pack's factual statements against the brief's claims and evidence.
Usage: python -I claim_probe.py <brief.json> <pack.json> <model> <out_dir>
Routing: data_collection deny + zdr. Never prints the key.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pack_probe import ENDPOINT, key, raise_for_routing, send  # noqa: E402

PROMPT = """You check a finished WIA content pack for fidelity before it reaches the client.
Below are (1) the approved brief's supported claims, its supporting example and guardrails (before-publishing items), (2) the call evidence (exact quotes with speaker), and (3) the finished pack.

List every statement in the pack that asserts something about the real event, the client, WIA's actions, a person's words, or a result (skip pure opinion, belief or general advice). For each, decide:
- "supported": the brief's claims or the evidence state it (paraphrase allowed if the meaning, actor, tense and certainty are the same);
- "unsupported": it adds an event, detail, motive, actor, number, result, time, or certainty the sources do not give, or changes who did what, or changes planned into done;
- "guardrail": it breaks a before-publishing keep-out item.
Quotes in the pack must match the evidence word for word (minor filler words dropped is allowed); otherwise mark "unsupported".
A keep-out item is broken not only by stating the kept-out detail but also by hinting at it (for example, a line about budget or affordability when price comparisons are kept out): mark such lines "guardrail".
The call took place in October 2026, so "recently" is fine. Offer descriptions are supported when they match the approved offer descriptors below. Statements of WIA's general beliefs or how WIA works are supported when they match the belief statements below.

Return JSON only: {"statements": [{"piece": str, "text": str, "verdict": "supported"|"unsupported"|"guardrail", "source": str /* claim text or evidence id */, "why": str}], "summary": {"supported": int, "unsupported": int, "guardrail": int}}
"""


def main():
    brief_path, pack_path, model, out_dir = sys.argv[1:5]
    body = json.loads(Path(brief_path).read_text(encoding="utf-8"))["content_body"]["document"]["body"]
    sources = {
        "supported_claims": [c["text"] for c in body.get("claims", []) if c.get("status") in ("supported", "attested", "general")],
        "supporting_example": body.get("supporting_example"),
        "before_publishing": body.get("before_publishing"),
        "evidence": [{"evidence_id": e["evidence_id"], "speaker": e["speaker"], "quote": e["quote"]} for e in body.get("evidence", [])],
    }
    kb = Path(r"C:/Users/KENIL/Desktop/wedding_industry_ads/WIA-Content-Atelier/backend/knowledge_base")
    sources["offer_descriptors"] = json.loads((kb / "offer-descriptors.json").read_text(encoding="utf-8"))
    sources["belief_statements"] = (kb / "16-belief-statements.md").read_text(encoding="utf-8")
    pack = json.loads(Path(pack_path).read_text(encoding="utf-8"))
    for k in ("change_notes", "stronger_with_permission", "before_publishing"):
        pack.pop(k, None)
    user = PROMPT + "\n# Sources\n" + json.dumps(sources, ensure_ascii=False, indent=1) + "\n\n# The finished pack\n" + json.dumps(pack, ensure_ascii=False, indent=1)
    req_body = {"model": model, "messages": [{"role": "user", "content": user}], "response_format": {"type": "json_object"},
                "max_tokens": 32000, "provider": {"data_collection": "deny", "zdr": True}, "usage": {"include": True},
                "reasoning": {"effort": "medium"}}
    t0 = time.time()
    response = send(ENDPOINT, req_body, {"Authorization": f"Bearer {key()}"}, timeout=900)
    raise_for_routing(response)
    resp = response.json()
    content = resp["choices"][0]["message"].get("content") or ""
    s, e = content.find("{"), content.rfind("}")
    result = json.loads(content[s:e + 1])
    out = Path(out_dir) / (Path(pack_path).name.replace(".pack.json", "") + f".claims2-{model.split('/')[-1]}.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    u = resp.get("usage", {})
    print(json.dumps({"out": str(out), "seconds": round(time.time() - t0), "cost": u.get("cost"), "summary": result.get("summary")}))
    for st in result.get("statements", []):
        if st.get("verdict") != "supported":
            print("-", st.get("verdict"), "|", st.get("piece"), "|", st.get("text"), "|", st.get("why"))


if __name__ == "__main__":
    main()
