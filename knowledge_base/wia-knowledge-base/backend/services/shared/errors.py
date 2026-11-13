"""Intake error taxonomy (Ingestion design §7.1). The class decides retry vs block vs gap."""


class IntakeError(Exception):
    error_class = "bug"
    retryable = False

    def __init__(self, message: str, *, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class TransientError(IntakeError):
    error_class = "transient"
    retryable = True


class ThrottledError(IntakeError):
    error_class = "throttled"
    retryable = True


class AuthInvalidError(IntakeError):
    """Credential revoked/expired or identity mismatch: block the connector account."""
    error_class = "auth_invalid"


class ScopeDeniedError(IntakeError):
    """A feature the credential was never granted: record as inaccessible coverage."""
    error_class = "scope_denied"


class NotFoundError(IntakeError):
    error_class = "not_found"


class CursorExpiredError(IntakeError):
    """Provider cursor/sync token invalid (e.g. HTTP 410): start a tracked full resync."""
    error_class = "cursor_expired"


class CrashLoopError(IntakeError):
    """A job whose worker died this many times running it: fail it (visible, resumable), never reclaim forever."""
    error_class = "crash_loop"


class UnsupportedContentError(IntakeError):
    error_class = "unsupported"
