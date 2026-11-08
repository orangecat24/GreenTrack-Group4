"""Offline storage contract tests using genuine SDK request/response validation."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import boto3
import pytest
from botocore.stub import Stubber
from fastapi.testclient import TestClient

from app import dynamodb_repository
from app.dynamodb_items import (
    anomaly_item, consumption_item, consumption_key, forecast_item, forecast_key,
    household_key, serialize_item, timestamp_key,
)
from app.dynamodb_repository import DynamoDBRepository
from app.main import create_app
from app.models import ConsumptionQuery, Window
from app.repository import MockRepository, RepositoryError
from app.service import EnergyService
from app.storage import DynamoSettings
from seed_demo import fixture_items, main, write_items

SETTINGS = DynamoSettings("eu-central-1", "demo-consumption", "demo-anomalies", "demo-forecasts")
WEEK = {"household_id": "household-1", "start": "2009-06-01T00:00:00Z", "end": "2009-06-08T00:00:00Z"}
TARGET = {**WEEK, "start": "2009-06-08T00:00:00Z", "end": "2009-06-09T00:00:00Z"}
CLI = ["--region", SETTINGS.region, "--consumption-table", SETTINGS.consumption_table,
       "--anomalies-table", SETTINGS.anomalies_table, "--forecasts-table", SETTINGS.forecasts_table]


@pytest.fixture
def aws_client():
    """Never resolve actual credentials or use an AWS endpoint, even by accident."""
    session = boto3.session.Session(aws_access_key_id="test", aws_secret_access_key="test",
                                   aws_session_token="test", region_name=SETTINGS.region)
    client = session.client("dynamodb", endpoint_url="http://127.0.0.1:9")
    yield client
    client.close()


def expected_query(table, pk, start="2009-06-01T00:00:00.000000Z", end="2009-06-07T23:59:59.999999Z"):
    """Describe the actual DynamoDB Query contract, including the exclusive end."""
    return {
        "TableName": table,
        "KeyConditionExpression": "#pk = :pk AND #sk BETWEEN :start AND :end",
        "ExpressionAttributeNames": {"#pk": "PK", "#sk": "SK"},
        "ExpressionAttributeValues": {":pk": {"S": pk}, ":start": {"S": start}, ":end": {"S": end}},
        "ScanIndexForward": True, "ConsistentRead": True, "Limit": 250,
    }


@pytest.mark.parametrize("kind", ["hourly", "daily", "anomalies", "forecast"])
def test_storage_mapping_preserves_response_contract(aws_client, kind):
    """The same synthetic data must produce identical public JSON in either store."""
    mock = MockRepository()
    repo = DynamoDBRepository(aws_client, SETTINGS)
    if kind in ("hourly", "daily"):
        query = ConsumptionQuery(**WEEK, grain=kind)
        points = mock.consumption(query)
        items = [serialize_item(consumption_item(point, kind)) for point in points]
        params = expected_query(SETTINGS.consumption_table, consumption_key("household-1", kind))
        method = "consumption"
    elif kind == "anomalies":
        query = Window(**WEEK)
        items = [serialize_item(anomaly_item(point)) for point in mock.anomalies(query)]
        params = expected_query(SETTINGS.anomalies_table, household_key("household-1"))
        method = "anomalies"
    else:
        query = Window(**TARGET)
        items = [serialize_item(forecast_item(point)) for point in mock.forecast(query)]
        params = expected_query(SETTINGS.forecasts_table, forecast_key("household-1", SETTINGS.forecast_origin),
                                "2009-06-08T00:00:00.000000Z", "2009-06-08T23:59:59.999999Z")
        method = "forecast"
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": items}, params)
        actual = getattr(EnergyService(repo), method)(query).model_dump(mode="json")
        expected = getattr(EnergyService(mock), method)(query).model_dump(mode="json")
        assert actual == expected
        assert actual["is_demo"] is True and actual["next_cursor"] is None
        stub.assert_no_pending_responses()


def test_query_consumes_pages_including_empty_page_with_cursor(aws_client):
    """A continuation key, not the current item count, determines completion."""
    query = ConsumptionQuery(**WEEK)
    points = MockRepository().consumption(query)[:2]
    items = [serialize_item(consumption_item(point, "hourly")) for point in points]
    params = expected_query(SETTINGS.consumption_table, consumption_key("household-1", "hourly"))
    cursor1 = {name: items[0][name] for name in ("PK", "SK")}
    cursor2 = {**cursor1, "SK": {"S": "2009-06-01T00:30:00.000000Z"}}
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": [items[0]], "LastEvaluatedKey": cursor1}, params)
        stub.add_response("query", {"Items": [], "LastEvaluatedKey": cursor2}, {**params, "ExclusiveStartKey": cursor1})
        stub.add_response("query", {"Items": [items[1]]}, {**params, "ExclusiveStartKey": cursor2})
        assert DynamoDBRepository(aws_client, SETTINGS).consumption(query) == points
        stub.assert_no_pending_responses()


def test_query_preserves_microsecond_boundaries(aws_client):
    """Subtracting a microsecond must still include a one-microsecond window."""
    query = ConsumptionQuery(**{**WEEK, "start": "2009-06-01T00:00:00.000001Z", "end": "2009-06-01T00:00:00.000002Z"})
    original = MockRepository().consumption(ConsumptionQuery(**WEEK))[0]
    point = original.model_copy(update={"timestamp": query.start})
    params = expected_query(SETTINGS.consumption_table, consumption_key("household-1", "hourly"),
                            "2009-06-01T00:00:00.000001Z", "2009-06-01T00:00:00.000001Z")
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": [serialize_item(consumption_item(point, "hourly"))]}, params)
        assert DynamoDBRepository(aws_client, SETTINGS).consumption(query) == (point,)


def test_later_query_page_failure_does_not_return_partial_results(aws_client):
    """A successful first page is not a complete response if the next page fails."""
    query = ConsumptionQuery(**WEEK)
    point = MockRepository().consumption(query)[0]
    item = serialize_item(consumption_item(point, "hourly"))
    cursor = {name: item[name] for name in ("PK", "SK")}
    params = expected_query(SETTINGS.consumption_table, consumption_key("household-1", "hourly"))
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": [item], "LastEvaluatedKey": cursor}, params)
        stub.add_client_error("query", service_error_code="InternalServerError", http_status_code=500,
                              expected_params={**params, "ExclusiveStartKey": cursor})
        with pytest.raises(RepositoryError, match="read unavailable"):
            DynamoDBRepository(aws_client, SETTINGS).consumption(query)
        stub.assert_no_pending_responses()


def test_forecast_reader_rejects_wrong_origin_under_an_active_run_key(aws_client):
    """Target times alone cannot validate a forecast stored under the wrong origin."""
    point = MockRepository().forecast(Window(**TARGET))[0]
    item = forecast_item(point)
    item["forecast_origin"] = "2009-06-07T00:00:00Z"
    params = expected_query(SETTINGS.forecasts_table, forecast_key("household-1", SETTINGS.forecast_origin),
                            "2009-06-08T00:00:00.000000Z", "2009-06-08T23:59:59.999999Z")
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": [serialize_item(item)]}, params)
        with pytest.raises(RepositoryError, match="24-hour origin"):
            DynamoDBRepository(aws_client, SETTINGS).forecast(Window(**TARGET))
        stub.assert_no_pending_responses()


@pytest.mark.parametrize("method,table,pk", [
    ("consumption", SETTINGS.consumption_table, consumption_key("household-2", "hourly")),
    ("anomalies", SETTINGS.anomalies_table, household_key("household-2")),
    ("forecast", SETTINGS.forecasts_table, forecast_key("household-2", SETTINGS.forecast_origin)),
])
def test_valid_empty_query_has_null_coverage(aws_client, method, table, pk):
    """A missing household/window remains an empty success, not fake fallback data."""
    query = ConsumptionQuery(**{**WEEK, "household_id": "household-2"})
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": []}, expected_query(table, pk))
        response = getattr(EnergyService(DynamoDBRepository(aws_client, SETTINGS)), method)(query)
        assert response.items == []
        assert response.covered_start is None and response.covered_end is None
        assert response.is_demo is True


@pytest.mark.parametrize("changes", [
    {"is_demo": False}, {"is_demo": None}, {"schema_version": 99},
    {"household_id": "household-2"}, {"PK": "wrong"}, {"SK": "wrong"},
    {"energy_kwh": -1}, {"grain": "daily"}, {"interval_end": WEEK["start"]},
])
def test_invalid_or_non_demo_storage_rows_fail_closed(aws_client, changes):
    """Bad stored data must not acquire a trusted synthetic-demo label."""
    query = ConsumptionQuery(**WEEK)
    point = MockRepository().consumption(query)[0]
    item = {**consumption_item(point, "hourly"), **changes}
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": [serialize_item(item)]},
                          expected_query(SETTINGS.consumption_table, consumption_key("household-1", "hourly")))
        with pytest.raises(RepositoryError):
            DynamoDBRepository(aws_client, SETTINGS).consumption(query)
        stub.assert_no_pending_responses()


def configure_dynamodb(monkeypatch, client):
    """Select storage with only public configuration and an injected offline client."""
    monkeypatch.setenv("APP_DATA_MODE", "dynamodb")
    monkeypatch.setenv("DYNAMODB_REGION", SETTINGS.region)
    monkeypatch.setenv("DYNAMODB_CONSUMPTION_TABLE", SETTINGS.consumption_table)
    monkeypatch.setenv("DYNAMODB_ANOMALIES_TABLE", SETTINGS.anomalies_table)
    monkeypatch.setenv("DYNAMODB_FORECASTS_TABLE", SETTINGS.forecasts_table)
    monkeypatch.delenv("DYNAMODB_FORECAST_ORIGIN", raising=False)
    monkeypatch.setattr(dynamodb_repository, "create_client", lambda settings: client)


@pytest.mark.parametrize("code", ["ResourceNotFoundException", "AccessDeniedException", "ProvisionedThroughputExceededException"])
def test_storage_failure_returns_safe_503_without_mock_fallback(aws_client, monkeypatch, code):
    """An unavailable table, denied access, or exhausted SDK retries is retryable HTTP failure."""
    configure_dynamodb(monkeypatch, aws_client)
    with Stubber(aws_client) as stub:
        stub.add_client_error("query", service_error_code=code, service_message="internal diagnostic only", http_status_code=400,
                              expected_params=expected_query(SETTINGS.consumption_table, consumption_key("household-1", "hourly")))
        with TestClient(create_app()) as client:
            response = client.get("/consumption", params=WEEK)
        assert response.status_code == 503
        assert "read unavailable" in response.json()["detail"]
        assert "internal diagnostic" not in response.text
        assert SETTINGS.consumption_table not in response.text
        stub.assert_no_pending_responses()


def test_dynamodb_mode_returns_daily_json_through_actual_routes(aws_client, monkeypatch):
    """Exercise mode selection, request validation, the adapter, and serialization together."""
    configure_dynamodb(monkeypatch, aws_client)
    query = ConsumptionQuery(**{**WEEK, "end": "2009-06-02T00:00:00Z"}, grain="daily")
    point = MockRepository().consumption(query)[0]
    with Stubber(aws_client) as stub:
        stub.add_response("query", {"Items": [serialize_item(consumption_item(point, "daily"))]},
                          expected_query(SETTINGS.consumption_table, consumption_key("household-1", "daily"),
                                         end="2009-06-01T23:59:59.999999Z"))
        with TestClient(create_app()) as client:
            response = client.get("/consumption", params={**WEEK, "end": "2009-06-02T00:00:00Z", "grain": "daily"})
        assert response.status_code == 200
        assert response.json() == EnergyService(MockRepository()).consumption(query).model_dump(mode="json")
        stub.assert_no_pending_responses()


def test_mock_path_never_constructs_aws_client(monkeypatch):
    """Default mock startup and reads must bypass every SDK client factory."""
    forbidden = Mock(side_effect=AssertionError("Mock mode constructed an AWS client"))
    monkeypatch.setattr(boto3.session.Session, "client", forbidden)
    monkeypatch.delenv("APP_DATA_MODE")
    with TestClient(create_app()) as client:
        assert client.get("/consumption", params=WEEK).status_code == 200
    forbidden.assert_not_called()


def test_dynamodb_startup_does_not_seed_or_query(aws_client, monkeypatch):
    """No Stubber responses are queued: any startup AWS operation fails this test."""
    configure_dynamodb(monkeypatch, aws_client)
    with Stubber(aws_client), TestClient(create_app()) as client:
        # Preserve the existing health contract: these are still mock/demo data,
        # and /health is process health rather than an AWS readiness check.
        assert client.get("/health").json() == {"status": "ok", "data_mode": "mock", "is_demo": True}


def test_dynamodb_requires_explicit_configuration_before_client_creation(monkeypatch):
    """Missing table/Region settings cannot silently use profile defaults."""
    monkeypatch.setenv("APP_DATA_MODE", "dynamodb")
    for name in ("DYNAMODB_REGION", "DYNAMODB_CONSUMPTION_TABLE", "DYNAMODB_ANOMALIES_TABLE", "DYNAMODB_FORECASTS_TABLE"):
        monkeypatch.delenv(name, raising=False)
    forbidden = Mock(side_effect=AssertionError("Invalid settings constructed a client"))
    monkeypatch.setattr(dynamodb_repository, "create_client", forbidden)
    with pytest.raises(ValueError, match="Region"):
        with TestClient(create_app()):
            pass
    forbidden.assert_not_called()


def test_loader_keys_are_idempotent_and_grains_origins_do_not_collide():
    """Rerunning replaces the same 202 keys; distinct grains/runs stay separate."""
    first, second = fixture_items(SETTINGS), fixture_items(SETTINGS)
    assert first == second
    assert [len(items) for items in first.values()] == [175, 3, 24]
    for items in first.values():
        keys = {(item["PK"]["S"], item["SK"]["S"]) for item in items}
        assert len(keys) == len(items)
        assert all(item["is_demo"] == {"BOOL": True} for item in items)
    hourly = first[SETTINGS.consumption_table][0]
    assert hourly["PK"] == {"S": "HOUSEHOLD#household-1#GRAIN#hourly"}
    assert hourly["SK"] == {"S": "2009-06-01T00:00:00.000000Z"}
    assert hourly["energy_kwh"] == {"N": "0.3"}
    assert first[SETTINGS.consumption_table][168]["energy_kwh"] == {"N": "13.46"}
    point = MockRepository().forecast(Window(**TARGET))[0]
    earlier_run = point.model_copy(update={"forecast_origin": point.forecast_origin - timedelta(days=1)})
    assert forecast_item(point)["PK"] != forecast_item(earlier_run)["PK"]
    assert forecast_item(point)["SK"] == forecast_item(earlier_run)["SK"]
    assert timestamp_key(datetime(2009, 6, 1, tzinfo=UTC)) == hourly["SK"]["S"]


@pytest.mark.parametrize("flags", [[], ["--dry-run"]])
def test_loader_dry_run_never_constructs_a_client(flags, capsys):
    """Both implicit and explicit dry runs preview everything without touching AWS."""
    forbidden = Mock(side_effect=AssertionError("Dry run constructed an AWS client"))
    assert main([*CLI, *flags], client_factory=forbidden) == 0
    assert '"total_items": 202' in capsys.readouterr().out
    forbidden.assert_not_called()


@pytest.mark.parametrize("args", [[], [*CLI, "--write", "--dry-run"],
    ["--region", "eu-central-1", "--consumption-table", "same", "--anomalies-table", "same", "--forecasts-table", "same"]])
def test_loader_rejects_missing_or_ambiguous_write_configuration(args):
    """A write needs valid, distinct, explicit destinations and an unambiguous flag."""
    forbidden = Mock(side_effect=AssertionError("Invalid CLI constructed a client"))
    with pytest.raises(SystemExit) as error:
        main(args, client_factory=forbidden)
    assert error.value.code == 2
    forbidden.assert_not_called()


def test_loader_retries_only_unprocessed_items(aws_client):
    """HTTP 200 does not imply the entire batch was written successfully."""
    items = fixture_items(SETTINGS)[SETTINGS.consumption_table][:2]
    both = {SETTINGS.consumption_table: [{"PutRequest": {"Item": item}} for item in items]}
    pending = {SETTINGS.consumption_table: [both[SETTINGS.consumption_table][1]]}
    sleep = Mock()
    with Stubber(aws_client) as stub:
        stub.add_response("batch_write_item", {"UnprocessedItems": pending}, {"RequestItems": both})
        stub.add_response("batch_write_item", {}, {"RequestItems": pending})
        assert write_items(aws_client, {SETTINGS.consumption_table: items}, sleep=sleep) == 2
        sleep.assert_called_once()
        stub.assert_no_pending_responses()


def test_loader_bounds_unprocessed_item_retries(aws_client):
    """Stop on a persistently throttled batch rather than retrying forever."""
    items = fixture_items(SETTINGS)[SETTINGS.consumption_table][:1]
    pending = {SETTINGS.consumption_table: [{"PutRequest": {"Item": items[0]}}]}
    with Stubber(aws_client) as stub:
        for _ in range(4):
            stub.add_response("batch_write_item", {"UnprocessedItems": pending}, {"RequestItems": pending})
        with pytest.raises(RepositoryError, match="retry limit"):
            write_items(aws_client, {SETTINGS.consumption_table: items}, sleep=lambda _: None)
        stub.assert_no_pending_responses()


def test_loader_batches_full_seed_and_replays_stable_keys(aws_client):
    """Two complete runs send the same puts, each respecting AWS's 25-item cap."""
    tables = fixture_items(SETTINGS)
    flat = [(table, item) for table, items in tables.items() for item in items]
    with Stubber(aws_client) as stub:
        for _ in range(2):
            for offset in range(0, len(flat), 25):
                batch = {}
                for table, item in flat[offset:offset + 25]:
                    batch.setdefault(table, []).append({"PutRequest": {"Item": item}})
                stub.add_response("batch_write_item", {}, {"RequestItems": batch})
        assert write_items(aws_client, tables) == 202
        assert write_items(aws_client, fixture_items(SETTINGS)) == 202
        stub.assert_no_pending_responses()


def test_loader_write_failure_is_nonzero_and_does_not_leak_aws_diagnostics(aws_client, capsys):
    """A partial write failure needs a failed CLI exit, not a success count."""
    with Stubber(aws_client) as stub:
        stub.add_client_error("batch_write_item", service_error_code="AccessDeniedException",
                              service_message="internal diagnostic only", http_status_code=400)
        assert main([*CLI, "--write"], client_factory=lambda settings: aws_client) == 1
        output = capsys.readouterr()
        assert "Seed failed" in output.err
        assert "internal diagnostic" not in output.err
        assert "Wrote 202" not in output.out
