# Bronze layer catalog and job. The bronze table keeps every source column as
# text, exactly as received ("?" stays "?"); only traceability metadata is
# added. Cleaning happens later, in silver.

resource "aws_glue_catalog_database" "bronze" {
  name = "${local.database_prefix}_bronze"
  tags = local.tags
}

# The table schema is defined here (one source of truth, reviewable in a PR);
# the Glue job only writes matching Parquet files into the table's location.
# Athena reads all objects under that location, including the per-source-file
# subfolders the job creates.
resource "aws_glue_catalog_table" "raw_readings" {
  name          = "raw_readings"
  database_name = aws_glue_catalog_database.bronze.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_lake.bucket}/${local.bronze_table_location}"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.parquet.ParquetHiveSerDe"
    }

    # The seven value columns stay text on purpose: bronze preserves "?" and
    # any malformed input instead of silently repairing it.
    dynamic "columns" {
      for_each = [
        "date", "time",
        "global_active_power", "global_reactive_power",
        "voltage", "global_intensity",
        "sub_metering_1", "sub_metering_2", "sub_metering_3",
        "source_file",
      ]
      content {
        name = columns.value
        type = "string"
      }
    }

    columns {
      name = "load_ts"
      type = "timestamp"
    }
  }
}

# Terraform uploads the job script so deployments never depend on a laptop.
resource "aws_s3_object" "bronze_job_script" {
  bucket      = aws_s3_bucket.data_lake.id
  key         = "${local.scripts_prefix}bronze_job.py"
  source      = var.bronze_job_script_path
  source_hash = filemd5(var.bronze_job_script_path)
  tags        = local.tags
}

resource "aws_glue_job" "bronze" {
  name     = "${var.name_prefix}-bronze"
  role_arn = aws_iam_role.glue_pipeline.arn
  tags     = local.tags

  glue_version = "5.0"
  # Smallest practical Spark setup: 2 workers is the Glue minimum for G.1X.
  worker_type       = "G.1X"
  number_of_workers = 2
  # One run at a time, no retry storms while we are learning the pipeline.
  execution_property {
    max_concurrent_runs = 1
  }
  timeout = 30 # minutes; the full 2M-row file converts well within this

  command {
    script_location = "s3://${aws_s3_bucket.data_lake.bucket}/${aws_s3_object.bronze_job_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    # Our script's own arguments. raw_key is overridden per run with the
    # specific uploaded file; the default converts the whole raw/ prefix.
    "--raw_key"     = ""
    "--raw_path"    = "s3://${aws_s3_bucket.data_lake.bucket}/${local.raw_prefix}"
    "--bronze_path" = "s3://${aws_s3_bucket.data_lake.bucket}/${local.bronze_table_location}"

    # Standard Glue housekeeping.
    "--TempDir"                          = "s3://${aws_s3_bucket.data_lake.bucket}/${local.glue_temp_prefix}"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-metrics"                   = "false"
  }
}
