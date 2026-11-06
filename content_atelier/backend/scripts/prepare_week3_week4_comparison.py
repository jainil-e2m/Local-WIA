"""Prepare two shared extractions and six isolated angle calls. Paid stages require --live."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend_pipeline.config import BACKEND_ROOT, Settings
from experiments.model_experiment import MODELS, SUITE, prepare_suite, run_cell, run_extraction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "extract", "angles"], nargs="?", default="prepare")
    parser.add_argument("--week", type=int, choices=[3, 4])
    parser.add_argument("--model", choices=list(MODELS))
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    base = Settings.from_env()
    suite = base.data_root / "experiments" / SUITE
    if args.action == "prepare":
        if args.live:
            parser.error("Preparation never sends inference requests")
        manifest = prepare_suite(base, suite, BACKEND_ROOT / ".storage-artifacts/verification/week3-week4-models-20261015")
        print(json.dumps({"suite": str(suite), "status": manifest["status"], "max_paid_calls": manifest["max_paid_calls"],
                          "extractions": manifest["extractions"], "cells": manifest["cells"]}, indent=2))
    elif args.action == "extract":
        if not args.live or args.week is None or args.model is not None:
            parser.error("Extraction requires --week and --live; its model is fixed to Luna Pro")
        print(json.dumps(run_extraction(base, suite, args.week, live=True), indent=2))
    else:
        if not args.live or args.week is None or args.model is None:
            parser.error("Angle generation requires --week, --model and --live after user approval")
        print(json.dumps(run_cell(base, suite, args.week, args.model, live=True), indent=2))


if __name__ == "__main__":
    main()
