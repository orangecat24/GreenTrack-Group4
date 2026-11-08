"""Storage configuration and lazy selection; importing this module never uses AWS."""

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from .repository import EnergyRepository, FORECAST_ORIGIN, MockRepository


@dataclass(frozen=True)
class DynamoSettings:
    """Explicit destination names and Region, shared by API and seed CLI."""

    region: str
    consumption_table: str
    anomalies_table: str
    forecasts_table: str
    forecast_origin: datetime = FORECAST_ORIGIN

    def __post_init__(self) -> None:
        """Reject missing/ambiguous destinations before constructing any client."""
        if not self.region or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+-\d+", self.region):
            raise ValueError("An explicit AWS Region is required, e.g. eu-central-1.")
        names = (self.consumption_table, self.anomalies_table, self.forecasts_table)
        if any(not re.fullmatch(r"[A-Za-z0-9_.-]{3,255}", name) for name in names):
            raise ValueError("Provide three explicit valid DynamoDB table names (3-255 characters).")
        if len(set(names)) != 3:
            raise ValueError("Consumption, anomalies, and forecasts require distinct tables.")
        if self.forecast_origin.tzinfo is None or self.forecast_origin.utcoffset() is None:
            raise ValueError("The active forecast origin must include a timezone.")
        object.__setattr__(self, "forecast_origin", self.forecast_origin.astimezone(UTC))

    @classmethod
    def from_environment(cls) -> "DynamoSettings":
        """Use dedicated variables; never infer a Region or table from credentials."""
        return cls(
            region=os.getenv("DYNAMODB_REGION", ""),
            consumption_table=os.getenv("DYNAMODB_CONSUMPTION_TABLE", ""),
            anomalies_table=os.getenv("DYNAMODB_ANOMALIES_TABLE", ""),
            forecasts_table=os.getenv("DYNAMODB_FORECASTS_TABLE", ""),
            forecast_origin=datetime.fromisoformat(os.getenv(
                "DYNAMODB_FORECAST_ORIGIN", FORECAST_ORIGIN.isoformat())),
        )


def create_repository() -> EnergyRepository:
    """Keep the mock path free of SDK imports, clients, and credential lookup."""
    mode = os.getenv("APP_DATA_MODE", "mock")
    if mode == "mock":
        return MockRepository()
    if mode == "dynamodb":
        settings = DynamoSettings.from_environment()
        # Importing/constructing the SDK belongs exclusively to this opt-in path.
        from .dynamodb_repository import DynamoDBRepository, create_client

        return DynamoDBRepository(create_client(settings), settings)
    raise RuntimeError("APP_DATA_MODE must be mock or dynamodb.")
