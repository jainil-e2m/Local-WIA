"""Re-run the deterministic brief checks on the stored v1 briefs (plan S.B4), with no model call.

Each v1 brief's dossier is rebuilt from its own row (`gate_two.dossier`, what Gate 2 reads), the document is checked with
today's `briefs.validation.checks`, and the result is set beside the findings recorded when the brief was made. A finding
that was recorded then and is gone now is listed, so a person can see which N2 false positives the S.B4 repairs removed.

    ATELIER_DATABASE_URL=... python scripts/revalidate_v1_briefs.py [--out result.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend_pipeline.briefs.gate_two import dossier
from backend_pipeline.briefs.validation import checks
from backend_pipeline.repository import ContentRepository
from backend_pipeline.storage_config import StorageSettings


def key(finding: dict) -> tuple:
    return finding.get("severity"), finding.get("claim_id"), finding.get("message")


def revalidate(repo) -> list[dict]:
    with repo.connection() as conn:
        rows = conn.execute("""SELECT * FROM content_briefs WHERE (content_body->>'schema_version') IS DISTINCT FROM '2'
            AND content_body ? 'document' ORDER BY brief_id""").fetchall()
    results = []
    for row in rows:
        now = checks(row["content_body"]["document"], dossier(row))
        then = [f for f in (row["content_body"].get("review") or {}).get("findings", []) if isinstance(f, dict)]
        current, recorded = {key(f) for f in now}, {key(f) for f in then}
        results.append({
            "brief_id": row["brief_id"], "angle_id": row["angle_id"], "week_id": row["week_id"],
            "schema_version": row["content_body"].get("schema_version"),
            "findings_now": now,
            "recorded_then": then,
            "gone_since": [dict(zip(("severity", "claim_id", "message"), k)) for k in sorted(recorded - current, key=str)],
            "new_since": [dict(zip(("severity", "claim_id", "message"), k)) for k in sorted(current - recorded, key=str)],
            "blocking_now": sum(f["severity"] == "blocking" for f in now),
        })
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    results = revalidate(ContentRepository(StorageSettings.from_env()))
    text = json.dumps(results, indent=2, ensure_ascii=False, default=str)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
