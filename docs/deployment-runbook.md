# Fresh-environment deployment runbook (Person 1, task P1 11)

Reconstruct the data and cloud foundation from an empty AWS account. Every
step is a Terraform or AWS CLI command; nothing requires a laptop-specific
file that is not in the repository.

## Prerequisites

- An AWS account with Lake Formation available in `eu-central-1`.
- An IAM identity or SSO profile with permission to create the bootstrap
  resources (admin-equivalent for the initial bootstrap only).
- Terraform 1.17.0 (pinned in [.terraform-version](../.terraform-version)).
- Python 3.12+ for `scripts/check_terraform.py` and job debugging.
- AWS CLI v2.

## Recreation order

### 0. Replace hard-coded account references

If deploying to a different AWS account than `886565871385`, update:

- `infra/bootstrap/main.tf` (`allowed_account_ids`, bucket name suffix).
- `infra/environments/dev/main.tf` (backend `bucket`, `allowed_account_ids`).
- `infra/modules/shared/main.tf` (GitHub trust `sub` values if the repository
  moves).
- `.github/workflows/*.yml` (role ARNs and account ids).

### 1. Bootstrap state (admin identity)

```
cd infra/bootstrap
terraform init
terraform apply
```

Produces the versioned, encrypted state bucket. Its own state stays local to
the operator; keep it with that owner so the dev root's backend is managed.

### 2. Shared foundation (admin identity)

```
cd infra/environments/dev
terraform init
terraform apply -target=module.shared
```

Creates the GitHub OIDC deploy role `g4-greentrack-github-deploy`. From this
point onwards, workflows can take over.

### 3. Data lake and pipeline (deploy role or SSO)

```
cd infra/environments/dev
terraform apply -target=module.challenge2
```

Applies 30 resources: data lake bucket, three catalog databases, bronze
table, Glue scripts, four Glue jobs, workflow + conditional triggers,
EventBridge rule and the two scoped roles.

### 4. SageMaker skeleton

```
terraform apply -target=module.challenge3
```

Adds the SageMaker execution role and the two Model Package Groups. The
pipeline and endpoint resources arrive with P1 10 once Person 3 delivers the
model package.

### 5. Application (Person 2)

```
terraform apply -target=module.challenge1
```

See [application-infrastructure.md](application-infrastructure.md) for the
frontend publish and smoke check.

### 6. Load sample data to prove the pipeline

```
aws s3 cp fixtures/raw_sample.csv \
  s3://g4-greentrack-dev-datalake-886565871385/raw/raw_sample.csv
```

Expect the workflow `g4-greentrack-dev-pipeline` to run bronze → silver →
quality → gold automatically and complete with 4/4 succeeded actions.
Validate the gold numbers against
[fixtures/expected_hourly.csv](../fixtures/expected_hourly.csv) using the
queries in [data-lake-gold.md](data-lake-gold.md).

### 7. Load the full dataset

```
aws s3 cp <path-to>/household_power_consumption.csv \
  s3://g4-greentrack-dev-datalake-886565871385/raw/household_power_consumption.csv
```

Full processing takes ~15 minutes end to end. Verified totals are recorded
in [data-lake-gold.md](data-lake-gold.md) (Verified results, full dataset).

### 8. Grant gold reads to teammates

Collect application, loader, inference and assistant role ARNs. Set them in a
reviewed change on the dev root:

```hcl
# terraform.tfvars
gold_consumer_role_arns = [ "...", "...", "..." ]
```

Run `terraform apply` and confirm each role can `SELECT` from gold through
Athena. See [data-lake-lake-formation.md](data-lake-lake-formation.md) for
the S3-registration follow-up.

## Day-two operations

- **Re-upload a CSV**: safe. Bronze overwrites one folder; silver MERGE
  overwrites one timestamp per newer load; gold is a full rebuild.
- **Fix bad input**: upload a corrected CSV with the same timestamps; the
  next workflow run merges the fix in and quality passes.
- **Rerun a stage manually**:
  `aws glue start-job-run --job-name g4-greentrack-dev-<stage>`.
- **Idle resource teardown**: `aws glue batch-delete-table ...` if a
  temporary experiment table remains; destroy throwaway endpoints with
  `terraform destroy -target=aws_sagemaker_endpoint.<name>`.

See also [resource-inventory.md](resource-inventory.md) for the exhaustive
list of what Person 1 owns and how to remove each piece.
