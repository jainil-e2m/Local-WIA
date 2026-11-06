"""Run the first-touch checks (E.B34) and the asset checks (E.B24's extension) over a hand-built pack document in the layout
of the 20 October v2 packs, and print the findings by pack. No model call.

    python scripts/pack_checks.py ../research/v2-reassessment-2026-10-20/packs/WIA-Content-Packs-Week-of-8-14-June-2026-v2.md \
        --attest 3 "Her AI assistant was plugged into her Google Ads account and made the changes itself; she had no idea."

`--attest N TEXT` gives pack N a fact an approver attested at a gate (5.B7), as Whitney did for Pack 3 on 20 October (W8).
The pack files live under research/ (R48); this script reads them where they are and writes nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend_pipeline.briefs.pack_markdown import check_packs, parse_packs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pack", type=Path, help="A pack document in the v2 layout")
    parser.add_argument("--attest", nargs=2, action="append", metavar=("PACK", "TEXT"), default=[],
                        help="A fact an approver attested for pack PACK")
    parser.add_argument("--json", action="store_true", help="Print the findings as JSON")
    args = parser.parse_args(argv)
    packs = parse_packs(args.pack.read_text(encoding="utf-8"))
    attested = {}
    for number, text in args.attest:
        attested.setdefault(int(number), []).append(text)
    results = check_packs(packs, attested=attested)
    if args.json:
        print(json.dumps({str(n): fs for n, fs in results.items()}, indent=2, ensure_ascii=False))
        return 0
    for p in packs:
        found = results[p["number"]]
        counts = Counter(f["check"] for f in found)
        print(f"# Pack {p['number']} · {p['pillar']}: {p['title']}")
        print("  " + (", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "no findings"))
        for f in found:
            print(f"  - {f['severity']}: {f['check']} at {f['field']}: {f['message']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
