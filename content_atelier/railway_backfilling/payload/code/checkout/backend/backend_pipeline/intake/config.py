from __future__ import annotations

import os
from pydantic import BaseModel, Field


class IntakeSettings(BaseModel):
    redis_url: str = 'redis://localhost:16379/0'
    slack_token: str = ''
    fathom_key: str = ''
    fathom_base_url: str = 'https://api.fathom.ai/external/v1'
    workspace: str = 'T03P5A3L1DK'
    channels: tuple[str, ...] = ('C082DURRJ2U', 'C09LQ656BPU', 'C091CPQD8L9')
    admins: tuple[str, ...] = ()
    encoding_enabled: bool = False
    max_upload_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    max_batch_bytes: int = Field(default=4 * 1024 * 1024, gt=0)
    audio_model: str = 'small.en'
    max_audio_seconds: int = 7200

    @classmethod
    def from_env(cls):
        return cls(
            redis_url=os.getenv('ATELIER_INTAKE_REDIS_URL', cls.model_fields['redis_url'].default),
            slack_token=os.getenv('ATELIER_SLACK_INTAKE_TOKEN', ''),
            fathom_key=os.getenv('ATELIER_FATHOM_API_KEY', ''),
            workspace=os.getenv('ATELIER_SLACK_WORKSPACE', cls.model_fields['workspace'].default),
            channels=tuple(x.strip() for x in os.getenv('ATELIER_SLACK_CHANNELS', ','.join(cls.model_fields['channels'].default)).split(',') if x.strip()),
            admins=tuple(x.strip().lower() for x in os.getenv('ATELIER_INTAKE_ADMINS', '').split(',') if x.strip()),
            encoding_enabled=os.getenv('ATELIER_ALLOW_INTAKE_ENCODING') == 'true',
            audio_model=os.getenv('ATELIER_INTAKE_AUDIO_MODEL', 'small.en'))
