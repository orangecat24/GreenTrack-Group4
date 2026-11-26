# Run GreenTrack locally and deploy the current mock app

**November 26, stage 6:** genuine gold consumption is now loaded into the existing
consumption table and verified through the local API/browser. For exact local
real-data startup use [gold-local-run.md](gold-local-run.md). The deployed cloud
application remains mock; no new cloud application deployment occurred.

**November 26 update:** the user reports successful manual deployment and use of
the mock website. The November 25 resource-absence and pending-check statements
below are historical observations, not a new check of today's cloud state.
No AWS calls were made for the current preparation stage. See
[real-data-integration.md](real-data-integration.md) for the genuine-consumption
design, passing offline baseline and staged authorization checklist. That
integration is not implemented yet; the commands below still run the mock demo.

Checked November 25, 2026 on clean local `main` at `5c024c7`.
This guide is for the **existing DataMax account**, not a fresh environment.
No Terraform plan/apply, uploads, invalidations or workflow dispatches were run
while preparing it. Only this documentation was changed.

## What is ready?

| Part | Current status |
| --- | --- |
| React/FastAPI local app | Works with synthetic mock data; tested locally today. |
| Bronze/silver/gold | Teammate reports full-data processing and verified totals; see gold-handoff.md. Those computations were not rerun/reverified here. |
| Gold -> app DynamoDB loader | Not implemented. Finishing preprocessing does not connect gold to the app automatically. |
| App DynamoDB adapter | Supports synthetic rows with known keys/provenance; not a real-gold-data integration. |
| Forecast/anomalies | Illustrative forecast and predefined synthetic anomalies; no deployed model calls. |
| Assistant/weekly summary | Disconnected placeholders, not Bedrock responses. |
| SageMaker | Role/registry skeleton in Terraform; no actual model/training/endpoint resources in that module yet. |
| Live app | Expected application resources were absent in today's authorized AWS checks. |

After renewing profile `greentrack`, STS confirmed account `886565871385`.
GetFunctionConfiguration returned ResourceNotFound for `g4-greentrack-dev-api`;
GetRole returned NoSuchEntity for `g4-greentrack-dev-api-execution`; DescribeTable
returned ResourceNotFound for `g4-greentrack-dev-consumption`. The named HTTP API
and the distribution with the Terraform comment had no matching list entries.
No Lambda environment values or state contents were inspected.

## 1. Local setup (PowerShell, repository root)

Use VS Code PowerShell. Node must be 24 and Python 3.14. Use npm.cmd because the
PowerShell npm.ps1 wrapper may be blocked. No AWS login is needed for mock mode.

```powershell
node --version
if (-not (Test-Path '.venv\Scripts\python.exe')) { py -3.14 -m venv .venv }
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r api/requirements-dev.txt
Push-Location web
npm.cmd ci
Pop-Location
```

Keep the existing venv if present. These install project dependencies, not new
global versions. Dependency downloads need internet; app requests in mock mode
do not need AWS or the data pipeline. Do not copy credentials into `.env` files.

## 2. Start the API (terminal 1, repository root)

```powershell
$env:APP_DATA_MODE = 'mock'
$env:APP_DATA_SOURCE = 'synthetic'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir api --reload
```

Leave it running. Open http://127.0.0.1:8000/docs for interactive API docs.
http://127.0.0.1:8000/ redirects there; `/health` returns JSON.

## 3. Start the website (terminal 2, repository root)

```powershell
cd web
$env:VITE_API_BASE_URL = '/api'
$env:API_PROXY_TARGET = 'http://127.0.0.1:8000'
npm.cmd run dev
```

Open http://127.0.0.1:5173. These terminal-local variables override an older
deployment URL/proxy setting; no global environment settings change. The browser
asks Vite for `/api/consumption`; Vite forwards `/consumption` to port 8000.
Keep both terminals open; Ctrl+C stops each server. Do not use `npm run preview`
for this setup: it serves built files without the development API proxy.

