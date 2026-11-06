"""Deterministic Gmail MIME → text, with authored vs quoted text separated.

Quoted history is kept (as a separate unit flagged is_quoted) so a client sentence
quoted in a later reply is not counted as a second statement.
"""
import base64
import html
import re
from html.parser import HTMLParser

_QUOTE_HEADERS = [
    re.compile(r"^\s*On .{5,200}wrote:\s*$", re.MULTILINE | re.DOTALL),
    re.compile(r"^\s*-{2,}\s*Original Message\s*-{2,}\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*-{5,}\s*Forwarded message\s*-{5,}\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*From:\s.+\n\s*(Sent|Date):\s.+$", re.MULTILINE),
]


def _b64(data: str | None) -> bytes:
    if not data:
        return b""
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "blockquote", "table"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head") and self._skip:
            self._skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(markup: str) -> str:
    parser = _TextExtractor()
    parser.feed(markup)
    text = html.unescape("".join(parser.parts))
    text = re.sub(r"[ \t ]+", " ", text)
    return re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()


def walk_parts(payload: dict) -> tuple[str | None, str | None, list[dict]]:
    """(plain, html, attachments) from a Gmail `format=full` payload."""
    plain, markup, attachments = None, None, []

    def visit(part: dict):
        nonlocal plain, markup
        mime = part.get("mimeType", "")
        body = part.get("body") or {}
        if part.get("filename"):
            # No attachmentId: Gmail issues a new one on every fetch, so it would fake a new version each run.
            attachments.append({"filename": part["filename"], "mime_type": mime, "size": body.get("size"),
                                "part_id": part.get("partId")})
        elif mime == "text/plain" and plain is None and body.get("data"):
            plain = _b64(body["data"]).decode("utf-8", errors="replace")
        elif mime == "text/html" and markup is None and body.get("data"):
            markup = _b64(body["data"]).decode("utf-8", errors="replace")
        for child in part.get("parts", []) or []:
            visit(child)

    visit(payload)
    return plain, markup, attachments


def split_quoted(text: str) -> tuple[str, str]:
    """(authored, quoted). Uses the earliest recognised reply/forward header or a trailing '>' block."""
    cut = len(text)
    for pattern in _QUOTE_HEADERS:
        m = pattern.search(text)
        if m and m.start() < cut:
            cut = m.start()
    lines = text[:cut].split("\n")
    i = len(lines)
    while i > 0 and (lines[i - 1].startswith(">") or not lines[i - 1].strip()):
        i -= 1
    if i < len(lines) and any(line.startswith(">") for line in lines[i:]):
        cut = len("\n".join(lines[:i]))
    return text[:cut].strip(), text[cut:].strip()


def message_text(payload: dict) -> tuple[str, str, list[dict], str]:
    """(authored, quoted, attachments, source_format)."""
    plain, markup, attachments = walk_parts(payload)
    if plain is not None:
        text, fmt = plain, "text/plain"
    elif markup is not None:
        text, fmt = html_to_text(markup), "text/html"
    else:
        text, fmt = "", "none"
    authored, quoted = split_quoted(text.replace("\r\n", "\n"))
    return authored, quoted, attachments, fmt
