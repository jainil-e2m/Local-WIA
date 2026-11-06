"""The scheduler starts itself again between passes once its memory passes the limit (production, 30 October to 6 November
2026: about 1 GB a day, toward the service's 8 GB). No database or queue needed."""
import sys

import pytest

from backend_pipeline.jobs import scheduler


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="reads /proc")
def test_past_the_limit_it_starts_again_in_place_and_not_before():
    started = []
    def execv(path, argv):
        started.append(argv)
    assert not scheduler.restart_if_large(10**6, execv=execv, uptime=3600), "under the limit: nothing"
    assert not scheduler.restart_if_large(1, execv=execv, uptime=60), "just started: never, whatever the limit"
    assert scheduler.restart_if_large(1, execv=execv, uptime=3600)
    assert started == [[sys.executable, "-m", "backend_pipeline.jobs", "scheduler"]]


def test_without_proc_it_never_restarts(monkeypatch):
    monkeypatch.setattr(scheduler, "resident_mb", lambda: None)
    assert not scheduler.restart_if_large(1, execv=lambda *a: pytest.fail("restarted"), uptime=3600)
    scheduler.release_memory()  # a no-op where glibc is not the allocator
