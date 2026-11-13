"""Local preview only: add a few clearly marked test proposals ("[TEST] …") so the admin review can be tried while
the AI is off. Each is tied to one of the client's real meetings, but no AI ran and the quote is a placeholder.

    python -m backend.scripts.seed_test_proposals            # 2 per client with a meeting, at most 4 clients
    python -m backend.scripts.seed_test_proposals --remove   # delete every test proposal (and its decision)
"""
import argparse
import sys
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import delete, select

from backend.config import get_settings
from backend.db import transaction
from backend.models.db import (
    ActionCandidate,
    AiRun,
    Business,
    RecordAssociation,
    SourceRecord,
)
from backend.models.db.base import utcnow
from backend.services.read_models import portfolio

SKILL = "test_seed"  # never a real skill: --remove deletes by it
PROPOSALS = [("Send the updated ad creative options for review", "WIA", 5),
             ("Share the venue's new tour availability for the landing page", "Client", 9)]


def seed(s, per_client: int = 2, clients: int = 4) -> int:
    added = 0
    for business in s.execute(select(Business).where(Business.status == "active").order_by(Business.slug)).scalars():
        meeting = s.execute(select(SourceRecord.id).join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                            .where(RecordAssociation.business_id == business.id, RecordAssociation.status == "associated",
                                   SourceRecord.record_kind.in_(("fathom_recording", "calendar_event")),
                                   SourceRecord.occurred_at <= utcnow())
                            .order_by(SourceRecord.occurred_at.desc()).limit(1)).scalar()
        if meeting is None:
            continue
        run = AiRun(id=uuid4(), skill=SKILL, skill_version="0", model="none (seeded)", subject_kind="meeting",
                    subject_id=str(meeting), business_id=business.id, input_hash=uuid4().hex, state="succeeded")
        s.add(run)
        s.flush()
        for title, side, days in PROPOSALS[:per_client]:
            s.add(ActionCandidate(id=uuid4(), run_id=run.id, business_id=business.id, kind="new", title=f"[TEST] {title}",
                                  owner_side=side, due_date=(utcnow() + timedelta(days=days)).date(),
                                  quote="Seeded test proposal: no AI ran, so there is no quote.",
                                  source_record_id=meeting, verified=False))
            added += 1
        clients -= 1
        if not clients:
            break
    portfolio.request_refresh(s)
    return added


def remove(s) -> int:
    runs = select(AiRun.id).where(AiRun.skill == SKILL)
    n = s.execute(delete(ActionCandidate).where(ActionCandidate.run_id.in_(runs))).rowcount
    s.execute(delete(AiRun).where(AiRun.skill == SKILL))
    portfolio.request_refresh(s)
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remove", action="store_true", help="delete every test proposal")
    args = parser.parse_args()
    if get_settings().environment != "local":
        sys.exit("Refused: test proposals are for a local preview only (ENVIRONMENT=local).")
    with transaction() as s:
        print(f"Removed {remove(s)} test proposals." if args.remove else f"Added {seed(s)} test proposals.")


if __name__ == "__main__":
    main()
