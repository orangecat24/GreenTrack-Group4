# Challenge 2 data lake: one S3 bucket holding every pipeline layer, kept in
# clearly separated prefixes so an upload trigger can later watch raw/ only and
# never fire again on the pipeline's own Parquet or query-result writes.
#
#   raw/            the CSV exactly as uploaded (never modified or deleted)
#   bronze/         Parquet conversion of raw, no business cleaning
#   silver/         cleaned Iceberg tables (added by the silver task, P1 04)
#   gold/           business summaries (added by the gold task, P1 06)
#   scripts/        Glue job scripts uploaded by Terraform
#   glue-temp/      scratch space Glue jobs need while running
#   athena-results/ Athena query output (Athena always needs a write location)

data "aws_caller_identity" "current" {}

locals {
  tags = merge(var.tags, { Challenge = "2" })

  # The account ID makes the bucket name unique across all of AWS,
  # the same trick the Terraform state bucket uses.
  bucket_name = "${var.name_prefix}-datalake-${data.aws_caller_identity.current.account_id}"

  raw_prefix            = "raw/"
  bronze_prefix         = "bronze/"
  bronze_table_location = "bronze/raw_readings/"
  scripts_prefix        = "scripts/"
  glue_temp_prefix      = "glue-temp/"
  athena_results_prefix = "athena-results/"

  # Glue database names may not contain dashes, so g4-greentrack-dev
  # becomes g4_greentrack_dev_bronze.
  database_prefix = replace(var.name_prefix, "-", "_")
}

resource "aws_s3_bucket" "data_lake" {
  bucket = local.bucket_name
  tags   = local.tags

  # The raw layer must stay exactly as received; refuse accidental destroys.
  lifecycle {
    prevent_destroy = true
  }
}

# Versioning protects the raw files: even an accidental overwrite of an
# uploaded CSV keeps the previous version recoverable.
resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket                  = aws_s3_bucket.data_lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
