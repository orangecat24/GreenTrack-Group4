"""Standalone FastAPI assistant using the draft Person 3 chat contract."""

from datetime import timedelta
from typing import Literal

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .bedrock import Model, RequestType
from .models import Coverage, QueryWindow, ToolInputError, utc_label
from .service import ChatService
from .settings import FIXTURE_PATH, HOUSEHOLDS, configured_model
from .tools import FixtureExecutor, QueryTools


class ChatRequest(BaseModel):
    """Validate the draft wire shape without changing Person 2's API models."""

    model_config = ConfigDict(extra="forbid", strict=True)
    household_id: str = Field(max_length=64)
    start: str
    end: str
    request_type: RequestType = "chat"
    message: str | None = Field(default=None, max_length=2000)

    @field_validator("message", mode="before")
    @classmethod
    def trim_message(cls, value: object) -> object:
        """Apply the length limit after trimming whitespace."""
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_message(self) -> "ChatRequest":
        """Require a nonblank message for ordinary chat only."""
        if self.request_type == "chat" and not self.message:
            raise ValueError("Chat requires a message.")
        return self

    def window(self) -> QueryWindow:
        """Apply shared P3 02 validation and the weekly-summary window rule."""
        window = QueryWindow.parse(self.household_id, self.start, self.end, HOUSEHOLDS)
        if self.request_type == "weekly_summary" and (
            window.start.hour or window.end.hour or window.end - window.start != timedelta(days=7)
        ):
            raise ToolInputError("Choose seven historical days from midnight to midnight.")
        return window


class Citation(BaseModel):
    """A title and URL using the shared draft citation shape."""

    title: str
    url: str


class ChatProvenance(BaseModel):
    """The data source and identifier, when a read completed."""

    source: Literal["synthetic_fixture", "athena"]
    source_id: str | None


class ChatResponse(BaseModel):
    """Data-backed, empty, refused and failed outcomes for review."""

    household_id: str
    request_type: RequestType
    requested_start: str
    requested_end: str
    status: Literal["ok", "no_data", "refused", "error"]
    answer: str
    citations: list[Citation]
    coverage: Coverage | None
    provenance: ChatProvenance
    assistant_connected: Literal[False] = False
    is_demo: Literal[True] = True


def create_app(*, model: Model | None = None, tools: QueryTools | None = None) -> FastAPI:
    """Build the route with replaceable adapters for offline tests."""
    app = FastAPI(title="GreenTrack Assistant")
    if tools is None:
        tools = QueryTools(FixtureExecutor(FIXTURE_PATH), allowed_households=HOUSEHOLDS)
    service = ChatService(model if model is not None else configured_model(), tools)

    @app.post("/chat", response_model=ChatResponse, responses={503: {"model": ChatResponse}})
    def chat(request: ChatRequest, response: Response) -> ChatResponse:
        """Return the draft outcome for one validated historical window."""
        try:
            window = request.window()
        except ToolInputError as error:
            raise HTTPException(422, detail=[{"loc": ["body"], "msg": str(error),
                                             "type": "value_error"}]) from None

        reply = service.answer(window, request.request_type, request.message)
        if reply.status == "error":
            response.status_code = 503
        provenance = ChatProvenance(
            **(reply.provenance or {"source": "synthetic_fixture", "source_id": None})
        )
        citations = []
        if reply.status == "ok" and provenance.source == "synthetic_fixture":
            citations.append(Citation(
                title="Synthetic Person 3 gold fixture (example only)",
                url="https://example.invalid/greentrack/person3-gold-fixture",
            ))
        return ChatResponse(
            household_id=window.household_id,
            request_type=request.request_type,
            requested_start=utc_label(window.start),
            requested_end=utc_label(window.end),
            status=reply.status,
            answer=reply.answer,
            citations=citations,
            coverage=reply.coverage,
            provenance=provenance,
        )

    return app


app = create_app()
