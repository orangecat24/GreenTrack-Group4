"""HTTP entry point: validate requests, call the service, serialize typed JSON."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .models import (
    AnomalyPoint, ChatRequest, ChatResponse, ConsumptionQuery, ConsumptionResponse,
    ForecastResponse, HealthResponse, ReadResponse, Window,
)
from .repository import RepositoryError
from .service import EnergyService
from .storage import create_repository


def create_app() -> FastAPI:
    """Create independent app instances so tests can verify startup configuration."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Choose storage once; the default path never constructs an AWS client."""
        repository = create_repository()
        app.state.energy_service = EnergyService(repository)
        try:
            yield
        finally:
            repository.close()

    app = FastAPI(
        title="GreenTrack demo API", version="0.1.0", lifespan=lifespan,
        description=("Synthetic household-1 data, June 1-7, 2009. UTC is a demo "
                     "convention only. Forecast/chat are illustrative or placeholders."),
    )

    @app.exception_handler(RepositoryError)
    async def storage_error(request: Request, error: RepositoryError) -> JSONResponse:
        """Return a safe retryable error, never raw AWS exception/credential details."""
        return JSONResponse(status_code=503, content={"detail": str(error)})

    def get_service(request: Request) -> EnergyService:
        """Reuse the service created at startup instead of rebuilding every request."""
        return request.app.state.energy_service

    @app.get("/", include_in_schema=False)
    def api_home(request: Request) -> RedirectResponse:
        """Send browser visitors to the interactive API documentation."""
        # Uvicorn's base URL points to '/', which previously had no route and
        # returned 404. This redirect helps humans find /docs; the frontend
        # continues requesting the JSON endpoints such as /consumption directly.
        # Resolve the named route so a future mounted URL prefix is respected.
        return RedirectResponse(request.url_for("swagger_ui_html"), status_code=307)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """Report local mock API health without checking any external services."""
        return HealthResponse()

    @app.get("/consumption", response_model=ConsumptionResponse)
    def consumption(
        query: Annotated[ConsumptionQuery, Query()],
        service: Annotated[EnergyService, Depends(get_service)],
    ) -> ConsumptionResponse:
        """Read hourly energy or full UTC-day totals within [start, end)."""
        return service.consumption(query)

    @app.get("/anomalies", response_model=ReadResponse[AnomalyPoint])
    def anomalies(
        query: Annotated[Window, Query()],
        service: Annotated[EnergyService, Depends(get_service)],
    ) -> ReadResponse[AnomalyPoint]:
        """Read synthetic anomaly hours within [start, end)."""
        return service.anomalies(query)

    @app.get("/forecast", response_model=ForecastResponse)
    def forecast(
        query: Annotated[Window, Query()],
        service: Annotated[EnergyService, Depends(get_service)],
    ) -> ForecastResponse:
        """Read target hours, not origin dates, within [start, end)."""
        return service.forecast(query)

    @app.post("/chat", response_model=ChatResponse)
    def chat(
        body: ChatRequest,
        service: Annotated[EnergyService, Depends(get_service)],
    ) -> ChatResponse:
        """Placeholder for questions and request_type=weekly_summary."""
        return service.chat(body)

    return app


app = create_app()
