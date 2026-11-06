"""Paged source reads with shared admission before content retrieval.

Provider dictionaries live only inside these functions. Checkpoints contain cursors,
IDs and times; they never contain bodies or raw API responses.
"""
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import select

from backend.db import transaction
from backend.models.db import DriveNode, SourceScope
from backend.models.domain.intake import ChangeBatch, Gap, NormalisedRecord
from backend.services.intake.admission import content_allowed, qualifies, recognize
from backend.services.intake.scoping import is_live, live_scope
from backend.services.shared.errors import IntakeError, NotFoundError, ScopeDeniedError


def tombstone(kind, external_id, *, availability="deleted_upstream", attributes=None, admitted=False):
    return NormalisedRecord(kind, external_id, None, None, None, attributes or {}, [],
        content_state="metadata_only", change_kind="tombstone", availability=availability,
        admitted=admitted, participants_complete=False, carry_content=True, authoritative=True)


def unavailable(kind, external_id, admitted=True):
    return tombstone(kind, external_id, availability="access_lost", admitted=admitted)


def fetch_or_gap(batch, kind, external_id, stored, fetch):
    """A second read distinguishes persistent access failure from a racing list/get."""
    for attempt in range(2):
        try:
            return fetch()
        except (NotFoundError, ScopeDeniedError) as exc:
            if attempt:
                batch.gaps.append(Gap(external_id, exc.error_class))
                if stored:
                    batch.records.append(unavailable(kind, external_id, stored.admitted))
    return None


def read_page(adapter, ctx, state):
    return READERS[adapter.provider](adapter, ctx, dict(state or {}))


def _finish(batch, state, cursor=None):
    batch.checkpoint = state
    batch.terminal = not bool(state.get("phase"))
    batch.committed_cursor = cursor if batch.terminal else None
    return batch


def read_gmail(a, ctx, st):
    kind = "gmail_message"
    batch = ChangeBatch([], None, False)
    if ctx.mode == "refresh":
        st = {"phase": "fetch", "ids": [ctx.target_external_id]}
    if not st:
        # Capture before enumeration, never after the potentially hours-long load.
        baseline = a._get("profile")["historyId"]
        st = {"phase": "history" if ctx.mode == "incremental" and ctx.stream_cursor.get("history_id") else "list",
              "baseline": str(baseline), "history_id": ctx.stream_cursor.get("history_id")}
    phase = st["phase"]
    if phase == "history":
        params = {"startHistoryId": st["history_id"], "maxResults": 100}
        if st.get("token"):
            params["pageToken"] = st["token"]
        data = a._get("history", params)
        changed, deleted = set(), set()
        for h in data.get("history", []):
            for item in h.get("messagesDeleted", []):
                deleted.add(item["message"]["id"])
            for field in ("messagesAdded", "labelsAdded", "labelsRemoved"):
                changed.update(item["message"]["id"] for item in h.get(field, []))
        # Read current state: a deletion followed by restoration must not be replayed blindly.
        ids = sorted(changed | deleted)
        token = data.get("nextPageToken")
        committed = {"history_id": str(data.get("historyId", st["baseline"]))}
    elif phase == "list":
        params = {"maxResults": 50, "includeSpamTrash": "true"}
        if st.get("token"):
            params["pageToken"] = st["token"]
        data = a._get("messages", params)
        ids = [m["id"] for m in data.get("messages", [])]
        deleted, token = set(), data.get("nextPageToken")
        committed = {"history_id": st["baseline"]}
    else:
        ids, deleted, token, committed = st["ids"], set(), None, None
    known = recognize(ctx, kind, ids)
    for mid in ids:
        stored = known.get(mid)
        # An explicit history deletion is authoritative only if current GET also says gone.
        try:
            meta = a._get(f"messages/{mid}", {"format": "metadata", "metadataHeaders":
                ["From", "To", "Cc", "Subject", "Date", "Message-ID", "In-Reply-To"]})
        except NotFoundError:
            if mid in deleted:
                batch.records.append(tombstone(kind, mid, admitted=bool(stored and stored.admitted)))
                continue
            meta = fetch_or_gap(batch, kind, mid, stored, lambda: a._get(f"messages/{mid}", {"format": "metadata"}))
        except ScopeDeniedError:
            meta = fetch_or_gap(batch, kind, mid, stored, lambda: a._get(f"messages/{mid}", {"format": "metadata"}))
        if meta is None:
            continue
        rec = a._normalise(meta)
        eligible = qualifies(ctx, [p.email for p in rec.participants if p.email], stored)
        if eligible and content_allowed(stored):
            msg = fetch_or_gap(batch, kind, mid, stored, lambda: a._get(f"messages/{mid}", {"format": "full"}))
            if msg is None:
                continue
            rec = a._normalise(msg)
        elif not eligible:
            rec.admitted = False
        rec.authoritative = True
        rec.provider_state = {"labels": meta.get("labelIds", []), "history_id": str(meta.get("historyId", "")),
                              "state": rec.attributes.get("state")}
        if phase == "history" and stored and stored.admitted and eligible:
            # Full reads detect any actual content changes; label-only updates hash identically.
            pass
        batch.records.append(rec)
    batch.discovered = len(ids)
    if token:
        st["token"] = token
    else:
        st.pop("phase", None)
        st.pop("token", None)
    return _finish(batch, st, committed)


