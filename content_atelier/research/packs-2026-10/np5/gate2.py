"""NP.X3 and NP-6: take N2's three briefs through Gate 2 as the WIA team's delegated reviewer (not product code).

Applies research/packs-2026-10/np5/gate2-actions.json through the same service functions the Gate 2 screen calls, as the
named team account (a users-row actor, as the API resolves it): the edits (each an exact replacement in one line), the CTA
confirmed as the brief proposed it, the before-publishing answers (a client's permission answered as a before-publishing
note), brief 2's clearance of Whitney's own quotation (D12, with the transcript reference), the claims check, then the
approval, which starts each brief's content pack. Every step is a new brief version with its delegated author.

Usage (from backend/, ATELIER_DATABASE_URL set): python -I ../research/packs-2026-10/np5/gate2.py <actions.json> [--dry-run]
    [--only <label>]
A step already done (a CTA a person confirmed, answers already given) is skipped, so an interrupted run resumes; `--only`
takes one brief, so the briefs can run side by side (NP-6: over a proxy each step takes minutes).
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3] / "backend"
sys.path.insert(0, str(BACKEND))

from backend_pipeline.briefs import gate_two, paths  # noqa: E402
from backend_pipeline.gates.roles import actor_for  # noqa: E402
from backend_pipeline.repository import ContentRepository  # noqa: E402
from backend_pipeline.storage_config import StorageSettings  # noqa: E402


def head(repo, brief_id):
    with repo.connection() as conn:
        while True:
            nxt = conn.execute("SELECT brief_id FROM content_briefs WHERE supersedes_id=%s", (brief_id,)).fetchone()
            if not nxt:
                return brief_id
            brief_id = nxt["brief_id"]


def norm(text):
    return " ".join((text or "").replace("’", "'").split()).lower()


def main():
    actions = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    dry = "--dry-run" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    repo = ContentRepository(StorageSettings.from_env())
    actor = actor_for(repo, actions["actor"])
    out = []
    for spec in actions["briefs"]:
        if only and spec["label"] != only:
            continue
        bid = head(repo, spec["brief_id"])
        row = gate_two.get(repo, bid, actor)
        if row["approval_status"] == "approved" and not spec.get("reopen"):
            out.append({"label": spec["label"], "brief_id": bid, "status": "already approved", "approved_hash": row["approved_hash"]})
            continue
        steps = []
        body = row["content_body"]["document"]["body"]
        if spec["edits"]:
            changes = {}
            for e in spec["edits"]:
                current = changes.get(e["path"], paths.get(body, e["path"]))
                # Applied by an earlier, interrupted run. An edit whose new text contains its old text (brief 2's Reel
                # script) still shows the old text once applied, so a resumed run must not apply it again (NP-6).
                if e["new"] in current and (e["old"] not in current or e["old"] in e["new"]):
                    continue
                assert current.count(e["old"]) == 1, (spec["label"], e["path"], current.count(e["old"]))
                changes[e["path"]] = current.replace(e["old"], e["new"])
            if dry or not changes:
                steps.append({"edit": sorted(changes)})
            else:
                done = gate_two.edit(repo, bid, row["content_hash"], changes, actor)
                bid = done["brief_id"]
                steps.append({"edit": sorted(changes), "brief_id": bid})
        if dry:
            out.append({"label": spec["label"], "brief_id": bid, "steps": steps})
            continue
        row = gate_two.get(repo, bid, actor)
        cta = row["content_body"]["document"]["header"]["cta"]
        if cta.get("chosen_by") != "person":
            done = gate_two.confirm_cta(repo, bid, row["content_hash"], {k: cta.get(k) for k in ("choice", "track", "action", "offer_connection")}, actor)
            bid = done["brief_id"]
            row = gate_two.get(repo, bid, actor)
        steps.append({"cta": cta.get("choice")})
        answers = {k: (actions["client_okay"] if v == "client_okay" else v) for k, v in spec["answers"].items()}
        given = [n.get("answer") for n in row["content_body"]["document"]["body"]["before_publishing"]]
        if given != [answers.get(f"P{i}", given[i - 1]) for i in range(1, len(given) + 1)]:
            done = gate_two.answers(repo, bid, row["content_hash"], answers, actor)
            bid = done["brief_id"]
        steps.append({"answers": sorted(answers)})
        for c in spec["clearances"]:
            row = gate_two.get(repo, bid, actor)
            body = row["content_body"]["document"]["body"]
            (ev,) = [e for e in body["evidence"] if norm(c["quote"]) in norm(e["quote"])]
            sel = next(e for e in row["selected_evidence"] if e["evidence_id"] == ev["evidence_id"])
            at = f"{ev['start_ms'] // 60000}:{(ev['start_ms'] // 1000) % 60:02d}"
            reference = f"{sel.get('title') or sel.get('transcript_id')} (transcript {sel.get('transcript_id')}), {at}, {c['attribution']}"
            done = gate_two.clearance(repo, bid, row["content_hash"], ev["evidence_id"], c["permission_reference"], reference, actor)
            bid = done["brief_id"]
            steps.append({"clearance": ev["evidence_id"], "attribution_reference": reference})
        row = gate_two.get(repo, bid, actor)
        claims = [c["claim_id"] for c in row["content_body"]["document"]["body"]["claims"]]
        done = gate_two.review(repo, bid, row["content_hash"], claims, spec["review_reason"], True, actor)
        bid = done["brief_id"]
        steps.append({"review": len(claims)})
        row = gate_two.get(repo, bid, actor)
        left = [b for b in row["blocker_items"] if b["kind"] != "role"]
        if left:
            out.append({"label": spec["label"], "brief_id": bid, "steps": steps, "blocked": left})
            continue
        decided = gate_two.decide(repo, bid, row["content_hash"], "approved",
                                  "Approved by the WIA team under delegation (D12); Whitney has not reviewed it.", actor,
                                  reason_code=None, author=actions["author"])
        steps.append({"decision": decided.get("approval_status"), "pack_run": decided.get("pack_run"), "pack_note": decided.get("pack_note")})
        out.append({"label": spec["label"], "brief_id": bid, "content_hash": row["content_hash"], "steps": steps})
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
