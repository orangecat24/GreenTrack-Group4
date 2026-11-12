output "data_lake_bucket_name" {
  description = "The one S3 bucket holding raw, bronze, silver, gold, scripts and Athena results."
  value       = aws_s3_bucket.data_lake.bucket
}

output "raw_upload_uri" {
  description = "Upload new source CSV files under this prefix."
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/${local.raw_prefix}"
}

output "athena_results_uri" {
  description = "Configure Athena to write query results here."
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/${local.athena_results_prefix}"
}

output "bronze_database_name" {
  description = "Glue catalog database for the bronze layer."
  value       = aws_glue_catalog_database.bronze.name
}

output "bronze_table_name" {
  description = "Queryable bronze table (all source columns as text plus traceability metadata)."
  value       = aws_glue_catalog_table.raw_readings.name
}

output "bronze_job_name" {
  description = "Glue job converting raw CSV to bronze Parquet."
  value       = aws_glue_job.bronze.name
}

output "silver_database_name" {
  description = "Glue catalog database for the silver layer."
  value       = aws_glue_catalog_database.silver.name
}

output "silver_table_name" {
  description = "Iceberg readings table; created by the silver job's first run."
  value       = "readings"
}

output "silver_job_name" {
  description = "Glue job cleaning bronze into the silver Iceberg table."
  value       = aws_glue_job.silver.name
}

output "quality_job_name" {
  description = "Glue job evaluating the DQDL ruleset against the silver table."
  value       = aws_glue_job.quality.name
}

output "quality_results_uri" {
  description = "Data quality evaluation results location."
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/${local.quality_results_prefix}"
}

output "glue_pipeline_role_arn" {
  description = "IAM role the Glue pipeline jobs run as."
  value       = aws_iam_role.glue_pipeline.arn
}
