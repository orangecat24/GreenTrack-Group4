"""Verify the Athena adapter using only a fake client and local tool calls."""

import unittest
from unittest.mock import Mock, call, patch

from assistant.athena import MAX_PAGES, MAX_POLLS, AthenaClient, AthenaExecutor
from assistant.query_templates import RESULT_ROW_LIMIT
from assistant.tools import QueryTools

DAY = {
    "household_id": "household-1",
    "start": "2009-06-01T00:00:00Z",
    "end": "2009-06-02T00:00:00Z",
}


def _row(*values):
    """Encode Athena string cells and SQL nulls as they appear over the wire."""
    return {"Data": [{} if value is None else {"VarCharValue": value} for value in values]}


HEADER = _row(
    "period_start", "energy_kwh", "minutes_with_data", "is_complete",
    "kitchen_kwh", "laundry_kwh", "heater_ac_kwh", "other_kwh",
)
FIRST = _row("2009-06-01 00:00:00.000", "1.5", "60", "true", "0.6", "0.3", "0.3", "0.3")
ALL_NULL = _row("2009-06-01 02:00:00.000", None, "0", "false", None, None, None, None)


def _page(*rows, **metadata):
    """Create a result page, with pagination metadata when supplied."""
    return {"ResultSet": {"Rows": list(rows)}, **metadata}


def _state(state):
    """Create an execution status response."""
    return {"QueryExecution": {"Status": {"State": state, "StateChangeReason": "internal details"}}}


class FakeThrottleError(Exception):
    """Mimic a retryable SDK service error without importing the SDK."""

    response = {"Error": {"Code": "TooManyRequestsException"}}


