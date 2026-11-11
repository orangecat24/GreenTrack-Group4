# Person 2 application infrastructure: prepared, not deployed

This increment defines the application and builds a local deployment artifact.
No AWS resource, backend state, table, asset upload or deployment was accessed by
this task. The teammate reports that the foundation bucket was already applied;
see [the foundation handoff](foundation-handoff.md). A future authorized
application plan/apply is still required. Existing local
Uvicorn/Vite commands and the four-tab UI are unchanged.
The GitHub pipeline is now prepared but off by default; see
[deployment-pipeline.md](deployment-pipeline.md) for activation, exact variables,
readiness evidence and recovery. The manual examples below are alternatives,
not commands executed by the implementation session.

## How the pieces connect

```text
Browser -> CloudFront HTTPS -> private S3 objects (React files)
Browser -> API Gateway HTTPS -> Lambda -> Mangum -> FastAPI route
                                               -> service -> mock repository
                                                          -> JSON response
                                                          -> optional DynamoDB Query
```

CloudFront serves only static files. The browser calls API Gateway directly
using a public URL embedded at frontend build time. There is no CloudFront
`/api` behavior and no production Vite proxy. No AWS credentials enter the SPA.

`infra/bootstrap` still owns the existing state-bucket definition, with local
bootstrap state. `infra/environments/dev` still owns the development S3 backend,
account guard and eu-central-1 provider. Its new `application.tf` calls
`infra/challenge1`; `infra/modules/shared` and its deployment role are unchanged.
The foundation PR reports bootstrap was already applied from the owner's laptop
and supplies the existing role ARN and dev backend settings. Those exact values
are recorded in [foundation-handoff.md](foundation-handoff.md). Reuse them; do
not recreate the bucket or lose the owner's local bootstrap state. We have not
inspected AWS or confirmed which resources are tracked in dev's remote state.

## Resources and defaults

| Resource/file | Purpose and limits |
| --- | --- |
| `infra/challenge1/main.tf` | Three `PAY_PER_REQUEST` tables, string `PK`/`SK`, no indexes, plus six Standard non-secret SSM configuration parameters. No table records are created. |
| `api.tf`: execution role | Trusts Lambda only. Writes only to its pre-created log group. In mock mode it has no DynamoDB permission. DynamoDB mode adds only `dynamodb:Query` on the three exact table ARNs; no Scan, seed writes, SSM reads or AI permissions. |
| `api.tf`: Lambda | Python 3.14, x86_64, 512 MB, 15-second timeout, reserved concurrency 2. Handler `app.lambda_handler.handler`. No VPC or provisioned concurrency. |
| `api.tf`: HTTP API | Payload v2 proxy, `$default` stage and route, automatic stage deployment, throttle target 2 requests/second with burst 10. Throttling is best effort, not a spending cap. |
| `api.tf`: logs | Separate Lambda and gateway log groups, both seven-day retention. Gateway logs contain request ID/status/route/response size, not query strings or chat bodies. |
| `frontend.tf`: S3 | Account-suffixed `g4-greentrack-dev-web-...` bucket, all public access blocked, ACLs disabled, AES256 encryption, no website endpoint. Nonempty bucket deletion fails (`force_destroy=false`). |
| `frontend.tf`: CloudFront/OAC | Default HTTPS domain/certificate, HTTP redirects to HTTPS, signed origin access restricted to this distribution, PriceClass_100, compression. Default object `index.html`. |
| `frontend.tf`: cache policy | Minimum TTL 0 so HTML's `no-cache` can be respected; default TTL 60 seconds, maximum one year for hashed assets. No cookies/query strings in the static cache key. |
| `api/app/lambda_handler.py` | Small Mangum adapter around the unchanged FastAPI app; `lifespan="on"` initializes and closes the repository on every invocation, including warm invocations. |
| `scripts/build_lambda.py` | Downloads pinned Linux wheels and builds ignored `build/greentrack-api.zip`. No host `.venv` files, tests, seed loader, credentials, `.env` or bytecode are copied. |
| `scripts/check_lambda_zip.py` | Linux-only check that imports the artifact's own libraries and runs the offline API Gateway event tests against it. |

Supporting resources without their own names/tags, such as bucket encryption,
permissions and integrations, belong to the named/tagged parent resources.
Provider defaults retain `Group=g4`, `Project=greentrack`, `Environment=dev` and
`ManagedBy=terraform`; the application adds `Challenge=1` where tags are supported.