Use `household-1`, June 1-7, 2009. Consumption totals **111.80 kWh** in the mock
week; anomalies has three entries; forecast targets June 8 and repeats the prior
day; assistant and weekly-summary actions return explicit placeholders. These
values are not the gold data's totals. The gold handoff reports different real
source-data values for the same week.

## 4. Local verification (another terminal, repository root)

```powershell
.\.venv\Scripts\python.exe -m pip check
# Avoid an inaccessible pytest-of-... directory left in the Windows temp area.
# Use a fresh dedicated path each time: pytest can empty an existing basetemp.
$testTemp = Join-Path (Get-Location) ('.qa\pytest-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest -c api/pytest.ini api/tests scripts/tests -q "--basetemp=$testTemp"
Push-Location web
npm.cmd run test:run
npm.cmd run lint
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd run test:e2e
Pop-Location
```

The browser install is needed once and after a Playwright update. The smoke test
starts/stops its own mock servers on 18000/15173 and visits every tab, changes a
date, sends chat and requests a weekly summary. It does not call cloud services.

Windows troubleshooting: if every Python test errors while setting up `tmp_path`
with access denied under `AppData/Local/Temp/pytest-of-...`, use the fresh local
`--basetemp` command above. It avoids that inaccessible directory without admin
mode or global TEMP/permission changes. Never set basetemp to the repository,
source or a directory with valuable files: pytest may clear an existing target.
If the API setup was run from web/ by mistake, use the root .venv after changing
back to the repository root. ESLint now ignores nested Python virtual environments
so their installed JavaScript is not mistaken for application source.

Today's results: 119 Python tests, 20 frontend tests, lint, production build,
local browser flow, pip check and actionlint passed. Terraform 1.17.0 fmt and
isolated backend-disabled init/validate passed for both registered roots,
including the new challenge2/challenge3 modules. The API tests still emit the
existing upstream Starlette/httpx deprecation warning. These are not live tests.

## 5. Can this be deployed without models/assistant?

**Yes, as an explicitly synthetic mock demo.** The UI does not require an ML
endpoint or Bedrock to start. Keep `app_data_mode=mock`. Do not claim the deployed
app uses gold data, live inference or a live assistant. Existing resources still
incur normal request/storage/log costs; quotas and write permissions require a
real plan/deployment check. No fixed price/free-tier assumption is made.

Do **not** simply enable `DEPLOY_ENABLED` yet. The dev root now also manages the
existing data lake, Lake Formation and SageMaker scaffolding. In particular,
`infra/challenge2/lake_formation.tf` sets its account-wide LF admins from the
current deploying role plus an empty-by-default extra-admin list. Today's
GetDataLakeSettings read showed the existing SSO DeveloperAdminAccess role as
the only admin. A GitHub apply uses a different identity, and the current code
would request a different admin list. No actual plan was run to assess drift.

Before GitHub auto-apply, coordinate an explicit stable admin configuration with
the foundation/data-lake owner, preserving approved existing admins. Do not
change shared-account governance as a side effect of application deployment.
The shared PowerUser deployment role itself was not changed here.

For a first app deployment, a **reviewed manual plan using the existing SSO
identity** is preferable to blindly enabling the current automatic workflow.
It should preserve the current LF administrator identity, but a plan must still
confirm that. Check the whole shared root for deletions, replacements, revoked
grants and unintended data-lake changes. Do not use `-target` to bypass review.

Do not follow the fresh-environment bootstrap instructions in
deployment-runbook.md for this account. Bootstrap and the data pipeline already
exist according to the handoff. Do not re-upload the raw dataset just to test the
website: that can trigger more Glue work and is unrelated to the mock app.

## 6. First manual deployment: setup and review (NOT executed here)

### How to enter the commands

**Use one command at a time, in the order shown.** Each PowerShell box below
contains exactly one command. Copy the entire command, paste it into the terminal,
then press **Enter once**. A long command may wrap visually; copy the whole box.

