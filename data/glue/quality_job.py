import sys

import boto3
from awsglue.utils import getResolvedOptions
from pyspark.conf import SparkConf
from pyspark.context import SparkContext

ARG_NAMES = [
    "JOB_NAME",
    "warehouse_path",
    "silver_database",
    "silver_table",
    "ruleset_bucket",
    "ruleset_key",
    "results_path",
]


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


def load_ruleset(bucket: str, key: str) -> str:
    response = boto3.client("s3").get_object(Bucket=bucket, Key=key)
    return response["Body"].read().decode("utf-8")


def main() -> None:
    args = getResolvedOptions(sys.argv, ARG_NAMES)
    spark_context = SparkContext(conf=iceberg_conf(args["warehouse_path"]))

    from awsglue.context import GlueContext
    from awsglue.dynamicframe import DynamicFrame
    from awsglue.job import Job
    from awsgluedq.transforms import EvaluateDataQuality

    glue_context = GlueContext(spark_context)
    spark = glue_context.spark_session
    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    ruleset = load_ruleset(args["ruleset_bucket"], args["ruleset_key"])
    silver = spark.table(
        f"glue_catalog.{args['silver_database']}.{args['silver_table']}"
    )
    frame = DynamicFrame.fromDF(silver, glue_context, "silver_readings")

    outcomes = EvaluateDataQuality.apply(
        frame=frame,
        ruleset=ruleset,
        publishing_options={
            "dataQualityEvaluationContext": "silver_readings",
            "enableDataQualityCloudWatchMetrics": False,
            "enableDataQualityResultsPublishing": True,
            "resultsS3Prefix": args["results_path"],
        },
    )

    results = outcomes.toDF()
    results.show(n=50, truncate=False)

    failed = [row for row in results.collect() if row["Outcome"] != "Passed"]
    if failed:
        summary = "; ".join(
            f"{row['Rule']} ({row['FailureReason']})" for row in failed
        )
        raise RuntimeError(f"Data quality failed on {len(failed)} rule(s): {summary}")

    job.commit()


if __name__ == "__main__":
    main()
