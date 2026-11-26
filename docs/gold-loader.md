# Gold backend and consumption loader: stage 3

Stage 4 frontend support is now complete; see [gold-frontend.md](gold-frontend.md)
for its results and opt-in smoke prerequisites. Earlier rollout warnings below
describe the stage 3 boundary. Live destination preview/load/deployment remain
separate gates and have not been performed by these implementation stages.

Implemented offline November 26, 2026 on `test/person2-app-validation`.
The [integration checklist](real-data-integration.md) remains the source of
stage status/evidence. No AWS calls, writes, Terraform plan/apply, deployment,
dependency upgrades, commits or pushes occurred in stage 3. Existing stage 1/2
Markdown edits and ignored genuine exports were preserved.

## What now works

Storage (`APP_DATA_MODE`) and provenance (`APP_DATA_SOURCE`) are independent:

| Mode | Source | Behavior |
| --- | --- | --- |
| mock (default) | synthetic (default) | Existing fixtures; no AWS clients, credentials or network calls. |
| mock | gold | Startup error before any SDK client construction. |
| dynamodb | synthetic | Existing schema-1 synthetic reads, demo labels retained. |
| dynamodb | gold | Schema-2 gold consumption reads; anomaly/forecast responses explicitly unavailable, chat/summary disconnected placeholders. |

Health reports `data_mode`, `data_source` and consumption-source `is_demo`
accurately from initialized configuration. It does **not** query DynamoDB or
claim authorization, loaded data or model readiness.

Read responses add `data_source`, `status` and `note`. Consumption energy may be
null and carries `minutes_with_data`/`is_complete`; synthetic quality fields are
null because they are invented observations. Gold rows require consistent
numeric counts, quality flags, interval bounds, PK/SK and provenance. A valid
empty gold response stays `data_source=gold`, `is_demo=false`; failed storage is
a safe 503. Existing paths, parameters, units, daily midnight validation,
inclusive start/exclusive end and pagination bounds are retained.

Gold mode never falls back to synthetic anomaly or forecast tables. Those
endpoints return HTTP 200, empty items, null coverage, `status=unavailable`,
`data_source=unavailable`, `is_demo=true` (placeholder) and an explicit note.
Unavailable forecast origins/target dates are null; available synthetic forecasts
still require their original dates and numeric values. Chat/summary responses,
citations and disconnected flags are unchanged and make no AI calls.

**Do not deploy gold yet:** stage 4 must update TypeScript/UI for null energy,
quality, unavailable dates and source-specific labels. The current frontend
remains tested in mock mode; passing its build does not establish gold UI support.
The mock browser launcher now forces synthetic source as well as mock storage.
The deployed *mock* smoke accepts the older health shape during rollout, and
checks `data_source=synthetic` when that field is present; Python tests require
the new field. A separate gold browser flow is still stage 4 work.

## Loader and collision behavior

`api/load_gold.py` accepts the stage 2 `manifest.json` with adjacent hourly/daily
CSVs. It validates both full inputs before constructing a client: source identity,
query IDs, SHA256s, CSV schema, clock/window, all 168/7 ordered distinct buckets,
quality, numeric finiteness, hourly/daily reconciliation and normalized snapshot
identity. It recomputes these checks instead of trusting manifest success flags.
This intentionally bounded first loader does not import other households/weeks.

Real source energy is already kWh. The mapper uses Decimal values and preserves
nulls; it never divides again, converts missing data to zero or applies an
invented source timezone conversion. Athena's literal UTC display suffix is
removed, then the agreed project-clock convention is attached for API/key use.

Existing PK/SK builders remain shared. Gold records have schema 2, `is_demo=false`,
`data_source=gold`, dataset/snapshot/clock provenance and coverage. Synthetic rows
retain schema 1 and the previous attributes/keys. Reads reject a wrong source,
malformed quality or multiple snapshots within a result.

There are three operations:

