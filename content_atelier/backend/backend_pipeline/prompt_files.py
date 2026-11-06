"""Reading a released prompt file (Round 2, WIA's feedback of 26 October 2026).

A line that is exactly `{{> name.md}}` is replaced by that file's text, from the same folder, so the writer and the
finisher share one craft and editorial guide (`craft_editorial.v1.md`) instead of two copies that drift. A file without
such a line reads exactly as written, so every earlier profile's text, and its hash, is unchanged.
"""
from __future__ import annotations

import re
from pathlib import Path

INCLUDE = re.compile(r"^\{\{> ([A-Za-z0-9_.-]+\.md)\}\}$", re.M)


def read(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return INCLUDE.sub(lambda m: (path.parent / m.group(1)).read_text(encoding="utf-8").strip(), text)
