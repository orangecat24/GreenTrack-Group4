# Person 2 deployment pipeline: prepared, activation is off by default

This prepares GitHub Actions code, not a completed deployment. No plan/apply,
asset upload, seeding, invalidation, workflow dispatch or repository-setting
change was performed from the implementation session. The shared IAM role,
trust, Terraform resources and application contract are unchanged.

## Which workflow does what?

| File | Trigger and purpose |
| --- | --- |
| `.github/workflows/demo-checks.yml` | Ordinary PR/manual checks, also reusable through `workflow_call`. No AWS credentials or OIDC permissions. Tests Python/API/deployment helpers, Linux ZIP, frontend, lint/build and local browser flow; validates Terraform offline. |
| `.github/workflows/deploy-main.yml` | Push to `main`, including a PR merge. Does nothing in AWS unless `DEPLOY_ENABLED` is exactly `true`. Reuses ordinary checks and receives their tested ZIP in the same run; deploys only after both check jobs succeed. |
| `.github/workflows/aws-pr-plan.yml` | Optional speculative PR plan. Requires explicit opt-in, an approved separate read-only role, a same-repository PR and an `aws-plan` label. Otherwise its summary says **AWS plan pending/not configured**. Forks never qualify. No apply or upload. |

`scripts/deployment.py` owns small CI steps: account check, fixed dev-root
init/plan/apply, validation of selected public outputs and asset publication.
It rejects local execution and rejects apply/publication from PRs or disabled
main runs. These are accident guards; IAM remains the actual AWS security
boundary. Its tests stub every command and contact neither Terraform nor AWS.

The deployment workflow's concurrency group is
`greentrack-886565871385-dev-state`, with cancellation **false at workflow level**.
A newer push does not interrupt a running apply. GitHub may replace older pending
runs, so this is not a FIFO promise. Any future workflow writing this same dev
state must use that group too. Terraform also uses the existing S3 lock, with a
five-minute acquisition timeout. Ordinary and optional PR checks use different
groups and can cancel outdated runs without cancelling an apply.

## Readiness: evidence, not assumptions (November 11, 2026)

Read-only commands using local SSO profile `greentrack` verified:

- Account `886565871385`, DataMax SSO `DeveloperAdminAccess` session, saved client
  Region `eu-central-1`.
- HeadBucket succeeds for `g4-greentrack-tfstate-886565871385`, in eu-central-1.
- HeadObject succeeds for `environments/dev/terraform.tfstate` (11,766 bytes,
  last modified November 8 at 21:53:07 UTC). Only metadata was queried: state
  contents/resource addresses were not downloaded or printed.
- IAM GetRole confirms
  `arn:aws:iam::886565871385:role/g4-greentrack-github-deploy` and its existing
  repo main/PR subjects, audience `sts.amazonaws.com` and account GitHub provider.
- ListAttachedRolePolicies confirms PowerUserAccess. GetRolePolicy confirms the
  `g4-*` IAM statement and OIDC read permissions from the handoff.

Those checks do not prove OIDC works from a GitHub runner, that state tracks the
existing role correctly, that all deployment writes are permitted, or that quotas
and account guardrails allow deployment. No write probes or secrets were used.
The GitHub role remains broad by the team's decision; application Lambda stays
logs-only in mock mode. Local SSO is not used in GitHub and does not establish
GitHub OIDC readiness. Bucket encryption/versioning were not re-verified here.

## Exact configuration and first activation

Use **repository Actions variables**, not secrets or environment variables
containing permanent credentials. No AWS access keys are required.

| Repository variable | Value | Effect |
| --- | --- | --- |
| `DEPLOY_ENABLED` | Unset or `false` initially; exactly `true` enables main deployment | The only required activation variable. Do not enable until the setup below is reviewed. |
| `AWS_PR_PLAN_ENABLED` | Unset/`false` by default; exactly `true` opts in | Optional PR plans only; not required for main deployment. |
| `AWS_PR_PLAN_ROLE_ARN` | ARN of an owner-approved, account-side read-only `g4-...` planning role in account `886565871385` | Must differ from the existing PowerUser deployment role. Do not set until IAM permissions and PR trust are reviewed. |

The known account, Region and main deployment ARN are intentionally fixed in
the workflow/helper to match the existing provider guard and handoff. Terraform
version is read from `.terraform-version` (**1.17.0**), not independently pinned
in YAML. Runtime targets remain Python 3.14 and Node 24. Application data mode
is explicitly mock in the planned deployment; no seeding step exists.

Repository maintainer setup, **not performed by this task**:

1. Review and merge the pipeline while `DEPLOY_ENABLED` is absent/false. The
   disabled main run reports that fact without authenticating to AWS.
2. Coordinate with the foundation owner: bootstrap already exists, and its local
   state stays with that owner. Preserve `module.shared` addresses in the existing
   dev state. Do not run bootstrap apply, import blindly or create a new backend.
3. Confirm that the existing GitHub role's permissions and the account's quotas
   permit these resources. The role is already present; no IAM change is required
   merely to keep local development or pipeline preparation going.
