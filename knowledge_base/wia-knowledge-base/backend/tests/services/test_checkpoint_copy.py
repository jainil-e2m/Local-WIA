"""A reader must never change the checkpoint it was given.

Regression (production backfill, 13 Nov): read_page made a shallow copy, the Drive walk popped the finished folder
from the queue list both copies shared, so the "did the page advance?" check saw old == new and failed the copy
with PageInvariantError whenever a folder finished within one page after page 0.
"""
from datetime import UTC, datetime
from uuid import uuid4

from backend.models.domain.intake import IntakeContext
from backend.services.intake.adapters import readers


class OneEmptyFolderDrive:
    provider = "drive"

    def _list(self, query, token, size):
        return {"files": []}  # the folder holds nothing more: it finishes in this page, no next token


def test_a_finished_drive_folder_advances_the_checkpoint_without_touching_the_input():
    ctx = IntakeContext(window_start=None, window_end=datetime.now(UTC), scope_external_id="fold-a",
                        scope_kind="folder", contacts=[], connector_account_id=uuid4(), mode="backfill")
    stored = {"phase": "walk", "feeds": {"user": "1"}, "queue": [["fold-a", []], ["fold-b", []]],
              "feed_queue": ["user"]}
    checkpoint = dict(stored)  # what execution.run_page passes in
    batch = readers.read_page(OneEmptyFolderDrive(), ctx, checkpoint)
    assert checkpoint["queue"] == [["fold-a", []], ["fold-b", []]]  # the caller's copy is untouched
    assert batch.checkpoint["queue"] == [["fold-b", []]]
    assert batch.checkpoint != checkpoint and not batch.terminal