The API is a public, unauthenticated synthetic demo. CORS controls browser
cross-origin access, not authentication. Do not put private household data in it.
Tabs use React state, so no deep-link router or blanket S3 403/404-to-HTML rewrite
is needed; a missing JavaScript asset remains an error.

## Inputs, configuration and outputs

The child accepts `name_prefix` (required), `lambda_zip_path` (required),
`data_mode` (default `mock`), `local_cors_origins` (default the exact localhost
and 127.0.0.1 origins on port 5173), and additional `tags`. The dev root supplies
`g4-greentrack-dev`, the repository's ZIP path and `var.app_data_mode`.

One Terraform map supplies both Lambda environment variables and SSM parameters
under `/g4-greentrack-dev/api/`:

- `APP_DATA_MODE`: `mock` by default.
- `DYNAMODB_REGION`: inherited eu-central-1.
- `DYNAMODB_CONSUMPTION_TABLE`, `DYNAMODB_ANOMALIES_TABLE`,
  `DYNAMODB_FORECASTS_TABLE`: application table names from Terraform.
- `DYNAMODB_FORECAST_ORIGIN`: `2009-06-08T00:00:00Z`.

SSM is a non-secret configuration record for operators/future integrations.
The function receives the same values directly; it does not fetch SSM during
startup. Edit configuration through Terraform, not manually in SSM: a manual
SSM edit does not update the Lambda environment. SSM creates no new secrets.

The dev root's `application` output contains `api_base_url`, `website_url`,
`frontend_bucket_name`, `cloudfront_distribution_id`, `table_names`,
`configuration_parameters` and `api_lambda_name`. Its existing
`github_deploy_role_arn` output remains intact.