4. Under Settings -> Rules/Branches, configure main review/check protection if
   required by the team. A workflow triggered by a push cannot itself prove that
   a PR was reviewed; direct main pushes would also deploy when enabled.
5. Under Settings -> Secrets and variables -> Actions -> Variables, create
   `DEPLOY_ENABLED=true` only when the team is ready for the **next** main push
   to create/update billable resources. Do not add static AWS credentials.
6. The next reviewed merge/push to main runs the pipeline below. No workflow
   dispatch or apply from chat is needed. Read its Actions summary and check logs.

There is deliberately **no GitHub Environment** on an authenticated job: the
current trust expects `repo:orangecat24/GreenTrack-Group4:ref:refs/heads/main`.
Adding `environment: dev` changes the OIDC subject. If protected-environment
approval is desired later, the account owner must first coordinate matching
environment trust; this implementation never widens trust to make it work.
The actual GitHub subject format must also match; local SSO cannot test it.

## The first enabled main run

1. Run all ordinary checks on that commit, including a real Linux import/event
   check of the Linux CPython 3.14 x86_64 ZIP. Retain **only that tested ZIP** as
   a one-day Actions artifact, named `greentrack-lambda-<commit SHA>`.
2. Download the same-run artifact; do not rebuild the Lambda between plan and
   apply. Use OIDC temporary credentials for the existing main deployment role.
   Only that deploy job receives `id-token: write`. The action and helper both
   verify account `886565871385` before proceeding.
3. Initialize only `infra/environments/dev`, using the existing backend/key,
   committed provider lock and `-lockfile=readonly`. Do not automatically apply
   bootstrap or change shared policies. The root includes the existing shared
   module, so its state continuity still matters.
4. Save a main plan under ignored `build/application.tfplan` with mock mode and
   S3 locking, then apply **that exact plan file in the same runner**. No `-target`
   or unplanned `apply -auto-approve` shortcut is used.
5. Read only the `application` Terraform output; whitelist its four public
   destinations before exporting them. Whole-state/all-output JSON is not logged.
6. Run `npm ci` and build Vite with the validated API Gateway URL as
   `VITE_API_BASE_URL`. The `$default` stage means no `/api` or `/stage` suffix.
7. Upload content-hashed assets first with correct MIME types and one-year
   immutable cache headers. Upload HTML last with revalidation headers. Retain
   old asset hashes; no `s3 sync --delete`. Unknown asset types/unhashed assets
   fail for review rather than receive unsafe MIME/cache defaults.
8. Compare the existing small HTML object's ETag; only changed/new HTML triggers
   its upload and invalidations for `/` and `/index.html`. Wait for that
   invalidation to finish. Resource creation/configuration stays in Terraform.
9. Run `npm run test:deployed`: real headless Chromium exercises all four tabs,
   date changes, mock chat and weekly summary, using the same journey as the local
   smoke. Also check health, explicit POST preflight headers and that the browser
   actually calls the output API origin. It never substitutes fixture responses.
   There are at most three attempts, with per-test and assertion timeouts.

The deploy job has a 60-minute timeout and requests a one-hour OIDC role session.
Long/partial runs can fail; they do not imply transactional rollback. Terraform
resource operations and CLI waiters have their own finite timeouts.

## Optional PR planning

This is independent of main deployment. Without configured planning access, leave
both optional variables unset and read the explicit pending summary. **Validate
is not an AWS plan.** No successful-plan claim is made for a skipped job.

The account owner must supply a separate read-only planning role: suitable PR
OIDC trust, GetObject/ListBucket for the named state, and the provider read/list
operations needed to refresh this dev root. Scope SSM reads to the application's
non-secret parameter prefix and scope other reads where AWS supports it. State
may contain sensitive values, so only approved PR authors should get this access.
The workflow adds a write-denying session policy as defence in depth; it is not
a substitute for account-side read-only enforcement because a PR can edit YAML.
Do not use the PowerUser role under a name claiming to be read-only.

After owner review, set the optional variables and add `aws-plan` to a trusted
same-repository PR. Label changes/synchronization trigger reevaluation. Forks do
not authenticate and `pull_request_target` is never used. PR planning builds the
ZIP only to obtain the proposed hash; it does not duplicate the ordinary test
pipeline or publish that artifact. Plan uses `-lock=false` to need no state-lock
writes. It is a speculative snapshot, may race a main update, is never applied
and is never promoted to the main deployment job. AWS read/API-request charges
may still apply. No binary plan or state is uploaded or posted as a PR comment.

## Local checks and useful commands

Safe PowerShell checks from the repository root (no CI deployment operations):

```powershell
.\.venv\Scripts\python.exe -m pip install -r api/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -c api/pytest.ini api/tests scripts/tests -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/build_lambda.py
# If using the previously downloaded portable Terraform (otherwise use 1.17.0 on PATH):
$env:PATH = (Join-Path (Get-Location) '.qa\terraform-1.17.0') + [IO.Path]::PathSeparator + $env:PATH
$env:CHECKPOINT_DISABLE = '1'
.\.venv\Scripts\python.exe scripts/check_terraform.py
Push-Location web
npm.cmd ci
npm.cmd run test:run
npm.cmd run lint
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd run test:e2e
Pop-Location
```