def _calendar_record(a, calendar_id, ev, admitted):
    rec = a._normalise(calendar_id, ev)
    rec.admitted = admitted
    rec.authoritative = True
    rec.participants_complete = not ev.get("attendeesOmitted", False)
    rec.parent_external_id = f"{calendar_id}:{ev['recurringEventId']}" if ev.get("recurringEventId") else None
    rec.attributes["recurrence"] = ev.get("recurrence", [])
    rec.attributes["organizer_self"] = bool((ev.get("organizer") or {}).get("self"))
    if ev.get("status") == "cancelled":
        rec.change_kind, rec.availability, rec.carry_content = "tombstone", "deleted_upstream", True
        rec.units = []
        # Never manufacture null/empty field values from an id-only cancellation.
        mapping = {"ical_uid": "iCalUID", "recurring_event_id": "recurringEventId", "original_start": "originalStartTime",
                   "summary": "summary", "start": "start", "end": "end", "attendees": "attendees",
                   "organizer": "organizer", "recurrence": "recurrence", "organizer_self": "organizer"}
        rec.attributes = {k: v for k, v in rec.attributes.items()
                          if k in ("calendar_id", "event_id", "status") or mapping.get(k) in ev}
        rec.participants_complete = False
    return rec


def read_calendar(a, ctx, st):
    kind, cal = "calendar_event", ctx.scope_external_id
    prefix = f"calendars/{quote(cal, safe='')}/events"
    batch = ChangeBatch([], None, False)
    if not st:
        st = {"phase": "base", "series": [], "sync_token":
              ctx.stream_cursor.get("sync_token") if ctx.mode == "incremental" else None}
    if ctx.mode == "refresh":
        event_id = ctx.target_external_id[len(cal) + 1:]
        ev = fetch_or_gap(batch, kind, ctx.target_external_id,
            recognize(ctx, kind, [ctx.target_external_id]).get(ctx.target_external_id),
            lambda: a._get(f"{prefix}/{quote(event_id, safe='')}"))
        items, data = ([ev] if ev else []), {}
    elif st["phase"] == "instances":
        series = st["series"][0]
        params = {"showDeleted": "true", "maxResults": 100,
                  "timeMax": (ctx.window_end + timedelta(days=120)).isoformat()}
        if ctx.mode != "backfill" or ctx.window_start:
            params["timeMin"] = (ctx.window_start or ctx.window_end - timedelta(days=90)).isoformat()
        if st.get("token"):
            params["pageToken"] = st["token"]
        data = a._get(f"{prefix}/{quote(series, safe='')}/instances", params)
        items = data.get("items", [])
    else:
        params = {"singleEvents": "false", "showDeleted": "true", "maxResults": 100}
        if st.get("sync_token"):
            params["syncToken"] = st["sync_token"]
        if st.get("token"):
            params["pageToken"] = st["token"]
        data = a._get(prefix, params)
        items = data.get("items", [])
    ids = [f"{cal}:{e['id']}" for e in items]
    parent_ids = [f"{cal}:{e['recurringEventId']}" for e in items if e.get("recurringEventId")]
    known = recognize(ctx, kind, ids + parent_ids)
    qualified_series = set()
    for ev in items:
        ext = f"{cal}:{ev['id']}"
        prior = known.get(ext)
        emails = [x.get("email", "") for x in ev.get("attendees", [])] + [(ev.get("organizer") or {}).get("email", "")]
        parent = known.get(f"{cal}:{ev.get('recurringEventId')}")
        eligible = qualifies(ctx, emails, prior) or bool(parent and parent.admitted) or ev.get("recurringEventId") in qualified_series
        if not eligible and ev.get("recurringEventId"):
            # Resolve explicit parent identity, never a title match.
            master = fetch_or_gap(batch, kind, f"{cal}:{ev['recurringEventId']}", parent,
                lambda: a._get(f"{prefix}/{quote(ev['recurringEventId'], safe='')}"))
            if master:
                me = [x.get("email", "") for x in master.get("attendees", [])]
                eligible = qualifies(ctx, me, parent)
                if eligible:
                    batch.records.append(_calendar_record(a, cal, master, True))
        if not eligible and ev.get("status") != "cancelled":
            # Pointer only (who, when, title; no description), so a contact approved later attaches it (P-02).
            batch.excluded += 1
            rec = _calendar_record(a, cal, ev, False)
            rec.units, rec.content_state = [], "metadata_only"
            batch.records.append(rec)
            continue
        rec = _calendar_record(a, cal, ev, eligible)
        if not content_allowed(prior):
            rec.units = []
        batch.records.append(rec)
        if ev.get("recurrence") and eligible:
            qualified_series.add(ev["id"])
            if ev.get("status") != "cancelled" and ev["id"] not in st["series"]:
                st["series"].append(ev["id"])
    batch.discovered = len(items)
    token = data.get("nextPageToken")
    if data.get("nextSyncToken"):
        st["next_sync_token"] = data["nextSyncToken"]
    if ctx.mode == "refresh":
        st.pop("phase", None)
    elif token:
        st["token"] = token
    else:
        st.pop("token", None)
        if st["phase"] == "instances":
            st["series"].pop(0)
        if st["series"]:
            st["phase"] = "instances"
        else:
            st.pop("phase", None)
    return _finish(batch, st, {"sync_token": st.get("next_sync_token") or st.get("sync_token")})


