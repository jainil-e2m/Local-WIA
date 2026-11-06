import json, sys
for b in json.load(sys.stdin):
    ev = {e["evidence_id"]: e for e in b["selected_evidence"]}
    print("==", b["brief_id"])
    for c in b["claims"]:
        print("  %s kind=%s status=%r quals=%s" % (c["claim_id"], c["kind"], c["source_status"], c.get("qualifications")))
        print("     text:", c["text"][:170])
        for i in c["evidence_ids"]:
            e = ev.get(i, {})
            print("     ev %s: status=%r quals=%s" % (i, e.get("claim_status"), e.get("qualifications")))
