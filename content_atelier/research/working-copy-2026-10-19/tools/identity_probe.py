"""Do imported moments get the weekly path's IDs when hashed over all of the artifact's matched documents? Read-only."""
import sys
from backend_pipeline.moments import imports
from backend_pipeline.moment_validation import resolve_moment_references_partial
from backend_pipeline.storage_sources import reconstruct
from backend_pipeline.repository import ContentRepository
from backend_pipeline.storage_config import StorageSettings

repo = ContentRepository(StorageSettings.from_env())
for path in sys.argv[1:]:
    (file, artifact), = imports.discover(path, include_failed=True)
    meetings = imports.parse_packet(imports.user_message(artifact))
    with repo.connection() as conn:
        docs = conn.execute("SELECT * FROM transcripts").fetchall()
        existing = {r["moment_id"] for r in conn.execute("SELECT moment_id FROM key_moments WHERE extractor_version='2026-10-13.weekly.v3'")}
    matches = imports.match_documents(meetings, docs)
    matched = [matches[m["ref"]]["document"] for m in meetings if m["ref"] in matches]
    transcripts, _, _ = reconstruct(matched)
    refs = {}
    for m in meetings:
        if m["ref"] in matches:
            refs.update(imports.meeting_refs(m, matches[m["ref"]]["document"]))
    resolved, unresolved = resolve_moment_references_partial(artifact.output, refs)
    result = imports._Checker()._partition_moments(resolved, "probe", transcripts, unresolved=unresolved)
    ids = [m.moment_id for m in result.moments]
    print(path.split("/")[-4][:12], "week-wide ids:", len(ids), "equal to stored weekly rows:", len(set(ids) & existing))
