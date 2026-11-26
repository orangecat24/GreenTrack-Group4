"""Offline validation of the reviewed gold export and its schema-2 projection.

Gold source contract v1 is separate from our DynamoDB record schema 2. A hash
binds reviewed inputs; it does not establish authenticity of arbitrary files.
"""

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any
from uuid import UUID

from .dynamodb_items import consumption_key, timestamp_key
from .models import ConsumptionPoint

ACCOUNT = "886565871385"
REGION = "eu-central-1"
DATASET = "uci-household-power-v1"
START = datetime(2009, 6, 1, tzinfo=UTC)
END = datetime(2009, 6, 8, tzinfo=UTC)
COLUMNS = ["household_id", "period_start", "energy_kwh", "minutes_with_data", "is_complete"]
CLOCK_NOTE = "Original clock preserved; UTC is the project interchange convention, not a verified source timezone."


def digest(value: bytes) -> str:
    """Fingerprint exact input bytes for review/destination binding."""
    return hashlib.sha256(value).hexdigest()


def validate_gold_item(item: dict[str, Any]) -> ConsumptionPoint:
    """Reject malformed provenance, keys, intervals and quality claims."""
    if (item.get("is_demo") is not False or item.get("schema_version") != 2
            or item.get("data_source") != "gold" or item.get("dataset_id") != DATASET
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(item.get("snapshot_id", "")))
            or item.get("source_clock_note") != CLOCK_NOTE):
        raise ValueError("Unsupported gold provenance or schema")
    grain = item.get("grain")
    if grain not in ("hourly", "daily"):
        raise ValueError("Invalid gold grain")
    # DynamoDB Number deserializes to Decimal. Reject strings/booleans instead
    # of letting Pydantic turn a wrongly typed storage value into a measurement.
    energy = item.get("energy_kwh")
    if (energy is not None and (isinstance(energy, bool) or not isinstance(energy, (Decimal, int, float)))):
        raise ValueError("Gold energy must be a number or null")
    if not isinstance(item.get("minutes_with_data"), (int, Decimal)):
        raise ValueError("Observed-minute count must be numeric")
    point = ConsumptionPoint.model_validate(item)
    minutes = 60 if grain == "hourly" else 1440
    t = point.timestamp
    if (t.utcoffset() != timedelta(0) or t.minute or t.second or t.microsecond
            or (grain == "daily" and t.hour)
            or point.interval_end != t + timedelta(minutes=minutes)
            or item.get("PK") != consumption_key(point.household_id, grain)
            or item.get("SK") != timestamp_key(t)):
        raise ValueError("Gold interval does not match its keys/grain")
    count = point.minutes_with_data
    if (count is None or isinstance(item.get("minutes_with_data"), bool)
            or not 0 <= count <= minutes or type(item.get("is_complete")) is not bool
            or point.is_complete != (count == minutes)
            or (count == 0) != (point.energy_kwh is None)):
        raise ValueError("Gold quality/energy fields are inconsistent")
    return point


