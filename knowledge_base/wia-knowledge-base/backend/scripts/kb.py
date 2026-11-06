"""Operator CLI for intake. Run from the repository root:

    python -m backend.scripts.kb clients backend/.local/clients.yaml
    python -m backend.scripts.kb connectors --register          # first time; later runs verify
    python -m backend.scripts.kb discover [--days 365] [--client SLUG]
    python -m backend.scripts.kb approve backend/.local/approval.yaml
    python -m backend.scripts.kb client add "Name" --slug name [--alias A ...]
    python -m backend.scripts.kb client archive|activate SLUG
    python -m backend.scripts.kb scope-add clickup list 901100000000 --client SLUG
    python -m backend.scripts.kb not-applicable SLUG slack --reason "no channel" [--clear]
    python -m backend.scripts.kb mapping                       # client x source coverage (S2 done-when)
    python -m backend.scripts.kb sender-rule partner celebratecreative.com --reason "web agency for several clients"
    python -m backend.scripts.kb sender-rule list
    python -m backend.scripts.kb clickup connect   # each person once; then: clickup list | verify NAME | disconnect NAME
    python -m backend.scripts.kb leadlock status | locations | reconcile   # after the agency installs the LeadLock app
    python -m backend.scripts.kb outbound status | draft-post C123 "text" | approve <id>   # nothing is sent without a typed yes
    python -m backend.scripts.kb backfill [--days 30 | --full]
    python -m backend.workers.runner --drain                    # or the docker `worker` service
    python -m backend.scripts.kb status
    python -m backend.scripts.kb run stop|resume <run-id>       # a copy, on command
    python -m backend.scripts.kb portfolio refresh              # rebuild what the production frontend loads
    python -m backend.scripts.kb ai check | due | runs | preview SKILL SUBJECT [--out F]   # AI layer; preview sends nothing
    python -m backend.scripts.kb config                        # local or production mode, what runs, which credentials are set
    python -m backend.scripts.kb config export FILE | import FILE|-   # clients, contacts, people, mappings: no data, no tokens
    python -m backend.scripts.kb report
    python -m backend.scripts.kb email <gmail-message-id> [--quoted]   # read a stored client email from Gmail

--days defaults to INGEST_WINDOW_DAYS for backfill (unset = full history, production) and to
DISCOVERY_WINDOW_DAYS for discover. Mapping commands are the same ones the admin UI will call.
"""
import argparse
import re
import sys
from pathlib import Path
from uuid import UUID
from datetime import date

from sqlalchemy import func, select

from backend.config import get_settings
from backend.db import transaction
from backend.logging.config import configure
from backend.models.db import (
    Business,
    ConnectorAccount,
    ContentUnit,
    CoverageWindow,
    RecordAssociation,
    SenderRule,
    SourceRecord,
    SourceScope,
    SourceVersion,
    SyncRun,
    WorkItem,
)
from backend.services.clients import mapping, registry
from backend.services.intake import connectors, discovery, sync
from backend.services.intake.adapters import PROVIDERS
from backend.services.intake.scoping import live_scope


def _days(args) -> int | None:
    if getattr(args, "full", False):
        return None
    return args.days if args.days is not None else get_settings().ingest_window_days


def cmd_clients(args):
    print("loaded:", ", ".join(registry.load(Path(args.file))))


def cmd_connectors(args):
    ok = True
    for provider in args.providers or PROVIDERS:
        try:
            account = connectors.verify(provider, register=args.register)
            print(f"  {provider:9} OK       {account.display_identity}")
        except Exception as exc:  # report every provider, then fail
            ok = False
            print(f"  {provider:9} FAILED   {type(exc).__name__}: {str(exc)[:160]}")
    sys.exit(0 if ok else 1)


def cmd_discover(args):
    days = None if args.full else (args.days if args.days is not None else get_settings().discovery_window_days)
    business_ids = None
    if args.client:
        with transaction() as session:
            business_ids = [mapping.business_by_slug(session, args.client).id]
    full = not args.client and not args.providers  # every client, every source: stale suggestions are cleared
    results = {}
    for provider, r in discovery.run_discovery(args.providers or PROVIDERS, days, business_ids, reset=full).items():
        if isinstance(r, Exception):
            print(f"  {provider:9} FAILED   {type(r).__name__}: {str(r)[:160]}")
            continue
        results[provider] = r
        print(f"  {provider:9} {len(r.scopes):4} scope candidates, {len(r.contacts):4} contact candidates")
    partners = next((r.possible_partners for r in results.values() if r.possible_partners), {})
    if partners:
        print(f"  possible partners (proposed for 3+ clients, held back): {len(partners)}")
    with transaction() as session:
        for contact, why in mapping.contact_conflicts(session):
            print(f"  WARNING approved contact {contact.email or '@' + contact.domain}: {why}; review it")
    proposal, approval = discovery.write_proposal(results, get_settings().local_dir)
    print(f"proposal: {proposal}\napproval file: {approval}")


def cmd_sender_rule(args):
    value = args.value.strip().lower()
    target = {"email": value} if "@" in value.lstrip("@") else {"domain": value.lstrip("@")}
    with transaction() as session:
        if args.action == "list":
            links = mapping.partner_links(session)
            for kind, email, domain, reason in session.execute(select(
                    SenderRule.kind, SenderRule.email, SenderRule.domain, SenderRule.reason).order_by(SenderRule.kind)):
                key = email or "@" + domain
                linked = f"  [linked to: {', '.join(links[key])}]" if links.get(key) else ""
                print(f"  {kind:8} {key:45} {reason}{linked}")
            return
        if args.action == "remove":
            mapping.remove_sender_rule(session, actor="cli", **target)
        else:
            mapping.add_sender_rule(session, args.action, actor="cli", reason=args.reason or "", **target)
    print("ok")


