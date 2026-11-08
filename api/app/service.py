"""Build stable API response envelopes over either storage implementation."""

from typing import Sequence, TypeVar

from .models import (
    AnomalyPoint, ChatRequest, ChatResponse, ConsumptionPoint, ConsumptionQuery,
    ConsumptionResponse, ForecastResponse, ReadResponse, Window,
)
from .repository import EnergyRepository


TimedPoint = TypeVar("TimedPoint", bound=ConsumptionPoint | AnomalyPoint)


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
        """Read the requested grain; storage can now query just that window."""
        items = self.repository.consumption(query)
        return ConsumptionResponse(**metadata(query, items, {"energy_kwh": "kWh"}), grain=query.grain)

    def anomalies(self, query: Window) -> ReadResponse[AnomalyPoint]:
        """Filter demo detections without calculating new anomaly scores."""
        items = self.repository.anomalies(query)
        return ReadResponse[AnomalyPoint](**metadata(query, items, {
            "observed_kwh": "kWh", "expected_kwh": "kWh", "score": "unitless",
        }))

    def forecast(self, query: Window) -> ForecastResponse:
        """Filter by target timestamp; keep origin and full horizon explicit."""
        items = self.repository.forecast(query)
        return ForecastResponse(
            **metadata(query, items, {"energy_kwh": "kWh"}),
            forecast_origin=self.repository.forecast_origin,
            target_start=self.repository.forecast_target_start,
            target_end=self.repository.forecast_target_end,
        )

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Reserve a clear integration point without inventing answers."""
        feature = "weekly summary" if request.request_type == "weekly_summary" else "chat"
        return ChatResponse(
            household_id=request.household_id, request_type=request.request_type,
            requested_start=request.start, requested_end=request.end,
            answer=f"Placeholder: {feature} is not implemented. Bedrock is not connected.",
        )
