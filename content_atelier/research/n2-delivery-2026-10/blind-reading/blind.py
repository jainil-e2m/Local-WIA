"""Blind brief reading inputs (5.0c, D39): the 20 October writer v4 briefs and N2's writer v5 briefs rendered by the app's
own Markdown export (gate_two.markdown), cut before the evidence, claims, prior coverage and checks (which name
versions and statuses), shuffled under neutral letters. The key goes to a separate file the reader never sees.

    python blind.py OUT_DIR V5_JSON...   (each V5_JSON: {"content_body": {...}} of a brief row)
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\KENIL\Desktop\wedding_industry_ads\WIA-Content-Atelier\backend")
from backend_pipeline.briefs import gate_two  # noqa: E402

gate_two.prior_coverage_lines = lambda row: []
V4 = Path(r"C:\Users\KENIL\Desktop\wedding_industry_ads\WIA-Content-Atelier\research\eb23-brief-contract-2026-10-20\results")


def text(document):
    from backend_pipeline.briefs import render_v4
    from backend_pipeline.briefs.contracts_v4 import is_v4_body
    row = {"content_body": {"document": document, "review": {"findings": []}}}
    md = render_v4.markdown_v4(row) if is_v4_body(document["body"]) else gate_two.markdown_v2(row)
    return md.split("\n## Evidence")[0].rstrip().removesuffix("---").rstrip() + "\n"


out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
items = [("writer_v4", p.stem, json.loads(p.read_text(encoding="utf-8"))["document"]) for p in sorted(V4.glob("brief-*.json"))]
for p in sys.argv[2:]:
    row = json.loads(Path(p).read_text(encoding="utf-8"))
    items.append(("writer_v5", Path(p).stem, row["content_body"]["document"]))
random.Random(20261023).shuffle(items)
key = {}
for letter, (config, source, document) in zip("ABCDEFGHIJ", items):
    (out / f"brief-{letter}.md").write_text(text(document), encoding="utf-8")
    key[letter] = {"config": config, "source": source}
(out.parent / f"{out.name}-key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
print(json.dumps({"briefs": len(items), "dir": str(out)}))