def cmd_client(args):
    with transaction() as session:
        if args.action == "add":
            slug = args.slug or re.sub(r"[^a-z0-9]+", "-", args.name.lower()).strip("-")
            b = mapping.create_client(session, name=args.name, slug=slug, aliases=args.alias or [],
                                      actor="cli", discover=not args.no_discover)
            print(f"added {b.slug}{'' if args.no_discover else '; discovery queued (run the worker)'}")
            return
        b = mapping.business_by_slug(session, args.name)
        mapping.set_client_status(session, b.id, "inactive" if args.action == "archive" else "active",
                                  expected_revision=None, actor="cli")
        print(f"{b.slug}: {b.status} ({'syncing paused' if b.status == 'inactive' else 'syncing resumes'})")


def cmd_scope_add(args):
    with transaction() as session:
        b = mapping.business_by_slug(session, args.client)
        scope = mapping.add_scope_by_id(session, args.provider, args.kind, args.external_id, business_id=b.id, actor="cli")
        print(f"approved {args.provider} {scope.kind} {scope.name} for {b.slug}")


def cmd_not_applicable(args):
    with transaction() as session:
        b = mapping.business_by_slug(session, args.client)
        if args.clear:
            mapping.clear_not_applicable(session, b.id, args.provider, actor="cli")
        else:
            mapping.mark_not_applicable(session, b.id, args.provider, reason=args.reason or "", actor="cli")
    print("ok")


MARK = {"mapped": "OK", "via_contacts": "OK*", "paused": "paused", "not_applicable": "n/a",
        "suggested": "review", "missing": "MISSING", "not_connected": "-"}


def cmd_mapping(args):
    with transaction() as session:
        rows = mapping.coverage(session)
    print(f"  {'client':32} {'status':8} " + " ".join(f"{p:9}" for p in PROVIDERS))
    missing = 0
    for r in rows:
        missing += sum(1 for st, _ in r["cells"].values() if st == "missing") if r["status"] == "active" else 0
        print(f"  {r['name'][:32]:32} {r['status']:8} " + " ".join(f"{MARK[r['cells'][p][0]]:9}" for p in PROVIDERS))
    print("  OK = dedicated scope, OK* = shared source via approved contacts, review = suggestions awaiting an admin")
    print(f"  missing cells for active clients: {missing}")


def cmd_leadlock(args):
    """LeadLock Marketplace app: the agency grant and the sub-accounts it covers (no client data shown)."""
    from backend.models.db import LeadLockInstallation, LeadLockLocation
    from backend.services.intake import leadlock_app
    settings = get_settings()
    if args.action == "status":
        for name, value in (("LEADLOCK_APP_CLIENT_ID", settings.leadlock_app_client_id),
                            ("LEADLOCK_APP_CLIENT_SECRET", settings.leadlock_app_client_secret),
                            ("LEADLOCK_APP_ID", settings.leadlock_app_id),
                            ("LEADLOCK_COMPANY_ID", settings.leadlock_company_id)):
            print(f"  {name:28} {'set' if value else 'MISSING'}")
        print(f"  {'LEADLOCK_REDIRECT_URI':28} {settings.leadlock_redirect_uri}")
        with transaction() as session:
            inst = session.execute(select(LeadLockInstallation).where(LeadLockInstallation.revoked_at.is_(None))
                                   .order_by(LeadLockInstallation.installed_at.desc())).scalars().first()
            if inst is None:
                last = session.execute(select(LeadLockInstallation).order_by(
                    LeadLockInstallation.installed_at.desc())).scalars().first()
                print("  agency grant: none" + (f" (last one revoked: {last.revoked_reason})" if last else
                                                 " (install the app from the LeadLock agency view)"))
            else:
                future = {True: "on", False: "off"}.get(inst.install_to_future_locations, "not reported")
                print(f"  agency grant: active since {inst.installed_at:%Y-%m-%d %H:%M}, refreshed "
                      f"{inst.revision - 1}x, access token expires {inst.access_expires_at:%Y-%m-%d %H:%M}")
                print(f"  scopes: {len(inst.scopes)}   install on new sub-accounts: {future}")
            counts = session.execute(select(LeadLockLocation.state, func.count()).group_by(LeadLockLocation.state)).all()
            print("  sub-accounts: " + (", ".join(f"{st}={n}" for st, n in counts) or "none yet"))
        return
    if args.action == "locations":
        with transaction() as session:
            rows = session.execute(select(LeadLockLocation).order_by(LeadLockLocation.state,
                                                                     LeadLockLocation.name)).scalars().all()
            for loc in rows:
                expires = f"token to {loc.access_expires_at:%m-%d %H:%M}" if loc.access_expires_at else "no token"
                print(f"  {(loc.name or '(name pending)')[:36]:36} {loc.location_id:24} {loc.state:11} {expires}"
                      + (f"  ! {loc.last_error}" if loc.last_error else ""))
            if not rows:
                print("  no sub-accounts yet")
        return
    result = leadlock_app.reconcile()
    print(f"  installed: {result['installed']}   marked uninstalled: {result['removed']}   "
          f"install on new sub-accounts: {result['install_to_future_locations']}")
    minted = failed = 0
    for location_id in result["needs_token"]:
        try:
            leadlock_app.mint_location_token(location_id)
            minted += 1
        except Exception as exc:  # recorded on the row; keep going for the others
            failed += 1
            print(f"  ! {location_id}: {type(exc).__name__}: {exc}")
    print(f"  tokens minted: {minted}   failed: {failed}")