class AthenaTests(unittest.TestCase):
    """Test the exact bound read and failures without an SDK or AWS account."""

    def setUp(self):
        """Inject a client with a successful header-only result by default."""
        self.client = Mock(spec=AthenaClient)
        self.client.start_query_execution.return_value = {"QueryExecutionId": "offline-id"}
        self.client.get_query_execution.return_value = _state("SUCCEEDED")
        self.client.get_query_results.return_value = _page(HEADER)
        self.tools = QueryTools(AthenaExecutor(self.client, workgroup="test-assistant"))

    def assert_read_failed(self):
        """Check that the public error contains neither partial data nor SDK detail."""
        result = self.tools.run("consumption_totals", **DAY)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["coverage"])
        self.assertIsNone(result["data"])
        self.assertIsNone(result["provenance"])
        self.assertEqual(result["message"], "Energy data could not be read. Try again later.")

    def test_parameters_and_pagination(self):
        """Check the fixed SELECT, typed values, nulls and the next-page request."""
        self.client.get_query_execution.side_effect = [
            _state("QUEUED"), _state("RUNNING"), _state("SUCCEEDED"),
        ]
        self.client.get_query_results.side_effect = [
            _page(HEADER, FIRST, NextToken="next"),
            _page(ALL_NULL),
        ]
        with patch("assistant.athena.sleep") as sleep:
            result = self.tools.run("hourly_patterns", **DAY)
        self.assertEqual(sleep.call_count, 2)
        self.client.start_query_execution.assert_called_once()
        submitted = self.client.start_query_execution.call_args.kwargs
        sql = submitted["QueryString"]
        self.assertTrue(sql.startswith("SELECT period_start, energy_kwh"))
        self.assertIn("FROM hourly_consumption\nWHERE household_id = ?", sql)
        self.assertIn("period_start >= ?", sql)
        self.assertIn("period_start < ?", sql)
        self.assertTrue(sql.endswith(f"LIMIT {RESULT_ROW_LIMIT + 1}"))
        self.assertNotIn("household-1", sql)
        self.assertEqual(sql.count("?"), 3)
        self.assertEqual(submitted["ExecutionParameters"], [
            "'household-1'",
            "CAST('2009-06-01 00:00:00' AS TIMESTAMP)",
            "CAST('2009-06-02 00:00:00' AS TIMESTAMP)",
        ])
        self.assertEqual(submitted["QueryExecutionContext"], {
            "Catalog": "AwsDataCatalog", "Database": "g4_greentrack_dev_gold",
        })
        self.assertEqual(submitted["WorkGroup"], "test-assistant")
        self.assertEqual(self.client.get_query_results.call_args_list, [
            call(QueryExecutionId="offline-id", MaxResults=1000),
            call(QueryExecutionId="offline-id", MaxResults=1000, NextToken="next"),
        ])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["provenance"], {"source": "athena", "source_id": "offline-id"})
        self.assertEqual(result["data"]["hours"][0]["observed_kwh"], 1.5)
        self.assertEqual(result["data"]["hours"][2]["bucket_status"], "all_null")
        self.assertEqual(result["coverage"]["measured_minutes"], 60)

    def test_header_only_is_no_data(self):
        """A completed SELECT with no rows still has a header and valid coverage."""
        result = self.tools.run("consumption_totals", **DAY)
        self.assertEqual(result["status"], "no_data")
        self.assertEqual(result["coverage"]["absent_hours"], 24)

    def test_failed_and_cancelled_queries(self):
        """Reject terminal failures without requesting results or resubmitting."""
        for state in ("FAILED", "CANCELLED"):
            with self.subTest(state=state):
                self.client.start_query_execution.reset_mock()
                self.client.get_query_execution.return_value = _state(state)
                self.assert_read_failed()
                self.client.start_query_execution.assert_called_once()
                self.client.get_query_results.assert_not_called()

    def test_polling_timeout_stops_query(self):
        """Bound wait attempts and request cancellation of an active query."""
        self.client.get_query_execution.return_value = _state("RUNNING")
        with patch("assistant.athena.sleep") as sleep:
            self.assert_read_failed()
        self.assertEqual(self.client.get_query_execution.call_count, MAX_POLLS)
        self.assertEqual(sleep.call_count, MAX_POLLS - 1)
        self.client.stop_query_execution.assert_called_once_with(QueryExecutionId="offline-id")
        self.client.get_query_results.assert_not_called()

    def test_later_page_failure_discards_first_page(self):
        """A transport failure midway through a read cannot yield a partial total."""
        self.client.get_query_results.side_effect = [
            _page(HEADER, FIRST, NextToken="next"),
            OSError("private client detail"),
        ]
        self.assert_read_failed()
        self.client.start_query_execution.assert_called_once()

    def test_transient_read_retries_once_with_same_token(self):
        """Recover from transient status and page errors without submitting again."""
        self.client.get_query_execution.side_effect = [FakeThrottleError(), _state("SUCCEEDED")]
        self.client.get_query_results.side_effect = [
            _page(HEADER, FIRST, NextToken="next"), FakeThrottleError(), _page(ALL_NULL),
        ]
        with patch("assistant.athena.sleep") as sleep:
            result = self.tools.run("consumption_totals", **DAY)
        self.assertEqual(result["data"], {"observed_kwh": 1.5})
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(self.client.get_query_results.call_args_list[-2:],
                         [call(QueryExecutionId="offline-id", MaxResults=1000, NextToken="next")] * 2)
        self.client.start_query_execution.assert_called_once()

    def test_retry_budget_is_bounded(self):
        """Fail cleanly if a status read is throttled twice."""
        self.client.get_query_execution.side_effect = FakeThrottleError()
        with patch("assistant.athena.sleep") as sleep:
            self.assert_read_failed()
        self.assertEqual(self.client.get_query_execution.call_count, 2)
        self.assertEqual(sleep.call_count, 1)
        self.client.start_query_execution.assert_called_once()

    def test_result_overflow(self):
        """Reject the extra SQL sentinel row instead of truncating the result."""
        self.client.get_query_results.return_value = _page(
            HEADER, *([FIRST] * (RESULT_ROW_LIMIT + 1))
        )
        self.assert_read_failed()

    def test_pagination_cannot_continue_indefinitely(self):
        """Reject repeated tokens and stop after the page budget."""
        self.client.get_query_results.side_effect = [
            _page(HEADER, FIRST, NextToken="same"), _page(ALL_NULL, NextToken="same"),
        ]
        self.assert_read_failed()
        self.assertEqual(self.client.get_query_results.call_count, 2)
        self.client.get_query_results.reset_mock()
        self.client.get_query_results.side_effect = [
            _page(HEADER, NextToken="1"),
            *(_page(FIRST, NextToken=str(i)) for i in range(2, MAX_PAGES + 1)),
        ]
        self.assert_read_failed()
        self.assertEqual(self.client.get_query_results.call_count, MAX_PAGES)

    def test_empty_continuation_is_incomplete(self):
        """Fail when a continuation token leads to a page with no rows."""
        self.client.get_query_results.side_effect = [_page(HEADER, FIRST, NextToken="next"), _page()]
        self.assert_read_failed()

    def test_malformed_rows_and_header(self):
        """Reject malformed wire data, duplicate hours, and an end-boundary row."""
        for page in (
            _page(), _page(FIRST), _page(HEADER, _row("2009-06-01 00:00:00")),
            _page(HEADER, _row("2009-06-01 00:00:00", "nan", "60", "true", "0", "0", "0", "0")),
            _page(HEADER, _row("2009-06-01 00:00:00", "1", "60", "false", "0", "0", "0", "0")),
            _page(HEADER, FIRST, FIRST),
            _page(HEADER, _row("2009-06-02 00:00:00", "1", "60", "true", "0", "0", "0", "1")),
        ):
            with self.subTest(page=page):
                self.client.get_query_results.return_value = page
                self.assert_read_failed()
