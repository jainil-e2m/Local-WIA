"""Dotted paths into a brief's body, and the locks a person's edits put on them (5.F1, 5.F4, 5.F5; interface 1).

A path names one place in the writer's sections of a v2, v3 or later brief body: section names and keys joined by dots, a
list item by its index from 0, as `format_plan.reels[1].cover_text`, `format_plan.email.subject_options[0]` or
`format_plan.carousel.slides[3].text`. A bare section name (`format_plan`) is a path too: the whole section, which is how
locks were recorded before 22 October, so older briefs keep their meaning.

The walker reads the body as data and knows no contract: contract v4's new fields are paths like any other, and the
contract's own model validates the result of an edit. Gate 2's editor (frontend/src/components/briefFields.ts) walks the
same shape with the same path syntax.

A person's edit locks the path it changed, never the whole section; a refresh keeps every locked line verbatim and may
rewrite everything else. A refreshed draft that changed a locked line has the person's line put back and the restoration
recorded (`restore`); a draft that has no place for a locked line (the Reel, the slide or the option is gone, or a slide
now carries another number) is refused, because putting the line back would put it in the wrong place.
"""
from __future__ import annotations

import copy
import re

_SEGMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)((?:\[\d{1,3}\])*)")
_INDEX = re.compile(r"\[(\d{1,3})\]")


def parse(path: str) -> list[str | int]:
    """The tokens of a path: keys as strings, list indexes as integers. Raises ValueError on anything else."""
    if not isinstance(path, str) or not path or len(path) > 300:
        raise ValueError(f"Not a field path: {path!r}")
    tokens: list[str | int] = []
    for part in path.split("."):
        m = _SEGMENT.fullmatch(part)
        if not m:
            raise ValueError(f"Not a field path: {path!r}; use names and [index], as format_plan.reels[0].cover_text")
        tokens.append(m.group(1))
        tokens.extend(int(i) for i in _INDEX.findall(m.group(2)))
    return tokens


def render(tokens: list[str | int]) -> str:
    out = ""
    for t in tokens:
        out += f"[{t}]" if isinstance(t, int) else (("." if out else "") + t)
    return out


def canonical(path: str) -> str:
    return render(parse(path))


def section(path: str) -> str:
    return str(parse(path)[0])


def _step(node, token):
    if isinstance(token, int):
        if not isinstance(node, list) or not 0 <= token < len(node):
            raise KeyError(token)
        return node[token]
    if not isinstance(node, dict) or token not in node:
        raise KeyError(token)
    return node[token]


def get(body: dict, path: str):
    """The value at a path. Raises ValueError when the path names no place in the body."""
    node = body
    for token in parse(path):
        try:
            node = _step(node, token)
        except KeyError:
            raise ValueError(f"The brief has no field {path}") from None
    return node


def exists(body: dict, path: str) -> bool:
    try:
        get(body, path)
        return True
    except ValueError:
        return False


def put(body: dict, path: str, value) -> dict:
    """A copy of the body with the value at an existing path replaced."""
    tokens = parse(path)
    out = copy.deepcopy(body)
    node = out
    for token in tokens[:-1]:
        try:
            node = _step(node, token)
        except KeyError:
            raise ValueError(f"The brief has no field {path}") from None
    last = tokens[-1]
    try:
        _step(node, last)
    except KeyError:
        raise ValueError(f"The brief has no field {path}") from None
    node[last] = copy.deepcopy(value)
    return out


def leaves(body, prefix: str = "") -> list[tuple[str, object]]:
    """Every scalar in the body with its path (strings, numbers, booleans and nulls), in document order."""
    if isinstance(body, dict):
        return [x for k, v in body.items() for x in leaves(v, f"{prefix}.{k}" if prefix else k)]
    if isinstance(body, list):
        return [x for i, v in enumerate(body) for x in leaves(v, f"{prefix}[{i}]")]
    return [(prefix, body)]


