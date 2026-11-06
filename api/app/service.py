"""Business rules: time filtering, daily aggregation, and response metadata."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Sequence, TypeVar

from .models import (
    AnomalyPoint, ChatRequest, ChatResponse, ConsumptionPoint, ConsumptionQuery,
    ConsumptionResponse, ForecastResponse, ReadResponse, Window,
)
from .repository import EnergyRepository, FORECAST_END, FORECAST_ORIGIN


TimedPoint = TypeVar("TimedPoint", bound=ConsumptionPoint | AnomalyPoint)


def select_window(records: Sequence[TimedPoint], window: Window) -> list[TimedPoint]:
    """Select buckets by start time using exactly start <= timestamp < end."""
    return [record for record in records if window.start <= record.timestamp < window.end]


def metadata(window: Window, items: Sequence[TimedPoint], units: dict[str, str]) -> dict[str, object]:
    """Describe the requested range and the whole buckets actually returned."""
    return {
        "household_id": window.household_id,
        "items": items,
        "units": units,
        "requested_start": window.start,
        "requested_end": window.end,
        "covered_start": items[0].timestamp if items else None,
        "covered_end": items[-1].interval_end if items else None,
    }


class EnergyService:
    """Keep storage details out of routes and HTTP details out of the repository."""

    def __init__(self, repository: EnergyRepository) -> None:
        """Accept storage through the contract so a real adapter can replace mocks."""
        self.repository = repository

    def consumption(self, query: ConsumptionQuery) -> ConsumptionResponse:
        """Aggregate filtered hourly readings; never maintain a second daily fixture."""
        items = select_window(self.repository.consumption(query.household_id), query)
        if query.grain == "daily":
            # Store integer hundredths while summing to avoid float drift. All
            # fixture readings have two decimal places; future data may need Decimal.
            daily_cents: dict[datetime, int] = defaultdict(int)
            for item in items:
                day = item.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                daily_cents[day] += round(item.energy_kwh * 100)
            items = [
                ConsumptionPoint(
                    household_id=query.household_id, timestamp=day,
                    interval_end=day + timedelta(days=1), energy_kwh=cents / 100,
                )
                for day, cents in sorted(daily_cents.items())
            ]
        return ConsumptionResponse(**metadata(query, items, {"energy_kwh": "kWh"}), grain=query.grain)

    def anomalies(self, query: Window) -> ReadResponse[AnomalyPoint]:
        """Filter demo detections without calculating new anomaly scores."""
        items = select_window(self.repository.anomalies(query.household_id), query)
        return ReadResponse[AnomalyPoint](**metadata(query, items, {
            "observed_kwh": "kWh", "expected_kwh": "kWh", "score": "unitless",
        }))

    def forecast(self, query: Window) -> ForecastResponse:
        """Filter by target timestamp; keep origin and full horizon explicit."""
        items = select_window(self.repository.forecast(query.household_id), query)
        return ForecastResponse(
            **metadata(query, items, {"energy_kwh": "kWh"}),
            forecast_origin=FORECAST_ORIGIN, target_start=FORECAST_ORIGIN,
            target_end=FORECAST_END,
        )

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Reserve a clear integration point without inventing answers."""
        feature = "weekly summary" if request.request_type == "weekly_summary" else "chat"
        return ChatResponse(
            household_id=request.household_id, request_type=request.request_type,
            requested_start=request.start, requested_end=request.end,
            answer=f"Placeholder: {feature} is not implemented. Bedrock is not connected.",
        )
