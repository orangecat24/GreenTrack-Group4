# Gold frontend and verification: stage 4

Implemented November 26, 2026 on `test/person2-app-validation`, preserving all
earlier uncommitted work. No AWS calls, data loads, deployment, repository setting
changes, dependency installs/upgrades, commit or push occurred in this stage.
The [integration checklist](real-data-integration.md) records the remaining gates.

## Changes and fixes

- `web/src/api/types.ts` reflects the implemented nullable energy/quality and
  source/status/note metadata; unavailable forecast dates are nullable. Numeric
  forecast points remain required. Existing API paths and fetch/base conventions
  are unchanged; production components have no duplicate fixture arrays.
- `consumptionSummary.ts` sums only observed numeric values. An all-null result
  is **No measured energy**, while a measured numeric zero remains 0.00 kWh.
  Missing expected periods, null energy, incomplete periods or unknown gold
  quality make the card **Observed energy**, with an explicit partial-total note.
  Synthetic quality is not presented as measured-minute coverage.
- Consumption shows returned coverage, absent periods and observed-minute counts.
  The first/last covered timestamps do not claim every interval was complete.
  Table cells show unavailable energy and per-row quality; days are calendar
  buckets rather than unconditionally described as complete days.
- `chartData.ts` inserts a display-only null marker where API intervals are
  absent, preserving gaps without changing source records or inventing zeros.
  Actual and illustrative forecast series stay distinct, with null connection
  disabled. Null tooltip/table values are never coerced into numeric zero.
- Response-level provenance shows **Historical source data** for gold and
  **Demo data** for synthetic responses, even when empty. Unavailable model
  responses show **Not integrated** and their API note, without a demo-data badge
  suggesting records exist. Forecast history has its own provenance label.
- Null forecast dates are never formatted as actual model dates. Gold mode can
  show historical observations with zero forecast points; synthetic mode keeps
  the original explicitly illustrative model-free series.
- Assistant messages show **Placeholder**, not a synthetic-measurement badge.
  Disconnected status and empty citations remain visible. Global copy no longer
  declares all consumption synthetic. The four tabs/layout and existing request
  cancellation, outdated-response guard, retry/loading/empty/error behavior stay.

Vitest/Testing Library has six new tests covering gold and empty provenance,
partial/minute coverage, missing/null chart gaps, all-null versus zero energy,
and unavailable models without invented dates. Existing state/filter/late-response
tests still pass. These invented test doubles are not real dataset evidence.

## Checks performed

| Check | Result |
| --- | --- |
| API/helper pytest suite | **162 passed**, no actual AWS access. |
| Frontend Vitest | **26 passed**, five files. |
| Frontend lint / production build | Passed using the existing dependencies. |
| Local mock Playwright flow | **1 passed**; own mock servers, no credentials. |
| Gold smoke collection (`--list`) | **1 test found**, reads local evidence only; no HTTP calls. |
| Actual gold browser flow / deployed gold | **Not run**; requires later reviewed load and application startup/deployment. |

The existing Starlette/httpx and browser color-variable warnings remain. A chart
regression assertion was updated to expect a null gap between separated intervals
while retaining the original observation/forecast separation assertions.
No API/Terraform changes were needed in this stage. Stage 3 validation results
are recorded separately; stage 4 does not imply a new infrastructure plan.

Repeat offline checks from the repository root, one command at a time:

```powershell
$testTemp = Join-Path (Get-Location) ('.qa\spa-gold-' + [guid]::NewGuid().ToString('N'))
```

```powershell
.\.venv\Scripts\python.exe -m pytest -c api/pytest.ini api/tests scripts/tests -q "--basetemp=$testTemp"
```

```powershell
npm.cmd --prefix web run test:run
```

```powershell
npm.cmd --prefix web run lint
```

```powershell
$env:VITE_API_BASE_URL = '/api'
```

```powershell
npm.cmd --prefix web run build
```

```powershell
npm.cmd --prefix web run test:e2e
```

## Opt-in gold smoke: prerequisites and exact commands

`playwright.gold.config.ts` and `gold/smoke.spec.ts` are separate from the ordinary
mock CI/browser flow. They start **no servers**, submit no loader operations and
never replace API responses. Opt-in is mandatory and invalid/missing origins
fail instead of falling back to mock. Browser requests are restricted to the
chosen API/website origins. Trace/screenshots are disabled for this live check.

Before actual execution, complete stages 5/6: review the destination and explicitly
load the approved snapshot. Start the API with dynamodb/gold and the frontend
with its `/api` Vite proxy, using [gold-loader.md](gold-loader.md). Local API calls
then read AWS; this smoke is not an offline test. For cloud execution, complete
the later reviewed plan/manual release first. Leave DEPLOY_ENABLED unset/false.

Keep the genuine stage 2 manifest and both adjacent CSVs in their ignored directory.
The smoke verifies the pinned reviewed manifest SHA256 and both CSV checksums.
Expected totals/counts come from that independently verified manifest, not mock
111.80 values or production React constants. Changed data requires a new evidence
review and explicit smoke update; do not change checksums just to pass a test.

In a dedicated repository-root PowerShell terminal, after those prerequisites:

```powershell
$env:GOLD_SMOKE_ENABLED = 'true'
```

```powershell
$env:GOLD_EXPORT_MANIFEST = Join-Path (Get-Location) 'build/real-data/2026-11-26-gold-week/manifest.json'
```

For the already-running local application:

```powershell
$env:GOLD_WEBSITE_URL = 'http://127.0.0.1:5173'
```

```powershell
$env:GOLD_API_BASE_URL = 'http://127.0.0.1:8000'
```

To check collection only, without sending HTTP requests (performed in stage 4):

```powershell
npm.cmd --prefix web run test:gold -- --list
```

Only after the local gold app is ready and real reads are authorized:

```powershell
npm.cmd --prefix web run test:gold
```

For a later deployed run, replace the two origins with the reviewed application's
public `website_url` and `api_base_url`. The config accepts CloudFront and the
eu-central-1 API Gateway HTTPS origins; do not append `/api`. Build Vite with
VITE_API_BASE_URL before publication as documented in the existing run guide.
The local smoke recognizes browser `/api` proxy requests, while the cloud smoke
requires the browser to call the configured API Gateway origin directly.

Execution checks configured health/provenance, both grains and their independently
verified totals, date-filter changes, hourly charts, all four tabs, unavailable
model states and explicit placeholder chat/summary requests. HTTPS adds CORS
origin and chat OPTIONS method/header checks. Expected result: **1 passed**.
It does not provision resources, invoke real AI or prove every AWS permission.
This complete-week sample contains no null/incomplete periods; offline tests
cover those cases without pretending the verified sample contains them.

## Save and share the implementation

All stages 1–4 are currently uncommitted. Inspect the complete diff, then stage
the intended source/docs (generated exports, plans, state and secrets stay ignored):

```powershell
git add README.md api docs infra/challenge1 infra/environments/dev/application.tf web
```

```powershell
git diff --cached --stat
```

Suggested commit, after reviewing that list:

```powershell
git commit -m "feat: add gold consumption loader and honest UI coverage"
```

```powershell
git push origin test/person2-app-validation
```

Open/update the draft PR into main and let ordinary credential-free checks run.
Do not merge or enable deployment as a side effect. After these checks, continue
with stage 5's authorized destination preview, not an early live write.