def cmd_clickup(args):
    """Per-person ClickUp connections (OAuth app "WIA Knowledge Base")."""
    from backend.models.db.outbound import ClickUpConnection
    from backend.models.db.people import Person
    from backend.services.outbound import clickup_oauth
    if args.action == "connect":
        token = _clickup_oauth_callback(clickup_oauth, open_browser=not args.no_browser, paste=args.paste)
        with transaction() as session:
            conn = clickup_oauth.connect(session, token, actor="cli")
            person = session.get(Person, conn.person_id)
            print(f"connected: {person.name} (ClickUp user {conn.clickup_username}); "
                  f"workspaces granted: {len(conn.workspace_ids)}")
        return
    with transaction() as session:
        if args.action == "list":
            rows = session.execute(select(ClickUpConnection, Person.name).join(
                Person, Person.id == ClickUpConnection.person_id).order_by(ClickUpConnection.connected_at)).all()
            for c, name in rows:
                state = f"revoked {c.revoked_at:%Y-%m-%d} ({c.revoked_reason})" if c.revoked_at else "active"
                print(f"  {name:28} {c.clickup_username or c.clickup_user_id:24} {state}")
            if not rows:
                print("  no ClickUp connections yet")
            return
        person = session.execute(select(Person).where(Person.name == args.person)).scalar_one_or_none()
        if person is None:
            raise SystemExit(f"no person named {args.person!r}")
        if args.action == "verify":
            conn = clickup_oauth.verify(session, person.id)
            print(f"ok: {person.name}'s ClickUp connection works (user {conn.clickup_username})")
        else:
            clickup_oauth.disconnect(session, person.id, actor="cli")
            print(f"disconnected {person.name}: their ClickUp edits are now blocked")


def _clickup_oauth_callback(clickup_oauth, *, open_browser: bool, paste: bool = False,
                            timeout_seconds: int = 300) -> str:
    """Catch ClickUp's redirect and return the access token.

    Listens on the redirect port on both IPv4 and IPv6 loopback ("localhost" may resolve to ::1 in the
    browser). With `paste`, or if nothing arrives, the user pastes the redirected URL from the address bar."""
    import secrets as pysecrets
    import socket
    import threading
    import webbrowser
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlparse

    redirect = urlparse(get_settings().clickup_oauth_redirect_uri)
    state, result, done = pysecrets.token_urlsafe(24), {}, threading.Event()

    def take(query: str) -> None:
        q = {k: v[0] for k, v in parse_qs(query).items()}
        if q.get("state") not in (None, state):
            result["error"] = "state mismatch: this callback belongs to an older attempt"
        elif "code" not in q:
            result["error"] = q.get("error", "no authorization code in the callback")
        else:
            result["code"] = q["code"]
        done.set()

    class Handler(BaseHTTPRequestHandler):
        timeout = 5  # browsers pre-open idle connections; never let one hold the listener

        def do_GET(self):
            url = urlparse(self.path)
            if url.path != redirect.path:
                self.send_response(404); self.end_headers(); return
            take(url.query)
            body = ("ClickUp connected. You can close this tab and return to the terminal." if "code" in result
                    else f"ClickUp connection failed: {result.get('error')}").encode()
            self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers(); self.wfile.write(body)

        def log_message(self, *a):  # keep the code out of the console
            pass

    class Server(ThreadingHTTPServer):
        daemon_threads = True  # each connection on its own thread: an idle one can't block the callback

    class V6Server(Server):
        address_family = socket.AF_INET6

    servers = []
    if not paste:
        for cls, host in ((Server, "127.0.0.1"), (V6Server, "::1")):
            try:
                servers.append(cls((host, redirect.port or 80), Handler))
            except OSError:
                pass  # e.g. no IPv6 loopback, or the port is taken on that stack
        if not servers:
            print(f"port {redirect.port} is busy (is the KB API running?); falling back to pasting the URL")
        for srv in servers:
            threading.Thread(target=srv.serve_forever, daemon=True).start()

    url = clickup_oauth.authorize_url(state)
    print("Sign in to ClickUp in your browser as the account to connect, tick the Wedding Industry Ads workspace,")
    print("and approve:\n  " + url)
    if open_browser:
        webbrowser.open(url)
    try:
        if servers:
            print(f"Waiting up to {timeout_seconds // 60} minutes for ClickUp to send you back...")
            done.wait(timeout_seconds)
        if not done.is_set():
            pasted = input("Paste the full URL from the browser address bar after approving: ").strip()
            take(urlparse(pasted).query)
    finally:
        for srv in servers:
            srv.shutdown(); srv.server_close()
    if "code" not in result:
        raise SystemExit(f"not connected: {result.get('error', 'no callback received')}")
    return clickup_oauth.exchange_code(result["code"])

def _outbound_request(session, ref: str):
    from sqlalchemy import cast, String as SqlString
    from backend.models.db.outbound import OutboundRequest
    rows = session.execute(select(OutboundRequest).where(cast(OutboundRequest.id, SqlString).like(ref + "%"))).scalars().all()
    if len(rows) != 1:
        raise SystemExit(f"{'no' if not rows else 'more than one'} request matches {ref!r}")
    return rows[0]


def _describe(req, people_names) -> str:
    who = f" as {people_names.get(req.as_person_id, '?')}" if req.as_person_id else ""
    lines = [f"  request {str(req.id)[:8]}  {req.kind}{who}  [{req.state}]  drafted by {req.drafted_by} "
             f"{req.drafted_at:%Y-%m-%d %H:%M}"]
    if req.kind == "clickup_task_update":
        pv, before = req.preview, req.preview.get("before", {})
        lines.append(f"  task      : {pv.get('task_name')} ({req.target}) in list {pv.get('list_name')} ({pv.get('list_id')})")
        if "status" in req.payload:
            lines.append(f"  status    : {before.get('status')} -> {req.payload['status']}")
        if "due_date" in req.payload:
            lines.append(f"  due date  : {before.get('due_date')} -> {req.payload['due_date']} (ms)")
        if req.payload.get("assignees_add") or req.payload.get("assignees_remove"):
            lines.append(f"  assignees : now {before.get('assignees')}; add {req.payload.get('assignees_add', [])}; "
                         f"remove {req.payload.get('assignees_remove', [])}")
    else:
        lines.append(f"  to        : {'channel' if req.kind == 'slack_post' else 'DM to user'} {req.target}")
        lines.append("  message   : " + req.payload["text"].replace("\n", "\n              "))
    if req.error:
        lines.append(f"  note      : {req.error}")
    return "\n".join(lines)


