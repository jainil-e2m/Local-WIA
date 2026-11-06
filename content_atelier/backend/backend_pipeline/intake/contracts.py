from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator


class Payload(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Asset(Payload):
    file_id: str = Field(min_length=1, max_length=200)
    filename: str = Field(min_length=1, max_length=300)
    mime_type: str = Field(min_length=1, max_length=150)
    size_bytes: int = Field(ge=0)
    sha256: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    permalink: str | None = Field(default=None, max_length=2000)


class Message(Payload):
    ts: str = Field(pattern=r'^\d{10,}\.[0-9]{1,9}$')
    thread_ts: str | None = Field(default=None, pattern=r'^\d{10,}\.[0-9]{1,9}$')
    text: str = Field(default='', max_length=200000)
    user: str | None = Field(default=None, max_length=200)
    updated_at: AwareDatetime
    deleted: bool = False
    context_only: bool = False
    permalink: str | None = Field(default=None, max_length=2000)
    files: list[Asset] = Field(default_factory=list, max_length=50)
    raw: dict = Field(default_factory=dict)


class SlackBatch(Payload):
    schema_version: Literal[1] = 1
    batch_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,140}$')
    request_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,140}$')
    workspace: str
    channel: str
    window_start: AwareDatetime
    window_end: AwareDatetime
    part: int = Field(ge=1)
    total_parts: int = Field(ge=1, le=10000)
    messages: list[Message] = Field(default_factory=list, max_length=1000)
    gaps: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def valid_window(self):
        if self.window_end < self.window_start or self.part > self.total_parts:
            raise ValueError('Invalid collection window or part number')
        return self


def slack_time(ts: str) -> datetime:
    return datetime.fromtimestamp(float(Decimal(ts)), UTC)
