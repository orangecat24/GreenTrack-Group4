"""Typed input and output contracts shared by routes and application logic."""

from datetime import UTC, datetime
from typing import Generic, Literal, TypeVar

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


class Window(BaseModel):
    """A household and an inclusive-start/exclusive-end, timezone-aware window."""

    model_config = ConfigDict(extra="forbid")

    household_id: str = Field(pattern=r"^household-[1-9][0-9]*$", max_length=64)
    start: AwareDatetime
    end: AwareDatetime

    @field_validator("start", "end", mode="before")
    @classmethod
    def require_iso_datetime(cls, value: object) -> object:
        """Reject date-only/numeric inputs rather than silently guessing a timezone."""
        if not isinstance(value, datetime) and not (isinstance(value, str) and "T" in value):
            raise ValueError("Use an ISO 8601 datetime with T and a timezone, e.g. 2009-06-01T00:00:00Z")
        return value

    @field_validator("start", "end")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        """Normalize explicit offsets so equivalent windows behave identically."""
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_order(self) -> "Window":
        """A reversed or zero-length window is an input error, not an empty result."""
        if self.end <= self.start:
            raise ValueError("end must be later than start")
        return self


class ConsumptionQuery(Window):
    """Select hourly buckets or complete UTC calendar-day totals."""

    grain: Literal["hourly", "daily"] = "hourly"

    @model_validator(mode="after")
    def validate_daily_boundaries(self) -> "ConsumptionQuery":
        """Avoid presenting a partial day's energy as a complete daily total."""
        if self.grain == "daily" and any(
            (value.hour, value.minute, value.second, value.microsecond) != (0, 0, 0, 0)
            for value in (self.start, self.end)
        ):
            raise ValueError("daily grain requires start and end at UTC midnight")
        return self


class ConsumptionPoint(BaseModel):
    """Energy used during [timestamp, interval_end), not instantaneous power."""

    model_config = ConfigDict(frozen=True)
    household_id: str
    timestamp: AwareDatetime
    interval_end: AwareDatetime
    energy_kwh: float = Field(ge=0)


class AnomalyPoint(BaseModel):
    """A synthetic spike linked to the same hour in the consumption fixture."""

    model_config = ConfigDict(frozen=True)
    household_id: str
    timestamp: AwareDatetime
    interval_end: AwareDatetime
    observed_kwh: float = Field(ge=0)
    expected_kwh: float = Field(ge=0)
    score: float = Field(ge=0, le=1)
    reason: str


class ForecastPoint(ConsumptionPoint):
    """timestamp is the target hour; forecast_origin is the historical cutoff."""

    forecast_origin: AwareDatetime
    method: Literal["illustrative_previous_day"] = "illustrative_previous_day"


Item = TypeVar("Item")


class ReadResponse(BaseModel, Generic[Item]):
    """Bounded demo results with explicit requested and actual bucket coverage."""

    household_id: str
    items: list[Item]
    units: dict[str, str]
    requested_start: AwareDatetime
    requested_end: AwareDatetime
    # Coverage describes returned whole buckets, not a claim of complete source data.
    covered_start: AwareDatetime | None
    covered_end: AwareDatetime | None
    next_cursor: None = None
    is_demo: Literal[True] = True
    timezone_note: str = "UTC is a demo convention only; the source dataset timezone is unconfirmed."


class ConsumptionResponse(ReadResponse[ConsumptionPoint]):
    """Consumption envelope carrying the selected aggregation grain."""

    grain: Literal["hourly", "daily"]


class ForecastResponse(ReadResponse[ForecastPoint]):
    """Keep the forecast cutoff/horizon visible even when the result is empty."""

    forecast_origin: AwareDatetime
    target_start: AwareDatetime
    target_end: AwareDatetime
    note: str = "Illustrative previous-day values, not a trained model or validated prediction."


class ChatRequest(Window):
    """Provisional chat and weekly-summary request contract."""

    request_type: Literal["chat", "weekly_summary"] = "chat"
    message: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, value: object) -> object:
        """Whitespace-only questions must fail the minimum-length validation."""
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_chat_message(self) -> "ChatRequest":
        """Weekly summaries need a window; chat also needs a question."""
        if self.request_type == "chat" and self.message is None:
            raise ValueError("message is required for chat")
        return self


class Citation(BaseModel):
    """Reserved for real, verifiable sources when the assistant is integrated."""

    title: str
    url: str


class ChatResponse(BaseModel):
    """An honest placeholder; no generated insights or invented citations."""

    household_id: str
    request_type: Literal["chat", "weekly_summary"]
    requested_start: AwareDatetime
    requested_end: AwareDatetime
    status: Literal["placeholder"] = "placeholder"
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    assistant_connected: Literal[False] = False
    is_demo: Literal[True] = True


class HealthResponse(BaseModel):
    """Local process health does not imply any AWS service is connected."""

    status: Literal["ok"] = "ok"
    data_mode: Literal["mock"] = "mock"
    is_demo: Literal[True] = True
