"""Adapt API Gateway HTTP API events to our existing FastAPI application."""

from mangum import Mangum

from .main import app

# Lambda calls this object, whereas local Uvicorn continues importing main:app.
# Startup builds the service/repository and shutdown closes it on EVERY invocation.
# Turning lifespan off would leave app.state.energy_service uninitialized. Using
# 'on' also makes configuration errors fail rather than skipping startup silently.
handler = Mangum(app, lifespan="on")
