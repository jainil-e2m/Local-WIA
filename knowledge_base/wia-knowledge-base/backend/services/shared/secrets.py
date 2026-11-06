"""Symmetric encryption for secrets the KB stores (per-person provider tokens). Key: KB_SECRET_KEY."""
from cryptography.fernet import Fernet, InvalidToken

from backend.config import get_settings


class SecretKeyMissing(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = get_settings().kb_secret_key
    if not key:
        raise SecretKeyMissing("KB_SECRET_KEY is not set; stored tokens cannot be encrypted or read")
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise SecretKeyMissing("stored token cannot be decrypted with the current KB_SECRET_KEY") from exc