1. Default / `--dry-run`: all-local validation and summary, no AWS client.
2. `--check-existing`: explicit later live preview. DescribeTable checks the
   exact account/Region/table and string PK/SK. Query checks both bounded grain
   partitions, including paginated/empty intermediate pages. No Scan/writes.
3. `--write`: requires a conflict-free reviewed preview, its explicit approved
   SHA256, matching source manifest/destination and a **new** report filename.
   Rechecks destination first; every insert is also conditional against races.

Only the agreed `g4-greentrack-dev-consumption` table in eu-central-1 is accepted.
New keys use `PutItem` with `attribute_not_exists(PK)`. Existing identical complete
records are skips; another source/snapshot/content is a conflict. No existing
record is overwritten/deleted. Conditional failures compare ALL_OLD or an exact
consistent Query if old values are omitted. Disappearance is a conflict, not an
assumed success. Transient failures get three bounded application attempts with
backoff, in addition to the SDK's existing bounded retries.

Reports record successes/skips and the failed or unconfirmed key. Resume with
the same reviewed inputs and a fresh report filename; the report is evidence,
not a trusted list of keys to skip. Storage and conditional checks determine
whether each key is already identical. A network error may follow an accepted
write, so failed reports cannot promise that no records were written.
Never replace a different snapshot automatically or delete rows to resume.

The synthetic seed live path now uses the same conditional insert protection.
Its 202-key dry run and identical synthetic reruns still work, but it cannot
overwrite a gold key. Unconditional BatchWriteItem tests were replaced with
conditional-write/race/retry tests. Operator permission examples mentioning only
BatchWriteItem are historical: protected loaders need PutItem and Query (gold
preview also needs DescribeTable). Runtime Lambda gets no write permission.

## Exact PowerShell commands

Run one box at a time from the repository root, using existing Python 3.14 `.venv`.
The following **offline dry run is safe now** and was executed successfully:

```powershell
.\.venv\Scripts\python.exe api/load_gold.py --manifest 'build/real-data/2026-11-26-gold-week/manifest.json' --region eu-central-1 --consumption-table g4-greentrack-dev-consumption --dry-run
```

Expected: `status=dry-run`, `total_items=175`, zero written/skipped, manifest
SHA256 `2cc84aceabcf19e830028648252cae300ff03eb0cc1f99af311e5e046f91e347`
and snapshot `sha256:a59514c69cc1d37884952d82fc19ee5cc15101b2461bb517693f5a8237ea4e93`.
All input files remain ignored. A dry run does not prove destination permissions.

The next commands are **examples for separately authorized stages 5/6 only**.
They were not executed in stage 3. Keep `DEPLOY_ENABLED` unset/false.
In a future dedicated cloud terminal, first log in if required:

```powershell
aws sso login --profile greentrack
```

```powershell
$env:AWS_PROFILE = 'greentrack'
```

```powershell
$env:AWS_REGION = 'eu-central-1'
```

After scoped access/account review, create a new read-only preview report:

```powershell
.\.venv\Scripts\python.exe api/load_gold.py --manifest 'build/real-data/2026-11-26-gold-week/manifest.json' --region eu-central-1 --consumption-table g4-greentrack-dev-consumption --check-existing --report 'build/real-data/gold-preview-1.json'
```

Review its source/destination/counts/keys and require zero conflicts. Then record
the SHA256 of **that reviewed file**; do not substitute an unreviewed report:

```powershell
$approvedPreviewHash = (Get-FileHash -LiteralPath 'build/real-data/gold-preview-1.json' -Algorithm SHA256).Hash.ToLowerInvariant()
```

Only after stage 6 explicit write authorization, use the matching reviewed file:

```powershell
.\.venv\Scripts\python.exe api/load_gold.py --manifest 'build/real-data/2026-11-26-gold-week/manifest.json' --region eu-central-1 --consumption-table g4-greentrack-dev-consumption --write --reviewed-preview 'build/real-data/gold-preview-1.json' --approve-preview-sha256 $approvedPreviewHash --report 'build/real-data/gold-write-1.json'
```

