from psycopg.types.json import Jsonb

from ..briefs import gate_two
from ..production_common import ProductionError, receipt, save_receipt
from ..repository import insert
from ..store import canonical_hash
from ..artifacts import store_for
from . import service
from .contracts import SLOTS, STAGES, VERSION, Review, schema


def queue(repo, brief_id, payload, actor, *, synthetic=False, model_settings=None):
    service.authorize(repo, actor)
    if not repo.settings.packs_enabled:
        raise ProductionError("Pack production is not enabled", "packs_disabled", 503)
    mode = "synthetic" if synthetic else payload.mode
    if synthetic and not repo.settings.synthetic:
        raise ValueError("Synthetic pack requires an isolated test database")
    if mode == "live" and not (repo.settings.generation_enabled and repo.settings.pack_live_enabled):
        raise PermissionError("Live pack generation is disabled")
    data = payload.model_dump(mode="json")
    operation = "generate-pack:" + brief_id
    with repo.connection() as conn:
        saved = receipt(conn, payload.request_id, actor, operation, data)
        if saved is not None:
            return saved
        brief = conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s FOR UPDATE", (brief_id,)).fetchone()
        if not brief:
            raise ProductionError("Brief not found", "not_found", 404)
        if brief["content_hash"] != payload.expected_brief_hash or brief["approval_status"] != "approved":
            raise ProductionError("Approve the current brief before production", "stale_brief")
        reasons = gate_two.blockers(conn, brief)
        if reasons:
            raise ProductionError("; ".join(reasons), "brief_blocked")
        if gate_two.is_v2(brief):
            # Packs stay mapped to version 1 briefs (E.B15 b). A v2 or v3 brief may be consumed (can_consume, E.B23); when
            # packs come into scope they read the version-independent hand-off view (briefs/handoff.py, GET
            # /briefs/{id}/handoff: pieces with keys, the anchor first, the message spine), not the contract's document.
            raise ProductionError("Packs are mapped for version 1 briefs only", "brief_v2_unmapped")
        from .runtime import execution_contract

        contract = execution_contract(repo.settings, model_settings)
        origin = conn.execute(
            "SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (brief["content_body"]["provenance"]["run_id"],)
        ).fetchone()
        brand = (origin or {}).get("input_refs", {}).get("brand")
        if not brand or brand.get("hash") != brief["content_body"]["provenance"]["brand_hash"]:
            raise ValueError("Approved founder brand bundle is unavailable")
        refs = {"brief": brief, "brand": brand, "mode": mode, "execution_contract": contract, "version": VERSION}
        # The identity records the pack's checks hold its copy to (N8), frozen with the run as a cycle's and a brief's are.
        from .checks import pack_identities

        refs.update(pack_identities(conn, brief))
        # Frozen SQL row timestamps are serialized for artifact-compatible identity.
        from fastapi.encoders import jsonable_encoder

        refs = jsonable_encoder(refs)
        intent = canonical_hash([brief_id, brief["content_hash"], contract, mode, payload.supersedes_id])
        # The settings the pack run was queued under (0.B8); kept out of the intent, so a changed setting does not requeue.
        from ..settings_store import snapshot_refs

        refs.update(snapshot_refs("pack", models=model_settings, storage=repo.settings, conn=conn))
        rid, pid = "pack_run_" + intent[:24], "pack_" + intent[:24]
        existing = conn.execute("SELECT pack_id FROM content_packs WHERE pack_id=%s", (pid,)).fetchone()
        if not existing:
            if payload.supersedes_id:
                old = conn.execute("SELECT * FROM content_packs WHERE pack_id=%s FOR UPDATE", (payload.supersedes_id,)).fetchone()
                old_brief = (
                    conn.execute("SELECT angle_id FROM content_briefs WHERE brief_id=%s", (old["source_brief_id"],)).fetchone()
                    if old
                    else None
                )
                if not old_brief or old_brief["angle_id"] != brief["angle_id"]:
                    raise ValueError("Replacement must retain the governing angle lineage")
                if conn.execute("SELECT 1 FROM content_packs WHERE supersedes_id=%s", (payload.supersedes_id,)).fetchone():
                    raise ValueError("Pack already has a replacement")
            insert(
                conn,
                "pipeline_runs",
                {
                    "run_id": rid,
                    "week_id": brief["week_id"],
                    "run_scope": "pack_generation",
                    "trigger_type": "manual",
                    "triggered_by": actor,
                    "input_refs": refs,
                },
            )
            insert(
                conn,
                "content_packs",
                {
                    "pack_id": pid,
                    "week_id": brief["week_id"],
                    "title": brief["content_body"]["document"]["title"],
                    "source_brief_id": brief_id,
                    "source_brief_hash": brief["content_hash"],
                    "production_run_id": rid,
                    "contract_version": VERSION,
                    "supersedes_id": payload.supersedes_id,
                },
            )
            ids = {s: "pack_job_" + canonical_hash([rid, s])[:24] for s in STAGES}
            for stage in STAGES:
                deps = (
                    []
                    if stage == "pack_prepare"
                    else (
                        [ids[f"pack_{s}"] for s in SLOTS]
                        if stage == "pack_validation"
                        else [ids["pack_validation"]]
                        if stage == "pack_assembly"
                        else [ids["pack_prepare"]]
                    )
                )
                insert(
                    conn,
                    "pipeline_jobs",
                    {
                        "job_id": ids[stage],
                        "run_id": rid,
                        "week_id": brief["week_id"],
                        "pack_id": pid,
                        "stage": stage,
                        "idempotency_key": rid + ":" + stage,
                        "input_hash": canonical_hash(refs),
                        "progress_details": {"dependencies": deps},
                    },
                )
            repo.event(conn, rid, "pack_queued", "Approved brief queued for production", details={"pack_id": pid, "actor": actor})
        return save_receipt(conn, payload.request_id, actor, operation, data, {"run_id": rid, "pack_id": pid})


