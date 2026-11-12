"""Bronze Glue job: convert the raw semicolon CSV to Parquet, changing nothing.

What this job does (and deliberately does NOT do):
  - Reads the uploaded CSV exactly as text. Every value column stays a string,
    so "?" markers and any malformed input survive into bronze unchanged.
  - Adds two traceability columns: source_file (which upload a row came from)
    and load_ts (when this job loaded it).
  - Writes Parquet into the bronze table location, in one subfolder per source
    file. Re-running the job for the same file OVERWRITES that subfolder, so a
    retry can never duplicate rows.
  - No cleaning, no type casting, no deduplication. That is silver's job.

Arguments (all provided by Terraform's default_arguments; raw_key is
overridden per run to convert one specific upload):
  --raw_key      full s3://bucket/raw/... URI of ONE file, or "" for all files
  --raw_path     s3://bucket/raw/ landing prefix (used when raw_key is "")
  --bronze_path  s3://bucket/bronze/raw_readings/ table location
"""

import re
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

# The exact header of the UCI file, in order. We define the schema ourselves
# instead of letting Spark infer types: inference would turn "?" columns into
# messy mixed types, and bronze must preserve the source as-is.
SOURCE_COLUMNS = [
    "Date",
    "Time",
    "Global_active_power",
    "Global_reactive_power",
    "Voltage",
    "Global_intensity",
    "Sub_metering_1",
    "Sub_metering_2",
    "Sub_metering_3",
]

# Lowercase names used in the Glue catalog table (contracts/data.md, bronze).
TARGET_NAMES = [name.lower() for name in SOURCE_COLUMNS]


def folder_name_for(source_file: str) -> str:
    """Turn an uploaded file name into a safe S3 folder name.

    Example: "household_power_consumption.csv" -> "household_power_consumption_csv".
    Each source file gets its own folder so a retry overwrites only itself.
    """
    return re.sub(r"[^A-Za-z0-9_-]", "_", source_file)


def main() -> None:
    args = getResolvedOptions(
        sys.argv, ["JOB_NAME", "raw_key", "raw_path", "bronze_path"]
    )

    spark_context = SparkContext()
    glue_context = GlueContext(spark_context)
    spark = glue_context.spark_session
    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    # One specific upload, or (fallback) everything in the landing prefix.
    input_path = args["raw_key"] or args["raw_path"]
    print(f"Reading raw CSV from {input_path}")

    schema = StructType(
        [StructField(name, StringType(), True) for name in SOURCE_COLUMNS]
    )
    raw = (
        spark.read.option("sep", ";")
        .option("header", "true")
        .schema(schema)
        .csv(input_path)
    )

    # Traceability: which file each row came from, and when we loaded it.
    # input_file_name() gives the full s3:// URI; keep only the file name.
    with_metadata = (
        raw.withColumn(
            "source_file", F.element_at(F.split(F.input_file_name(), "/"), -1)
        )
        .withColumn("load_ts", F.current_timestamp())
    )

    # Rename headers to the lowercase catalog column names. Values untouched.
    for source_name, target_name in zip(SOURCE_COLUMNS, TARGET_NAMES):
        with_metadata = with_metadata.withColumnRenamed(source_name, target_name)

    # Write one folder per source file, overwriting that folder only. The
    # bronze table reads the whole bronze_path, so Athena sees all folders.
    source_files = [
        row["source_file"]
        for row in with_metadata.select("source_file").distinct().collect()
    ]
    total_rows = 0
    for source_file in source_files:
        part = with_metadata.filter(F.col("source_file") == source_file)
        part_count = part.count()
        total_rows += part_count
        destination = args["bronze_path"] + folder_name_for(source_file) + "/"
        print(f"Writing {part_count} rows from {source_file} to {destination}")
        part.write.mode("overwrite").parquet(destination)

    # The completion check for P1 03: input and output row counts must match,
    # because bronze never removes or repairs source observations.
    input_rows = raw.count()
    print(f"Input rows: {input_rows}, written rows: {total_rows}")
    if input_rows != total_rows:
        raise RuntimeError(
            f"Row count mismatch: read {input_rows} but wrote {total_rows}."
        )

    job.commit()


if __name__ == "__main__":
    main()
