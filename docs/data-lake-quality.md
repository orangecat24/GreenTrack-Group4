# Data quality checks on silver (Person 1, task P1 05)

Continues [data-lake-silver.md](data-lake-silver.md). Thresholds come from
[contracts/data.md](../contracts/data.md), section 6.

## What this increment adds

| Resource | Name | Purpose |
| --- | --- | --- |
| DQDL ruleset | `data/quality/silver_readings.dqdl` (uploaded to `scripts/`) | Reviewable single source of the rules |
| Glue job | `g4-greentrack-dev-quality` | Evaluates the ruleset against `silver.readings`, fails on any broken rule |
| Prefix `quality-results/` | result store | Published evaluation results, readable without access to anyone's laptop |

## Rules and why each exists

| Rule | Threshold | Purpose |
| --- | --- | --- |
| `IsComplete reading_ts` | 0 nulls | every row must have a time |
| `IsUnique reading_ts` | 0 duplicates | proves the silver duplicate rule worked |
| `Completeness global_active_power_kw` | >= 95% | full file has 1.25% missing; much more means a broken load |
| `global_active_power_kw` range | 0 to 12 kW | observed 0.076 to 11.122 |
| `voltage_v` range | 200 to 260 V | observed 223.2 to 254.15 |
| `sub_metering_x_wh` range | 0 to 100 Wh | observed max 88 |

Range rules skip nulls (`where ... is not null`): missing values are governed
by the completeness rules, not the range rules.

## Failure policy

A broken rule makes the quality job fail with the rule and reason in its error
message and CloudWatch log; evaluation results are also published to
`quality-results/` and to the Glue Data Quality console. When orchestration
lands (P1 07), the workflow runs bronze → silver → **quality → gold**, so a
quality failure blocks gold publication. Until then the failed job run is the
visible signal, and gold must not be built manually from a failing silver.

## Pass check

After the silver fixture run (130 rows):

```
aws glue start-job-run --job-name g4-greentrack-dev-quality
```

Expect `SUCCEEDED` and all 13 rules `Passed` in the run log and in
`quality-results/`.

## Fail check (intentional, reversible)

1. Upload the bad fixture (out-of-range power, voltage and sub-metering on
   2006-12-22): `aws s3 cp fixtures/raw_quality_fail.csv s3://g4-greentrack-dev-datalake-886565871385/raw/raw_quality_fail.csv`
2. Run bronze with `--raw_key` for that file, then silver, then quality.
3. Expect the quality job to **fail** naming at least the
   `global_active_power_kw <= 12`, `voltage_v` and `sub_metering_2_wh <= 100`
   rules. Anyone can read the reason in the job error, CloudWatch log or
   `quality-results/` without asking Person 1.
4. Repair: upload `fixtures/raw_quality_fix.csv` (same five timestamps, valid
   values) and rerun bronze + silver. The silver MERGE replaces the bad rows
   because the fix has a newer `load_ts`. Rerun quality: `SUCCEEDED`.

This repair path is also the usable-data policy: bad readings are corrected by
re-uploading the affected minutes, never by editing tables by hand.

## Status

Written and validated offline; no AWS run yet. Record observed pass/fail run
IDs here or in the PR when executed.
