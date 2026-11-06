import sys, json, glob, os, re, collections
sys.stdout.reconfigure(encoding="utf-8")
prefix = sys.argv[1] if len(sys.argv) > 1 else "J-"
rows = []
for f in sorted(glob.glob(os.path.join("runs", prefix + "*.json"))):
    name = os.path.basename(f)[:-5]
    m = re.match(r"J(?:W1R?)?-(.+?)-X_(.+?)-Y_(.+)$", name)
    judge, x, y = m.groups()
    o = json.load(open(f, encoding="utf-8"))["output"]
    pref = {"X": x, "Y": y, "tie": "tie"}[o["overall_preference"]]
    crit = {c["criterion"]: {"X": x, "Y": y, "tie": "tie"}[c["better"]] for c in o["criteria"]}
    rows.append((judge, x, y, pref, o["estimated_whitney_rating"], crit, o["factual_problems"], o["overall_reason"]))
pairs = collections.defaultdict(list)
for r in rows:
    pairs[tuple(sorted([r[1], r[2]]))].append(r)
for (a, b), rs in pairs.items():
    print(f"\n=== {a}  vs  {b}")
    tally = collections.Counter(r[3] for r in rs)
    print("  overall preference tally:", dict(tally))
    crit_tally = collections.defaultdict(collections.Counter)
    for judge, x, y, pref, rating, crit, fp, reason in rs:
        ra = {x: rating["X"], y: rating["Y"]}
        for k, v in crit.items(): crit_tally[k][v] += 1
        print(f"  judge={judge:18s} first-shown={x[:22]:22s} prefers={pref[:22]:22s} rating {a[:10]}={ra[a]} {b[:10]}={ra[b]}")
        for p in fp: print("     factual:", {"X": x, "Y": y}[p["set"]][:22], "|", p["angle"][:60], "|", p["problem"][:260])
    for k, c in crit_tally.items(): print(f"    {k:34s} {dict(c)}")
