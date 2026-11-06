from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
import httpx
from psycopg.types.json import Jsonb

from .normalize import fathom as normalize
from .repository import lock


class PendingTranscript(Exception):
    pass


class FathomClient:
    def __init__(self, settings, transport=None):
        self.client = httpx.Client(base_url=settings.fathom_base_url + '/',
            headers={'X-Api-Key': settings.fathom_key}, timeout=60, follow_redirects=False, transport=transport)

    def close(self):
        self.client.close()

    def meetings(self, start, end):
        cursor, seen = None, set()
        while True:
            params = {'created_after': start.isoformat(), 'created_before': end.isoformat()}
            if cursor:
                params['cursor'] = cursor
            response = self.client.get('meetings', params=params)
            response.raise_for_status()
            body = response.json()
            items = body.get('items')
            if not isinstance(items, list):
                raise ValueError('Invalid Fathom meeting page')
            yield items
            cursor = body.get('next_cursor')
            if not cursor:
                return
            if cursor in seen:
                raise ValueError('Fathom pagination repeated its cursor')
            seen.add(cursor)

    def transcript(self, recording_id):
        response = self.client.get(f'recordings/{recording_id}/transcript')
        if response.status_code in {202, 404}:
            raise PendingTranscript('Transcript is not available yet')
        response.raise_for_status()
        if not response.json().get('transcript'):
            raise PendingTranscript('Transcript is not available yet')
        return response.content, response.json()


def collect(repo, request_id, client):
    with repo.connection() as conn:
        request = conn.execute("""SELECT r.*,c.activated_at,c.checkpoint FROM intake_requests r
            JOIN intake_connections c USING(connection_id) WHERE request_id=%s""", (request_id,)).fetchone()
    if request['status'] == 'completed':
        return
    # The overlap handles provider timing races, and can never cross activation.
    start = max(request['activated_at'], request['window_start'] - timedelta(minutes=10))
    discovered = set()
    for page in client.meetings(start, request['window_end']):
        with repo.connection() as conn:
            lock(conn)
            for meeting in page:
                created = datetime.fromisoformat(meeting['created_at'])
                if created.tzinfo is None:
                    raise ValueError('Fathom creation timestamp requires a timezone')
                if not request['activated_at'] <= created < request['window_end']:
                    continue
                recording_id = meeting['recording_id']
                if type(recording_id) is not int:
                    raise ValueError('Fathom recording ID must be an integer')
                sid = repo.source(conn, 'fathom', str(recording_id), 'fathom',
                    meeting.get('title') or meeting.get('meeting_title') or f'Fathom {recording_id}',
                    occurred_at=meeting.get('recording_start_time'), url=meeting.get('share_url') or meeting.get('url'),
                    metadata={'meeting': meeting, 'request_id': request_id})
                discovered.add(sid)
                # Save the exact metadata response for provenance before advancing discovery.
                repo.store.write_json(f'intake/fathom-metadata/{sid}/{request_id}.json', meeting)
    with repo.connection() as conn:
        lock(conn)
        # All discovered identities/metadata are now durable; transcription may lag.
        conn.execute("UPDATE intake_connections SET checkpoint=GREATEST(checkpoint,%s),health='ready',error_summary=NULL,updated_at=now() WHERE connection_id='fathom'", (request['window_end'],))
        pending = conn.execute("""SELECT * FROM intake_sources WHERE connection_id='fathom' AND
            (latest_revision_id IS NULL OR source_id=ANY(%s) OR metadata->>'last_checked_at' IS NULL
             OR (metadata->>'last_checked_at')::timestamptz<now()-interval '1 day') ORDER BY received_at""", (list(discovered),)).fetchall()
    unavailable = False
    for source in pending:
        try:
            raw, payload = client.transcript(source['upstream_id'])
        except PendingTranscript:
            unavailable = True
            with repo.connection() as conn:
                conn.execute("UPDATE intake_sources SET status='pending_transcript' WHERE source_id=%s", (source['source_id'],))
            continue
        digest = hashlib.sha256(raw).hexdigest()
        path = f'intake/fathom-transcripts/{digest}.json'
        repo.store.write_bytes(path, raw)
        normalized = normalize(source['metadata']['meeting'], payload, source['source_id'], digest)
        with repo.connection() as conn:
            lock(conn)
            repo.revision(conn, source['source_id'], digest, path, normalized)
            conn.execute("UPDATE intake_sources SET metadata=metadata || %s WHERE source_id=%s",
                         (Jsonb({'last_checked_at': datetime.now(UTC).isoformat()}), source['source_id']))
    with repo.connection() as conn:
        lock(conn)
        conn.execute('UPDATE intake_requests SET status=%s WHERE request_id=%s',
                     ('pending_transcript' if unavailable else 'completed', request_id))
    if unavailable:
        raise PendingTranscript('Discovered recordings are awaiting transcript publication')
