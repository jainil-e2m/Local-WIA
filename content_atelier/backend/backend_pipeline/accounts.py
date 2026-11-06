"""Account memory (plan 3.B17, D25): what happened with a client account, from WIA's own records, never from a model.

A story card about a client is written from one call. The call is rarely the end of the story: a recommendation is built a
month later, a result is measured, or the account needs a look. Week 2's three account stories all had documented sequels,
and the 13 October packs still ended on "ideas to discuss and test" about changes WIA had already built; a public CONVERT
story was also proposed about an account that had, internally, dipped. So each account gets a dated timeline built from the
records D25 allows (every WIA record about the client):

* **its calls**: the verified scenes of the account's documents, each a dated entry of what was recommended, built,
  decided, measured or said, or what was left open, with the scene and the call as its source;
* **internal meetings** (team practice, D24) that mention the account: shown to the reviewer as cautions and as WIA's
  own work, never given to a writer as the client's evidence;
* **published content** that names the account, and **WIA's sent emails and recaps** in the context store.

A date is the call's occurrence date, or the week its source folder names when that is all the evidence says (1.B11),
shown as such. Nothing here calls a model: the timeline is a query, so it is current whenever it is read.

`for_card` is what Gate 1 and Gate 2 show beside a client story card: the account, its naming, its current state and what
happened after the card's call. `next_evidence` gives the brief writer "what happened next" as evidence items the claim
ledger can bind, each flagged for the approver's permission before publishing (it is a later record, not the card's call).
"""
from __future__ import annotations

import re
from datetime import UTC, datetime

# The scene types and WIA moves an entry is filed under, in the order a reader thinks of an account's story.
KINDS = ("recommended", "built", "decided", "measured", "said", "open", "published", "sent", "internal")
MOVE_KINDS = {"recommended": "recommended", "built": "built", "decided": "decided", "reviewed": "built"}
TYPE_KINDS = {"result": "measured", "data_point": "measured", "decision": "decided", "counter_expected_decision": "decided",
              "testimonial": "said", "human_line": "said"}
LATEST = 4  # entries shown as the account's current state
MOVE = re.compile(r"^(?P<speaker>[^|:]+?) (?P<move>asked|noticed|recommended|decided|explained|reviewed|built): ", re.I)


def _when(row: dict) -> tuple[datetime | None, str]:
    """A document's date and how exact it is: a day, a week from its folder, or none."""
    if row.get("occurred_at"):
        return row["occurred_at"], "day"
    window = (row.get("date_evidence") or {}).get("window") or {}
    if window.get("start"):
        # The folder's own first day (its window starts at midnight in the folder's time zone): "week of 31 August", not
        # the UTC instant's date, which falls on the day before.
        return datetime.fromisoformat(window["start"]), "week"
    return None, "undated"


def _kind(body: dict) -> str | None:
    """What a scene records for the account's story, or None for a scene that adds nothing to it (a question, small talk)."""
    moves = [m.group("move").lower() for part in (body.get("proposition") or "").split(" | ") if (m := MOVE.match(part.strip()))]
    for move in ("built", "decided", "recommended", "reviewed"):
        if move in moves:
            return MOVE_KINDS[move]
    if body.get("moment_type") in TYPE_KINDS:
        return TYPE_KINDS[body["moment_type"]]
    if "| Left open: " in (body.get("proposition") or "") or (body.get("proposition") or "").startswith("Left open: "):
        return "open"
    return None


def _spellings(account: dict) -> list[str]:
    """How a record may refer to the account: its name and aliases, and its people's names and aliases (an internal meeting
    says "Allie asked for a new video", not the venue's name). Only capitalised or multi-word spellings, so a lower-case
    transcript label is never taken for a mention."""
    names = [account["name"], *(account.get("aliases") or []), *(account.get("people") or [])]
    return [s for s in dict.fromkeys(names) if s and len(s) >= 4 and (" " in s or s[0].isupper())]


def _patterns(account: dict) -> list[re.Pattern]:
    """One search per case rule: a multi-word spelling matches in any case, a single word only as written."""
    spellings = _spellings(account)
    groups = (([s for s in spellings if " " not in s], 0), ([s for s in spellings if " " in s], re.I))
    return [re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(map(re.escape, group)) + r")(?![A-Za-z0-9])", flags) for group, flags in groups if group]


def _mentions(account: dict, text: str) -> bool:
    return any(p.search(text or "") for p in account["patterns"])


def _entry(when, precision, kind, text, source) -> dict:
    return {"date": when.date().isoformat() if when else None, "precision": precision, "kind": kind, "text": text.strip(),
            "source": source}


