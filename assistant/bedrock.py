"""Model adapters for the scripted demo and future Bedrock Converse calls."""

import re
from typing import Any, Literal, Protocol

from .models import QueryWindow, utc_label

TOOL_DESCRIPTIONS = {
    "consumption_totals": "Sum observed energy over the selected window.",
    "hourly_patterns": "List observed energy and coverage for each requested hour.",
    "weekday_weekend": "Compare mean energy per complete hour by day type.",
    "submetering_breakdown": "Sum observed energy by sub-meter circuit or group.",
}

Message = dict[str, Any]
RequestType = Literal["chat", "weekly_summary"]
REFUSAL = "REFUSED"


class Model(Protocol):
    """Choose the next turn for a single request's conversation."""

    def next_turn(
        self, messages: list[Message], window: QueryWindow, request_type: RequestType
    ) -> Message:
        """Return a Converse-shaped assistant turn."""


def _tool_specs() -> list[dict]:
    """Declare the four fixed tools and their exact argument shape."""
    return [
        {"toolSpec": {
            "name": name,
            "description": description,
            "inputSchema": {"json": {
                "type": "object",
                "properties": {
                    "household_id": {"type": "string"},
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                },
                "required": ["household_id", "start", "end"],
                "additionalProperties": False,
            }},
        }}
        for name, description in TOOL_DESCRIPTIONS.items()
    ]


class ConverseClient(Protocol):
    """The subset of the injected SDK client used here."""

    def converse(self, **kwargs: Any) -> Message:
        """Run one Converse request."""


class BedrockModel:
    """Translate a turn request into the Bedrock Converse API."""

    def __init__(
        self, client: ConverseClient, *, model_id: str, guardrail: tuple[str, str] | None = None
    ) -> None:
        """Use an explicitly selected model and optional guardrail ID and version."""
        self._client = client
        self._model_id = model_id
        self._guardrail = guardrail

    def next_turn(
        self, messages: list[Message], window: QueryWindow, request_type: RequestType
    ) -> Message:
        """Pass structured tool calls and results through Converse."""
        scope = (
            f"Use only {window.household_id} from {utc_label(window.start)} (inclusive) "
            f"to {utc_label(window.end)} (exclusive). Use these exact values in tool calls."
        )
        system = (
            "You select approved read-only GreenTrack energy tools. "
            f"{scope} For an out-of-scope or write request reply exactly {REFUSAL}. "
            "For a weekly summary, select consumption_totals. When tools return, "
            "finish the turn so the application can render the verified values."
        )
        options = {}
        if self._guardrail:
            identifier, version = self._guardrail
            options["guardrailConfig"] = {
                "guardrailIdentifier": identifier, "guardrailVersion": version,
            }
        return self._client.converse(
            modelId=self._model_id,
            system=[{"text": f"{system} Request type is {request_type}."}],
            messages=messages,
            toolConfig={"tools": _tool_specs()},
            inferenceConfig={"maxTokens": 400, "temperature": 0},
            **options,
        )


def _turn(reason: str, *content: dict) -> Message:
    """Build a scripted turn with the same structure as Converse."""
    return {
        "stopReason": reason,
        "output": {"message": {"role": "assistant", "content": list(content)}},
    }


class ScriptedModel:
    """Select an example read tool from a small set of offline prompts."""

    def next_turn(
        self, messages: list[Message], window: QueryWindow, request_type: RequestType
    ) -> Message:
        """Request a tool, then finish after receiving its real result."""
        if len(messages) > 1:
            return _turn("end_turn", {"text": "Ready to render the tool result."})

        question = messages[0]["content"][0]["text"].lower()
        # This demonstration has a small vocabulary. Tool validation in the
        # service is independent of this routing and also applies to Claude.
        write = r"\b(delete|drop|truncate|write|upload|update|insert|erase|remove|modify|overwrite|set)\b"
        energy = r"\b(energy|usage|consumption|kwh|electricity|power)\b|\bhow much\b.*\buse[ds]?\b"
        if re.search(write, question):
            return _turn("end_turn", {"text": REFUSAL})
        if request_type == "weekly_summary":
            name = "consumption_totals"
        elif re.search(r"\b(weekday|weekdays|weekend|weekends)\b", question):
            name = "weekday_weekend"
        elif re.search(r"\b(sub.?meter\w*|breakdown|circuits?)\b", question):
            name = "submetering_breakdown"
        elif re.search(r"\b(hourly|peak|spike)\b", question):
            name = "hourly_patterns"
        elif re.search(energy, question):
            name = "consumption_totals"
        else:
            return _turn("end_turn", {"text": REFUSAL})

        return _turn("tool_use", {"toolUse": {
            "toolUseId": "scripted-1",
            "name": name,
            "input": {
                "household_id": window.household_id,
                "start": utc_label(window.start),
                "end": utc_label(window.end),
            },
        }})
