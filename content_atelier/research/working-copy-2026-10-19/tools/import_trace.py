import sys, json
from backend_pipeline.moments import imports, store
orig = store.save
def traced(conn, moments, records, **kw):
    for m in moments:
        old = conn.execute("SELECT moment_body,evidence_refs FROM key_moments WHERE moment_id=%s", (m.moment_id,)).fetchone()
        if old:
            body = m.model_dump(mode="json", exclude={"moment_id", "source_ids", "anchor_span_ids", "context_span_ids"})
            refs = store.evidence_refs(m, records)
            if old["moment_body"] != body or old["evidence_refs"] != refs:
                print("CONFLICT", m.moment_id, set(body) ^ set(old["moment_body"]), {k: body.get(k) for k in set(body) ^ set(old["moment_body"])}, old["moment_body"] == body, old["evidence_refs"] == refs, type(old["evidence_refs"]), type(refs), json.dumps(old["moment_body"], sort_keys=True) == json.dumps(body, sort_keys=True), [k for k in set(body) | set(old["moment_body"]) if body.get(k) != old["moment_body"].get(k)],
                      "refs differ" if refs != old["evidence_refs"] else "")
                if refs != old["evidence_refs"]:
                    print(" new", json.dumps(refs)[:400]); print(" old", json.dumps(old["evidence_refs"])[:400])
    return orig(conn, moments, records, **kw)
store.save = traced
from backend_pipeline.repository import ContentRepository
from backend_pipeline.storage_config import StorageSettings
try:
    print(imports.import_saved(ContentRepository(StorageSettings.from_env()), sys.argv[1], apply=True, include_failed=True)["moments"])
except ValueError as e:
    print("ERR", e)
