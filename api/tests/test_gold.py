"""Offline gold integration tests using invented source-shaped records, not UCI evidence."""

import csv
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
from unittest.mock import Mock

from botocore.stub import Stubber
from fastapi.testclient import TestClient
import pytest

from app.conditional_write import WriteConflict, conditional_put, same_item
from app.dynamodb_items import consumption_key, serialize_item
from app.dynamodb_repository import DynamoDBRepository
from app.gold import CLOCK_NOTE, DATASET, START, load_export, validate_gold_item
from app.main import create_app
from app.models import ConsumptionQuery, ForecastPoint, Window
from app.repository import RepositoryError
from app.service import EnergyService
from app.storage import DynamoSettings
from load_gold import main, preview
from test_dynamodb import aws_client, configure_dynamodb, expected_query, put_params, WEEK

TABLE = "g4-greentrack-dev-consumption"
SETTINGS = DynamoSettings("eu-central-1", TABLE, "demo-anomalies", "demo-forecasts", data_source="gold")


def make_export(directory, overrides=None, daily_delta=Decimal(0)):
    """Build a full *invented* 1-kWh/hour week, with optional missing/partial hours."""
    overrides = overrides or {}
    source = []
    for i in range(168):
        energy, minutes = overrides.get(i, (Decimal(1), 60))
        source.append(["household-1", START.replace(tzinfo=None) + timedelta(hours=i), energy, minutes, minutes == 60])
    days = []
    for i in range(7):
        hours = source[i * 24:(i + 1) * 24]
        energies = [r[2] for r in hours if r[2] is not None]
        minutes = sum(r[3] for r in hours)
        days.append(["household-1", hours[0][1], sum(energies, Decimal(0)) if energies else None, minutes, minutes == 1440])
    if days[0][2] is not None:
        days[0][2] += daily_delta
    manifest = {"export_manifest_version": 1, "account": "886565871385", "region": "eu-central-1",
        "household_id": "household-1", "source_contract_version": "v1", "dataset_id": DATASET,
        "requested_start": WEEK["start"], "requested_end": WEEK["end"], "source_clock_note": CLOCK_NOTE, "exports": {}}
    canonical = {"dataset_id": DATASET, "source_contract_version": "v1", "household_id": "household-1",
                 "start": WEEK["start"], "end": WEEK["end"], "grains": {}}
    for grain, rows in (("hourly", source), ("daily", days)):
        path = directory / f"{grain}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["household_id", "period_start", "energy_kwh", "minutes_with_data", "is_complete"])
            for household, clock, energy, minutes, complete in rows:
                writer.writerow([household, clock.isoformat(sep=" ") + ".000000 UTC",
                                 energy if energy is not None else "", minutes, str(complete).lower()])
        manifest["exports"][grain] = {"file": path.name, "table": f"g4_greentrack_dev_gold.{grain}_consumption",
            "row_count": len(rows), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "query_id": "00000000-0000-4000-8000-000000000001"}
        canonical["grains"][grain] = [[h, t.isoformat(), str(e.normalize()) if e is not None else None, n, c]
                                      for h, t, e, n, c in rows]
    manifest["snapshot_id"] = "sha256:" + hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    path = directory / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def cli(path):
    """Keep the reviewed destination explicit, even for an offline dry run."""
    return ["--manifest", str(path), "--region", "eu-central-1", "--consumption-table", TABLE]


