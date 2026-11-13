"""Call-type skills: one Markdown file per call type, frontmatter for code and sections for the model.

Seeded from services/callprep/skills/*.md into `call_skills`; edits in the app add versions there. A brief records
the version it was built with (`ref`), so an edited skill marks that type's upcoming briefs for a rebuild.

Frontmatter (validated, a bad file is never saved):
  key, name, order (detection order, lowest first), detect / not_if (regexes on the calendar title), purpose,
  type_block, sections (what the screen shows), blocks (what the evidence pack loads, see BLOCKS), length (caps the
  checks enforce), leave_out_terms (lines containing them are dropped), model: {reasoning, id?}.
Body: `## This call must decide`, `## Agenda skeleton`, `## Leave out`, `## Guidance`, `## Type-specific block`.
"""
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from sqlalchemy import func, select, update

from backend.models.db import CallSkill

SEED_DIR = Path(__file__).parent / "skills"
BLOCKS = {"last_call", "since_last_call", "owed", "email_since", "internal_slack", "leads", "ads", "profile"}
SECTIONS = {"since", "asks", "owed", "agenda", "questions", "watch", "opportunity", "typeBlock", "limits"}
BODY = ("This call must decide", "Agenda skeleton", "Leave out", "Guidance", "Type-specific block")
LENGTH_KEYS = {"points", "questions", "watch", "highlights"}
FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
HEADING = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)


class SkillError(ValueError):
    """A skill file that must not be used; the message names the field."""


@dataclass(frozen=True)
class Skill:
    key: str
    name: str
    order: int
    detect: tuple[re.Pattern, ...]
    not_if: tuple[re.Pattern, ...]
    purpose: str
    type_block: str
    sections: tuple[str, ...]
    blocks: dict
    length: dict
    leave_out_terms: tuple[str, ...]
    reasoning: str | None
    model_id: str | None
    body: dict  # heading -> text
    text: str
    ref: str = ""
    edited: dict = field(default_factory=dict)  # {by, at, version} when the current version is an edit

    @property
    def agenda(self) -> list[str]:
        return [re.sub(r"^\s*(\d+\.|[-*])\s*", "", line).strip() for line in self.body["Agenda skeleton"].splitlines()
                if line.strip()]


