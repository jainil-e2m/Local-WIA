"""Provider-independent source views with exact offsets and extraction locators."""
import hashlib
from .contracts import slack_time
from ..store import canonical_hash


def record(source_id, title, kind, entries, *, url=None, occurred_at=None, content_hash=None):
    text, passages, cursor = [], [], 0
    for entry in entries:
        body = entry['text']
        if not body.strip():
            continue
        ordinal = len(passages)
        passages.append({'passage_id': f'{source_id}:span:{ordinal}', 'ordinal': ordinal,
                         'start': cursor, 'end': cursor + len(body), 'kind': kind,
                         'speaker': entry.get('speaker'), 'start_ms': entry.get('start_ms'),
                         'end_ms': entry.get('end_ms'), 'locator': entry.get('locator', {}),
                         'extraction_method': entry.get('extraction_method', 'provider')})
        text.append(body)
        cursor += len(body) + 1
    original = '\n'.join(text)
    digest = content_hash or canonical_hash(entries)
    return {'transcript_id': 'live_' + canonical_hash([source_id, digest])[:32], 'week_id': None,
            'source_type': kind, 'upstream_id': source_id, 'title': title,
            'source_url': url, 'occurred_at': occurred_at, 'original_text': original,
            'content_hash': digest, 'passage_map': passages,
            'source_metadata': {'normalized_sha256': hashlib.sha256(original.encode()).hexdigest()},
            'use_restrictions': {'research_allowed': True, 'public_use': False, 'attribution_verified': False},
            'processing_status': 'pending'}


def fathom(metadata, payload, source_id, digest):
    from ..fathom_sources import timestamp_ms
    entries, previous = [], -1
    for i, segment in enumerate(payload.get('transcript') or []):
        stamp = timestamp_ms(segment.get('timestamp'))
        if stamp < previous or not isinstance(segment.get('text'), str) or not segment['text'].strip():
            raise ValueError('Invalid Fathom transcript segment ordering or text')
        previous = stamp
        speaker = (segment.get('speaker') or {}).get('display_name')
        entries.append({'text': f'{speaker}: {segment["text"]}' if speaker else segment['text'],
                        'speaker': speaker, 'start_ms': stamp,
                        'locator': {'segment': i, 'timestamp': segment['timestamp']}})
    if not entries:
        raise ValueError('Fathom transcript is not available yet')
    return record(source_id, metadata.get('title') or metadata.get('meeting_title') or 'Fathom recording',
                  'fathom', entries, url=metadata.get('share_url') or metadata.get('url'),
                  occurred_at=metadata.get('recording_start_time'), content_hash=digest)


def slack(message, channel, source_id, digest):
    entries = [] if message.get('deleted') else [{'text': message.get('text', ''),
        'speaker': message.get('user'), 'locator': {'channel': channel, 'ts': message['ts'],
        'thread_ts': message.get('thread_ts')}, 'extraction_method': 'provider'}]
    return record(source_id, f'Slack #{channel} · {message["ts"]}', 'slack', entries,
                  url=message.get('permalink'), occurred_at=slack_time(message['ts']), content_hash=digest)
