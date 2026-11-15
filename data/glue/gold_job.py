import sys

from awsglue.utils import getResolvedOptions
from pyspark.conf import SparkConf
from pyspark.context import SparkContext
from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

ARG_NAMES = [
    "JOB_NAME",
    "warehouse_path",
    "silver_database",
    "silver_table",
    "gold_database",
]

MINUTES_PER_HOUR = 60
MINUTES_PER_DAY = 1440


def iceberg_conf(warehouse_path: str) -> SparkConf:
    conf = SparkConf()
    conf.set(
        "spark.sql.extensions",
        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    )
    conf.set("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog")
    conf.set("spark.sql.catalog.glue_catalog.warehouse", warehouse_path)
    conf.set(
        "spark.sql.catalog.glue_catalog.catalog-impl",
        "org.apache.iceberg.aws.glue.GlueCatalog",
    )
    conf.set(
        "spark.sql.catalog.glue_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO"
    )
    return conf


def consumption(silver: DataFrame, period_start: Column, minutes_required: int) -> DataFrame:
    aggregated = silver.groupBy(
        "household_id", period_start.alias("period_start")
    ).agg(
        (F.sum("global_active_power_kw") / MINUTES_PER_HOUR).alias("energy_kwh"),
        (F.sum("sub_metering_1_wh") / 1000).alias("kitchen_kwh"),
        (F.sum("sub_metering_2_wh") / 1000).alias("laundry_kwh"),
        (F.sum("sub_metering_3_wh") / 1000).alias("heater_ac_kwh"),
        F.count("global_active_power_kw").alias("minutes_with_data"),
    )
    return aggregated.select(
        "household_id",
        "period_start",
        "energy_kwh",
        "kitchen_kwh",
        "laundry_kwh",
        "heater_ac_kwh",
        (
            F.col("energy_kwh")
            - F.col("kitchen_kwh")
            - F.col("laundry_kwh")
            - F.col("heater_ac_kwh")
        ).alias("other_kwh"),
        "minutes_with_data",
        (F.col("minutes_with_data") == minutes_required).alias("is_complete"),
        F.year("period_start").alias("year"),
        F.month("period_start").alias("month"),
    )


def daily_peak(hourly: DataFrame, silver: DataFrame) -> DataFrame:
    highest_hour_first = Window.partitionBy("household_id", "day").orderBy(
        F.col("energy_kwh").desc_nulls_last(), F.col("period_start").asc()
    )
    peak_hours = (
        hourly.withColumn("day", F.to_date("period_start"))
        .withColumn("hour_rank", F.row_number().over(highest_hour_first))
        .filter(F.col("hour_rank") == 1)
        .select(
            "household_id",
            "day",
            F.col("period_start").alias("peak_hour_start"),
            F.col("energy_kwh").alias("peak_hour_kwh"),
        )
    )
    minute_maxima = silver.groupBy(
        "household_id", F.to_date("reading_ts").alias("day")
    ).agg(F.max("global_active_power_kw").alias("max_minute_power_kw"))

    return peak_hours.join(minute_maxima, ["household_id", "day"]).select(
        "household_id",
        "day",
        "peak_hour_start",
        "peak_hour_kwh",
        "max_minute_power_kw",
        F.year("day").alias("year"),
        F.month("day").alias("month"),
    )


def publish(spark, table_name: str, gold_database: str, data: DataFrame) -> None:
    view_name = f"{table_name}_source"
    data.createOrReplaceTempView(view_name)
    spark.sql(
        f"""
        CREATE OR REPLACE TABLE glue_catalog.{gold_database}.{table_name}
        USING iceberg
        PARTITIONED BY (year, month)
        AS SELECT * FROM {view_name}
        """
    )
    count = spark.table(f"glue_catalog.{gold_database}.{table_name}").count()
    print(f"{gold_database}.{table_name}: {count} rows")


def main() -> None:
    args = getResolvedOptions(sys.argv, ARG_NAMES)
    spark_context = SparkContext(conf=iceberg_conf(args["warehouse_path"]))

    from awsglue.context import GlueContext
    from awsglue.job import Job

    glue_context = GlueContext(spark_context)
    spark = glue_context.spark_session
    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    silver = spark.table(
        f"glue_catalog.{args['silver_database']}.{args['silver_table']}"
    )

    hourly = consumption(silver, F.date_trunc("hour", F.col("reading_ts")), MINUTES_PER_HOUR)
    daily = consumption(silver, F.date_trunc("day", F.col("reading_ts")), MINUTES_PER_DAY)
    peaks = daily_peak(hourly, silver)

    publish(spark, "hourly_consumption", args["gold_database"], hourly)
    publish(spark, "daily_consumption", args["gold_database"], daily)
    publish(spark, "daily_peak", args["gold_database"], peaks)

    job.commit()


if __name__ == "__main__":
    main()
