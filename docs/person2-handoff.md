# Person 2: first mock API increment

Decision for our 7–10 day delivery: start with a small FastAPI service and an
explicit provisional contract. A React/TypeScript/Vite SPA now consumes it in `web/`.
An opt-in DynamoDB demo adapter is now implemented locally. No deployed
infrastructure or live AI integration is included.
Python 3.14.10 was used; Node 24 LTS is the frontend target. Persistent teaching
and stack instructions are in `AGENTS.md`.

## Run on Windows PowerShell

Run from the repository root. The project `.venv` already exists; on another
machine create it once with `py -3.14 -m venv .venv`. Use its executable directly
so PowerShell activation policy and the system's older `python` do not interfere.

```powershell
# Reproduce the pinned development environment when needed (downloads packages).
.\.venv\Scripts\python.exe -m pip install -r api\requirements-dev.txt

# Start locally; stop with Ctrl+C. Mock is also the default when this is unset.
$env:APP_DATA_MODE = 'mock'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir api --reload
```

Open http://127.0.0.1:8000/docs to try the typed requests interactively.
The bare http://127.0.0.1:8000/ now redirects there. Previously `/` had no route
and returned `{"detail":"Not Found"}` even while the API was healthy.
Use http://127.0.0.1:8000/health for the JSON health check, and port 5173 for the React app.
In a second terminal, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -c api\pytest.ini api\tests -q
.\.venv\Scripts\python.exe -m pip check
Invoke-RestMethod 'http://127.0.0.1:8000/consumption?household_id=household-1&start=2009-06-01T00:00:00Z&end=2009-06-02T00:00:00Z&grain=daily'
```

`api/requirements.txt` pins runtime dependencies including transitive packages;
`requirements-dev.txt` includes those pins plus test dependencies. `.env.example`
is safe documentation; the API does not automatically load `.env` files. No AWS
settings are needed. Unsupported `APP_DATA_MODE` values deliberately fail startup.

## Provisional contract and fixture decisions

- `GET /health` reports mock process health. `GET /consumption`, `/anomalies`, and
  `/forecast` require `household_id`, `start`, `end`. Use ISO datetimes with `T`
  and explicit offsets; they are normalized to UTC. Start is inclusive and end
  exclusive, selecting buckets by their **start timestamp**.
- Consumption accepts `grain=hourly` (default) or `daily`. Daily boundaries must
  be UTC midnight; reject partial-day requests rather than label partial sums
  as full daily totals. `energy_kwh` is energy per interval, not kW power.
- `household-1` has 168 continuous synthetic hours in
  `[2009-06-01T00:00:00Z, 2009-06-08T00:00:00Z)`. Seven daily totals are calculated
  from those readings, totaling 111.80 kWh. Three anomalies reference the same
  hourly values: June 2 at 18:00, June 4 at 19:00, June 6 at 12:00.
- The illustrative forecast origin is June 8 at 00:00 UTC. Its 24 hourly targets
  cover `[June 8 00:00, June 9 00:00)` by repeating June 7's observations.
  Queries filter **target** timestamps. This is not a trained/validated model.
- UTC is **only a demo convention**. The source dataset's timezone is unconfirmed;
  none of these synthetic readings are represented as source dataset records.
- Read envelopes include typed `items`, `units`, `requested_start/end`,
  `covered_start/end`, `next_cursor=null`, and `is_demo=true`. Coverage is the
  boundaries of returned whole buckets; hourly coverage can extend beyond an
  unaligned requested end. Empty results have null coverage. Results are ordered,
  deterministic, and bounded at 168/7/3/24 items (hourly/daily/anomalies/forecast),
  so this increment needs no pagination. Add stable query-bound cursors before
  introducing an unbounded real repository.
- Household IDs follow `household-<positive integer>`. Well-formed unknown IDs
  and valid windows without data return `200` with empty items. Invalid inputs,
  missing fields, unsupported grain, and extra parameters return FastAPI's `422`
  `detail` error list. Equal or reversed dates are invalid.
- `POST /chat` accepts the same household/window plus `request_type=chat` and
  `message`; or `request_type=weekly_summary` without a message. Both return
  `status=placeholder`, `assistant_connected=false`, `is_demo=true`, empty
  citations, and an explicit placeholder / Bedrock-disconnected explanation.

Example weekly-summary JSON for `/docs`:

```json
{"household_id":"household-1","start":"2009-06-01T00:00:00Z","end":"2009-06-08T00:00:00Z","request_type":"weekly_summary"}
```

## File tour, checks, and handoffs

`api/app/main.py` owns routes and startup; `models.py` defines Pydantic contracts;
`service.py` builds response envelopes; `repository.py` owns the fixtures, shared
daily aggregation, and the window-aware storage protocol. `api/tests/` exercises actual routes and
startup in memory, removes common AWS credential settings, and blocks application
network connections (allowing only Windows' internal event-loop socketpair).

Validation on Windows/Python 3.14.10: **56 tests passed**, `pip check` passed,
and a real local Uvicorn smoke check passed for `/health`, `/docs`, and the
13.46 kWh daily response; the temporary server was stopped. The test dependency
currently emits one upstream Starlette warning about future migration from
HTTPX to HTTPX2. There are no failing tests. No live AWS/AI checks apply here.

For example, the daily consumption request above enters the **route**, which
validates its query. The **service** asks the **repository** for daily observations.
The mock repository sums June 1's 24 hourly buckets; the DynamoDB repository queries
the stored daily partition (seeded using that same calculation). FastAPI returns **JSON** with
one daily item (`energy_kwh=13.46`), units and covered dates. Routes handle HTTP;
services handle rules; repositories supply data. Changing storage should not
require rewriting the HTTP routes.

Person 1 can provision the tables below and agree normalized gold records for
the small loader boundary; Person 3 can replace the assistant placeholder and supply model outputs.
Confirm source timezone and agree any contract changes through review, while
continuing against these fixtures. The four React views now use this API; next
integration work is replacing the mock repository and assistant through reviewed
contracts. No commits or pushes were made by the implementation tasks.

## React SPA increment

See [web/README.md](../web/README.md) for exact PowerShell start/check commands,
the file tour, deployment base-URL examples, and the SPA/Razor comparison.
Start FastAPI on port 8000, then run `npm.cmd run dev` from `web/` and visit
http://127.0.0.1:5173. The default `/api` prefix is stripped by Vite's development
proxy. Production must provide that route or set `VITE_API_BASE_URL` to the actual
API prefix **before building**; no endpoint suffix or credentials belong in it.

History uses inclusive calendar dates (converted to the API's exclusive end).
Forecast has its own June 8 target window and separate actual/forecast series.
All displayed records come from the API; demo flags, units, UTC caveats and
placeholder assistant behavior remain visible. Requests are cancelled/ignored
when filters change. Validation: 19 frontend tests, production build, lint, and
a real desktop/mobile Chrome smoke check passed. npm reports zero vulnerabilities.

Review update (November 8): 57 API tests, 20 frontend tests, build, lint, and a
committed Playwright Chromium smoke flow passed locally. Run `npm.cmd run test:e2e`
from `web/`; first install its browser with `npx.cmd playwright install chromium`.
The test starts/stops its own mock servers on 18000/15173. The new demo-checks
workflow runs the same checks in CI; the remote workflow has not been run here.
Fixed weekly-summary requests deleting an unsent chat draft. See `web/README.md`
for setup, browser installation, reporting, and the remaining upstream API warning.

## DynamoDB adapter and synthetic seed loader

`APP_DATA_MODE=mock` remains the default. `storage.py` selects the repository;
only `APP_DATA_MODE=dynamodb` imports/constructs the SDK client. DynamoDB startup
never reads, seeds, or creates tables. Explicit Region and three distinct table
names are required before client construction. No tables were created or accessed
in this task; only local SDK Stubber responses and a no-client CLI dry run ran.

### Three table schemas

Provision these **through Terraform**, separately from the loader. Each uses
`BillingMode=PAY_PER_REQUEST` (on-demand), string partition key `PK` (`HASH`),
string sort key `SK` (`RANGE`), and no secondary indexes. Only `PK` and `SK` go in
DynamoDB's `AttributeDefinitions`; the remaining fields are ordinary attributes.
The example names below can be changed, provided API and loader use the same names.

| Example table | PK | SK | Ordinary attributes |
| --- | --- | --- | --- |
| `g4-greentrack-demo-consumption` | `HOUSEHOLD#<id>#GRAIN#hourly` or `...#GRAIN#daily` | interval start | household_id, timestamp, interval_end, grain, energy_kwh, is_demo, schema_version |
| `g4-greentrack-demo-anomalies` | `HOUSEHOLD#<id>` | affected hour start | household_id, timestamp, interval_end, observed_kwh, expected_kwh, score, reason, is_demo, schema_version |
| `g4-greentrack-demo-forecasts` | `HOUSEHOLD#<id>#ORIGIN#<origin>` | **target** hour start | household_id, timestamp, interval_end, forecast_origin, energy_kwh, method, is_demo, schema_version |

