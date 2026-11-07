"""Contract tests emphasize meaningful boundaries and cross-endpoint consistency."""

from datetime import datetime, timedelta
import socket

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

WEEK = {"household_id": "household-1", "start": "2009-06-01T00:00:00Z", "end": "2009-06-08T00:00:00Z"}
TARGET = {**WEEK, "start": "2009-06-08T00:00:00Z", "end": "2009-06-09T00:00:00Z"}


def test_health_and_openapi(client):
    """All planned routes are discoverable and the health check is honestly mock."""
    assert client.get("/health").json() == {"status": "ok", "data_mode": "mock", "is_demo": True}
    schema = client.get("/openapi.json").json()
    assert set(schema["paths"]) == {"/health", "/consumption", "/anomalies", "/forecast", "/chat"}


def test_default_mode_needs_no_configuration(monkeypatch):
    """Removing APP_DATA_MODE must still start a working offline application."""
    monkeypatch.delenv("APP_DATA_MODE")
    with TestClient(create_app()) as client:
        assert client.get("/health").json()["data_mode"] == "mock"


def test_unsupported_mode_fails_clearly(monkeypatch):
    """A typo or premature AWS setting must never silently produce mock results."""
    monkeypatch.setenv("APP_DATA_MODE", "aws")
    with pytest.raises(RuntimeError, match="Only APP_DATA_MODE=mock"):
        with TestClient(create_app()):
            pass


def test_coherent_week_and_computed_daily_totals(client):
    """Check continuity, a known independent total, and daily/hourly agreement."""
    hourly_response = client.get("/consumption", params=WEEK)
    assert hourly_response.status_code == 200
    hourly = hourly_response.json()
    daily = client.get("/consumption", params={**WEEK, "grain": "daily"}).json()
    assert len(hourly["items"]) == 168
    assert len(daily["items"]) == 7
    timestamps = [datetime.fromisoformat(item["timestamp"]) for item in hourly["items"]]
    assert all(b - a == timedelta(hours=1) for a, b in zip(timestamps, timestamps[1:]))
    for index, day in enumerate(daily["items"]):
        expected = sum(row["energy_kwh"] for row in hourly["items"][index * 24:(index + 1) * 24])
        assert day["energy_kwh"] == pytest.approx(expected)
    assert [day["energy_kwh"] for day in daily["items"]] == [13.46, 16.44, 14.42, 18.00, 15.38, 17.76, 16.34]
    # Explicit fixture arithmetic, independent of repository constants.
    assert hourly["items"][0]["energy_kwh"] == 0.30
    assert hourly["items"][42]["energy_kwh"] == 3.67
    assert hourly["covered_start"] == WEEK["start"]
    assert hourly["covered_end"] == WEEK["end"]
    assert hourly["units"] == {"energy_kwh": "kWh"}
    assert hourly["next_cursor"] is None and hourly["is_demo"] is True
    assert "source dataset timezone is unconfirmed" in hourly["timezone_note"]
    assert client.get("/consumption", params=WEEK).json() == hourly


@pytest.mark.parametrize("path,window,start,end", [
    ("/consumption", WEEK, "2009-06-01T00:00:00Z", "2009-06-01T01:00:00Z"),
    ("/anomalies", WEEK, "2009-06-02T18:00:00Z", "2009-06-04T19:00:00Z"),
    ("/forecast", TARGET, "2009-06-08T00:00:00Z", "2009-06-08T01:00:00Z"),
])
def test_inclusive_start_exclusive_end(client, path, window, start, end):
    """Each read endpoint must include its start record and exclude its end record."""
    response = client.get(path, params={**window, "start": start, "end": end})
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["timestamp"] == start


@pytest.mark.parametrize("path", ["/consumption", "/anomalies", "/forecast"])
@pytest.mark.parametrize("changes", [
    {"start": "2009-07-01T00:00:00Z", "end": "2009-07-02T00:00:00Z"},
    {"household_id": "household-2"},
])
def test_valid_empty_windows(client, path, changes):
    """Missing data is a successful empty result, distinct from invalid input."""
    response = client.get(path, params={**WEEK, **changes})
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["covered_start"] is None and body["covered_end"] is None
    assert body["next_cursor"] is None and body["is_demo"] is True


