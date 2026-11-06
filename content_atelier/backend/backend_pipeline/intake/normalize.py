"""Provider-independent source views for live intake. The builders live in normalise/sources.py (plan 1.B14); this module
keeps the names the intake code already calls."""
from ..normalise.sources import LIVE_RESTRICTIONS, entries_document, fathom_document, slack_time


def record(source_id, title, kind, entries, *, url=None, occurred_at=None, content_hash=None):
    """A document from entries that already hold their text (attachments and extracted files)."""
    return entries_document(source_id, title, kind, entries, url=url, occurred_at=occurred_at, content_hash=content_hash)


def fathom(metadata, payload, source_id, digest):
    """A Fathom recording from the API. The recording, not the intake source, is the document's identity, so the same
    call from the API and from native JSON gives the same passages, identifiers and speaker emails."""
    return fathom_document(metadata, payload, digest, use_restrictions=LIVE_RESTRICTIONS)


def slack(message, channel, source_id, digest):
    """One delivered Slack message as a document (live intake keeps one source per message; threads are grouped by
    `normalise.sources.slack_threads`, which the export import uses)."""
    entries = [] if message.get('deleted') else [{'text': message.get('text', ''), 'speaker': message.get('user'),
        'locator': {'channel': channel, 'ts': message['ts'], 'thread_ts': message.get('thread_ts')}, 'extraction_method': 'provider'}]
    return entries_document(source_id, f'Slack #{channel} · {message["ts"]}', 'slack', entries,
                            url=message.get('permalink'), occurred_at=slack_time(message['ts']), content_hash=digest)
