"""Write the portfolio read model into the frontend's local WIA preview data file.

    python -m backend.scripts.export_frontend_snapshot          # → frontend/src/kb-live.local.json (gitignored)

Same shape production serves from GET /api/v1/portfolio (services/read_models/portfolio.py), with logos
embedded as data URIs so the single-file export works offline.
"""
import json

from backend.config import BACKEND_DIR
from backend.services.read_models.portfolio import build

OUT = BACKEND_DIR.parent / "frontend" / "src" / "kb-live.local.json"


def main() -> None:
    out = build(logos="inline")
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} · {len(out['clients'])} clients, {len(out['evidence'])} evidence, "
          f"{len(out['actions'])} actions, {len(out['calls'])} upcoming calls, {len(out['events'])} history events")


if __name__ == "__main__":
    main()
