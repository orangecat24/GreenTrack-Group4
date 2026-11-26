# P3 04 shared dev Terraform plan review

On 26 November 2026, a full refreshed plan from the current checkout previewed
**1 import, 21 additions, 8 in-place changes, and 0 destroys**. The saved plan
is `build/p304-assistant-fresh-20261126.tfplan`. STS independently confirmed
that `AWS_PROFILE=greentrack` selected account `886565871385` before Terraform
opened the Frankfurt dev backend. Terraform 1.17.0 used the repository lock for
AWS provider 6.73.0 and the backend's normal S3 locking.

The checkout received the four Terraform file changes from Person 2's
`9883c93` after an overlap check. The plan retained the earlier dev inputs,
including mock mode for the shared API and the existing SageMaker gold consumer
role. It enabled the standalone assistant and Athena, disabled the assistant's
Bedrock model, and scoped its source reads to
`gold/g4_greentrack_dev_gold.db/hourly_consumption/`. Terraform validation
passed. The saved plan's assistant ZIP hash matches the existing archive that
passed a fresh Linux x86_64 CPython 3.14 scripted Lambda smoke test. The plan
review ended before deployment. [P3 04 verification handoff](person3-p304-verification.md)

## Workgroup adoption

The import block previews adopting `g4-greentrack-dev-assistant`. The refreshed
workgroup and planned settings both show an enabled workgroup, automatic engine
selection with Athena engine 3 effective, CloudWatch metrics enabled, and a
scan cutoff of 1,099,511,627,776,000 bytes per query. The workgroup enforces
customer-managed results at
`s3://g4-greentrack-dev-datalake-886565871385/athena-results/assistant/` with
SSE-S3 encryption. Expected bucket owner and ACL are unset. The only in-place
change to the imported workgroup is the addition of the four default provider
tags `Environment`, `Group`, `ManagedBy`, and `Project`.

## Planned additions

All 21 additions belong to Challenge 4. The new `assistant` output provides
references for the team handoff.

| Count | Resources and purpose |
| --- | --- |
| 7 | Standalone Python 3.14 x86_64 Lambda, 14-day CloudWatch log group, Lambda IAM role, log and Athena inline policies, and two Lake Formation grants. The Lambda uses Athena and a scripted model. The grants give `DESCRIBE` on the gold database and `DESCRIBE` and `SELECT` on `hourly_consumption`. |
| 2 | Bedrock prompt-attack Guardrail and its published version. |
| 6 | Corpus S3 bucket and public access block, two guidance documents, and their two metadata objects. |
| 2 | S3 Vectors bucket and its 256-dimensional cosine index. |
| 4 | Bedrock Knowledge Base and S3 data source, plus a Bedrock service role and ingestion policy scoped to the Titan embedding model, corpus prefix, and vector index. |

The assistant role can run queries in its workgroup, write results under its
results prefix, read objects under the approved hourly prefix, and read the
named Glue database and table. Lake Formation provides the separate catalog
grants. The Bedrock model flag controls the Lambda's inference mode and model
policy. The module also provisions the Guardrail and Knowledge Base resources
listed above.

## Shared dev resources

| Resource | Plan review |
| --- | --- |
| API Gateway | No planned writes to the API, integration, routes, or stage. `GET /{proxy+}`, `GET /`, and `POST /chat` are preserved. Refresh observed empty scope and request-model representations on two routes and an auto-deploy stage deployment ID change. |
| SageMaker gold grants | No planned writes. The database keeps `ALL` and `DESCRIBE`. The table grant keeps `DESCRIBE` and `SELECT`. |
| Shared API Lambda | The absolute ZIP path changes. Local bytes match both the refreshed deployed code hash and the recorded source hash. The provider treats a path change as a code update and would re-upload the ZIP. [AWS provider Lambda update](https://github.com/hashicorp/terraform-provider-aws/blob/v6.73.0/internal/service/lambda/function.go#L964-L1004) |
| CloudFront | The origin gains an explicit S3 origin block with an empty legacy access identity. Response completion timeout changes from `0` to computed. The domain, origin access control, and cache behavior match. The provider normalizes these origin fields and would still call `UpdateDistribution`. [AWS provider CloudFront update](https://github.com/hashicorp/terraform-provider-aws/blob/v6.73.0/internal/service/cloudfront/distribution.go#L1169-L1207) · [Origin field handling](https://github.com/hashicorp/terraform-provider-aws/blob/v6.73.0/internal/service/cloudfront/distribution.go#L2222-L2290) |
| Data-lake objects | The source paths change for `scripts/bronze_job.py`, `scripts/silver_job.py`, `scripts/gold_job.py`, `scripts/quality_job.py`, and `scripts/silver_readings.dqdl`. The four scripts match the deployed ETags and recorded hashes. The ruleset in this checkout uses LF. The CRLF copy from the earlier review matches the deployed ETag and source hash, and the two copies match after line-ending normalization. The provider would upload all five objects, including the new ruleset bytes. [AWS provider S3 object update](https://github.com/hashicorp/terraform-provider-aws/blob/v6.73.0/internal/service/s3/object.go#L326-L330) · [S3 change detection](https://github.com/hashicorp/terraform-provider-aws/blob/v6.73.0/internal/service/s3/object.go#L593-L612) |

## Before deployment

- Coordinate with the shared dev owners on the API code upload, CloudFront
  update, five S3 uploads, the ruleset's line endings, and the workgroup tags.
  Agree on the exact ZIPs and source files for a refreshed plan from the
  intended deployment checkout.
- Confirm the scope and cost for the Guardrail, Knowledge Base, and S3 Vectors
  resources. The data source is configured for Titan embeddings. Ingestion is
  a separate operation.
- Confirm with Person 1 that the selected Iceberg table's metadata and data
  live under the approved prefix and that its Lake Formation registration
  matches the IAM approach. Confirm that the deploying identity can grant both
  Lake Formation permissions. After an authorized deployment, use the
  assistant Lambda role to verify the live chat query and the June 1 benchmark.
  The console benchmark in the earlier handoff came from the project user.
  [Live verification checklist](person3-p304-verification.md#evidence-pending-for-live-verification)

To reopen the saved preview locally from the repository root in PowerShell,
use the pinned CLI and the local provider cache created for this run.

```powershell
$env:TF_DATA_DIR = Join-Path $PWD 'build/p304-fresh-tfdata-20261126'
$plan = Join-Path $PWD 'build/p304-assistant-fresh-20261126.tfplan'
& .\build\p304-terraform-1.17.0\terraform.exe '-chdir=infra/environments/dev' show $plan
```
