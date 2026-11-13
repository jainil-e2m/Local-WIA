"""`kb ads ...` and `kb callprep ...` (registered in scripts/kb.py).

    kb ads status                                  configured platforms, accounts seen and mapped, last pull
    kb ads google-auth                             one-time: a refresh token with the adwords scope (you sign in)
    kb ads discover                                list every ad account the credentials can see, with a suggested client
    kb ads map google_ads 1234567890 client-slug   map an account (or `none` to unmap and delete its figures)
    kb ads pull [--days N] [--account ID]          read daily campaign figures for mapped accounts
    kb ads summary CLIENT                          the figures call prep shows for a client

    kb callprep seed                               load the repo skill files into call_skills (edits are kept)
    kb callprep calls [--days 14]                  upcoming client calls: type, host, RSVP risk, brief state
    kb callprep facts CALL_ID                      the computed facts for one call (no model)
    kb callprep preview CALL_ID [--out F] [--no-email]   the exact prompt the model would get (sends nothing)
    kb callprep due                                what the scheduler would build now
"""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


def cmd_ads(args):
    from backend.db import transaction
    from backend.services import ads
    if args.action == "status":
        with transaction() as s:
            for provider, row in ads.status(s).items():
                print(f"  {ads.PROVIDERS[provider]:10} configured={row['configured']!s:5} accounts={row['accounts']} "
                      f"mapped={row['mapped']} last pull={row['last_pull'] or 'never'}")
    elif args.action == "google-auth":
        _google_auth()
    elif args.action == "discover":
        for a in ads.discover():
            mapped = f"-> {a['mapped_to']}" if a["mapped_to"] else (f"(suggest: {a['suggested']})" if a["suggested"] else "(unmapped)")
            print(f"  {a['provider']:10} {a['account_id']:>16}  {a['name'][:48]:48} {a.get('status') or '':10} {mapped}")
        print("Map one with: kb ads map <provider> <account id> <client slug>")
    elif args.action == "map":
        if not (args.provider and args.account and args.client):
            raise SystemExit("kb ads map <google_ads|meta> <account id> <client slug | none>")
        with transaction() as s:
            ads.map_account(s, args.provider, args.account, None if args.client == "none" else args.client, actor="kb-cli")
        print("mapped; run `kb ads pull` to read its figures")
    elif args.action == "pull":
        for row in ads.pull(days=args.days, account=args.account):
            print("  " + json.dumps(row))
    elif args.action == "summary":
        from sqlalchemy import select
        from backend.models.db import Business
        with transaction() as s:
            b = s.execute(select(Business).where(Business.slug == args.provider)).scalar_one()
            print(json.dumps(ads.summary(s, b.id, datetime.now(UTC).date()), indent=2, default=str))


def _google_auth():
    """Loopback OAuth for the Google Ads refresh token. The person signs in in their own browser; nothing is stored
    here: copy the printed token into backend/.env as GOOGLE_ADS_REFRESH_TOKEN."""
    import secrets
    import socket
    import urllib.parse
    from http.server import BaseHTTPRequestHandler, HTTPServer

    import httpx

    from backend.config import get_settings
    from backend.services.ads.google_ads import SCOPE
    s = get_settings()
    client_id = s.google_ads_client_id or s.google_client_id
    secret = s.google_ads_client_secret or s.google_client_secret
    if not (client_id and secret):
        raise SystemExit("set GOOGLE_ADS_CLIENT_ID/SECRET (or GOOGLE_CLIENT_ID/SECRET, a Desktop-app OAuth client) first")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    redirect, state, got = f"http://127.0.0.1:{port}", secrets.token_urlsafe(16), {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            got.update(q)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Done. You can close this tab and return to the terminal.")

        def log_message(self, *a):
            pass

    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": state})
    print("Open this link, sign in with a Google account that can see WIA's manager account, and allow access:\n")
    print(url + "\n")
    HTTPServer(("127.0.0.1", port), Handler).handle_request()
    if got.get("state") != state or "code" not in got:
        raise SystemExit(f"sign-in did not complete: {got.get('error', 'no code returned')}")
    r = httpx.post("https://oauth2.googleapis.com/token", timeout=25, data={
        "grant_type": "authorization_code", "code": got["code"], "redirect_uri": redirect,
        "client_id": client_id, "client_secret": secret})
    r.raise_for_status()
    token = r.json().get("refresh_token")
    if not token:
        raise SystemExit("Google returned no refresh token; remove the app's access at myaccount.google.com and retry")
    print("Add this line to backend/.env (it is a credential: never commit it):\n")
    print(f"GOOGLE_ADS_REFRESH_TOKEN={token}")


def cmd_callprep(args):
    from backend.db import transaction
    from backend.services.callprep import facts, pack, registry, schedule, skill_files
    now = datetime.now(UTC)
    if args.action == "seed":
        with transaction() as s:
            for note in skill_files.seed(s, actor="kb-cli") or ["nothing to seed: the skills are current"]:
                print("  " + note)
    elif args.action == "calls":
        with transaction() as s:
            for c in registry.calls(s, now, now + timedelta(days=args.days)):
                state = "cancelled" if c.cancelled else f"set aside: {c.excluded}" if c.excluded else c.skill.name
                print(f"  {c.call_id}  {c.starts_at:%Y-%m-%d %H:%M}  {c.business.slug:24} {state:34} host={c.host}"
                      + (f"  !{c.attendance_risk}" if c.attendance_risk else ""))
    elif args.action == "due":
        with transaction() as s:
            for record_id, trigger, fp in schedule.due(s, now):
                print(f"  {record_id}  {trigger}  {fp[:12]}")
    elif args.action in ("facts", "preview"):
        if not args.call:
            raise SystemExit(f"kb callprep {args.action} CALL_ID   (kb callprep calls lists them)")
        with transaction() as s:
            call = registry.get(s, registry.record_id_of(args.call))
            if call is None:
                raise SystemExit("no client call with that id")
            data = pack.payload(s)
            if args.action == "facts":
                print(json.dumps(facts.compute(s, call, data, now), indent=2, default=str))
                return
            fetch = (lambda mid: {"authored": "(email text not fetched in this preview)"}) if args.no_email else None
            p = pack.build(s, call, data=data, fetch=fetch, now=now)
            system, user = pack.render(p)
        text = f"===== SYSTEM =====\n{system}\n\n===== USER =====\n{user}\n\n===== FINGERPRINT {p.fingerprint[:12]} =====\n"
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"wrote {args.out} (it holds client data: keep it under backend/.local/)")
        else:
            print(text)


def register(sub):
    p = sub.add_parser("ads", help="ad platforms (Google Ads MCC, Meta): status, google-auth, discover, map, pull, summary")
    p.add_argument("action", choices=["status", "google-auth", "discover", "map", "pull", "summary"])
    p.add_argument("provider", nargs="?", help="map: google_ads|meta; summary: the client slug")
    p.add_argument("account", nargs="?"); p.add_argument("client", nargs="?")
    p.add_argument("--days", type=int); p.add_argument("--account", dest="account_filter")
    p.set_defaults(fn=lambda a: cmd_ads(_pull_args(a)))
    p = sub.add_parser("callprep", help="call preparation: seed skills, list calls, facts, preview, due")
    p.add_argument("action", choices=["seed", "calls", "facts", "preview", "due"])
    p.add_argument("call", nargs="?"); p.add_argument("--days", type=int, default=14)
    p.add_argument("--out"); p.add_argument("--no-email", action="store_true")
    p.set_defaults(fn=cmd_callprep)


def _pull_args(a):
    if a.action == "pull":
        a.account = a.account_filter
    return a
