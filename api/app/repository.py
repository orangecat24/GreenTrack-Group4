"""Deterministic in-memory fixtures; this module has no cloud or network client."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol, Sequence, TypeVar

from .models import AnomalyPoint, ConsumptionPoint, ConsumptionQuery, ForecastPoint, Window

HOUSEHOLD = "household-1"
HISTORY_START = datetime(2009, 6, 1, tzinfo=UTC)
FORECAST_ORIGIN = datetime(2009, 6, 8, tzinfo=UTC)
FORECAST_END = FORECAST_ORIGIN + timedelta(hours=24)

# Hundredths of a kWh keep fixture arithmetic deterministic. This is invented
# demonstration data, not a sample copied from the UCI source dataset.
HOURLY_CENTS = (30, 28, 27, 26, 28, 35, 55, 80, 65, 50, 45, 48,
                70, 55, 45, 48, 65, 90, 115, 105, 85, 65, 48, 38)
SPIKES_CENTS = {(1, 18): 250, (3, 19): 310, (5, 12): 190}


class RepositoryError(RuntimeError):
    """A safe storage failure message, without raw AWS errors or configuration."""


Point = TypeVar("Point", bound=ConsumptionPoint | AnomalyPoint)


def select_window(records: Sequence[Point], query: Window) -> tuple[Point, ...]:
    """Select whole buckets by start time with inclusive start/exclusive end."""
    return tuple(row for row in records if query.start <= row.timestamp < query.end)


def daily_totals(readings: Sequence[ConsumptionPoint]) -> tuple[ConsumptionPoint, ...]:
    """Derive daily rows once for both mock reads and the synthetic seed loader."""
    totals: dict[tuple[str, datetime], Decimal] = defaultdict(Decimal)
    for row in readings:
        day = row.timestamp.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        # Decimal(str(...)) sums displayed energy without binary-float drift.
        totals[(row.household_id, day)] += Decimal(str(row.energy_kwh))
    return tuple(
        ConsumptionPoint(household_id=household, timestamp=day,
                         interval_end=day + timedelta(days=1), energy_kwh=float(total))
        for (household, day), total in sorted(totals.items())
    )


class EnergyRepository(Protocol):
    """The small window-aware contract shared by mock and DynamoDB storage."""

    forecast_origin: datetime
    forecast_target_start: datetime
    forecast_target_end: datetime

    def consumption(self, query: ConsumptionQuery) -> tuple[ConsumptionPoint, ...]:
        """Return ordered windowed observations in the requested grain."""
        ...

    def anomalies(self, query: Window) -> tuple[AnomalyPoint, ...]:
        """Return ordered anomaly records for one household."""
        ...

    def forecast(self, query: Window) -> tuple[ForecastPoint, ...]:
        """Return ordered target hours from the illustrative forecast."""
        ...

    def close(self) -> None:
        """Release owned storage resources during application shutdown."""
        ...


class MockRepository:
    """Build one coherent week once, then expose immutable fixture records."""

    forecast_origin = FORECAST_ORIGIN
    forecast_target_start = FORECAST_ORIGIN
    forecast_target_end = FORECAST_END

    def __init__(self) -> None:
        """Create 168 readings, three matching spikes, and 24 future buckets."""
        readings = []
        anomalies = []
        for day in range(7):
            for hour, base_cents in enumerate(HOURLY_CENTS):
                timestamp = HISTORY_START + timedelta(days=day, hours=hour)
                expected_cents = base_cents + day * 2
                spike_cents = SPIKES_CENTS.get((day, hour), 0)
                reading = ConsumptionPoint(
                    household_id=HOUSEHOLD, timestamp=timestamp,
                    interval_end=timestamp + timedelta(hours=1),
                    energy_kwh=(expected_cents + spike_cents) / 100,
                )
                readings.append(reading)
                if spike_cents:
                    anomalies.append(AnomalyPoint(
                        household_id=HOUSEHOLD, timestamp=timestamp,
                        interval_end=reading.interval_end,
                        observed_kwh=reading.energy_kwh,
                        expected_kwh=expected_cents / 100, score=0.95,
                        reason="Synthetic fixture spike; not a model detection.",
                    ))
        self._readings = tuple(readings)
        self._anomalies = tuple(anomalies)
        # Repeat the final observed day to illustrate a forecast shape without
        # training a model or reading observations from the future target day.
        self._forecast = tuple(
            ForecastPoint(
                household_id=HOUSEHOLD,
                timestamp=FORECAST_ORIGIN + timedelta(hours=hour),
                interval_end=FORECAST_ORIGIN + timedelta(hours=hour + 1),
                energy_kwh=reading.energy_kwh, forecast_origin=FORECAST_ORIGIN,
            )
            for hour, reading in enumerate(self._readings[-24:])
        )

    def consumption(self, query: ConsumptionQuery) -> tuple[ConsumptionPoint, ...]:
        """Unknown but well-formed household IDs have no demo observations."""
        readings = self._readings if query.household_id == HOUSEHOLD else ()
        rows = daily_totals(readings) if query.grain == "daily" else readings
        return select_window(rows, query)

    def anomalies(self, query: Window) -> tuple[AnomalyPoint, ...]:
        """Return the three fixed spikes, with no inference calls."""
        return select_window(self._anomalies, query) if query.household_id == HOUSEHOLD else ()

    def forecast(self, query: Window) -> tuple[ForecastPoint, ...]:
        """Return the fixed June 8 target horizon, with no inference calls."""
        return select_window(self._forecast, query) if query.household_id == HOUSEHOLD else ()

    def close(self) -> None:
        """The in-memory repository has no connections to close."""
