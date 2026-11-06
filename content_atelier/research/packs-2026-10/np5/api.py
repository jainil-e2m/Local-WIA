"""A small client for the stack's API in NP-5 (not product code): `python -I api.py METHOD PATH [JSON]`.

STACK_API (default http://127.0.0.1:18081/storage), STACK_SECRET (the stack's ATELIER_API_SECRET) and STACK_ACTOR name the
API, its shared secret and the signed-in person, as the Atelier's Node server sends them."""
import json
import os
import sys

import httpx

BASE = os.getenv("STACK_API", "http://127.0.0.1:18081/storage")
HEADERS = {"Authorization": f"Bearer {os.getenv('STACK_SECRET', 'shakedown-local-secret')}",
           "X-Atelier-Actor": os.getenv("STACK_ACTOR", "ai@weddingindustryads.com"),
           "X-Atelier-Email": os.getenv("STACK_ACTOR", "ai@weddingindustryads.com")}


def call(method, path, body=None, **params):
    r = httpx.request(method, BASE + path, json=body, headers=HEADERS, params=params or None, timeout=120)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, r.text


if __name__ == "__main__":
    method, path = sys.argv[1], sys.argv[2]
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    status, value = call(method, path, body)
    print(status)
    print(json.dumps(value, indent=1, default=str) if not isinstance(value, str) else value[:4000])