Wait until the command finishes and the `PS ...>` prompt returns before moving
to the next box. Do not paste commands from several boxes together. If an error
appears, stop at that step instead of continuing.

- Lines starting with `$` are commands too. They save a value or configure this
  terminal; they often succeed without printing anything.
- Do not copy the `PS ...>` prompt or `>>` continuation prompt.
- Do not add a backslash `\` at the end of a command.
- If you see `>>` unexpectedly, PowerShell is waiting for an unfinished command.
  Press Ctrl+C to cancel that input, then paste the complete command again.
- Keep using this **same terminal** through sections 6, 7 and 8. Closing it loses
  the variables these steps use.

The local API can stay running. Stop the local website and any frontend test
watchers before section 7.4 reinstalls dependencies: Windows cannot replace
esbuild.exe while Vite/Vitest is using it. Open a separate PowerShell terminal
for deployment. If another deployment/apply is running, wait for it to finish;
do not cancel it. Coordinate with the owner if GitHub deployment is enabled.

Section 6 signs in, builds the package and previews a plan. It does not apply
infrastructure changes. Section 7 is the separate, billable deployment step.

### 6.1 Go to the repository root

Copy this command, press Enter, then wait for the prompt:

```powershell
Set-Location 'C:\Users\Macintoks\Desktop\Master\Other\Internship And Job Applications\DataMax\GreenTrack-Group4'
```

The prompt should now end in `GreenTrack-Group4>`, not `web>` or `api>`.
Stay at this location for all remaining steps; the npm commands below select
web/ for you.

### 6.2 Sign in to AWS and finish the browser step

Run **only this command first**:

```powershell
aws sso login --profile greentrack
```

If a browser opens, complete the DataMax sign-in/MFA and CLI authorization.
Return to this terminal. Wait for a successful-login message and the PowerShell
prompt to return. **Do not paste the next command while login is still running.**

### 6.3 Select the profile and Region

Run this command and press Enter. No output is normal:

```powershell
$env:AWS_PROFILE = 'greentrack'
```

Then run this next command and press Enter. No output is normal here too:

```powershell
$env:AWS_REGION = 'eu-central-1'
```

These select the profile and application Region for this terminal only.

### 6.4 Check the account

Run this command and wait for the prompt. It saves the result, so no output is
normal unless the CLI reports an error:

```powershell
$account = aws sts get-caller-identity --query Account --output text --no-cli-pager
```

Next, run this entire single-line check:

```powershell
if ($LASTEXITCODE -ne 0 -or $account -ne '886565871385') { throw 'Stop: wrong account or expired login.' }
```

If it prints a red error, stop. If it returns silently, the check passed.
To display the checked account, run:

```powershell
$account
```

Expected output: `886565871385`. Do not continue with another account.

### 6.5 Select Terraform 1.17.0

This machine already has the portable pinned copy. Run:

```powershell
$env:PATH = (Join-Path (Get-Location) '.qa\terraform-1.17.0') + [IO.Path]::PathSeparator + $env:PATH
```

Then check which version this terminal will use:

```powershell
terraform version
```

Expected: `Terraform v1.17.0`. If the version is different or the command is
missing, stop and select/install the pinned version. Do not change the repo's pin
just to bypass the check. No global PATH change is made by the command above.

### 6.6 Build the Lambda ZIP

Run and wait until the build finishes:

```powershell
.\.venv\Scripts\python.exe scripts/build_lambda.py
```

Then check success:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Lambda ZIP build failed; stop here.' }
```

Expected: a `Built build\greentrack-api.zip` message and SHA256 hash. This downloads
Linux-compatible packages and creates a local ZIP; it does not upload to AWS.

### 6.7 Run the offline Terraform checks

Run:

```powershell
.\.venv\Scripts\python.exe scripts/check_terraform.py
```

