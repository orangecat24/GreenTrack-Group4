resource "aws_glue_catalog_database" "gold" {
  name = "${local.database_prefix}_gold"
  tags = local.tags
}

resource "aws_s3_object" "gold_job_script" {
  bucket      = aws_s3_bucket.data_lake.id
  key         = "${local.scripts_prefix}gold_job.py"
  source      = var.gold_job_script_path
  source_hash = filemd5(var.gold_job_script_path)
  tags        = local.tags
}

resource "aws_glue_job" "gold" {
  name     = "${var.name_prefix}-gold"
  role_arn = aws_iam_role.glue_pipeline.arn
  tags     = local.tags

  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  execution_property {
    max_concurrent_runs = 1
  }
  timeout = 60

  command {
    script_location = "s3://${aws_s3_bucket.data_lake.bucket}/${aws_s3_object.gold_job_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--warehouse_path"  = "s3://${aws_s3_bucket.data_lake.bucket}/gold/"
    "--silver_database" = aws_glue_catalog_database.silver.name
    "--silver_table"    = "readings"
    "--gold_database"   = aws_glue_catalog_database.gold.name

    "--datalake-formats" = "iceberg"

    "--TempDir"                          = "s3://${aws_s3_bucket.data_lake.bucket}/${local.glue_temp_prefix}"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-metrics"                   = "false"
  }
}
