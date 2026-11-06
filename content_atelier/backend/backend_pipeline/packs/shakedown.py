"""The free-model shakedown's canned finisher answer (NP.X1; plan section 7.1, K70), never usable on a paid run.

A free model is expected to fail the finisher's contract. So that the stages after it (check, repair, finalize, review,
edit, ready, published, export) still run on real data in the shakedown, a canned answer (the planning probe's Opus answer
for the same brief, converted to contracts_v2.FinishOutput by research/packs-2026-10/np5/canned.py) is put in the pack's
response cache for the exact request the run's finisher will send. The finisher then replays it at USD 0, recorded as a
replay. It refuses unless the run's frozen writer model is a free model, so it can never stand in for a paid finisher.
"""
from __future__ import annotations

from ..artifacts import store_for
from ..llm import workflow_fingerprint
from ..llm.routing import is_free
from ..store import canonical_hash
from . import contracts_v2 as c2
from . import finish, runtime_v2, stages


def seed_finish(worker, run_id: str, answer: dict) -> dict:
    with worker.repo.connection() as conn:
        run = conn.execute("SELECT * FROM pipeline_runs WHERE run_id=%s", (run_id,)).fetchone()
    if not run or run["input_refs"].get("workflow") != c2.VERSION:
        raise ValueError("Not a content pack v2 run")
    writer = (run["input_refs"].get("execution_contract") or {}).get("writer")
    if not is_free(writer):
        raise PermissionError("A canned finisher answer is for the free-model shakedown only: this run's writer is "
                              f"{writer or 'not frozen yet'}")
    c2.FinishOutput.model_validate(answer)
    prior = stages.output(worker, run, "pack_assemble")
    draft, handoff = prior["draft"], prior["handoff"]
    mode = draft["finish_mode"] if draft["finish_mode"] != "assemble" else "finish"
    request, _, _, _ = runtime_v2.request_for(worker, run, "pack_finish", finish.packet(draft, handoff, mode))
    fp = workflow_fingerprint(workflow=runtime_v2.WORKFLOW, stage="pack_finish", request=request,
                              endpoint=worker.models.openrouter_base_url, synthetic=worker.storage.synthetic)
    store = store_for(worker.storage)
    artifact = f"pack-canned/{run_id}/{fp}.json"
    store.write_json(artifact, {"raw_response": {"canned": True, "note": "NP.X1: pipeline path, not model quality"},
                                "output": answer}, overwrite=True)
    store.write_json(f"pack-cache/{fp}.json", {"fingerprint": fp, "output": answer, "output_hash": canonical_hash(answer),
                                               "artifact": artifact}, overwrite=True)
    return {"run_id": run_id, "fingerprint": fp, "artifact": artifact}