Wait for initialization/validation to finish for both roots. Then run:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Terraform checks failed; stop here.' }
```

Expected: successful configuration validation for bootstrap and dev.
This helper uses isolated metadata and does not connect to the live backend.

### 6.8 Connect to the existing dev backend

Now run this command and wait for it to finish:

```powershell
terraform -chdir=infra/environments/dev init -reconfigure -input=false -lockfile=readonly
```

Then check success:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Backend initialization failed; stop here.' }
```

This initialization accesses the existing remote backend. It does not apply
resources. Do not run bootstrap apply or make a new state bucket.

### 6.9 Save and preview a plan

First save a local filename in a variable. No output is normal:

```powershell
$reviewPlan = Join-Path (Get-Location) 'build\first-app-preserved-grants.tfplan'
```

Then run the plan command:

```powershell
terraform -chdir=infra/environments/dev plan -input=false -var=app_data_mode=mock "-out=$reviewPlan"
```

Wait for the plan summary and prompt to return. Then check success:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Plan failed; do not apply an older plan.' }
```

### 6.10 STOP and review before section 7

**Updated November 25 review:** the original `build/first-app.tfplan` is rejected
because it removes an existing SageMaker database permission. A scoped correction
and a new full-root plan have now been reviewed: use
`build/first-app-preserved-grants.tfplan`, with **27 additions, 5 identical-content
script/ruleset updates and 0 destructions/replacements**. All existing Lake
Formation grants/admins are unchanged. See [first-app-plan-review.md](first-app-plan-review.md)
for the new plan's hash and evidence. If the reviewed new file already exists,
do not rerun section 6.9 unnecessarily: select and check it in section 7.1.
A regenerated file, even under the same name, needs another review.

A successful plan is not approval to apply it. Binary plans can contain sensitive
values; keep this ignored file local. Review the proposed changes, including:

- Correct account/Region and existing resources tracked in the existing state.
- Expected new app resources; no raw/silver/gold deletion or unintended replacement.
- Existing Lake Formation admins and grants retained, especially SageMaker's gold grant.
- No existing GitHub/data-lake role being recreated as a duplicate.
- No blindly copied `terraform.tfvars.example`: its API-only consumer list would
  replace the default SageMaker consumer. The mock API does not need a gold grant.

Resolve unexpected changes with the relevant owner and generate a fresh plan.
Review the identity-dependent Lake Formation issue in section 5 before enabling
GitHub deployment. A local SSO plan does not prove a GitHub plan is identical.

## 7. Apply the reviewed plan and publish (NOT executed here)

**Start this section only after the plan is reviewed and acceptable.**
No other deployment should be running. Continue in the same root terminal.
If code/state changed since planning, generate and review a fresh plan first.

### 7.1 Select and check the exact NEW plan that was reviewed

Your terminal may still have the rejected old filename saved in `$reviewPlan`.
Replace it by running this command from the repository root:

```powershell
$reviewPlan = Join-Path (Get-Location) 'build\first-app-preserved-grants.tfplan'
```

Then check that it exists:

```powershell
if (-not $reviewPlan -or -not (Test-Path -LiteralPath $reviewPlan)) { throw 'Reviewed plan missing: complete section 6 in this terminal first.' }
```

No output means the file check passed. Next save its fingerprint:

```powershell
$reviewedPlanHash = (Get-FileHash -LiteralPath $reviewPlan -Algorithm SHA256).Hash
```

Then verify it is the binary reviewed on November 25:

```powershell
if ($reviewedPlanHash -ne '90378945114720104d4bad9a1ca4b8b1f48728e5a7910622fef5514711120f7c') { throw 'Plan differs from the reviewed file; stop for a fresh review.' }
```

No output means the hash matches. Do not bypass this check by substituting a
different expected hash yourself. A new plan requires a new review first.

### 7.2 Apply: this starts actual AWS changes

The next command creates/updates billable resources. Because it uses a saved
plan, **do not expect another yes/no approval prompt**. Run it only when you have
decided to apply the reviewed changes:

```powershell
terraform -chdir=infra/environments/dev apply $reviewPlan
```

Wait for `Apply complete!` and the prompt to return. This can take several
minutes. Then run:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Apply failed; stop before publishing.' }
```

