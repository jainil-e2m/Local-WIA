import hashlib
import json
import unicodedata
from typing import Any


def normalise_text(text: str) -> str:
    """Unicode NFC + normalised line endings. Whitespace inside lines is preserved for quoting.

    NUL is dropped: PDF text extraction can emit it, and PostgreSQL text/jsonb reject it.
    """
    return unicodedata.normalize("NFC", text.replace("\x00", "")).replace("\r\n", "\n").replace("\r", "\n").strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str))
