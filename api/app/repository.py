"""Deterministic in-memory fixtures; this module has no cloud or network client."""

from datetime import UTC, datetime, timedelta
from typing import Protocol

from .models import AnomalyPoint, ConsumptionPoint, ForecastPoint

HOUSEHOLD = "household-1"
HISTORY_START = datetime(2009, 6, 1, tzinfo=UTC)
FORECAST_ORIGIN = datetime(2009, 6, 8, tzinfo=UTC)
FORECAST_END = FORECAST_ORIGIN + timedelta(hours=24)

# Hundredths of a kWh keep fixture arithmetic deterministic. This is invented
# demonstration data, not a sample copied from the UCI source dataset.
HOURLY_CENTS = (30, 28, 27, 26, 28, 35, 55, 80, 65, 50, 45, 48,
                70, 55, 45, 48, 65, 90, 115, 105, 85, 65, 48, 38)
SPIKES_CENTS = {(1, 18): 250, (3, 19): 310, (5, 12): 190}


class EnergyRepository(Protocol):
    """The small storage contract a future DynamoDB adapter must implement."""

    def consumption(self, household_id: str) -> tuple[ConsumptionPoint, ...]:
        """Return ordered hourly observations for one household."""
        ...

    def anomalies(self, household_id: str) -> tuple[AnomalyPoint, ...]:
        """Return ordered anomaly records for one household."""
        ...

    def forecast(self, household_id: str) -> tuple[ForecastPoint, ...]:
        """Return ordered target hours from the illustrative forecast."""
        ...


class MockRepository:
    """Build one coherent week once, then expose immutable fixture records."""

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

    def consumption(self, household_id: str) -> tuple[ConsumptionPoint, ...]:
        """Unknown but well-formed household IDs have no demo observations."""
        return self._readings if household_id == HOUSEHOLD else ()

    def anomalies(self, household_id: str) -> tuple[AnomalyPoint, ...]:
        """Return the three fixed spikes, with no inference calls."""
        return self._anomalies if household_id == HOUSEHOLD else ()

    def forecast(self, household_id: str) -> tuple[ForecastPoint, ...]:
        """Return the fixed June 8 target horizon, with no inference calls."""
        return self._forecast if household_id == HOUSEHOLD else ()
