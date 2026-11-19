# Person 1 resource inventory (P1 12)

Everything Person 1 owns in the DataMax account, how to inspect it and how
to remove it. Shared resources (state bucket, deploy role, OIDC provider) are
intentionally retained; one-off experiments are the ones to clean up.

## Retained for the lifetime of the project

| Resource | Why kept | Remove by |
| --- | --- | --- |
| `g4-greentrack-tfstate-886565871385` (S3) | Terraform remote state | Only after the project is archived; `prevent_destroy = true` |
| OIDC provider in account | Shared across groups | Never delete; it is managed outside this repository |
| `g4-greentrack-github-deploy` | GitHub Actions identity | `terraform destroy -target=module.shared` when the repository is archived |
| `g4-greentrack-dev-datalake-886565871385` | Raw data of record | `prevent_destroy = true`; delete source files only through a reviewed procedure |

## Standing data and pipeline resources

Managed through `module.challenge2`. Full list by name prefix
(`g4-greentrack-dev-`):

- Glue databases: `g4_greentrack_dev_bronze`, `_silver`, `_gold`
- Glue tables: `g4_greentrack_dev_bronze.raw_readings` (Iceberg silver/gold
  tables are owned by the engine; see note below)
- Glue jobs: `bronze`, `silver`, `quality`, `gold`
- Glue workflow + triggers: `pipeline`, `start-on-upload`,
  `silver-after-bronze`, `quality-after-silver`, `gold-after-quality`
- IAM roles: `glue-pipeline`, `eventbridge-pipeline`
- EventBridge rule: `raw-upload`
- Lake Formation grants (when `gold_consumer_role_arns` is set)

Remove with `terraform destroy -target=module.challenge2` from
`infra/environments/dev`. S3 objects in the data lake bucket are kept because
the bucket has `prevent_destroy = true`.

### Iceberg tables

`g4_greentrack_dev_silver.readings`, `g4_greentrack_dev_gold.*` are created
by the Glue jobs, not Terraform. They are reconstructable by re-running the
pipeline against the same raw files, so leaving them after `destroy` is safe;
to remove them manually:

```
aws glue delete-table --database-name g4_greentrack_dev_silver --name readings
aws glue delete-table --database-name g4_greentrack_dev_gold --name hourly_consumption
aws glue delete-table --database-name g4_greentrack_dev_gold --name daily_consumption
aws glue delete-table --database-name g4_greentrack_dev_gold --name daily_peak
aws s3 rm s3://g4-greentrack-dev-datalake-886565871385/silver/ --recursive
aws s3 rm s3://g4-greentrack-dev-datalake-886565871385/gold/ --recursive
```

## SageMaker skeleton

Managed through `module.challenge3`:

- `g4-greentrack-dev-sagemaker-execution` IAM role
- Model Package Groups `forecast`, `anomaly`

Remove with `terraform destroy -target=module.challenge3`. Later increments
will add pipeline and endpoint resources; those must be destroyed **before**
the group is deleted or the destroy will leave orphaned model packages.

## Expected one-off resources (idle after demo)

These do not exist yet; this list is the cleanup target once P1 10 lands.

| Resource | Owner | Destroy command |
| --- | --- | --- |
| Forecast real-time endpoint | Person 1 (P1 10) | `terraform destroy -target=aws_sagemaker_endpoint.forecast` |
| Anomaly real-time endpoint | Person 1 (P1 10) | `terraform destroy -target=aws_sagemaker_endpoint.anomaly` |
| Approved model versions | Person 1 (P1 10) | Kept in the Model Package Group for traceability; the groups stay until final cleanup |
| SageMaker pipeline executions and training jobs | SageMaker lifecycle | Auto-expire; delete processing/training output manually in `ml/artifacts/` if the group is deleted |

## Post-demo final cleanup checklist

1. Confirm no running SageMaker endpoints: `aws sagemaker list-endpoints`.
2. `terraform destroy -target=module.challenge1` (application).
3. `terraform destroy -target=module.challenge3` (SageMaker skeleton).
4. `terraform destroy -target=module.challenge2` leaves the data lake bucket
   and raw data in place.
5. Decide explicitly whether to keep the data lake and state bucket. The
   defaults are "keep" through `prevent_destroy`. Removing them is a
   separate, deliberate change.