On failure, stop and inspect the error. Some resources may already have changed.

### 7.3 Read the application URLs and destinations

Run:

```powershell
$application = terraform -chdir=infra/environments/dev output -json application | ConvertFrom-Json
```

It saves the values without displaying them. Next, check them:

```powershell
if ($LASTEXITCODE -ne 0 -or -not $application.api_base_url) { throw 'Application outputs are missing; stop here.' }
```

Then display only these public destinations:

```powershell
$application | Select-Object api_base_url, website_url, frontend_bucket_name, cloudfront_distribution_id
```

Keep this terminal open: later commands use `$application`. The API prefix should
be an HTTPS API Gateway URL without an added `/api` or `/stage` suffix.
The website URL should be HTTPS on CloudFront, not an S3 website URL.

### 7.4 Build the frontend for this API

**First stop the local frontend.** Go to the terminal running `npm.cmd run dev`
(port 5173), press Ctrl+C and wait for its PowerShell prompt to return. Stop any
Vitest watch session too. The Python API may keep running. Do not close the
deployment terminal: it holds `$application` and the AWS settings.

Return to that same deployment terminal at the repository root. If npm ci
previously failed with EPERM/unlink on esbuild.exe, rerun npm ci below after
stopping the frontend; it may already have removed some dependency files.
Do not skip straight to the build. Keep the local frontend stopped until the
dependency installation and deployment build are complete. Do not use admin
mode or delete node_modules as the first response to this file-lock error.

First set the public API URL for the build:

```powershell
$env:VITE_API_BASE_URL = $application.api_base_url
```

Then install the locked frontend dependencies, still from the repository root:

```powershell
npm.cmd --prefix web ci
```

Check success before continuing:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed; stop here.' }
```

Build:

```powershell
npm.cmd --prefix web run build
```

Wait for the successful Vite build, then check success:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed; do not upload.' }
```

This creates web/dist locally. It does not upload anything yet. The API URL is
embedded in the JavaScript, so changing an environment variable after upload
cannot change that built URL.

### 7.5 Upload JavaScript, then CSS, then HTML

Upload JavaScript first and wait for completion:

```powershell
aws s3 sync web/dist/assets "s3://$($application.frontend_bucket_name)/assets" --exclude '*' --include '*.js' --content-type application/javascript --cache-control 'public,max-age=31536000,immutable' --region eu-central-1
```

Check success:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'JavaScript upload failed; do not upload HTML.' }
```

Next upload CSS and wait:

```powershell
aws s3 sync web/dist/assets "s3://$($application.frontend_bucket_name)/assets" --exclude '*' --include '*.css' --content-type text/css --cache-control 'public,max-age=31536000,immutable' --region eu-central-1
```

Check success:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'CSS upload failed; do not upload HTML.' }
```

Only after both asset uploads succeed, upload HTML:

```powershell
aws s3 cp web/dist/index.html "s3://$($application.frontend_bucket_name)/index.html" --content-type text/html --cache-control 'no-cache,max-age=0,must-revalidate' --region eu-central-1
```

Check success:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'HTML upload failed; stop here.' }
```

These commands keep old hashed assets for existing browser tabs. The rules match
the current JS/CSS/HTML build; future asset types need correct MIME/cache rules.

### 7.6 Refresh CloudFront's entry pages

Run:

```powershell
$invalidationId = aws cloudfront create-invalidation --distribution-id $application.cloudfront_distribution_id --paths / /index.html --query Invalidation.Id --output text --no-cli-pager
```

Check success:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Invalidation creation failed; stop here.' }
```

Then wait for completion:

```powershell
aws cloudfront wait invalidation-completed --distribution-id $application.cloudfront_distribution_id --id $invalidationId --no-cli-pager
```

