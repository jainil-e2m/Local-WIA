"""All configuration loading for the KB backend.

Secrets come from the environment (backend/.env locally, deployment variables in
Railway). Nothing in this module has a secret default.

PRODUCTION_MODE is the one switch between the two ways the backend runs:
  false (default)  local development: intake runs on demand (`kb backfill`, `worker --drain`), the
                   sync scheduler stays off, and the unauthenticated local-only routes are available.
  true             staging / production: the sync scheduler is on unless SYNC_SCHEDULER_ENABLED=false
                   pauses it, team routes need the shared team password, and get_settings() refuses to
                   start when a production requirement is missing (see config_problems).
"""
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


class ConfigError(RuntimeError):
    """Configuration that must not start. Names settings only, never their values."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore", env_ignore_empty=True)

    production_mode: bool = False
    # local | staging | production. Unset: follows PRODUCTION_MODE (local, or production).
    environment: str | None = None
    database_url: str = "postgresql+psycopg://kb:kb@localhost:5440/kb"
    ops_token: str | None = None  # protects /api/v1/ops until Command Center hand-off exists

    # Intake behaviour. INGEST_WINDOW_DAYS unset = full history (production backfill).
    ingest_window_days: int | None = None
    # Discovery looks further back than the backfill so quiet clients still get contacts (G-04)
    discovery_window_days: int = 365
    # ClickUp spaces where every folder (or folderless list) is one client, e.g. '["ELEVATE Clients"]'.
    # Their folders are proposed even when no client matches yet, so a new client shows up for mapping.
    clickup_client_spaces: list[str] = Field(default_factory=list)
    slack_thread_lookback_days: int = 90  # older roots are re-read so in-window replies are not missed
    http_timeout_seconds: float = 30.0
    max_file_bytes: int = 25 * 1024 * 1024

    # Work runner
    worker_lanes: str = "sync,bulk,maintenance"
    lease_seconds: int = 90
    retry_delays_seconds: list[int] = Field(default_factory=lambda: [10, 30, 120])
    poll_idle_seconds: float = 2.0
    # Unset: follows PRODUCTION_MODE. Set false in production to pause all provider polling (e.g. during
    # an incident); set true locally only to try the scheduler by hand.
    sync_scheduler_enabled: bool | None = None
    scheduler_sweep_seconds: float = 30.0
    sync_interval_seconds: int = 300
    reconcile_interval_seconds: int = 86400
    fathom_webhook_secrets: dict[str, str] = Field(default_factory=dict)  # account UUID -> whsec_...

    # Connector credentials (read only by adapters, never logged or stored in the DB)
    slack_bot_token: str | None = None
    clickup_token: str | None = None
    clickup_team_id: str | None = None
    fathom_api_key: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_refresh_token: str | None = None
    # ClickUp OAuth app: per-person connections for write-back under each person's own name (S1/S12)
    clickup_oauth_client_id: str | None = None
    clickup_oauth_client_secret: str | None = None
    clickup_oauth_redirect_uri: str = "http://localhost:8010/api/v1/clickup/oauth/callback"
    kb_secret_key: str | None = None  # Fernet key; encrypts stored per-person tokens
    # Where the KB frontend lives: OAuth callbacks send people back here (frontend dev server locally)
    kb_app_url: str = "http://127.0.0.1:3001"
    # LeadLock (HighLevel) Marketplace app "WIA Client Knowledge Base": one agency install, a token per client
    # sub-account. Only grants for leadlock_company_id are accepted. The URL path avoids "ghl": HighLevel's
    # white-label rules refuse redirect URLs that mention it.
    leadlock_app_client_id: str | None = None
    leadlock_app_client_secret: str | None = None
    leadlock_app_id: str | None = None
    leadlock_company_id: str | None = None
    leadlock_redirect_uri: str = "http://localhost:8010/api/v1/leadlock/oauth/callback"
    # HighLevel's published Ed25519 key for the X-GHL-Signature webhook header (the RSA X-WH-Signature
    # header was retired on 1 Sep 2026). Override only if HighLevel rotates it.
    leadlock_webhook_public_key: str = (
        "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAi2HR1srL4o18O8BRa7gVJY7G7bupbN3H9AwJrHCDiOg=\n-----END PUBLIC KEY-----")

    # Outbound guard (S1/S12). Nothing reaches Slack or ClickUp unless: mode allows it, the kill switch is
    # off, the target is allowed (sandbox), and a listed approver approved that exact request at a terminal.
    outbound_mode: str = "off"  # off | sandbox | live  (live only ever set by hand on production)
    outbound_kill_switch: bool = False
    outbound_approvers: list[str] = Field(default_factory=list)  # e.g. '["jainil"]'
    outbound_approval_ttl_hours: int = 24
    outbound_sandbox_slack_channels: list[str] = Field(default_factory=list)  # channel IDs, e.g. '["C0..."]'
    outbound_sandbox_slack_users: list[str] = Field(default_factory=list)  # Slack user IDs allowed for test DMs
    outbound_sandbox_clickup_lists: list[str] = Field(default_factory=list)  # ClickUp list IDs

    # Interim shared team password (until named Google sign-in): HTTP Basic, checked against this scrypt hash.
    # Make one with `python -m backend.scripts.kb password-hash`. Required outside local.
    kb_team_password_hash: str | None = None
    frontend_dist: Path | None = None  # built portfolio (npm run build:live), served at / when set

    # AI layer (OpenRouter), decided 6 Nov. Nothing is sent unless AI_MODE=live, a key is set and the month's
    # spend is under AI_MONTHLY_BUDGET_USD. Off: no AI worker, the AI sweep queues nothing.
    ai_mode: str = "off"  # off | live
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    ai_monthly_budget_usd: float = 0.0
    ai_email_batch_hours: int = 24
    ai_brief_lead_hours: int = 36
    ai_models: dict[str, str] = Field(default_factory=dict)  # per-skill model override, e.g. '{"call_brief": "..."}'
    # Internal team meetings (all invitees internal) whose title matches are read for actions; empty = none.
    internal_meeting_title_pattern: str | None = None

    # Local runtime output (gitignored): discovery proposals and run reports
    local_dir: Path = BACKEND_DIR / ".local"

    @model_validator(mode="after")
    def _derive_from_mode(self) -> "Settings":
        # Fill the mode-dependent defaults only. Checks that refuse to start live in config_problems(),
        # outside pydantic, so an error can never echo a secret value back into a log.
        if self.environment is None:
            self.environment = "production" if self.production_mode else "local"
        # Railway's Postgres reference is postgresql://; the installed driver is psycopg 3.
        for prefix in ("postgres://", "postgresql://"):
            if self.database_url.startswith(prefix):
                self.database_url = "postgresql+psycopg://" + self.database_url[len(prefix):]
        if self.sync_scheduler_enabled is None:
            self.sync_scheduler_enabled = self.production_mode
        return self

    @property
    def mode(self) -> str:
        return "production" if self.production_mode else "local"

    def config_problems(self) -> list[str]:
        """Every reason this configuration must not start, by setting name."""
        problems = []
        if self.environment not in ("local", "staging", "production"):
            problems.append("ENVIRONMENT must be local, staging or production")
        elif self.production_mode and self.environment == "local":
            # ENVIRONMENT=local opens the unauthenticated local-only routes: never with production data.
            problems.append("PRODUCTION_MODE=true needs ENVIRONMENT=staging or production (or unset)")
        elif not self.production_mode and self.environment != "local":
            problems.append(f"ENVIRONMENT={self.environment} needs PRODUCTION_MODE=true")
        if self.outbound_mode not in ("off", "sandbox", "live"):
            problems.append("OUTBOUND_MODE must be off, sandbox or live")
        if self.kb_team_password_hash:
            from backend.routes.access import valid_hash
            if not valid_hash(self.kb_team_password_hash):
                problems.append("KB_TEAM_PASSWORD_HASH is not a hash from `kb password-hash`")
        if self.ai_mode not in ("off", "live"):
            problems.append("AI_MODE must be off or live")
        elif self.ai_mode == "live" and (not self.openrouter_api_key or self.ai_monthly_budget_usd <= 0):
            problems.append("AI_MODE=live needs OPENROUTER_API_KEY and AI_MONTHLY_BUDGET_USD above 0")
        if self.internal_meeting_title_pattern:
            import re
            try:
                re.compile(self.internal_meeting_title_pattern)
            except re.error:
                problems.append("INTERNAL_MEETING_TITLE_PATTERN is not a valid regular expression")
        if not self.production_mode:
            if self.outbound_mode == "live":
                problems.append("OUTBOUND_MODE=live is refused outside PRODUCTION_MODE")
            return problems
        if _is_local(self.database_url):
            problems.append("DATABASE_URL points at this machine; production needs its own database")
        if not self.kb_secret_key:
            problems.append("KB_SECRET_KEY is required: it encrypts the stored ClickUp and LeadLock tokens")
        if not self.ops_token:
            problems.append("OPS_TOKEN is required: it protects the ops API used to watch sync")
        if not self.kb_team_password_hash:
            problems.append("KB_TEAM_PASSWORD_HASH is required: it protects the portfolio and its API")
        if self.ingest_window_days is not None:
            problems.append("INGEST_WINDOW_DAYS must be unset: production intake covers full history")
        oauth_urls = []
        if self.clickup_oauth_client_id:
            oauth_urls += [("KB_APP_URL", self.kb_app_url), ("CLICKUP_OAUTH_REDIRECT_URI", self.clickup_oauth_redirect_uri)]
        if self.leadlock_app_client_id:
            oauth_urls.append(("LEADLOCK_REDIRECT_URI", self.leadlock_redirect_uri))
        for name, url in oauth_urls:
            if _is_local(url) or urlparse(url).scheme != "https":
                problems.append(f"{name} must be the deployed https address, not a local one")
        return problems


def _is_local(url: str) -> bool:
    return (urlparse(url.replace("+psycopg", "")).hostname or "") in LOCAL_HOSTS


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    problems = settings.config_problems()
    if problems:
        raise ConfigError(f"{settings.mode} configuration refused:\n  - " + "\n  - ".join(problems))
    return settings
