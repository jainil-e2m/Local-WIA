"""E.B6: argument labels (the engineer's reading, D21) -> same-argument pair labels -> the collapse cutoff."""
import json, sys
L = {
 "A_searchterm": "c044 c054 c112 c023 c027 c029 c032 c036 c038 c042 c047 c051 c056 c110 c116 c002 c006 c009",
 "A_comparison": "c024 c025 c028 c031 c035 c039 c041 c043 c048 c050 c052 c057 c109 c113 c114 c003 c007 c010",
 "A_funnel": "c022 c026 c033 c037 c040 c045 c055 c004 c008 c011",
 "A_retarget": "c030 c034 c046 c049 c053 c108 c111 c115",
 "A_market": "c000", "A_candid": "c001 c005",
 "B_buying": "c058 c063 c066 c070 c076 c080 c082 c088 c091 c094 c100 c103 c117 c121 c125 c012 c015 c019",
 "B_tour": "c060 c062 c068 c071 c074 c079 c083 c087 c092 c096 c099 c104 c118 c122 c127 c013 c016 c020",
 "B_accel": "c059 c067 c075 c078 c095 c119 c126",
 "B_click": "c064 c072 c084 c089 c093 c101 c105 c107 c123 c014 c017 c021",
 "B_sales_tool": "c073 c086 c098",
 "B_existing": "c061 c065 c069 c077 c081 c085 c090 c097 c102 c106 c120 c124 c128",
 "B_firststep": "c018"}
arg = {c: k for k, v in L.items() for c in v.split()}
d = json.load(open(sys.argv[1]))
assert set(arg) == {c["id"] for c in d["cards"]}, set(c["id"] for c in d["cards"]) ^ set(arg)
pairs = [{**p, "duplicate": arg[p["a"]] == arg[p["b"]], "args": [arg[p["a"]], arg[p["b"]]]} for p in d["pairs"]]
def score(cut, ps):
    tp = sum(p["duplicate"] and p["cosine"] >= cut for p in ps); fp = sum((not p["duplicate"]) and p["cosine"] >= cut for p in ps)
    fn = sum(p["duplicate"] and p["cosine"] < cut for p in ps)
    return tp, fp, fn, (2 * tp / (2 * tp + fp + fn) if tp else 0)
rows = []
for c in [x / 100 for x in range(70, 96)]:
    tp, fp, fn, f1 = score(c, pairs); rows.append((c, tp, fp, fn, round(f1, 4)))
print("cut  tp  fp  fn  f1  (all same-week pairs)"); [print(*r) for r in rows]
neg = sorted((p for p in pairs if not p["duplicate"]), key=lambda p: -p["cosine"])[:8]
pos = sorted((p for p in pairs if p["duplicate"]), key=lambda p: p["cosine"])[:8]
print("hardest non-duplicates:", [(p["cosine"], p["args"]) for p in neg])
print("hardest duplicates:", [(p["cosine"], p["args"]) for p in pos])
sr = [p for p in pairs if p["same_run"]]
print("same-run pairs:", len(sr), "duplicates among them:", [(p["a"], p["b"], p["cosine"], p["args"][0]) for p in sr if p["duplicate"]])
print("same-run non-duplicates above 0.80:", [(p["cosine"], p["args"]) for p in sr if not p["duplicate"] and p["cosine"] >= 0.80])
json.dump({"labels": L, "pairs": pairs, "sweep": rows}, open(sys.argv[2], "w"), indent=1)
