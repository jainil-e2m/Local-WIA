"""Re-file Drive records under the client whose approved folder actually contains them.

Before the fix in pipeline.membership_scope, the legacy backfill stored every file the Drive walk found
under the *running* scope, so files landed on whichever client's run reached them first. persist._associate
keeps an existing association on later runs, so re-running the backfill does not undo it; this does.

For each stored drive_file: walk its parents (read-only Drive API, cached) up to the approved folder scopes.
Owner = the client(s) of those scopes (an archived client still owns its files; archiving only pauses sync).
- already associated with an owner: left alone
- otherwise: record.scope_id moves to the owner's scope, the wrong association becomes `rejected`, the
  owner's is upserted (basis scope_mapping); one audit event per record
- no approved folder above it: associations become `unresolved` (never guessed)

    python -m backend.scripts.repair_drive_associations            # dry run: prints the plan, changes nothing
    python -m backend.scripts.repair_drive_associations --apply    # writes, with audit events
Report: backend/.local/drive_association_repair.json
"""
import argparse
import json
from collections import Counter
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from backend.config import BACKEND_DIR
from backend.db import transaction
from backend.models.db import Business, ConnectorAccount, RecordAssociation, SourceRecord, SourceScope, SourceVersion
from backend.models.db.base import utcnow
from backend.models.db.ops import AuditEvent
from backend.services.intake.adapters.drive import DriveAdapter
from backend.services.shared.errors import NotFoundError, ScopeDeniedError

REPORT = BACKEND_DIR / ".local" / "drive_association_repair.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    drive = DriveAdapter()
    with transaction() as s:
        account = s.execute(select(ConnectorAccount).where(ConnectorAccount.provider == "drive")).scalar_one()
        scopes = s.execute(select(SourceScope).where(SourceScope.connector_account_id == account.id,
                                                     SourceScope.state == "approved",
                                                     SourceScope.business_id.is_not(None))).scalars().all()
        roots = {sc.external_id: sc for sc in scopes}
        names = {b.id: b.slug for b in s.execute(select(Business)).scalars()}
        rows = s.execute(select(SourceRecord, SourceVersion).join(
            SourceVersion, SourceVersion.id == SourceRecord.current_version_id).where(
            SourceRecord.connector_account_id == account.id, SourceRecord.record_kind == "drive_file")).all()
        files = [(r.id, r.external_id, list(v.attributes.get("parents") or []), v.attributes.get("name")) for r, v in rows]
        current = {}
        for a in s.execute(select(RecordAssociation).where(RecordAssociation.status == "associated")).scalars():
            current.setdefault(a.record_id, set()).add(a.business_id)

    parents_of: dict[str, list[str]] = {}

    def owners(parents: list[str], seen=frozenset()) -> list[SourceScope]:
        found = []
        for p in parents:
            if p in roots:
                found.append(roots[p])
                continue
            if p in seen:
                continue
            if p not in parents_of:
                try:
                    parents_of[p] = drive._get(f"drive/v3/files/{p}", {"fields": "id,parents", "supportsAllDrives": "true"}).get("parents", [])
                except (NotFoundError, ScopeDeniedError):
                    parents_of[p] = []
            found.extend(owners(parents_of[p], seen | {p}))
        return list(dict.fromkeys(found))

    plan, tally = [], Counter()
    for rid, ext, parents, name in files:
        own = owners(parents)
        own_biz = {sc.business_id for sc in own}
        have = current.get(rid, set())
        if have and have <= own_biz:
            tally["already_correct"] += 1
            continue
        if not own:
            tally["no_approved_folder"] += 1
            plan.append({"record_id": str(rid), "file": name, "from": sorted(names[b] for b in have), "to": [], "action": "unresolved"})
            continue
        tally["moved" if have else "associated"] += 1
        plan.append({"record_id": str(rid), "file": name, "from": sorted(names[b] for b in have),
                     "to": sorted(names[b] for b in own_biz), "scope_id": str(own[0].id), "action": "move"})

    moves = Counter((tuple(p["from"]), tuple(p["to"])) for p in plan)
    print(json.dumps(dict(tally)), "\n" + "\n".join(f"  {list(a)} -> {list(b)}: {n}" for (a, b), n in moves.most_common()))
    REPORT.write_text(json.dumps({"applied": args.apply, "tally": tally, "plan": plan}, indent=1, default=str), encoding="utf-8")
    print(f"report: {REPORT}")
    if not args.apply:
        print("dry run: nothing changed (pass --apply to write)")
        return

    with transaction() as s:
        for p in plan:
            rid = UUID(p["record_id"])
            wrong = s.execute(select(RecordAssociation).where(RecordAssociation.record_id == rid,
                                                              RecordAssociation.status == "associated")).scalars().all()
            if p["action"] == "unresolved":
                for a in wrong:
                    a.status = "unresolved"
            else:
                target = s.get(SourceScope, UUID(p["scope_id"]))
                owner_ids = {sc.business_id for sc in scopes if names[sc.business_id] in p["to"]}
                for a in wrong:
                    if a.business_id not in owner_ids:
                        a.status = "rejected"
                for bid in owner_ids:
                    s.execute(insert(RecordAssociation).values(
                        id=uuid4(), record_id=rid, business_id=bid, basis="scope_mapping",
                        status="associated", multi_client=len(owner_ids) > 1, created_at=utcnow()
                    ).on_conflict_do_update(index_elements=["record_id", "business_id"],
                                            set_={"status": "associated", "basis": "scope_mapping",
                                                  "multi_client": len(owner_ids) > 1}))
                s.get(SourceRecord, rid).scope_id = target.id
            s.add(AuditEvent(actor="cli:repair_drive_associations", action="drive_association.repaired",
                             target_type="source_record", target_id=p["record_id"],
                             details={"file": p["file"], "from": p["from"], "to": p["to"], "action": p["action"]}))
    print(f"applied {len(plan)} change(s)")


if __name__ == "__main__":
    main()