@pytest.mark.parametrize("path", ["/consumption", "/anomalies", "/forecast"])
@pytest.mark.parametrize("changes", [
    {"end": WEEK["start"]}, {"end": "2009-05-31T00:00:00Z"},
    {"start": "garbage"}, {"start": "2009-06-01"},
    {"start": "2009-06-01T00:00:00"}, {"household_id": " "},
    {"household_id": "household-0"}, {"unexpected": "value"},
])
def test_invalid_read_input_is_422(client, path, changes):
    """Validation belongs at the HTTP boundary, before any storage work."""
    response = client.get(path, params={**WEEK, **changes})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize("path", ["/consumption", "/anomalies", "/forecast"])
def test_required_read_parameters(client, path):
    """No implicit household or current-date window hides missing inputs."""
    assert client.get(path).status_code == 422


@pytest.mark.parametrize("changes", [
    {"grain": "weekly"}, {"grain": "daily", "start": "2009-06-01T00:30:00Z"},
    {"grain": "daily", "end": "2009-06-07T23:00:00Z"},
])
def test_invalid_consumption_grain(client, changes):
    """Daily totals require full UTC dates; unsupported grains are rejected."""
    assert client.get("/consumption", params={**WEEK, **changes}).status_code == 422


def test_explicit_offsets_are_normalized(client):
    """The same instants expressed at +02:00 must return identical results."""
    offset = {**WEEK, "start": "2009-06-01T02:00:00+02:00", "end": "2009-06-08T02:00:00+02:00", "grain": "daily"}
    assert client.get("/consumption", params=offset).json() == client.get(
        "/consumption", params={**WEEK, "grain": "daily"}).json()


def test_anomalies_match_consumption(client):
    """Anomalies must reference actual fixture readings with consistent units."""
    readings = {row["timestamp"]: row for row in client.get("/consumption", params=WEEK).json()["items"]}
    result = client.get("/anomalies", params=WEEK).json()
    assert len(result["items"]) == 3
    for anomaly in result["items"]:
        assert anomaly["observed_kwh"] == readings[anomaly["timestamp"]]["energy_kwh"]
        assert anomaly["observed_kwh"] > anomaly["expected_kwh"]
        assert 0 <= anomaly["score"] <= 1
    assert result["units"]["score"] == "unitless"


def test_forecast_origin_targets_and_values(client):
    """The forecast targets the next 24 hours and only reuses earlier observations."""
    result = client.get("/forecast", params=TARGET).json()
    history = client.get("/consumption", params=WEEK).json()["items"]
    assert len(result["items"]) == 24
    assert result["forecast_origin"] == TARGET["start"]
    assert result["target_start"] == TARGET["start"]
    assert result["target_end"] == TARGET["end"]
    assert result["covered_end"] == TARGET["end"]
    assert [row["energy_kwh"] for row in result["items"]] == [row["energy_kwh"] for row in history[-24:]]
    assert all(row["forecast_origin"] <= row["timestamp"] for row in result["items"])
    assert all(row["method"] == "illustrative_previous_day" for row in result["items"])
    assert "not a trained model" in result["note"]


@pytest.mark.parametrize("request_type", ["chat", "weekly_summary"])
def test_honest_assistant_placeholders(client, request_type):
    """Both assistant actions are explicitly disconnected and provide no citations."""
    body = {**WEEK, "request_type": request_type}
    if request_type == "chat":
        body["message"] = "Why was usage high?"
    response = client.post("/chat", json=body)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "placeholder" and result["is_demo"] is True
    assert result["assistant_connected"] is False
    assert result["citations"] == []
    # The current API uses neutral wording; the important contract is that the
    # response openly identifies the placeholder and disconnected assistant.
    assert "placeholder" in result["answer"].lower()
    assert "Bedrock is not connected" in result["answer"]


@pytest.mark.parametrize("changes", [
    {}, {"message": "   "}, {"message": "a" * 2001},
    {"request_type": "unsupported", "message": "Hi"},
    {"request_type": "weekly_summary", "end": WEEK["start"]},
    {"message": "Hi", "start": 1243814400},
    {"message": "Hi", "start": "2009-06-01T00:00:00"},
])
def test_invalid_chat_input(client, changes):
    """Body validation covers questions, feature names, and shared time rules."""
    assert client.post("/chat", json={**WEEK, **changes}).status_code == 422


def test_network_guard_blocks_application_connections():
    """Prove the offline fixture rejects both external and localhost app calls."""
    with socket.socket() as connection:
        for address in (("example.com", 443), ("127.0.0.1", 8000)):
            with pytest.raises(AssertionError, match="outbound network"):
                connection.connect(address)
