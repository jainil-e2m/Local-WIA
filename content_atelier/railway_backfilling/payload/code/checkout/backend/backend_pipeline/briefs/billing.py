from ..costs import call_record,write_run_summary
from ..store import JsonStore,canonical_hash
STAGES=('brief_plan','brief_grade','brief_write','brief_review','brief_repair','brief_query_embedding','brief_web')

def record(worker,job,run,stage,fingerprint,raw=None,*,dispatched=False,reused=False):
    store=JsonStore(worker.storage.artifact_root);directory=f'brief-runs/{run["run_id"]}'
    value=call_record(raw=raw,dispatched=dispatched and not worker.storage.synthetic,reused=reused,
        stage=stage,job_id=job['job_id'],attempt=job['attempt_count'],fingerprint=fingerprint,
        synthetic=worker.storage.synthetic,real_external_dispatch=dispatched and not worker.storage.synthetic)
    path=f'{directory}/costs/{job["job_id"]}-{job["attempt_count"]}-{stage}-{fingerprint}.json'
    store.write_json(path,value,overwrite=True)
    return write_run_summary(store,directory,stages_to_report=STAGES)
