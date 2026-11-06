"""Export the live development week's three developed cards and their first v2 briefs from the local review store.

Inputs for the 19 October brief-writer experiment (E.B22). Reads the `atelier_test_review2` database (the reviewed
store of 18 October); writes `inputs/<angle>.json` with the approved card, the first brief version the writer produced
(after its one repair) and the evidence the writer saw. Call excerpts only, already committed under research/ (R48).
"""
import json
import pathlib
import sys

import psycopg

ROOT = pathlib.Path(__file__).parent
URL = sys.argv[1] if len(sys.argv) > 1 else "postgresql://atelier:atelier_ci_only@127.0.0.1:25432/atelier_test_review2"

FIRST_BRIEFS = {
    "angle_bb74a6718f964153adbecd86d0e9fbc9": "brief_32ea9d5a7246c57341881052",
    "angle_6cda7af998500d981f79f6d4": "brief_482c1f665c8f7d0dcbd1b714",
    "angle_6272bda35f744111ad64d919d4f2db12": "brief_2afef8cfe9822442a4bbf2d5",
}


def main():
    out = ROOT / "inputs"
    out.mkdir(exist_ok=True)
    with psycopg.connect(URL) as conn:
        for angle_id, brief_id in FIRST_BRIEFS.items():
            card = conn.execute("select content_body from content_angles where angle_id = %s", (angle_id,)).fetchone()[0]
            body, evidence, prior = conn.execute(
                "select content_body, selected_evidence, prior_content_context from content_briefs where brief_id = %s",
                (brief_id,)).fetchone()
            record = {"angle_id": angle_id, "brief_id": brief_id, "card": card.get("card", card),
                      "first_brief": body, "selected_evidence": evidence, "prior_content_context": prior}
            (out / f"{angle_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
            print(angle_id, "->", brief_id, "evidence items:", len(evidence) if isinstance(evidence, list) else type(evidence).__name__)


if __name__ == "__main__":
    main()
