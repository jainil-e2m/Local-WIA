import sys
from backend_pipeline.normalise import dates
from backend_pipeline.repository import ContentRepository
from backend_pipeline.storage_config import StorageSettings
repo = ContentRepository(StorageSettings.from_env())
with repo.connection() as conn:
    for r in conn.execute("SELECT * FROM transcripts WHERE title ILIKE %s ORDER BY title", ("%" + sys.argv[1] + "%",)):
        print(r["transcript_id"], r["title"][:60], r["source_type"], round(dates.document_minutes(r) or -1, 1), r["call_type"], r["occurred_at"], r["canonical_document_id"])
