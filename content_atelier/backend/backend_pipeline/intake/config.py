from __future__ import annotations

import os
from pydantic import Field
from .. import settings_store
from ..settings_store import LoadedSettings, default


def fathom_api_key(environ=None) -> str:
    """The Fathom key: `ATELIER_FATHOM_API_KEY`, else `FATHOM_API_KEY` (the name a developer's backend/.env has long used).
    The prefixed name wins when both are set."""
    environ = os.environ if environ is None else environ
    return environ.get('ATELIER_FATHOM_API_KEY') or environ.get('FATHOM_API_KEY', '')


class IntakeSettings(LoadedSettings):
    """Intake configuration. It reads the environment through the same single reader as the rest of the platform
    (settings_store.load_env_files, which includes .env.intake.local); the workspace, the channels and the audio
    model are settings, the tokens, keys and the encoding catch stay in the environment."""
    redis_url: str = 'redis://localhost:16379/0'
    slack_token: str = ''
    fathom_key: str = ''
    fathom_base_url: str = 'https://api.fathom.ai/external/v1'
    workspace: str = default('intake.slack.workspace')
    channels: tuple[str, ...] = default('intake.slack.channels')
    admins: tuple[str, ...] = ()
    encoding_enabled: bool = False
    max_upload_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    max_batch_bytes: int = Field(default=4 * 1024 * 1024, gt=0)
    audio_model: str = default('intake.audio_model')
    max_audio_seconds: int = 7200

    @classmethod
    def from_env(cls, conn=None, *, database_url: str | None = None):
        return cls.from_effective(settings_store.load(conn, database_url=database_url))

    @classmethod
    def from_effective(cls, eff):
        return cls(
            redis_url=os.getenv('ATELIER_INTAKE_REDIS_URL', cls.model_fields['redis_url'].default),
            slack_token=os.getenv('ATELIER_SLACK_INTAKE_TOKEN', ''),
            fathom_key=fathom_api_key(),
            workspace=eff['intake.slack.workspace'],
            channels=eff['intake.slack.channels'],
            admins=tuple(x.strip().lower() for x in os.getenv('ATELIER_INTAKE_ADMINS', '').split(',') if x.strip()),
            encoding_enabled=os.getenv('ATELIER_ALLOW_INTAKE_ENCODING') == 'true',
            audio_model=eff['intake.audio_model'])._attach(eff)
