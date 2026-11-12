# Data lake and bronze layer (Person 1, task P1 03)

This document records what the Challenge 2 bronze increment adds, how to deploy
and verify it, and what teammates receive from it. The schema rules come from
[contracts/data.md](../contracts/data.md); nothing here changes that contract.

## What exists after this increment

All resources are defined in Terraform under `infra/challenge2/`, called as
`module.challenge2` from the existing `infra/environments/dev` root. Nothing
was created from the AWS console.

| Resource | Name | Purpose |
| --- | --- | --- |
| S3 bucket | `g4-greentrack-dev-datalake-886565871385` | One data lake bucket, layers separated by prefix |
| Prefix `raw/` | upload target | Source CSV exactly as received; versioned, never modified |
| Prefix `bronze/raw_readings/` | bronze table location | Parquet conversion, one subfolder per source file |
| Prefix `scripts/` | Glue scripts | `bronze_job.py`, uploaded by Terraform from the repository |
| Prefix `glue-temp/` | Glue scratch space | Needed by Glue while a job runs |
| Prefix `athena-results/` | Athena output | Athena always needs a result-writing location |
| Glue database | `g4_greentrack_dev_bronze` | Bronze catalog database |
| Glue table | `raw_readings` | All source columns as text, plus `source_file` and `load_ts` |
| Glue job | `g4-greentrack-dev-bronze` | CSV to Parquet, no business changes (Glue 5.0, 2x G.1X, 30 min timeout) |
| IAM role | `g4-greentrack-dev-glue-pipeline` | Read raw/scripts, write bronze/silver/gold/temp only |

The prefixes are deliberately separate so the later upload trigger (P1 07) can
watch `raw/` only: Parquet outputs and Athena query results can never re-fire
the pipeline.

## Bronze rules (from the contract)

- Every source value column stays a **string**. `?` stays `?`. Nothing is
  cleaned, cast, deduplicated or repaired; that happens in silver (P1 04).
- Each row carries `source_file` (which upload it came from) and `load_ts`
  (when the job loaded it). That is the traceability path: any bronze row
  points back to the exact object under `raw/`.
- The job writes each source file to its own subfolder and overwrites only
  that subfolder on a retry, so re-running the same input cannot duplicate
  rows. It also fails loudly if the written row count differs from the input.

## How to deploy (foundation owner or activated pipeline)

From `infra/environments/dev`, with the usual SSO profile
(`AWS_PROFILE=greentrack`, `AWS_REGION=eu-central-1`) and the pinned
Terraform 1.17.0:

```
terraform init
terraform plan    # review: bucket, database, table, job, role, script upload
terraform apply
```

The apply prints a `data_lake` output with every name teammates need.

## How to verify with the fixture (completion check for P1 03)

1. Upload the committed fixture:
   `aws s3 cp fixtures/raw_sample.csv s3://g4-greentrack-dev-datalake-886565871385/raw/raw_sample.csv`
2. Run the job for exactly that file:
   `aws glue start-job-run --job-name g4-greentrack-dev-bronze --arguments '{"--raw_key":"s3://g4-greentrack-dev-datalake-886565871385/raw/raw_sample.csv"}'`
3. Wait for `SUCCEEDED` (`aws glue get-job-run ...`), then query in Athena
   (result location `s3://g4-greentrack-dev-datalake-886565871385/athena-results/`):

   ```sql
   SELECT count(*) FROM g4_greentrack_dev_bronze.raw_readings;
   -- expected: 131 (130 real rows + the fixture's fake duplicate; bronze keeps it)

   SELECT date, time, global_active_power, source_file, load_ts
   FROM g4_greentrack_dev_bronze.raw_readings
   WHERE time = '11:23:00';
   -- expected: global_active_power = '?', source_file = 'raw_sample.csv'
   ```

4. Re-run step 2 and repeat the count: still 131, because the retry overwrote
   the same subfolder instead of appending.
5. Only after the fixture passes, upload the full
   `household_power_consumption.csv` the same way and expect 2,075,259 rows.

Record the observed counts in the PR or in this document when the run is
performed; as of this commit the module is written and validated offline, but
**no AWS apply or job run has been performed yet**.

## Handoff to Persons 2 and 3

- The bronze schema is the contract's section 5 bronze table; query it with
  the Athena examples above.
- Traceability example: pick any row, read its `source_file`, and find that
  object under `raw/` (versioned, so even replaced uploads are recoverable).
- Person 3 can inspect representative raw patterns (missing `?` rows,
  duplicates) directly in `raw_readings` once the full file is loaded.
- Silver (Iceberg, cleaning, dedup) is the next increment, P1 04.
