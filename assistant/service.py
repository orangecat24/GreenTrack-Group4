"""Validate model turns and render answers exclusively from approved tool results."""

from dataclasses import dataclass
from time import monotonic
from typing import Literal

from .bedrock import Message, Model, REFUSAL, RequestType, TOOL_DESCRIPTIONS
from .models import Coverage, Provenance, QueryWindow, ToolInputError, ToolResult, utc_label
from .tools import QueryTools

MAX_MODEL_TURNS = 3
MAX_TOOL_CALLS = 2
SERVICE_BUDGET_SECONDS = 8


@dataclass(frozen=True)
class Reply:
    """Structured outcome before the HTTP layer adds the requested scope."""

    status: Literal["ok", "no_data", "refused", "error"]
    answer: str
    coverage: Coverage | None = None
    provenance: Provenance | None = None


REFUSED = Reply("refused", "I can answer questions about energy use using approved read-only queries.")
FAILED = Reply("error", "Energy data is temporarily unavailable. Please try again.")


def _calls(message: Message, window: QueryWindow) -> list[tuple[str, str]]:
    """Check a complete batch before any tool is allowed to read data."""
    calls = []
    for block in message["content"]:
        if "toolUse" not in block:
            continue
        call = block["toolUse"]
        name, call_id, args = call["name"], call["toolUseId"], call["input"]
        if (
            not isinstance(name, str)
            or name not in TOOL_DESCRIPTIONS
            or not isinstance(call_id, str)
            or not call_id
            or not isinstance(args, dict)
            or args.keys() != {"household_id", "start", "end"}
        ):
            raise ToolInputError("Invalid model tool call.")
        proposed = QueryWindow.parse(**args, allowed_households=frozenset({window.household_id}))
        if proposed != window:
            raise ToolInputError("The model tool call changed the requested scope.")
        calls.append((call_id, name))
    return calls


def _describe(result: ToolResult) -> str:
    """Summarize P3 02 data while keeping observed values and units visible."""
    data = result["data"]
    match result["tool"]:
        case "consumption_totals":
            return f"Observed usage was {data['observed_kwh']:.6g} kWh."
        case "hourly_patterns":
            # P3 02 returns the grid in time order. max keeps the earliest tie.
            observed = [hour for hour in data["hours"] if hour["observed_kwh"] is not None]
            peak = max(observed, key=lambda hour: hour["observed_kwh"])
            return (
                f"The largest observed hour in this window began at {peak['period_start']} "
                f"and used {peak['observed_kwh']:.6g} kWh."
            )
        case "weekday_weekend":
            groups = []
            for name, group in data.items():
                average = group["mean_kwh_per_complete_hour"]
                if average is None:
                    groups.append(f"{name}: unavailable")
                else:
                    groups.append(f"{name}: {average:.6g} kWh per complete hour "
                                  f"({group['eligible_hours']} hours)")
            return "Observed comparison — " + ", ".join(groups) + "."
        case "submetering_breakdown":
            labels = {"kitchen_kwh": "kitchen", "laundry_kwh": "laundry",
                      "heater_ac_kwh": "heater/AC", "other_kwh": "other"}
            groups = []
            for field, group in data.items():
                energy = group["observed_kwh"]
                value = "unavailable" if energy is None else f"{energy:.6g} kWh"
                groups.append(f"{labels[field]}: {value}")
            return "Observed circuit totals — " + ", ".join(groups) + "."
    raise ValueError("Unknown result tool.")


def _reply(results: list[ToolResult], request_type: RequestType) -> Reply:
    """Compose evidence and coverage for the exact request window."""
    successful = [result for result in results if result["status"] == "ok"]
    first = results[0]
    coverage = first["coverage"]
    provenance = first["provenance"]
    synthetic = "Synthetic data. " if provenance["source"] == "synthetic_fixture" else ""
    measured = coverage["measured_minutes"]
    expected = coverage["expected_minutes"]
    minutes = f"{measured:,} of {expected:,} minutes"
    if not successful:
        return Reply("no_data", f"{synthetic}No usable values for this calculation. "
                     f"Active-power coverage was {minutes}.", coverage, provenance)
    facts = " ".join(dict.fromkeys(_describe(result) for result in successful))
    if len(successful) == 1 and successful[0]["tool"] == "consumption_totals":
        facts = f"{facts.removesuffix('.')} across {minutes}."
    else:
        facts = f"{facts} Active-power coverage was {minutes}."
    if request_type == "weekly_summary":
        facts += " Forecast and anomaly sections are placeholders pending model results."
    return Reply("ok", synthetic + facts, coverage, provenance)


class ChatService:
    """Run a bounded read-only conversation with a request-scoped tool perimeter."""

    def __init__(self, model: Model, tools: QueryTools) -> None:
        """Accept independently replaceable model and query adapters."""
        self._model = model
        self._tools = tools

    def answer(self, window: QueryWindow, request_type: RequestType, question: str | None) -> Reply:
        """Run model turns and return a deterministic, evidence-backed reply."""
        try:
            return self._answer(window, request_type, question)
        except ToolInputError:
            return REFUSED
        except Exception:
            # This boundary may see SDK or executor details. The HTTP response
            # carries only a stable retry message.
            return FAILED

    def _answer(self, window: QueryWindow, request_type: RequestType, question: str | None) -> Reply:
        """Keep conversation, call IDs and timing local to this request."""
        messages: list[Message] = [{
            "role": "user", "content": [{"text": question or "Summarize the selected energy week."}],
        }]
        results: list[ToolResult] = []
        seen_ids: set[str] = set()
        deadline = monotonic() + SERVICE_BUDGET_SECONDS
        for turn in range(MAX_MODEL_TURNS):
            if monotonic() >= deadline:
                return FAILED
            model_reply = self._model.next_turn(messages, window, request_type)
            if monotonic() >= deadline:
                return FAILED
            reason = model_reply["stopReason"]
            if reason in ("guardrail_intervened", "content_filtered"):
                return REFUSED
            if reason not in ("end_turn", "tool_use"):
                return FAILED
            message = model_reply["output"]["message"]
            if message["role"] != "assistant" or not isinstance(message["content"], list):
                return FAILED
            if reason == "end_turn":
                if any("toolUse" in block for block in message["content"]):
                    return FAILED
                if not results or any(block.get("text", "").strip() == REFUSAL
                                      for block in message["content"]):
                    return REFUSED
                return _reply(results, request_type)
            calls = _calls(message, window)
            ids = {call_id for call_id, _ in calls}
            if not calls or len(ids) != len(calls) or seen_ids.intersection(ids):
                return REFUSED
            if turn + 1 == MAX_MODEL_TURNS or len(results) + len(calls) > MAX_TOOL_CALLS:
                return FAILED
            seen_ids.update(ids)
            tool_results = []
            for call_id, name in calls:
                if monotonic() >= deadline:
                    return FAILED
                result = self._tools.run(name, household_id=window.household_id,
                                         start=utc_label(window.start), end=utc_label(window.end))
                if result["status"] == "error":
                    return FAILED
                results.append(result)
                tool_results.append({"toolResult": {
                    "toolUseId": call_id, "content": [{"json": result}],
                }})
            messages.extend((message, {"role": "user", "content": tool_results}))
        return FAILED
