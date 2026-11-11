# Existing AWS foundation: teammate handoff

Recorded November 11, 2026 from the foundation PR description supplied by Vangjel.
The foundation commit is `99cc0aa`, "Added Terraform foundation: state bucket,
remote backend and GitHub deploy role". This document preserves that handoff
alongside the code; future PR descriptions should link to repository Markdown.

## Reported status and exact identifiers

The teammate explicitly reports that **bootstrap was already applied once from
his laptop**. Do not treat the state bucket as a new resource to create from a
fresh checkout. The PR also hands over the GitHub deployment role and dev backend
settings below. No AWS API, credentials or remote state were inspected to verify
these statements during this documentation update.

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
Role existence/permissions and state contents remain unverified locally.

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

## GitHub Actions handoff: recorded, not enabled

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
uploads in it. A future deployment-workflow task can use the existing role;
this update does not enable one or require hardening before local work continues.

See [application-infrastructure.md](application-infrastructure.md) for the
application build/deployment order and [pr-checks.md](pr-checks.md) for safe local
checks. Markdown handoffs and the chat completion report remain part of the
working process, even when a PR description also summarizes the work.