def overlaps(a: str, b: str) -> bool:
    """Whether one path is the other or lies inside it (an edit of either touches the other)."""
    x, y = parse(a), parse(b)
    n = min(len(x), len(y))
    return x[:n] == y[:n]


def touched(path: str, edited) -> bool:
    return any(overlaps(path, p) for p in edited)


def apply(body: dict, changes: dict, allowed) -> tuple[dict, list[str]]:
    """The body with a person's changes ({path: value}) applied, and the paths whose value changed (canonical, sorted).
    Every path must name an existing place in a section a person may edit."""
    out, changed = body, []
    for raw, value in changes.items():
        path = canonical(raw)
        if section(path) not in allowed:
            raise ValueError(f"{path} is not a field a person edits; editable sections: " + ", ".join(sorted(allowed)))
        before = get(out, path)
        if before != value:
            out = put(out, path, value)
            changed.extend(_changed_lines(path, before, value))
    return out, sorted(set(changed))


def _changed_lines(path: str, before, after) -> list[str]:
    """The lines an edit changed: when a whole section or item is sent with the same shape (the screen of 20 October sent
    whole sections), only the leaves whose value differs; otherwise the path itself."""
    if isinstance(before, (dict, list)) and isinstance(after, (dict, list)):
        old, new = dict(leaves(before, path)), dict(leaves(after, path))
        if old.keys() == new.keys():
            return [p for p in new if old[p] != new[p]]
    return [path]


def merge_locks(existing, added) -> list[str]:
    """The locks after an edit: the old ones and the new paths, one per place."""
    return sorted({canonical(p) for p in [*existing, *added]})


def _same_place(parent: dict, draft: dict, path: str) -> bool:
    """Whether the draft has the place the locked line had: every index on the path exists, and an item that carries a
    `number` (a carousel slide) carries the same number."""
    a, b = parent, draft
    for token in parse(path):
        try:
            a, b = _step(a, token), _step(b, token)
        except KeyError:
            return False
        if isinstance(token, int) and isinstance(a, dict) and isinstance(b, dict) and a.get("number") != b.get("number"):
            return False
    return True


def restore(parent: dict, draft: dict, keep) -> tuple[dict, list[dict]]:
    """The draft with every kept lock's value put back from the parent, and a record of each line the draft had changed.
    Raises ValueError, naming the line, when the draft has no place for it."""
    out, restored = draft, []
    for path in sorted(set(keep)):
        if not exists(parent, path):
            continue  # a lock on a place the parent itself no longer has (an earlier section edit removed it)
        if not _same_place(parent, out, path):
            raise ValueError(f"The refreshed draft has no place for the locked line {path}: it removed or renumbered it. "
                             "The person's edit is kept on the current version; refresh again, or unlock that line first")
        value = get(parent, path)
        if get(out, path) != value:
            restored.append({"path": path, "draft": get(out, path)})
            out = put(out, path, value)
    return out, restored


def revision_locks(run: dict, parent: dict | None) -> list[str]:
    """The locks a revision keeps: the parent's, less the lines the reviewer released for this refresh (`unlock`) and,
    for a lock on a whole section, a section the instructions name ("rewrite the format_plan"), as before."""
    from .validation import unlocked_fields
    if not parent:
        return []
    locks = parent["content_body"].get("review", {}).get("locked_fields", [])
    released = {canonical(p) for p in run["input_refs"].get("unlock") or []}
    named = unlocked_fields(run["input_refs"].get("instructions") or "", [p for p in locks if "." not in p and "[" not in p])
    return sorted({canonical(p) for p in locks} - released - set(named))


def locked_values(body: dict, locks) -> list[dict]:
    """The writer's `locked_fields` render variable (interface 1): each lock with the value it must keep."""
    return [{"path": p, "value": get(body, p)} for p in sorted(set(locks)) if exists(body, p)]
