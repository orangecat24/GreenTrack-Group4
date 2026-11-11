# Existing AWS foundation: teammate handoff

Recorded November 11, 2026 from the foundation PR description supplied by Vangjel.
The foundation commit is `99cc0aa`, "Added Terraform foundation: state bucket,
remote backend and GitHub deploy role". This document preserves that handoff
alongside the code; future PR descriptions should link to repository Markdown.

## Reported status and exact identifiers

The teammate explicitly reports that **bootstrap was already applied once from
his laptop**. Do not treat the state bucket as a new resource to create from a
fresh checkout. The PR also hands over the GitHub deployment role and dev backend
settings below. The initial handoff capture did not verify AWS resources.
The later read-only CLI verification is recorded at the end of this document;
credentials and remote state contents were not inspected.

| Item | Handoff value |
| --- | --- |
| AWS account | `886565871385` |
| Region | `eu-central-1` |
| Terraform CLI | `1.17.0` (repository `.terraform-version`) |
| State bucket | `g4-greentrack-tfstate-886565871385` |
| Dev state key | `environments/dev/terraform.tfstate` |
| Dev backend | S3, encrypted, native S3 locking with `use_lockfile=true` |
| GitHub role name | `g4-greentrack-github-deploy` |
| GitHub role ARN | `arn:aws:iam::886565871385:role/g4-greentrack-github-deploy` |
| Existing OIDC provider | `https://token.actions.githubusercontent.com` (shared account resource; read, never recreated) |
| Trusted main subject | `repo:orangecat24/GreenTrack-Group4:ref:refs/heads/main` |
| Trusted PR subject | `repo:orangecat24/GreenTrack-Group4:pull_request` |
| OIDC audience | `sts.amazonaws.com` |

These names and the role ARN are configuration identifiers, not access keys.
The handoff does not prove that the dev state object currently exists or contains
the shared role, nor that any Person 2 application resources have been applied.
Later checks verified the GitHub role's existence/trust/policy configuration and
the state object's existence, as recorded below and in the pipeline guide.
State contents and effective deployment write permissions remain unverified.

## Ownership: reuse the existing foundation

- `infra/bootstrap` defines the versioned, AES256-encrypted state bucket with
  public access blocked and `prevent_destroy`. Its own state remains local to
  the bootstrap owner, as described by the original configuration. Preserve it
  with the owner; do not commit, request in chat, or copy state into a fresh root.
- `infra/environments/dev` is the existing root for team infrastructure. It
  already selects the bucket/key above, eu-central-1 and the account guard.
- `infra/modules/shared` is called as `module.shared` by dev. Keep those resource
  addresses so an existing role tracked in dev state is updated in place.
- `infra/challenge1` is the application child module called as
  `module.challenge1` by the same dev root. It has no competing backend or
  GitHub deployment role. Its Lambda execution role is a different identity.
- `.github/terraform-roots.txt` keeps only bootstrap and dev as deployable roots;
  both provider locks and the CLI pin remain in place. Checking bootstrap with
  backend-disabled init/validate does not reapply it or inspect its owner's state.

For a later authorized deployment, use the existing **dev** backend. Coordinate
with the owner about state continuity first. If a future reviewed plan proposes
creating a role known to exist, reconcile its Terraform state ownership rather
than renaming resources, importing blindly or creating a duplicate foundation.
A role ARN alone does not tell Terraform which state manages that role.
No import, migration, plan or apply was performed for this update.

## Current permission decision

Keep the teammate's shared role configuration unchanged for this increment:

- AWS-managed `PowerUserAccess`.
- Custom IAM management permissions on `g4-*` roles/policies, plus the existing
  read permissions for the account's GitHub OIDC provider.
- Trust for this repository's main and pull-request subjects.

**Work can continue with this setup. Hardening is recommended, not a technical
prerequisite imposed by the application or this repository's checks.** It is a
security tradeoff, not a guarantee that the role is isolated to Group 4:
PowerUserAccess permits broad non-IAM service actions across resources; the
`g4-*` restriction applies to the custom IAM statement. That statement also
matches the deployment role itself, allowing changes to its own permissions.
Other account guardrails, if any, were not inspected.

