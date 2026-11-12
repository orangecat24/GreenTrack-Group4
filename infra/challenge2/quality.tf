resource "aws_s3_object" "quality_ruleset" {
  bucket      = aws_s3_bucket.data_lake.id
  key         = "${local.scripts_prefix}silver_readings.dqdl"
  source      = var.quality_ruleset_path
  source_hash = filemd5(var.quality_ruleset_path)
  tags        = local.tags
}

resource "aws_s3_object" "quality_job_script" {
  bucket      = aws_s3_bucket.data_lake.id
  key         = "${local.scripts_prefix}quality_job.py"
  source      = var.quality_job_script_path
  source_hash = filemd5(var.quality_job_script_path)
  tags        = local.tags
}

resource "aws_glue_job" "quality" {
  name     = "${var.name_prefix}-quality"
  role_arn = aws_iam_role.glue_pipeline.arn
  tags     = local.tags

  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  execution_property {
    max_concurrent_runs = 1
  }
  timeout = 30

  command {
    script_location = "s3://${aws_s3_bucket.data_lake.bucket}/${aws_s3_object.quality_job_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--warehouse_path"  = "s3://${aws_s3_bucket.data_lake.bucket}/silver/"
    "--silver_database" = aws_glue_catalog_database.silver.name
    "--silver_table"    = "readings"
    "--ruleset_bucket"  = aws_s3_bucket.data_lake.bucket
    "--ruleset_key"     = aws_s3_object.quality_ruleset.key
    "--results_path"    = "s3://${aws_s3_bucket.data_lake.bucket}/${local.quality_results_prefix}"

    "--datalake-formats" = "iceberg"

    "--TempDir"                          = "s3://${aws_s3_bucket.data_lake.bucket}/${local.glue_temp_prefix}"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-metrics"                   = "false"
  }
}
