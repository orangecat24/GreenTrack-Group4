output "sagemaker_execution_role_arn" {
  description = "Role SageMaker processing, training and inference jobs assume."
  value       = aws_iam_role.sagemaker_execution.arn
}

output "forecast_model_package_group" {
  description = "Model Registry group for forecasting models."
  value       = aws_sagemaker_model_package_group.forecast.model_package_group_name
}

output "anomaly_model_package_group" {
  description = "Model Registry group for anomaly models."
  value       = aws_sagemaker_model_package_group.anomaly.model_package_group_name
}

output "artifacts_prefix" {
  description = "S3 prefix under the data lake bucket for model artifacts."
  value       = "s3://${var.data_lake_bucket_name}/${local.artifacts_key}"
}

output "scripts_prefix" {
  description = "S3 prefix for pipeline entry-point scripts that Person 3 publishes."
  value       = "s3://${var.data_lake_bucket_name}/${local.scripts_key}"
}
