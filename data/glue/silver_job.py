"""Silver Glue job: clean bronze into a typed Apache Iceberg table.

What this job does (rules come from contracts/data.md, sections 2, 4 and 5):
  - Combines the text Date + Time columns into one real timestamp, reading_ts.
  - Converts "?" (and empty strings) to null, NEVER to 0, and casts the seven
    value columns to double.
  - Rejects rows whose Date/Time cannot be parsed into a timestamp: a reading
    without a valid time is unusable. Rejected rows are counted and logged,
    and the job fails if more than 1% of the input is rejected (that would
    mean a malformed file, not a few bad lines).
  - Removes duplicate timestamps: one row per reading_ts, the row with the
    newest load_ts wins (a correction uploaded later replaces the old value).
  - MERGEs into an Iceberg table partitioned by year and month. MERGE makes
    reprocessing safe: running the same source twice updates the same rows
    instead of doubling them, and every run creates a new Iceberg snapshot
    (which later gives us time travel, P1 08).

Arguments (defaults come from Terraform; see infra/challenge2/glue.tf):
  --bronze_path      s3://bucket/bronze/raw_readings/ Parquet to read
  --warehouse_path   s3://bucket/silver/ Iceberg warehouse root
  --silver_database  Glue database that will hold the table
  --silver_table     table name, "readings"
  --household_id     constant "household-1" (the dataset has one household)
"""

import sys

from awsglue.utils import getResolvedOptions
from pyspark.conf import SparkConf
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Bronze text column -> (silver column, from contracts/data.md section 5).
VALUE_COLUMNS = {
    "global_active_power": "global_active_power_kw",
    "global_reactive_power": "global_reactive_power_kw",
    "voltage": "voltage_v",
    "global_intensity": "global_intensity_a",
    "sub_metering_1": "sub_metering_1_wh",
    "sub_metering_2": "sub_metering_2_wh",
    "sub_metering_3": "sub_metering_3_wh",
}

REJECTED_ROW_LIMIT = 0.01  # fail if more than 1% of rows have no valid timestamp


def clean_number(column_name: str):
    """Return the column as double, with "?" and "" becoming null (never 0)."""
    text = F.trim(F.col(column_name))
    return (
        F.when((text == "?") | (text == ""), F.lit(None))
        .otherwise(text)
        .cast("double")
    )


def main() -> None:
    args = getResolvedOptions(
        sys.argv,
        [
            "JOB_NAME",
            "bronze_path",
            "warehouse_path",
            "silver_database",
            "silver_table",
            "household_id",
        ],
    )

    # Iceberg needs these settings BEFORE the Spark context exists. They tell
    # Spark to use the Glue Data Catalog as an Iceberg catalog named
    # "glue_catalog", storing table files under our silver/ prefix.
    conf = SparkConf()
    conf.set(
        "spark.sql.extensions",
        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    )
    conf.set("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog")
    conf.set("spark.sql.catalog.glue_catalog.warehouse", args["warehouse_path"])
    conf.set(
        "spark.sql.catalog.glue_catalog.catalog-impl",
        "org.apache.iceberg.aws.glue.GlueCatalog",
    )
    conf.set(
        "spark.sql.catalog.glue_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO"
    )

    spark_context = SparkContext(conf=conf)

    # Import awsglue AFTER the configured context exists, so GlueContext wraps
    # the Iceberg-enabled session instead of creating a plain one.
    from awsglue.context import GlueContext
    from awsglue.job import Job

    glue_context = GlueContext(spark_context)
    spark = glue_context.spark_session
    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    bronze = spark.read.parquet(args["bronze_path"])
    input_rows = bronze.count()
    print(f"Bronze input rows: {input_rows}")

    # Date is d/m/yyyy in the source; a failed parse gives null, not an error.
    cleaned = bronze.withColumn(
        "reading_ts",
        F.to_timestamp(
            F.concat_ws(" ", F.trim(F.col("date")), F.trim(F.col("time"))),
            "d/M/yyyy HH:mm:ss",
        ),
    )

    rejected = cleaned.filter(F.col("reading_ts").isNull())
    rejected_rows = rejected.count()
    print(f"Rejected rows (unparseable Date/Time): {rejected_rows}")
    if input_rows > 0 and rejected_rows / input_rows > REJECTED_ROW_LIMIT:
        raise RuntimeError(
            f"{rejected_rows} of {input_rows} rows have no valid timestamp; "
            "the input looks malformed, refusing to publish silver."
        )

    typed = cleaned.filter(F.col("reading_ts").isNotNull())
    for bronze_name, silver_name in VALUE_COLUMNS.items():
        typed = typed.withColumn(silver_name, clean_number(bronze_name))

    # Duplicate rule from the contract: one row per reading_ts, newest load_ts
    # wins. row_number gives every duplicate group exactly one survivor.
    one_per_minute = Window.partitionBy("reading_ts").orderBy(
        F.col("load_ts").desc(), F.col("source_file").desc()
    )
    deduplicated = (
        typed.withColumn("row_rank", F.row_number().over(one_per_minute))
        .filter(F.col("row_rank") == 1)
        .drop("row_rank")
    )

    silver = deduplicated.select(
        F.lit(args["household_id"]).alias("household_id"),
        F.col("reading_ts"),
        *[F.col(name) for name in VALUE_COLUMNS.values()],
        F.year("reading_ts").alias("year"),
        F.month("reading_ts").alias("month"),
        F.col("source_file"),
        F.col("load_ts"),
    )
    output_rows = silver.count()
    print(f"Silver rows after cleaning and deduplication: {output_rows}")

    table = f"glue_catalog.{args['silver_database']}.{args['silver_table']}"
    silver.createOrReplaceTempView("silver_source")

    # First run: create the empty partitioned table from the same shape.
    # "WHERE 1 = 0" copies the schema without inserting any rows yet.
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {table}
        USING iceberg
        PARTITIONED BY (year, month)
        AS SELECT * FROM silver_source WHERE 1 = 0
        """
    )

    # Every run: merge by timestamp. The same input twice changes nothing;
    # a newer load of the same minute replaces the older row.
    spark.sql(
        f"""
        MERGE INTO {table} AS target
        USING silver_source AS source
        ON target.household_id = source.household_id
           AND target.reading_ts = source.reading_ts
        WHEN MATCHED AND source.load_ts >= target.load_ts THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
        """
    )

    final_count = spark.sql(f"SELECT count(*) AS n FROM {table}").collect()[0]["n"]
    print(f"Silver table row count after merge: {final_count}")

    job.commit()


if __name__ == "__main__":
    main()