This command can remain quiet for several minutes. Wait for the prompt instead
of pasting the next command while it runs. After it returns, check:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Invalidation has not completed; check its status before testing.' }
```

## 8. Test the deployed version

Continue in the same root terminal after successful deployment/publication.

### 8.1 Check API health

Run:

```powershell
Invoke-RestMethod "$($application.api_base_url)/health"
```

Expected: status `ok`, data_mode `mock`, is_demo `True`.
If this fails, stop and inspect the error before treating the deployment as healthy.

### 8.2 Check an actual data response

Run:

```powershell
Invoke-RestMethod "$($application.api_base_url)/consumption?household_id=household-1&start=2009-06-01T00:00:00Z&end=2009-06-02T00:00:00Z&grain=daily"
```

Expected: one mock daily item with energy_kwh 13.46 and is_demo=true.
Health alone does not verify data responses, website delivery or CORS.

### 8.3 Configure the real deployed browser test

Set the website URL; no output is normal:

```powershell
$env:DEPLOYED_WEBSITE_URL = $application.website_url
```

Next set the API URL; no output is normal:

```powershell
$env:DEPLOYED_API_BASE_URL = $application.api_base_url
```

If Chromium is not already installed, run the project's local Playwright command:

```powershell
.\web\node_modules\.bin\playwright.cmd install chromium
```

Wait until installation completes, then check:

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Browser installation failed; stop here.' }
```

It is fine to run this install command again when the browser is already present.

### 8.4 Run the deployed browser test

Run:

```powershell
npm.cmd --prefix web run test:deployed
```

Wait for the result. Expected: `1 passed`. The test starts no local servers:
it visits the real HTTPS website and checks all four tabs, date filters,
placeholder chat/summary, the API origin and CORS preflight. It expects mock data
and will need updating when real consumption/model data are integrated.

### 8.5 Open the website yourself

Print the URL:

```powershell
$application.website_url
```

Copy that printed HTTPS URL into your browser's address bar. Do not use the S3
bucket URL: the bucket is private and CloudFront serves the website.

If a test fails after apply/upload, some resources/files may already be live.
Inspect the failed step, browser Network errors and the eu-central-1 log groups
`/aws/lambda/g4-greentrack-dev-api` and `/aws/apigateway/g4-greentrack-dev-api`.
Do not destroy data or reset Terraform state to fix an application error.

### 8.6 Recover from chat preflight HTTP 405

Observed November 25, 2026: the user reports a successful manual apply and asset
publication. Independent public HTTPS checks confirmed `/health` returns 200
with `data_mode=mock` and `is_demo=true`. However, `OPTIONS /chat` returned 405
and `{"detail":"Method Not Allowed"}`, despite having the correct CORS headers.
Read-only API Gateway metadata confirmed the deployed `$default` route and the
correct CloudFront/local CORS origins. The full deployed smoke has not passed.

