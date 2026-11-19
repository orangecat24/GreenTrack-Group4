-- GreenTrack Iceberg demonstrations for P1 08.
-- Run in Athena with query result location
-- s3://g4-greentrack-dev-datalake-886565871385/athena-results/.

-- 1) Available snapshots of the silver readings table, oldest first.
SELECT snapshot_id, committed_at, operation, summary
FROM "g4_greentrack_dev_silver"."readings$snapshots"
ORDER BY committed_at;

-- 2) Rows visible at the oldest snapshot. Replace <OLDEST_ID> with the
--    first snapshot_id returned by query 1.
SELECT count(*) AS rows_at_oldest_snapshot
FROM "g4_greentrack_dev_silver"."readings"
FOR VERSION AS OF <OLDEST_ID>;

-- 3) Rows visible now (current state of the table).
SELECT count(*) AS rows_now
FROM "g4_greentrack_dev_silver"."readings";

-- 4) Prove an upsert: compare a specific minute at two snapshots. Replace
--    both ids and the timestamp.
SELECT 'oldest' AS snapshot, reading_ts, global_active_power_kw, load_ts
FROM "g4_greentrack_dev_silver"."readings" FOR VERSION AS OF <OLDEST_ID>
WHERE reading_ts = timestamp '2006-12-21 10:30:00'
UNION ALL
SELECT 'newest', reading_ts, global_active_power_kw, load_ts
FROM "g4_greentrack_dev_silver"."readings"
WHERE reading_ts = timestamp '2006-12-21 10:30:00';
