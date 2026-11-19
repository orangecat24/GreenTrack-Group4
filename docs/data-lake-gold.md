# Gold layer: business summaries (Person 1, task P1 06)

Continues [data-lake-quality.md](data-lake-quality.md). Schemas and
calculation rules come from [contracts/data.md](../contracts/data.md),
sections 3 and 5.

## What this increment adds

| Resource | Name | Purpose |
| --- | --- | --- |
| Glue database | `g4_greentrack_dev_gold` | Gold catalog database (Terraform) |
| Glue job | `g4-greentrack-dev-gold` | Builds all three gold tables from silver (Iceberg, full recompute) |
| Iceberg tables | `hourly_consumption`, `daily_consumption`, `daily_peak` | Created by the job, partitioned by `year`, `month`, stored under `gold/` |

## Calculation rules implemented (data/glue/gold_job.py)

- `energy_kwh` = sum of per-minute power / 60 — power is converted to energy,
  never just summed (contract section 3).
- Sub-metering columns are already energy in Wh: `/ 1000` to kWh;
  `other_kwh` = `energy_kwh` minus the three sub-meters.
- Only minutes with values are added; `minutes_with_data` reports coverage and
  `is_complete` is true at 60 (hour) or 1440 (day). Missing minutes are never
  counted as zero; an empty hour has null energy.
- `daily_peak` takes the hour with the highest `energy_kwh` per day (earliest
  hour wins a tie) plus the day's highest single-minute power.
- The job rebuilds all three tables with `CREATE OR REPLACE`, so every run is
  a consistent snapshot of current silver and reruns are idempotent.

## How to verify with the fixture (completion check for P1 06)

Prerequisite: silver fixture data exists (130 rows from
[data-lake-silver.md](data-lake-silver.md)).

1. `aws glue start-job-run --job-name g4-greentrack-dev-gold`
2. Wait for `SUCCEEDED`, then in Athena:

   ```sql
   SELECT period_start, energy_kwh, kitchen_kwh, laundry_kwh, heater_ac_kwh,
          other_kwh, minutes_with_data, is_complete
   FROM g4_greentrack_dev_gold.hourly_consumption
   ORDER BY period_start;
   ```

   Compare against [fixtures/expected_hourly.csv](../fixtures/expected_hourly.csv),
   which was calculated independently with plain Python:

   | period_start | energy_kwh | minutes_with_data | is_complete |
   | --- | --- | --- | --- |
   | 2006-12-21 10:00 | 1.767700 | 60 | true |
   | 2006-12-21 11:00 | 0.516833 | 58 | false |
   | 2006-12-21 12:00 | 0.037767 | 10 | false |

   A mismatch means investigating the job, not editing the expected file.

3. Check the peak:

   ```sql
   SELECT * FROM g4_greentrack_dev_gold.daily_peak WHERE day = date '2006-12-21';
   -- expected: peak_hour_start 10:00, peak_hour_kwh 1.7677, max_minute_power_kw 3.728
   ```

4. Rerun step 1: identical results (full recompute).

With the full dataset loaded, additionally compare one real week's hourly and
daily totals between silver (manual SQL aggregation) and the gold tables.

## Gold handoff package (to publish after the verified AWS run)

- Catalog: `g4_greentrack_dev_gold`; tables above; schema v1 as in the
  contract; S3 under `gold/` in the data lake bucket.
- Quality policy: gold is rebuilt only from silver that passed the DQDL rules
  (enforced by the workflow from P1 07); coverage fields tell consumers about
  incomplete periods.
- Verified SQL totals: record the Athena numbers here when the run happens.
- Role access: granted in P1 08 (Lake Formation) once Person 2 and Person 3
  provide their runtime role ARNs.

## Verified results (2026-11-15, applied and run in AWS)

Athena returned values identical to the independently calculated
[fixtures/expected_hourly.csv](../fixtures/expected_hourly.csv):

| period_start | energy_kwh | kitchen | laundry | heater_ac | other | minutes | complete |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2006-12-21 10:00 | 1.7677 | 0.569 | 0.031 | 0.89 | 0.2777 | 60 | true |
| 2006-12-21 11:00 | 0.516833 | 0.0 | 0.0 | 0.0 | 0.516833 | 58 | false |
| 2006-12-21 12:00 | 0.037767 | 0.0 | 0.0 | 0.0 | 0.037767 | 10 | false |

`daily_consumption`: 2.3223 kWh over 128 minutes, `is_complete=false`.
`daily_peak`: peak hour 10:00 at 1.7677 kWh, max minute power 3.728 kW —
all matching the contract's hand calculations.

### Verified results (2026-11-19, full UCI dataset)

Full workflow run
`wr_b38a9cb412c00d3720d0ecf9b6b47761b138b9a217fdad07661e2fe2b79b5721`
processed `household_power_consumption.csv` (2,075,259 rows) end to end.

- `g4_greentrack_dev_silver.readings`: 2,075,259 rows with 2,075,259 distinct
  timestamps, spanning `2006-12-16 17:24` to `2010-11-26 21:02`.
- `g4_greentrack_dev_gold.hourly_consumption`: **34,589 rows** covering the
  same span (~48 months × ~720 hours).
- Fixture hours still reconcile: 2006-12-21 10:00 = 1.7677 kWh (complete);
  11:00 = 0.516833 kWh (58 min); the 12:00 hour grew to 0.819133 kWh (full
  60 min) because the full dataset supplied the minutes the fixture lacked.
- Demo week 2009-06-01 to 2009-06-07 (all complete days):

  | day | daily_kwh | peak_hour | peak_kwh | max_minute_power_kw |
  | --- | --- | --- | --- | --- |
  | 2009-06-01 | 24.054 | 12:00 | 2.512 | 5.322 |
  | 2009-06-02 | 18.177 | 08:00 | 1.664 | 2.992 |
  | 2009-06-03 | 22.610 | 08:00 | 2.058 | 4.262 |
  | 2009-06-04 | 17.261 | 08:00 | 1.826 | 4.892 |
  | 2009-06-05 | 20.506 | 07:00 | 1.597 | 4.190 |
  | 2009-06-06 | 24.591 | 19:00 | 2.556 | 6.282 |
  | 2009-06-07 | 20.123 | 13:00 | 3.455 | 8.760 |

## Gold handoff package (ready for Persons 2 and 3)

- Catalog: `g4_greentrack_dev_gold`; three Iceberg tables listed above.
- S3 locations: `s3://g4-greentrack-dev-datalake-886565871385/gold/`.
- Schema version: v1 as in [contracts/data.md](../contracts/data.md).
- Quality policy: gold is rebuilt only after silver passes the DQDL ruleset
  (enforced by the Glue workflow; see
  [data-lake-orchestration.md](data-lake-orchestration.md)).
- Role access: granted through
  [data-lake-lake-formation.md](data-lake-lake-formation.md)'s
  `gold_consumer_role_arns` variable once teammate ARNs land.
