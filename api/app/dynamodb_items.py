"""Shared, deterministic DynamoDB keys and record mapping for readers/loaders."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

from .models import AnomalyPoint, ConsumptionPoint, ForecastPoint

Grain = Literal["hourly", "daily"]


def timestamp_key(value: datetime) -> str:
    """Fixed-width UTC strings sort by time, including subsecond boundaries."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("DynamoDB timestamps must include a timezone.")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def household_key(household_id: str) -> str:
    """Keep household isolation explicit in every table's partition key."""
    return f"HOUSEHOLD#{household_id}"


def consumption_key(household_id: str, grain: Grain) -> str:
    """Put daily and hourly buckets in separate queryable partitions."""
    return f"{household_key(household_id)}#GRAIN#{grain}"


def forecast_key(household_id: str, origin: datetime) -> str:
    """Separate forecast runs so different origins never overwrite each other."""
    return f"{household_key(household_id)}#ORIGIN#{timestamp_key(origin)}"


def point_item(point: ConsumptionPoint | AnomalyPoint, pk: str) -> dict[str, Any]:
    """Map one normalized point, retaining synthetic provenance in storage."""
    item = point.model_dump(mode="json")
    item.update(PK=pk, SK=timestamp_key(point.timestamp), is_demo=True, schema_version=1)
    item["timestamp"] = timestamp_key(point.timestamp)
    item["interval_end"] = timestamp_key(point.interval_end)
    return item


def consumption_item(point: ConsumptionPoint, grain: Grain) -> dict[str, Any]:
    """Future gold loaders can reuse this mapper after agreeing real provenance."""
    return {**point_item(point, consumption_key(point.household_id, grain)), "grain": grain}


def anomaly_item(point: AnomalyPoint) -> dict[str, Any]:
    """Map one anomaly under the household and affected hour."""
    return point_item(point, household_key(point.household_id))


def forecast_item(point: ForecastPoint) -> dict[str, Any]:
    """Use origin in PK and target timestamp in SK; both also remain attributes."""
    item = point_item(point, forecast_key(point.household_id, point.forecast_origin))
    item["forecast_origin"] = timestamp_key(point.forecast_origin)
    return item


def serialize_item(item: dict[str, Any]) -> dict[str, Any]:
    """Boto3 requires Decimal, not float, for low-level DynamoDB numbers."""
    serializer = TypeSerializer()
    return {
        key: serializer.serialize(Decimal(str(value)) if isinstance(value, float) else value)
        for key, value in item.items()
    }


def deserialize_item(item: dict[str, Any]) -> dict[str, Any]:
    """Recover normal Python values; Pydantic converts numeric Decimal fields."""
    deserializer = TypeDeserializer()
    return {key: deserializer.deserialize(value) for key, value in item.items()}
