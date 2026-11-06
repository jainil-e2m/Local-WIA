"""S.B5: brief research's archive snapshot over the working copy with default settings (no model call)."""
import json
from backend_pipeline.config import Settings, embedding_contract
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.repository import ContentRepository
from backend_pipeline import retrieval
models = Settings.from_env(); repo = ContentRepository(StorageSettings.from_env())
with repo.connection() as conn:
    snap = retrieval.archive(conn, models, repo.settings.synthetic)
    included = conn.execute("SELECT count(*) n FROM transcripts WHERE included AND canonical_document_id IS NULL").fetchone()['n']
print(json.dumps({"contract": embedding_contract(models), "sources": len(snap['sources']), "included_canonical": included,
                  "chunks": len(snap['chunks']), "verified_moments": len(snap['moments'])}, indent=1))