Tables use the repository's existing shared keys, not a new schema. Example:
`PK=HOUSEHOLD#household-1#GRAIN#daily`,
`SK=2009-06-01T00:00:00.000000Z`. Forecast PKs also include their origin;
SKs identify target hours. See [the handoff](person2-handoff.md#three-table-schemas).

For a later reviewed switch, set `app_data_mode=dynamodb` in the dev Terraform
configuration (or pass `-var=app_data_mode=dynamodb` to a future authorized plan).
This updates both the environment and the conditional Query policy. Changing
only the Lambda environment in AWS would leave the mock role without Query.
Empty, unseeded tables return empty results. There is no startup seeding or
silent fallback. The separate loader still requires explicit table names,
Region and `--write`, under a separate authorized identity with BatchWriteItem.
Synthetic data remains `is_demo=true` in DynamoDB. Chat/weekly summary remain
disconnected placeholders; no Person 3 Lambda, Bedrock or SageMaker is created.

## Build and safe checks: Windows PowerShell

Run from the repository root. Use Python 3.14, Node 24 and Terraform **1.17.0**.
No global PATH or tool settings need to change. Terraform was downloaded for
this task into ignored `.qa/terraform-1.17.0`; that portable copy is local only,
not part of a fresh clone. Otherwise install the pinned CLI before these commands.

```powershell
# Only if absent: py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r api\requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -c api/pytest.ini api/tests -q
.\.venv\Scripts\python.exe scripts/build_lambda.py

# Only when using the task's portable copy; process-local PATH, not global.
$env:PATH = (Join-Path (Get-Location) '.qa\terraform-1.17.0') + [IO.Path]::PathSeparator + $env:PATH
$env:CHECKPOINT_DISABLE = '1'
.\.venv\Scripts\python.exe scripts/check_terraform.py

Push-Location web
npm.cmd ci
npm.cmd run test:run
npm.cmd run lint
npm.cmd run build
# Install once, and again when Playwright changes:
npx.cmd playwright install chromium
npm.cmd run test:e2e
Pop-Location
```

Local development is still two terminals: API with
`.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir api --reload`,
and `npm.cmd run dev` from `web/`. Mock is the default. `APP_DATA_MODE=mock`
can be set explicitly in PowerShell with `$env:APP_DATA_MODE = 'mock'`.

## Build and safe checks: Linux / CI

Install Terraform 1.17.0 on PATH; the existing Actions workflow does this for
the Terraform job. Create the project venv only if absent.

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r api/requirements-dev.txt
.venv/bin/python -m pip check
.venv/bin/python -m pytest -c api/pytest.ini api/tests -q
.venv/bin/python scripts/build_lambda.py
.venv/bin/python scripts/check_lambda_zip.py
CHECKPOINT_DISABLE=1 .venv/bin/python scripts/check_terraform.py
cd web
npm ci
npm run test:run
npm run lint
npm run build
npx playwright install --with-deps chromium
npm run test:e2e
```

The ZIP builder uses `--only-binary=:all:`, CPython 3.14, ABI `cp314`/`abi3`/`none`,
and x86_64 manylinux_2_28/manylinux2014/manylinux_2_17 targets. The current
pydantic-core wheel is cp314 manylinux2014/manylinux_2_17, compatible with
Amazon Linux 2023. Native contents are checked for ELF64 AMD64; a missing wheel
fails instead of compiling on Windows or downgrading Python. `--no-deps` means
the fully pinned requirements file explicitly lists the entire runtime set;
keep transitive pins current when adding a dependency. Optional wheel CLI
scripts are omitted because Lambda imports libraries instead.

Source newlines, ZIP timestamps, file order and permissions are normalized;
the builder prints its SHA256. Dependency versions are pinned; this is not a
hash-locked wheel supply-chain manifest. No container fallback was needed.
Windows can build/inspect Linux binaries but cannot execute their native code.
CI's added Linux ZIP check verifies real packaged imports and event handling;
it still does not emulate Lambda's Amazon Linux runtime or call AWS.

Official references: [Lambda Python runtimes](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html),
[native wheel packaging](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html),
[Mangum lifespan](https://mangum.fastapiexpert.com/lifespan/).

The Terraform helper checks formatting in all source directories and runs
`init -backend=false -input=false -lockfile=readonly` plus `validate -no-color`
for bootstrap/dev. Child modules are checked through dev, not registered as
new roots. It does not need the ZIP for validation; a future plan fails with a
clear precondition if the ZIP is absent. Provider lockfiles are unchanged.
Provider downloads use the internet but do not authenticate to AWS.
The helper isolates TF_DATA_DIR per root to avoid reusing a developer's live
backend cache: `-backend=false` alone proved insufficient after real backend
initialization. Existing .terraform metadata is preserved.
**Validate is not a plan:** it cannot confirm account permissions, quotas,
provider data-source results, OAC delivery or a successful runtime deployment.

## Later deployment order: documentation only, not executed

Before any deployment, coordinate with the foundation owner. The current shared
GitHub role trusts PR subjects and has PowerUserAccess plus broad `g4-` IAM
management. The team can continue with this setup; narrower trust and permissions,
including protection against self-modification, are recommended improvements,
not a technical prerequisite. See [the recorded decision](foundation-handoff.md#current-permission-decision).
This task deliberately leaves those policies unchanged. Ordinary PR checks stay
credential-free. Main plan/apply automation is prepared behind `DEPLOY_ENABLED`;
it has not been enabled or run. Optional AWS PR planning needs separate read-only
access and does not block main deployment. See [the pipeline guide](deployment-pipeline.md).

1. Reuse the already-applied bootstrap bucket and the recorded account/Region,
   role ARN and dev backend. Coordinate state ownership with the foundation owner;
   the handoff does not establish dev state's contents. Preserve bootstrap's
   local state with its owner. Do not create a second foundation or reapply
   bootstrap from a fresh checkout.
2. Build/test the Linux Lambda ZIP. Rebuild it whenever application code or
   runtime requirements change; Terraform uses its file hash to detect updates.
3. In an explicitly authorized AWS session, initialize the dev backend, review
   an AWS plan, then apply it. This also needs permissions to manage the existing
   shared foundation; the application execution role does not provide them.
4. Read the resulting application output, build the SPA with its API base URL,
   then upload hashed assets first and HTML last. Terraform does not upload
   frontend files. A newly created distribution has no app until those uploads.
5. Verify HTTPS, CORS preflight, each tab, placeholder chat, logs, direct S3
   denial and API limits in AWS. Seeding and DynamoDB mode require separate
   authorization; mock mode already serves fixtures without table reads.

The following commands are **later-only examples**, not part of local checks.
They can access AWS state or create billable resources. A successful plan is not
an approval to apply. Never commit its saved binary, state or personal tfvars.

```powershell
# LATER ONLY: approved AWS session, foundation confirmed, ZIP already built.
terraform -chdir=infra/environments/dev init -input=false -lockfile=readonly
terraform -chdir=infra/environments/dev plan -out=application.tfplan
# Only after the plan is reviewed and deployment is authorized:
terraform -chdir=infra/environments/dev apply application.tfplan
$application = terraform -chdir=infra/environments/dev output -json application | ConvertFrom-Json

$env:VITE_API_BASE_URL = $application.api_base_url
Push-Location web
npm.cmd ci
npm.cmd run build
Pop-Location
Remove-Item Env:\VITE_API_BASE_URL

# Upload hashed assets first. No --delete: older tabs may still need old hashes.
aws s3 sync web/dist/assets "s3://$($application.frontend_bucket_name)/assets" --exclude '*' --include '*.js' --content-type application/javascript --cache-control 'public,max-age=31536000,immutable' --region eu-central-1
aws s3 sync web/dist/assets "s3://$($application.frontend_bucket_name)/assets" --exclude '*' --include '*.css' --content-type text/css --cache-control 'public,max-age=31536000,immutable' --region eu-central-1
aws s3 cp web/dist/index.html "s3://$($application.frontend_bucket_name)/index.html" --content-type text/html --cache-control 'no-cache,max-age=0,must-revalidate' --region eu-central-1
aws cloudfront create-invalidation --distribution-id $application.cloudfront_distribution_id --paths /index.html /
```

Linux equivalents, after the same explicit authorization (requires `jq` and
AWS CLI for these later operations):

```bash
terraform -chdir=infra/environments/dev init -input=false -lockfile=readonly
terraform -chdir=infra/environments/dev plan -out=application.tfplan
# Reviewed plan and explicit authorization required:
terraform -chdir=infra/environments/dev apply application.tfplan
application=$(terraform -chdir=infra/environments/dev output -json application)
api_base=$(printf '%s' "$application" | jq -r .api_base_url)
frontend_bucket=$(printf '%s' "$application" | jq -r .frontend_bucket_name)
distribution_id=$(printf '%s' "$application" | jq -r .cloudfront_distribution_id)
(cd web && npm ci && VITE_API_BASE_URL="$api_base" npm run build)
aws s3 sync web/dist/assets "s3://$frontend_bucket/assets" --exclude '*' --include '*.js' --content-type application/javascript --cache-control 'public,max-age=31536000,immutable' --region eu-central-1
aws s3 sync web/dist/assets "s3://$frontend_bucket/assets" --exclude '*' --include '*.css' --content-type text/css --cache-control 'public,max-age=31536000,immutable' --region eu-central-1
aws s3 cp web/dist/index.html "s3://$frontend_bucket/index.html" --content-type text/html --cache-control 'no-cache,max-age=0,must-revalidate' --region eu-central-1
aws cloudfront create-invalidation --distribution-id "$distribution_id" --paths /index.html /
```

The current build has only index.html and hashed JS/CSS assets. These commands
set explicit MIME types to avoid Windows guessing JavaScript as text/plain.
Future asset types need an upload step with their correct MIME type; un-hashed
public files need short-cache headers. The cache policy permits HTML
revalidation and immutable assets; retain older asset hashes until clients no
longer reference them. Avoid blanket error-page rewrites and wildcard cache
invalidations when updating only the entry HTML.

`api_base_url` is the complete HTTPS prefix, e.g.
`https://<api-id>.execute-api.eu-central-1.amazonaws.com`. The `$default` stage
adds no stage suffix. The client appends `/consumption`, `/anomalies`, `/forecast`
or `/chat` exactly once. If a future named stage is introduced, include it once
in the output and handle its ASGI path/root-path behavior with tests. Do not
append `/api` or an endpoint here. The URL must be set BEFORE `npm run build`;
changing a server environment variable cannot change uploaded JavaScript.

CORS is managed only by the HTTP API, for the exact CloudFront HTTPS origin,
`http://localhost:5173` and `http://127.0.0.1:5173`. Allowed methods are
GET/POST/OPTIONS; allowed headers are Accept/Content-Type; credentials are not
enabled. API Gateway supplies preflight responses. Local development still uses
the Vite proxy, so no FastAPI CORS middleware is added. See
[HTTP API CORS](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-cors.html)
and [S3 origin access control](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html).

## Costs and remaining verification

Billable categories include Lambda invocations/duration, HTTP API requests,
DynamoDB storage and read/write requests, S3 storage/requests, CloudFront
requests/data transfer/invalidations, CloudWatch ingestion/storage, and any
applicable SSM API/tier charges. The foundation state bucket also stores objects
and versions. Actual charges depend on usage, Region, account arrangements and
current pricing; no price or free-tier assumption is made here. Concurrency,
throttles and log retention reduce exposure but do not guarantee a fixed bill.
There are no idle SageMaker endpoints, NAT gateways or provisioned concurrency.

Local check results are recorded in [the handoff](person2-handoff.md). Linux
artifact execution/remote GitHub Actions, actual Lambda startup, account quotas
(including reserved concurrency), IAM propagation, CloudFront/OAC/S3 behavior,
CORS in a deployed browser and billing remain separate verification stages.
No plan, apply, seed write, AWS upload, invalidation, commit or push was run.
