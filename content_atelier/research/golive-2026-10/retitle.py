"""Give N4's newly imported Fathom documents the title the corrected builder gives them (N4; not product code).

The October import ran before `fathom_title` (commit 9607bce), so two calls were stored as "Impromptu Zoom Meeting". Only a
document with no scenes, chunks with vectors or citations is retitled; the caller then normalises it again by the rules.
Usage (from backend/, production's variables loaded): python -I ../research/packs-2026-10/np5/remote.py ../research/golive-2026-10/retitle.py <transcript_id>...
"""
import json
import os
import sys

import psycopg
from psycopg.rows import dict_row

from backend_pipeline.normalise.sources import fathom_title

changed = []
with psycopg.connect(os.environ["ATELIER_DATABASE_URL"], connect_timeout=30, row_factory=dict_row) as conn:
    for tid in sys.argv[1:]:
        row = conn.execute("SELECT transcript_id,title,source_type,source_metadata,extraction_status FROM transcripts "
                           "WHERE transcript_id=%s FOR UPDATE", (tid,)).fetchone()
        if row is None or row["source_type"] != "fathom":
            raise SystemExit(f"{tid}: not a Fathom document")
        meeting = (row["source_metadata"] or {}).get("provider_metadata") or {}
        title = fathom_title(meeting, meeting.get("recording_id"))
        used = conn.execute("SELECT (SELECT count(*) FROM key_moments WHERE document_id=%s) AS scenes, "
                            "(SELECT count(*) FROM transcript_chunks WHERE transcript_id=%s AND embedding IS NOT NULL) AS vectors",
                            (tid, tid)).fetchone()
        if used["scenes"] or used["vectors"]:
            raise SystemExit(f"{tid}: already has scenes or vectors; retitle it through a person's decision instead")
        if title != row["title"]:
            conn.execute("UPDATE transcripts SET title=%s WHERE transcript_id=%s", (title, tid))
            changed.append({"transcript_id": tid, "from": row["title"], "to": title})
print(json.dumps({"retitled": changed}, indent=1))