Before a cross-origin JSON chat POST, browsers send an OPTIONS preflight to ask
whether that request is allowed. In this deployment the catch-all `$default`
route forwarded OPTIONS into FastAPI, which rejected the unsupported method.
The local Terraform correction replaces that route with `GET /{proxy+}`, adds
`GET /` for the documentation redirect, and adds `POST /chat` for chat/summary.
OPTIONS is left to API Gateway's existing CORS handling. The `$default` **stage**
stays, so URLs and the already published frontend do not change. CORS remains
gateway-only; no wildcard origins, FastAPI middleware or IAM changes were added.
See [AWS's HTTP API CORS documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-cors.html).

The correction is local until a **new reviewed plan** is applied. Do not reuse
the earlier deployment plan. In the original repository-root PowerShell terminal,
with the same greentrack profile and eu-central-1 settings from section 6:

1. Run this command, press Enter and wait for Terraform to finish:

   ```powershell
   & '.\.qa\terraform-1.17.0\terraform.exe' '-chdir=infra/environments/dev' plan '-input=false' '-var=app_data_mode=mock' '-out=../../../build/chat-cors.tfplan'
   ```

   Keep the quotes around each complete flag/value pair. The earlier unquoted
   command produced "Too many command line arguments" in Windows PowerShell;
   Terraform rejected it before creating a plan or changing resources. Quoting
   keeps the relative output path together as a single native-command argument.

2. After the prompt returns, check the command succeeded:

   ```powershell
   if ($LASTEXITCODE -ne 0) { throw 'Plan failed; stop here.' }
   ```

3. **Stop for review.** Expected scope is updating `module.challenge1`'s existing
   route key and adding two routes, usually **2 to add, 1 to change, 0 to destroy**.
   This is an expectation, not a live plan result. Share the route differences
   and final summary for review. IAM, LF, Glue, data-lake objects, tables, Lambda,
   frontend bucket and CloudFront should have no changes. Investigate any other
   differences before applying. Do not share state, credentials or saved-plan
   files. Configuration validation alone does not prove this deployment works.

   **Actual November 25 review:** the saved `build/chat-cors.tfplan` has **2 to
   add, 2 to change, 0 to destroy**, including an investigated CloudFront origin
   configuration update. It preserves the same bucket and OAC; no resources are
   replaced. This exact plan is acceptable under the review in
   [chat-cors-plan-review.md](chat-cors-plan-review.md), which records its hash,
   the extra difference and preservation checks. That review supersedes the
   route-only estimate for this file, not for arbitrary future plans.

4. **Only after that new plan is reviewed and approved**, apply the saved plan:

   ```powershell
   & '.\.qa\terraform-1.17.0\terraform.exe' '-chdir=infra/environments/dev' apply '../../../build/chat-cors.tfplan'
   ```

5. Wait for `Apply complete!`, then check success:

   ```powershell
   if ($LASTEXITCODE -ne 0) { throw 'Apply failed; inspect the error before continuing.' }
   ```

6. With the deployed-test URL variables still set from section 8.3, rerun:

   ```powershell
   npm.cmd --prefix web run test:deployed
   ```

The smoke requires a successful OPTIONS status and the exact CORS headers,
then visits all four tabs and sends the mock requests. Its failure message now
includes the preflight status/body. Bounded retries allow gateway propagation;
if it still fails, inspect the new response. No Lambda rebuild, frontend upload,
CloudFront invalidation, seeding or data-pipeline rerun is needed for this route
correction. No plan, apply or publication was performed by the troubleshooting
session.

Local correction checks passed: Terraform 1.17.0 formatting, isolated
backend-disabled init with readonly provider locks, and validate for both
registered roots; frontend 20 tests, lint and production build. The initial
sandbox blocked provider-network/esbuild access; the permitted reruns passed.
API code/dependencies were unchanged. The deployed browser pass remains pending
the reviewed route deployment; health success alone is not a complete pass.

## 9. Later automatic deployments and real data

Once the LF admin configuration and full-root plan are reviewed for the GitHub
identity, the maintainer can set repository Actions variable `DEPLOY_ENABLED`
to exactly `true`. The next reviewed main merge/push runs existing checks,
builds/tests the Linux ZIP, authenticates with OIDC, plans/applies the dev root,
publishes and runs the deployed browser smoke. This is not required to run
locally. The setting was not inspected or changed in this task; check its
current value in repository Settings before pushing any main change.

See deployment-pipeline.md for all variables and recovery. Do not bypass the
CI-only guards in scripts/deployment.py by fabricating GITHUB_ACTIONS locally.
The manual commands above are the local route; the helper is the CI route.

For real gold-backed consumption, implement and review the gold loader/mapping,
coverage/null handling and real-data provenance contract first. Current API
responses enforce is_demo=true and the DynamoDB repository rejects non-demo
records. Do not mark real rows as synthetic just to bypass those checks.
ML/assistant can be integrated separately later. seed_demo.py only writes our
invented fixtures; it is not a substitute for a gold loader.
