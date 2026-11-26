"""Offline-first gold consumption CLI; --check-existing and --write are opt-in.

No startup hook imports or runs this CLI. Validate both CSVs and their manifest
before constructing a client. Preview/write authorization is bound to exact input
bytes, account, Region, table and snapshot; collisions are never overwritten.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Sequence

from botocore.exceptions import BotoCoreError, ClientError

from app.conditional_write import WriteConflict, conditional_put, same_item
from app.dynamodb_items import consumption_key, deserialize_item, serialize_item, timestamp_key
from app.gold import ACCOUNT, REGION, START, digest, load_export
from app.repository import RepositoryError


def create_client(region: str) -> Any:
    """Import cloud construction only after the CLI has selected a live action."""
    from app.dynamodb_repository import create_dynamodb_client
    return create_dynamodb_client(region)


def key(item: dict) -> tuple[str, str]:
    """Use the same full primary key for preview, reports and conditional writes."""
    return item["PK"], item["SK"]


def check_table(client: Any, table: str) -> None:
    """Prevent a profile/destination mistake before reads or writes."""
    metadata = client.describe_table(TableName=table)["Table"]
    if (metadata["TableArn"] != f"arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/{table}"
            or metadata["TableStatus"] != "ACTIVE"
            or {r["AttributeName"]: r["KeyType"] for r in metadata["KeySchema"]} != {"PK": "HASH", "SK": "RANGE"}
            or {r["AttributeName"]: r["AttributeType"] for r in metadata["AttributeDefinitions"]} != {"PK": "S", "SK": "S"}):
        raise ValueError("Destination account, Region, table status or key schema differs")


def preview(client: Any, table: str, items: list[dict]) -> dict:
    """Query both bounded partitions, including empty pages with continuations."""
    existing = {}
    for grain in ("hourly", "daily"):
        params = {"TableName": table, "ConsistentRead": True, "ScanIndexForward": True, "Limit": 250,
            "KeyConditionExpression": "#pk = :pk AND #sk BETWEEN :start AND :end",
            "ExpressionAttributeNames": {"#pk": "PK", "#sk": "SK"},
            "ExpressionAttributeValues": {":pk": {"S": consumption_key("household-1", grain)},
                ":start": {"S": timestamp_key(START)},
                ":end": {"S": "2009-06-07T23:59:59.999999Z"}}}
        for _ in range(100):
            response = client.query(**params)
            for raw in response.get("Items", []):
                row = deserialize_item(raw)
                if key(row) in existing or len(existing) >= 175:
                    raise ValueError("Unexpected or duplicate destination records")
                existing[key(row)] = raw
            cursor = response.get("LastEvaluatedKey")
            if not cursor:
                break
            params["ExclusiveStartKey"] = cursor
        else:
            raise ValueError("Destination preview page limit reached")
    expected = {key(row): row for row in items}
    if not existing.keys() <= expected.keys():
        raise ValueError("Destination has unexpected keys in the bounded window")
    result = {"new": 0, "identical": 0, "conflicts": 0, "keys": []}
    for item in items:
        old = existing.get(key(item))
        outcome = "new" if old is None else "identical" if same_item(old, serialize_item(item)) else "conflicts"
        result[outcome] += 1
        result["keys"].append({"PK": item["PK"], "SK": item["SK"], "outcome": outcome})
    return result


def main(argv: Sequence[str] | None = None, client_factory: Callable = create_client) -> int:
    """Return nonzero with a safe local partial report on every failed live load."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--region", required=True)
    parser.add_argument("--consumption-table", required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--check-existing", action="store_true")
    action.add_argument("--write", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--reviewed-preview", type=Path)
    parser.add_argument("--approve-preview-sha256")
    args = parser.parse_args(argv)
    client, report = None, None

    def save_report() -> None:
        """Flush progress after every key; the report is evidence, not a skip list."""
        if args.report and report is not None:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    try:
        if args.region != REGION or args.consumption_table != "g4-greentrack-dev-consumption":
            raise ValueError("Use the explicit eu-central-1 project destination")
        if args.report and args.report.exists():
            raise ValueError("Report already exists; use a new report filename")
        manifest, items = load_export(args.manifest)
        binding = {"account": ACCOUNT, "region": args.region, "table": args.consumption_table,
                   "manifest_sha256": manifest["manifest_sha256"], "snapshot_id": manifest["snapshot_id"]}
        report = {**binding, "status": "dry-run", "total_items": len(items), "written": 0, "skipped": 0, "keys": []}
        if args.write:
            if not (args.report and args.reviewed_preview and args.approve_preview_sha256):
                raise ValueError("Write requires a new report, reviewed preview and its approved SHA256")
            raw = args.reviewed_preview.read_bytes()
            approved = json.loads(raw)
            if (digest(raw) != args.approve_preview_sha256.lower() or approved.get("status") != "preview"
                    or any(approved.get(k) != v for k, v in binding.items())
                    or approved.get("conflicts") != 0 or approved.get("total_items") != len(items)):
                raise ValueError("Preview fingerprint, source, destination or conflict review differs")
        if not (args.write or args.check_existing):
            save_report()
            print(json.dumps(report))
            return 0
        if not args.report:
            raise ValueError("Live preview requires a report filename")
        client = client_factory(args.region)
        check_table(client, args.consumption_table)
        current = preview(client, args.consumption_table, items)
        report.update(current, status="preview")
        save_report()
        if current["conflicts"]:
            raise ValueError("Destination conflicts found; no writes performed")
        if args.write:
            report.update(status="writing", keys=[])
            save_report()
            for item in items:
                try:
                    outcome = conditional_put(client, args.consumption_table, serialize_item(item))
                except (RepositoryError, ClientError, BotoCoreError):
                    report["keys"].append({"PK": item["PK"], "SK": item["SK"], "outcome": "failed_or_unconfirmed"})
                    raise
                report[outcome] += 1
                report["keys"].append({"PK": item["PK"], "SK": item["SK"], "outcome": outcome})
                save_report()
            report["status"] = "complete"
            save_report()
        print(json.dumps({k: v for k, v in report.items() if k != "keys"}))
        return 0
    except (ValueError, KeyError, TypeError, ArithmeticError, OSError, RepositoryError, ClientError, BotoCoreError) as error:
        category = ("write_conflict" if isinstance(error, WriteConflict) else
                    "storage_unavailable" if isinstance(error, (RepositoryError, ClientError, BotoCoreError)) else
                    "input_or_report_error")
        if report is not None:
            report["status"] = "failed"
            report["error_category"] = category
            save_report()
        # Neither SDK diagnostics nor raw record contents belong in CLI errors.
        print(f"Gold operation failed ({category}); no overwrite/delete was attempted. Check inputs, configuration and the local report.")
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