Linux uses `.venv/bin/python` and `npm`/`npx`; also run
`.venv/bin/python scripts/check_lambda_zip.py` and install Chromium with
`npx playwright install --with-deps chromium`. The Linux artifact execution is
not possible with Windows' native Python.

`scripts/check_terraform.py` now gives each registered root its own ignored
`build/terraform-checks/...` TF_DATA_DIR. This fixes an observed defect: an
existing `.terraform` cache from real backend initialization caused a state
metadata request despite `init -backend=false`. The isolated checks preserve
the developer's real backend cache/state and prevent that reuse. A regression
test verifies init and validate share the isolated directory.

The new deployed browser test can be collected without contacting any URL:

```powershell
Push-Location web
$env:DEPLOYED_WEBSITE_URL = 'https://example.cloudfront.net'
$env:DEPLOYED_API_BASE_URL = 'https://example.execute-api.eu-central-1.amazonaws.com'
npm.cmd run test:deployed -- --list
Remove-Item Env:\DEPLOYED_WEBSITE_URL, Env:\DEPLOYED_API_BASE_URL
Pop-Location
```

Those example domains are only for **collection**, not execution or proof of a
deployment. Executing `test:deployed` sends real requests: use actual authorized
deployment outputs. No API/base URL can silently fall back to localhost here.
An ignored local actionlint 1.7.12 executable is available under `.qa` on this
machine; `actionlint` on another developer's PATH can check the YAML as well.

## Failures, blockers and recovery

Open Actions -> the relevant workflow -> its run -> the first failed step.
Main steps are separated into authentication, initialization, plan, apply,
outputs, build, publication and smoke, so the failing phase is visible. Its
summary reports the result and public URLs when available. Plans, state, raw
Terraform output, AWS command bodies and credentials are deliberately not
published as logs/artifacts. Fixed error categories such as AccessDenied are
shown; an authorized maintainer may reproduce detailed diagnostics locally
without pasting sensitive logs into chat or a public issue. The ordinary local
mock browser failure report remains available; deployed traces/screenshots
are disabled to avoid storing cloud responses or temporary URLs unintentionally.

| Blocker or failure | Responsible owner and smallest next action |
| --- | --- |
| Deployment remains disabled | Repo maintainer: complete setup, then set `DEPLOY_ENABLED=true`; next reviewed main push activates it. This task did not change the setting. |
| GitHub OIDC not yet exercised | Repo/account owner: inspect the first enabled authentication step; compare issuer/audience/actual subject to the existing trust if it fails. Do not print JWTs or broaden trust to arbitrary refs. |
| Optional AWS PR plan pending | Account owner: provide a truly read-only planning identity if wanted; maintainer configures variables and label. Main does not depend on it. |
| Terraform wants to create an existing shared role | Foundation owner: reconcile ownership in the existing dev state through an explicitly reviewed state/import task. Do not rename/recreate it to force an apply. State contents were not inspected here. |
| AccessDenied/quota/role propagation | Account owner: identify the exact required operation/quota from authorized diagnostics, then make the smallest appropriate permission/quota change outside this task. Broad role policy inspection does not prove every effective permission. |
| Apply stopped partway | Deployment owner: inspect the failed phase and existing state under authorized access, then obtain a fresh plan in a new main run. Do not blindly destroy or reuse a stale saved plan. Never cancel an apply just because a newer commit arrived. |
| Assets/index upload failed | Deployment owner: assets were uploaded first and old hashes retained; correct the upload error and rerun the deployment. Some files may already be present. Check MIME/cache headers and the actual index/API prefix. |
| Smoke failed after apply/publication | Deployment owner: infrastructure/assets may already be live. Inspect gateway/Lambda logs and CDN/API URLs, fix the observed defect, deploy a reviewed correction; do not assume automatic rollback. |

To stop **future** automatic runs, a maintainer can set `DEPLOY_ENABLED=false`.
That neither stops an active apply nor deletes resources. To restore older
application behavior, prefer a reviewed revert followed by a fresh plan/build
and deploy. Do not restore old Terraform state as an application rollback.
State-lock recovery is an owner action only after confirming no writer remains.

Billable categories remain Lambda requests/duration, HTTP API requests, S3
storage/requests/state versions, DynamoDB storage/requests, CloudFront requests,
transfer/invalidations, CloudWatch logs and applicable SSM usage. Retaining old
assets adds storage. GitHub runner minutes/artifact storage may also count
against the repository's plan. No free-tier entitlement or price is assumed.

Official references: [OIDC credentials action](https://github.com/aws-actions/configure-aws-credentials),
[reusable workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows),
[concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency),
[Terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan).

Final local check results are recorded in [person2-handoff.md](person2-handoff.md).
GitHub-hosted OIDC/Actions/artifact transfer, Linux ZIP execution, real AWS plans,
write permissions, deployment and deployed HTTPS/CORS checks remain unexecuted.
