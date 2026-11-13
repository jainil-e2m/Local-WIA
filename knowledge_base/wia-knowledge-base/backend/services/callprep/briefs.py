"""Brief versions: stored per call, each with the skill version, instructions, fingerprint and facts it was built
from. Only a `ready` version becomes current; a rejected one is kept for its reasons. "Changed since built" and
"not applicable" are derived when read, never stored.
"""
from sqlalchemy import func, select, update

from backend.models.db import CallBrief


def save(s, pack, *, output: dict | None, checks: dict, ai_run_id, trigger: str, built_by: str) -> CallBrief:
    version = (s.scalar(select(func.max(CallBrief.version)).where(CallBrief.record_id == pack.call.record_id)) or 0) + 1
    ready = output is not None
    if ready:
        s.execute(update(CallBrief).where(CallBrief.record_id == pack.call.record_id, CallBrief.is_current)
                  .values(is_current=False))
        s.flush()
    row = CallBrief(record_id=pack.call.record_id, version=version, is_current=ready, skill_key=pack.skill.key,
                    skill_ref=pack.skill.ref, instructions=pack.instructions, fingerprint=pack.fingerprint,
                    inputs=pack.inputs, facts=pack.facts, output=output, refs=pack.refs.items, checks=checks,
                    ai_run_id=ai_run_id, trigger=trigger, built_by=built_by, outcome="ready" if ready else "rejected")
    s.add(row)
    s.flush()
    return row


def current(s, record_id) -> CallBrief | None:
    return s.execute(select(CallBrief).where(CallBrief.record_id == record_id, CallBrief.is_current)).scalar_one_or_none()


def latest_instructions(s, record_id) -> str | None:
    """Instructions a person gave stay with the call: automatic rebuilds reuse the latest version's."""
    row = s.execute(select(CallBrief).where(CallBrief.record_id == record_id)
                    .order_by(CallBrief.version.desc()).limit(1)).scalar_one_or_none()
    return row.instructions if row else None


def reasons(old: dict, new: dict) -> list[str]:
    """Plain phrases for what changed between two fingerprints' inputs."""
    out = []

    def added(key):
        return len({repr(x) for x in new.get(key, [])} - {repr(x) for x in old.get(key, [])})
    if old.get("skill") != new.get("skill"):
        out.append("call-type skill edited or changed")
    if old.get("starts") != new.get("starts"):
        out.append("call moved")
    if old.get("instructions") != new.get("instructions"):
        out.append("instructions changed")
    for key, label in (("email", "client email"), ("slack", "internal Slack message"), ("asks", "unanswered ask"),
                       ("awaiting", "email awaiting our reply"), ("changes", "History event")):
        n = added(key)
        if n:
            out.append(f"{n} new {label}{'s' if n != 1 else ''}")
    if old.get("actions") != new.get("actions"):
        n = added("actions")
        out.append(f"{n} action{'s' if n != 1 else ''} changed" if n else "actions closed or changed")
    if old.get("promised") != new.get("promised") or old.get("digest") != new.get("digest"):
        out.append("the last meeting's digest or its promises changed")
    if old.get("attendance") != new.get("attendance"):
        out.append("attendance changed")
    return out


def history(s, record_id) -> list[CallBrief]:
    return s.execute(select(CallBrief).where(CallBrief.record_id == record_id).order_by(CallBrief.version)).scalars().all()
