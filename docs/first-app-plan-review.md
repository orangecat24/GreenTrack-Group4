# First application deployment plan review (November 25, 2026)

## Corrected plan: acceptable for the reviewed manual mock deployment

The user authorized a scoped configuration correction and a new full-root plan.
The correction explicitly preserves ALL/DESCRIBE for the existing SageMaker
database consumer only. Other consumers still default to DESCRIBE. No grant,
admin, IAM policy or state was manually edited in AWS, and no apply was run.

- **Use:** `build/first-app-preserved-grants.tfplan`.
- **Do not use:** the original `build/first-app.tfplan` reviewed below.
- Terraform 1.17.0; new plan timestamp `2026-11-25T21:19:30Z`.
- SHA256: `90378945114720104d4bad9a1ca4b8b1f48728e5a7910622fef5514711120f7c`.
- **27 additions, 5 updates, 0 destructions, 0 replacements.**

The new plan was generated using greentrack SSO after checking account
886565871385. Terraform may acquire/release the backend lock for this operation;
no resource deployment or permission change was applied. Raw plan/state JSON and
credentials were not printed. The original rejected binary remains unchanged.

Review assertions passed:

- All 27 additions belong to module.challenge1 and are the expected mock app.
- The only modifications outside challenge1 are the five S3 script/ruleset
  objects below. Each existing ETag and before/after source_hash equals its local
  content MD5: the uploads preserve identical contents and stay under scripts/.
- Every Lake Formation grant is no-op, including SageMaker's ALL/DESCRIBE on
  the gold database and its SELECT/DESCRIBE on gold tables.
- Lake Formation admins are unchanged for this SSO plan.
- Existing data-lake resources, Glue jobs, shared/SageMaker roles and model
  registries have no planned modifications.
- Mock mode is selected, all plan checks pass, and the Lambda ZIP SHA256 matches
  the saved plan's source_code_hash.

Terraform formatting and validation passed after the change. A complete new AWS
plan provides the integration check here; application code/tests are unchanged.
The map validation rejects overrides for inactive consumer roles or invalid
database permissions. This deliberately does not hide permission drift globally.

**Recommendation:** proceeding with this exact new manual plan is reasonable
under the requested preservation goal. It is not a guarantee of AWS provisioning
success or a cost-free operation. If code/artifacts/state change, or the binary
hash differs, generate and review another plan. Approval does not extend to the
old file or to GitHub auto-apply's different Lake Formation admin identity.
The run guide now selects/checks this new file before the apply command.

## Original plan: rejected (historical review)

**Decision: do not apply this saved plan as-is.** It includes a permissions
reduction on an existing SageMaker role in addition to the new application.
No apply, new plan, state edit, permission change or deployment was performed
during this review. The review did not require the teammate's laptop.

## Exact plan reviewed

- Local ignored file: `build/first-app.tfplan`.
- Terraform version: 1.17.0.
- Plan timestamp: `2026-11-25T19:34:56Z`.
- Plan SHA256: `d094875a0c0dab354bd1830bde5f56daa202ec73d56b3970c3cdfa005dc54bc7`.
- The plan reports applyable/complete=true and errored=false. These indicate a
  technically valid plan, not a safety approval.
- Mode: mock. Gold consumer list retains the existing SageMaker execution role.

The plan was decoded locally into memory. Only change metadata, relevant
permissions/admin ARNs and content hashes were examined/reported; raw plan/state
JSON and credential values were not printed or saved as a report artifact.

## Actual changes

| Change | Assessment |
| --- | --- |
| 27 new application resources | Expected: HTTP API, Lambda/execution role, three empty on-demand tables, private frontend bucket/CloudFront, logs and non-secret configuration. |
| One existing Lake Formation grant replaced | **Hold:** removes ALL from the SageMaker role's gold database grant, retaining only DESCRIBE. Unrelated to creating the mock application. |
| Five existing S3 script/ruleset objects updated | Source paths change between checkouts; before/after source_hash and existing ETag match each local file's MD5. Content is identical as represented in this plan. |

Terraform's usual count would be **28 additions, 5 changes, 1 destruction**:
the replacement contributes both one addition and one destruction. That
destruction refers to an access-grant resource, **not a database, table or bucket**.
No raw/silver/gold data deletion, Glue job replacement or training/endpoint
creation is proposed in this saved plan.

## Permission change that prevents approval

Resource:

```text
module.challenge2.aws_lakeformation_permissions.consumer_gold_database["arn:aws:iam::886565871385:role/g4-greentrack-dev-sagemaker-execution"]
```

Database: `g4_greentrack_dev_gold`.

```text
Before: ALL, DESCRIBE
After:  DESCRIBE
Actions: delete existing grant, create replacement grant
```

The separate gold-table SELECT/DESCRIBE grant remains unchanged, so this is not
evidence that gold data would be erased or all read access would disappear.
However, ALL includes broader database capabilities; removing it is an actual
authorization change. Its impact on future ML workflows has not been tested.
Under the requested goal of deploying the app without disturbing existing work,
this unrelated reduction should not be bundled into the first deployment.
See [the AWS permission reference](https://docs.aws.amazon.com/lake-formation/latest/dg/lf-permissions-reference.html).

## Other checks

- Lake Formation administrators: **unchanged** in this SSO-generated plan.
  The earlier warning about a GitHub-generated admin list remains applicable to
  future automation; it is not a proposed change in this specific saved plan.
- Glue pipeline permissions and the gold-table consumer grant: unchanged.
- No planned updates to the shared GitHub role or existing SageMaker role.
  Refresh/drift entries are distinct from proposed remote resource actions.
- Lambda: Python 3.14 x86_64, mock mode, 512 MB, 15 seconds, concurrency 2.
- Current local Lambda ZIP hash matches the saved plan's source_code_hash.
- New Lambda trust is for Lambda; frontend public-access blocking is enabled.
- The five identical-content uploads are under `scripts/`, not raw/silver/gold.
  They may create new S3 object versions; they are not data-file uploads.

## Next safe step

Make a narrow, explicit Terraform configuration correction preserving the
SageMaker role's current database grant for this app deployment, without
extending those permissions to other consumers. Then generate a **new full-root
plan** and review it again. Do not use this old binary plan after a code change.

Do not bypass the finding with `-target`, manual state edits, blanket ignored
permission drift or an unreviewed apply. A later deliberate permission reduction
can be reviewed separately when model requirements are known.

This is a plan review, not a guarantee of successful provisioning: account
quotas, effective write permissions, IAM propagation and intervening live
changes can still affect execution. No live AWS permission query was needed
for the conclusion; the before/after values above come from the saved plan.
