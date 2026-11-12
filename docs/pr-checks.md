# Pull-request checks

The ordinary workflow, `.github/workflows/demo-checks.yml`, handles pull requests,
manual runs and reusable calls from the main pipeline. It uses `pull_request`,
not `pull_request_target`, and grants only
`contents: read`. Checkout does not persist credentials. There are no AWS secrets,
AWS authentication steps, OIDC permissions, deployments, plans, applies, or merges.
When a newer run starts for the same PR, its older run is cancelled; other PRs
have independent concurrency groups. Separate, explicitly activated AWS jobs
are described in [deployment-pipeline.md](deployment-pipeline.md); they do not
add credentials to these ordinary checks.

The teammate's existing AWS role/backend handoff is recorded in
[foundation-handoff.md](foundation-handoff.md). Its main/PR trust permits future
AWS-enabled jobs, but does not authenticate the current workflow automatically.
The suggested OIDC settings belong to the prepared AWS-enabled jobs, not these
ordinary checks. The foundation bucket is reported already applied; offline
bootstrap validation neither reapplies it nor reads its owner's local state.

## What happens in GitHub

The existing `mock-demo` job uses Ubuntu 24.04, **Python 3.14** and **Node 24**:

1. Create `.venv`, install the fully pinned runtime/test requirements, and run
   `pip check`. `requirements-dev.txt` includes the runtime pins.
2. Run pytest for `api/tests` and `scripts/tests`. DynamoDB responses are stubbed with fake test credentials; tests
   block application network connections and avoid real authentication files.
   Then build the Linux Python 3.14/x86_64 Lambda ZIP and run its packaged
   imports/API Gateway event tests offline on Linux. No artifact is sent to AWS.
3. Run **`npm ci`**, which installs `web/package-lock.json` and fails if it
   disagrees with `package.json`. CI does not regenerate the dependency lockfile.
4. Install Playwright's matching Chromium and Linux libraries.
5. Run frontend tests, lint, and the production build as separate named steps.
6. Run the real browser flow against fresh **local mock** API/web servers on
   18000/15173. Playwright starts and stops them. No AWS account is needed.
7. If a browser check fails, retain its report/trace artifact for seven days.

The Terraform job is independent, so application failures do not hide its result.
`infra/bootstrap` and `infra/environments/dev` are registered roots. The dev root
also validates `infra/modules/shared` and `infra/challenge1`. CI installs the
pinned Terraform 1.17.0 and uses each root's committed AWS provider lock.

## Run the application checks locally: Windows PowerShell

From the repository root, using the existing Python 3.14 environment:

```powershell
# Create only if absent: py -3.14 -m venv .venv
$env:APP_DATA_MODE = 'mock'
.\.venv\Scripts\python.exe -m pip install -r api\requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -c api\pytest.ini api\tests -q
# Also run deployment command/cache-isolation regressions:
.\.venv\Scripts\python.exe -m pytest -c api\pytest.ini scripts\tests -q
.\.venv\Scripts\python.exe scripts/build_lambda.py
# Linux-only artifact execution: .venv/bin/python scripts/check_lambda_zip.py
cd web
npm.cmd ci
npx.cmd playwright install chromium
npm.cmd run test:run
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e
```

No manually started servers are needed for the smoke flow. Normal development
servers on 8000/5173 can stay running. On Linux use `.venv/bin/python`, `npm`, and
`npx playwright install --with-deps chromium`; the workflow shows the exact Linux
commands. Dependency/browser downloads need internet access, but these checks
do not use AWS credentials or make real AWS service calls.

## Existing Terraform checks and adding future roots

The current roots and CLI/provider locks are already configured. When adding
another genuinely independent deployment root:

- Add its **deployable root directories** to `.github/terraform-roots.txt`, one
  repository-relative path per line, for example `infra/environments/dev`.
  Child modules with required provider aliases are validated through these roots,
  rather than incorrectly treating every module folder as a deployment.
- Add `.terraform-version` at the repository root containing an exact version
  such as `X.Y.Z`, chosen to match the configuration's `required_version`.
- Initialize provider selections locally with
  `terraform -chdir=infra/environments/dev init -backend=false -input=false` and
  commit that root's `.terraform.lock.hcl`. Pin remote module versions too;
  Terraform's provider lockfile does not lock remote modules.
- Install that same CLI version locally. CI installs the repository-pinned
  version through `hashicorp/setup-terraform`, without an account token.

The shared `scripts/check_terraform.py` script discovers tracked and unignored
Terraform source paths. If Terraform appears without registered roots/version/
provider locks, it fails with setup guidance rather than silently skipping checks.
It checks formatting in each source directory, including shared modules. It then
initializes and validates each registered root using:

```powershell
# Illustrative commands for a FRESH isolated TF_DATA_DIR. Prefer the shared
# helper below: a developer's existing .terraform cache may have a live backend.
terraform -chdir=infra/environments/dev fmt -check -diff
terraform -chdir=infra/environments/dev init -backend=false -input=false -lockfile=readonly
terraform -chdir=infra/environments/dev validate -no-color
```

To run all registered configurations with the same discovery/version/lock policy
as CI, from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\check_terraform.py
```

The helper uses a separate ignored `build/terraform-checks/...` TF_DATA_DIR per
root: `-backend=false` alone can reuse live cached backend metadata on a developer
machine. Isolation prevents that reuse and preserves the existing .terraform
directory. Provider initialization may still
download provider/module packages, and `-lockfile=readonly` prevents CI from
silently changing provider selections. Use publicly downloadable dependencies
for ordinary credential-free PR checks.

**Validate is not an AWS plan.** It checks Terraform syntax, references and types
using the installed providers. It does not prove that AWS permissions, account
quotas, data sources, target Region, or proposed resource changes are correct.
A plan requires its own authorized environment and account context. This workflow
never runs `plan` or `apply`. The separate optional AWS PR workflow explicitly
reports pending when read-only planning access is not configured; its result is
independent of this validation. See [the pipeline guide](deployment-pipeline.md)
and the [Terraform validate documentation](https://developer.hashicorp.com/terraform/cli/commands/validate).

## Find a failed step's logs

1. Open the PR on GitHub, select **Checks**, then the failed `mock-demo` or
   **Terraform configuration checks** job. Alternatively use **Actions → Student
   demo checks → the relevant run**.
2. Expand the first red step. Its log contains the failing command and error;
   later steps marked skipped generally did not cause the failure.
3. For a browser failure, open that run's **Summary → Artifacts** and download
   `mock-browser-failure`. The archive contains the HTML report and, when produced,
   the screenshot/trace. A setup failure before browser startup may have no artifact.
4. Reproduce that step locally using the commands above. For local browser output,
   run `npx.cmd playwright show-report` from `web/`.

Cancelled runs are expected when a newer commit supersedes them. Review the newest
run on the PR. If checks are mandatory for merging, a repository maintainer must
configure branch protection separately; this task does not change repository settings.

## Verification limits

Local application and Terraform results are recorded in the task handoff.
See [application-infrastructure.md](application-infrastructure.md) for Lambda
packaging, resource/configuration details and later-only deployment commands.
GitHub-hosted execution, action downloads, artifact upload,
concurrency cancellation and Linux-only browser-library installation cannot be
verified by local Windows tests. The actual Linux ZIP import/event tests also
require Linux; building/inspecting that ZIP on Windows does not execute it.
Terraform fmt/backend-disabled init/validate passed locally for both roots;
these do not validate live permissions or perform a plan. No deployment or
remote workflow is triggered by local checks.
