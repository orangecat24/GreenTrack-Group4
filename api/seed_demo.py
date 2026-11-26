"""Dry-run-first CLI for explicitly seeding deterministic synthetic demo rows.

Run from the repository root with: .venv/Scripts/python.exe api/seed_demo.py ...
This script never creates tables and is never invoked by API startup.
"""

import argparse
import json
import sys
import time
from typing import Any, Callable, Sequence

from botocore.exceptions import BotoCoreError, ClientError

from app.dynamodb_items import anomaly_item, consumption_item, forecast_item, serialize_item
from app.dynamodb_repository import create_client
from app.models import ConsumptionQuery, Window
from app.repository import FORECAST_END, FORECAST_ORIGIN, HISTORY_START, HOUSEHOLD, MockRepository, RepositoryError
from app.storage import DynamoSettings


def fixture_items(settings: DynamoSettings) -> dict[str, list[dict[str, Any]]]:
    """Map existing fixtures to the same keys that the DynamoDB reader queries."""
    repository = MockRepository()
    history = {"household_id": HOUSEHOLD, "start": HISTORY_START, "end": FORECAST_ORIGIN}
    consumption = [
        serialize_item(consumption_item(point, grain))
        for grain in ("hourly", "daily")
        for point in repository.consumption(ConsumptionQuery(**history, grain=grain))
    ]
    return {
        settings.consumption_table: consumption,
        settings.anomalies_table: [serialize_item(anomaly_item(point))
                                  for point in repository.anomalies(Window(**history))],
        settings.forecasts_table: [serialize_item(forecast_item(point))
                                  for point in repository.forecast(Window(
                                      household_id=HOUSEHOLD, start=FORECAST_ORIGIN, end=FORECAST_END))],
    }


def write_items(client: Any, tables: dict[str, list[dict[str, Any]]],
                sleep: Callable[[float], None] = time.sleep) -> int:
    """Insert synthetic rows conditionally; reruns skip identical existing rows.

    Gold and synthetic keys can overlap. Never let a demo seed replace a real
    observation, even if another writer inserts after our offline preview.
    """
    from app.conditional_write import conditional_put

    for table, items in tables.items():
        for item in items:
            conditional_put(client, table, item, sleep=sleep)
    return sum(map(len, tables.values()))


def main(argv: Sequence[str] | None = None, client_factory: Callable = create_client) -> int:
    """Require explicit destinations; no write flag means no AWS client at all."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--consumption-table", required=True)
    parser.add_argument("--anomalies-table", required=True)
    parser.add_argument("--forecasts-table", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview only; this is also the default.")
    mode.add_argument("--write", action="store_true", help="Explicitly enable writes to the named existing tables.")
    args = parser.parse_args(argv)
    try:
        settings = DynamoSettings(args.region, args.consumption_table, args.anomalies_table, args.forecasts_table)
    except ValueError as error:
        parser.error(str(error))
    tables = fixture_items(settings)
    print(json.dumps({
        "mode": "write" if args.write else "dry-run (no AWS client or calls)",
        "region": settings.region,
        "is_demo": True,
        "total_items": sum(map(len, tables.values())),
        "tables": {table: {"items": len(items), "first_key": {key: items[0][key]["S"] for key in ("PK", "SK")}}
                   for table, items in tables.items()},
    }, indent=2))
    if not args.write:
        return 0
    client = None
    try:
        client = client_factory(settings)
        count = write_items(client, tables)
        print(f"Wrote {count} synthetic demo items using protected stable keys (identical records skipped).")
        return 0
    except (RepositoryError, ClientError, BotoCoreError):
        print("Seed failed. Some records may already be written; check configuration and rerun with the same keys.", file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
