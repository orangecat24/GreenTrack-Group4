# P3 02 approved energy query tools

The four Python tools read one bounded slice of hourly gold. The executor
supplies rows and provenance, then the tools build a chronological grid and
calculate the requested result. The fixture executor uses local synthetic JSON.
The Athena adapter takes an injected client. Both paths use the same
calculations. [P3 01 fixtures](../fixtures/person3/README.md) ·
[Assistant contract draft](../contracts/assistant.md)

## Run offline

From the repository root, use a working Python interpreter and Node for the
P3 01 checker. The Python tests use the standard library and a fake Athena
client. The fixture path requires only the local JSON file.

```powershell
python -B -m unittest discover -s assistant/tests -v
node fixtures/person3/check.mjs
git diff --check
```

If the Windows `python` alias is unavailable, substitute the full path to an
installed interpreter. The implementation checks ran with Python 3.14.

To print a synthetic result in PowerShell, run this from the repository root.

```powershell
@'
import json
from pathlib import Path
from assistant.tools import FixtureExecutor, QueryTools

tools = QueryTools(FixtureExecutor(Path("fixtures/person3/gold_hourly.json")))
result = tools.run(
    "consumption_totals",
    household_id="household-1",
    start="2009-06-01T00:00:00Z",
    end="2009-06-02T00:00:00Z",
)
print(json.dumps(result, indent=2))
'@ | python -B -
```

## Tool contract for Person 2

Call `QueryTools.run(name, *, household_id, start, end)` with one of the
approved names below. Requests take only those arguments. The dataset scope
defaults to `household-1` and is set by the application when constructing
`QueryTools`. IDs must match the draft household format and the dataset scope.

Provide ISO date-times with `T` and an explicit timezone. Bounds are normalized
to UTC, must land on whole hours and select bucket starts in `[start, end)`.
The positive window limit is 31 days (744 hours). UTC labels follow the
provisional historical source clock.

| Tool name | Result data | Synthetic result for 1 June 2009 |
| --- | --- | --- |
| `consumption_totals` | `observed_kwh` sums available hourly energy, including partial hours. | 9.75 kWh with 210 of 1,440 minutes measured. |
| `hourly_patterns` | `hours` lists each requested hour with `period_start`, `observed_kwh`, `minutes_with_data` and `bucket_status`. | 01:00 has 0.75 kWh over 30 minutes, 02:00 is all-null, 03:00 is absent, 04:00 is a measured zero, and 05:00 has the largest observed hour at 7.5 kWh. |
| `weekday_weekend` | Each of `weekday` and `weekend` returns `mean_kwh_per_complete_hour`, `eligible_hours` and group coverage. | Monday averages 3.0 kWh per complete hour across 3 hours. Weekend is null with 0 eligible hours. |
| `submetering_breakdown` | Each of `kitchen_kwh`, `laundry_kwh`, `heater_ac_kwh` and `other_kwh` returns `observed_kwh` and `hours_with_values`. | 1.95, 1.05, 2.25 and 4.5 kWh respectively, each with 4 hours containing values. |

Weekday means Monday through Friday on the same clock. Each group uses its own
count of complete hours as the denominator. Measured zero contributes to the
count. Partial, all-null and absent hours are excluded from the mean and
remain visible in coverage. A group with zero eligible hours has a null mean.
Coverage describes active-power readings. The four breakdown columns are
summed independently across their non-null values, including any readings
available in a bucket with missing active power. The tool carries the
published `other_kwh` residual, including null or signed values. Coverage
can differ across columns when some readings are missing, so use the
per-column counts. Sub-meters describe circuits or groups.

Every response includes the tool name, household, normalized window and
`unit: "kWh"`. Successful reads include coverage (expected and measured
minutes and complete, partial, all-null and absent hour counts), source
provenance and the tool's data. The fixture day has 3 complete, 1 partial,
1 all-null and 19 absent hours. The largest observed hour in the series
represents interval energy in kWh. The separate daily gold fixture's maximum
single-minute power is 12 kW.

- `ok` means at least one applicable measurement or group mean is available.
- `no_data` means the read completed and the tool found no eligible values.
  The caller can use the coverage and null values to explain the result.
- `error` has a safe retry message and null data, coverage and provenance.
  Invalid names and malformed windows raise `ToolInputError` before any
  read. Unexpected extra keyword arguments are rejected by Python.

The local result has `provenance: {"source": "synthetic_fixture", "source_id":
"gold_hourly.json"}`. The future Athena path uses `source: "athena"` with the
query execution ID as `source_id`. That ID identifies the query, while the
gold publication or snapshot needs its own reference in later live evidence.

## SQL and permissions review for Person 1

All tools share one fixed SELECT on
`AwsDataCatalog.g4_greentrack_dev_gold.hourly_consumption`. The query uses
`household_id` and `period_start` for its parameterized filter and reads
`period_start`, `energy_kwh`, `minutes_with_data`, `is_complete`,
`kitchen_kwh`, `laundry_kwh`, `heater_ac_kwh` and `other_kwh`.
The approved catalog, database and table are repository constants.
The query asks for at most 745 rows so the adapter can reject results
over the 744-row budget. The tools also reject duplicate, misaligned or
out-of-window rows. Please review the projected types and nullability, the
half-open timestamp filter, the observed-energy sums, and the complete-hour
comparison rule. [Gold job](../data/glue/gold_job.py) ·
[Fixed SELECT](query_templates.py)

For later live operation, supply an explicitly approved assistant Athena
workgroup with enforced result settings and a bytes-scanned limit. The adapter
requires `athena:StartQueryExecution`, `athena:GetQueryExecution`,
`athena:GetQueryResults` and `athena:StopQueryExecution` for that workgroup.
Scope the role's Glue Data Catalog metadata and Lake Formation
`DESCRIBE`/`SELECT` grants to the approved catalog/database/table and needed
columns, with `lakeformation:GetDataAccess` where required. Provide source
object reads for the approved Iceberg metadata and data path through the
agreed access model.

For query results, reserve a dedicated assistant prefix under the approved
results location. Scope result-object reads and writes and the associated
bucket location/list access to that path as applicable. Confirm encryption
at the workgroup and authorize only the necessary KMS use on the selected key
if using SSE-KMS. Keep source storage and catalog access read-only.
[Data lake output](../infra/challenge2/outputs.tf)

For the future injected SDK client, set finite connect and read timeouts
and use `total_max_attempts=1` so retry limits stay in one place. The adapter
allows 20 status polls with 250 ms between pending states and best-effort
cancellation after the last pending poll. It reads up to eight result pages
and retries each status or result read once after a retryable service error.
The elapsed time includes SDK request time. A failed execution or incomplete
fetch returns a safe error to the caller.

P3 04 still needs Person 1's confirmation of Spark/Athena clock handling,
deployed catalog types, the gold run or snapshot, scoped runtime grants and
independently reconciled arithmetic on the approved live window. Person 1's
gold handoff reports AWS checks for a separate pipeline fixture. The P3 02
evidence here comes from the synthetic dataset and fake Athena responses.
[Gold handoff](../docs/data-lake-gold.md) ·
[Person 3 assistant handoff](../docs/person3-handoff.md)
