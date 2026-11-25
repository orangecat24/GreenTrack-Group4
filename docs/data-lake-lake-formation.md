# Lake Formation and Iceberg demonstrations (Person 1, task P1 08)

Continues [data-lake-orchestration.md](data-lake-orchestration.md). Governs
who reads what and demonstrates the two Iceberg features the brief requires.

## Lake Formation module

[`infra/challenge2/lake_formation.tf`](../infra/challenge2/lake_formation.tf)
adds:

- `aws_lakeformation_data_lake_settings` — the deploying identity is added as
  a data lake administrator so Terraform can keep managing LF resources. More
  administrators can be added through `lake_formation_extra_admins`.
- `ALL` on bronze, silver and gold databases for the pipeline role, so the
  managed workflow keeps writing correctly once LF enforcement is on.
- `SELECT` + `DESCRIBE` on the gold database and all gold tables for every
  role ARN in `consumer_role_arns`.

### Collect the ARNs from your teammates

The module's `consumer_role_arns` variable only accepts role ARNs that
already exist in IAM; a grant on a missing principal fails apply with
`InvalidPrincipal`. Expected roles:

| Role | Owner | Status (2026-11-19) |
| --- | --- | --- |
| `g4-greentrack-dev-sagemaker-execution` | Person 1 (infra/challenge3) | applied, exists |
| `g4-greentrack-dev-api-execution` | Person 2 (infra/challenge1) | ARN delivered; Terraform written but **not yet applied in AWS** |
| inference / gold-loader runtime role | Person 2 | ARN pending (not yet implemented) |
| assistant tool / query role | Person 3 (infra/challenge4) | ARN pending |

Activation procedure, once a role has actually been deployed:

1. Confirm the role exists: `aws iam get-role --role-name <name>` returns 0.
2. Add its ARN to the `gold_consumer_role_arns` default list in
   [infra/environments/dev/datalake.tf](../infra/environments/dev/datalake.tf)
   through a reviewed pull request. ARNs are not secrets; the module
   validator refuses anything that isn't a `g4-` prefixed role in this
   account.
3. `terraform apply -target=module.challenge2.aws_lakeformation_permissions.consumer_gold_database`
   and the matching `consumer_gold_tables` resource.

The module validates that only `g4-` prefixed roles in this account are
accepted, which prevents cross-group grants by accident.

### Known ARNs

- `arn:aws:iam::886565871385:role/g4-greentrack-dev-sagemaker-execution` —
  **granted and verified** (2026-11-19). `aws lakeformation list-permissions`
  returns `SELECT`, `DESCRIBE` on `g4_greentrack_dev_gold.*`.
- `arn:aws:iam::886565871385:role/g4-greentrack-dev-api-execution` — Person 2
  published this ARN but has not yet applied `module.challenge1` in AWS.
  Add it to `gold_consumer_role_arns` **after** Person 2 confirms the role
  exists, otherwise apply will fail with `InvalidPrincipal`.

### Why S3 location registration is deferred

Lake Formation grants only enforce once the S3 locations are registered with
LF. Registering before every consumer role is in place would lock teammates
out mid-integration. The planned sequence is:

1. Collect all four ARNs above and apply this module with them set.
2. Confirm the consumer roles can `SELECT` from gold through Athena.
3. Add `aws_lakeformation_resource` registrations for `bronze/`, `silver/`,
   `gold/` and revoke the deployment role's direct S3 writes to those
   prefixes. This hardens access without changing the application contract.

## Iceberg demonstrations

Runnable in Athena against the current silver table. The SQL lives in
[docs/athena/iceberg_demos.sql](athena/iceberg_demos.sql).

### Upsert and time travel (verified 2026-11-19)

Silver's MERGE is the upsert. Each workflow run creates a new Iceberg
snapshot with a `summary` entry that records added/deleted record counts,
giving both the time-travel pointer and the write policy evidence.

Current snapshots of `g4_greentrack_dev_silver.readings`:

| snapshot_id | committed_at | operation | total_records |
| --- | --- | --- | --- |
| 4339315958782429796 | 2026-11-15 21:59:45 | append | 0 (empty create) |
| 4772813796024699498 | 2026-11-15 21:59:51 | append | 130 (first fixture) |
| 1828366379834308211 | 2026-11-15 22:21:44 | overwrite | 130 (replay) |
| 2956731301628486579 | 2026-11-19 13:10:43 | overwrite | 135 (fail demo) |
| 2628479247819102025 | 2026-11-19 13:21:44 | overwrite | 135 (repair demo) |
| 6271800957731412107 | 2026-11-19 13:31:46 | overwrite | **2,075,259 (full UCI dataset)** |

Upsert evidence at `reading_ts = 2006-12-22 10:00:00`:

| snapshot | global_active_power_kw | voltage_v | load_ts |
| --- | --- | --- | --- |
| FAIL (2956731…) | 15.3 (out-of-range) | 300.5 | 2026-11-19 13:08 |
| FIX (2628479…) | 1.41 | 240.5 | 2026-11-19 13:19 |
| NEWEST (6271800…) | 1.41 | 240.5 | 2026-11-19 13:29 |

Each state is retrievable through `FOR VERSION AS OF <snapshot_id>` on the
silver table, which is Athena's native Iceberg time-travel syntax.
