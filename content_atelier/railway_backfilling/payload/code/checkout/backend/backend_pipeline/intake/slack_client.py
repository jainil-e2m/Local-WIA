"""Delivery adapter for an existing Slack collector; never calls Slack itself.

Persist prepared batches in the bot's outbox before send(). Retrying the exact
same bytes/batch ID is safe, including after an ambiguous HTTP timeout.
"""
from __future__ import annotations

import hashlib
import httpx
from .contracts import SlackBatch


class SlackDeliveryClient:
    def __init__(self, origin, token, *, transport=None):
        self.client = httpx.Client(base_url=origin.rstrip('/') + '/intake/v1/',
            headers={'Authorization': 'Bearer ' + token}, timeout=60,
            follow_redirects=False, transport=transport)

    def close(self):
        self.client.close()

    def requests(self):
        response = self.client.get('requests')
        response.raise_for_status()
        return response.json()

    @staticmethod
    def prepare(request, channel, messages, *, part=1, total_parts=1, gaps=None):
        # Caller pages/splits raw structured messages before assigning part counts.
        # Identity includes content and window: transport retries stay identical.
        base = {'schema_version': 1, 'request_id': request['request_id'],
                'workspace': request['config']['workspace'], 'channel': channel,
                'window_start': request['window_start'], 'window_end': request['window_end'],
                'part': part, 'total_parts': total_parts, 'messages': messages, 'gaps': gaps or []}
        from ..store import canonical_hash
        base['batch_id'] = 'bot_' + canonical_hash(base)[:48]
        return SlackBatch.model_validate(base).model_dump_json().encode()

    def send(self, prepared_bytes):
        response = self.client.post('slack/batches', content=prepared_bytes, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        return response.json()

    def receipt(self, batch_id):
        response = self.client.get(f'batches/{batch_id}')
        response.raise_for_status()
        return response.json()

    def upload(self, asset, content):
        if len(content) != asset['size_bytes'] or (asset.get('expected_hash') and hashlib.sha256(content).hexdigest() != asset['expected_hash']):
            raise ValueError('Local file differs from the attachment manifest')
        response = self.client.put(f'assets/{asset["asset_id"]}/content', content=content,
                                   headers={'Content-Type': 'application/octet-stream'})
        response.raise_for_status()
        return response.json()
