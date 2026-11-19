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

Before applying this module to grant real consumer access, Person 2 and
Person 3 must publish their runtime role ARNs through their own Terraform
outputs. Expected pattern (ARNs validated by the module variable):

- Person 2 application / loader runtime role
- Person 2 model-invocation Lambda role
- Person 3 assistant query role
- `${var.name_prefix}-sagemaker-execution` (owned by this project,
  [infra/challenge3](../infra/challenge3))

Set them on the dev root through
`gold_consumer_role_arns`:

```hcl
# infra/environments/dev/terraform.tfvars (not committed; or pass via -var)
gold_consumer_role_arns = [
  "arn:aws:iam::886565871385:role/g4-greentrack-dev-sagemaker-execution",
  "arn:aws:iam::886565871385:role/g4-greentrack-dev-app-runtime",
  "arn:aws:iam::886565871385:role/g4-greentrack-dev-assistant-tool",
]
```

The module validates that only `g4-` prefixed roles in this account are
accepted, which prevents cross-group grants by accident.

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