def stub_table(stub):
    """Identity and schema are verified by DescribeTable, not inferred from names."""
    stub.add_response("describe_table", {"Table": {"TableArn": f"arn:aws:dynamodb:eu-central-1:886565871385:table/{TABLE}",
        "TableStatus": "ACTIVE", "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        "AttributeDefinitions": [{"AttributeName": "PK", "AttributeType": "S"}, {"AttributeName": "SK", "AttributeType": "S"}]}}, {"TableName": TABLE})


def stub_preview(stub, hourly=(), daily=()):
    """Preview must query both grains inside the exact half-open week."""
    for grain, rows in (("hourly", hourly), ("daily", daily)):
        stub.add_response("query", {"Items": list(rows)}, expected_query(TABLE, consumption_key("household-1", grain)))


def test_export_quality_totals_and_stable_keys(tmp_path):
    """Missing hours remain null; partial observations retain energy and coverage."""
    path = make_export(tmp_path, {0: (None, 0), 1: (Decimal("0.5"), 30)})
    manifest, items = load_export(path)
    assert len(items) == 175 and load_export(path)[1] == items
    assert items[0]["energy_kwh"] is None and items[0]["minutes_with_data"] == 0
    assert items[1]["energy_kwh"] == Decimal("0.5") and not items[1]["is_complete"]
    assert items[168]["energy_kwh"] == Decimal("22.5")
    assert items[168]["minutes_with_data"] == 1350 and not items[168]["is_complete"]
    assert items[0]["PK"] != items[168]["PK"] and items[0]["SK"] == items[168]["SK"]
    assert all(r["snapshot_id"] == manifest["snapshot_id"] and r["is_demo"] is False for r in items)


@pytest.mark.parametrize("mutation", ["csv", "checksum", "snapshot", "window", "source", "path", "daily_count"])
def test_whole_input_validation_precedes_client_creation(tmp_path, mutation):
    """Corruption in the second grain must also prevent even a first write/client."""
    path = make_export(tmp_path)
    m = json.loads(path.read_text())
    if mutation == "csv": (tmp_path / "daily.csv").write_text("broken")
    elif mutation == "checksum": m["exports"]["daily"]["sha256"] = "0" * 64
    elif mutation == "snapshot": m["snapshot_id"] = "sha256:" + "0" * 64
    elif mutation == "window": m["requested_end"] = "2009-06-09T00:00:00Z"
    elif mutation == "source": m["dataset_id"] = "synthetic"
    elif mutation == "path": m["exports"]["hourly"]["file"] = "../other.csv"
    else: m["exports"]["daily"]["row_count"] = 8
    path.write_text(json.dumps(m))
    forbidden = Mock(side_effect=AssertionError("Invalid export constructed client"))
    assert main([*cli(path), "--check-existing", "--report", str(tmp_path / "report.json")], forbidden) == 1
    forbidden.assert_not_called()


@pytest.mark.parametrize("change", [{"minutes_with_data": 61}, {"minutes_with_data": -1},
    {"is_complete": False}, {"is_complete": "true"}, {"energy_kwh": None},
    {"energy_kwh": float("nan")}, {"energy_kwh": -1}, {"energy_kwh": True},
    {"energy_kwh": "1"}, {"minutes_with_data": "60"}, {"schema_version": 1},
    {"is_demo": True}, {"dataset_id": "unknown"}, {"snapshot_id": "unknown"},
    {"interval_end": "2009-06-01T02:00:00Z"}, {"SK": "2009-06-02T00:00:00.000000Z"}])
def test_reader_rejects_inconsistent_records(tmp_path, change):
    """A source label alone is insufficient to trust malformed real records."""
    _, items = load_export(make_export(tmp_path))
    with pytest.raises(ValueError): validate_gold_item({**items[0], **change})


@pytest.mark.parametrize("flags", [[], ["--dry-run"]])
def test_default_dry_run_is_offline(tmp_path, flags, capsys):
    """No SDK client is constructed for either kind of offline dry run."""
    forbidden = Mock(side_effect=AssertionError("Dry run constructed client"))
    assert main([*cli(make_export(tmp_path)), *flags], forbidden) == 0
    assert '"total_items": 175' in capsys.readouterr().out
    forbidden.assert_not_called()


def test_routes_gold_health_null_empty_and_unavailable_outputs(tmp_path, aws_client, monkeypatch):
    """Actual routes retain gold provenance for empty windows and never query models."""
    _, items = load_export(make_export(tmp_path, {0: (None, 0)}))
    configure_dynamodb(monkeypatch, aws_client)
    monkeypatch.setenv("APP_DATA_SOURCE", "gold")
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": [serialize_item(items[0])]}, expected_query("demo-consumption", consumption_key("household-1", "hourly")))
        stub.add_response("query", {"Items": []}, expected_query("demo-consumption", consumption_key("household-1", "daily")))
        with TestClient(create_app()) as client:
            assert client.get("/health").json() == {"status": "ok", "data_mode": "dynamodb", "data_source": "gold", "is_demo": False}
            data = client.get("/consumption", params=WEEK).json()
            assert data["items"][0]["energy_kwh"] is None and data["is_demo"] is False
            assert data["items"][0]["minutes_with_data"] == 0
            empty = client.get("/consumption", params={**WEEK, "grain": "daily"}).json()
            assert empty["items"] == [] and empty["covered_start"] is None
            assert empty["data_source"] == "gold" and empty["is_demo"] is False
            for endpoint in ("anomalies", "forecast"):
                response = client.get('/' + endpoint, params=WEEK).json()
                assert response["status"] == "unavailable" and response["items"] == []
                assert response["data_source"] == "unavailable" and response["is_demo"] is True
                if endpoint == "forecast": assert response["forecast_origin"] is None
            for request_type in ("chat", "weekly_summary"):
                chat = client.post("/chat", json={**WEEK, "request_type": request_type, "message": "hello"}).json()
                assert chat["status"] == "placeholder" and not chat["assistant_connected"] and not chat["citations"]
        stub.assert_no_pending_responses()


@pytest.mark.parametrize("source", ["gold", "unknown"])
def test_invalid_mock_source_fails_before_client(source, monkeypatch):
    """An inherited gold setting cannot relabel in-memory fixtures as real."""
    monkeypatch.setenv("APP_DATA_SOURCE", source)
    with pytest.raises(ValueError, match="APP_DATA_SOURCE"):
        with TestClient(create_app()): pass


def test_query_pagination_and_mixed_snapshot_rejection(tmp_path, aws_client):
    """An empty internal page is not the end, and different snapshots cannot mix."""
    _, items = load_export(make_export(tmp_path))
    params = expected_query(TABLE, consumption_key("household-1", "hourly"))
    cursor = {"PK": {"S": items[0]["PK"]}, "SK": {"S": items[0]["SK"]}}
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": [], "LastEvaluatedKey": cursor}, params)
        stub.add_response("query", {"Items": [serialize_item(items[0])]}, {**params, "ExclusiveStartKey": cursor})
        result = EnergyService(DynamoDBRepository(aws_client, SETTINGS)).consumption(ConsumptionQuery(**WEEK))
        assert len(result.items) == 1 and result.is_demo is False
        changed = {**items[1], "snapshot_id": "sha256:" + "f" * 64}
        stub.add_response("query", {"Items": [serialize_item(items[0]), serialize_item(changed)]}, params)
        with pytest.raises(RepositoryError): DynamoDBRepository(aws_client, SETTINGS).consumption(ConsumptionQuery(**WEEK))
        stub.assert_no_pending_responses()


def test_preview_conflicts_and_empty_internal_page(tmp_path, aws_client):
    """One conflicting record is visible; preview uses Query, never full-table Scan."""
    _, items = load_export(make_export(tmp_path))
    params = expected_query(TABLE, consumption_key("household-1", "hourly"))
    cursor = {k: serialize_item(items[0])[k] for k in ("PK", "SK")}
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": [], "LastEvaluatedKey": cursor}, params)
        stub.add_response("query", {"Items": [serialize_item(items[0]), serialize_item({**items[1], "is_demo": True})]}, {**params, "ExclusiveStartKey": cursor})
        stub.add_response("query", {"Items": []}, expected_query(TABLE, consumption_key("household-1", "daily")))
        result = preview(aws_client, TABLE, items)
        assert (result["new"], result["identical"], result["conflicts"]) == (173, 1, 1)
        stub.assert_no_pending_responses()


def test_seed_cannot_overwrite_a_gold_record(tmp_path, aws_client):
    """Even when preview races with a gold writer, the synthetic put must fail."""
    _, items = load_export(make_export(tmp_path))
    gold = serialize_item(items[0])
    seed = serialize_item({**items[0], "is_demo": True, "schema_version": 1})
    with Stubber(aws_client) as stub:
        stub.add_client_error("put_item", "ConditionalCheckFailedException", expected_params=put_params(TABLE, seed), modeled_fields={"Item": gold})
        with pytest.raises(WriteConflict): conditional_put(aws_client, TABLE, seed)
        stub.assert_no_pending_responses()


def test_partial_write_report_and_safe_resume(tmp_path, aws_client):
    """A failed run records its boundary; resume rechecks storage and skips success."""
    path = make_export(tmp_path)
    _, items = load_export(path)
    approved_path = tmp_path / "preview.json"
    with Stubber(aws_client) as stub:
        stub_table(stub); stub_preview(stub)
        assert main([*cli(path), "--check-existing", "--report", str(approved_path)], lambda _: aws_client) == 0
        approved_hash = hashlib.sha256(approved_path.read_bytes()).hexdigest()
        flags = ["--write", "--reviewed-preview", str(approved_path), "--approve-preview-sha256", approved_hash]
        stub_table(stub); stub_preview(stub)
        stub.add_response("put_item", {}, put_params(TABLE, serialize_item(items[0])))
        stub.add_client_error("put_item", "AccessDeniedException", service_message="DO NOT PRINT", expected_params=put_params(TABLE, serialize_item(items[1])))
        failed = tmp_path / "failed.json"
        assert main([*cli(path), *flags, "--report", str(failed)], lambda _: aws_client) == 1
        report = json.loads(failed.read_text())
        assert report["status"] == "failed" and report["written"] == 1
        assert report["keys"][-1]["outcome"] == "failed_or_unconfirmed"
        stub_table(stub); stub_preview(stub, [serialize_item(items[0])])
        stub.add_client_error("put_item", "ConditionalCheckFailedException", expected_params=put_params(TABLE, serialize_item(items[0])), modeled_fields={"Item": serialize_item(items[0])})
        for item in items[1:]: stub.add_response("put_item", {}, put_params(TABLE, serialize_item(item)))
        resumed = tmp_path / "resumed.json"
        assert main([*cli(path), *flags, "--report", str(resumed)], lambda _: aws_client) == 0
        result = json.loads(resumed.read_text())
        assert result["status"] == "complete" and result["written"] == 174 and result["skipped"] == 1
        stub.assert_no_pending_responses()


def test_write_requires_review_and_preserves_old_report(tmp_path):
    """Missing write review cannot create a client or destroy existing evidence."""
    path = make_export(tmp_path)
    report = tmp_path / "report.json"
    report.write_text("KEEP")
    forbidden = Mock(side_effect=AssertionError("Unreviewed write constructed client"))
    assert main([*cli(path), "--write", "--report", str(report)], forbidden) == 1
    assert report.read_text() == "KEEP"
    assert main([*cli(path), "--write"], forbidden) == 1
    forbidden.assert_not_called()


def test_all_missing_day_is_null_and_daily_disagreement_fails(tmp_path):
    """No observed minutes is null, while contradictory exported grains fail closed."""
    _, items = load_export(make_export(tmp_path, {i: (None, 0) for i in range(24)}))
    assert items[168]["energy_kwh"] is None and items[168]["minutes_with_data"] == 0
    assert items[168]["is_complete"] is False
    with pytest.raises(ValueError, match="reconcile"):
        load_export(make_export(tmp_path, daily_delta=Decimal(1)))


def test_gold_read_rejects_exclusive_end_record(tmp_path, aws_client):
    """Even a bad storage response cannot leak the next hour into a narrow window."""
    _, items = load_export(make_export(tmp_path))
    query = ConsumptionQuery(**{**WEEK, "end": "2009-06-01T01:00:00Z"})
    params = expected_query(TABLE, consumption_key("household-1", "hourly"), end="2009-06-01T00:59:59.999999Z")
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": [serialize_item(items[1])]}, params)
        with pytest.raises(RepositoryError): DynamoDBRepository(aws_client, SETTINGS).consumption(query)
        stub.assert_no_pending_responses()


def test_preview_wrong_account_prevents_query_and_write(tmp_path, aws_client):
    """Matching table names in another account are not sufficient authorization."""
    path = make_export(tmp_path)
    with Stubber(aws_client) as stub:
        stub.add_response("describe_table", {"Table": {"TableArn": f"arn:aws:dynamodb:eu-central-1:111111111111:table/{TABLE}",
            "TableStatus": "ACTIVE", "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "PK", "AttributeType": "S"}]}}, {"TableName": TABLE})
        assert main([*cli(path), "--check-existing", "--report", str(tmp_path / "preview.json")], lambda _: aws_client) == 1
        stub.assert_no_pending_responses()


def test_absent_old_value_after_conditional_failure_is_not_a_skip(tmp_path, aws_client):
    """A disappearing/racing record needs investigation, not a false success report."""
    _, items = load_export(make_export(tmp_path))
    raw = serialize_item(items[0])
    with Stubber(aws_client) as stub:
        stub.add_client_error("put_item", "ConditionalCheckFailedException", expected_params=put_params(TABLE, raw))
        stub.add_response("query", {"Items": []}, {"TableName": TABLE, "ConsistentRead": True,
            "KeyConditionExpression": "#pk = :pk AND #sk = :sk",
            "ExpressionAttributeNames": {"#pk": "PK", "#sk": "SK"},
            "ExpressionAttributeValues": {":pk": raw["PK"], ":sk": raw["SK"]}})
        with pytest.raises(WriteConflict): conditional_put(aws_client, TABLE, raw)
        stub.assert_no_pending_responses()


def test_ambiguous_success_can_be_skipped_without_overwrite(tmp_path, aws_client):
    """A retry after a server error safely recognizes a previously accepted item."""
    _, items = load_export(make_export(tmp_path))
    raw = serialize_item(items[0])
    with Stubber(aws_client) as stub:
        stub.add_client_error("put_item", "InternalServerError", expected_params=put_params(TABLE, raw))
        stub.add_client_error("put_item", "ConditionalCheckFailedException", expected_params=put_params(TABLE, raw), modeled_fields={"Item": raw})
        assert conditional_put(aws_client, TABLE, raw, sleep=lambda _: None) == "skipped"
        stub.assert_no_pending_responses()


def test_changed_preview_cannot_authorize_write(tmp_path, aws_client):
    """The explicit approval hash binds the reviewed destination/source preview."""
    path = make_export(tmp_path)
    report = tmp_path / "preview.json"
    with Stubber(aws_client) as stub:
        stub_table(stub); stub_preview(stub)
        assert main([*cli(path), "--check-existing", "--report", str(report)], lambda _: aws_client) == 0
    forbidden = Mock(side_effect=AssertionError("Changed preview constructed client"))
    assert main([*cli(path), "--write", "--reviewed-preview", str(report),
        "--approve-preview-sha256", "0" * 64, "--report", str(tmp_path / "write.json")], forbidden) == 1
    forbidden.assert_not_called()


def test_new_preview_conflict_stops_before_first_write(tmp_path, aws_client):
    """An earlier approval does not authorize a conflict introduced afterwards."""
    path = make_export(tmp_path)
    _, items = load_export(path)
    report = tmp_path / "preview.json"
    with Stubber(aws_client) as stub:
        stub_table(stub); stub_preview(stub)
        assert main([*cli(path), "--check-existing", "--report", str(report)], lambda _: aws_client) == 0
        fingerprint = hashlib.sha256(report.read_bytes()).hexdigest()
        stub_table(stub); stub_preview(stub, [serialize_item({**items[0], "schema_version": 1, "is_demo": True})])
        assert main([*cli(path), "--write", "--reviewed-preview", str(report), "--approve-preview-sha256", fingerprint,
            "--report", str(tmp_path / "write.json")], lambda _: aws_client) == 1
        stub.assert_no_pending_responses()  # No put_item may be attempted.


def test_gold_storage_error_is_503_without_diagnostics(aws_client, monkeypatch):
    """Gold authorization/storage failure must not turn into a successful empty result."""
    configure_dynamodb(monkeypatch, aws_client)
    monkeypatch.setenv("APP_DATA_SOURCE", "gold")
    with Stubber(aws_client) as stub:
        stub.add_client_error("query", "AccessDeniedException", service_message="PRIVATE DIAGNOSTIC",
            expected_params=expected_query("demo-consumption", consumption_key("household-1", "hourly")))
        with TestClient(create_app()) as client:
            response = client.get("/consumption", params=WEEK)
            assert response.status_code == 503 and "PRIVATE DIAGNOSTIC" not in response.text
        stub.assert_no_pending_responses()


def test_idempotency_preserves_dynamodb_attribute_types():
    """Equivalent numbers are identical; a numeric 0 must not stand in for false."""
    assert same_item({"energy": {"N": "1.00"}}, {"energy": {"N": "1"}})
    assert not same_item({"is_demo": {"N": "0"}}, {"is_demo": {"BOOL": False}})
