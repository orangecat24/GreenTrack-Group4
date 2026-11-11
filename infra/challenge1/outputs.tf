output "api_base_url" {
  description = "Complete VITE_API_BASE_URL prefix. $default stage means no /stage or /api suffix."
  value       = aws_apigatewayv2_api.api.api_endpoint
}

output "website_url" {
  description = "Public HTTPS website URL after assets have been uploaded."
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "frontend_bucket_name" {
  description = "Private deployment destination for web/dist, never a public website endpoint."
  value       = aws_s3_bucket.frontend.id
}

output "cloudfront_distribution_id" {
  description = "Distribution ID for a later authorized index.html invalidation."
  value       = aws_cloudfront_distribution.frontend.id
}

output "table_names" {
  description = "Explicit destinations for the separately authorized seed loader."
  value       = { for name, table in aws_dynamodb_table.demo : name => table.name }
}

output "configuration_parameters" {
  description = "Non-secret SSM parameter names; runtime uses the same Terraform values directly."
  value       = { for key, parameter in aws_ssm_parameter.api_configuration : key => parameter.name }
}

output "api_lambda_name" {
  description = "Function name for later deployment diagnostics."
  value       = aws_lambda_function.api.function_name
}
