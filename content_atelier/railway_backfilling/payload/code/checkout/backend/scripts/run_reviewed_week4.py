"""Prepare the approved quote recovery or send exactly one remaining Week 4 angle call."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend_pipeline.config import BACKEND_ROOT, Settings
from backend_pipeline.model_experiment import MODELS, SUITE
from backend_pipeline.reviewed_experiment import prepare_reviewed_recovery, run_reviewed_cell


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "angles"])
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--model", choices=list(MODELS))
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    base = Settings.from_env()
    suite = base.data_root / "experiments" / SUITE
    if args.action == "prepare":
        if not args.approved or args.live or args.model:
            parser.error("Local recovery preparation requires --approved; it never dispatches inference")
        proposal = BACKEND_ROOT.parent / "research/week3-week4-comparison-2026-10-15/week4-quote-recovery-proposal.json"
        result = prepare_reviewed_recovery(suite, proposal, approved=True)
    else:
        if not args.live or not args.model or args.approved:
            parser.error("One remaining angle call requires --model and --live after reviewed preparation")
        result = run_reviewed_cell(base, suite, args.model, live=True)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
