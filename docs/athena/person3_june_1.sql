-- P3 04 comparison queries for an authorized live verification session.
-- Run against the same approved gold publication as the assistant.
-- The source timestamps use the historical clock labelled UTC by the app.
WITH hourly AS (
    SELECT period_start, energy_kwh, minutes_with_data, is_complete
    FROM g4_greentrack_dev_gold.hourly_consumption
    WHERE household_id = 'household-1'
      AND period_start >= TIMESTAMP '2009-06-01 00:00:00'
      AND period_start <  TIMESTAMP '2009-06-02 00:00:00'
)
SELECT
    round(sum(energy_kwh), 3) AS observed_kwh_3dp,
    count(*) AS row_count,
    count(DISTINCT period_start) AS distinct_hours,
    1440 AS expected_minutes,
    coalesce(sum(minutes_with_data), 0) AS measured_minutes,
    count_if(is_complete AND minutes_with_data = 60) AS complete_hours,
    count_if(minutes_with_data BETWEEN 1 AND 59) AS partial_hours,
    count_if(minutes_with_data = 0 AND energy_kwh IS NULL) AS all_null_hours,
    24 - count(DISTINCT period_start) AS absent_hours
FROM hourly;

-- Reconcile the hourly sum independently with the published daily row.
SELECT period_start, round(energy_kwh, 3) AS observed_kwh_3dp,
       minutes_with_data, is_complete
FROM g4_greentrack_dev_gold.daily_consumption
WHERE household_id = 'household-1'
  AND period_start >= TIMESTAMP '2009-06-01 00:00:00'
  AND period_start <  TIMESTAMP '2009-06-02 00:00:00';