def execute(worker, job):
    from .runtime import call, check_dependencies

    repo = worker.repo
    with repo.connection() as conn:
        run = conn.execute("SELECT * FROM pipeline_runs WHERE run_id=%s", (job["run_id"],)).fetchone()
    from .contracts_v2 import VERSION as V2
    if run["input_refs"].get("workflow") == V2:
        # Content pack v2 (Phase NP): the finisher and its fidelity loop over hand-off view v2 (packs/stages.py).
        from . import stages
        return stages.execute(worker, job)
    check_dependencies(worker, run)
    brief = run["input_refs"]["brief"]
    document = brief["content_body"]["document"]
    pid = job["pack_id"]
    stage = job["stage"]
    store = store_for(worker.storage)
    if stage == "pack_prepare":
        with repo.connection() as conn:
            repo.guard(conn, job)
            for ordinal, slot in enumerate(SLOTS, 1):
                insert(
                    conn,
                    "content_assets",
                    {
                        "asset_id": "asset_" + canonical_hash([pid, slot])[:24],
                        "pack_id": pid,
                        "brief_id": brief["brief_id"],
                        "brief_input_hash": brief["content_hash"],
                        "slot_key": slot,
                        "ordinal": ordinal,
                        "asset_type": slot.split("_")[0],
                        "reader_contribution": document["email"]["reader_job"]
                        if slot == "email"
                        else document["carousel_reader_job"]
                        if slot == "carousel"
                        else document["reels"][int(slot[-1]) - 1]["reader_job"],
                    },
                    conflict=True,
                )
            repo.finish(conn, job, {"pack_id": pid}, message="Production inputs frozen")
    elif stage in {f"pack_{s}" for s in SLOTS}:
        slot = stage.removeprefix("pack_")
        output = call(
            worker,
            job,
            run,
            "pack_write",
            schema(slot),
            {
                "slot": slot,
                "approved_brief": document,
                "evidence": brief["selected_evidence"],
                "brand": run["input_refs"]["brand"],
            },
        )
        validate_copy(document, output.model_dump(), slot)
        envelope = {
            "version": VERSION,
            "slot": slot,
            "document": output.model_dump(),
            "brief_id": brief["brief_id"],
            "brief_hash": brief["content_hash"],
        }
        path = f"pack-runs/{run['run_id']}/{slot}.json"
        store.write_json(path, envelope)
        with repo.connection() as conn:
            repo.guard(conn, job)
            repo.finish(conn, job, {"artifact": path, "hash": canonical_hash(envelope)}, message="Saved " + slot + " copy")
    elif stage == "pack_validation":
        outputs = written(repo, store, run["run_id"])
        for slot, envelope in outputs.items():
            validate_copy(document, schema(slot).model_validate(envelope["document"]).model_dump(), slot)
        review = call(
            worker,
            job,
            run,
            "pack_review",
            Review,
            {"approved_brief": document, "evidence": brief["selected_evidence"], "assets": outputs},
        )
        if not (review.grounded and review.preserves_approved_direction and review.distinct_contributions):
            raise ValueError("Pack review blocked: " + "; ".join(review.findings))
        path = f"pack-runs/{run['run_id']}/validation.json"
        value = {
            "passed": True,
            "review": review.model_dump(),
            "asset_hashes": {s: canonical_hash(v) for s, v in outputs.items()},
        }
        store.write_json(path, value)
        with repo.connection() as conn:
            repo.guard(conn, job)
            repo.finish(
                conn,
                job,
                {"artifact": path, "hash": canonical_hash(value)},
                message="Pack validation passed; human review remains",
            )
    elif stage == "pack_assembly":
        outputs = written(repo, store, run["run_id"])
        with repo.connection() as conn:
            pack, rows = service.locked(repo, conn, pid)
            repo.guard(conn, job)
            result = conn.execute(
                "SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='pack_validation'", (run["run_id"],)
            ).fetchone()["result_refs"]
            validation = store.read_json(result["artifact"])
            if canonical_hash(validation) != result["hash"] or validation["asset_hashes"] != {
                s: canonical_hash(v) for s, v in outputs.items()
            }:
                raise ValueError("Pack validation artifact changed")
            for a in rows:
                envelope = outputs[a["slot_key"]]
                conn.execute(
                    """UPDATE content_assets SET content_body=%s,content_hash=%s,status='generated',
                    validation_result=%s,updated_at=now() WHERE asset_id=%s""",
                    (Jsonb(envelope), canonical_hash(envelope), Jsonb(validation), a["asset_id"]),
                )
            pack["validation_result"] = validation
            digest = service.manifest(pack, service.assets(conn, pid))
            conn.execute(
                "UPDATE content_packs SET validation_result=%s,manifest_hash=%s,updated_at=now() WHERE pack_id=%s",
                (Jsonb(validation), digest, pid),
            )
            repo.finish(conn, job, {"pack_id": pid, "manifest_hash": digest}, message="Pack ready for human review")
    else:
        raise ValueError("Unknown production stage")


