from __future__ import annotations

import argparse
import json

from .config import Settings
from .pipeline import Pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Content Atelier transcript-to-angle pipeline")
    parser.add_argument("command", choices=["plan", "run"])
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--mode", choices=["plan", "fake", "live", "replay"], default="plan")
    parser.add_argument("--run-id", help="Optional new report ID; existing IDs are never overwritten")
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.mode == "live" and not settings.live_enabled:
        parser.error("Live mode requires CONTENT_ATELIER_LIVE=true")
    if args.mode == "live":
        try:
            settings.require_explicit_models()
        except ValueError as error:
            parser.error(str(error))
    pipeline = Pipeline(settings)
    result = (
        pipeline.plan(args.week, args.mode)
        if args.command == "plan"
        else pipeline.run(args.week, mode=args.mode, run_id=args.run_id)
    )
    print(json.dumps(result.model_dump(mode="json") if hasattr(result, "model_dump") else result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