def parse(text: str) -> Skill:
    m = FRONT.match(text.replace("\r\n", "\n"))
    if not m:
        raise SkillError("the file must start with --- frontmatter --- and then the sections")
    try:
        front = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as error:
        raise SkillError(f"frontmatter is not valid YAML: {str(error).splitlines()[0]}") from None
    if not isinstance(front, dict):
        raise SkillError("frontmatter must be key: value pairs")
    for name in ("key", "name", "purpose"):
        if not isinstance(front.get(name), str) or not front[name].strip():
            raise SkillError(f"`{name}` is required")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,39}", front["key"]):
        raise SkillError("`key` is lowercase letters, digits and dashes")

    def patterns(name):
        raw = front.get(name) or []
        if not isinstance(raw, list) or not all(isinstance(p, str) for p in raw):
            raise SkillError(f"`{name}` is a list of patterns")
        try:
            return tuple(re.compile(p, re.IGNORECASE) for p in raw)
        except re.error as error:
            raise SkillError(f"`{name}` has a bad pattern: {error}") from None

    sections = front.get("sections") or []
    if not isinstance(sections, list) or set(sections) - SECTIONS:
        raise SkillError(f"`sections` takes {sorted(SECTIONS)}")
    blocks = front.get("blocks") or {}
    if not isinstance(blocks, dict) or set(blocks) - BLOCKS:
        raise SkillError(f"`blocks` takes {sorted(BLOCKS)}; got {sorted(set(blocks) - BLOCKS) if isinstance(blocks, dict) else blocks}")
    length = front.get("length") or {}
    if not isinstance(length, dict) or set(length) - LENGTH_KEYS or not all(isinstance(v, int) and v >= 0 for v in length.values()):
        raise SkillError(f"`length` takes whole numbers for {sorted(LENGTH_KEYS)}")
    terms = front.get("leave_out_terms") or []
    if not isinstance(terms, list) or not all(isinstance(t, str) and t.strip() for t in terms):
        raise SkillError("`leave_out_terms` is a list of words or phrases")
    model = front.get("model") or {}
    if not isinstance(model, dict) or model.get("reasoning") not in (None, "low", "medium", "high"):
        raise SkillError("`model.reasoning` is low, medium or high")
    parts = HEADING.split(m.group(2))
    body = {parts[i].strip(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    missing = [h for h in BODY if not body.get(h)]
    if missing:
        raise SkillError(f"missing section: ## {missing[0]}")
    return Skill(key=front["key"], name=front["name"].strip(), order=int(front.get("order", 500)),
                 detect=patterns("detect"), not_if=patterns("not_if"), purpose=front["purpose"].strip(),
                 type_block=str(front.get("type_block") or ""), sections=tuple(sections), blocks=blocks,
                 length={"points": 5, "questions": 3, "watch": 2, "highlights": 4, **length},
                 leave_out_terms=tuple(t.strip().lower() for t in terms), reasoning=model.get("reasoning"),
                 model_id=model.get("id"), body=body, text=text)


def sha(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest()


def seed_files() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(SEED_DIR.glob("*.md"))}


def _from_files() -> dict[str, Skill]:
    out = {}
    for stem, text in seed_files().items():
        skill = parse(text)
        if skill.key != stem:
            raise SkillError(f"{stem}.md declares key {skill.key}")
        out[skill.key] = _with(skill, ref=f"file:{sha(text)[:12]}")
    return out


def _with(skill: Skill, **changes) -> Skill:
    from dataclasses import replace
    return replace(skill, **changes)


def load_all(s=None) -> dict[str, Skill]:
    """Current skills by key, in detection order: the database versions, or the repo files before any seeding."""
    rows = s.execute(select(CallSkill).where(CallSkill.is_current)).scalars().all() if s is not None else []
    if not rows:
        skills = _from_files()
    else:
        skills = {}
        for r in rows:
            skill = parse(r.text)
            skills[r.key] = _with(skill, ref=f"db:{r.key}:{r.version}",
                                  edited={"by": r.edited_by, "at": r.created_at.isoformat(), "version": r.version}
                                  if r.source == "edit" else {})
    if "other" not in skills:
        raise SkillError("the `other` skill is required: it is the fallback for every unmatched call")
    return dict(sorted(skills.items(), key=lambda kv: (kv[1].order, kv[0])))


def excluded(skills: dict[str, Skill], title: str | None) -> str | None:
    """The pattern that marks this title as not a client call (sales, intro, interview), or None."""
    for skill in skills.values():
        for p in skill.not_if:
            if p.search(title or ""):
                return p.pattern
    return None


def detect(skills: dict[str, Skill], title: str | None) -> Skill:
    for skill in skills.values():
        if any(p.search(title or "") for p in skill.detect):
            return skill
    return skills["other"]


def seed(s, actor: str = "seed") -> list[str]:
    """Insert repo skills as new versions where the current version is an older seed (or missing). Edits made in
    the app are never overwritten: those keys are reported instead."""
    notes = []
    for stem, text in seed_files().items():
        parse(text)
        current = s.execute(select(CallSkill).where(CallSkill.key == stem, CallSkill.is_current)).scalar_one_or_none()
        digest = sha(text)
        if current is not None and (current.seed_sha == digest or current.source == "edit"):
            if current.source == "edit" and current.seed_sha != digest and not _seed_seen(s, stem, digest):
                notes.append(f"{stem}: the repo default changed but the app has edits; kept the edits")
            continue
        _add(s, stem, text, source="seed", seed_sha=digest, by=actor)
        notes.append(f"{stem}: seeded")
    return notes


def _seed_seen(s, key, digest) -> bool:
    return s.execute(select(CallSkill.id).where(CallSkill.key == key, CallSkill.seed_sha == digest)).first() is not None


def _add(s, key, text, *, source, by, seed_sha=None, note=None) -> CallSkill:
    version = (s.scalar(select(func.max(CallSkill.version)).where(CallSkill.key == key)) or 0) + 1
    s.execute(update(CallSkill).where(CallSkill.key == key, CallSkill.is_current).values(is_current=False))
    s.flush()
    row = CallSkill(key=key, version=version, is_current=True, text=text.replace("\r\n", "\n"), source=source,
                    seed_sha=seed_sha, edited_by=by, note=note)
    s.add(row)
    s.flush()
    return row


def save(s, key: str, text: str, *, by: str, note: str | None = None) -> CallSkill:
    """A person's edit: validated, then stored as the new current version. A new key adds a call type."""
    skill = parse(text)
    if skill.key != key:
        raise SkillError(f"the file's key is {skill.key}, not {key}")
    others = {k: v for k, v in load_all(s).items() if k != key}
    taken = {p.pattern.lower() for o in others.values() for p in o.detect}
    clash = [p.pattern for p in skill.detect if p.pattern.lower() in taken]
    if clash:
        raise SkillError(f"`detect` pattern {clash[0]!r} already belongs to another call type")
    if not s.execute(select(CallSkill.id).where(CallSkill.is_current)).first():
        seed(s)
    return _add(s, key, text, source="edit", by=by, note=note)


def revert(s, key: str, version: int, *, by: str) -> CallSkill:
    old = s.execute(select(CallSkill).where(CallSkill.key == key, CallSkill.version == version)).scalar_one_or_none()
    if old is None:
        raise SkillError(f"{key} has no version {version}")
    return _add(s, key, old.text, source="edit", by=by, note=f"Restored version {version}")


def versions(s, key: str) -> list[dict]:
    rows = s.execute(select(CallSkill).where(CallSkill.key == key).order_by(CallSkill.version.desc())).scalars()
    return [{"version": r.version, "current": r.is_current, "source": r.source, "by": r.edited_by,
             "at": r.created_at.isoformat(), "note": r.note, "text": r.text} for r in rows]


def present(skill: Skill) -> dict:
    """The shape the Call-type skills dialog reads (frontend calls.ts `Skill`), plus the raw file for editing."""
    return {"key": skill.key, "name": skill.name, "purpose": skill.purpose,
            "detect": "Title matches " + (", ".join(f"“{p.pattern}”" for p in skill.detect) or "nothing (fallback)"),
            "sections": list(skill.sections), "typeBlock": skill.type_block, "agenda": skill.agenda,
            "leaveOut": skill.body["Leave out"], "guidance": skill.body["Guidance"],
            "decide": skill.body["This call must decide"], "ref": skill.ref, "text": skill.text,
            **({"edited": skill.edited} if skill.edited else {})}
