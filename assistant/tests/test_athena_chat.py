"""Exercise the configured Athena chat path with fabricated wire results."""

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from assistant.athena import AthenaClient
from assistant.main import create_app
from assistant.query_templates import HOURLY_COLUMNS

BASELINE = json.loads(
    (Path(__file__).resolve().parents[2] / "evaluation/assistant/gold_ground_truth.json")
    .read_text(encoding="utf-8")
)
ATHENA_SETTINGS = {
    "GREENTRACK_ASSISTANT_DATA_MODE": "athena",
    "GREENTRACK_ASSISTANT_ATHENA_WORKGROUP": "offline-assistant",
    "GREENTRACK_ASSISTANT_MODEL_MODE": "scripted",
}


def _row(*cells):
    """Encode cells as the string-valued Athena result format."""
    return {"Data": [{"VarCharValue": cell} for cell in cells]}


class AthenaChatTests(unittest.TestCase):
    """Test configuration, query submission and the public HTTP response."""

    def test_athena_chat_composes_a_read_only_result(self):
        """Use fabricated hours whose sum matches the reported daily benchmark."""
        athena = Mock(spec=AthenaClient)
        athena.start_query_execution.return_value = {"QueryExecutionId": "fake-athena-june-1"}
        athena.get_query_execution.return_value = {"QueryExecution": {"Status": {"State": "SUCCEEDED"}}}
        # These are test doubles, not historical hourly readings or AWS evidence.
        rows = [
            _row(f"2009-06-01 {hour:02}:00:00.000", "1.054" if hour == 23 else "1",
                 "60", "true", "0", "0", "0", "1.054" if hour == 23 else "1")
            for hour in range(24)
        ]
        athena.get_query_results.side_effect = [
            {"ResultSet": {"Rows": [_row(*HOURLY_COLUMNS), *rows[:12]]}, "NextToken": "next"},
            {"ResultSet": {"Rows": rows[12:]}},
        ]
        with patch.dict("os.environ", ATHENA_SETTINGS), patch("boto3.client", return_value=athena) as factory:
            with TestClient(create_app()) as client:
                response = client.post("/chat", json=BASELINE["request"])
        factory.assert_called_once()
        self.assertEqual(factory.call_args.args, ("athena",))
        self.assertEqual(factory.call_args.kwargs["region_name"], "eu-central-1")
        athena.start_query_execution.assert_called_once()
        query = athena.start_query_execution.call_args.kwargs
        self.assertEqual(query["WorkGroup"], "offline-assistant")
        self.assertEqual(query["QueryExecutionContext"], {
            "Catalog": "AwsDataCatalog", "Database": "g4_greentrack_dev_gold",
        })
        self.assertIn("period_start >= ?", query["QueryString"])
        self.assertIn("period_start < ?", query["QueryString"])
        self.assertEqual(query["ExecutionParameters"], [
            "'household-1'", "CAST('2009-06-01 00:00:00' AS TIMESTAMP)",
            "CAST('2009-06-02 00:00:00' AS TIMESTAMP)",
        ])
        self.assertEqual(athena.get_query_results.call_count, 2)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "ok")
        self.assertIn(
            f"{BASELINE['reported_daily_kwh_rounded_to_3dp']:.3f} kWh across 1,440 of 1,440 minutes",
            result["answer"],
        )
        self.assertEqual(result["coverage"], BASELINE["expected_hourly_coverage_from_reported_complete_day"])
        self.assertEqual(result["provenance"], {"source": "athena", "source_id": "fake-athena-june-1"})
        self.assertEqual(result["citations"], [])
        self.assertIs(result["is_demo"], False)
        self.assertIs(result["assistant_connected"], False)

    def test_athena_error_does_not_fall_back_to_fixture(self):
        """Return the draft safe error without fake coverage or a fixture citation."""
        athena = Mock(spec=AthenaClient)
        athena.start_query_execution.side_effect = RuntimeError("private upstream details")
        with patch.dict("os.environ", ATHENA_SETTINGS), patch("boto3.client", return_value=athena):
            with TestClient(create_app()) as client:
                response = client.post("/chat", json=BASELINE["request"])
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["provenance"], {"source": "athena", "source_id": None})
        self.assertIsNone(response.json()["coverage"])
        self.assertNotIn("private", response.json()["answer"])

    def test_default_uses_fixture_without_constructing_clients(self):
        """An unset mode keeps the existing synthetic chat behavior."""
        with patch.dict("os.environ", {}, clear=True), patch("boto3.client") as factory:
            with TestClient(create_app()) as client:
                response = client.post("/chat", json=BASELINE["request"])
        factory.assert_not_called()
        self.assertIn("9.75 kWh", response.json()["answer"])
        self.assertIs(response.json()["is_demo"], True)

    def test_missing_workgroup_fails_before_constructing_a_client(self):
        """An explicit opt-in requires a trusted workgroup selection."""
        settings = {**ATHENA_SETTINGS, "GREENTRACK_ASSISTANT_ATHENA_WORKGROUP": ""}
        with patch.dict("os.environ", settings), patch("boto3.client") as factory:
            with self.assertRaisesRegex(ValueError, "requires an approved workgroup"):
                create_app()
        factory.assert_not_called()
