# Pipeline orchestration on upload (Person 1, task P1 07)

Continues [data-lake-gold.md](data-lake-gold.md). This increment makes a CSV
upload run the whole medallion pipeline automatically.

## Flow

```
s3://.../raw/<file>.csv  (Object Created event)
        │  EventBridge rule, key prefix raw/ only
        ▼
Glue workflow g4-greentrack-dev-pipeline
  bronze ─SUCCEEDED→ silver ─SUCCEEDED→ quality ─SUCCEEDED→ gold
```

- The S3 bucket publishes events to EventBridge; the rule matches only
  `Object Created` with key prefix `raw/`. Parquet written under `bronze/`,
  `silver/`, `gold/`, Athena results under `athena-results/` and quality
  results under `quality-results/` can never re-trigger the pipeline.
- Each arrow is a Glue conditional trigger on `SUCCEEDED`. A quality failure
  stops the workflow before gold, which enforces the policy from
  [data-lake-quality.md](data-lake-quality.md): bad data never reaches gold.
- EventBridge starts the workflow through a dedicated role that may do
  exactly one thing: `glue:NotifyEvent` on this workflow.

## Why the jobs need no per-file parameters

Every job is idempotent over the whole lake, so the workflow simply runs them
with their defaults:

| Job | Idempotency |
| --- | --- |
| bronze | one Parquet folder per source file, overwritten on rerun |
| silver | Iceberg MERGE on `household_id, reading_ts`; newest `load_ts` wins |
| quality | read-only evaluation |
| gold | full `CREATE OR REPLACE` recompute from silver |

Re-uploading the same file therefore cannot duplicate observations or double
published totals, and a retry is just "upload again" or "rerun the workflow".

## How to verify (completion check for P1 07)

1. Upload a fixture: `aws s3 cp fixtures/raw_sample.csv s3://g4-greentrack-dev-datalake-886565871385/raw/raw_sample.csv`
2. Watch the run: `aws glue get-workflow-runs --name g4-greentrack-dev-pipeline`
   (or the Glue console workflow graph). All four jobs should reach
   `SUCCEEDED` within ~1 minute of batching delay plus job runtimes.
3. Query gold in Athena and compare with
   [fixtures/expected_hourly.csv](../fixtures/expected_hourly.csv).
4. Failure case: upload `fixtures/raw_quality_fail.csv`; the workflow stops at
   the failed quality job and gold is not rebuilt. The reason is visible in
   the workflow graph and the quality job error.
5. Retry case: upload `fixtures/raw_quality_fix.csv`; the next run repairs the
   bad minutes (silver MERGE) and completes through gold. Re-upload
   `raw_sample.csv` once more and confirm gold totals are unchanged.
6. Record run IDs and observed counts here after the real AWS run.

Downstream signal for Person 2 (gold-to-DynamoDB loader): watch for the gold
job's `SUCCEEDED` state in this workflow (EventBridge exposes Glue job state
changes); the exact hookup is agreed in P2 06. Person 3 reads the available
data period from `gold.hourly_consumption` bounds.

## Status

Written and validated offline; no AWS run yet.
