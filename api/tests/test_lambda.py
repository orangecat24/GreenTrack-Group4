"""Exercise the real Lambda adapter using API Gateway HTTP API v2 events offline."""

import base64
import json
from urllib.parse import urlencode

import boto3
import pytest
from mangum.exceptions import LifespanFailure

from app.lambda_handler import handler
from app.repository import MockRepository

WEEK = {"household_id": "household-1", "start": "2009-06-01T00:00:00Z", "end": "2009-06-08T00:00:00Z"}


def event(path, *, method="GET", query=None, body=None, encoded=False):
    """Model the gateway's payload v2 shape, including URL query and JSON body."""
    text = json.dumps(body) if body is not None else ""
    return {
        "version": "2.0", "routeKey": "$default", "rawPath": path,
        "rawQueryString": urlencode(query or {}),
        "headers": {"host": "example.execute-api.eu-central-1.amazonaws.com",
                    "x-forwarded-proto": "https", "content-type": "application/json"},
        "requestContext": {
            "stage": "$default", "requestId": "offline-test",
            "http": {"method": method, "path": path, "protocol": "HTTP/1.1",
                     "sourceIp": "127.0.0.1", "userAgent": "offline-test"},
        },
        "body": base64.b64encode(text.encode()).decode() if encoded else text,
        "isBase64Encoded": encoded,
    }


@pytest.fixture(autouse=True)
def no_aws_client(monkeypatch):
    """Network blocking is inherited from conftest; also forbid SDK construction."""
    def forbidden(*args, **kwargs):
        """Fail even before a credentials lookup or network attempt can occur."""
        raise AssertionError("The mock Lambda must not construct an AWS client")

    monkeypatch.setattr(boto3.session.Session, "client", forbidden)


def test_default_mock_health_and_https_redirect(monkeypatch):
    """Unset configuration still works, and redirects retain gateway HTTPS."""
    monkeypatch.delenv("APP_DATA_MODE")
    response = handler(event("/health"), {})
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"status": "ok", "data_mode": "mock", "is_demo": True}
    redirect = handler(event("/"), {})
    assert redirect["statusCode"] == 307
    assert redirect["headers"]["location"] == "https://example.execute-api.eu-central-1.amazonaws.com/docs"


@pytest.mark.parametrize("path,query,count", [
    ("/consumption", {**WEEK, "grain": "daily"}, 7),
    ("/anomalies", WEEK, 3),
    ("/forecast", {**WEEK, "start": "2009-06-08T00:00:00Z", "end": "2009-06-09T00:00:00Z"}, 24),
])
def test_gateway_queries_keep_existing_contract(path, query, count):
    """Actual adapter serialization preserves dates, items, units and provenance."""
    response = handler(event(path, query=query), {})
    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert len(data["items"]) == count
    assert data["is_demo"] is True
    assert data["next_cursor"] is None
    if path == "/consumption":
        assert data["items"][0]["energy_kwh"] == 13.46
        assert data["units"] == {"energy_kwh": "kWh"}
    if path == "/forecast":
        assert data["forecast_origin"] == "2009-06-08T00:00:00Z"
        assert "not a trained model" in data["note"]


def test_gateway_validation_and_empty_windows():
    """Bad input stays 422; valid historical windows without readings stay 200."""
    invalid = handler(event("/consumption", query={**WEEK, "end": WEEK["start"]}), {})
    assert invalid["statusCode"] == 422
    assert isinstance(json.loads(invalid["body"])["detail"], list)
    empty = handler(event("/anomalies", query={**WEEK, "household_id": "household-2"}), {})
    assert empty["statusCode"] == 200
    data = json.loads(empty["body"])
    assert data["items"] == []
    assert data["covered_start"] is None


@pytest.mark.parametrize("request_type,encoded", [("chat", True), ("weekly_summary", False)])
def test_gateway_chat_is_a_placeholder(request_type, encoded):
    """Both gateway body encodings preserve the disconnected assistant contract."""
    request = {**WEEK, "request_type": request_type}
    if request_type == "chat":
        request["message"] = "Why was my usage high?"
    response = handler(event("/chat", method="POST", body=request, encoded=encoded), {})
    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert data["status"] == "placeholder"
    assert data["assistant_connected"] is False
    assert data["citations"] == []
    assert "Bedrock is not connected" in data["answer"]


def test_each_warm_invocation_starts_and_closes_repository(monkeypatch):
    """An already-imported handler must still initialize/close request resources."""
    created = []
    closed = []

    class TrackedRepository(MockRepository):
        """Track lifecycle behavior without introducing any external storage."""

        def __init__(self):
            """Create the same deterministic fixtures and remember this instance."""
            super().__init__()
            created.append(self)

        def close(self):
            """Record cleanup so disabling Mangum lifespan cannot pass unnoticed."""
            closed.append(self)

    monkeypatch.setattr("app.main.create_repository", TrackedRepository)
    for _ in range(2):
        assert handler(event("/consumption", query=WEEK), {})["statusCode"] == 200
    assert len(created) == 2
    assert closed == created


def test_lambda_configuration_errors_do_not_silently_skip_startup(monkeypatch):
    """A configuration typo must fail before serving data with a stale service."""
    monkeypatch.setenv("APP_DATA_MODE", "typo")
    with pytest.raises(LifespanFailure, match="APP_DATA_MODE must be mock or dynamodb"):
        handler(event("/health"), {})