def team_meeting(ctx, m) -> bool:
    """WIA's internal team meeting (every invitee is WIA's, title matches INTERNAL_MEETING_TITLE_PATTERN): read in
    full, linked to no client, so the team-meeting digest can attribute its actions to clients."""
    pattern = getattr(ctx.settings, "internal_meeting_title_pattern", None)
    emails = [(i.get("email") or "").lower() for i in m.get("calendar_invitees", [])]
    return bool(pattern and emails and ctx.internal_emails and all(e in ctx.internal_emails for e in emails)
                and re.search(pattern, m.get("title") or "", re.IGNORECASE))


def read_fathom(a, ctx, st):
    kind = "fathom_recording"
    batch = ChangeBatch([], None, False)
    params = {"include_action_items": "true"}
    if st.get("token"):
        params["cursor"] = st["token"]
    # Refresh must discover current metadata too; recording URLs are not API IDs.
    data = a.http.get_json("meetings", params)
    items = data.get("items", [])
    if ctx.mode == "refresh":
        items = [m for m in items if str(m["recording_id"]) == ctx.target_external_id]
    known = recognize(ctx, kind, [str(m["recording_id"]) for m in items])
    for m in items:
        rid = str(m["recording_id"])
        stored = known.get(rid)
        eligible = qualifies(ctx, [i.get("email", "") for i in m.get("calendar_invitees", [])], stored) or team_meeting(ctx, m)
        if not eligible:
            batch.excluded += 1
            batch.records.append(a._pointer(m))
            continue
        if content_allowed(stored):
            rec = fetch_or_gap(batch, kind, rid, stored, lambda: a._normalise(m))
        else:
            rec = NormalisedRecord(kind, rid, None, None, m.get("url"),
                {"title": m.get("title"), "created_at": m.get("created_at")}, [], content_state="metadata_only",
                participants_complete=False, change_kind="patch", carry_content=True)
        if rec:
            rec.authoritative = True
            if rec.content_state == "content_pending" and stored:
                rec.change_kind, rec.carry_content, rec.participants_complete = "patch", True, False
            batch.records.append(rec)
    batch.discovered = len(items)
    token = data.get("next_cursor")
    if token and token == st.get("token"):
        raise IntakeError("fathom: repeated pagination cursor")
    if ctx.mode == "refresh" and items:
        token = None
    if token:
        st.update(phase="list", token=token)
    else:
        st.pop("phase", None)
        if ctx.mode == "refresh" and not items:
            stored = recognize(ctx, kind, [ctx.target_external_id]).get(ctx.target_external_id)
            batch.gaps.append(Gap(ctx.target_external_id, "not_found"))
            if stored:
                batch.records.append(unavailable(kind, ctx.target_external_id, stored.admitted))
    return _finish(batch, st, {})


