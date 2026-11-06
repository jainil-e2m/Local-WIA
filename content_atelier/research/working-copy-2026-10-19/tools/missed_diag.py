"""For each missed golden scene: the verified scenes whose context holds the anchor (found nearby) or none (absent)."""
import json, re, sys, psycopg
from psycopg.rows import dict_row
N = lambda s: " ".join(re.findall(r"\w+", (s or "").lower()))
g = {s["id"]: s for s in json.load(open(sys.argv[1]))["scenes"]}
c = psycopg.connect("postgresql://atelier:atelier_ci_only@127.0.0.1:25432/atelier_work", row_factory=dict_row)
for sid in sys.argv[2:]:
    s = g[sid]; t = c.execute("SELECT original_text, passage_map FROM transcripts WHERE transcript_id=%s", (s["document"]["transcript_id"],)).fetchone()
    text = {p["passage_id"]: t["original_text"][p["start"]:p["end"]] for p in t["passage_map"]}
    where = [k for k, v in text.items() if N(s["anchor"]) in N(v)]
    print(f"== {sid} anchor in span {where}")
    for m in c.execute("SELECT moment_body b, evidence_refs e, quote_verified v FROM key_moments WHERE document_id=%s AND is_current AND extractor_version='2026-10-18.scenes.v1'", (s["document"]["transcript_id"],)):
        ctx = m["b"].get("context_span_ids") or []
        if any(w in ctx for w in where):
            print("  in context:", m["v"], "|", m["b"].get("moment_type"), "|", (m["b"].get("quote") or "")[:110])
