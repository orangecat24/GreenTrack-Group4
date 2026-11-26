"""Offline HTTP and Converse contract checks for the standalone assistant."""

import json
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from assistant.bedrock import BedrockModel
from assistant.main import create_app
from assistant.service import MAX_MODEL_TURNS, MAX_TOOL_CALLS
from assistant.settings import FIXTURE_PATH
from assistant.tools import FixtureExecutor, QueryTools

WINDOW = {
    "household_id": "household-1",
    "start": "2009-06-01T00:00:00Z",
    "end": "2009-06-02T00:00:00Z",
}
QUESTION = {**WINDOW, "message": "How much energy did we use on June 1, 2009?"}


def _reply(reason, *content):
    """Create an offline Converse response."""
    return {"stopReason": reason, "output": {"message": {
        "role": "assistant", "content": list(content),
    }}}


def _tool(name="consumption_totals", args=None, call_id="call-1"):
    """Create a test tool call with one overridable field at a time."""
    return {"toolUse": {"toolUseId": call_id, "name": name,
                        "input": WINDOW if args is None else args}}


class ChatTests(unittest.TestCase):
    """Exercise valid and invalid requests through the real FastAPI route."""

    def setUp(self):
        """Observe calls to real P3 02 tools without replacing their calculations."""
        self.tools = Mock(wraps=QueryTools(FixtureExecutor(FIXTURE_PATH)))

    def post(self, body=QUESTION, *, model=None):
        """Run the standalone route with a cloud-client tripwire."""
        with patch.dict("os.environ", {"GREENTRACK_ASSISTANT_MODEL_MODE": "scripted"}):
            with patch("boto3.client", side_effect=AssertionError("Unexpected AWS client")) as aws:
                with TestClient(create_app(model=model, tools=self.tools)) as client:
                    response = client.post("/chat", json=body)
                aws.assert_not_called()
        return response

    def test_june_first_milestone(self):
        """Read actual fixture totals and report their measured coverage."""
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.tools.run.assert_called_once_with("consumption_totals", **WINDOW)
        result = response.json()
        self.assertEqual(result["status"], "ok")
        self.assertIn("9.75 kWh across 210 of 1,440 minutes", result["answer"])
        self.assertEqual(result["coverage"]["measured_minutes"], 210)
        self.assertEqual(result["coverage"]["expected_minutes"], 1440)
        self.assertEqual(result["provenance"], {
            "source": "synthetic_fixture", "source_id": "gold_hourly.json",
        })
        self.assertIs(result["is_demo"], True)
        self.assertIs(result["assistant_connected"], False)

    def test_weekly_summary_keeps_partial_coverage_and_labels_placeholders(self):
        """Read a seven-day request without making model predictions."""
        response = self.post({**WINDOW, "end": "2009-06-08T00:00:00Z",
                              "request_type": "weekly_summary"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("210 of 10,080 minutes", response.json()["answer"])
        self.assertIn("placeholders", response.json()["answer"])

    def test_invalid_requests_return_422(self):
        """Reject missing messages and incorrect historical bounds before reading."""
        for body in (
            WINDOW, {**QUESTION, "message": " "}, {**QUESTION, "start": "2009-06-01T00:01:00Z"},
            {**QUESTION, "household_id": "household-2"},
            {**WINDOW, "request_type": "weekly_summary"},
            {**WINDOW, "request_type": "weekly_summary",
             "start": "2009-06-01T01:00:00Z", "end": "2009-06-08T01:00:00Z"},
        ):
            with self.subTest(body=body):
                response = self.post(body)
                self.assertEqual(response.status_code, 422)
                self.assertIsInstance(response.json()["detail"], list)
        self.tools.run.assert_not_called()

    def test_missing_data_retains_coverage_without_an_energy_total(self):
        """Read an all-null hour and an absent hour through the normal route."""
        response = self.post({**QUESTION, "start": "2009-06-01T02:00:00Z",
                              "end": "2009-06-01T04:00:00Z"})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "no_data")
        self.assertEqual(result["coverage"]["all_null_hours"], 1)
        self.assertEqual(result["coverage"]["absent_hours"], 1)
        self.assertNotIn("kWh", result["answer"])
        self.assertEqual(result["citations"], [])

    def test_write_and_unsupported_prompts_are_refused(self):
        """The scripted path can decline requests without querying data."""
        for message in ("Delete all readings for this day.", "How do I use Git?"):
            with self.subTest(message=message):
                response = self.post({**WINDOW, "message": message})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "refused")
        self.tools.run.assert_not_called()

    def test_invalid_model_calls_never_reach_tools(self):
        """Reject an entire batch when a later call is unknown or changes scope."""
        for invalid in (
            _tool("drop_table", call_id="bad"),
            _tool(args={**WINDOW, "table": "gold"}, call_id="bad"),
            _tool(args={**WINDOW, "household_id": "household-2"}, call_id="bad"),
            _tool(args={**WINDOW, "end": "2009-06-01T22:00:00Z"}, call_id="bad"),
            _tool(args={**WINDOW, "start": 123}, call_id="bad"),
            _tool(),
        ):
            with self.subTest(invalid=invalid):
                model = Mock()
                model.next_turn.return_value = _reply("tool_use", _tool(), invalid)
                response = self.post(model=model)
                self.assertEqual(response.json()["status"], "refused")
        self.tools.run.assert_not_called()

    def test_round_limit_reserves_a_final_model_turn(self):
        """Stop repeated calls within both budgets."""
        model = Mock()
        model.next_turn.side_effect = [
            _reply("tool_use", _tool(call_id=f"call-{index}"))
            for index in range(MAX_MODEL_TURNS)
        ]
        response = self.post(model=model)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(model.next_turn.call_count, MAX_MODEL_TURNS)
        self.assertEqual(self.tools.run.call_count, MAX_TOOL_CALLS)

    def test_over_budget_batch_runs_no_queries(self):
        """Check the call count before executing any member of a model batch."""
        model = Mock()
        model.next_turn.return_value = _reply("tool_use", *[
            _tool(call_id=f"call-{index}") for index in range(MAX_TOOL_CALLS + 1)
        ])
        self.assertEqual(self.post(model=model).status_code, 503)
        self.tools.run.assert_not_called()

    def test_query_and_model_failures_are_safe(self):
        """A 503 response discloses no injected exception or partial evidence."""
        self.tools.run.return_value = {"status": "error", "message": "private upstream message"}
        model = Mock()
        model.next_turn.side_effect = RuntimeError("private model details")
        for response in (self.post(), self.post(model=model)):
            self.assertEqual(response.status_code, 503)
            result = response.json()
            self.assertEqual(result["status"], "error")
            self.assertNotIn("private", result["answer"])
            self.assertIsNone(result["coverage"])
            self.assertEqual(result["citations"], [])

    def test_bedrock_protocol_and_fact_grounding(self):
        """Pass actual tool results to a fake Converse client and use verified facts only."""
        client = Mock()
        client.converse.side_effect = [
            _reply("tool_use", _tool()), _reply("end_turn", {"text": "The total was 999 kWh."}),
        ]
        response = self.post(model=BedrockModel(
            client, model_id="offline-test-model", guardrail=("offline-guardrail", "1"),
        ))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("999", response.json()["answer"])
        first, final = (call.kwargs for call in client.converse.call_args_list)
        self.assertEqual(first["guardrailConfig"], {
            "guardrailIdentifier": "offline-guardrail", "guardrailVersion": "1",
        })
        specs = first["toolConfig"]["tools"]
        self.assertEqual({item["toolSpec"]["name"] for item in specs}, {
            "consumption_totals", "hourly_patterns", "weekday_weekend", "submetering_breakdown",
        })
        result = final["messages"][-1]["content"][0]["toolResult"]
        self.assertEqual(result["toolUseId"], "call-1")
        self.assertEqual(result["content"][0]["json"]["data"], {"observed_kwh": 9.75})

    def test_guardrail_intervention_is_refused(self):
        """A guardrail stop can omit the usual assistant output."""
        model = Mock()
        model.next_turn.return_value = {"stopReason": "guardrail_intervened"}
        self.assertEqual(self.post(model=model).json()["status"], "refused")
        self.tools.run.assert_not_called()

    def test_scripted_other_tools_use_real_rows(self):
        """Smoke-test the remaining three routes through the same service."""
        for question, name, answer in (
            ("What was the hourly peak?", "hourly_patterns", "7.5 kWh"),
            ("Compare weekdays and weekends.", "weekday_weekend", "weekend: unavailable"),
            ("Show the circuit breakdown.", "submetering_breakdown", "kitchen: 1.95 kWh"),
        ):
            with self.subTest(question=question):
                self.tools.run.reset_mock()
                response = self.post({**WINDOW, "message": question})
                self.assertEqual(response.status_code, 200)
                self.assertIn(answer, response.json()["answer"])
                self.tools.run.assert_called_once_with(name, **WINDOW)

    def test_source_handler_accepts_http_api_v2_event(self):
        """Exercise Mangum locally before running the separate ZIP check."""
        with patch.dict("os.environ", {"GREENTRACK_ASSISTANT_MODEL_MODE": "scripted"}):
            from assistant.lambda_handler import handler

            result = handler({
                "version": "2.0", "routeKey": "POST /chat", "rawPath": "/chat",
                "rawQueryString": "", "headers": {"content-type": "application/json"},
                "requestContext": {
                    "stage": "$default",
                    "http": {"method": "POST", "path": "/chat", "sourceIp": "127.0.0.1"},
                },
                "body": json.dumps(QUESTION), "isBase64Encoded": False,
            }, None)
        self.assertEqual(result["statusCode"], 200)
        self.assertIn("9.75 kWh", json.loads(result["body"])["answer"])