def _shared_records(conn) -> dict:
    """What every account's timeline scans: the accounts, the internal meetings' scenes, published content and the context
    store. A scene's text carries its anchor passages only, cut from each transcript read once: reading the transcript with
    every scene took 41 MB a timeline on production, and a week's review builds one for each card's account."""
    people = {}
    for r in conn.execute("SELECT client_id,name,aliases FROM people").fetchall():
        people.setdefault(r["client_id"], []).extend([r["name"], *(r["aliases"] or [])])
    clients = {}
    for c in conn.execute("SELECT client_id,name,aliases FROM clients").fetchall():
        c["people"] = people.get(c["client_id"], [])
        c["patterns"] = _patterns(c)
        clients[c["client_id"]] = c
    internal = conn.execute("""SELECT m.moment_id,m.moment_body,m.evidence_refs,t.transcript_id,t.title,t.occurred_at,t.date_evidence
            FROM key_moments m JOIN transcripts t ON t.transcript_id=m.document_id
            WHERE m.is_current AND m.quote_verified AND m.evidence_class='team_practice' AND t.included""").fetchall()
    originals = {r["transcript_id"]: r["original_text"] for r in conn.execute(
        "SELECT transcript_id,original_text FROM transcripts WHERE transcript_id=ANY(%s)",
        (sorted({r["transcript_id"] for r in internal}),)).fetchall()}
    for row in internal:
        body, original = row["moment_body"], originals[row["transcript_id"]]
        # Scene profile v4 keeps a client's name out of an internal scene's record (D24), so the scene's anchor passages, the
        # transcript's words where it happens, say which account it is about (its wider context runs into other accounts).
        passages = " ".join(original[r["start"]:r["end"]] for r in row["evidence_refs"] or []
                            if r.get("transcript_id") == row["transcript_id"] and "anchor" in (r.get("roles") or []))
        row["text"] = " ".join([*(str(body.get(k) or "") for k in ("quote", "proposition", "context_summary")), passages])
    return {"clients": clients, "internal": internal, "timelines": {},
            "published": conn.execute("""SELECT content_id,published_on,channel,title,text FROM published_content
                WHERE status IN ('confirmed','unconfirmed')""").fetchall(),
            "kit": conn.execute("""SELECT item_id,key,kind,text,valid_from,source_ref FROM brand_kit_items
                WHERE status IN ('confirmed','candidate') AND kind IN ('exemplar','result','performance_note','campaign')""").fetchall()}


def timeline(conn, client_id: str, shared: dict | None = None) -> list[dict]:
    """Every dated entry for one account, oldest first (undated entries last). A read showing several cards passes one
    `shared` dict for the whole read, so the records are read once and each account's timeline built once."""
    shared = {} if shared is None else shared
    if not shared:
        shared.update(_shared_records(conn))
    if client_id in shared["timelines"]:
        return shared["timelines"][client_id]
    account = shared["clients"].get(client_id)
    if account is None:
        raise LookupError("Account not found")
    others = [c for c in shared["clients"].values() if c["client_id"] != client_id]
    entries = []
    for row in conn.execute("""SELECT m.moment_id,m.moment_body,m.evidence_class,t.transcript_id,t.title,t.occurred_at,t.date_evidence
            FROM key_moments m JOIN transcripts t ON t.transcript_id=m.document_id
            WHERE m.is_current AND m.quote_verified AND t.included AND t.canonical_document_id IS NULL
              AND m.evidence_class='call' AND (t.client_id=%s OR m.client_id=%s)
            ORDER BY t.occurred_at NULLS LAST,m.moment_id""", (client_id, client_id)).fetchall():
        kind = _kind(row["moment_body"])
        if kind is None:
            continue
        when, precision = _when(row)
        entries.append(_entry(when, precision, kind, row["moment_body"].get("context_summary") or row["moment_body"].get("proposition") or "",
                              {"kind": "call", "transcript_id": row["transcript_id"], "title": row["title"], "moment_id": row["moment_id"]}))
    # Internal meetings that discuss the account: the reviewer's cautions and WIA's own work, never the client's evidence.
    for row in shared["internal"]:
        body, text = row["moment_body"], row["text"]
        # An account review runs through several accounts in one turn: a scene is this account's only when it names no other.
        if not _mentions(account, text) or any(_mentions(other, text) for other in others):
            continue
        when, precision = _when(row)
        entries.append(_entry(when, precision, "internal", body.get("context_summary") or body.get("proposition") or "",
                              {"kind": "internal_meeting", "transcript_id": row["transcript_id"], "title": row["title"],
                               "moment_id": row["moment_id"], "built": _kind(body) in ("built", "decided", "recommended"),
                               "move": _kind(body)}))
    for row in shared["published"]:
        if _mentions(account, f"{row['title']}\n{row['text'] or ''}"):
            when = datetime(row["published_on"].year, row["published_on"].month, row["published_on"].day, 12, tzinfo=UTC) \
                if row["published_on"] else None
            entries.append(_entry(when, "day" if when else "undated", "published", f"{row['channel']}: {row['title']}",
                                  {"kind": "published", "content_id": row["content_id"]}))
    for row in shared["kit"]:
        if _mentions(account, row["text"]):
            when = datetime(row["valid_from"].year, row["valid_from"].month, row["valid_from"].day, 12, tzinfo=UTC) \
                if row["valid_from"] else None
            entries.append(_entry(when, "day" if when else "undated", "sent" if row["kind"] == "exemplar" else "measured",
                                  row["text"][:400], {"kind": "context_store", "item_id": row["item_id"], "key": row["key"]}))
    entries.sort(key=lambda e: (e["date"] is None, e["date"] or "", KINDS.index(e["kind"])))
    shared["timelines"][client_id] = entries
    return entries


