# Stage 6: verified gold load and local application

Completed November 26, 2026 on `test/person2-app-validation` at application
revision `2dacab7`. Earlier stage 5 Markdown changes were preserved. No application
defect was found; only documentation and ignored local evidence files changed.

**The genuine week is loaded and the local gold application passed.** The deployed
Lambda/website remain the existing mock release; no infrastructure, runtime role,
Lambda configuration, S3 frontend assets or CloudFront settings were changed.
Keep `DEPLOY_ENABLED` unset/false. Cloud application planning/release is stage 7+.

## What was authorized and executed

Source manifest, both CSV checksums, normalized snapshot and reviewed preview
fingerprints still matched [the stage 5 review](gold-load-review.md). STS reconfirmed
account 886565871385 via greentrack's existing SSO DeveloperAdminAccess session;
eu-central-1 was explicit. A fresh DescribeTable/schema/account check and both
bounded Query reads produced a preview **exactly equal** to the approved one:
175 new keys, zero identical/conflicting records. No stale-preview change occurred.

The authorized loader command was then executed once, using conditional PutItem
on **g4-greentrack-dev-consumption only**, with the approved preview fingerprint.

| Outcome | Count |
| --- | --- |
| Written | **175** (168 hourly + 7 daily) |
| Skipped | **0** |
| Failed/unconfirmed | **0** |
| Conflicts | **0** |
| Post-load Query comparison | **175 identical, 0 new, 0 conflicts** |

Every stored candidate record matched the independently validated source,
including energy, quality, timestamps, keys and provenance. This proves the local
operator could perform this bounded conditional write; it does not prove every
future permission or the deployed Lambda's DynamoDB access. Its execution role
and deployed mock configuration were left untouched. No test record, delete,
overwrite, seed_demo run, anomaly/forecast write, preprocessing, IAM/LF change,
Terraform plan/apply, upload, invalidation, commit or push occurred.

## Evidence and verification

Evidence is ignored under `build/real-data/`; keep it locally, not in Git:

| File | Evidence |
| --- | --- |
| `gold-preview-stage6-before.json` | Fresh Query preview; SHA256 remains `3131f6d47aac4e29f74f6eb71a2ae712e1fa0aa0a96e2e03c8a59b67568baafc`. |
| `gold-write-1.json` | Complete per-key write report; SHA256 `732b4440845d9d93b34ab77f9f5754f6cfdccf7a4c62f81d802f8e9a6525302a`. |
| `gold-preview-stage6-after.json` | Full bounded Query comparison; 175 identical records, no conflicts. |
| `gold-stage6-local-verification.json` | HTTP checks against actual local FastAPI reading AWS DynamoDB. |
| `gold-stage6-result.json` | Scope, counts, check results and fingerprints of the reviewed/source/write/verification evidence. |

Source manifest SHA256 remains
`2cc84aceabcf19e830028648252cae300ff03eb0cc1f99af311e5e046f91e347`;
snapshot remains
`sha256:a59514c69cc1d37884952d82fc19ee5cc15101b2461bb517693f5a8237ea4e93`.

Local verification used **API 18080 / Vite 15174**, separate from standard dev
and mock-test ports. Hidden temporary processes were started for the check and
stopped afterward using only their recorded PIDs/start times. Other development
servers were not stopped. Follow the instructions below to start your own.

| Check | Observed result |
| --- | --- |
| Post-load Query preview | Every one of 175 full records identical to source. |
| Local HTTP API comparison | All 168 hourly + 7 daily JSON records matched source energy, intervals and quality. |
| Weekly energy | **147.3223 kWh**; hourly/daily sums agree within floating-point tolerance. |
| Quality | All intervals complete: 60 minutes/hour, 1,440/day; both grains represent the same 10,080 observed minutes. |
| Health | `status=ok`, `data_mode=dynamodb`, `data_source=gold`, `is_demo=false`; actual reads independently proved storage access. |
| Valid empty window | June 1 00:01..00:02 returned empty items/null coverage with gold provenance retained. |
| Date boundaries | Adjacent 00:00..01:00 and 01:00..02:00 returned distinct single hours; end stayed exclusive. Invalid daily boundary/zero-length window returned 422. |
| Anomalies / forecast | Explicit unavailable responses, no records or invented forecast dates. |
| Gold Playwright | **1 passed**, actual browser/API, verified export totals, date-filter changes, hourly chart, all four tabs and placeholder chat/summary. |
| Mock Playwright | **1 passed**, separate credential-free synthetic servers. |
| Offline regressions | **162 Python tests + 26 frontend tests passed**, including null/incomplete data, empty/loading/error/stale responses and write safety. |