def read_slack(a, ctx, st):
    kind, channel = "slack_message", ctx.scope_external_id
    batch = ChangeBatch([], None, False)
    if ctx.mode == "refresh":
        ts = ctx.target_external_id[len(channel) + 1:]
        prior = recognize(ctx, kind, [ctx.target_external_id]).get(ctx.target_external_id)
        thread = prior.attributes.get("thread_ts") if prior else None
        if thread and thread != ts:
            items = [m for m in a._replies(channel, thread) if m["ts"] == ts]
        else:
            items = a._call("conversations.history", channel=channel, oldest=ts, latest=ts,
                            inclusive="true", limit=1).get("messages", [])
        data = {}
    else:
        params = {"channel": channel, "limit": 100, "latest": f"{ctx.window_end.timestamp():.6f}", "inclusive": "true"}
        if ctx.mode == "incremental":
            params["oldest"] = f"{(ctx.window_end - timedelta(days=7)).timestamp():.6f}"
        elif ctx.window_start:
            params["oldest"] = f"{ctx.window_start.timestamp():.6f}"
        if st.get("token"):
            params["cursor"] = st["token"]
        data = a._call("conversations.history", **params)
        items = []
        for root in data.get("messages", []):
            items.extend(a._replies(channel, root["ts"]) if root.get("reply_count") else [root])
    ids = [f"{channel}:{m.get('deleted_ts') or m['ts']}" for m in items]
    known = recognize(ctx, kind, ids)
    for m, ext in zip(items, ids):
        prior = known.get(ext)
        if m.get("subtype") == "message_deleted":
            batch.records.append(tombstone(kind, ext, admitted=bool(prior and prior.admitted)))
        else:
            rec = a._normalise(channel, m)
            if qualifies(ctx, [p.email for p in rec.participants if p.email], prior):
                rec.authoritative = True
                if not content_allowed(prior):
                    rec.units = []
                batch.records.append(rec)
            else:
                batch.excluded += 1
    if ctx.mode == "refresh" and not items:
        batch.records.append(unavailable(kind, ctx.target_external_id))
        batch.gaps.append(Gap(ctx.target_external_id, "not_found"))
    batch.discovered = len(items)
    token = (data.get("response_metadata") or {}).get("next_cursor")
    if token:
        if token == st.get("token"):
            raise IntakeError("slack: repeated pagination cursor")
        st.update(phase="list", token=token)
    else:
        st.pop("phase", None)
    return _finish(batch, st, {"watermark": ctx.window_end.isoformat()})