All key timestamps use fixed-width UTC with six fractional digits. For example,
the June 1 hourly record has `PK=HOUSEHOLD#household-1#GRAIN#hourly` and
`SK=2009-06-01T00:00:00.000000Z`, with `energy_kwh=0.30`. The computed daily record
uses `PK=HOUSEHOLD#household-1#GRAIN#daily`, that same SK, next-day interval_end,
and `energy_kwh=13.46`. They are different keys, so neither overwrites the other.
One forecast example is:

```json
{
  "PK": "HOUSEHOLD#household-1#ORIGIN#2009-06-08T00:00:00.000000Z",
  "SK": "2009-06-08T01:00:00.000000Z",
  "household_id": "household-1",
  "timestamp": "2009-06-08T01:00:00.000000Z",
  "interval_end": "2009-06-08T02:00:00.000000Z",
  "forecast_origin": "2009-06-08T00:00:00.000000Z",
  "energy_kwh": 0.40,
  "method": "illustrative_previous_day",
  "is_demo": true,
  "schema_version": 1
}
```

An origin names the forecast run; `timestamp`/SK names the hour being predicted.
The API selects one active **24-hour illustrative run**, defaulting to June 8
00:00 UTC. Optional `DYNAMODB_FORECAST_ORIGIN` selects another explicit run;
there is no automatic latest-origin search or mixing runs in one response.
The seed loader always writes our existing June 8 fixture run. UTC remains a
demo convention, not a claim about the UCI source dataset timezone.

