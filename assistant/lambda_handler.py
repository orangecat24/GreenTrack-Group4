"""Adapt the standalone assistant to a Lambda HTTP API v2 event."""

from mangum import Mangum

from .main import app

handler = Mangum(app, lifespan="off")
