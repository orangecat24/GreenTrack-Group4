# Real gold-consumption integration

**Latest: stage 6 completed November 26, 2026.** The explicitly authorized load
wrote 175 consumption records, skipped/failed 0. Post-load Query found all 175
identical; actual local gold API/browser and mock regressions passed. See
[gold-local-run.md](gold-local-run.md) for evidence and exact two-terminal startup.
The deployed Lambda remains unchanged; infrastructure planning/release is pending.
The stage 5 read-only preview completed November 26, 2026.
[gold-load-review.md](gold-load-review.md) records the exact source/destination,
fingerprints and proposed later write. The bounded Query reads found 175 new
keys, 0 identical records and 0 conflicts; no records were written. Proceed to
stage 6 only with its explicit authorization and rechecks.
Stage 4 completed offline November 26, 2026. See
[gold-frontend.md](gold-frontend.md) for UI behavior, 26 passing frontend tests,
mock browser verification and the opt-in gold smoke (collected, not executed).
Backend/loader/source
plumbing now exist; [gold-loader.md](gold-loader.md) records commands, tests,
compatibility and scope. Gold application deployment remains pending.
Genuine source exports were independently verified in stage 2.
See [the stage 2 evidence](#stage-2-evidence-november-26-2026). The stage 1 account
below records that earlier session's offline-only scope, not today's cumulative
cloud activity.

## Stage 1 record: November 26, 2026

**Status: design and offline baseline complete; integration not implemented.**
Starting branch: `test/person2-app-validation`, clean and tracking its matching
origin branch. Starting commit: `9883c93` (`fix: stabilized demo deployment and
document verification`). Only documentation is changed in this stage.

The user reports that they applied/published the mock version and successfully
visited and exercised the deployed website. That is **user-reported manual
verification**, not a fresh deployed Playwright result from this session.
Person 1 reports successful gold preprocessing and November 19 totals in
[gold-handoff.md](gold-handoff.md). No gold rows or live permissions were
independently verified in this stage. Earlier deployment checks in other
handoffs remain historical evidence, not new checks performed today.

No AWS calls, SSO login, Terraform backend access/plan/apply, queries, loads,
uploads, invalidations or repository-setting changes were performed. Credentials,
authentication files and state contents were not inspected. Nothing was committed
or pushed. `DEPLOY_ENABLED` must remain unset/false; its live setting was not read.

## Smallest implementation

```text
Existing gold Iceberg tables
    -> two bounded Athena SELECT exports + provenance manifest
    -> explicit CLI validation, preview and conditional consumption writes
    -> existing DynamoDB consumption table
    -> existing repository -> service -> FastAPI -> existing React tabs
```

There is no new storage platform, loader Lambda, inference service or model call.
The API does not query Athena or read the gold S3 prefix at request time. A local
API in DynamoDB mode still contacts AWS; only mock mode and stubbed tests are
offline. The export/loader is an operator action, never an API startup hook or
ordinary deployment step. Do not rerun preprocessing or upload raw data to
connect the app: raw uploads can trigger the existing Glue workflow.

The first release serves **genuine historical consumption only**. It does not
make this a live meter feed. Person 3's anomaly/model/assistant work stays separate.

## Existing contract and observed gaps

[Person 1's contract](../contracts/data.md) owns the source/gold rules. Do not
rewrite it as part of Person 2's implementation. This file defines the planned
application projection, retaining the contract's meaning.

| Existing location | What needs changing in a later stage |
| --- | --- |
| `api/app/models.py` | Energy currently requires a number; read responses require `is_demo=true`; health only permits `mock`; forecast dates are always required. |
| `api/app/dynamodb_items.py` | `point_item` always writes synthetic provenance and record schema version 1. Reuse its key builders, not its synthetic provenance for gold. |
| `api/app/dynamodb_repository.py` | Rejects every row without `is_demo=true`/schema 1. Windowed Query/pagination already exist and should be retained. |
| `api/app/storage.py`, `main.py`, `service.py` | Storage selection exists, but response provenance comes from defaults. Health always returns mock even for DynamoDB. |
| `api/seed_demo.py` | Synthetic-only BatchWriteItem loader, with unconditional stable-key overwrites. It is not the gold loader and must not run against gold-loaded keys. |
| `web/src/api/types.ts`, components/chart mapping | Energy is non-nullable; arithmetic/table formatting assume numbers. Text implies synthetic history and complete days; absent timestamps can still be joined by a line. |
| `web/e2e/studentDemo.ts`, `web/deployed/smoke.spec.ts` | Assert synthetic totals and mock health. Preserve these checks and add explicit gold checks instead of weakening them. |
| `scripts/deployment.py`, `deploy-main.yml` | Automatic plans explicitly select mock. Later activation would risk reverting a manual gold configuration. |

No implementation defect was fixed in this documentation stage.

## Source window, units and quality

- Household: `household-1` only for the initial export/load.
- Window: `[2009-06-01T00:00:00Z, 2009-06-08T00:00:00Z)`. The UI's inclusive
  Through date is June 7, converted to the exclusive June 8 API end.
- Select `household_id`, `period_start`, `energy_kwh`, `minutes_with_data` and
  `is_complete` from **both** gold consumption tables. Sub-meter breakdowns and
  daily peaks are outside this increment; the existing API does not need them.
- Gold already contains energy in kWh. Do not divide by 60 again, treat it as
  kW, or recompute real daily rows using the synthetic fixture helper.
- Preserve the source clock. Attaching UTC for API/key interoperability is a
  project convention, **not a conversion or proof of the source timezone**.
  Do not apply an invented Europe/Paris or daylight-saving conversion.
- SQL must use `period_start >= start AND period_start < end`, with household
  and applicable year/month partition predicates. Handoff examples use
  inclusive `BETWEEN`; copying that would include the exclusive end boundary.
- A complete week would contain 168 hourly and 7 daily periods. Verify actual
  rows and distinct aligned keys, not just counts. Do not manufacture missing
  observations or silently trim an unexpectedly larger query result.
- Gold hour counts are 0..60; day counts are 0..1440. `is_complete` must agree
  with the required minute count. Zero minutes requires null energy; positive
  coverage carries a finite nonnegative observed-energy value. Reject
  inconsistent source records rather than silently correcting them.
- Partial periods can have numeric observed energy and `is_complete=false`.
  Missing energy stays null. Entirely absent periods are absent observations,
  not zero-energy records. UI charts must show gaps for both cases.
- Verify daily rows against hourly sums and minute counts using unrounded values
  and an explicit small floating-point tolerance. Exported daily rows remain the
  source of truth for daily reads; disagreements are investigation failures.

Person 1 reports June 1..7 daily kWh of 24.054, 18.177, 22.610, 17.261, 20.506,
24.591 and 20.123, with complete days. These rounded figures are **comparison
targets only**, not a new real-data fixture array or proof of access. The actual
export and its precision must drive later verification. Mock totals remain
111.80 kWh for the week and 13.46 kWh for June 1.

## Planned configuration: storage and provenance are separate

The following settings are now implemented by stage 3, including startup
validation and the safe environment example. Actual gold loading/deployment is
still a later gate; use [gold-loader.md](gold-loader.md), not an early cloud switch.

| Setting | Default / meaning |
| --- | --- |
| `APP_DATA_MODE` | Existing `mock` default; `dynamodb` selects the existing cloud repository. |
| `APP_DATA_SOURCE` | New `synthetic` default; `gold` explicitly selects the genuine-consumption contract. |
| Existing `DYNAMODB_*` | Retain Region/table names and the illustrative forecast origin for synthetic mode. |

| Mode/source combination | Planned behavior |
| --- | --- |
| `mock` + `synthetic` | Existing coherent fixtures, no AWS SDK clients/credentials/network, including chat and summary. |
| `mock` + `gold` | Invalid configuration; fail before constructing an AWS client. Never label fixtures as gold. |
| `dynamodb` + `synthetic` | Existing supported synthetic records; all demo labels retained. |
| `dynamodb` + `gold` | Query genuine consumption only; no synthetic/model fallback for other tabs. |

Validate configuration once at startup and pass the selected source through the
small repository/service boundary. Do not add a plugin registry or a parallel
repository framework. Do not derive provenance from nonempty rows, DynamoDB
storage, the current date or an AWS credential check. Validate returned row
provenance against the selected contract; mismatches give a safe storage error.

Keep Terraform `app_data_mode` default `mock`; add `app_data_source` default
`synthetic` through dev/module inputs. Add the actually-used non-secret
`APP_DATA_SOURCE` value to the existing Lambda configuration map and SSM mirror
`/g4-greentrack-dev/api/APP_DATA_SOURCE`. Lambda receives configuration directly
in its environment; no SSM runtime fetch or new secret is needed. Gold is a later
explicit plan with `app_data_mode=dynamodb` and `app_data_source=gold`.

## Planned API projection and frontend behavior

Keep `/`, `/health`, `/consumption`, `/anomalies`, `/forecast`, `/chat`, household
validation, query parameters, hourly/daily grain, units, half-open boundaries,
422 validation and safe 503 storage errors. Daily windows still require midnight
boundaries. Preserve bounded internal DynamoDB pagination; a small weekly import
does not require inventing a new public cursor format (`next_cursor` stays null).

Existing numeric mock values, dates, synthetic detections, illustrative forecasts
and placeholder answers must stay the same. New metadata is additive; update
tests that intentionally compare entire JSON objects to cover the explicit new
contract. Do not remove important assertions just to accommodate new behavior.

| Response location | Planned change |
| --- | --- |
| Consumption point | Relax `energy_kwh` to number or null. Add nullable `minutes_with_data` and `is_complete`; both are required/validated for gold. Synthetic quality fields are null (not observed source coverage). |
| Read envelope | Add `data_source` (`synthetic`, `gold`, `unavailable`), `status` (`available`, `unavailable`) and an explanatory nullable `note`; retain existing fields. |
| Gold consumption envelope | `data_source=gold`, `status=available`, `is_demo=false`, including a valid empty window. Empty does not mean synthetic or storage failure. |
| Synthetic reads | `data_source=synthetic`, `status=available`, `is_demo=true`. Genuine zero anomalies cannot be inferred from synthetic detections. |
| Gold-mode anomalies/forecast | HTTP 200, empty items, null coverage, `data_source=unavailable`, `status=unavailable`, `is_demo=true` for the placeholder, explicit not-integrated note. Do not query/fill from the synthetic tables. |
| Forecast metadata | Allow origin/target bounds to be null only for unavailable output; retain concrete fixture dates in synthetic mode. Never invent a model run or horizon to satisfy serialization. |
| Chat/weekly summary | Keep `status=placeholder`, disconnected assistant, honest existing text, empty citations and `is_demo=true`, regardless of consumption source. No summary computation or model call. |
| Health | Keep `status=ok`; allow actual `data_mode`; add configured `data_source` (`synthetic`/`gold`). `is_demo` describes the selected consumption source. No storage read/probe: health cannot prove records, authorization or ML availability. |

Here `available` describes an implemented read feature, not guaranteed full
coverage; a failed Query still returns 503. `is_demo=false` is never sufficient
by itself to prove source data or service readiness. In unavailable model
responses, `is_demo=true` identifies a placeholder, not generated observations;
the UI should show **Not integrated**, not a badge implying there are demo rows.

For gold records, map `period_start` to `timestamp`, attach the agreed clock
convention and derive `interval_end` by the grain. Do not change units or discard
quality. Update TypeScript alongside Pydantic and check inherited forecast types
so relaxing consumption energy does not accidentally permit invalid model data.

In React, keep four simple state-based tabs and the shared typed fetch client:

- Label consumption **Historical source data** when gold; keep synthetic/demo
  labeling for fixtures. Replace unconditional synthetic copy in headers/footer
  using API metadata, not a build-time inference about the data.
- Show returned-period and observed-minute coverage, incomplete counts and
  missing periods. `covered_start/end` only describe the first/last returned
  bucket; they do not establish that intervening periods were present/complete.
- Sum only numeric observed values and label partial totals as **Observed energy**
  with a coverage warning. An all-null selection is **No measured energy**, not
  0 kWh. A genuine numeric zero remains 0 kWh. Do not double-count hourly and daily
  grains. Format missing table/tooltip values as unavailable, not `Number(null)`.
- Leave null/missing-period gaps in the chart. Visual gap markers must not become
  invented API readings or carried-forward observations.
- Preserve actual/forecast series separation. In gold mode show real history and
  **Forecast not integrated**, without fixture targets or an illustrative line.
  Keep the illustrative series only in explicit synthetic mode.
- Distinguish not-integrated output, a successful empty selection, loading and
  errors. Keep cancellation/outdated-response handling and panel-local errors.

Changing storage alone does **not** complete this integration. Stages 3/4 now
implement coordinated backend and TypeScript/UI handling of nullable values and
unavailable dates. The reviewed load and full application release remain pending;
deploying only one side is not a complete release.

## Keys, loader and source manifest

Reuse the existing consumption table and shared key-building functions:

```text
PK = HOUSEHOLD#household-1#GRAIN#hourly  (or #GRAIN#daily)
SK = 2009-06-01T00:00:00.000000Z       (fixed-width period start)
```

Hourly/daily partitions differ; target dates and origins in the existing forecast
keys remain untouched. Do not introduce a new household ID, table or key namespace
just to hide conflicts with synthetic records. Query the explicit partition/window.

Retain synthetic record schema 1. Define gold consumption record schema 2 in the
application mapping, distinct from Person 1's **gold source contract v1**. Gold
records carry `is_demo=false`, `data_source=gold`, a stable dataset identifier
`uci-household-power-v1`, a manifest-derived `snapshot_id`, quality fields and
the existing grain/timestamps. Reader validation must check these fields, not
accept arbitrary rows because someone supplied `is_demo=false`.

The export manifest records account/Region, source database/tables, query IDs,
exact household/window, source-clock note, source schema, export SHA256 hashes,
row counts, quality/coverage, query scanned bytes and collection time. Base the
stable snapshot identity on normalized source content and source/window identity,
not wall-clock export time or query ID alone. Preserve the query IDs as evidence.
Keep downloaded rows, detailed manifests and write/resume reports under ignored
`build/real-data/`; commit only concise evidence summaries and permitted test data.

Implement a small `api/load_gold.py` CLI and only the shared normalization helpers
it needs. Offline dry run validates **both** inputs/manifest before constructing
any AWS client. Live preview is a separate explicit operation. A write operation
requires the reviewed manifest, exact destination, Region and explicit write flag.

Preview all candidate keys with windowed Query reads; identify new, identical and
conflicting records. Do not trust approximate table ItemCount as proof of absence.
Use conditional PutItem writes, not unconditional BatchWriteItem, for the new
loader. Conditions must protect against another writer racing after the preview.
Identical normalized records from the same dataset/snapshot are safe skips;
different source/snapshot/content, including synthetic rows at the same key, are
conflicts. Stop for a reviewed resolution; no automatic overwrite, delete or Scan.
The conditional-failure path must recheck rather than treat every race as success.

Use bounded retries for transient failures and a resumable local report of
written/skipped/failed keys. A partial load must be reported as partial; rerunning
the same reviewed snapshot must not duplicate or mutate conflicting records.
Loading a new snapshot over old keys is a later explicit migration decision.

The current seed CLI is also an overwrite hazard: before gold is loaded, add a
conflict guard to its live write path so it cannot overwrite gold records. Retain
its offline dry run, synthetic mapping and supported synthetic reruns. A preliminary
read followed by unconditional writes is insufficient protection from races.
Do not execute `seed_demo.py --write` as part of this work.

## Existing resources and permission boundaries

The following identifiers come from repository configuration and prior handoffs;
**existence/current permissions are not reverified today**.

| Item | Existing value |
| --- | --- |
| Account / Region / local profile | `886565871385` / `eu-central-1` / `greentrack` |
| Prefix / tags | `g4-greentrack-dev-`; Group=g4, Project=greentrack, Environment=dev, ManagedBy=terraform (application Challenge=1). |
| Deployment root / application child | `infra/environments/dev` / `infra/challenge1`. |
| Backend | `g4-greentrack-tfstate-886565871385`, key `environments/dev/terraform.tfstate`, S3 lockfile. Bootstrap ownership remains with its original owner. |
| API Lambda / execution role | `g4-greentrack-dev-api` / `arn:aws:iam::886565871385:role/g4-greentrack-dev-api-execution`. |
| Application DynamoDB | `g4-greentrack-dev-consumption`, `g4-greentrack-dev-anomalies`, `g4-greentrack-dev-forecasts`. Existing string PK/SK, on-demand billing. |
| Frontend bucket | `g4-greentrack-dev-web-886565871385`, private, CloudFront OAC access. |
| API / website URLs | Resolve later from dev's public `application` output. Keep the existing distribution, HTTPS default domain and HTTP API routes; no new domain or frontend origin. |
| Data lake / export prefix | `s3://g4-greentrack-dev-datalake-886565871385/gold/` / existing `athena-results/` in that bucket. |
| Gold database / tables | `g4_greentrack_dev_gold.hourly_consumption`, `.daily_consumption`; `.daily_peak` is outside this projection. |
| Athena workgroup | Handoff says `primary`; verify its actual enforced output/encryption/limits before querying. |
| Configuration / logs | `/g4-greentrack-dev/api/*`; `/aws/lambda/g4-greentrack-dev-api` and `/aws/apigateway/g4-greentrack-dev-api`, existing seven-day retention. |
| GitHub deployment role | `arn:aws:iam::886565871385:role/g4-greentrack-github-deploy`; separate from runtime. |

The API role remains logs-only in mock. Gold DynamoDB mode needs only Query on
the exact consumption table; synthetic DynamoDB mode retains Query on the three
synthetic tables it uses. Preserve Terraform resource addresses while narrowing
the appropriate policy. No runtime Scan, writes, S3 gold reads, Athena, Glue,
Lake Formation, Bedrock or SageMaker permissions. The API does not need a gold
Lake Formation grant merely to read a DynamoDB projection.

The operator/export path needs separately verified IAM and LF access to SELECT
the two gold tables, describe their database/schema, execute/check Athena queries
and read/write only the approved query-result location. This query-result write
is an explicit later authorization, not a read-only AWS check. Respect enforced
workgroup encryption and any required existing key permissions; do not change
them to bypass access failures. Use Iceberg-aware Athena SQL, not arbitrary
Parquet files from S3 (which can include obsolete snapshots).

The CLI loader needs scoped identity/table checks, Query and conditional PutItem
on the exact destination consumption table under an approved operator identity.
It does not inherit Lambda's role or require a new role/Lambda by default.
If denied, document the smallest missing grant for the responsible account/data
owner rather than broadening policies or assuming SageMaker's role.

The existing shared GitHub role is broad PowerUser plus g4-* IAM permissions and
trusts this repo's main/PR subjects. Do not describe it as read-only or change it
here. Dev's LF admin list depends on the deploying identity; preserve existing
admins/grants and SageMaker's explicit ALL/DESCRIBE exception. GitHub activation
requires a separately reviewed stable LF admin configuration. Do not add API
roles to `gold_consumer_role_arns` as a substitute for deciding who runs exports.

## Release, rollback and verification gates

Use the current test branch; it does not create an isolated AWS environment.
Keep the working cloud mock app unchanged while developing/exporting/loading.
Neither a successful mock test nor a local SSO login proves gold permissions or
GitHub OIDC access. Keep `DEPLOY_ENABLED` unset/false and optional AWS PR planning
unconfigured unless separately authorized. Settings were not changed/read today.

Before release, archive the known mock ZIP/build inputs and frontend HTML/asset
references to ignored local release evidence without exposing secrets/state.
Run mock regressions and new gold/null/quality tests, then opt-in real DynamoDB
and browser checks against the independently verified export. Normal PR checks
must remain credential-free; gold cloud checks cannot be silently skipped and
reported as passes. Do not use fabricated unit-test examples as real-source proof.

Build/test the Python 3.14 Linux x86_64 ZIP; the actual Linux-native check is for
Linux/CI, not a Windows import. Plan the **whole existing dev root** using matching
SSO/account/Region and explicit source settings. Record plan/artifact hashes and
review every mutation, including provider-normalized CloudFront differences.
Preserve data-lake/LF/IAM ownership; do not use -target or hide broad drift.
Only an approved later manual apply may update resources. Validation is not a
plan and does not prove permissions, quotas or successful deployment.

Before switching the API to gold, deploy the updated frontend in a mock-tested,
backward-compatible form if needed so existing open pages do not fail on null
energy or unavailable forecast dates. Retain legacy response keys and test the
transition explicitly. Then apply the reviewed API/configuration plan, build or
confirm the website with the existing HTTPS API base URL and verify the gold
version. Keep `/api` only for local Vite; the production base is the API Gateway
HTTPS prefix without `/api` or a duplicated stage. No browser credentials.
Publish hashed assets before HTML, correct MIME/cache headers, retain old hashes
and invalidate only necessary HTML using the existing manual conventions.

The existing workflow/helper explicitly plans mock and the deployed smoke expects
mock totals. Do not enable automatic deployment after a manual gold switch until
both configuration selection and tests have been deliberately updated; otherwise
the next main deployment can revert the dataset selection.

Rollback uses a **fresh reviewed full-root plan** selecting `mock` + `synthetic`
and a tested compatible application/frontend artifact. A configuration-only
rollback should restore fixtures with the new code if that regression passed.
Do not replay stale saved plans, delete projected gold records, destroy tables,
rerun Glue, edit state or change LF admins to recover an application error.
On partial writes/apply/publication, record completed operations, inspect the
failure and resume only the reviewed scope. Do not start overlapping applies.
Keep loader reports and old static assets for recovery.

Later billable categories include Athena scanned bytes/query results, S3
requests/storage, DynamoDB reads/writes/storage, Lambda/API requests, CloudFront
delivery/invalidations and logs. Exact charges depend on usage/account terms;
no prices or cost-free promises are assumed. No cloud activity occurs in stage 1.

## Persistent checklist

Update each row with date, revision, commands, evidence and any blocker. A later
prompt authorizes only its stated operations; this checklist does not authorize
future AWS access/writes/apply on its own.

| Stage | Status / exit evidence |
| --- | --- |
| 1. Inspect, decide projection, offline baseline | **Complete, 2026-11-26**, results below. |
| 2. Verify gold access and export bounded sample | **Complete, 2026-11-26**: two authorized SELECTs, 168 hourly + 7 daily rows, hashes/manifest/coverage and handoff comparisons verified; evidence below. No source mutation. |
| 3. Backend, safe loader, config plumbing | **Complete offline, 2026-11-26**: 162 Python tests, 20 frontend tests, mock browser/lint/build, isolated Terraform checks and genuine-export dry run passed. No actual AWS calls; see gold-loader.md. |
| 4. UI and integration tests | **Complete offline, 2026-11-26**: 26 frontend tests, lint/build, mock browser and 162 Python tests passed; gold smoke collection passed. Actual gold browser execution requires later loading/startup. See gold-frontend.md. |
| 5. Review destination and proposed load | **Complete read-only, 2026-11-26** at 2dacab7: source dry run, identity/DescribeTable and both Query windows passed. 175 new / 0 identical / 0 conflicts. Reviewed manifests saved; see gold-load-review.md. Conditional write permission remains unverified. |
| 6. Load approved sample, verify local app | **Complete, 2026-11-26**: 175 written / 0 skipped / 0 failed; Query verified 175 identical. Local gold browser 1 passed, mock browser 1 passed, Python 162 and frontend 26 passed; HTTP source/quality/empty/boundary checks passed. See gold-local-run.md. Deployed Lambda unchanged. |
| 7. Artifact/readiness/full-root plan | Pending separate authorization; Linux artifact proof, exact hashes and explicit proceed/hold decision. No apply. |
| 8. Manual deployment instructions and user execution | Pending approved plan; one quoted PowerShell command per box, expected results, stopping points and safe publication/rollback. |
| 9. Deployed verification and final handoff | Pending HTTPS/browser/CORS/data/provenance/quality evidence, local regressions, truthful remaining Person 3 integration work. |

Access is **unverified**, not assumed denied. If blocked later, name capability,
owner and smallest next action (SSO renewal by user; scoped gold/LF access by data
owner; scoped loader rights by account owner). Continue independent offline work
but keep all real-data success claims pending. No schema meeting is required for
the application projection above; an actual mismatch must be documented, not
resolved by rewriting Person 1's source contract.

## Offline baseline evidence and repeat commands

All results below were rerun November 26 on Windows PowerShell at the starting
revision. Python **3.14.10**, Node **24.22.2**, npm **11.19.1**, Terraform **1.17.0**.
Existing installed dependencies were reused without installs/upgrades or lock
changes. All 31 Python pins match installed versions; npm reports a valid direct
dependency tree (Vite 7.3.7, Vitest 4.1.12, Playwright 1.65.0). A separate local
comparison matched all 299 installed frontend package versions to package-lock
entries; absent platform-specific packages were not required for this host.

| Check | Result |
| --- | --- |
| `pip check` / Python pin comparison | Passed; no broken requirements, all 31 pins match. |
| pytest API + helper tests | **119 passed** (103 API + 16 script tests); no real SDK/network calls. |
| Vitest | **20 passed** across four test files. |
| Frontend lint / build | Both passed; build used `/api` locally and was not uploaded. |
| Playwright mock browser | **1 passed**; own API/Vite ports 18000/15173, all tabs/filter/chat/summary, Chromium already installed. |
| actionlint | Passed for existing workflows using local 1.7.12. |
| Terraform fmt / init / validate | Passed all source-directory formatting and both registered roots, readonly provider locks and isolated disabled backends; cached AWS providers 6.72.0/6.73.0 only. No AWS calls or downloads. |
| Linux ZIP execution / GitHub-hosted checks | Not run here: Windows cannot execute Linux native wheels; remote CI not invoked or claimed verified. ZIP was not rebuilt/downloaded for this documentation-only baseline. |
| Gold data / live application / AWS plan | Not run or verified in this stage. User-reported deployed mock website success is separate. |

Known existing warning: Starlette's TestClient/httpx deprecation. No dependency
upgrade was made just to remove it. Browser startup also emits a non-failing
NO_COLOR/FORCE_COLOR warning. Sandbox restrictions required permitted reruns for
esbuild/browser execution and cached provider reads; these are local tool-access
issues, not application/AWS test failures. An initial cache-path quoting attempt
failed before init; forward-slash quoting below resolved it. No global settings
or ACLs were changed.

Run from the repository root in a **separate PowerShell check terminal**, one
box at a time. Existing environments/dependencies/browser are prerequisites;
see [run-the-demo.md](run-the-demo.md) if setup is missing. The fresh pytest path
must remain dedicated because pytest may clear an existing basetemp directory.

```powershell
.\.venv\Scripts\python.exe -m pip check
```

```powershell
$baselineTemp = Join-Path (Get-Location) ('.qa\baseline-' + [guid]::NewGuid().ToString('N'))
```

```powershell
.\.venv\Scripts\python.exe -m pytest -c api/pytest.ini api/tests scripts/tests -q "--basetemp=$baselineTemp"
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

```powershell
& '.\.qa\actionlint-1.7.12\actionlint.exe' -no-color
```

For this machine's strictly offline Terraform checks, use its existing portable
CLI and local cache. These ignored paths are not promised in a fresh clone.
Do not use this check terminal for later live backend initialization; close it
after verification to discard the temporary CLI flags.

```powershell
$env:PATH = (Join-Path (Get-Location) '.qa\terraform-1.17.0') + [IO.Path]::PathSeparator + $env:PATH
```

```powershell
$cachedProviders = (Join-Path (Get-Location) 'build\terraform-checks\infra\environments\dev\providers').Replace('\', '/')
```

```powershell
$env:TF_CLI_ARGS_init = '-plugin-dir="' + $cachedProviders + '"'
```

```powershell
.\.venv\Scripts\python.exe scripts/check_terraform.py
```

The helper uses `init -backend=false -input=false -lockfile=readonly` with an
isolated `TF_DATA_DIR` under `build/terraform-checks`, followed by validate. The
local plugin directory contains both committed provider selections, so no
registry/AWS connection is needed. If that cache is absent, report the offline
check as unavailable rather than using the live backend to make it pass.

## Stage 2 evidence: November 26, 2026

**Result: gold access and the bounded source sample verified. Proceed to stage 3's
offline backend/loader implementation. No DynamoDB load or application release
is authorized by this result.** Starting branch remained
`test/person2-app-validation` at 9883c93; the existing stage 1 Markdown edits were
preserved. No tracked application, Terraform, dependency or workflow code changed.

Authorized identity check confirmed account **886565871385**, Region
**eu-central-1**, using `greentrack` and its existing SSO DeveloperAdminAccess
session. The sandbox initially could not resolve that profile; the permitted
outside-sandbox SDK/CLI calls succeeded. No SSO login/configuration change was
needed, and no authentication files or secret values were displayed.

Scoped readiness checks succeeded:

- Glue GetTable for `g4_greentrack_dev_gold.hourly_consumption` and
  `.daily_consumption`: both are registered Iceberg tables under the intended
  data-lake gold prefix. Five projected columns have expected types;
  `minutes_with_data` is **bigint**, not the handoff's generic int, and fits the
  planned Python integer field. `year` and `month` are integer columns available
  for the query filters. Glue's PartitionKeys was null; no partition definition
  was changed or invented. Athena/Iceberg performed source reads.
- Lake Formation settings identify the SSO role as an administrator; scoped
  ListPermissions checks for that principal/tables returned ALL grants. The
  successful SELECTs, rather than administrator status alone, establish actual
  query access for this session. No grant was added or changed.
- Athena `primary` is enabled, effective engine version 3, with no enforced
  output location/encryption configuration and no configured scanned-byte cutoff
  returned. No workgroup setting was changed. Row limits bound returned records,
  not scanning costs; household/month/date predicates limit the source selection.
- S3 HeadBucket and GetBucketEncryption confirmed the named bucket in eu-central-1,
  expected account ownership checks and AES256 default encryption. Both query
  result objects were subsequently checked with HeadObject and downloaded with
  GetObject using the expected owner. Result objects report AES256 encryption.

Only two SELECT executions were submitted, with result reuse disabled. Both
selected `household_id`, `period_start`, `energy_kwh`, `minutes_with_data` and
`is_complete`, filtered household-1, year=2009, month=6 and the exact half-open
window. Ordered `LIMIT 169`/`LIMIT 8` provide an extra sentinel row: a result
beyond expected coverage would fail validation rather than silently truncate.
Both results were below their sentinel limits, with every expected start present.

| Grain | Query execution ID | Rows | Scanned bytes | CSV SHA256 |
| --- | --- | --- | --- | --- |
| Hourly | `8994e7d3-0dbc-4951-b24f-24503e4f3892` | 168 | 8,312 | `49b498b56026c246ae2b480231636e9e7f05c1790348f75356d6fb240bf52d7f` |
| Daily | `85180a54-30da-4552-aee5-16a3b04c118d` | 7 | 717 | `25084d0c5e543fd9c5771bdf2092a6768e90bc26132e471bb62cfbbec2bd2fc4` |

The normal Athena result objects are under the approved prefix:
`s3://g4-greentrack-dev-datalake-886565871385/athena-results/person2-validation/2026-11-26-gold-week/`.
Total scanned bytes: **9,029**. Query-result object writes are the only cloud
writes in this stage; they can incur normal Athena/S3 charges. No invented price
or cost-free claim is made. No manual S3 upload, source mutation, DDL, CTAS,
INSERT, UNLOAD, preprocessing, Glue job or new resource was executed.

### Local evidence files and validation

All exports/evidence are under ignored
`build/real-data/2026-11-26-gold-week/`:

- `hourly.csv`, `daily.csv`: exact downloaded Athena output bytes, not rewritten
  or fabricated source samples.
- `hourly.sql`, `daily.sql`: exact bounded SELECT statements.
- `hourly-query.json`, `daily-query.json`: execution status, timestamps, effective
  output configuration and query statistics.
- `readiness.json`: scoped schema/workgroup/bucket/LF evidence.
- `queries.json`: local resume bookkeeping; no need to paste its contents.
- `export_stage2.py`: ignored one-stage operator helper, not the future loader.
- `manifest.json`: source identity/window/schema, query IDs, export checksums,
  counts, quality, totals, scanned bytes and validation comparisons. Keep this
  manifest with its exports for stages 3/5; do not commit the downloaded data.

Snapshot ID:
`sha256:a59514c69cc1d37884952d82fc19ee5cc15101b2461bb517693f5a8237ea4e93`.
This hashes source identity/window plus ordered normalized rows/quality in both
grains, excluding export time and query IDs. SHA256 of the completed manifest:
`2cc84aceabcf19e830028648252cae300ff03eb0cc1f99af311e5e046f91e347`.
Later evidence updates must not silently change the reviewed source bytes.

Every hour has 60 observed minutes; every day has 1,440. Both grains represent
the same **10,080 observed minutes**; do not add the two grain totals together.
There are no null-energy rows, incomplete intervals, duplicate starts, off-grain
starts, wrong households or gaps in this validation sample. This does not prove
that the wider dataset has no missing data; stage 3 still needs offline null and
incomplete-period tests.

Independent local re-reading verified both CSV hashes, all expected interval
starts and flags. Daily sums reconcile with hourly sums within **0.000001 kWh**,
with matching minute counts. The downloaded daily total is
`147.322300000000019` kWh versus hourly `147.32229999999999590` kWh: the small
difference is source floating-point accumulation. The displayed weekly total is
**147.3223 kWh**, not the synthetic 111.80 kWh.

| Day in June 2009 | Exported daily kWh (rounded here to 6 decimals) | Handoff kWh (3 decimals) | Comparison |
| --- | --- | --- | --- |
| 1 | 24.054333 | 24.054 | Matches display precision |
| 2 | 18.177300 | 18.177 | Matches display precision |
| 3 | 22.609633 | 22.610 | Matches display precision |
| 4 | 17.261000 | 17.261 | Matches display precision |
| 5 | 20.506000 | 20.506 | Matches display precision |
| 6 | 24.590833 | 24.591 | Matches display precision |
| 7 | 20.123200 | 20.123 | Matches display precision |

The manifest retains full exported precision and each comparison. Handoff
rounding tolerance was 0.000500001 kWh; no values were rounded before the
hourly/daily checks.

Athena's CSV timestamp text includes a literal suffix, for example
`2009-06-01 00:00:00.000000 UTC`. The first local parser expected an ISO timestamp
without that suffix and stopped after the hourly download. It was corrected to
remove only the known display suffix, preserving the clock. Query IDs/request
bookkeeping were persisted before polling, so resuming reused that same hourly
execution and submitted only the one remaining daily SELECT. No extra query was
used to repair local parsing. The suffix does **not** establish the original UCI
timezone; the project-clock convention remains unchanged.

### Scope and next action

No access denial or owner action is blocking stage 3. This proves the current
operator session can read/export these gold tables, **not** that the application
role, GitHub role or loader has every later required permission. DynamoDB was not
read or written; the deployed mock app was not invoked or changed. No Terraform
plan/apply, IAM/LF/workgroup/bucket-policy modification, commit or push occurred.
All exported datasets/helper evidence were confirmed ignored by Git.

Stage 3 can now implement the offline backend/loader using these genuine exports
and separate, honestly labeled test cases for null/incomplete data. Keep mock as
default and `DEPLOY_ENABLED` unset/false. Do not run a live loader or change the
deployed data source until the later destination preview/write/deployment gates.