def read_clickup(a, ctx, st):
    kind = "clickup_task"
    batch = ChangeBatch([], None, False)
    if ctx.mode == "refresh":
        known = recognize(ctx, kind, [ctx.target_external_id])
        task = fetch_or_gap(batch, kind, ctx.target_external_id, known.get(ctx.target_external_id),
                           lambda: a.http.get_json(f"task/{ctx.target_external_id}"))
        tasks, last = ([task] if task else []), True
    else:
        params = {"include_closed": "true", "subtasks": "true", "include_markdown_description": "true",
                  "page": st.get("page", 0), "order_by": "updated", "reverse": "false",
                  "date_updated_lt": int(ctx.window_end.timestamp() * 1000) + 1}
        if ctx.mode == "incremental":
            lo = ctx.stream_cursor.get("watermark")
            lo = datetime.fromisoformat(lo) if lo else ctx.window_end - timedelta(days=7)
            params["date_updated_gt"] = int((lo - timedelta(minutes=5)).timestamp() * 1000)
        elif ctx.window_start:
            params["date_updated_gt"] = int(ctx.window_start.timestamp() * 1000)
        data = a.http.get_json(f"list/{ctx.scope_external_id}/task", params)
        tasks = data.get("tasks", [])
        last = data.get("last_page", len(tasks) < 100)
        known = recognize(ctx, kind, [str(t["id"]) for t in tasks])
    for task in tasks:
        ext = str(task["id"])
        prior = known.get(ext)
        # GET current avoids a stale list snapshot overwriting a newer task read.
        current = fetch_or_gap(batch, kind, ext, prior, lambda: a.http.get_json(f"task/{ext}"))
        if not current:
            continue
        ids = {str((current.get("list") or {}).get("id")), *[str(x.get("id")) for x in current.get("locations", [])]}
        paused = False
        with transaction() as s:
            if ctx.connector_account_id:
                listed = s.execute(select(SourceScope).where(SourceScope.connector_account_id == ctx.connector_account_id,
                    SourceScope.state == "approved", SourceScope.external_id.in_(ids))).scalars().all()
                scopes = [x.id for x in listed if is_live(s, x)]
                paused = bool(listed) and not scopes
            else:
                scopes = [ctx.scope_id]
        if paused:
            batch.excluded += 1  # archived client's list: syncing paused, the stored task stays as it is
            continue
        if not scopes:
            if prior:
                batch.records.append(tombstone(kind, ext, availability="out_of_scope", admitted=prior.admitted))
            batch.excluded += 1
            continue
        comments = fetch_or_gap(batch, kind, ext, prior, lambda: a._comments(ext))
        if comments is None:
            continue
        rec = a._normalise(current, comments)
        rec.authoritative = True
        if not content_allowed(prior):
            rec.units = []
        batch.records.append(rec)
        batch.memberships.append({"external_id": ext, "kind": kind, "scope_ids": list(map(str, scopes))})
    batch.discovered = len(tasks)
    if last:
        st.pop("phase", None)
    else:
        st.update(phase="list", page=st.get("page", 0) + 1)
    return _finish(batch, st, {"watermark": ctx.window_end.isoformat()})


def _folders(ctx):
    with transaction() as s:
        return [(str(x.id), x.external_id) for x in s.execute(select(SourceScope).where(
            SourceScope.connector_account_id == ctx.connector_account_id, live_scope())).scalars()]