def cmd_outbound(args):
    """Outbound requests: draft -> approve (a listed approver types yes at a terminal) -> send, once."""
    from backend.models.db.outbound import OutboundRequest
    from backend.models.db.people import Person
    from backend.services.outbound import requests as outbound
    settings = get_settings()
    with transaction() as session:
        names = {p.id: p.name for p in session.execute(select(Person)).scalars()}
        if args.action == "status":
            print(f"  mode: {settings.outbound_mode}   kill switch: {'ON' if settings.outbound_kill_switch else 'off'}"
                  f"   approvers: {settings.outbound_approvers or 'none'}")
            print(f"  sandbox: channels {settings.outbound_sandbox_slack_channels}, DM users "
                  f"{settings.outbound_sandbox_slack_users}, ClickUp lists {settings.outbound_sandbox_clickup_lists}")
            counts = session.execute(select(OutboundRequest.state, func.count()).group_by(OutboundRequest.state)).all()
            print("  requests: " + (", ".join(f"{st}={n}" for st, n in counts) or "none"))
            return
        if args.action in ("draft-post", "draft-dm"):
            if not args.target or not args.text:
                raise SystemExit("give a target and the message text")
            fn = outbound.draft_slack_post if args.action == "draft-post" else outbound.draft_slack_dm
            req = fn(session, args.target, args.text, actor="cli")
            print(_describe(req, names))
            print("  waiting for approval: kb outbound approve " + str(req.id)[:8] if req.state == "draft"
                  else "  REFUSED by the guard: nothing will be sent")
            return
        if args.action == "draft-edit":
            person = session.execute(select(Person).where(Person.name == args.as_person)).scalar_one_or_none()
            if person is None:
                raise SystemExit(f"no person named {args.as_person!r} (use --as with a roster name)")
            req = outbound.draft_clickup_update(session, args.target, as_person_id=person.id, actor="cli",
                                                status=args.status, due_date=args.due,
                                                assignees_add=args.assign or [], assignees_remove=args.unassign or [])
            print(_describe(req, names))
            print("  waiting for approval: kb outbound approve " + str(req.id)[:8] if req.state == "draft"
                  else "  REFUSED by the guard: nothing will be sent")
            return
        if args.action == "list":
            q = select(OutboundRequest).order_by(OutboundRequest.drafted_at.desc())
            if not args.all:
                q = q.where(OutboundRequest.state.in_(("draft", "approved", "failed")))
            rows = session.execute(q.limit(50)).scalars().all()
            for r in rows:
                print(_describe(r, names) + "\n")
            if not rows:
                print("  nothing waiting")
            return
        req = _outbound_request(session, args.target or "")
        if args.action == "show":
            print(_describe(req, names))
            return
        if args.action == "reject":
            outbound.reject(session, req.id, approver=args.approver or "cli")
            print("  rejected: it will not be sent")
            return
        if args.action == "approve":
            print(_describe(req, names))
            interactive = sys.stdin.isatty()
            if not interactive:
                raise SystemExit("approval needs a person at an interactive terminal: nothing approved")
            approver = args.approver or input("  Your approver name: ").strip()
            typed = input("  Type yes to approve and send exactly this, anything else to reject: ")
            try:
                outbound.approve(session, req.id, approver=approver, typed=typed, interactive=interactive)
            except outbound.OutboundError as exc:
                print(f"  not approved: {exc}")
                return
            req_id = req.id
        elif args.action == "send":
            req_id = req.id
        else:
            raise SystemExit("unknown action")
    with transaction() as session:  # the approval is committed before anything is sent
        try:
            req = outbound.send(session, req_id)
            print(f"  SENT: {req.result}")
        except outbound.OutboundError as exc:
            print(f"  not sent: {exc}")


def cmd_approve(args):
    print(discovery.apply_approval(Path(args.file)))


def cmd_backfill(args):
    days = _days(args)
    with transaction() as session:
        q = select(SourceScope.id).join(ConnectorAccount).where(live_scope(),
                                                                 ConnectorAccount.state == "active")
        if args.providers:
            q = q.where(ConnectorAccount.provider.in_(args.providers))
        # The resumable path: a stopped run continues from its checkpoint; Drive folders share one account run.
        run_ids = {sync.request_run(session, scope_id, "backfill", days=days)[0].id
                   for scope_id in session.execute(q.order_by(SourceScope.id)).scalars()}
    print(f"queued {len(run_ids)} scope backfill run(s), window: "
          f"{'full history' if days is None else f'last {days} days'}")



def cmd_run(args):
    """Stop or resume one copy on command (`kb status` lists them; ids are in `railway logs` too)."""
    with transaction() as session:
        try:
            run = (sync.operator_stop if args.action == "stop" else sync.resume)(session, args.run_id)
        except ValueError as exc:
            raise SystemExit(str(exc))
        print(f"run {run.id} ({run.mode}): {run.state}")



def cmd_password_hash(args):
    """KB_TEAM_PASSWORD_HASH for the shared team password. The password is read without echo and never printed."""
    import getpass
    from backend.routes.access import hash_password
    first = getpass.getpass("Team password: ")
    if len(first) < 12:
        raise SystemExit("use at least 12 characters")
    if getpass.getpass("Again: ") != first:
        raise SystemExit("the two entries differ")
    print(hash_password(first))



def cmd_portfolio(args):
    """Rebuild the portfolio now (it also rebuilds by itself after each copy that stored changes)."""
    from backend.services.read_models import portfolio
    out = portfolio.refresh()
    print(f"portfolio built: {len(out['clients'])} clients, {len(out['evidence'])} evidence, "
          f"{len(out['actions'])} actions, {len(out['calls'])} upcoming calls")



