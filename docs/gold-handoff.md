# Gold ready handoff package

Person 1 to Persons 2 and 3. All items on page 6 of the work plan are
present here: catalog names, S3 locations, schema version, sample rows,
quality policy, verified SQL totals, and granted role access.

## Catalog and locations

| Item | Value |
| --- | --- |
| AWS account | `886565871385` |
| Region | `eu-central-1` |
| Data lake bucket | `s3://g4-greentrack-dev-datalake-886565871385/` |
| Gold S3 prefix | `s3://g4-greentrack-dev-datalake-886565871385/gold/` |
| Gold catalog database | `g4_greentrack_dev_gold` |
| Athena query result location | `s3://g4-greentrack-dev-datalake-886565871385/athena-results/` |

## Tables and schemas

Schema version **v1**, from [contracts/data.md](../contracts/data.md).

### `g4_greentrack_dev_gold.hourly_consumption`

| Column | Type | Notes |
| --- | --- | --- |
| household_id | string | always `household-1` |
| period_start | timestamp | start of the hour, UTC convention |
| energy_kwh | double | sum of per-minute power / 60 |
| kitchen_kwh | double | sub-meter 1 / 1000 |
| laundry_kwh | double | sub-meter 2 / 1000 |
| heater_ac_kwh | double | sub-meter 3 / 1000 |
| other_kwh | double | energy_kwh minus the three sub-meters |
| minutes_with_data | int | 0..60 |
| is_complete | boolean | true when minutes_with_data = 60 |
| year, month | int | Iceberg partitions |

### `g4_greentrack_dev_gold.daily_consumption`

Same columns as hourly; `period_start` is midnight, `minutes_with_data` is
0..1440, and `is_complete` is true at 1440.

### `g4_greentrack_dev_gold.daily_peak`

| Column | Type | Notes |
| --- | --- | --- |
| household_id | string | |
| day | date | |
| peak_hour_start | timestamp | hour with the highest `energy_kwh` that day |
| peak_hour_kwh | double | energy of that hour |
| max_minute_power_kw | double | highest single-minute power that day |
| year, month | int | Iceberg partitions |

## Quality policy

- Gold is rebuilt only after silver passes the DQDL ruleset (see
  [data-lake-quality.md](data-lake-quality.md)); the Glue workflow enforces
  this as a conditional trigger (bronze → silver → **quality → gold**).
- Missing minutes are never counted as zero. Use `is_complete` and
  `minutes_with_data` before treating a row as a full period.
- Timestamps carry the same UTC convention as the source file; no
  daylight-saving conversion is applied.

## Verified totals (2026-11-19)

Workflow run
`wr_b38a9cb412c00d3720d0ecf9b6b47761b138b9a217fdad07661e2fe2b79b5721`
processed `household_power_consumption.csv` (2,075,259 rows) end to end.

- Silver spans `2006-12-16 17:24` to `2010-11-26 21:02`.
- Gold holds **34,589 hourly rows** across the same span.
- Fixture hours (see [fixtures/expected_hourly.csv](../fixtures/expected_hourly.csv)):
  2006-12-21 10:00 = 1.7677 kWh (complete); 11:00 = 0.516833 kWh (58 min).
- Demo week 2009-06-01..07 daily totals: 24.054, 18.177, 22.610, 17.261,
  20.506, 24.591, 20.123 kWh (all complete days). Peak hours and max-minute
  powers recorded in [data-lake-gold.md](data-lake-gold.md).

## Sample rows

```sql
SELECT * FROM g4_greentrack_dev_gold.hourly_consumption
WHERE period_start BETWEEN timestamp '2009-06-01 06:00:00'
                       AND timestamp '2009-06-01 09:00:00'
ORDER BY period_start;
```

Returns three hours with `is_complete = true`, non-zero sub-metering during
the breakfast/morning peak, and the remainder flowing into `other_kwh`.

Full reproducible query set:
[docs/athena/verification_queries.sql](athena/verification_queries.sql).

## Granted access (Lake Formation)

| Role ARN | Grant on gold | Status |
| --- | --- | --- |
| `arn:aws:iam::886565871385:role/g4-greentrack-dev-sagemaker-execution` | `SELECT`, `DESCRIBE` on database and all tables | **Applied** |
| `arn:aws:iam::886565871385:role/g4-greentrack-dev-api-execution` | add to `gold_consumer_role_arns` after Person 2 deploys their module | Pending |
| Person 2 inference/gold-loader role | awaiting ARN | Pending |
| Person 3 assistant tool role | awaiting ARN | Pending |

Procedure for the pending ones is in
[data-lake-lake-formation.md](data-lake-lake-formation.md).

## How to query (Person 2 and Person 3)

Through the Athena console (any identity with LF SELECT on gold):

```sql
SELECT period_start, energy_kwh, is_complete
FROM g4_greentrack_dev_gold.hourly_consumption
WHERE period_start BETWEEN timestamp '2009-06-01 00:00:00'
                       AND timestamp '2009-06-08 00:00:00'
ORDER BY period_start;
```

Programmatic access (Python / boto3): `start_query_execution` against the
Athena workgroup `primary`, with `OutputLocation` set to the Athena query
result location above. The caller assumes a role granted `SELECT` on gold.

## What this handoff means you can start

- Person 2's consumption loader can query these three tables and write the
  per-household / per-period items into DynamoDB today.
- Person 3's processing script can read `gold.hourly_consumption` as the
  model feature source. The `sagemaker-execution` role is already granted
  and is the one SageMaker jobs use.
