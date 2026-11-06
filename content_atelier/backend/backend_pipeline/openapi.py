"""Publish or check the OpenAPI document the frontend's TypeScript types are generated from (plan 1.F1).

    python -m backend_pipeline.openapi --check      # CI: exits 1 when backend/openapi.json differs from the application
    python -m backend_pipeline.openapi --write      # after changing a route or a response model in api_models.py

The document is `app.openapi()` of `backend_pipeline.api:app`, with sorted keys, two-space indentation and LF line
endings, so the same application always renders the same bytes. Building it reads no database and calls no provider.
The frontend then runs `npm run api:types` and commits `frontend/src/api/schema.d.ts`; its CI step fails on drift.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import BACKEND_ROOT

DOCUMENT = Path(BACKEND_ROOT) / 'openapi.json'


def render(spec: dict) -> str:
    return json.dumps(spec, indent=2, sort_keys=True) + '\n'


def current() -> str:
    from .api import app
    return render(app.openapi())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    text = current()
    if args.write:
        DOCUMENT.write_bytes(text.encode('utf-8'))
        print(f'Wrote {DOCUMENT.name}')
        return 0
    # Compare bytes, so a CRLF checkout counts as drift instead of passing by accident.
    if not DOCUMENT.exists() or DOCUMENT.read_bytes() != text.encode('utf-8'):
        print('backend/openapi.json differs from the application. Run: python -m backend_pipeline.openapi --write', file=sys.stderr)
        return 1
    print('backend/openapi.json is current')
    return 0


if __name__ == '__main__':
    sys.exit(main())
