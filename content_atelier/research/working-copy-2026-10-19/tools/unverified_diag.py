"""Why unverified scene quotes failed: is the quote in the document, in a cited span, across adjacent spans?"""
import re, psycopg
from psycopg.rows import dict_row
N = lambda s: " ".join(re.findall(r"\w+", (s or "").lower()))
c = psycopg.connect("postgresql://atelier:atelier_ci_only@127.0.0.1:25432/atelier_work", row_factory=dict_row)
for m in c.execute("SELECT k.moment_body b, k.unverified_reason r, t.original_text o, t.passage_map p, t.transcript_id d FROM key_moments k JOIN transcripts t ON t.transcript_id=k.document_id WHERE NOT k.quote_verified AND k.extractor_version LIKE '%scenes%'"):
    b, q = m["b"], N(m["b"].get("quote"))
    spans = {p["passage_id"]: N(m["o"][p["start"]:p["end"]]) for p in m["p"]}
    ids = [p["passage_id"] for p in m["p"]]
    anchors = b.get("anchor_span_ids") or []
    where = [i for i, t in spans.items() if q and q in t]
    joined = None
    for a in anchors:
        if a in ids:
            k = ids.index(a); w = " ".join(spans[x] for x in ids[max(0, k-1):k+3])
            if q in w: joined = a; break
    print(m["d"][-6:], m["r"][:40], "| in_doc:", q in N(m["o"]), "| in_span:", where[:2], "| cited:", anchors[:3], "| across_adjacent_from:", joined, "| anchors_known:", all(a in spans for a in anchors))
