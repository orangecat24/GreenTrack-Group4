-- Reproducible verification queries for the GreenTrack data lake.
-- Query result location: s3://g4-greentrack-dev-datalake-886565871385/athena-results/

-- Bronze: row count matches source upload (131 after sample, or
-- 131 + 2_075_259 after loading the full UCI file).
SELECT source_file, count(*) AS rows
FROM g4_greentrack_dev_bronze.raw_readings
GROUP BY source_file
ORDER BY source_file;

-- Silver: deduplicated row count equals number of unique reading_ts across
-- all uploaded source files.
SELECT count(*) AS silver_rows,
       count(DISTINCT reading_ts) AS distinct_timestamps
FROM g4_greentrack_dev_silver.readings;

-- Silver: missing values stayed NULL (not zero) for the fixture's gap at
-- 11:23 and 11:24 on 2006-12-21.
SELECT reading_ts, global_active_power_kw, sub_metering_3_wh
FROM g4_greentrack_dev_silver.readings
WHERE reading_ts BETWEEN timestamp '2006-12-21 11:23:00'
                     AND timestamp '2006-12-21 11:24:00'
ORDER BY reading_ts;

-- Gold: verify the fixture hours against fixtures/expected_hourly.csv.
SELECT period_start,
       round(energy_kwh,    6) AS energy,
       round(kitchen_kwh,   6) AS kitchen,
       round(laundry_kwh,   6) AS laundry,
       round(heater_ac_kwh, 6) AS heater,
       round(other_kwh,     6) AS other,
       minutes_with_data,
       is_complete
FROM g4_greentrack_dev_gold.hourly_consumption
WHERE period_start BETWEEN timestamp '2006-12-21 10:00:00'
                       AND timestamp '2006-12-21 12:00:00'
ORDER BY period_start;

-- Gold: full-dataset daily totals for a complete demo week.
SELECT period_start,
       round(energy_kwh, 3)    AS energy_kwh,
       minutes_with_data,
       is_complete
FROM g4_greentrack_dev_gold.daily_consumption
WHERE period_start BETWEEN timestamp '2009-06-01 00:00:00'
                       AND timestamp '2009-06-08 00:00:00'
ORDER BY period_start;

-- Gold: full-dataset peak hour per day of the same demo week.
SELECT day, peak_hour_start, round(peak_hour_kwh, 3) AS peak_kwh, max_minute_power_kw
FROM g4_greentrack_dev_gold.daily_peak
WHERE day BETWEEN date '2009-06-01' AND date '2009-06-07'
ORDER BY day;

-- Silver: list Iceberg snapshots for the time-travel demo (P1 08).
SELECT snapshot_id, committed_at, operation
FROM "g4_greentrack_dev_silver"."readings$snapshots"
ORDER BY committed_at;