def cmd_ai(args):
    """The AI layer, operator side. Nothing here sends a prompt: `preview` renders it, `check` reads OpenRouter's
    public model list. Calls happen only in the AI worker, only with AI_MODE=live."""
    from datetime import UTC, datetime
    from backend.services.ai import runner, skills, sweep
    s = get_settings()
    if args.action == "check":
        with transaction() as session:
            spent = runner.month_spend(session, datetime.now(UTC))
        print(f"  AI_MODE={s.ai_mode} · key {'set' if s.openrouter_api_key else 'not set'} · "
              f"budget ${s.ai_monthly_budget_usd:g}/month · spent this month ${spent:.2f}")
        ids = {name: skills.model_for(skill) for name, skill in skills.SKILLS.items()}
        try:
            from backend.services.ai.openrouter import models_available
            found = models_available(sorted(set(ids.values())))
        except Exception as exc:  # noqa: BLE001 — offline: still show the configuration
            found = {}
            print(f"  (could not reach OpenRouter's model list: {type(exc).__name__})")
        for name, skill in skills.SKILLS.items():
            mark = {True: "ok", False: "NOT FOUND"}.get(found.get(ids[name]), "unchecked")
            print(f"  {name:20} {ids[name]:34} reasoning={skill.reasoning or '-':6} max_out={skill.max_tokens:<5} "
                  f"reserve=${skill.max_cost_usd:.2f}  {mark}")
    elif args.action == "due":
        with transaction() as session:
            for skill, subject, marker in sweep.due(session):
                print(f"  {skill:20} {subject}  ({marker})")
    elif args.action == "preview":
        if not args.skill or not args.subject:
            raise SystemExit("kb ai preview SKILL SUBJECT  (kb ai due lists subjects)")
        fetch = (lambda message_id: {"authored": "(email text not fetched in this preview)"}) if args.no_email else None
        with transaction() as session:
            p = runner.prepare(session, args.skill, args.subject, fetch=fetch)
        text = f"===== SYSTEM =====\n{p.system}\n\n===== USER =====\n{p.user}\n"
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"wrote {args.out} (it holds client data: keep it under backend/.local/)")
        else:
            print(text)
        print(f"  model {skills.model_for(p.skill)} · ~{(len(p.system) + len(p.user)) // 4:,} input tokens · "
              f"{len(p.refs.items)} refs · clipped: {p.checks.get('clipped') or 'nothing'} · nothing was sent")
    elif args.action == "runs":
        from backend.models.db import AiRun
        with transaction() as session:
            for r in session.execute(select(AiRun).order_by(AiRun.created_at.desc()).limit(args.limit)).scalars():
                print(f"  {r.created_at:%Y-%m-%d %H:%M} {r.skill:20} {r.state:9} ${r.cost_usd:.4f} "
                      f"{r.prompt_tokens}+{r.completion_tokens} tok {r.model} {r.subject_id}"
                      + (f" error={r.error_class}" if r.error_class else ""))
    elif args.action == "team-meetings":
        _ai_team_meetings()


def _ai_team_meetings():
    """Read in full the internal team meetings already seen as pointers (title pattern + all invitees WIA's)."""
    import re as _re
    from backend.services.people.roster import internal_addresses
    pattern = get_settings().internal_meeting_title_pattern
    if not pattern:
        raise SystemExit("set INTERNAL_MEETING_TITLE_PATTERN first")
    queued = 0
    with transaction() as session:
        internal = internal_addresses(session)
        rows = session.execute(select(SourceRecord, SourceVersion).join(ConnectorAccount)
                               .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
                               .where(ConnectorAccount.provider == "fathom", SourceRecord.admitted_at.is_(None))).all()
        targets = [(r.scope_id, r.external_id) for r, v in rows
                   if _re.search(pattern, v.attributes.get("title") or "", _re.IGNORECASE)
                   and v.attributes.get("invitees")
                   and all((i.get("email") or "").lower() in internal for i in v.attributes["invitees"])]
    for scope_id, external_id in targets:
        with transaction() as session:
            sync.request_run(session, scope_id, "refresh", target=external_id)
            queued += 1
    print(f"queued {queued} team meeting(s) to be read in full")


CREDENTIALS = ("SLACK_BOT_TOKEN", "CLICKUP_TOKEN", "CLICKUP_TEAM_ID", "FATHOM_API_KEY", "GOOGLE_CLIENT_ID",
               "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "CLICKUP_OAUTH_CLIENT_ID", "CLICKUP_OAUTH_CLIENT_SECRET",
               "LEADLOCK_APP_CLIENT_ID", "LEADLOCK_APP_CLIENT_SECRET", "KB_SECRET_KEY", "OPS_TOKEN",
               "KB_TEAM_PASSWORD_HASH", "OPENROUTER_API_KEY")


def cmd_config(args):
    """The effective configuration, with no secret values: which mode, what runs, which credentials are set.
    Reaching this line means get_settings() accepted the configuration.

    `config export FILE` / `config import FILE|-`: move clients, contacts, people and mappings (never source
    data or tokens) into an empty database, e.g. production (services/clients/config_transfer.py)."""
    if args.action in ("export", "import"):
        return _config_transfer(args)
    from urllib.parse import urlparse
    s = get_settings()
    window = "full history" if s.ingest_window_days is None else f"last {s.ingest_window_days} days"
    print(f"  mode:            {s.mode} (PRODUCTION_MODE={str(s.production_mode).lower()}, ENVIRONMENT={s.environment})")
    print(f"  sync scheduler:  {'on' if s.sync_scheduler_enabled else 'off (on demand: kb backfill + worker --drain)'}"
          f", incremental every {s.sync_interval_seconds}s, reconcile every {s.reconcile_interval_seconds}s")
    print(f"  intake window:   {window}")
    print(f"  outbound:        {s.outbound_mode}{' (kill switch ON)' if s.outbound_kill_switch else ''}")
    print(f"  AI:              {s.ai_mode}" + (f", budget ${s.ai_monthly_budget_usd:g}/month" if s.ai_mode == "live" else ""))
    print(f"  team password:   {'set' if s.kb_team_password_hash else 'not set (local: routes open)'}")
    print(f"  database host:   {urlparse(s.database_url.replace('+psycopg', '')).hostname}")
    print(f"  KB app URL:      {s.kb_app_url}")
    missing = [name for name in CREDENTIALS if not getattr(s, name.lower())]
    print(f"  credentials:     {len(CREDENTIALS) - len(missing)} of {len(CREDENTIALS)} set"
          + (f"; missing: {', '.join(missing)}" if missing else ""))



