"""The approved query and its positional Athena parameters."""

from .models import MAX_HOURS, QueryWindow

# This pair is the allowlist for this dataset. The table is fixed in the SQL,
# and Athena resolves it only in this trusted catalog and database.
GOLD_CATALOG = "AwsDataCatalog"
GOLD_DATABASE = "g4_greentrack_dev_gold"
RESULT_ROW_LIMIT = MAX_HOURS
HOURLY_COLUMNS = (
    "period_start", "energy_kwh", "minutes_with_data", "is_complete",
    "kitchen_kwh", "laundry_kwh", "heater_ac_kwh", "other_kwh",
)

# Ask for one extra row so a duplicate or other overflow cannot silently
# truncate the largest valid window. All four tools share this projection.
HOURLY_SELECT = f"""SELECT {", ".join(HOURLY_COLUMNS)}
FROM hourly_consumption
WHERE household_id = ?
  AND period_start >= ?
  AND period_start < ?
ORDER BY period_start
LIMIT {RESULT_ROW_LIMIT + 1}"""


def hourly_parameters(window: QueryWindow) -> list[str]:
    """Bind a validated ID and timestamp literals in placeholder order."""
    # ExecutionParameters takes SQL literals as strings, including the quotes
    # around VARCHAR values. QueryWindow validates the ID at the tool boundary.
    household = window.household_id.replace("'", "''")
    start = window.start.replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    end = window.end.replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    return [f"'{household}'", f"CAST('{start}' AS TIMESTAMP)", f"CAST('{end}' AS TIMESTAMP)"]