Trusting PR subjects means a suitably configured PR job could assume this role
before its application code is merged. Trust alone does not authenticate a job
or run any AWS action. Future workflow design should control which PR code can
receive these permissions and what it runs. Narrower deployment permissions and
trusted deployment triggers remain recommended improvements; no permission or
trust changes are made here.

The **application execution role** remains least-privilege: logs only in mock
mode; Query on the three application tables when DynamoDB mode is selected.
Neither the browser nor the application receives the PowerUser deployment role.
Mock mode still requires no AWS credentials and makes no application AWS calls.

References: [AWS PowerUserAccess policy](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/PowerUserAccess.html),
[GitHub OIDC configuration](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).

## GitHub Actions handoff: prepared, not enabled

The teammate's guidance for a future AWS-enabled job is:

- Grant that job `contents: read` and `id-token: write`.
- Use `aws-actions/configure-aws-credentials` with `role-to-assume` set to the
  exact role ARN above and `aws-region: eu-central-1`.
- Authenticate with short-lived OIDC credentials, not static AWS access keys.
- Match the actual GitHub OIDC subject to the role trust when implementing it.

`id-token: write` permits requesting an OIDC token; assuming the trusted role is
what grants AWS access. This handoff does not mean adding AWS authentication to
every PR check or automatically running apply on PRs.

The existing `.github/workflows/demo-checks.yml` remains credential-free:
application tests, artifact checks, fmt, backend-disabled init and validate.
There are no AWS authentication steps, OIDC permissions, AWS plans, applies or
uploads in it. The separate main deployment pipeline now uses the existing role
behind explicit activation; optional PR planning requires another read-only role.
See [deployment-pipeline.md](deployment-pipeline.md). Neither activation nor
deployment was performed from chat, and shared IAM configuration is unchanged.

See [application-infrastructure.md](application-infrastructure.md) for the
application build/deployment order and [pr-checks.md](pr-checks.md) for safe local
checks. Markdown handoffs and the chat completion report remain part of the
working process, even when a PR description also summarizes the work.

## Local SSO and bucket verification (November 11, 2026)

With Vangjel's authorization to check his CLI setup, these read-only checks
were run using profile `greentrack`:

- AWS CLI is `2.36.29`; the saved client Region is `eu-central-1`.
- STS GetCallerIdentity returned account `886565871385` and an assumed
  `AWSReservedSSO_DeveloperAdminAccess_...` role. This is the local DataMax SSO
  identity, not the GitHub OIDC deployment role. No session tokens were displayed.
- S3 HeadBucket succeeded for `g4-greentrack-tfstate-886565871385`, with expected
  owner `886565871385`, and returned `BucketRegion=eu-central-1`.

This confirms a working local SSO session and access for that bucket check.
HeadBucket requires ListBucket on this general-purpose bucket; it does not prove
GetObject/PutObject rights on state, lock-file writes/deletes, or application
deployment permissions. No bucket objects were listed/downloaded and the dev
state's existence/contents were not checked. Bucket encryption/versioning,
the GitHub role's live policies and application deployment remain unverified.

The local Terraform on PATH is `1.17.2`, while `.terraform-version` and the check
helper require exactly `1.17.0`. The existing ignored portable copy at
`.qa/terraform-1.17.0/terraform.exe` can be selected for this terminal only; no
uninstall, global PATH change or repository pin change is necessary.

Future local Terraform commands should use `AWS_PROFILE=greentrack` and
`AWS_REGION=eu-central-1`, with the existing **dev** backend. No attempt to assume
the GitHub-only role from the laptop is needed. Backend initialization, plans,
applies and resource writes were not run during this verification. No code,
workflow, permissions or AWS resources changed.

## Deployment-pipeline readiness update (November 11, 2026)

Additional authorized read-only checks confirm the dev state object exists
(HeadObject metadata only), the named GitHub role exists, its audience/main/PR
trust matches the handoff, PowerUserAccess is attached, and its custom g4-* IAM
policy matches the repository. No state contents were read and no permissions
were modified. The original bootstrap applied-on-laptop statement remains
teammate-reported; live bucket encryption/versioning were not rechecked.

The new [pipeline guide](deployment-pipeline.md) records exact evidence, activation
variables, optional planning-role requirements, failure recovery and verification
limits. GitHub OIDC, effective write access and deployment remain untested.
