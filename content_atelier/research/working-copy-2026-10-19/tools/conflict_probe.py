"""Which part of an imported moment differs from the stored weekly row with the same ID? Read-only."""
import sys, json
from backend_pipeline.moments import imports, store
from backend_pipeline.repository import ContentRepository
from backend_pipeline.storage_config import StorageSettings

repo = ContentRepository(StorageSettings.from_env())
(file, artifact), = imports.discover(sys.argv[1], include_failed=True)
meetings = imports.parse_packet(imports.user_message(artifact))
with repo.connection() as conn:
    docs = conn.execute("SELECT * FROM transcripts").fetchall()
    matches = imports.match_documents(meetings, docs)
    sources = [matches[m["ref"]]["document"] for m in meetings if m["ref"] in matches]
    for meeting in meetings:
        doc = matches[meeting["ref"]]["document"]
        part = imports.check_meeting(artifact.output, meeting, doc, artifact.prompt_version, sources)
        for m in part.moments:
            old = conn.execute("SELECT moment_body, evidence_refs FROM key_moments WHERE moment_id=%s", (m.moment_id,)).fetchone()
            if not old: print(m.moment_id, "not stored"); continue
            body = m.model_dump(mode="json", exclude={"moment_id", "source_ids", "anchor_span_ids", "context_span_ids"})
            refs = store.evidence_refs(m, [doc])
            for k in sorted(set(body) | set(old["moment_body"])):
                if body.get(k) != old["moment_body"].get(k): print(m.moment_id, "body", k, "| new:", json.dumps(body.get(k))[:150], "| old:", json.dumps(old["moment_body"].get(k))[:150])
            if refs != old["evidence_refs"]:
                print(m.moment_id, "refs new:", json.dumps(refs)[:300]); print("   refs old:", json.dumps(old["evidence_refs"])[:300])