The actual loaded week has no null/incomplete intervals. Those cases were verified
using honestly labeled offline test examples, not by modifying real observations
to manufacture a live example. The local HTTP audit initially compared timestamp
text literally; `.000000Z` and `Z` differed despite the same instant. Repeating
the audit with timezone-aware datetime equality passed; no source/application
change was necessary. Existing Starlette/httpx and color-environment warnings remain.

Not performed: deployed HTTPS/gold/CORS smoke, artifact rebuild/Linux ZIP execution,
new Terraform checks/plan/apply or GitHub deployment. Earlier build/lint validation
is recorded in stage 4; no source code changed requiring a new build here.

## Start it yourself: Windows PowerShell, repository root

This is a **local app using AWS data**, not an offline mock. Your Python API uses
SSO to Query the already-loaded DynamoDB consumption table. The browser gets JSON
through Vite's `/api` proxy; credentials never go into React or VITE_* variables.
These commands do not load data or change the deployed app.

Open **terminal 1** in VS Code PowerShell. Run each box separately, pressing Enter
once and waiting for the prompt before the next. Keep it open once Uvicorn runs.
Use the existing installed dependencies; no npm ci is needed unless they changed.

```powershell
Set-Location 'C:\Users\Macintoks\Desktop\Master\Other\Internship And Job Applications\DataMax\GreenTrack-Group4'
```

If login is expired (or you want to renew it), run this and complete the browser:

```powershell
aws sso login --profile greentrack
```

```powershell
$env:AWS_PROFILE = 'greentrack'
```

```powershell
$env:AWS_REGION = 'eu-central-1'
```

```powershell
$account = aws sts get-caller-identity --query Account --output text --no-cli-pager
```

```powershell
if ($LASTEXITCODE -ne 0 -or $account -ne '886565871385') { throw 'Stop: wrong account or expired login.' }
```

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

The existing settings validate all three names; gold mode queries consumption
only and returns the model-unavailable envelopes without reading the other tables.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir api --host 127.0.0.1 --port 18080
```

Expected: Uvicorn running on http://127.0.0.1:18080. Leave it running. If a port
is in use, identify your existing server and stop it deliberately with Ctrl+C;
do not kill unrelated Python/Node processes. Do not start a duplicate server.

Open **terminal 2**, also at the repository root, and run one box at a time:

```powershell
Set-Location 'C:\Users\Macintoks\Desktop\Master\Other\Internship And Job Applications\DataMax\GreenTrack-Group4'
```

```powershell
$env:VITE_API_BASE_URL = '/api'
```

```powershell
$env:API_PROXY_TARGET = 'http://127.0.0.1:18080'
```

```powershell
npm.cmd --prefix web run dev -- --port 15174
```

Open **http://127.0.0.1:15174**. Use household-1, June 1 through June 7 inclusive.
Consumption should show **Historical source data**, **147.32 kWh**, complete
coverage and the API-provided units. June 1 alone is **24.05 kWh**. Anomalies and
forecast are not integrated; assistant/weekly summary remain disconnected
placeholders. These are historical UCI readings, not live home-meter telemetry.

## Repeat the real browser check

Keep terminals 1/2 running. In **terminal 3 at the repository root**:

```powershell
$env:GOLD_SMOKE_ENABLED = 'true'
```

```powershell
$env:GOLD_EXPORT_MANIFEST = Join-Path (Get-Location) 'build/real-data/2026-11-26-gold-week/manifest.json'
```

```powershell
$env:GOLD_WEBSITE_URL = 'http://127.0.0.1:15174'
```

```powershell
$env:GOLD_API_BASE_URL = 'http://127.0.0.1:18080'
```

```powershell
npm.cmd --prefix web run test:gold
```

Expected: **1 passed**. This starts no servers and uses the reviewed local export
evidence; it will issue real DynamoDB reads through terminal 1's API. It will not
write records or invoke AI. For offline regression commands, see
[gold-frontend.md](gold-frontend.md#checks-performed).

Ctrl+C stops each server. To return the same API terminal to mock, reset **both**
APP_DATA_MODE=mock and APP_DATA_SOURCE=synthetic before restarting. Do not run
seed_demo to change modes, or rerun the already-completed write command.

## Save the documentation; next gate

No new application commit is required: stage 6 found no source defect. Save this
stage's records together with the still-uncommitted stage 5 review if desired:

```powershell
git add docs/gold-local-run.md docs/gold-load-review.md docs/real-data-integration.md docs/person2-handoff.md docs/run-the-demo.md
```

```powershell
git diff --cached --stat
```

```powershell
git commit -m "docs: record verified gold load and local integration checks"
```

```powershell
git push origin test/person2-app-validation
```

These Git commands were not executed by the agent. Keep the PR for review and
DEPLOY_ENABLED unset/false. Next is stage 7: build/verify the matching artifact
and review a full-root infrastructure plan. Loading DynamoDB did not switch the
deployed Lambda to gold or change its runtime permissions.