def _config_transfer(args):
    import json
    from backend.services.clients import config_transfer
    if not args.file:
        raise SystemExit(f"kb config {args.action} needs a file ('-' reads stdin on import)")
    if args.action == "export":
        with transaction() as session:
            text = config_transfer.dumps(config_transfer.export(session))
        Path(args.file).write_text(text, encoding="utf-8")
        print(f"wrote {args.file}: client data, keep it out of git and delete it after the import")
        return
    raw = sys.stdin.buffer.read().decode("utf-8") if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    with transaction() as session:
        try:
            counts = config_transfer.import_(session, json.loads(raw), actor="kb config import")
        except ValueError as exc:
            raise SystemExit(str(exc))
    print("imported: " + ", ".join(f"{k}={v}" for k, v in counts.items()))


def cmd_status(args):
    s = get_settings()
    print(f"  mode: {s.mode} · sync scheduler: {'on' if s.sync_scheduler_enabled else 'off (on demand)'}")
    with transaction() as session:
        rows = session.execute(
            select(ConnectorAccount.provider, SourceScope.name, SyncRun.state, SyncRun.pages, CoverageWindow.counts,
                   CoverageWindow.state, SyncRun.error_class, SyncRun.id, SyncRun.mode)
            .join(SourceScope, SyncRun.scope_id == SourceScope.id)
            .join(ConnectorAccount, SourceScope.connector_account_id == ConnectorAccount.id)
            .join(CoverageWindow, CoverageWindow.run_id == SyncRun.id)
            .where(SyncRun.mode.in_(("backfill", "reconcile")))
            .order_by(ConnectorAccount.provider, SourceScope.name, SyncRun.started_at)
        ).all()
        for p, name, state, pages, c, cov, err, run_id, mode in rows:
            print(f"  {p:9} {name[:40]:40} {mode:9} {state:9} {run_id} pages={pages:<3} stored={c['stored_content']}+{c['stored_metadata']}m "
                  f"unchanged={c['unchanged']} excluded={c['excluded']} gaps={c['failed'] + c['inaccessible'] + c['unsupported']} "
                  f"coverage={cov}{' error=' + err if err else ''}")
        work = session.execute(select(WorkItem.lane, WorkItem.state, func.count()).group_by(WorkItem.lane, WorkItem.state)).all()
        print("  work:", ", ".join(f"{lane}/{state}={n}" for lane, state, n in work))


def cmd_report(args):
    out = get_settings().local_dir / "backfill_report.md"
    with transaction() as session:
        lines = ["# Backfill report", "", "## Per client", "",
                 "| Client | Provider | Records | With content | Units | Multi-client |", "|---|---|---|---|---|---|"]
        q = (select(Business.name, ConnectorAccount.provider, func.count(func.distinct(SourceRecord.id)),
                    func.count(func.distinct(SourceRecord.id)).filter(SourceRecord.qualification == "content"),
                    func.sum(SourceVersion.unit_count), func.count().filter(RecordAssociation.multi_client))
             .select_from(RecordAssociation)
             .join(Business, Business.id == RecordAssociation.business_id)
             .join(SourceRecord, SourceRecord.id == RecordAssociation.record_id)
             .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
             .join(ConnectorAccount, ConnectorAccount.id == SourceRecord.connector_account_id)
             .group_by(Business.name, ConnectorAccount.provider).order_by(Business.name, ConnectorAccount.provider))
        for name, provider, n, content, units, multi in session.execute(q):
            lines.append(f"| {name} | {provider} | {n} | {content} | {units or 0} | {multi} |")
        unassociated = session.execute(
            select(func.count()).select_from(SourceRecord)
            .where(~select(RecordAssociation.id).where(RecordAssociation.record_id == SourceRecord.id).exists())
        ).scalar_one()
        lines += ["", f"Records with no client association (unresolved): {unassociated}", "",
                  "## Units by domain", "", "| Domain | Units |", "|---|---|"]
        for domain, n in session.execute(select(ContentUnit.domain, func.count()).group_by(ContentUnit.domain)):
            lines.append(f"| {domain} | {n} |")
        lines += ["", "## Coverage per scope", "", "| Provider | Scope | Window start | State | Counts | Gaps |",
                  "|---|---|---|---|---|---|"]
        for p, name, ws, state, counts, gaps in session.execute(
                select(ConnectorAccount.provider, SourceScope.name, CoverageWindow.window_start, CoverageWindow.state,
                       CoverageWindow.counts, CoverageWindow.gaps)
                .join(SourceScope, SourceScope.id == CoverageWindow.scope_id)
                .join(ConnectorAccount, ConnectorAccount.id == SourceScope.connector_account_id)
                .order_by(ConnectorAccount.provider, SourceScope.name)):
            counts_txt = ", ".join(f"{k}={v}" for k, v in counts.items() if v)
            lines.append(f"| {p} | {name} | {ws:%Y-%m-%d} | {state} | {counts_txt} | {len(gaps)} |"
                         if ws else f"| {p} | {name} | full | {state} | {counts_txt} | {len(gaps)} |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report: {out}")


