"""Run an NP research script against a remote database over a TCP proxy (NP-6; not product code).

The settings loader connects with a 3-second timeout (`settings_store`), which suits a service next to its database. Over
a proxy a connection sometimes takes longer, and the loader then falls back to the environment and defaults, which would
let a Gate 2 step or a pack queue run with the wrong settings. Here every connection waits up to 30 seconds, and that
fallback stops the script instead.

Usage (from backend/): python -I ../research/packs-2026-10/np5/remote.py <script.py> [its arguments]
"""
import logging
import runpy
import sys
from pathlib import Path

import psycopg

_connect = psycopg.connect


def connect(*args, **kwargs):
    kwargs["connect_timeout"] = max(int(kwargs.get("connect_timeout") or 0), 30)
    return _connect(*args, **kwargs)


psycopg.connect = connect


class _Fatal(logging.Handler):
    def emit(self, record):
        if record.getMessage().startswith("Settings table unreachable"):
            print(f"STOPPED: {record.getMessage()}", file=sys.stderr, flush=True)
            raise SystemExit(3)


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
from backend_pipeline import settings_store  # noqa: E402

settings_store.log.addHandler(_Fatal())
settings_store.log.propagate = True
logging.raiseExceptions = True
script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(script).resolve().parent))
runpy.run_path(script, run_name="__main__")
