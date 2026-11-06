"""One executor for every job (plan 0.B5, 0.B6, R35): rows first, RQ queues, one reconcile loop.

policy     which queue and timeout a stage has
dispatch   put committed rows on their queue (RQ job id = idempotency key + attempt)
executor   `run_job`, the function every queue worker runs
recover    settle a job whose worker is gone; paid work is not repeated unless its answer is saved
scheduler  the reconcile loop and the keyed scheduled work
periodic   `(task, period)` claims
health     job health from the job rows
"""
