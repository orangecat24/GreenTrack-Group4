"""Validate and run the four approved tools over hourly gold rows."""

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from math import fsum
from pathlib import Path
from typing import Callable, Protocol

from .models import (
    HOUR,
    METER_FIELDS,
    BucketStatus,
    Coverage,
    HourlyRead,
    HourlyRow,
    QueryError,
    QueryWindow,
    ToolInputError,
    ToolResult,
    utc_label,
)


class HourlyExecutor(Protocol):
    """The only read operation needed for the tools."""

    def fetch_hours(self, window: QueryWindow) -> HourlyRead:
        """Return all selected hourly rows or raise QueryError."""


class FixtureExecutor:
    """Read explicitly synthetic gold data without any cloud client."""

    def __init__(self, path: Path) -> None:
        """Load a local P3 01-shaped fixture for offline use."""
        self._path = path

    def fetch_hours(self, window: QueryWindow) -> HourlyRead:
        """Apply the same household and half-open range filter as Athena."""
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if payload["is_synthetic"] is not True:
                raise QueryError("Expected a fixture marked as synthetic.")
            source_rows = payload["hourly_consumption"]
            if not isinstance(source_rows, list):
                raise QueryError("Expected a list of synthetic hourly rows.")
            rows = []
            for raw in source_rows:
                if raw["household_id"] == window.household_id:
                    row = HourlyRow.from_fixture(raw)
                    if window.start <= row.period_start < window.end:
                        rows.append(row)
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            raise QueryError("The synthetic fixture could not be read.") from None
        return HourlyRead(rows, {"source": "synthetic_fixture", "source_id": self._path.name})


@dataclass(frozen=True)
class _Bucket:
    """A requested hour with an optional published row."""

    start: datetime
    row: HourlyRow | None

    @property
    def status(self) -> BucketStatus:
        """Identify missing rows separately from published all-null rows."""
        return "absent" if self.row is None else self.row.status


def _buckets(window: QueryWindow, rows: list[HourlyRow]) -> list[_Bucket]:
    """Fill gaps on the hourly grid and reject inconsistent results."""
    count = (window.end - window.start) // HOUR
    if len(rows) > count:
        raise QueryError("The read returned more rows than requested hours.")
    by_start: dict[datetime, HourlyRow] = {}
    for row in rows:
        start = row.period_start
        if (
            start.tzinfo is None
            or not window.start <= start < window.end
            or (start - window.start) % HOUR
            or start in by_start
        ):
            raise QueryError("The read returned a duplicate or unexpected hour.")
        by_start[start] = row
    return [
        _Bucket(start, by_start.get(start))
        for start in (window.start + offset * HOUR for offset in range(count))
    ]


def _coverage(buckets: list[_Bucket]) -> Coverage:
    """Count bucket types and minutes for every requested hour."""
    counts = Counter(bucket.status for bucket in buckets)
    return {
        "expected_minutes": 60 * len(buckets),
        "measured_minutes": sum(bucket.row.minutes_with_data for bucket in buckets if bucket.row),
        "complete_hours": counts["complete"],
        "partial_hours": counts["partial"],
        "all_null_hours": counts["all_null"],
        "absent_hours": counts["absent"],
    }


def _consumption_totals(buckets: list[_Bucket]) -> tuple[bool, dict[str, object]]:
    """Sum the observed kWh, retaining null when every bucket is missing."""
    observed = [
        bucket.row.energy_kwh for bucket in buckets
        if bucket.row is not None and bucket.row.energy_kwh is not None
    ]
    return bool(observed), {"observed_kwh": fsum(observed) if observed else None}


def _hourly_patterns(buckets: list[_Bucket]) -> tuple[bool, dict[str, object]]:
    """Return a chronological series, including grid hours missing from gold."""
    hours = [
        {
            "period_start": utc_label(bucket.start),
            "observed_kwh": bucket.row.energy_kwh if bucket.row else None,
            "minutes_with_data": bucket.row.minutes_with_data if bucket.row else 0,
            "bucket_status": bucket.status,
        }
        for bucket in buckets
    ]
    return any(hour["observed_kwh"] is not None for hour in hours), {"hours": hours}


def _weekday_weekend(buckets: list[_Bucket]) -> tuple[bool, dict[str, object]]:
    """Compare average energy per complete hour on the historical clock."""
    groups: dict[str, list[_Bucket]] = {"weekday": [], "weekend": []}
    for bucket in buckets:
        groups["weekday" if bucket.start.weekday() < 5 else "weekend"].append(bucket)

    comparison = {}
    for name, group in groups.items():
        # A partial hour would lower the average based on missing minutes.
        # Compare equal-length measured hours and include genuine zero values.
        observed = [
            bucket.row.energy_kwh for bucket in group
            if bucket.row and bucket.row.is_complete and bucket.row.energy_kwh is not None
        ]
        comparison[name] = {
            "mean_kwh_per_complete_hour": fsum(observed) / len(observed) if observed else None,
            "eligible_hours": len(observed),
            "coverage": _coverage(group),
        }
    return any(item["eligible_hours"] for item in comparison.values()), comparison


def _submetering_breakdown(buckets: list[_Bucket]) -> tuple[bool, dict[str, object]]:
    """Sum observed circuit values independently and retain the gold residual."""
    meters = {}
    for field in METER_FIELDS:
        values = [getattr(bucket.row, field) for bucket in buckets if bucket.row]
        observed = [value for value in values if value is not None]
        meters[field] = {
            "observed_kwh": fsum(observed) if observed else None,
            "hours_with_values": len(observed),
        }
    return any(item["hours_with_values"] for item in meters.values()), meters


_TOOLS: dict[str, Callable[[list[_Bucket]], tuple[bool, dict[str, object]]]] = {
    "consumption_totals": _consumption_totals,
    "hourly_patterns": _hourly_patterns,
    "weekday_weekend": _weekday_weekend,
    "submetering_breakdown": _submetering_breakdown,
}


class QueryTools:
    """Public entry point for named, read-only energy tools."""

    def __init__(
        self, executor: HourlyExecutor, *, allowed_households: frozenset[str] = frozenset({"household-1"})
    ) -> None:
        """Use a trusted dataset scope and an executor chosen by the application."""
        self._executor = executor
        self._allowed_households = allowed_households

    def run(self, name: str, *, household_id: str, start: str, end: str) -> ToolResult:
        """Run one approved calculation after validating all request arguments."""
        if not isinstance(name, str) or name not in _TOOLS:
            raise ToolInputError("Choose an approved read-only energy tool.")
        window = QueryWindow.parse(household_id, start, end, self._allowed_households)
        result: ToolResult = {
            "tool": name,
            "status": "error",
            "household_id": window.household_id,
            "start": utc_label(window.start),
            "end": utc_label(window.end),
            "unit": "kWh",
            "coverage": None,
            "provenance": None,
            "data": None,
            "message": "Energy data could not be read. Try again later.",
        }
        try:
            read = self._executor.fetch_hours(window)
            buckets = _buckets(window, read.rows)
            has_data, data = _TOOLS[name](buckets)
        except (QueryError, OverflowError):
            return result

        result["status"] = "ok" if has_data else "no_data"
        result["coverage"] = _coverage(buckets)
        result["provenance"] = read.provenance
        result["data"] = data
        result["message"] = None
        return result