Check the exit code and report. A failed/partial run stops this procedure. Review
the error/category and existing progress; do not repeat with overwrite flags.
For an approved resume, retain the input/review and use a new write-report name.

## API configuration and future startup

`api/.env.example` documents values; the API does not automatically read .env.
For now, start the working mock API in terminal 1:

```powershell
$env:APP_DATA_MODE = 'mock'
```

```powershell
$env:APP_DATA_SOURCE = 'synthetic'
```

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir api --reload
```

In terminal 2 use the existing [mock frontend commands](run-the-demo.md#3-start-the-website-terminal-2-repository-root).
For future stage 6 local gold testing (after stage 4 UI and approved load), set
the following process variables **before restarting Uvicorn**:

```powershell
$env:APP_DATA_MODE = 'dynamodb'
```

```powershell
$env:APP_DATA_SOURCE = 'gold'
```

```powershell
$env:DYNAMODB_REGION = 'eu-central-1'
```

```powershell
$env:DYNAMODB_CONSUMPTION_TABLE = 'g4-greentrack-dev-consumption'
```

```powershell
$env:DYNAMODB_ANOMALIES_TABLE = 'g4-greentrack-dev-anomalies'
```

```powershell
$env:DYNAMODB_FORECASTS_TABLE = 'g4-greentrack-dev-forecasts'
```

Select the approved AWS profile as above. Existing DynamoSettings still validates
three distinct explicit table names, although gold mode only queries consumption.
No read/AI request to the other tables/services occurs. Switching back to mock
requires resetting **both** settings to mock/synthetic and restarting the API.

## Terraform, file tour and verification

Dev `app_data_source` -> child `data_source` -> existing Lambda map -> direct
`APP_DATA_SOURCE` environment and its non-secret SSM mirror. Defaults stay
mock/synthetic. Mock+gold fails validation/precondition. Gold's execution policy
contains Query only on consumption; synthetic DynamoDB mode retains Query on
three tables. Existing role/resource addresses, shared trust, LF admins/grants,
backend, API routes/CORS and frontend infrastructure are unchanged. No provider
locks changed. Full-root AWS planning and deployment remain later gates.

| File | Purpose |
| --- | --- |
| `api/app/gold.py` | Offline source validation, canonical snapshot verification and gold record validation. |
| `api/app/conditional_write.py` | Shared race-safe insert, identical-skip and bounded retry behavior. |
| `api/load_gold.py` | Explicit dry-run/preview/reviewed-write CLI and per-key reports. |
| Existing models/storage/repository/service/main modules | Typed nullable/quality responses, source selection, row checks, accurate health and unavailable model envelopes. |
| `api/seed_demo.py` | Existing synthetic-only seed, now protected from overwriting gold records. |
| `api/tests/test_gold.py` | Offline invented source-shaped samples and genuine SDK Stubber contract tests; not proof of real data access. |
| Terraform dev/challenge1 configuration | Source setting and minimal Query permission plumbing; no resource deployment. |

Example request path: GET `/consumption?...&grain=daily` -> FastAPI validates the
window -> EnergyService requests the selected source -> DynamoDBRepository uses
the existing daily PK and half-open time keys -> validates schema 2, quality and
provenance -> service serializes gold metadata and JSON points, including nulls.
The loader is separate and is never invoked by that request or health.

Checks passed: **162 pytest tests**, **20 frontend tests**, lint, production build,
**one mock browser smoke**, and Terraform fmt/cached-provider init with disabled
isolated backends/readonly locks/validate for both registered roots. The genuine
stage 2 files passed the offline 175-item loader dry run. No dependency changes.
The existing Starlette/httpx and browser color-environment warnings remain.
Linux ZIP execution, real loader permissions/writes and gold browser/deployment
checks were not run; Windows cannot execute the Lambda's Linux native wheels.
Validation is not an AWS plan or proof that a deployment works.

Next: stage 4's frontend/null/quality/provenance work. Do not load/deploy early.
