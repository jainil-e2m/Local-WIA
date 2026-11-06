"""Re-run queued jobs with StageCaller.call_json patched to save the request it builds (no provider call possible:
the run is in replay mode and no key is set)."""
import json, sys
from backend_pipeline.llm import stage as st

out = sys.argv[1]
orig = st.StageCaller.call_json

def capture(self, stage, run, run_dir, system, user, input_hash, schema, **kw):
    request = st.stage_body(self.settings, stage, system, user, schema)
    fp = self.request_key(run=run, stage=stage, endpoint=self.settings.openrouter_base_url.rstrip("/"), request=request, input_hash=input_hash)
    json.dump({"stage": stage, "fingerprint": fp, "mode": run.mode, "input_hash": input_hash, "request": request}, open(f"{out}/{stage}.json", "w"), indent=1)
    return orig(self, stage, run, run_dir, system, user, input_hash, schema, **kw)

st.StageCaller.call_json = capture
from backend_pipeline import storage_cli
sys.argv = ["storage_cli", "worker", "--max-jobs", "5"]
raise SystemExit(storage_cli.main())
