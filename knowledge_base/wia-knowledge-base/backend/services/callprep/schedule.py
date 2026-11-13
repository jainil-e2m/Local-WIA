"""When briefs are built (architecture §6.2):

| condition                                                             | trigger        |
|-----------------------------------------------------------------------|----------------|
| applies, starts within AI_BRIEF_LEAD_HOURS (24), no ready version     | first          |
| starts within 2 h, current built before T-2 h, fingerprint changed    | final          |
| the call-type skill changed since the current version, within 24 h    | skill_changed  |
| cancelled, or set aside as not a client call                          | nothing        |

The fingerprint is code-only (pointers, no email bodies), so checking it every sweep costs nothing. Work items are
deduplicated on the fingerprint: the same inputs are never queued, or paid for, twice.
"""
from datetime import UTC, datetime, timedelta

from backend.config import get_settings
from backend.services.callprep import briefs, pack, registry

FINAL = timedelta(hours=2)


def due(s, now: datetime | None = None) -> list[tuple[str, str, str]]:
    """(record id, trigger, fingerprint) for every brief that should be built now. Reads only."""
    now = now or datetime.now(UTC)
    lead = timedelta(hours=get_settings().ai_brief_lead_hours)
    data = pack.payload(s)
    out = []
    for call in registry.calls(s, now, now + lead, include_cancelled=False):
        if call.excluded:
            continue
        cur = briefs.current(s, call.record_id)
        p = pack.build(s, call, data=data, instructions=briefs.latest_instructions(s, call.record_id), now=now,
                       read_bodies=False)
        if cur is None:
            out.append((str(call.record_id), "first", p.fingerprint))
        elif cur.skill_ref != call.skill.ref or cur.skill_key != call.skill.key:
            out.append((str(call.record_id), "skill_changed", p.fingerprint))
        elif call.starts_at - now <= FINAL and cur.built_at < call.starts_at - FINAL and cur.fingerprint != p.fingerprint:
            out.append((str(call.record_id), "final", p.fingerprint))
    return out
