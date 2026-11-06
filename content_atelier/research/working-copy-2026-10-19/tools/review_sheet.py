"""A review sheet for classification decisions: one block per document (read-only)."""
import json, sys
from backend_pipeline.repository import ContentRepository
from backend_pipeline.storage_config import StorageSettings
agreement = json.load(open(sys.argv[1]))
index = {e["file"]: e for e in json.load(open(sys.argv[2]))}
ids = [d["document"] for d in agreement["disagreements"]] + list(agreement["not_covered_by_the_index"])
theirs = {d["document"]: d["index"] for d in agreement["disagreements"]}
repo = ContentRepository(StorageSettings.from_env())
with repo.connection() as conn:
    for i in ids:
        i = i if isinstance(i, str) else i.get("document") or i.get("transcript_id")
        r = conn.execute("SELECT transcript_id,title,call_type,classification,participants,speaker_map,original_text,passage_map FROM transcripts WHERE transcript_id=%s", (i,)).fetchone()
        text = r["original_text"]
        words = len(text.split())
        roles = {k: (v or {}).get("role") for k, v in (r["speaker_map"] or {}).items()}
        c = r["classification"] or {}
        print(f"### {i} | {r['title'][:90]}")
        print(f"ours={r['call_type']} ({c.get('method')}, {c.get('confidence')}) index={theirs.get(i, '—')} words={words}")
        print(f"speakers={roles}")
        print(f"reason: {str(c.get('reason'))[:220]}")
        print("start: " + " ".join(text[:700].split()))
        mid = len(text) // 2
        print("middle: " + " ".join(text[mid:mid + 500].split()))
        print()