def _naming(account: dict) -> str:
    from .identities import naming_of
    return naming_of(account["consent"], bool(account.get("do_not_name")))


def state(conn, client_id: str, entries: list[dict] | None = None) -> dict:
    """The account's current state: its status and naming, how many calls the records hold and the last, the latest
    entries, and the internal cautions since its last call."""
    account = conn.execute("SELECT * FROM clients WHERE client_id=%s", (client_id,)).fetchone()
    entries = timeline(conn, client_id) if entries is None else entries
    calls = {e["source"]["transcript_id"]: e for e in entries if e["source"]["kind"] == "call"}
    dated = [e for e in entries if e["date"]]
    last_call = max((e for e in calls.values() if e["date"]), key=lambda e: e["date"], default=None)
    return {"client_id": client_id, "name": account["name"], "business": account.get("business"), "status": account["status"],
            "naming": _naming(account), "calls": len(calls),
            "last_call": {"date": last_call["date"], "precision": last_call["precision"], "title": last_call["source"]["title"]}
            if last_call else None,
            "latest": [e for e in dated if e["kind"] != "internal"][-LATEST:],
            "cautions": [e for e in dated if e["kind"] == "internal" and (not last_call or e["date"] >= last_call["date"])][-LATEST:]}


def accounts_of(conn, moment_ids) -> list[tuple[str, str | None]]:
    """(account, the latest date of the card's own scenes from that account) for the accounts a set of scenes involves."""
    rows = conn.execute("""SELECT COALESCE(m.client_id,t.client_id) AS client_id,max(COALESCE(to_char(t.occurred_at AT TIME ZONE 'UTC',
            'YYYY-MM-DD'),left(t.date_evidence->'window'->>'start',10))) AS at
        FROM key_moments m JOIN transcripts t ON t.transcript_id=m.document_id
        WHERE m.moment_id=ANY(%s) AND COALESCE(m.client_id,t.client_id) IS NOT NULL GROUP BY 1 ORDER BY 1""",
                        (sorted(set(moment_ids or [])),)).fetchall()
    return [(r["client_id"], r["at"]) for r in rows]


def for_card(conn, moment_ids, shared: dict | None = None) -> list[dict]:
    """Beside a client story card at Gate 1 and Gate 2: each account the card's scenes come from, with its current state and
    what the records say happened after the card's call."""
    shared = {} if shared is None else shared
    out = []
    for client_id, since in accounts_of(conn, moment_ids):
        entries = timeline(conn, client_id, shared)
        later = [e for e in entries if since and e["date"] and e["date"] > since]
        out.append({**state(conn, client_id, entries), "card_call_date": since,
                    "what_happened_next": [e for e in later if e["kind"] != "internal"],
                    "internal_since": [e for e in later if e["kind"] == "internal"]})
    return out


# What the writer most needs from a later record, first: what was built or measured, then decided or recommended.
NEXT_PRIORITY = ("built", "measured", "decided", "recommended", "said", "open", "internal")


def next_evidence(conn, moment_ids, *, limit: int = 8) -> list[dict]:
    """"What happened next" for the brief writer: the later scenes of the card's accounts (their own calls, and what WIA built
    or decided in an internal meeting about them), newest last, as moment IDs with their account and date. The caller turns
    them into evidence items (briefs/inputs.py), so the claim ledger can bind a line about them and every consent and
    team-practice check applies to them as to the card's own evidence."""
    picked = []
    shared = {}
    for client_id, since in accounts_of(conn, moment_ids):
        if not since:
            continue
        for e in timeline(conn, client_id, shared):
            if not e["date"] or e["date"] <= since or e["source"]["kind"] not in ("call", "internal_meeting"):
                continue
            if e["source"]["kind"] == "internal_meeting" and not e["source"].get("built"):
                continue  # an internal remark about the account is a caution for the reviewer, not material for copy
            internal = e["source"]["kind"] == "internal_meeting"
            # An internal meeting's record of WIA's own work ranks by what it records (built, decided), like a call's.
            picked.append({"moment_id": e["source"]["moment_id"], "client_id": client_id, "date": e["date"],
                           "kind": e["source"].get("move") or "internal" if internal else e["kind"],
                           "precision": e["precision"], "evidence_class": "team_practice" if internal else "call"})
    seen, unique = set(moment_ids or []), []
    for p in picked:
        if p["moment_id"] not in seen:
            seen.add(p["moment_id"])
            unique.append(p)
    # The most telling later records (what was built or measured before what was said; the newest first within a kind, the
    # sort being stable), then back in date order for the writer.
    def rank(p):
        return NEXT_PRIORITY.index(p["kind"]) if p["kind"] in NEXT_PRIORITY else len(NEXT_PRIORITY)
    kept = sorted(sorted(unique, key=lambda p: p["date"], reverse=True), key=rank)[:limit]
    return sorted(kept, key=lambda p: (p["date"], p["moment_id"]))
