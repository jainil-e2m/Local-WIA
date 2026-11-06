"""A call's turn as a person reads it: the words without the "Speaker:" its transcript line begins with (a Zoom cue and a
Fathom line both read "Speaker: words"), wherever the speaker is named beside them already (N1 shakedown)."""
from __future__ import annotations


def words(text: str | None, speaker: str | None) -> str:
    """The text without a leading whole "Speaker:" of this speaker; any other text unchanged."""
    text, speaker = text or "", (speaker or "").strip()
    return text[len(speaker) + 1:].lstrip() if speaker and text.startswith(speaker + ":") else text
