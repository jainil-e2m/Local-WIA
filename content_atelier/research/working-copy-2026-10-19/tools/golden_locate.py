"""Locate benchmark-v1 excerpts and Weeks 3-4 trace quotes in the working copy's transcripts (no model call)."""
import json, re, sys
import psycopg
from psycopg.rows import dict_row
R = "/Users/kenilshah/Desktop/Wedding_industy_ads/WIA-Content-Atelier/research/"
W = lambda s: " ".join(re.findall(r"\w+", (s or "").lower()))
conn = psycopg.connect("postgresql://atelier:atelier_ci_only@127.0.0.1:25432/atelier_work", row_factory=dict_row)
docs = conn.execute("SELECT transcript_id, title, included, call_type, original_text FROM transcripts WHERE canonical_document_id IS NULL").fetchall()
for d in docs: d["n"] = W(d["original_text"])
def find(text):
    probe = W(text)[:120]
    return [(d["transcript_id"], d["title"], d["included"], d["call_type"]) for d in docs if probe and probe in d["n"]]
out = []
for wk in ("week1", "week2"):
    for m in json.load(open(R + f"quality-experiments-2026-10-18/sources/{wk}.json")):
        longest = max(m["turns"], key=lambda t: len(t["text"]))
        out.append({"src": m["moment_id"], "meeting": m["meeting"], "hits": find(longest["text"]),
                    "turns": [f'{t["speaker"]}: {t["text"]}' for t in m["turns"]]})
for c in json.load(open(R + "root-cause-2026-10-16/source-to-angle-traces.json")):
    om = c["original_moment"]
    out.append({"src": c["case"], "meeting": om["source_ids"], "hits": find(om["quote"]), "quote": om["quote"],
                "summary": om["context_summary"], "proposition": om["proposition"]})
json.dump(out, open(sys.argv[1], "w"), indent=1)
for o in out: print(o["src"], o["meeting"], o["hits"])
