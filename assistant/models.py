"""Shared request, gold-row and result types for the energy query tools."""

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, TypedDict

HOUR = timedelta(hours=1)
MAX_HOURS = 31 * 24
HOUSEHOLD_ID = re.compile(r"household-[1-9][0-9]*")
ISO_DATETIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}"
    r"(?::[0-9]{2}(?:\.[0-9]{1,6})?)?(?:Z|[+-][0-9]{2}:[0-9]{2})"
)
METER_FIELDS = ("kitchen_kwh", "laundry_kwh", "heater_ac_kwh", "other_kwh")


class ToolInputError(ValueError):
    """The requested tool or its arguments are outside the approved scope."""


class QueryError(RuntimeError):
    """The read failed and no result can safely be used."""


def _parse_bound(value: str) -> datetime:
    """Read an explicit ISO timestamp and check alignment on the UTC clock."""
    if not isinstance(value, str) or not ISO_DATETIME.fullmatch(value):
        raise ToolInputError("Use ISO date-times with T and an explicit timezone.")
    if value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise ToolInputError("Use a valid timezone offset.")
    try:
        bound = datetime.fromisoformat(value).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise ToolInputError("Use a valid date and time.") from None
    if bound.minute or bound.second or bound.microsecond:
        raise ToolInputError("Start and end must align with UTC hours.")
    return bound


def utc_label(value: datetime) -> str:
    """Format a normalized UTC timestamp for tool results."""
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class QueryWindow:
    """A single household and a validated, half-open hourly window."""

    household_id: str
    start: datetime
    end: datetime

    @classmethod
    def parse(
        cls, household_id: str, start: str, end: str, allowed_households: frozenset[str]
    ) -> "QueryWindow":
        """Apply the ID pattern, dataset scope and shared time bounds."""
        if (
            not isinstance(household_id, str)
            or len(household_id) > 64
            or not HOUSEHOLD_ID.fullmatch(household_id)
            or household_id not in allowed_households
        ):
            raise ToolInputError("Choose an approved household ID.")
        start_utc, end_utc = _parse_bound(start), _parse_bound(end)
        if not timedelta(0) < end_utc - start_utc <= MAX_HOURS * HOUR:
            raise ToolInputError(f"Choose a positive window of at most {MAX_HOURS} hours.")
        return cls(household_id, start_utc, end_utc)


def _number(value: object) -> float | None:
    """Keep null separate from zero and reject non-finite energy readings."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected a finite number or null.")
    return float(value)


BucketStatus = Literal["complete", "partial", "all_null", "absent"]


@dataclass(frozen=True)
class HourlyRow:
    """The projected columns of a published gold hourly row."""

    period_start: datetime
    energy_kwh: float | None
    minutes_with_data: int
    is_complete: bool
    kitchen_kwh: float | None
    laundry_kwh: float | None
    heater_ac_kwh: float | None
    other_kwh: float | None

    def __post_init__(self) -> None:
        """Check coverage and null consistency before using a row."""
        if (
            type(self.minutes_with_data) is not int
            or not 0 <= self.minutes_with_data <= 60
            or self.is_complete is not (self.minutes_with_data == 60)
            or (self.energy_kwh is None) != (self.minutes_with_data == 0)
        ):
            raise ValueError("Inconsistent hourly energy or coverage.")
        _number(self.energy_kwh)
        for field in METER_FIELDS:
            _number(getattr(self, field))

    @classmethod
    def from_fixture(cls, row: dict) -> "HourlyRow":
        """Parse a synthetic gold row using the fixture's explicit UTC label."""
        return cls(
            period_start=_parse_bound(row["period_start"]),
            energy_kwh=_number(row["energy_kwh"]),
            minutes_with_data=row["minutes_with_data"],
            is_complete=row["is_complete"],
            kitchen_kwh=_number(row["kitchen_kwh"]),
            laundry_kwh=_number(row["laundry_kwh"]),
            heater_ac_kwh=_number(row["heater_ac_kwh"]),
            other_kwh=_number(row["other_kwh"]),
        )

    @property
    def status(self) -> BucketStatus:
        """Classify a present bucket using active-power coverage."""
        if self.is_complete:
            return "complete"
        if self.minutes_with_data == 0:
            return "all_null"
        return "partial"


class Provenance(TypedDict):
    """Identify the input used by the executor."""

    source: Literal["synthetic_fixture", "athena"]
    source_id: str


@dataclass(frozen=True)
class HourlyRead:
    """The executor's complete set of rows and its source identifier."""

    rows: list[HourlyRow]
    provenance: Provenance


class Coverage(TypedDict):
    """Coverage of active-power observations in the requested buckets."""

    expected_minutes: int
    measured_minutes: int
    complete_hours: int
    partial_hours: int
    all_null_hours: int
    absent_hours: int


class ToolResult(TypedDict):
    """JSON-ready result envelope shared by the four tools."""

    tool: str
    status: Literal["ok", "no_data", "error"]
    household_id: str
    start: str
    end: str
    unit: Literal["kWh"]
    coverage: Coverage | None
    provenance: Provenance | None
    data: dict[str, object] | None
    message: str | None