Normal reads call **Query**, never Scan: PK equality plus a timestamp key range.
DynamoDB `BETWEEN` includes its upper bound, so the reader queries through
`end - 1 microsecond` to preserve our inclusive-start/exclusive-end API contract.
It follows every `LastEvaluatedKey`, including one on an empty page. Public
responses stay unchanged (`next_cursor=null`); internal SDK pagination is consumed
before returning. A request exceeding 10,000 rows or 100 pages fails with safe
HTTP 503 rather than silently returning a partial window. Use a smaller window.
The API role needs `dynamodb:Query`; the separate seed role needs
`dynamodb:BatchWriteItem` on these named tables.

### Exact PowerShell commands, from the repository root

Install the pinned SDK locally if needed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r api\requirements-dev.txt
```

Safe preview, **no client, credentials lookup, or AWS calls** (omitting both flags
also defaults to this dry run):

```powershell
.\.venv\Scripts\python.exe api\seed_demo.py --region eu-central-1 --consumption-table g4-greentrack-demo-consumption --anomalies-table g4-greentrack-demo-anomalies --forecasts-table g4-greentrack-demo-forecasts --dry-run
```

It previews **202** rows: 168 hourly + 7 computed daily, 3 anomalies, 24 forecast
targets. **Later only**, after the named demo tables exist and your approved AWS
authentication/Region are ready, this explicit flag enables actual writes:

```powershell
.\.venv\Scripts\python.exe api\seed_demo.py --region eu-central-1 --consumption-table g4-greentrack-demo-consumption --anomalies-table g4-greentrack-demo-anomalies --forecasts-table g4-greentrack-demo-forecasts --write
```

Rerunning replaces items at the same stable keys; it does not append duplicates.
It overwrites matching keys, so use the dedicated demo tables. Writes are batches
of at most 25. Only unprocessed items are retried, with jittered exponential
backoff, at most four sends per batch. HTTP/transport retries use SDK standard
mode with three total attempts. BatchWrite is not atomic: an interrupted or
failed load may have partially written, returns a nonzero exit, and can be
rerun with the same keys. No seeding occurs during API cold starts.

Later API selection (this starts the AWS-backed path; **not run during this task**):

```powershell
$env:APP_DATA_MODE = 'dynamodb'
$env:DYNAMODB_REGION = 'eu-central-1'
$env:DYNAMODB_CONSUMPTION_TABLE = 'g4-greentrack-demo-consumption'
$env:DYNAMODB_ANOMALIES_TABLE = 'g4-greentrack-demo-anomalies'
$env:DYNAMODB_FORECASTS_TABLE = 'g4-greentrack-demo-forecasts'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir api --reload
# Return to offline development before starting again:
$env:APP_DATA_MODE = 'mock'
```

Synthetic rows and responses retain **is_demo=true**. Unknown/non-demo provenance,
invalid stored rows, or exhausted read retries return safe 503 errors, without
raw AWS diagnostics or a silent fallback to mock data. For compatibility,
`/health` keeps its existing `data_mode=mock` and `is_demo=true`: these describe
the synthetic dataset, not the storage provider. It is process health, not an
AWS table readiness check. Chat/weekly summary stay disconnected placeholders.

`dynamodb_items.py` is the shared key/normalization boundary; `seed_demo.py` maps
existing typed points and writes them. A future gold loader should supply agreed
normalized records here, without implementing Glue exports or SageMaker payloads.
Real-data provenance needs an explicit response-contract update before serving
real rows; this adapter deliberately supports only the existing demo contract.

Offline validation: **94 pytest tests** passed, including SDK Stubber mapping,
pagination, half-open ranges, empty results, safe errors, default no-client mode,
and idempotent batch/retry behavior. The CLI dry run previewed 202 rows. Existing
frontend tests (20), build, and lint passed. SDK network retry internals, live AWS
permissions/resources, and remote CI are unverified; no AWS or Docker was used.

## Pull-request workflow

The existing `demo-checks.yml` now cancels outdated runs per PR and retains browser
failure reports. It keeps Python 3.14, Node 24, pinned requirements, `npm ci`,
tests, lint, build, and a credential-free mock browser flow in one workflow.
There is also a conditional Terraform job: no Terraform exists today, so it
explicitly skips. When added, register deployable roots in `.github/terraform-roots.txt`,
pin `.terraform-version`, and commit provider locks. It then checks fmt and runs
backend-disabled init plus validate, never an AWS plan or apply.
See [pr-checks.md](pr-checks.md) for matching local commands and finding failed
GitHub step logs/artifacts. GitHub execution and real Terraform validation have
not been run locally.

Local PR-check verification passed: pinned Python dependencies and `pip check`,
clean cached `npm ci`, 94 pytest tests, 20 frontend tests, lint, production build,
and one Playwright Chromium flow. The Terraform helper reports the expected skip;
its registration/lock/path discovery policies were checked using temporary local
fixtures without invoking Terraform. No Terraform configuration or CLI exists
here, so fmt/init/validate remain unrun. The upstream HTTPX warning remains.