def cmd_email(args):
    """Intake keeps only a pointer to each email (BF-2). This reads the text from Gmail and stores nothing."""
    from backend.services.intake.adapters import get_adapter
    from backend.services.shared.errors import NotFoundError
    with transaction() as session:
        row = session.execute(
            select(SourceRecord, SourceVersion).join(ConnectorAccount)
            .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
            .where(ConnectorAccount.provider == "gmail", SourceRecord.record_kind == "gmail_message",
                   SourceRecord.external_id == args.message_id)).first()
    # Only client emails: a message seen in the mailbox but never admitted to a client stays unread.
    if row is None or row.SourceRecord.admitted_at is None:
        raise SystemExit("not a stored client email")
    pointer = row.SourceVersion.attributes
    try:
        body = get_adapter("gmail").fetch_body(args.message_id)
    except NotFoundError:
        raise SystemExit("no longer available in Gmail")
    print(f"Subject: {pointer.get('subject') or '(no subject)'}\nFrom: {pointer.get('from')}\n"
          f"To: {', '.join(pointer.get('to') or [])}\nDate: {pointer.get('sent_header_at')}\n")
    if pointer.get("body_sha256") and pointer["body_sha256"] != body["body_sha256"]:
        print("(the text has changed in Gmail since intake)\n")
    print(body["authored"] or "(no text)")
    if args.quoted and body["quoted"]:
        print("\n--- quoted history ---\n" + body["quoted"])


def cmd_roster_load(args):
    from backend.services.people.roster import load_roster
    print(load_roster(Path(args.file), actor="cli"))


def cmd_people_list(args):
    from backend.models.db.people import Person
    with transaction() as session:
        q = select(Person).where(Person.merged_into_id.is_(None)).order_by(Person.kind, Person.name)
        if args.kind:
            q = q.where(Person.kind == args.kind)
        for p in session.execute(q).scalars():
            print(f"  {p.id}  {p.kind:16} {p.status:9} r{p.revision:<3} {p.name}  {', '.join(p.functions or [])}")


def cmd_people_unknown(args):
    from backend.services.people.resolve import unknown_people
    with transaction() as session:
        rows = unknown_people(session, limit=args.limit)
        print("  identity | provider | external key | display name | email | party | units")
        for r in rows:
            print(f"  {r['id']} | {r['provider']} | {r['external_key']} | {r.get('display_name') or ''} | "
                  f"{r.get('email') or ''} | {r.get('party') or 'unknown'} | {r['unit_count']}")


def cmd_people_link(args):
    from backend.services.people.roster import person_by_name_or_id
    from backend.services.people.resolve import link_identity
    with transaction() as session:
        person = person_by_name_or_id(session, args.person)
        link_identity(session, args.identity, person.id, actor="cli", expected_revision=args.expected_revision)
        print(f"linked to {person.name}")


def cmd_people_resolve(args):
    from backend.services.people.resolve import resolve_all
    with transaction() as session:
        counts = resolve_all(session, only_unresolved=not args.all)
    print("  " + ", ".join(f"{party}={count}" for party, count in sorted(counts.items())))


def cmd_team_suggest(args):
    from backend.services.people.teams import former_assignments, suggest_teams
    with transaction() as session:
        changed = suggest_teams(session, days=args.days, actor="cli")
        former = former_assignments(session)
    print(f"suggested rows changed: {changed}")
    for row in former:
        print(f"  WARNING former person: {row['person']} | {row['client']} | {row['task_count']} current task(s)")


def cmd_team_set(args):
    from backend.services.people.roster import person_by_name_or_id
    from backend.services.people.teams import set_team_member
    with transaction() as session:
        business = mapping.business_by_slug(session, args.client)
        person = person_by_name_or_id(session, args.person)
        member = set_team_member(session, business.id, args.role, person.id, actor="cli",
                                 started_on=args.started_on, expected_revision=args.expected_revision)
        print(f"{member.id}: {business.slug} {member.role} -> {person.name} (confirmed, r{member.revision})")


def cmd_team_end(args):
    from backend.services.people.teams import end_team_member
    with transaction() as session:
        row = end_team_member(session, args.member, actor="cli", ended_on=args.ended_on,
                              expected_revision=args.expected_revision)
        print(f"{row.id}: ended (r{row.revision})")


def cmd_team_list(args):
    from backend.services.people.teams import clients_without_owner, former_assignments, team_for
    with transaction() as session:
        clients = ([mapping.business_by_slug(session, args.client)] if args.client else
                   list(session.execute(select(Business).where(Business.status == "active").order_by(Business.name)).scalars()))
        ids = {b.id for b in clients}
        missing = {b.id for b in clients_without_owner(session)}
        for business in clients:
            print(f"  {business.slug}: {business.name}" + (" [NO CONFIRMED OWNER]" if business.id in missing else ""))
            for row in team_for(session, business.id):
                print(f"    {row['id']}  {row['role']:12} {row['status']:9} r{row['revision']:<3} {row['person']}"
                      + (" [FORMER PERSON]" if row['kind'] == "former" else ""))
        for row in former_assignments(session):
            if row['business_id'] in ids:
                print(f"  WARNING former person still assigned: {row['person']} | {row['client']} | "
                      f"{row['task_count']} current task(s): {', '.join(row['tasks'].values())}")


