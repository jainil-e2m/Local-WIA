"""python -m evaluation <command>, run from backend/.

  manifest                          print benchmark version 1's inputs and their hashes
  seed                              write the benchmark labels as calibration rows (needs ATELIER_DATABASE_URL, migration 005)
  run --configs a,b --weeks w1,w2 --samples 3 [--dry] [--knowledge-base-version V]
                                    generate and report; a paid run needs an active run plan (ATELIER_RUN_PLAN_ID or
                                    ATELIER_RUN_PLAN_FILE, or research/benchmark-v1/run_plan.json)
  judge-calibrate [--judge-model M] [--context kb+pack] [--seed N] [--single-order] [--limit N] [--labels auto|files|db]
                  [--dry | --replay]
                                    run E.B3's pairwise judge on the labelled pairs and report its agreement with them;
                                    --dry counts the calls and estimates their cost, --replay reads saved responses
                                    only; a paid run needs an active run plan (ATELIER_RUN_PLAN_FILE, or
                                    research/benchmark-v1/run_plan_judge.json)
  judge-compare --configs a,b [--weeks w1,w2] [--samples 3] [the judge options above, without --limit and --labels]
                                    run the same judge on two configurations' saved samples (configuration, or
                                    configuration@knowledge-base-version), slate against slate per week and sample;
                                    never generates a sample
  judge-labels [--judge dry|replay|paid] [--judge-model M] [--context kb|kb+pack|none]
                                    E.B3: score every recorded judge output against WIA's notes of 13 and 20 October
                                    (research/judge-labels/, offline, no call); --judge also runs the pairwise judge on
                                    her pairs (dry: count and plan command; paid: under a run plan). A diagnostic only
  packets --name week1|week2|october [--from D --to D] [--budget-tokens N]
                                    benchmark v2 (E.B27): a whole week's packet from the moments ledger (needs
                                    ATELIER_DATABASE_URL, the working copy), with its scene coverage, written under
                                    research/benchmark-v2/packets/; no model call. `run --weeks week2_v2` reads it
  stance --configs a,b --weeks week2 --samples 3 [--knowledge-base-version V]
                                    E.B26's report on saved samples (golden scenes g07 and g09, ATTRACT cards, template
                                    titles); reads saved samples only, never generates one
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from . import benchmark, judge, run


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m evaluation")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("manifest")
    sub.add_parser("seed")
    go = sub.add_parser("run")
    go.add_argument("--configs", default="default,strategist_v5")
    go.add_argument("--weeks", default="week1,week2")
    go.add_argument("--samples", type=int, default=3)
    go.add_argument("--dry", action="store_true")
    go.add_argument("--smoke", action="store_true", help="Allow fewer than three samples: a smoke result, saved as one and never "
                    "the recorded benchmark result (E.B3)")
    go.add_argument("--knowledge-base-version", help="Evaluate a compiled version (needs ATELIER_DATABASE_URL); L.B4")
    judging = argparse.ArgumentParser(add_help=False)
    judging.add_argument("--judge-model", default=judge.JUDGE_MODEL)
    judging.add_argument("--context", choices=judge.CONTEXTS, default=judge.DEFAULT_CONTEXT)
    judging.add_argument("--seed", type=int, default=judge.DEFAULT_SEED)
    judging.add_argument("--single-order", action="store_true", help="Judge each pair in its drawn order only (no bias check)")
    how = judging.add_mutually_exclusive_group()
    how.add_argument("--dry", action="store_true")
    how.add_argument("--replay", action="store_true")
    cal = sub.add_parser("judge-calibrate", parents=[judging])
    cal.add_argument("--limit", type=int, help="The first N pairs, in group and ID order")
    cal.add_argument("--labels", choices=("auto", "files", "db"), default="auto")
    versus = sub.add_parser("judge-compare", parents=[judging])
    versus.add_argument("--configs", required=True, help="Two configurations, each optionally @knowledge-base-version")
    versus.add_argument("--weeks", default="week1,week2")
    versus.add_argument("--samples", type=int, default=3)
    jl = sub.add_parser("judge-labels")
    jl.add_argument("--judge", choices=("dry", "replay", "paid"))
    jl.add_argument("--judge-model", default=None)
    jl.add_argument("--context", choices=judge.CONTEXTS, default=judge.DEFAULT_CONTEXT)
    jl.add_argument("--seed", type=int, default=judge.DEFAULT_SEED)
    pk = sub.add_parser("packets")
    pk.add_argument("--name", required=True, choices=("week1", "week2", "october"))
    pk.add_argument("--from", dest="start", type=date.fromisoformat)
    pk.add_argument("--to", dest="end", type=date.fromisoformat)
    pk.add_argument("--budget-tokens", type=int)
    st = sub.add_parser("stance")
    st.add_argument("--configs", default="strategist_v5,strategist_v6")
    st.add_argument("--weeks", default="week2")
    st.add_argument("--samples", type=int, default=3)
    st.add_argument("--knowledge-base-version", help="Read the samples saved under this compiled version's label")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if args.command == "manifest":
        result = benchmark.manifest()
    elif args.command == "judge-calibrate":
        result = calibrate(args)
    elif args.command == "judge-compare":
        result = compare(args)
    elif args.command == "judge-labels":
        from . import wia_notes
        result = wia_notes.report()
        if args.judge:
            result["judge"] = wia_notes.measure(wia_notes.load(), model=args.judge_model or wia_notes.JUDGE_MODEL,
                                                context=args.context, seed=args.seed, mode=args.judge)
        if args.judge != "dry":
            path = wia_notes.RESULTS / f"{date.today().isoformat()}-wia-notes{'-' + args.judge if args.judge else '-offline'}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
            result = {"saved": path.relative_to(benchmark.PROJECT).as_posix(),
                      "recorded": [{k: r[k] for k in ("judge", "her_failures_caught", "her_passes_kept", "missed")}
                                   for r in result["recorded"]]}
    elif args.command == "packets":
        from backend_pipeline.database import connect
        from backend_pipeline.storage_config import StorageSettings

        from . import packets
        with connect(StorageSettings.from_env().database_url, vectors=False) as conn:
            built = packets.build(conn, args.name, start=args.start, end=args.end,
                                  budget_tokens=args.budget_tokens or packets.BUDGET_TOKENS)
        path = packets.write(built)
        result = {"saved": path.relative_to(benchmark.PROJECT).as_posix(), "state": built["state"],
                  "coverage": built["coverage"]["summary"]}
    elif args.command == "stance":
        from . import stance
        label = f".{args.knowledge_base_version}" if args.knowledge_base_version else ""
        result = stance.report(args.configs.split(","), args.weeks.split(","), args.samples, label)
    elif args.command == "seed":
        from backend_pipeline.database import connect
        from backend_pipeline.storage_config import StorageSettings
        with connect(StorageSettings.from_env().database_url, vectors=False) as conn:
            result = benchmark.seed(conn)
    else:
        configs, weeks = args.configs.split(","), args.weeks.split(",")
        if args.knowledge_base_version:
            from functools import partial

            from backend_pipeline.database import connect
            from backend_pipeline.storage_config import StorageSettings
            run.CONTEXT.update(version=args.knowledge_base_version,
                               connection=partial(connect, StorageSettings.from_env().database_url))
        if args.samples < 3 and not args.dry and not args.smoke:
            raise SystemExit("A recorded result needs at least three samples per configuration (E.B3)")
        if args.dry:
            result = {f"{c}-{w}": run.generate(c, w, 1, dry=True) for c in configs for w in weeks}
        else:
            result = run.report(configs, weeks, args.samples)
            smoke = "-smoke" if args.samples < 3 else ""
            path = run.OUT / "results" / f"{date.today().isoformat()}-{'-'.join(configs)}{run.run_label()}{smoke}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
            result = {"saved": path.relative_to(benchmark.PROJECT).as_posix(), "total_cost_usd": result["total_cost_usd"]}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def calibrate(args) -> dict:
    labels, cards, source = judge.load_labels(args.labels)
    pairs, excluded = judge.pairs_from_labels(labels, cards)
    mode = "dry" if args.dry else "replay" if args.replay else "paid"
    result = judge.calibrate(pairs, model=args.judge_model, context=args.context, seed=args.seed,
                             both_orders=not args.single_order, mode=mode, limit=args.limit, label_source=source,
                             excluded=excluded)
    if mode == "dry":
        return result
    path = judge.results_path(args.judge_model, args.context)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return {"saved": path.relative_to(benchmark.PROJECT).as_posix(), "total_cost_usd": result["total_cost_usd"],
            "missing": result["missing"], "unparsed": result["unparsed"], "prescreen": result["prescreen"]}


def compare(args) -> dict:
    names = args.configs.split(",")
    mode = "dry" if args.dry else "replay" if args.replay else "paid"
    result = judge.compare_configs(names, args.weeks.split(","), args.samples, model=args.judge_model, context=args.context,
                                   seed=args.seed, both_orders=not args.single_order, mode=mode)
    if mode == "dry":
        return result
    path = judge.results_path(args.judge_model, args.context, names)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return {"saved": path.relative_to(benchmark.PROJECT).as_posix(), "total_cost_usd": result["total_cost_usd"],
            "missing": result["missing"], "unparsed": result["unparsed"], "configs": result["configs"],
            "position_bias": result["position_bias"]}


if __name__ == "__main__":
    main()
