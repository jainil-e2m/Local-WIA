"""Small, deterministic Slack messages. No model calls, credentials or full piece copy."""
from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo

LABELS = {"email": "Email", "carousel": "Carousel", "reel_1": "Reel 1", "reel_2": "Reel 2", "reel_3": "Reel 3"}
DESTINATIONS = {"email": "email", "carousel": "social", "reel": "social"}


def instant(value):
    value = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("invalid_schedule_instant")
    return value


def public_origin(value: str, *, allow_loopback: bool = False) -> str:
    try:
        parsed = urlsplit(value)
        local = allow_loopback and parsed.hostname in ("localhost", "127.0.0.1", "::1")
        if local:
            if (parsed.scheme not in ("http", "https") or parsed.username or parsed.password
                    or parsed.path not in ("", "/") or parsed.query or parsed.fragment or re.search(r"[\s\\<>|]", value)):
                raise ValueError
            if parsed.port is not None and not 1 <= parsed.port <= 65535:
                raise ValueError
            return f"{parsed.scheme}://{parsed.netloc}"
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or re.search(r"[\s\\<>|]", value) or parsed.port not in (None, 443)):
            raise ValueError
        host = parsed.hostname.lower()
        if "." not in host or host.endswith((".internal", ".local")):
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("invalid_public_app_url") from None
    return f"https://{parsed.netloc}".rstrip("/")


def title(asset: dict) -> str:
    copy = (asset.get("content_body") or {}).get("content") or (asset.get("content_body") or {}).get("document") or {}
    subjects = copy.get("subject_options") or []
    value = (subjects[0] if subjects and isinstance(subjects[0], str) else None) if asset["asset_type"] == "email" else copy.get("title")
    value = value if isinstance(value, str) and value.strip() else LABELS.get(asset["slot_key"], asset["asset_type"])
    return re.sub(r"\s+", " ", value).strip()[:200]


def escaped(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "｜")


def when(value, zone: str) -> str:
    local = instant(value).astimezone(ZoneInfo(zone))
    offset = local.strftime("%z")
    return f"{local:%a %d %b %Y} · {local:%H:%M} {local.tzname()} (UTC{offset[:3]}:{offset[3:]})"


def message(payload: dict, pieces: list[dict], origin: str, zone: str, *, allow_loopback: bool = False) -> dict:
    origin = public_origin(origin, allow_loopback=allow_loopback)
    count = len(pieces)
    noun = "email" if payload["destination"] == "email" else "social content piece"
    noun += "s" if count != 1 else ""
    changed = [bool(p.get("previous_time")) for p in pieces]
    if all(changed):
        ending = "time is" if count == 1 else "times are"
        opening = f"Content Atelier has updated the publishing schedule for {count} {noun}. The updated {ending} below."
    elif any(changed):
        opening = f"Content Atelier has publishing schedule updates for {count} {noun}. The times are below."
    else:
        quantity = f"a new {noun}" if count == 1 else f"{count} new {noun}"
        ending = "time" if count == 1 else "times"
        opening = f"Content Atelier has {quantity} scheduled for publishing at the {ending} below."
    blocks = [{"type": "section", "text": {"type": "plain_text", "text": opening}}]
    fallback = [opening]
    for piece in pieces:
        key = piece["slot_key"]
        if key not in LABELS:
            raise ValueError("unknown_piece_key")
        link = f"{origin}/studio/packs/{quote(payload['pack_id'], safe='')}?piece={quote(key, safe='')}"
        label = f"{LABELS[key]} · {piece['title']}"
        at = when(piece["scheduled_for"], zone)
        if piece.get("previous_time"):
            at = f"{when(piece['previous_time'], zone)} → {at}"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "verbatim": True,
                       "text": f"<{link}|{escaped(label)}>\n{at}"}})
        fallback.append(f"{label}\n{at}\n{link}")
    return {"text": "\n\n".join(fallback), "blocks": blocks, "mrkdwn": False, "parse": "none",
            "link_names": False, "unfurl_links": False, "unfurl_media": False}
