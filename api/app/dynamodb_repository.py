"""Opt-in DynamoDB reads, using key-range Query calls and no Scan operations."""

from datetime import timedelta
from typing import Any, TypeVar

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import ValidationError

from .dynamodb_items import (
    consumption_key, deserialize_item, forecast_key, household_key, timestamp_key,
)
from .models import AnomalyPoint, ConsumptionPoint, ConsumptionQuery, ForecastPoint, Window
from .repository import RepositoryError
from .storage import DynamoSettings

Point = TypeVar("Point", ConsumptionPoint, AnomalyPoint, ForecastPoint)


def create_client(settings: DynamoSettings) -> Any:
    """Construct only on opt-in; SDK standard retries transient transport errors."""
    return boto3.session.Session().client(
        "dynamodb", region_name=settings.region,
        config=Config(retries={"mode": "standard", "total_max_attempts": 3},
                      connect_timeout=3, read_timeout=5),
    )


class DynamoDBRepository:
    """Read synthetic demo rows from named tables without seeding at startup."""

    def __init__(self, client: Any, settings: DynamoSettings) -> None:
        """Allow injected Stubber clients; construction performs no table reads."""
        self.client = client
        self.settings = settings
        self.forecast_origin = settings.forecast_origin
        self.forecast_target_start = settings.forecast_origin
        # This increment serves one configured 24-hour illustrative run. There
        # is no implicit 'latest' selection or mixing records from several runs.
        self.forecast_target_end = settings.forecast_origin + timedelta(hours=24)

    def _query(self, table: str, pk: str, query: Window, model: type[Point]) -> tuple[Point, ...]:
        """Consume DynamoDB's internal pages without changing public next_cursor."""
        params: dict[str, Any] = {
            "TableName": table,
            "KeyConditionExpression": "#pk = :pk AND #sk BETWEEN :start AND :end",
            "ExpressionAttributeNames": {"#pk": "PK", "#sk": "SK"},
            "ExpressionAttributeValues": {
                ":pk": {"S": pk}, ":start": {"S": timestamp_key(query.start)},
                # BETWEEN includes both ends. Subtract one microsecond because
                # our API end is exclusive and every stored key has six digits.
                ":end": {"S": timestamp_key(query.end - timedelta(microseconds=1))},
            },
            "ScanIndexForward": True, "ConsistentRead": True, "Limit": 250,
        }
        
        rows = []
        try:
            for _ in range(100):
                response = self.client.query(**params)
                for raw in response.get("Items", []):
                    item = deserialize_item(raw)
                    # Persisting fixtures in AWS does not make them real data.
                    # Refuse unknown provenance rather than mislabel it as demo.
                    if item.get("is_demo") is not True or item.get("schema_version") != 1:
                        raise RepositoryError("Stored demo data have unsupported provenance or schema.")
                    point = model.model_validate(item)
                    if (point.household_id != query.household_id
                            or item["PK"] != pk or item["SK"] != timestamp_key(point.timestamp)
                            or (isinstance(query, ConsumptionQuery) and item.get("grain") != query.grain)
                            or not query.start <= point.timestamp < query.end
                            or point.interval_end <= point.timestamp):
                        raise RepositoryError("Stored demo data do not match their household/time keys.")
                    rows.append(point)
                if len(rows) > 10_000:
                    raise RepositoryError("Too many records; request a smaller time window.")
                cursor = response.get("LastEvaluatedKey")
                if not cursor:
                    return tuple(sorted(rows, key=lambda point: point.timestamp))
                # An empty page can still carry a continuation key: never stop
                # just because this particular page contains zero items.
                params["ExclusiveStartKey"] = cursor
            raise RepositoryError("Too many storage pages; request a smaller time window.")
        except (ClientError, BotoCoreError) as error:
            raise RepositoryError("DynamoDB read unavailable; check storage configuration or retry.") from error
        except (ValidationError, ValueError, KeyError, TypeError) as error:
            raise RepositoryError("Stored demo data are invalid.") from error

    def consumption(self, query: ConsumptionQuery) -> tuple[ConsumptionPoint, ...]:
        """Query the requested grain, not all household history or both grains."""
        return self._query(self.settings.consumption_table,
                           consumption_key(query.household_id, query.grain), query, ConsumptionPoint)

    def anomalies(self, query: Window) -> tuple[AnomalyPoint, ...]:
        """Read only anomaly hours within the selected household window."""
        return self._query(self.settings.anomalies_table, household_key(query.household_id), query, AnomalyPoint)

    def forecast(self, query: Window) -> tuple[ForecastPoint, ...]:
        """Select target hours within the explicitly configured forecast origin."""
        rows = self._query(self.settings.forecasts_table,
                           forecast_key(query.household_id, self.forecast_origin), query, ForecastPoint)
        if any(point.forecast_origin != self.forecast_origin
               or not self.forecast_target_start <= point.timestamp < self.forecast_target_end
               for point in rows):
            raise RepositoryError("Stored forecast data do not match the selected 24-hour origin.")
        return rows

    def close(self) -> None:
        """Release this app instance's HTTP connection pool on shutdown."""
        self.client.close()