def written(repo, store, run_id):
    with repo.connection() as conn:
        refs = {
            r["stage"].removeprefix("pack_"): r["result_refs"]
            for r in conn.execute(
                "SELECT stage,result_refs FROM pipeline_jobs WHERE run_id=%s AND stage=ANY(%s) AND status='completed'",
                (run_id, [f"pack_{s}" for s in SLOTS]),
            )
        }
    if set(refs) != set(SLOTS):
        raise ValueError("All five production slots must be complete")
    values = {s: store.read_json(r["artifact"]) for s, r in refs.items()}
    if any(canonical_hash(values[s]) != r["hash"] for s, r in refs.items()):
        raise ValueError("Production artifact integrity failed")
    return values


def validate_copy(brief, copy, slot):
    if copy["cta"] != brief["cta"]:
        raise ValueError("Production CTA differs from the approved brief")
    if not set(copy["evidence_ids"]).issubset(brief["sources"]):
        raise ValueError("Production evidence must come from the approved brief")
    claims = {c["claim_id"]: c for c in brief["claims"]}
    for claim in copy["claims"]:
        if not claim["brief_claim_ids"] or not set(claim["brief_claim_ids"]).issubset(claims):
            raise ValueError("Copy claim lacks an approved claim reference")
        qualifiers = {q for cid in claim["brief_claim_ids"] for q in claims[cid]["qualifications"]}
        if not qualifiers.issubset(claim["qualifications"]):
            raise ValueError("Copy claim dropped an approved qualification")
    if slot == "carousel" and [s["number"] for s in copy["slides"]] != [s["number"] for s in brief["carousel"]]:
        raise ValueError("Carousel must preserve the approved slide structure")
