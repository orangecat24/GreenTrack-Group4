# Person 2: first mock API increment

Decision for our 7–10 day delivery: start with a small FastAPI service and an
explicit provisional contract. A React/TypeScript/Vite SPA now consumes it in `web/`.
An opt-in DynamoDB demo adapter and Terraform application module are implemented
locally. Person 2's application infrastructure is prepared, not deployed by these
tasks. The teammate reports that the foundation state bucket was already applied;
see [the foundation handoff](foundation-handoff.md) for its role/backend details
and verification limits. Live AI integration is not included.
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

The tables below are now defined in `infra/challenge1`; Person 1 can agree normalized gold records for
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
The Terraform job discovers the existing bootstrap/dev roots, installs the pinned
CLI and checks formatting, backend-disabled init and validate, never an AWS plan
or apply. Shared/application child modules are validated through dev, not
registered as new roots. Each root retains its committed provider lock.
See [pr-checks.md](pr-checks.md) for matching local commands and finding failed
GitHub step logs/artifacts. GitHub-hosted execution remains unverified; the
latest local Terraform results are recorded below.

Earlier PR-check verification passed: pinned Python dependencies and `pip check`,
clean cached `npm ci`, 94 pytest tests, 20 frontend tests, lint, production build,
and one Playwright Chromium flow. At that earlier increment Terraform discovery
skipped because no configurations existed. The new infrastructure check results
are recorded below. The upstream HTTPX warning remains.

## Person 2 application infrastructure (November 10)

`infra/challenge1` is a child module of the existing `infra/environments/dev`
root: Python 3.14 x86_64 Lambda/Mangum, HTTP API, three matching on-demand
DynamoDB tables, private frontend S3, CloudFront/OAC, seven-day logs and six
non-secret SSM parameters. Shared backend/bootstrap/IAM permissions are unchanged.
The execution role has logs only in mock mode; explicit DynamoDB mode adds only
Query on these tables. Configuration goes directly into Lambda's environment
and is also published to SSM, with no runtime SSM lookup. No startup seeding.

The public API/SPA contracts remain unchanged. Gateway-only CORS allows the
CloudFront origin and local port-5173 origins. Build Vite using the HTTPS API
base output, without `/api`; the Vite proxy remains local-only. Forecast and
assistant remain clearly labeled illustrative/placeholder features.

See [application-infrastructure.md](application-infrastructure.md) for the resource
tour, exact PowerShell/Linux checks and later-only deployment commands, config
inputs/outputs, cache rules, billable categories and integration limits. Build
the ZIP before any future plan. The existing CI now builds and tests the actual
Linux artifact offline; Windows can build but cannot execute its native library.
Shared deployment-role trust/permission hardening is recommended, not a technical
blocker. The current broad role and main/PR trust are deliberately retained; see
[the recorded foundation decision](foundation-handoff.md#current-permission-decision).
Ordinary PR checks remain credential-free and deployment automation is not enabled.

Local verification: **103 API tests**, **20 frontend tests**, lint, build and
**one Playwright smoke flow** passed; `pip check` passed. The Linux-targeted ZIP
built with a cp314 x86_64 pydantic-core ELF library. Terraform **1.17.0** fmt,
backend-disabled init with readonly provider locks and validate passed for
bootstrap/dev, including both child modules. A portable CLI was downloaded into
ignored `.qa` without global changes. Provider selections were not changed.
Actual Linux ZIP execution/CI remains unrun locally (Windows; no running Docker
daemon). Validation is not an AWS plan: live IAM, quotas, runtime, CORS and
CloudFront delivery require later authorized AWS checks. No AWS API calls,
plan/apply, seeding, uploads, invalidations, commits or pushes were performed.

## Foundation handoff correction (November 11)

The teammate's PR description, supplied after the application increment, confirms
that bootstrap was already applied from his laptop and provides the deployment
role ARN, Region and dev state location. These are now preserved in
[foundation-handoff.md](foundation-handoff.md), linked from the root README and
deployment guide. The application's existing dev-root wiring already matches
the handoff, so no Terraform resource, backend, UI or API change was needed.
The bootstrap header now explicitly says it was already applied and points to
the state owner; shared IAM code and provider locks are unchanged.

The foundation role can continue to be used as designed, subject to its broad
permissions and PR trust. Hardening is an improvement, not an absolute technical
requirement. The teammate's OIDC job settings are documented for later use, not
enabled in ordinary checks. AGENTS.md now requires persistent Markdown records
for substantial changes/teammate handoffs, alongside a junior-friendly chat report.
No AWS service or state access was used to verify the reported deployment status.

Verification for this correction: Terraform 1.17.0 formatting and validation
passed for bootstrap/dev, root discovery passed, foundation identifiers/trust
subjects matched the existing configuration, and 20 local Markdown links plus
`git diff --check` passed. Only Markdown and a bootstrap explanatory comment
changed; application tests were not rerun. No AWS authentication, state access,
deployment, commit or push occurred.

## Deployment pipeline preparation (November 11)

The repository now has an explicitly activated main deployment pipeline and
optional AWS PR planning. See [deployment-pipeline.md](deployment-pipeline.md)
for exact setup, configuration names, resource costs, readiness evidence,
first-run behavior, blockers and recovery; the root README links to it.

`demo-checks.yml` is reused, not copied. It runs tests/build/local smoke and
offline Terraform checks without credentials, and can pass the tested Linux ZIP
to the main job in the same run. `deploy-main.yml` uses OIDC only after those
checks, verifies the account, plans/applies the same saved dev-root plan, builds
Vite using the API output, uploads hashed assets before HTML, invalidates only
changed entry HTML, and checks the actual HTTPS site/API/CORS with Playwright.
Its workflow-level concurrency never cancels an active apply. Activation is
off unless a maintainer sets repository variable `DEPLOY_ENABLED=true`.

`aws-pr-plan.yml` reports pending unless a trusted same-repository PR has the
`aws-plan` label and an owner-approved separate read-only planning role is
configured via `AWS_PR_PLAN_ENABLED`/`AWS_PR_PLAN_ROLE_ARN`. The broad deployment
role is not reused under a read-only label. Speculative PR plans never lock/write
state, apply or upload; optional planning does not block main deployment.
No shared role/policy, Terraform resource, UI or API behavior changed.

Read-only readiness checks now verify the named state object exists (metadata
only) and the GitHub role/trust/attached and inline policies match the handoff.
No state contents were downloaded, and those checks cannot prove GitHub OIDC,
state resource ownership, effective deployment write access or quotas.

An observed local defect was fixed: cached live backend metadata caused
`init -backend=false` to attempt a state metadata request (403). The check helper
now isolates TF_DATA_DIR under ignored build/terraform-checks for each root,
preserving the user's original cache. A regression test protects this behavior.
The later isolated init/validate checks passed without reusing that live backend.

Validation: **119 Python tests** (103 API + 16 deployment/helper regressions),
**20 frontend tests**, lint, production build, **one local browser smoke**,
`pip check`, actionlint **1.7.12** for all workflows, and Terraform **1.17.0**
fmt/backend-disabled readonly init/validate for both roots passed. The Linux ZIP
rebuilt at 20,376,799 bytes with the same SHA256 as before; the deployed browser
test's collection passed without execution. Linux ZIP execution, GitHub-hosted
Actions/OIDC/artifact transfer, AWS plans/applies/writes and deployed HTTPS/CORS
remain unexecuted. No account/repository settings, seed writes, uploads,
invalidations, commits, merges or pushes were performed from this session.