def load_export(manifest_path: Path) -> tuple[dict, list[dict]]:
    """Validate BOTH grains before a caller may create an AWS client.

    This first loader accepts only the agreed household/week. An edited manifest
    cannot silently widen its write scope. Missing buckets are rejected, not filled.
    """
    raw_manifest = manifest_path.read_bytes()
    if len(raw_manifest) > 100_000:
        raise ValueError("Manifest is unexpectedly large")
    manifest = json.loads(raw_manifest)
    expected = {"export_manifest_version": 1, "account": ACCOUNT, "region": REGION,
                "household_id": "household-1", "source_contract_version": "v1",
                "dataset_id": DATASET, "requested_start": "2009-06-01T00:00:00Z",
                "requested_end": "2009-06-08T00:00:00Z", "source_clock_note": CLOCK_NOTE}
    if any(manifest.get(k) != v for k, v in expected.items()):
        raise ValueError("Manifest identity, contract, clock or bounded window differs")
    rows_by_grain = {}
    canonical = {"dataset_id": DATASET, "source_contract_version": "v1",
        "household_id": "household-1", "start": expected["requested_start"],
        "end": expected["requested_end"], "grains": {}}
    for grain, minutes, count in (("hourly", 60, 168), ("daily", 1440, 7)):
        entry = manifest["exports"][grain]
        if entry["table"] != f"g4_greentrack_dev_gold.{grain}_consumption":
            raise ValueError("Unexpected source table")
        UUID(entry["query_id"])
        relative = Path(entry["file"])
        path = (manifest_path.parent / relative).resolve()
        if (relative.name != str(relative) or relative.suffix != ".csv"
                or not path.is_relative_to(manifest_path.parent.resolve())):
            raise ValueError("Export file must stay beside the manifest")
        raw = path.read_bytes()
        if len(raw) > 1_000_000 or digest(raw) != entry["sha256"]:
            raise ValueError("Export checksum/size differs from manifest")
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if reader.fieldnames != COLUMNS:
            raise ValueError("Unexpected CSV schema")
        rows = []
        for row in reader:
            # Remove only Athena's display suffix. Preserve the source clock;
            # attaching UTC is the project convention, not a zone conversion.
            clock = datetime.fromisoformat(row["period_start"].removesuffix(" UTC"))
            if clock.tzinfo is not None:
                raise ValueError("Expected the exported unconverted source clock")
            timestamp = clock.replace(tzinfo=UTC)
            if row["is_complete"] not in ("true", "false") or None in row:
                raise ValueError("Invalid CSV boolean or extra columns")
            energy = Decimal(row["energy_kwh"]) if row["energy_kwh"] else None
            item = {"household_id": row["household_id"], "timestamp": timestamp_key(timestamp),
                "interval_end": timestamp_key(timestamp + timedelta(minutes=minutes)),
                "energy_kwh": energy, "minutes_with_data": int(row["minutes_with_data"]),
                "is_complete": row["is_complete"] == "true", "grain": grain,
                "PK": consumption_key(row["household_id"], grain), "SK": timestamp_key(timestamp),
                "schema_version": 2, "is_demo": False, "data_source": "gold", "dataset_id": DATASET,
                "snapshot_id": manifest["snapshot_id"], "source_clock_note": CLOCK_NOTE}
            validate_gold_item(item)
            if row["household_id"] != "household-1" or timestamp != START + timedelta(minutes=minutes * len(rows)):
                raise ValueError("Missing, duplicate, unordered or out-of-window bucket")
            rows.append(item)
        if len(rows) != count or entry["row_count"] != count:
            raise ValueError("Unexpected bounded export row count")
        canonical["grains"][grain] = [[r["household_id"],
            datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")).replace(tzinfo=None).isoformat(),
            str(r["energy_kwh"].normalize()) if r["energy_kwh"] is not None else None,
            r["minutes_with_data"], r["is_complete"]] for r in rows]
        rows_by_grain[grain] = rows
    snapshot = "sha256:" + digest(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode())
    if manifest["snapshot_id"] != snapshot:
        raise ValueError("Normalized source snapshot identity differs")
    for day in rows_by_grain["daily"]:
        hours = [r for r in rows_by_grain["hourly"] if r["timestamp"][:10] == day["timestamp"][:10]]
        energies = [r["energy_kwh"] for r in hours if r["energy_kwh"] is not None]
        total = sum(energies, Decimal(0)) if energies else None
        daily = day["energy_kwh"]
        if (sum(r["minutes_with_data"] for r in hours) != day["minutes_with_data"]
                or (total is None) != (daily is None)
                or (total is not None and abs(total - daily) > Decimal("0.000001"))):
            raise ValueError("Hourly/daily energy or coverage does not reconcile")
    return {**manifest, "manifest_sha256": digest(raw_manifest)}, rows_by_grain["hourly"] + rows_by_grain["daily"]
