"""2.B11's golden fixture, the search half (not product code): each golden scene of the Funktastic chain searched by a
paraphrase, as a person would look for it, over the whole archive; found when a top-k result is from the source call and
contains the scene's anchor (a chunk's text, or a moment's quote or anchor passage).

Usage (from backend/): python -I ../research/n8-2026-10/golden_search.py <golden.json> <out.json> [k] [client_id]
(a client_id searches within that account only, the filter the N8 identities make possible)
with ATELIER_DATABASE_URL, ATELIER_ARTIFACT_ROOT and the embedding key in the environment (one embedding call per query).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from backend_pipeline.config import Settings  # noqa: E402
from backend_pipeline.repository import ContentRepository  # noqa: E402
from backend_pipeline.search.api import SearchRequest, run_search  # noqa: E402
from backend_pipeline.storage_config import StorageSettings  # noqa: E402

PARAPHRASES = {
    "f01": "a client's DJ business went from about seventeen events last year to ninety this year",
    "f02": "the client says everything runs automatically so she never has to do manual work",
    "f03": "weddings booked from ad leads without any outreach, just through automated follow-up",
    "f04": "couples on calls say they found the business by seeing it on Instagram",
    "f05": "leads come in automatically and turn into booked consultation calls",
}


def norm(text):
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).split())


def main():
    golden = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    filters = {"client_id": sys.argv[4]} if len(sys.argv) > 4 else {}
    repo, models = ContentRepository(StorageSettings.from_env()), Settings.from_env()
    results = []
    for scene in golden["scenes"]:
        query = PARAPHRASES[scene["id"]]
        answer = run_search(repo, models, SearchRequest(text=query, k=k, scope="all", filters=filters))
        hits = []
        for rank, hit in enumerate(answer["hits"], 1):
            citation = hit["citation"].model_dump(mode="json")
            text = json.dumps(citation) + " " + (json.dumps(hit["chunk"].model_dump(mode="json")) if hit["kind"] == "chunk" else
                                                 json.dumps(hit["moment"].model_dump(mode="json")))
            if scene["document"]["transcript_id"] in text and norm(scene["anchor"]) in norm(text):
                hits.append({"rank": rank, "kind": hit["kind"], "matched_by": hit["matched_by"],
                             "id": hit["moment"].moment_id if hit["kind"] == "moment" else hit["chunk"].chunk_id})
        results.append({"id": scene["id"], "query": query, "found": bool(hits), "hits": hits[:3], "vector": answer.get("query_vector")})
        print(scene["id"], bool(hits), hits[:1])
    Path(sys.argv[2]).write_text(json.dumps({"k": k, "filters": filters, "results": results,
                                              "found": sum(r["found"] for r in results), "scenes": len(results)}, indent=1),
                                  encoding="utf-8")


if __name__ == "__main__":
    main()
