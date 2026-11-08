"""Run every API test without credentials or outbound network access."""

import socket
import threading

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def offline_mock(monkeypatch, tmp_path):
    """Remove common AWS settings and fail if application code attempts networking."""
    for name in (
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
        "AWS_PROFILE", "AWS_DEFAULT_PROFILE", "AWS_SHARED_CREDENTIALS_FILE",
        "AWS_CONFIG_FILE", "AWS_WEB_IDENTITY_TOKEN_FILE", "AWS_ROLE_ARN",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP_DATA_MODE", "mock")
    # Stubber clients use explicit fake credentials. Point the SDK's optional
    # config/credential paths at nonexistent test paths so it cannot inspect a
    # developer's actual authentication files while resolving client settings.
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "absent-aws-config"))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "absent-aws-credentials"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")

    def deny_network(*args, **kwargs):
        """TestClient uses in-process ASGI; real connections are always a mistake."""
        raise AssertionError("Mock mode attempted an outbound network call")

    # Windows implements asyncio's internal wake-up socketpair over loopback.
    # Permit only that stdlib operation, not arbitrary localhost application calls.
    internal = threading.local()
    original_pair = socket.socketpair
    original_connect = socket.socket.connect

    def internal_socketpair(*args, **kwargs):
        """Allow Windows event-loop plumbing while retaining the outbound guard."""
        internal.creating_pair = True
        try:
            return original_pair(*args, **kwargs)
        finally:
            internal.creating_pair = False

    def guarded_connect(sock, address):
        """Connections are allowed only while the stdlib builds its socketpair."""
        if getattr(internal, "creating_pair", False):
            return original_connect(sock, address)
        return deny_network(sock, address)

    monkeypatch.setattr(socket, "socketpair", internal_socketpair)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(socket, "getaddrinfo", deny_network)


@pytest.fixture
def client():
    """Exercise the real startup/shutdown path and HTTP validation in memory."""
    with TestClient(create_app()) as test_client:
        yield test_client