def main():
    configure("WARNING")
    parser = argparse.ArgumentParser(prog="kb")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("clients"); p.add_argument("file"); p.set_defaults(fn=cmd_clients)
    p = sub.add_parser("connectors"); p.add_argument("--register", action="store_true")
    p.add_argument("providers", nargs="*"); p.set_defaults(fn=cmd_connectors)
    for name, fn in (("discover", cmd_discover), ("backfill", cmd_backfill)):
        p = sub.add_parser(name); p.add_argument("--days", type=int); p.add_argument("--full", action="store_true")
        p.add_argument("providers", nargs="*"); p.set_defaults(fn=fn)
        if name == "discover":
            p.add_argument("--client", help="slug: discover for this client only")
    p = sub.add_parser("client"); p.add_argument("action", choices=["add", "archive", "activate"])
    p.add_argument("name", help="client name (add) or slug"); p.add_argument("--slug")
    p.add_argument("--alias", action="append"); p.add_argument("--no-discover", action="store_true")
    p.set_defaults(fn=cmd_client)
    p = sub.add_parser("scope-add"); p.add_argument("provider"); p.add_argument("kind"); p.add_argument("external_id")
    p.add_argument("--client", required=True); p.set_defaults(fn=cmd_scope_add)
    p = sub.add_parser("not-applicable"); p.add_argument("client"); p.add_argument("provider")
    p.add_argument("--reason"); p.add_argument("--clear", action="store_true"); p.set_defaults(fn=cmd_not_applicable)
    sub.add_parser("mapping").set_defaults(fn=cmd_mapping)
    p = sub.add_parser("outbound", help="draft / approve / send Slack messages and ClickUp edits")
    p.add_argument("action", choices=["status", "draft-post", "draft-dm", "draft-edit", "list", "show", "approve",
                                      "reject", "send"])
    p.add_argument("target", nargs="?", help="channel ID / Slack user ID / ClickUp task ID / request ID")
    p.add_argument("text", nargs="?", help="message text (draft-post, draft-dm)")
    p.add_argument("--as", dest="as_person", help="draft-edit: whose ClickUp connection (roster name)")
    p.add_argument("--status"); p.add_argument("--due", help="YYYY-MM-DD")
    p.add_argument("--assign", action="append", help="ClickUp user ID to add (repeatable)")
    p.add_argument("--unassign", action="append", help="ClickUp user ID to remove (repeatable)")
    p.add_argument("--approver"); p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_outbound)
    p = sub.add_parser("clickup", help="per-person ClickUp connections (OAuth)")
    p.add_argument("action", choices=["connect", "list", "verify", "disconnect"])
    p.add_argument("person", nargs="?", help="person name (verify / disconnect)")
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--paste", action="store_true", help="paste the redirected URL instead of listening on the port")
    p.set_defaults(fn=cmd_clickup)
    p = sub.add_parser("leadlock", help="LeadLock Marketplace app: agency grant and sub-account tokens")
    p.add_argument("action", choices=["status", "locations", "reconcile"])
    p.set_defaults(fn=cmd_leadlock)
    p = sub.add_parser("sender-rule", help="team / partner / blocked senders, for every client")
    p.add_argument("action", choices=["team", "partner", "blocked", "remove", "list"])
    p.add_argument("value", nargs="?", default="", help="an email address, or a domain")
    p.add_argument("--reason"); p.set_defaults(fn=cmd_sender_rule)
    p = sub.add_parser("approve"); p.add_argument("file"); p.set_defaults(fn=cmd_approve)
    p = sub.add_parser("config", help="show the effective settings (no secret values), or export/import configuration")
    p.add_argument("action", nargs="?", choices=["show", "export", "import"], default="show")
    p.add_argument("file", nargs="?", help="export: file to write; import: file to read, or - for stdin")
    p.set_defaults(fn=cmd_config)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("password-hash", help="hash the shared team password for KB_TEAM_PASSWORD_HASH").set_defaults(
        fn=cmd_password_hash)
    p = sub.add_parser("ai", help="AI layer: check, due, preview (renders, sends nothing), runs, team-meetings")
    p.add_argument("action", choices=["check", "due", "preview", "runs", "team-meetings"])
    p.add_argument("skill", nargs="?"); p.add_argument("subject", nargs="?")
    p.add_argument("--out"); p.add_argument("--no-email", action="store_true", help="preview without reading Gmail")
    p.add_argument("--limit", type=int, default=30); p.set_defaults(fn=cmd_ai)
    p = sub.add_parser("portfolio", help="rebuild the portfolio the production frontend loads")
    p.add_argument("action", choices=["refresh"]); p.set_defaults(fn=cmd_portfolio)
    p = sub.add_parser("run", help="stop or resume one copy")
    p.add_argument("action", choices=["stop", "resume"]); p.add_argument("run_id", type=UUID); p.set_defaults(fn=cmd_run)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    p = sub.add_parser("email", help="read one stored client email from Gmail (the body is never stored)")
    p.add_argument("message_id"); p.add_argument("--quoted", action="store_true"); p.set_defaults(fn=cmd_email)
    p = sub.add_parser("roster", help="load the private people/roster file")
    roster_sub = p.add_subparsers(dest="roster_action", required=True)
    p = roster_sub.add_parser("load"); p.add_argument("file"); p.set_defaults(fn=cmd_roster_load)
    p = sub.add_parser("people", help="people and provider-identity resolution")
    people_sub = p.add_subparsers(dest="people_action", required=True)
    p = people_sub.add_parser("list"); p.add_argument("--kind"); p.set_defaults(fn=cmd_people_list)
    p = people_sub.add_parser("unknown"); p.add_argument("--limit", type=int, default=100); p.set_defaults(fn=cmd_people_unknown)
    p = people_sub.add_parser("link"); p.add_argument("identity", type=UUID); p.add_argument("person")
    p.add_argument("--expected-revision", type=int); p.set_defaults(fn=cmd_people_link)
    p = people_sub.add_parser("resolve"); p.add_argument("--all", action="store_true"); p.set_defaults(fn=cmd_people_resolve)
    p = sub.add_parser("team", help="suggestions and confirmed account teams")
    team_sub = p.add_subparsers(dest="team_action", required=True)
    p = team_sub.add_parser("suggest"); p.add_argument("--days", type=int, default=120); p.set_defaults(fn=cmd_team_suggest)
    p = team_sub.add_parser("set"); p.add_argument("client"); p.add_argument("role"); p.add_argument("person")
    p.add_argument("--started-on", type=date.fromisoformat); p.add_argument("--expected-revision", type=int)
    p.set_defaults(fn=cmd_team_set)
    p = team_sub.add_parser("end"); p.add_argument("member", type=UUID)
    p.add_argument("--ended-on", type=date.fromisoformat); p.add_argument("--expected-revision", type=int)
    p.set_defaults(fn=cmd_team_end)
    p = team_sub.add_parser("list"); p.add_argument("client", nargs="?")
    p.set_defaults(fn=cmd_team_list)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
