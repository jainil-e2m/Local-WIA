from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ID = r"^[A-Za-z0-9_-]{1,140}$"


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Mutation(Payload):
    request_id: str = Field(min_length=8, max_length=140, pattern=ID)


class ScheduleItem(Payload):
    asset_id: str = Field(pattern=ID)
    expected_asset_hash: str = Field(min_length=1, max_length=128)
    entry_id: str | None = Field(default=None, pattern=ID)
    expected_revision: int | None = Field(default=None, ge=1)
    scheduled_for: datetime
    display_timezone: str = Field(default="Asia/Kolkata", max_length=80)

    @field_validator("display_timezone")
    @classmethod
    def zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Choose a valid IANA timezone") from exc
        return value

    @model_validator(mode="after")
    def instant(self):
        if self.scheduled_for.tzinfo is None or self.scheduled_for.utcoffset() is None:
            raise ValueError("Publishing time must include a UTC offset")
        local = self.scheduled_for.astimezone(ZoneInfo(self.display_timezone))
        if local.utcoffset() != self.scheduled_for.utcoffset():
            raise ValueError("Publishing offset does not match the selected timezone")
        if (self.entry_id is None) != (self.expected_revision is None):
            raise ValueError("Existing entry ID and revision must be supplied together")
        return self


class Schedule(Mutation):
    expected_pack_manifest_hash: str = Field(min_length=1, max_length=128)
    whole_pack: bool = False
    items: list[ScheduleItem] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def unique(self):
        if len({i.asset_id for i in self.items}) != len(self.items):
            raise ValueError("An asset may be scheduled only once per request")
        return self


class Reschedule(Mutation):
    expected_revision: int = Field(ge=1)
    scheduled_for: datetime
    display_timezone: str = Field(default="Asia/Kolkata", max_length=80)

    @model_validator(mode="after")
    def valid_instant(self):
        ScheduleItem(
            asset_id="validation",
            expected_asset_hash="validation",
            scheduled_for=self.scheduled_for,
            display_timezone=self.display_timezone,
        )
        return self


class Cancel(Mutation):
    expected_revision: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2000)


def utc(value):
    return value.astimezone(UTC)
