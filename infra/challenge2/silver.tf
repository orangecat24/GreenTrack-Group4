# Silver layer: cleaned, typed readings in an Apache Iceberg table.
#
# Unlike bronze, the silver TABLE is not defined in Terraform: Iceberg tables
# carry their own metadata (schema, snapshots, partitions), and the engine
# that writes them must create them. The silver job creates the table on its
# first run inside this Terraform-managed database, under the silver/ prefix
# of the Terraform-managed bucket, running as the Terraform-managed role.

resource "aws_glue_catalog_database" "silver" {
  name = "${local.database_prefix}_silver"
  tags = local.tags
}

resource "aws_s3_object" "silver_job_script" {
  bucket      = aws_s3_bucket.data_lake.id
  key         = "${local.scripts_prefix}silver_job.py"
  source      = var.silver_job_script_path
  source_hash = filemd5(var.silver_job_script_path)
  tags        = local.tags
}

resource "aws_glue_job" "silver" {
  name     = "${var.name_prefix}-silver"
  role_arn = aws_iam_role.glue_pipeline.arn
  tags     = local.tags

  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  execution_property {
    max_concurrent_runs = 1
  }
  # Cleaning plus an Iceberg MERGE over the full 2M-row file needs more room
  # than the bronze conversion.
  timeout = 60 # minutes

  command {
    script_location = "s3://${aws_s3_bucket.data_lake.bucket}/${aws_s3_object.silver_job_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    # Our script's own arguments; names match contracts/data.md section 5.
    "--bronze_path"     = "s3://${aws_s3_bucket.data_lake.bucket}/${local.bronze_table_location}"
    "--warehouse_path"  = "s3://${aws_s3_bucket.data_lake.bucket}/silver/"
    "--silver_database" = aws_glue_catalog_database.silver.name
    "--silver_table"    = "readings"
    "--household_id"    = "household-1"

    # Tells Glue 5.0 to put the Iceberg runtime on the job's classpath; the
    # script itself configures the Iceberg catalog before Spark starts.
    "--datalake-formats" = "iceberg"

    # Standard Glue housekeeping.
    "--TempDir"                          = "s3://${aws_s3_bucket.data_lake.bucket}/${local.glue_temp_prefix}"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-metrics"                   = "false"
  }
}