def read_drive(a, ctx, st):
    from backend.services.intake.adapters.drive import COMMON, FOLDER
    kind = "drive_file"
    batch = ChangeBatch([], None, False)
    folders = _folders(ctx)
    roots = {fid: sid for sid, fid in folders}
    feeds = dict(st.get("feeds") or ctx.stream_cursor.get("feeds") or {})
    full = ctx.mode in ("backfill", "reconcile") or not feeds
    if not st:
        # A separate changes cursor for each approved shared drive and the user corpus.
        drive_ids = {"user"}
        for _, fid in folders:
            root = a._get(f"drive/v3/files/{fid}", {"fields": "id,driveId", "supportsAllDrives": "true"})
            drive_ids.add(root.get("driveId") or "user")
        if full:
            feeds = {d: a._get("drive/v3/changes/startPageToken", {"supportsAllDrives": "true",
                **({"driveId": d} if d != "user" else {})})["startPageToken"] for d in sorted(drive_ids)}
        st = {"phase": "walk" if full else "changes", "feeds": feeds,
              "queue": [[fid, []] for _, fid in folders] if full else [], "feed_queue": sorted(feeds)}
    if ctx.mode == "refresh":
        data = a._get(f"drive/v3/files/{ctx.target_external_id}", {"fields":
            "id,name,mimeType,parents,modifiedTime,createdTime,size,webViewLink,version,trashed", "supportsAllDrives": "true"})
        files, token = [data], None
    elif st["phase"] == "walk":
        folder, path = st["queue"][0]
        data = a._list(f"'{folder}' in parents and trashed=false", st.get("token"), 50)
        files, token = data.get("files", []), data.get("nextPageToken")
    else:
        feed = st["feed_queue"][0]
        params = {"pageToken": st.get("token") or feeds[feed], "pageSize": 100,
                  "includeRemoved": "true", "includeCorpusRemovals": "true", **COMMON}
        if feed != "user":
            params["driveId"] = feed
        data = a._get("drive/v3/changes", params)
        files = []
        for change in data.get("changes", []):
            if change.get("fileId"):
                f = dict(change.get("file") or {"id": change["fileId"]})
                f["_removed"] = change.get("removed", False)
                files.append(f)
        token = data.get("nextPageToken")
        if data.get("newStartPageToken"):
            feeds[feed] = data["newStartPageToken"]
    known = recognize(ctx, kind, [f["id"] for f in files])
    cache = {}
    with transaction() as s:
        for node in s.execute(select(DriveNode).where(DriveNode.connector_account_id == ctx.connector_account_id)).scalars():
            cache[node.external_id] = {"id": node.external_id, "parents": node.parents, "name": node.name}
    for f in files:
        cache[f["id"]] = f
    def memberships(fid, visiting=None):
        visiting = set(visiting or ())
        if fid in roots:
            return {roots[fid]}, []
        if fid in visiting:
            raise IntakeError("drive: cyclic folder ancestry")
        visiting.add(fid)
        f = cache.get(fid)
        if f is None:
            f = a._get(f"drive/v3/files/{fid}", {"fields": "id,name,parents,mimeType", "supportsAllDrives": "true"})
            cache[fid] = f
        found, names = set(), []
        for parent in f.get("parents", []):
            scope_ids, path = memberships(parent, visiting)
            found.update(scope_ids)
            if scope_ids:
                names = path + [cache.get(parent, {}).get("name", "")]
        return found, names
    for f in files:
        ext, prior = f["id"], known.get(f["id"])
        if f.get("_removed") or f.get("trashed"):
            if prior:
                batch.records.append(tombstone(kind, ext, admitted=prior.admitted) if f.get("trashed") else unavailable(kind, ext, prior.admitted))
                if f.get("_removed") and not f.get("trashed"):
                    batch.gaps.append(Gap(ext, "scope_denied"))
            continue
        try:
            scope_ids, path = memberships(ext)
        except (NotFoundError, ScopeDeniedError) as exc:
            batch.gaps.append(Gap(ext, exc.error_class))
            if prior:
                batch.records.append(unavailable(kind, ext, prior.admitted))
            continue
        batch.memberships.append({"external_id": ext, "kind": kind, "scope_ids": sorted(scope_ids),
                                  "node": {"parents": f.get("parents", []), "name": f.get("name", ""),
                                           "is_folder": f.get("mimeType") == FOLDER}})
        if f.get("mimeType") == FOLDER:
            # A folder move changes descendant eligibility even when child files have no change event.
            if scope_ids and ext not in [x[0] for x in st["queue"]]:
                st["queue"].append([ext, path + [f.get("name", "")]])
            continue
        if not scope_ids:
            if prior:
                batch.records.append(tombstone(kind, ext, availability="out_of_scope", admitted=prior.admitted))
            batch.excluded += 1
            continue
        rec = fetch_or_gap(batch, kind, ext, prior, lambda: a._normalise(f, path))
        if rec:
            rec.authoritative = True
            if not content_allowed(prior):
                rec.units = []
            batch.records.append(rec)
    batch.discovered = len(files)
    if ctx.mode == "refresh":
        st.pop("phase", None)
    elif token:
        st["token"] = token
    else:
        st.pop("token", None)
        if st["phase"] == "walk":
            st["queue"].pop(0)
        else:
            st["feed_queue"].pop(0)
        if st["queue"]:
            st["phase"] = "walk"
        elif st["feed_queue"] and not full:
            st["phase"] = "changes"
        else:
            st.pop("phase", None)
    st["feeds"] = feeds
    return _finish(batch, st, {"feeds": feeds})


READERS = {"gmail": read_gmail, "calendar": read_calendar, "fathom": read_fathom,
           "slack": read_slack, "clickup": read_clickup, "drive": read_drive}
