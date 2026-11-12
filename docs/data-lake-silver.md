# Silver layer: cleaned Iceberg readings (Person 1, task P1 04)

Continues [data-lake-bronze.md](data-lake-bronze.md). The cleaning rules are
the contract's sections 2, 4 and 5 ([contracts/data.md](../contracts/data.md)).

## What this increment adds

| Resource | Name | Purpose |
| --- | --- | --- |
| Glue database | `g4_greentrack_dev_silver` | Silver catalog database (Terraform) |
| Glue job | `g4-greentrack-dev-silver` | Bronze Parquet to Iceberg `readings` (Glue 5.0, Iceberg enabled, 60 min timeout) |
| Iceberg table | `readings` | Created by the job's **first run**, partitioned by `year`, `month`, stored under `silver/` |

The table is intentionally not a Terraform resource: Iceberg tables own their
metadata (schema, snapshots for time travel, partition layout) and must be
created by the writing engine. Terraform still owns the database, bucket,
prefix, job and role around it.

## Cleaning rules implemented (data/glue/silver_job.py)

- `reading_ts` = Date + Time parsed as `d/M/yyyy HH:mm:ss`; rows that cannot
  be parsed are **rejected and counted**, and the job fails if more than 1% of
  the input is rejected (a few bad lines pass, a malformed file does not).
- `?` and empty strings become **null, never 0**; the seven value columns are
  cast to double with the contract's silver names (`global_active_power_kw`,
  ..., `sub_metering_3_wh`).
- Duplicates: one row per `reading_ts`; the row with the newest `load_ts`
  wins, so a corrected upload replaces the old value.
- Reprocessing safety: the job ends in an Iceberg `MERGE` keyed on
  `household_id, reading_ts`. Running the same source twice changes nothing;
  every run is a new Iceberg snapshot (the time-travel evidence for P1 08).
- `household_id` is the constant `household-1`; `source_file` and `load_ts`
  carry through from bronze for traceability.

## How to verify with the fixture (completion check for P1 04)

Prerequisite: the bronze fixture run from
[data-lake-bronze.md](data-lake-bronze.md) succeeded (131 bronze rows).

1. Run the silver job (defaults already point at bronze):
   `aws glue start-job-run --job-name g4-greentrack-dev-silver`
2. Wait for `SUCCEEDED`, then in Athena:

   ```sql
   SELECT count(*) FROM g4_greentrack_dev_silver.readings;
   -- expected: 130 (the fixture's duplicate 10:30 row collapsed to one)

   SELECT reading_ts, global_active_power_kw, sub_metering_3_wh
   FROM g4_greentrack_dev_silver.readings
   WHERE reading_ts BETWEEN timestamp '2006-12-21 11:23:00'
                        AND timestamp '2006-12-21 11:24:00';
   -- expected: both rows present with NULL values (missing, not zero)

   SELECT count(*) FROM g4_greentrack_dev_silver.readings
   WHERE reading_ts = timestamp '2006-12-21 10:30:00';
   -- expected: 1 (duplicate removed)
   ```

3. Re-run step 1 and repeat the first count: still 130 (MERGE is idempotent).
4. Compare the three expected numbers against
   [fixtures/expected_hourly.csv](../fixtures/expected_hourly.csv) coverage:
   hour 10 has 60 minutes, hour 11 has 58, hour 12 has 10.

Record observed results here or in the PR when the run is performed; as of
this commit the job is written and validated offline, **no AWS run yet**.

## Handoff notes

- Person 3 receives this clean sample for feature inspection; the gold
  contract (P1 06) stays the final training interface.
- Partition pruning: filter on `year` and `month` (or on `reading_ts`, which
  Iceberg maps to partitions) to keep Athena scans small.
- Next increments: Glue Data Quality rules on silver (P1 05), then gold
  summaries (P1 06).
