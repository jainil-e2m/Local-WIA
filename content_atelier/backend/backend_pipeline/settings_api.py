"""Settings over HTTP (plan 0.B8): GET /storage/settings and PUT /storage/settings/{key}.

These routes serve operators and scripts holding the backend secret, and the app's Settings screen (6.F7): the Node
server's allowlist (frontend/server/allowlist.mjs) relays the read, and a change only to the four keys that screen edits
(the duplicate cutoff and the weekly cycle's schedule). Every other key stays a `storage_cli settings` change.

Who may read and write is decided in one place, `require_settings_admin`. Item 0.B9 replaces its body with the
users-and-roles lookup; until then it uses the Gate 1 lists (editors and approvers read, approvers write).
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from . import gate_one, settings_store


def require_settings_admin(repo, actor, capability):
    """capability 'read': an editor or approver; 'write': an approver. Resolved through gates/roles.py like every other role check (0.B9)."""
    gate_one.require(repo, actor, 'decide' if capability == 'write' else 'edit')


class SettingValue(BaseModel):
    model_config = ConfigDict(extra='forbid')
    value: Any = None


def install(routes, repo, decider, action):
    def checked(call):
        def run():
            try:
                return call()
            except settings_store.SettingError as error:
                raise HTTPException(422, str(error)) from error
        return run

    @routes.get('/settings')
    def settings_list(subject: str = Depends(decider)):
        def read():
            require_settings_admin(repo, subject, 'read')
            with repo.connection() as conn:
                effective = settings_store.load(conn, read_files=False)
                return {'settings': settings_store.listing(conn), 'problems': effective.problems}
        return action(checked(read))

    @routes.put('/settings/{key}')
    def settings_put(key: str, payload: SettingValue, subject: str = Depends(decider)):
        def write():
            require_settings_admin(repo, subject, 'write')
            with repo.connection() as conn:
                result = settings_store.set_value(conn, key, payload.value, subject)
                conn.commit()
                return result
        return action(checked(write))
