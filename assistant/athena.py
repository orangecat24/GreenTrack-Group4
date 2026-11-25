"""Run the fixed hourly SELECT through an injected Athena client."""

from datetime import datetime, timezone
from time import sleep
from typing import Any, Callable, Protocol

from .models import HourlyRead, HourlyRow, QueryError, QueryWindow
from .query_templates import (
    GOLD_CATALOG,
    GOLD_DATABASE,
    HOURLY_COLUMNS,
    HOURLY_SELECT,
    RESULT_ROW_LIMIT,
    hourly_parameters,
)

MAX_POLLS = 20
POLL_SECONDS = 0.25
MAX_PAGES = 8
RETRYABLE_READ_CODES = {"TooManyRequestsException", "ThrottlingException", "InternalServerException"}


class AthenaClient(Protocol):
    """The small part of the SDK that the adapter needs."""

    def start_query_execution(self, **kwargs: Any) -> dict[str, Any]:
        """Submit the repository-owned query."""

    def get_query_execution(self, **kwargs: Any) -> dict[str, Any]:
        """Read the execution state."""

    def get_query_results(self, **kwargs: Any) -> dict[str, Any]:
        """Read one page of result rows."""

    def stop_query_execution(self, **kwargs: Any) -> dict[str, Any]:
        """Request cancellation when the polling budget expires."""


def _read_with_retry(operation: Callable[..., dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    """Retry an idempotent status or page read once on a transient service error."""
    try:
        return operation(**kwargs)
    except Exception as error:
        # Botocore ClientError exposes the service code through response.
        response = getattr(error, "response", {})
        if response.get("Error", {}).get("Code") not in RETRYABLE_READ_CODES:
            raise
    sleep(POLL_SECONDS)
    return operation(**kwargs)


def _cells(raw_row: dict) -> tuple[str | None, ...]:
    """Decode Athena string cells, where an empty datum represents SQL null."""
    data = raw_row["Data"]
    if not isinstance(data, list) or len(data) != len(HOURLY_COLUMNS):
        raise QueryError("Athena returned a row with an unexpected width.")
    cells = tuple(cell.get("VarCharValue") for cell in data)
    if any(cell is not None and not isinstance(cell, str) for cell in cells):
        raise QueryError("Athena returned an invalid result cell.")
    return cells


def _hourly_row(raw_row: dict) -> HourlyRow:
    """Translate Athena's wire representation into typed gold values."""
    timestamp, energy, minutes, complete, kitchen, laundry, heater_ac, other = _cells(raw_row)
    if timestamp is None or minutes is None or complete not in ("true", "false"):
        raise QueryError("Athena returned an incomplete hourly row.")
    period_start = datetime.fromisoformat(timestamp)
    if period_start.tzinfo is not None or " " not in timestamp:
        raise QueryError("Athena returned an unexpected timestamp format.")
    # An Athena TIMESTAMP has no offset. The gold clock is provisionally
    # labelled UTC, so attach the label without shifting the source time.
    return HourlyRow(
        period_start=period_start.replace(tzinfo=timezone.utc),
        energy_kwh=None if energy is None else float(energy),
        minutes_with_data=int(minutes),
        is_complete=(complete == "true"),
        kitchen_kwh=None if kitchen is None else float(kitchen),
        laundry_kwh=None if laundry is None else float(laundry),
        heater_ac_kwh=None if heater_ac is None else float(heater_ac),
        other_kwh=None if other is None else float(other),
    )


class AthenaExecutor:
    """Read hourly gold through a trusted workgroup with enforced output settings."""

    def __init__(self, client: AthenaClient, *, workgroup: str) -> None:
        """Accept a client with finite timeouts and SDK retries disabled."""
        self._client = client
        self._workgroup = workgroup

    def fetch_hours(self, window: QueryWindow) -> HourlyRead:
        """Submit, wait and fetch a complete result or raise a safe QueryError."""
        try:
            started = self._client.start_query_execution(
                QueryString=HOURLY_SELECT,
                QueryExecutionContext={"Catalog": GOLD_CATALOG, "Database": GOLD_DATABASE},
                WorkGroup=self._workgroup,
                ExecutionParameters=hourly_parameters(window),
            )
            execution_id = started["QueryExecutionId"]
            if not isinstance(execution_id, str) or not execution_id:
                raise QueryError("Athena returned an invalid execution ID.")
            self._wait(execution_id)
            rows = self._read_rows(execution_id)
        except QueryError:
            raise
        except Exception:
            # SDK errors can include operational details. Keep the tool-facing
            # error generic even if the client or response shape changes.
            raise QueryError("The Athena hourly read failed.") from None
        return HourlyRead(rows, {"source": "athena", "source_id": execution_id})

    def _wait(self, execution_id: str) -> None:
        """Follow queued/running states with a bounded number of polls."""
        for poll in range(MAX_POLLS):
            response = _read_with_retry(self._client.get_query_execution, QueryExecutionId=execution_id)
            state = response["QueryExecution"]["Status"]["State"]
            if state == "SUCCEEDED":
                return
            if state not in ("QUEUED", "RUNNING"):
                raise QueryError("Athena did not complete the hourly read.")
            if poll + 1 < MAX_POLLS:
                sleep(POLL_SECONDS)
        try:
            self._client.stop_query_execution(QueryExecutionId=execution_id)
        except Exception:
            # Cancellation is best-effort. Either way the timed-out read fails.
            pass
        raise QueryError("The Athena hourly read timed out.")

    def _read_rows(self, execution_id: str) -> list[HourlyRow]:
        """Consume sequential pages, verifying the header and all row limits."""
        rows: list[HourlyRow] = []
        token: str | None = None
        seen_tokens: set[str] = set()
        for page_index in range(MAX_PAGES):
            options = {"NextToken": token} if token is not None else {}
            page = _read_with_retry(
                self._client.get_query_results, QueryExecutionId=execution_id, MaxResults=1000, **options
            )
            raw_rows = page["ResultSet"]["Rows"]
            if not isinstance(raw_rows, list):
                raise QueryError("Athena returned an invalid result page.")
            # Athena SELECT results contain the column labels as the first
            # result row. Later pages contain data rows only.
            if page_index == 0:
                if not raw_rows or _cells(raw_rows[0]) != HOURLY_COLUMNS:
                    raise QueryError("Athena returned unexpected result columns.")
                raw_rows = raw_rows[1:]
            elif not raw_rows:
                raise QueryError("Athena returned an empty continuation page.")
            if len(rows) + len(raw_rows) > RESULT_ROW_LIMIT:
                raise QueryError("Athena exceeded the hourly result limit.")
            rows.extend(_hourly_row(row) for row in raw_rows)
            if "NextToken" not in page:
                return rows
            token = page["NextToken"]
            if not isinstance(token, str) or not token or token in seen_tokens:
                raise QueryError("Athena returned an invalid pagination token.")
            seen_tokens.add(token)
        raise QueryError("Athena exceeded the result page limit.")
